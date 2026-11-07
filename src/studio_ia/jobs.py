"""Transactional history and one intensive worker; restart never invents success."""

import json
import sqlite3
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from studio_ia.core import Cancellation, Cancelled, StudioError, Tools, build_identity
from studio_ia.pipeline import Request, build_plan, run_plan

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}


class Store:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = root
        self.path = root / "jobs.sqlite3"
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StudioError(
                    "Historique créé par une version plus récente ; ne pas le modifier."
                )
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("PRAGMA user_version=1")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def put(self, data: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?, ?)",
                (data["id"], json.dumps(data, ensure_ascii=False)),
            )

    def get(self, job_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise StudioError("Tâche introuvable.")
        return json.loads(row[0])

    def list(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT data FROM jobs ORDER BY rowid DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def remove(self, job_id: str) -> None:
        if self.get(job_id)["state"] not in TERMINAL:
            raise StudioError("Impossible de supprimer une tâche active.")
        with self.connect() as db:
            db.execute("DELETE FROM jobs WHERE id=?", (job_id,))


class Manager:
    def __init__(self, root: Path, tools: Tools | None = None):
        self.store = Store(root)
        self.tools = tools
        self.lock = threading.RLock()
        self.tokens: dict[str, Cancellation] = {}
        self.closed = False
        # OS advisory lock is released after a crash. Do not recover another live manager's jobs.
        self.owner = (root / "manager.lock").open("a+b")
        try:
            if sys.platform == "win32":
                import msvcrt

                self.owner.seek(0)
                self.owner.write(b"0")
                self.owner.flush()
                self.owner.seek(0)
                msvcrt.locking(self.owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.owner.close()
            raise StudioError("STUDIO IA est déjà ouvert avec cet historique.") from exc
        for row in self.store.list():
            if row["state"] not in TERMINAL:
                row.update(
                    state="INTERRUPTED", error="Arrêt précédent ; relancer depuis l'original."
                )
                self.store.put(row)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="studio-job")

    def update(self, job_id: str, **changes) -> None:
        with self.lock:
            row = self.store.get(job_id)
            if row["state"] == "CANCEL_REQUESTED" and changes.get("state") in (
                "VALIDATING",
                "QUEUED",
                "RUNNING",
                "VERIFYING",
            ):
                changes.pop("state")
            row.update(changes)
            row["updated_at"] = datetime.now(UTC).isoformat()
            self.store.put(row)

    def submit(self, request: Request) -> str:
        with self.lock:
            if self.closed:
                raise StudioError("Gestionnaire fermé.")
            destination = Path(request.destination).expanduser().resolve()
            for job_id in self.tokens:
                row = self.store.get(job_id)
                if (
                    row["state"] not in TERMINAL
                    and Path(row["request"]["destination"]).resolve() == destination
                ):
                    raise StudioError("Une tâche utilise déjà cette destination.")
            job_id = str(uuid.uuid4())
            self.store.put(
                {
                    "id": job_id,
                    "state": "CREATED",
                    "created_at": datetime.now(UTC).isoformat(),
                    "request": asdict(request),
                    "progress": None,
                    "elapsed_seconds": 0,
                    "error": None,
                    "result": None,
                    "application": build_identity(),
                }
            )
            self.tokens[job_id] = Cancellation()
            self.pool.submit(self._run, job_id, request)
            return job_id

    def _run(self, job_id: str, request: Request) -> None:
        token = self.tokens[job_id]
        started = time.monotonic()
        last_update = 0.0
        try:
            token.check()
            self.update(job_id, state="VALIDATING")
            tools = self.tools or Tools.discover()
            plan = build_plan(request, tools)
            token.check()
            self.update(job_id, state="QUEUED", plan=plan.to_dict())

            def progress(value: float | None) -> None:
                nonlocal last_update
                now = time.monotonic()
                if now - last_update >= 0.2:
                    self.update(job_id, progress=value, elapsed_seconds=now - started)
                    last_update = now

            result = run_plan(
                plan,
                tools,
                self.store.root / "jobs" / job_id,
                token,
                progress,
                lambda state: self.update(job_id, state=state),
            )
            self.update(
                job_id,
                state="SUCCEEDED",
                progress=1,
                result=result,
                elapsed_seconds=time.monotonic() - started,
            )
        except Cancelled as exc:
            self.update(
                job_id,
                state="CANCELLED",
                error=str(exc),
                elapsed_seconds=time.monotonic() - started,
            )
        except Exception as exc:
            self.update(
                job_id, state="FAILED", error=str(exc), elapsed_seconds=time.monotonic() - started
            )
        finally:
            with self.lock:
                self.tokens.pop(job_id, None)

    def cancel(self, job_id: str) -> None:
        with self.lock:
            row = self.store.get(job_id)
            token = self.tokens.get(job_id)
            if row["state"] not in TERMINAL and token and token.request():
                self.update(job_id, state="CANCEL_REQUESTED")

    def retry(self, job_id: str, destination: str) -> str:
        row = self.store.get(job_id)
        if row["state"] not in TERMINAL:
            raise StudioError("Attendre la fin de la tâche avant relancement.")
        return self.submit(Request(**{**row["request"], "destination": destination}))

    def close(self) -> None:
        with self.lock:
            if self.closed:
                return
            self.closed = True
            for job_id in self.tokens:
                self.cancel(job_id)
        self.pool.shutdown(wait=True)
        self.owner.close()

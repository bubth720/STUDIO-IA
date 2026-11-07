"""Configuration, capabilities and cancellable external processes. Never uses a shell."""

import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from studio_ia import __version__


class StudioError(Exception):
    """Actionable error, safe to show in the local UI."""


class Cancelled(StudioError):
    pass


def build_identity() -> dict:
    identity: dict = {
        "version": __version__,
        "source_sha": os.environ.get("GITHUB_SHA")
        or os.environ.get("STUDIO_IA_SOURCE_SHA", "unknown"),
    }
    if getattr(sys, "frozen", False):
        manifest = Path(sys.executable).parent / "BUILD_INFO.json"
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            identity["source_sha"] = data["source_commit"]
            identity["source_dirty"] = data["source_dirty"]
    else:
        git_dir = Path(__file__).resolve().parents[2] / ".git"
        if git_dir.is_dir():
            head = (git_dir / "HEAD").read_text().strip()
            if head.startswith("ref: "):
                reference = git_dir / head[5:]
                if reference.is_file():
                    identity["source_sha"] = reference.read_text().strip()
            else:
                identity["source_sha"] = head
    return identity


class Cancellation:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.committed = False

    def request(self) -> bool:
        with self.lock:
            if self.committed:
                return False
            self.event.set()
            return True

    def check(self) -> None:
        if self.event.is_set():
            raise Cancelled("Traitement annulé ; source conservée.")


def state_dir() -> Path:
    root = os.environ.get("STUDIO_IA_HOME")
    if root:
        path = Path(root)
    elif os.name == "nt":
        path = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "STUDIO-IA"
    else:
        path = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "studio-ia"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


@dataclass(frozen=True)
class Tools:
    ffmpeg: str
    ffprobe: str

    @classmethod
    def discover(cls) -> "Tools":
        config_path = state_dir() / "config.json"
        try:
            config = json.loads(config_path.read_text()) if config_path.exists() else {}
        except (OSError, ValueError) as exc:
            raise StudioError("Configuration illisible ; corriger config.json.") from exc
        found = []
        for name in ("ffmpeg", "ffprobe"):
            configured = os.environ.get(f"STUDIO_IA_{name.upper()}") or config.get(name)
            candidate = shutil.which(configured or name)
            if not candidate:
                raise StudioError(f"{name} absent. Installer localement ou configurer son chemin.")
            found.append(str(Path(candidate).resolve()))
        return cls(*found)


def process_options() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def capture(args: list[str], timeout: float = 30) -> str:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            **process_options(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StudioError(f"Impossible d'exécuter {Path(args[0]).name} : {exc}") from exc
    if result.returncode:
        raise StudioError(f"{Path(args[0]).name} : {result.stderr[-3000:]}")
    return result.stdout


def capabilities(tools: Tools) -> dict:
    ffmpeg = capture([tools.ffmpeg, "-version"])
    ffprobe = capture([tools.ffprobe, "-version"])
    encoders_text = capture([tools.ffmpeg, "-hide_banner", "-encoders"])
    filters_text = capture([tools.ffmpeg, "-hide_banner", "-filters"])
    encoders = [line.split()[1] for line in encoders_text.splitlines() if len(line.split()) >= 2]
    filters = [line.split()[1] for line in filters_text.splitlines() if len(line.split()) >= 2]
    return {
        "schema_version": 1,
        "application": build_identity(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "tools": asdict(tools),
        "ffmpeg_version": ffmpeg.splitlines()[0],
        "ffprobe_version": ffprobe.splitlines()[0],
        "ffmpeg_build": ffmpeg,
        "encoders": encoders,
        "filters": filters,
        "cpu_ready": all(x in encoders for x in ("libx264", "aac"))
        and all(x in filters for x in ("hqdn3d", "scale", "eq", "setsar")),
        "neural_validated": False,
    }


def stop_process(proc: subprocess.Popen) -> None:
    """Ask ffmpeg to exit, then terminate/kill its owned process group if necessary."""
    if proc.poll() is not None:
        return
    try:
        if proc.stdin:
            proc.stdin.write("q\n")
            proc.stdin.flush()
        proc.wait(timeout=2)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, check=False
            )
        else:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    except ProcessLookupError:
        pass


def execute(
    args: list[str],
    log: Path,
    cancel: Cancellation,
    progress: Callable[[float | None], None] | None = None,
    duration: float | None = None,
    timeout: float = 86400,
) -> None:
    cancel.check()
    started = time.monotonic()
    try:
        with log.open("a", encoding="utf-8") as stderr:
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
                text=True,
                encoding="utf-8",
                errors="replace",
                **process_options(),
            )
            failures: list[Exception] = []

            def read_progress() -> None:
                assert proc.stdout is not None
                try:
                    for line in proc.stdout:
                        if progress and line.startswith("out_time_us="):
                            try:
                                seconds = int(line.strip().split("=", 1)[1]) / 1e6
                                progress(min(0.98, seconds / duration) if duration else None)
                            except ValueError:
                                pass
                except Exception as exc:
                    failures.append(exc)

            reader = threading.Thread(target=read_progress, daemon=True)
            reader.start()
            try:
                while proc.poll() is None:
                    cancel.check()
                    if time.monotonic() - started > timeout:
                        raise StudioError("Délai de traitement dépassé (24 h maximum).")
                    time.sleep(0.05)
                cancel.check()
                reader.join(timeout=5)
                if failures:
                    raise StudioError(f"Lecture progression : {failures[0]}")
                if proc.returncode:
                    raise StudioError(f"FFmpeg a échoué (code {proc.returncode}). Voir le journal.")
            finally:
                stop_process(proc)
                reader.join(timeout=5)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stdin:
                    proc.stdin.close()
    except OSError as exc:
        raise StudioError(f"Erreur processus ou stockage : {exc}") from exc

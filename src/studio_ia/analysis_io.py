"""Bounded, cancellable local-tool capture, reusing the existing process-group policy."""

import math
import subprocess
import threading
import time
from pathlib import Path

from studio_ia.core import (
    Cancellation,
    StudioError,
    external_process_env,
    process_options,
    stop_process,
)


def capture_local(
    args: list[str],
    cancel: Cancellation | None = None,
    *,
    timeout: float = 120,
    max_bytes: int = 16 * 1024**2,
) -> str:
    cancel = cancel or Cancellation()
    cancel.check()
    if (
        not args
        or not math.isfinite(timeout)
        or not 0 < timeout <= 3600
        or type(max_bytes) is not int
        or not 1 <= max_bytes <= 32 * 1024**2
    ):
        raise StudioError("Budget de capture invalide.")
    chunks: list[bytes] = []
    errors: list[Exception] = []
    started = time.monotonic()
    try:
        with subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=external_process_env(),
            **process_options(),
        ) as proc:
            stderr_tail: list[bytes] = []

            def read():
                total = 0
                try:
                    assert proc.stdout is not None
                    while chunk := proc.stdout.read(65536):
                        total += len(chunk)
                        if total > max_bytes:
                            raise StudioError("Sortie de diagnostic hors budget.")
                        chunks.append(chunk)
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=read, daemon=True)
            worker.start()

            def read_errors():
                total = 0
                try:
                    assert proc.stderr is not None
                    while chunk := proc.stderr.read(65536):
                        total += len(chunk)
                        stderr_tail[:] = [b"".join(stderr_tail + [chunk])[-65536:]]
                        if total > max_bytes:
                            raise StudioError("Journal de diagnostic hors budget.")
                except Exception as exc:
                    errors.append(exc)

            error_worker = threading.Thread(target=read_errors, daemon=True)
            error_worker.start()
            try:
                while proc.poll() is None:
                    cancel.check()
                    if errors:
                        raise errors[0]
                    if time.monotonic() - started > timeout:
                        raise StudioError("Délai de diagnostic dépassé.")
                    time.sleep(0.02)
                cancel.check()
                worker.join(timeout=5)
                error_worker.join(timeout=5)
                if worker.is_alive() or error_worker.is_alive():
                    raise StudioError("Lecture du diagnostic incomplète.")
                if errors:
                    raise errors[0]
                if proc.returncode:
                    detail = b"".join(stderr_tail)[-3000:].decode("utf-8", "replace")
                    raise StudioError(f"{Path(args[0]).name} (code {proc.returncode}) : {detail}")
                return b"".join(chunks).decode("utf-8", "replace")
            finally:
                stop_process(proc)
                worker.join(timeout=5)
                error_worker.join(timeout=5)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
    except OSError as exc:
        raise StudioError("Outil local ou stockage de diagnostic inaccessible.") from exc

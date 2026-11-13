"""UTF-8 metadata and atomic publication without replacing existing files."""

import ctypes
import errno
import json
import os
import sys
import tempfile
from pathlib import Path


def publish_no_replace(source: Path, destination: Path) -> str:
    if sys.platform == "win32":
        # Windows rename fails if the destination exists; works without hard-link support.
        os.rename(source, destination)
        return "windows_rename_no_replace"
    try:
        os.link(source, destination)
        return "hard_link_no_replace"
    except OSError as exc:
        if exc.errno not in (errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS):
            raise
        if sys.platform != "linux":
            raise
        library = ctypes.CDLL(None, use_errno=True)
        rename = getattr(library, "renameat2", None)
        if rename is None:
            raise exc
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        # AT_FDCWD, RENAME_NOREPLACE; no fallback to POSIX overwrite-capable rename.
        if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(destination)) from exc
        return "linux_renameat2_no_replace"


def write_json(path: Path, data: dict | list, *, replace: bool = True) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".studio-json-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            publish_no_replace(temporary, path)
    finally:
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

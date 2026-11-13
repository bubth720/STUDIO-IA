"""Machine profile and resource policy (Windows first, Linux maintained). No Qt.

Detects CPU, logical cores, RAM, free disk and Vulkan GPUs with their device-local
memory, then derives what STUDIO IA may attempt on THIS machine. Thresholds are
conservative ESTIMATES, not measurements: they only choose safe defaults (tile size,
disk budget) and refuse clearly impossible work. A real run always has the last word.
Nothing here installs, downloads or launches anything.
"""

import ctypes
import os
import platform
import shutil
import sys
from pathlib import Path

from studio_ia.hardware import vulkan_devices

GIB = 1024**3


def cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            ) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    info = Path("/proc/cpuinfo")
    if info.is_file():
        for line in info.read_text(errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "inconnu"


def memory_bytes() -> tuple[int | None, int | None]:
    """(total, available) physical RAM, or (None, None) when unknown."""
    if sys.platform == "win32":

        class Status(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = Status()
        status.dwLength = ctypes.sizeof(Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
            return status.ullTotalPhys, status.ullAvailPhys
        return None, None
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values = {}
        for line in meminfo.read_text().splitlines():
            key, _, rest = line.partition(":")
            if rest.strip().endswith("kB"):
                values[key] = int(rest.split()[0]) * 1024
        return values.get("MemTotal"), values.get("MemAvailable")
    return None, None


def pick_gpu(devices: list[dict]) -> dict | None:
    """Prefer a discrete GPU, then the largest device-local memory; never a CPU device."""
    physical = [d for d in devices if d.get("physical_gpu")]
    if not physical:
        return None
    return sorted(
        physical,
        key=lambda d: (d.get("device_type") != 2, -(d.get("device_local_bytes") or 0), d["index"]),
    )[0]


def recommended_tile(vram: int | None) -> int | None:
    """NCNN tile size from device-local memory (ESTIMATE; smaller tiles = less memory)."""
    if not vram:
        return None
    if vram >= 6 * GIB:
        return 256
    if vram >= 3 * GIB:
        return 128
    if vram >= 3 * GIB // 2:
        return 64
    if vram >= GIB:
        return 32
    return None


def profile(work_dir: Path | None = None, *, vulkan: dict | None = None) -> dict:
    work_dir = work_dir or Path.home()
    total, available = memory_bytes()
    try:
        free_disk = shutil.disk_usage(work_dir).free
    except OSError:
        free_disk = None
    vk = vulkan if vulkan is not None else vulkan_devices()
    gpu = pick_gpu(vk.get("devices", []))
    vram = gpu.get("device_local_bytes") if gpu else None
    tile = recommended_tile(vram) if gpu else None
    try:
        from studio_ia.core import StudioError, Tools

        Tools.discover()
        ffmpeg = True
    except (StudioError, OSError):
        ffmpeg = False
    limits: list[str] = []
    restore_ai = "BLOCKED"
    if gpu is None:
        limits.append(
            "Aucun GPU Vulkan physique : restauration IA indisponible, mode CPU classique seul."
        )
    elif tile is None:
        limits.append("Mémoire graphique < 1 Gio : restauration IA refusée sur ce GPU.")
    else:
        restore_ai = "POSSIBLE_NOT_QUALIFIED"
    if total is not None and total < 8 * GIB:
        limits.append("Moins de 8 Gio de RAM : vidéos courtes et basse résolution conseillées.")
    if free_disk is not None and free_disk < 10 * GIB:
        limits.append(
            "Moins de 10 Gio libres : les traitements IA (images temporaires) seront limités."
        )
    unreal_ok = (total or 0) >= 16 * GIB and (vram or 0) >= 4 * GIB and gpu is not None
    if not unreal_ok:
        limits.append(
            "Sous la configuration conseillée par Epic pour Unreal (32 Go RAM, GPU 8 Go) : "
            "CREATE reste utilisable pour préparer les scènes ; rendu Unreal non garanti."
        )
    workspace = None
    if free_disk is not None:
        workspace = int(min(16 * GIB, max(64 * 1024**2, free_disk * 0.5)))
    return {
        "schema_version": 1,
        "os": platform.platform(),
        "machine": platform.machine(),
        "cpu": {"name": cpu_name(), "logical_cores": os.cpu_count()},
        "ram": {"total_bytes": total, "available_bytes": available},
        "disk": {"path": str(work_dir), "free_bytes": free_disk},
        "gpu": {
            "vulkan_status": vk.get("status"),
            "vulkan_reason": vk.get("reason"),
            "devices": vk.get("devices", []),
            "selected": gpu,
            "device_local_bytes": vram,
        },
        "capabilities": {
            "restore_cpu": "READY" if ffmpeg else "FFMPEG_MISSING",
            "restore_ai": restore_ai,
            "create_scene_preparation": "READY",
            "create_unreal_render": "NOT_TESTED_RECOMMENDED_HARDWARE"
            if unreal_ok
            else "BELOW_RECOMMENDED_HARDWARE",
        },
        "recommendations": {
            "ncnn_tile": tile,
            "ncnn_gpu_index": gpu["index"] if gpu else None,
            "neural_workspace_bytes": workspace,
            "basis": "ESTIMATES_FROM_DETECTED_RESOURCES_NOT_MEASUREMENTS",
        },
        "limits": limits,
    }


def human(value: int | None) -> str:
    return "inconnu" if value is None else f"{value / GIB:.1f} Gio"

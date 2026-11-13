"""Read-only Vulkan enumeration. Loader presence is never inference qualification."""

import ctypes as C
import ctypes.util
import platform
from pathlib import Path


class ApplicationInfo(C.Structure):
    _fields_ = [
        ("sType", C.c_uint32),
        ("pNext", C.c_void_p),
        ("pApplicationName", C.c_char_p),
        ("applicationVersion", C.c_uint32),
        ("pEngineName", C.c_char_p),
        ("engineVersion", C.c_uint32),
        ("apiVersion", C.c_uint32),
    ]


class InstanceInfo(C.Structure):
    _fields_ = [
        ("sType", C.c_uint32),
        ("pNext", C.c_void_p),
        ("flags", C.c_uint32),
        ("pApplicationInfo", C.POINTER(ApplicationInfo)),
        ("layerCount", C.c_uint32),
        ("layers", C.c_void_p),
        ("extensionCount", C.c_uint32),
        ("extensions", C.c_void_p),
    ]


class PhysicalProperties(C.Structure):
    # Reserve more than VkPhysicalDeviceLimits + SparseProperties on all supported ABIs.
    _fields_ = [
        ("apiVersion", C.c_uint32),
        ("driverVersion", C.c_uint32),
        ("vendorID", C.c_uint32),
        ("deviceID", C.c_uint32),
        ("deviceType", C.c_uint32),
        ("deviceName", C.c_char * 256),
        ("remainder", C.c_uint64 * 1024),
    ]


class MemoryType(C.Structure):
    _fields_ = [("propertyFlags", C.c_uint32), ("heapIndex", C.c_uint32)]


class MemoryHeap(C.Structure):
    _fields_ = [("size", C.c_uint64), ("flags", C.c_uint32)]


class MemoryProperties(C.Structure):
    _fields_ = [
        ("memoryTypeCount", C.c_uint32),
        ("memoryTypes", MemoryType * 32),
        ("memoryHeapCount", C.c_uint32),
        ("memoryHeaps", MemoryHeap * 16),
    ]


DEVICE_TYPES = {0: "OTHER", 1: "INTEGRATED_GPU", 2: "DISCRETE_GPU", 3: "VIRTUAL_GPU", 4: "CPU"}


def vulkan_devices() -> dict:
    instance = C.c_void_p()
    lib = None
    try:
        name = (
            "vulkan-1.dll" if platform.system() == "Windows" else ctypes.util.find_library("vulkan")
        )
        if not name:
            return {"status": "BLOCKED", "reason": "VULKAN_LOADER_ABSENT", "devices": []}
        lib = C.CDLL(name)
        create = lib.vkCreateInstance
        create.argtypes = [C.POINTER(InstanceInfo), C.c_void_p, C.POINTER(C.c_void_p)]
        create.restype = C.c_int32
        app = ApplicationInfo(0, None, b"STUDIO-IA-diagnostic", 1, b"none", 1, 1 << 22)
        info = InstanceInfo(1, None, 0, C.pointer(app), 0, None, 0, None)
        result = create(C.byref(info), None, C.byref(instance))
        if result != 0:
            return {
                "status": "BLOCKED",
                "reason": "VULKAN_INSTANCE_FAILED",
                "vk_result": result,
                "devices": [],
            }
        enum = lib.vkEnumeratePhysicalDevices
        enum.argtypes = [C.c_void_p, C.POINTER(C.c_uint32), C.POINTER(C.c_void_p)]
        enum.restype = C.c_int32
        count = C.c_uint32()
        result = enum(instance, C.byref(count), None)
        if result != 0 or count.value > 64:
            return {
                "status": "BLOCKED",
                "reason": "VULKAN_ENUMERATION_FAILED",
                "vk_result": result,
                "devices": [],
            }
        devices = (C.c_void_p * count.value)()
        result = enum(instance, C.byref(count), devices)
        if result != 0:
            return {
                "status": "BLOCKED",
                "reason": "VULKAN_ENUMERATION_FAILED",
                "vk_result": result,
                "devices": [],
            }
        props = lib.vkGetPhysicalDeviceProperties
        props.argtypes = [C.c_void_p, C.POINTER(PhysicalProperties)]
        props.restype = None
        memory = lib.vkGetPhysicalDeviceMemoryProperties
        memory.argtypes = [C.c_void_p, C.POINTER(MemoryProperties)]
        memory.restype = None
        rows = []
        for index, device in enumerate(devices):
            p = PhysicalProperties()
            props(device, C.byref(p))
            m = MemoryProperties()
            memory(device, C.byref(m))
            heaps = [m.memoryHeaps[i] for i in range(min(m.memoryHeapCount, 16))]
            rows.append(
                {
                    "index": index,
                    "name": p.deviceName.decode("utf-8", "replace"),
                    "device_type": p.deviceType,
                    "device_type_name": DEVICE_TYPES.get(p.deviceType, "UNKNOWN"),
                    # DEVICE_LOCAL heaps: dedicated VRAM on a discrete GPU, shared RAM on iGPU.
                    "device_local_bytes": sum(h.size for h in heaps if h.flags & 1),
                    "physical_gpu": p.deviceType in (1, 2),
                    "vendor_id": p.vendorID,
                    "device_id": p.deviceID,
                    "driver_version_raw": p.driverVersion,
                    "vulkan_api_version_raw": p.apiVersion,
                }
            )
        physical = any(row["physical_gpu"] for row in rows)
        return {
            "status": "COMPATIBLE" if physical else "BLOCKED",
            "devices": rows,
            "reason": "INFERENCE_NOT_TESTED" if physical else "NO_PHYSICAL_VULKAN_GPU",
        }
    except (OSError, AttributeError) as exc:
        return {
            "status": "BLOCKED",
            "reason": "VULKAN_UNAVAILABLE",
            "error": str(exc),
            "devices": [],
        }
    finally:
        if instance.value and lib is not None:
            destroy = lib.vkDestroyInstance
            destroy.argtypes = [C.c_void_p, C.c_void_p]
            destroy(instance, None)


def hardware_report() -> dict:
    cpu_info = Path("/proc/cpuinfo")
    text = cpu_info.read_text() if cpu_info.is_file() else ""
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in text.splitlines()
            if line.startswith("model name")
        ),
        platform.processor(),
    )
    flags = next(
        (line.split(":", 1)[1].split() for line in text.splitlines() if line.startswith("flags")),
        [],
    )
    vulkan = vulkan_devices()
    return {
        "schema_version": 1,
        "os_arch": platform.platform(),
        "cpu": cpu,
        "cpu_flags": flags,
        "avx2_observed": "avx2" in flags if flags else None,
        "vulkan": vulkan,
        "inference": "NOT_RUN",
        "real_video_validated": False,
        "gpu_memory_bytes": None,
        "protections_changed": False,
        "drivers_installed": False,
    }

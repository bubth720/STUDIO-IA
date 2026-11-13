"""Reproduce actual CPU cut/AV/motion checks and bounded 30s/3min measurements.

Every output is synthetic. A repeat control is explicitly NON_NEURAL, never RIFE.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

from generate_temporal_fixtures import audio_fixture, motion_fixture

from studio_ia.core import Tools, build_identity, capture
from studio_ia.files import write_json
from studio_ia.interpolate import plan_x2
from studio_ia.media import sha256
from studio_ia.motion import analyze_motion
from studio_ia.scene_detect import scan_scenes
from studio_ia.temporal_audio import audit_audio, compare_audio


def peak_self_memory() -> dict:
    if sys.platform != "win32":
        import resource

        return {
            "self_lifetime_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            * 1024,
            "children_lifetime_peak_rss_bytes": resource.getrusage(
                resource.RUSAGE_CHILDREN
            ).ru_maxrss
            * 1024,
            "method": "getrusage Linux KiB; separate Python and child peaks, not summed",
        }
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(Counters),
        wintypes.DWORD,
    ]
    if not psapi.GetProcessMemoryInfo(
        kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        return {"self_lifetime_peak_rss_bytes": None, "method": "GetProcessMemoryInfo failed"}
    return {
        "self_lifetime_peak_rss_bytes": counters.PeakWorkingSetSize,
        "children_lifetime_peak_rss_bytes": None,
        "method": "Windows GetProcessMemoryInfo; child peak unavailable",
    }


def generate(tools, path, kind, seconds=8):
    filters = {
        "cut": "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable=gte(n\\,100)",
        "flash": "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable=eq(n\\,20)",
        "split": "drawbox=x=0:y=0:w=iw/2:h=ih:color=white:t=fill",
        "fade": "fade=t=in:st=0:d=2",
    }
    color = "white" if kind == "fade" else "black"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            f"color={color}:size=64x48:rate=25:duration={seconds}",
            "-vf",
            filters[kind],
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-crf",
            "0",
            str(path),
        ]
    )
    return path


def child_measure(output: Path, seconds: int) -> None:
    tools = Tools.discover()
    source = generate(tools, output / f"control-{seconds}s.mp4", "split", seconds)
    before = sha256(source)
    started, cpu_started = time.perf_counter(), time.process_time()
    scan, motion = analyze_motion(source, tools)
    elapsed, cpu = time.perf_counter() - started, time.process_time() - cpu_started
    assert len(scan.timeline.frames) == seconds * 25 and scan.timeline.complete
    assert before == sha256(source)
    result = {
        "status": "PASS_CPU_ONLY",
        "seconds_source": seconds,
        "frames": len(scan.timeline.frames),
        "wall_seconds": elapsed,
        "python_cpu_seconds": cpu,
        "effective_analysis_fps": len(scan.timeline.frames) / elapsed,
        "source_unchanged": True,
        "memory": peak_self_memory(),
        "motion_status": motion["status"],
        "vram_bytes": None,
        "neural_executed": False,
    }
    write_json(output / f"measure-{seconds}s.json", result, replace=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--measure-seconds", type=int, choices=[30, 180])
    args = parser.parse_args()
    output = args.output.resolve()
    if args.measure_seconds:
        child_measure(output, args.measure_seconds)
        return
    output.mkdir(parents=True, exist_ok=False)
    tools = Tools.discover()
    cases = []
    scans = {}
    for kind, seconds in (("cut", 8), ("flash", 2), ("split", 2), ("fade", 3), ("pan", 1)):
        source = (
            motion_fixture(tools, output / "pan.mkv", moving=True)
            if kind == "pan"
            else generate(tools, output / f"{kind}.mp4", kind, seconds)
        )
        scan = scan_scenes(source, tools)
        scans[kind] = scan
        detected = {b.frame_index for b in scan.boundaries if b.kind == "CUT_CANDIDATE"}
        truth = {100} if kind == "cut" else set()
        cases.append(
            {
                "fixture": kind,
                "source_sha256": scan.source_sha256,
                "hard_cut_truth": sorted(truth),
                "hard_cut_candidates": sorted(detected),
                "hard_cut_false_positives": len(detected - truth),
                "hard_cut_false_negatives": len(truth - detected),
                "boundaries": [b.__dict__ for b in scan.boundaries],
            }
        )
    assert {b.frame_index for b in scans["cut"].boundaries} == {100}
    assert {b.frame_index for b in scans["flash"].boundaries} == {20, 21}
    write_json(
        output / "cuts.json",
        {
            "status": "PASS_CONTROLLED_CORPUS_WITH_LIMITATIONS",
            "threshold_percent": "10",
            "cases": cases,
            "semantic_generalization": False,
            "note": "False positives on high-texture pans are retained, not hidden.",
        },
        replace=False,
    )
    schedule = plan_x2(scans["cut"], explicit_opt_in=True)
    write_json(output / "x2-plan.json", schedule, replace=False)
    # Exercise transport with repetitions only. This is not an interpolation backend.
    control = output / "NON_NEURAL_REPEAT_CONTROL.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-i",
            str(output / "cut.mp4"),
            "-vf",
            "fps=50",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-crf",
            "0",
            str(control),
        ]
    )
    capture([tools.ffmpeg, "-v", "error", "-xerror", "-i", str(control), "-f", "null", "-"])
    repeated = scan_scenes(control, tools)
    assert repeated.timeline.duration == scans["cut"].timeline.duration == Fraction(8)
    assert len(repeated.frame_hashes) == 400
    assert repeated.frame_hashes[::2] == repeated.frame_hashes[1::2] == scans["cut"].frame_hashes
    write_json(
        output / "repeat-control.json",
        {
            "status": "PASS_NON_NEURAL_REPEAT_TRANSPORT",
            "frames": 400,
            "fps": "50",
            "duration_seconds": "8",
            "all_repeated_hashes_match": True,
            "rife_executed": False,
            "output_sha256": sha256(control),
        },
        replace=False,
    )
    metrics = {}
    for kind in ("static", "pan", "exposure"):
        source = motion_fixture(
            tools, output / f"metric-{kind}.mkv", moving=kind == "pan", flashing=kind == "exposure"
        )
        _, metrics[kind] = analyze_motion(source, tools)
    write_json(output / "temporal-metrics.json", metrics, replace=False)
    audio = []
    for vfr in (False, True):
        source = audio_fixture(tools, output / f"audio-{vfr}.mkv", vfr=vfr)
        target = output / f"audio-copy-{vfr}.mkv"
        before = audit_audio(source, tools)
        capture(
            [
                tools.ffmpeg,
                "-v",
                "error",
                "-n",
                "-copyts",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "0:a",
                "-c",
                "copy",
                "-avoid_negative_ts",
                "disabled",
                str(target),
            ]
        )
        capture(
            [
                tools.ffmpeg,
                "-v",
                "error",
                "-xerror",
                "-i",
                str(target),
                "-map",
                "0:v:0",
                "-map",
                "0:a",
                "-f",
                "null",
                "-",
            ]
        )
        after = audit_audio(target, tools)
        audio.append(
            {
                "vfr": vfr,
                "before": before,
                "after": after,
                "comparison": compare_audio(before, after),
            }
        )
    write_json(
        output / "av-sync-report.json",
        {"status": "PASS_CPU_COPY_CONTROL", "cases": audio},
        replace=False,
    )
    for seconds in (30, 180):
        subprocess.run(
            [sys.executable, __file__, "--output", str(output), "--measure-seconds", str(seconds)],
            check=True,
        )
    write_json(
        output / "resources.json",
        {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_logical_count": os.cpu_count(),
            "application": build_identity(),
            "source_dirty": bool(
                capture(["git", "status", "--porcelain", "--untracked-files=no"]).strip()
            ),
            "ffmpeg_version": capture([tools.ffmpeg, "-version"]).splitlines()[0],
            "measurements": [
                json.loads((output / f"measure-{s}s.json").read_text()) for s in (30, 180)
            ],
            "gpu_tests": "BLOCKED_NO_QUALIFIED_GPU",
            "m005_status": "PREPARATION",
        },
        replace=False,
    )
    print(json.dumps({"status": "PASS_CPU_ONLY", "output": str(output), "m005_accepted": False}))


if __name__ == "__main__":
    main()

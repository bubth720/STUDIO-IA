"""Explicit local NCNN path. A detected executable never grants GPU qualification."""

import os
import shutil
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from studio_ia.content_profiles import check_model, describe, profile_for_model
from studio_ia.core import (
    Cancellation,
    StudioError,
    Tools,
    build_identity,
    execute,
    external_process_env,
    process_options,
    state_dir,
)
from studio_ia.files import publish_no_replace, write_json
from studio_ia.hardware import hardware_report
from studio_ia.media import analyze, sha256
from studio_ia.models import BACKEND, ModelRecord, inspect, native_scale
from studio_ia.pipeline import Request, build_plan, verify_output
from studio_ia.plans_v2 import PlanV2, compare_timing, frame_table, load_plan

_ACTIVE = threading.Lock()
TRUSTED_BINARIES = frozenset(
    [
        "22c2296a39b40cc43ac92615c827ab6d4b60b7142e8cee59f718e3f8e2cdbda9",
        "07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c",
    ]
)


def probe(binary: Path) -> dict:
    entered = binary.expanduser()
    if entered.is_symlink() or not entered.is_file():
        raise StudioError("Binaire NCNN absent ou lié ; choisir un exécutable local fiable.")
    binary = entered.resolve(strict=True)
    binary_hash = sha256(binary)
    if binary_hash not in TRUSTED_BINARIES:
        raise StudioError(
            "Binaire NCNN non épinglé : aucune commande arbitraire importée exécutée."
        )
    try:
        result = subprocess.run(
            [str(binary), "-h"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            env=external_process_env(),
            **process_options(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StudioError("Aide NCNN inexécutable ou délai dépassé.") from exc
    help_text = result.stdout + result.stderr
    if len(help_text) > 65536 or not all(
        flag in help_text
        for flag in (
            "realesrgan-ncnn-vulkan",
            "-i input-path",
            "-o output-path",
            "-m model-path",
            "-n model-name",
            "-s scale",
            "-j load:proc:save",
        )
    ):
        raise StudioError("CLI NCNN non reconnue ; aucun flag d'une autre version n'est supposé.")
    return {
        "backend": BACKEND,
        "path": str(binary),
        "sha256": sha256(binary),
        "version_source": "CLI_CONTRACT_V0_2_0_NOT_SELF_REPORTED_VERSION",
        "help": help_text,
        "help_exit_code": result.returncode,
        "status": "DETECTED",
        "real_video_validated": False,
    }


@contextmanager
def intensive_job():
    if not _ACTIVE.acquire(blocking=False):
        raise StudioError("Une tâche neuronale est déjà active.")
    lock = state_dir() / "neural-active.lock"
    owned = False
    try:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise StudioError(
                "Verrou neuronal présent ; vérifier la tâche ou l'arrêt précédent."
            ) from exc
        owned = True
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        try:
            if owned:
                try:
                    lock.unlink(missing_ok=True)
                except OSError:
                    pass  # Leftover lock blocks the next job; never invalidate a committed export.
        finally:
            _ACTIVE.release()


def image_command(
    engine: dict, model: ModelRecord, root: Path, source: Path, output: Path, *, tile: int, gpu: int
) -> list[str]:
    return [
        engine["path"],
        "-i",
        str(source),
        "-o",
        str(output),
        "-s",
        str(native_scale(model.manifest)),
        "-t",
        str(tile),
        "-m",
        str(root),
        "-n",
        model.manifest["name"],
        "-g",
        str(gpu),
        "-j",
        "1:1:1",
        "-f",
        "png",
    ]


def qualify(
    engine: dict,
    model: ModelRecord,
    tools: Tools,
    directory: Path,
    cancel: Cancellation,
    *,
    tile: int = 64,
    _owns_lock: bool = False,
) -> dict:
    if not _owns_lock:
        with intensive_job():
            return qualify(engine, model, tools, directory, cancel, tile=tile, _owns_lock=True)
    cancel.check()
    model.revalidate()
    if sha256(Path(engine["path"]), cancel) != engine["sha256"]:
        raise StudioError("Binaire modifié après le plan.")
    hardware = hardware_report()
    report = {
        "status": "BLOCKED",
        "engine_sha256": engine["sha256"],
        "model_identity": model.identity,
        "hardware": hardware,
        "real_video_validated": False,
        "inference": "NOT_RUN",
    }
    if hardware["vulkan"]["status"] != "COMPATIBLE":
        report["reason"] = hardware["vulkan"]["reason"]
        return report
    gpu = next(d["index"] for d in hardware["vulkan"]["devices"] if d["physical_gpu"])
    directory.mkdir(parents=True, exist_ok=False)
    log = directory / "inference.log"
    model.snapshot(directory / "models")
    source, output = directory / "tiny-source.png", directory / "tiny-output.png"
    execute(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=32x32:rate=1",
            "-frames:v",
            "1",
            "-threads",
            "1",
            str(source),
        ],
        log,
        cancel,
        timeout=30,
    )
    started = time.monotonic()
    execute(
        image_command(engine, model, directory / "models", source, output, tile=tile, gpu=gpu),
        log,
        cancel,
        timeout=120,
    )
    info = analyze(output, tools)
    expected = 32 * native_scale(model.manifest)
    if (info.video["width"], info.video["height"]) != (expected, expected):
        raise StudioError("Inférence courte : dimensions incorrectes.")
    execute(
        [tools.ffmpeg, "-v", "error", "-xerror", "-i", str(output), "-f", "null", "-"],
        log,
        cancel,
        timeout=30,
    )
    model.revalidate()
    return {
        **report,
        "status": "PASS_SHORT_INFERENCE",
        "inference": "PASS",
        "gpu_index": gpu,
        "elapsed_seconds": time.monotonic() - started,
        "memory_bytes": None,
        "memory_limitation": "Peak VRAM/RSS not instrumented; no universal memory guarantee",
        "output_sha256": sha256(output),
        "source_sha256": sha256(source),
    }


def build_neural_plan(
    request: Request,
    tools: Tools,
    model: ModelRecord,
    binary: Path,
    *,
    tile: int = 64,
    max_frames: int = 10000,
    workspace_budget: int = 2 * 1024**3,
    content_profile: str | None = None,
) -> PlanV2:
    if type(tile) is not int or tile not in (32, 64, 128, 256, 512):
        raise StudioError("Tuile NCNN invalide.")
    if type(workspace_budget) is not int or not 64 * 1024**2 <= workspace_budget <= 16 * 1024**3:
        raise StudioError("Budget disque invalide.")
    model.revalidate()
    profile = profile_for_model(model.manifest) if content_profile is None else content_profile
    check_model(profile, model.manifest)
    if (
        request.scale != 2
        or request.denoise != "off"
        or request.deband != "off"
        or (request.brightness, request.contrast, request.saturation) != (0, 1, 1)
    ):
        raise StudioError(
            "NN initial : sortie ×2, débruitage et anti-banding désactivés ; "
            "couleurs neutres obligatoires."
        )
    cpu = build_plan(request, tools)
    if Path(cpu.request.destination).suffix.lower() not in (".mp4", ".mkv"):
        raise StudioError("NN : export MP4 ou MKV requis.")
    if any(
        cpu.media.video.get(k) != v
        for k, v in (
            ("color_space", "bt709"),
            ("color_primaries", "bt709"),
            ("color_transfer", "bt709"),
            ("color_range", "tv"),
        )
    ):
        raise StudioError("NN initial : source SDR BT.709 limitée explicitement déclarée requise.")
    timing = frame_table(Path(cpu.media.path), tools, max_frames=max_frames)
    native = native_scale(model.manifest)
    source_pixels = cpu.media.video["width"] * cpu.media.video["height"]
    # Extracted frame + native NCNN frame (×4 for x4plus is 16× the source pixels).
    pixels = source_pixels + source_pixels * native * native
    estimate = len(timing["frames"]) * (pixels * 4 + 16384) + 64 * 1024**2
    if (
        estimate > workspace_budget
        or estimate > shutil.disk_usage(Path(cpu.request.destination).parent).free
    ):
        raise StudioError("Budget/espace insuffisant pour les frames et la sortie.")
    cpu.filters = []  # NCNN replaces the CPU upscale; never append Lanczos to neural SR.
    cpu.warnings = [
        "Neuronal expérimental : détails plausibles, identité historique non garantie.",
        "CFR SDR BT.709 uniquement ; VFR/HDR non qualifiés.",
    ]
    if native != request.scale:
        cpu.warnings.append(
            f"Modèle natif ×{native} : réduction Lanczos vers ×{request.scale} après inférence."
        )
    return load_plan(
        {
            "schema_version": 2,
            "kind": "neural-ncnn",
            "content_profile": describe(profile),
            "cpu_plan": cpu.to_dict(),
            "source_sha256": sha256(Path(cpu.media.path)),
            "engine": probe(binary),
            "model": {"root": model.root, "manifest": model.manifest, "identity": model.identity},
            "timing": timing,
            "budgets": {
                "tile": tile,
                "max_frames": max_frames,
                "workspace_bytes": workspace_budget,
                "estimated_bytes": estimate,
                "gpu_memory_bytes": None,
                "host_memory_limit_enforced": False,
            },
            "policies": {
                "pts": "EXACT_CFR_NO_RESAMPLE",
                "audio": "MAP_ALL_SOURCE_STREAMS",
                "color": "BT709_TV_TO_RGB24_TO_BT709_TV",
                "preprocessing": "NONE",
                "scaling": {
                    "native_scale": native,
                    "output_scale": 2,
                    "post_inference": "NONE" if native == 2 else "LANCZOS_TO_OUTPUT",
                },
                "output": "ATOMIC_NO_CLOBBER",
                "network": "NO_DOWNLOAD_OR_REMOTE_PROTOCOL",
            },
        }
    )


def run_neural_plan(
    plan: PlanV2,
    tools: Tools,
    job_dir: Path,
    cancel: Cancellation | None = None,
    on_progress=None,
    on_stage=None,
) -> dict:
    cancel = cancel or Cancellation()
    data, cpu = plan.data, plan.cpu_plan()
    if data["kind"] != "neural-ncnn":
        raise StudioError("Plan neuronal requis.")
    model = inspect(Path(data["model"]["root"]), data["model"]["manifest"])
    if (
        model.identity != data["model"]["identity"]
        or sha256(Path(cpu.media.path), cancel) != data["source_sha256"]
    ):
        raise StudioError("Source ou modèle modifié depuis le plan.")
    # Rebuild and compare all policy/timing/resource fields, not just a caller's success label.
    rebuilt = build_neural_plan(
        cpu.request,
        tools,
        model,
        Path(data["engine"]["path"]),
        tile=data["budgets"]["tile"],
        max_frames=data["budgets"]["max_frames"],
        workspace_budget=data["budgets"]["workspace_bytes"],
        content_profile=data.get("content_profile", {}).get("id"),
    )
    if rebuilt.identity != plan.identity:
        raise StudioError("Plan/binaire/média modifié ; recréer le plan explicitement.")
    job_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(job_dir / "plan.json", data)
    log = job_dir / "pipeline.log"
    with intensive_job():
        receipt = qualify(
            data["engine"],
            model,
            tools,
            job_dir / "qualification",
            cancel,
            tile=data["budgets"]["tile"],
            _owns_lock=True,
        )
        write_json(job_dir / "qualification.json", receipt)
        if receipt["status"] != "PASS_SHORT_INFERENCE":
            raise StudioError(
                "BLOCKED : inférence courte sur GPU physique non validée ; utiliser CPU classique."
            )
        destination = Path(cpu.request.destination)
        owned = Path(tempfile.mkdtemp(prefix=".studio-ia-nn-", dir=destination.parent))
        started = time.monotonic()
        committed = False
        result = None
        try:
            inputs, outputs = owned / "input", owned / "output"
            inputs.mkdir()
            outputs.mkdir()
            model.snapshot(owned / "models")
            if on_stage:
                on_stage("RUNNING")
            execute(
                [
                    tools.ffmpeg,
                    "-v",
                    "error",
                    "-n",
                    "-threads",
                    "2",
                    "-filter_threads",
                    "1",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    cpu.media.path,
                    "-map",
                    "0:v:0",
                    "-vf",
                    "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
                    "-fps_mode",
                    "passthrough",
                    "-threads",
                    "1",
                    str(inputs / "%08d.png"),
                ],
                log,
                cancel,
            )
            frames = sorted(inputs.glob("*.png"))
            native = data["policies"]["scaling"]["native_scale"]
            native_size = (
                cpu.media.video["width"] * native,
                cpu.media.video["height"] * native,
            )
            if native == 2 and native_size != (cpu.width, cpu.height):
                raise StudioError("Plan ×2 natif incohérent avec la taille de sortie.")
            if len(frames) != len(data["timing"]["frames"]):
                raise StudioError("Extraction : nombre de frames incorrect.")
            ledger = []
            for index, frame in enumerate(frames):
                cancel.check()
                target = outputs / frame.name
                if sha256(Path(data["engine"]["path"]), cancel) != data["engine"]["sha256"]:
                    raise StudioError("Binaire remplacé pendant le traitement.")
                execute(
                    image_command(
                        data["engine"],
                        model,
                        owned / "models",
                        frame,
                        target,
                        tile=data["budgets"]["tile"],
                        gpu=receipt["gpu_index"],
                    ),
                    log,
                    cancel,
                    timeout=120,
                )
                image = analyze(target, tools)
                if (image.video["width"], image.video["height"]) != native_size:
                    raise StudioError("Frame neuronale invalide.")
                ledger.append(
                    {
                        **data["timing"]["frames"][index],
                        "input_sha256": sha256(frame),
                        "output_sha256": sha256(target),
                    }
                )
                if on_progress:
                    on_progress((index + 1) / len(frames) * 0.9)
            write_json(
                job_dir / "frames.json",
                {"time_base": data["timing"]["time_base"], "frames": ledger},
            )
            container = Path(cpu.request.destination).suffix.lower()
            temporary = owned / ("export" + container)
            timebase = Fraction(data["timing"]["time_base"])
            origin = data["timing"]["frames"][0]["pts"] * timebase
            args = [
                tools.ffmpeg,
                "-v",
                "error",
                "-n",
                "-threads",
                "2",
                "-filter_threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
            ]
            if origin:
                # Keep source audio/video timestamps; shift inferred frames to the exact
                # source video origin. compare_timing() refuses any residual drift.
                args += ["-copyts"]
            args += ["-framerate", data["timing"]["frame_rate"]]
            if origin:
                args += ["-itsoffset", f"{float(origin):.6f}"]  # microseconds
            args += [
                "-i",
                str(outputs / "%08d.png"),
                "-i",
                cpu.media.path,
                "-map",
                "0:v:0",
                "-map",
                "1:a?",
                "-map_metadata",
                "1",
                "-map_chapters",
                "1",
                "-vf",
                ("" if native == 2 else f"scale={cpu.width}:{cpu.height}:flags=lanczos,")
                + "scale=in_range=pc:out_color_matrix=bt709:out_range=tv,format=yuv420p",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                "-crf",
                str(cpu.request.crf),
                "-preset",
                "medium",
                "-x264-params",
                "colorprim=bt709:transfer=bt709:colormatrix=bt709",
                "-enc_time_base",
                str(timebase),
                "-fps_mode",
                "passthrough",
                "-c:a",
                cpu.audio_policy,
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-color_range",
                "tv",
                "-avoid_negative_ts",
                "disabled",
            ]
            if container == ".mp4":
                args += [
                    "-video_track_timescale",
                    str(timebase.denominator),
                    "-movflags",
                    "+faststart",
                ]
            if cpu.audio_policy == "aac":
                args += ["-b:a", "192k"]
            args.append(str(temporary))
            write_json(job_dir / "assembly-command.json", args)
            execute(args, log, cancel)
            if on_stage:
                on_stage("VERIFYING")
            verification = verify_output(cpu, temporary, tools, cancel, log)
            compare_timing(
                data["timing"],
                frame_table(temporary, tools, max_frames=data["budgets"]["max_frames"]),
            )
            if sha256(Path(cpu.media.path), cancel) != data["source_sha256"]:
                raise StudioError("La source a changé ; aucune publication.")
            model.revalidate()
            result = {
                "schema_version": 2,
                "status": "VERIFIED_NOT_COMMITTED",
                "plan": cpu.to_dict(),
                "neural_plan": data,
                "application": build_identity(),
                "source_sha256": data["source_sha256"],
                "output_sha256": sha256(temporary, cancel),
                "elapsed_seconds": time.monotonic() - started,
                "qualification": receipt,
                "warnings": [],
                **verification,
            }
            result["assertions"].update(exact_pts_and_frame_count=True, source_unchanged=True)
            write_json(job_dir / "verification.json", result)
            with cancel.lock:
                cancel.check()
                result["finalization"] = publish_no_replace(temporary, destination)
                cancel.committed = committed = True
            result["status"] = "PASS"
            try:
                write_json(job_dir / "result.json", result)
            except OSError:
                result["warnings"].append("Export validé ; rapport local non écrit.")
            return result
        finally:
            try:
                shutil.rmtree(owned)
            except OSError:
                if not committed:
                    raise StudioError(
                        "Nettoyage incomplet du job neuronal ; aucun succès annoncé."
                    ) from None
                if result is not None:
                    result["warnings"].append("Export validé ; nettoyage temporaire incomplet.")


def preview_neural(
    plan: PlanV2,
    tools: Tools,
    directory: Path,
    *,
    seconds: float = 0,
    duration: float = 1,
    cancel: Cancellation | None = None,
) -> dict:
    import math

    if (
        not math.isfinite(seconds)
        or not math.isfinite(duration)
        or not 0 <= seconds
        or not 0 < duration <= 3
    ):
        raise StudioError("Aperçu : instant positif et durée de 0 à 3 s requis.")
    cancel = cancel or Cancellation()
    directory.mkdir(parents=True, exist_ok=False)
    # Slice only after admission; never supply prerecorded thumbnails for a blocked engine.
    data = plan.data
    model = inspect(Path(data["model"]["root"]), data["model"]["manifest"])
    if (
        sha256(Path(plan.request.source), cancel) != data["source_sha256"]
        or model.identity != data["model"]["identity"]
        or sha256(Path(data["engine"]["path"]), cancel) != data["engine"]["sha256"]
    ):
        raise StudioError("Source/modèle/moteur modifié avant aperçu.")
    sample = next(
        (
            frame
            for frame in data["timing"]["frames"]
            if Fraction(frame["pts"]) * Fraction(data["timing"]["time_base"])
            >= Fraction(str(seconds))
        ),
        None,
    )
    if sample is None:
        raise StudioError("Instant d'aperçu hors vidéo.")
    actual_sample = Fraction(sample["pts"]) * Fraction(data["timing"]["time_base"])
    receipt = qualify(data["engine"], model, tools, directory / "qualification", cancel)
    write_json(directory / "qualification.json", receipt)
    if receipt["status"] != "PASS_SHORT_INFERENCE":
        raise StudioError("BLOCKED : aperçu neuronal sans GPU qualifié.")
    segment = directory / "source-segment.mp4"
    execute(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-i",
            plan.request.source,
            "-ss",
            str(float(actual_sample)),
            "-t",
            str(duration),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-crf",
            "0",
            "-x264-params",
            "colorprim=bt709:transfer=bt709:colormatrix=bt709",
            "-c:a",
            "aac",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-color_range",
            "tv",
            str(segment),
        ],
        directory / "preview.log",
        cancel,
    )
    request = replace(plan.request, source=str(segment), destination=str(directory / "neural.mp4"))
    sliced = build_neural_plan(
        request,
        tools,
        model,
        Path(data["engine"]["path"]),
        tile=data["budgets"]["tile"],
        content_profile=data.get("content_profile", {}).get("id"),
    )
    result = run_neural_plan(sliced, tools, directory / "job", cancel)
    cpu = build_plan(replace(request, destination=str(directory / "cpu.mp4")), tools)
    from studio_ia.pipeline import run_plan
    from studio_ia.preview import snapshot

    run_plan(cpu, tools, directory / "cpu-job", cancel)
    for name in ("source-segment", "cpu", "neural"):
        snapshot(directory / f"{name}.mp4", 0, directory / f"{name}.png", tools)
    if sha256(Path(plan.request.source), cancel) != data["source_sha256"]:
        raise StudioError("Source modifiée pendant l'aperçu.")
    return {
        "status": result["status"],
        "scope": "SHORT_SEGMENT_ONLY_NOT_FULL_VIDEO_QUALIFICATION",
        "requested_source_seconds": seconds,
        "actual_sample_source_pts": sample["pts"],
        "actual_sample_source_time_base": data["timing"]["time_base"],
        "actual_sample_source_seconds_rational": str(actual_sample),
        "duration": duration,
        "plan_identity": plan.identity,
        "segment_plan_identity": sliced.identity,
        "settings_changed": False,
        "sample_policy": "FIRST_DECODED_SEGMENT_FRAME_COMMON_TO_ALL_THREE",
        "output_directory": str(directory),
        "frames": {
            "source": str(directory / "source-segment.png"),
            "cpu": str(directory / "cpu.png"),
            "neural": str(directory / "neural.png"),
        },
        "source_sha256": sha256(Path(plan.request.source)),
    }

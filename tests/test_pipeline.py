import json
import threading
from dataclasses import replace

import pytest
from generate_fixtures import fixture

from studio_ia.core import Cancellation, Cancelled, StudioError, capabilities
from studio_ia.media import analyze, sha256
from studio_ia.pipeline import Request, build_plan, run_plan

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("denoise,scale", [("off", 1), ("light", 2), ("moderate", 1)])
def test_real_export(source, tmp_path, tools, denoise, scale):
    original = sha256(source)
    dest = tmp_path / "résultat ; $ sans shell.mp4"
    plan = build_plan(Request(str(source), str(dest), denoise=denoise, scale=scale), tools)
    result = run_plan(plan, tools, tmp_path / "job")
    assert all(result["assertions"].values())
    assert sha256(source) == original
    output = analyze(dest, tools)
    assert (output.video["width"], output.video["height"]) == (320 * scale, 180 * scale)
    assert len(output.audio) == 1
    assert not list(tmp_path.glob(".studio-ia-*"))


@pytest.mark.parametrize("size,audio", [("640x360", False), ("360x640", True)])
def test_silent_and_portrait(tmp_path, tools, size, audio):
    source = fixture(tools, tmp_path / "source.mp4", size=size, duration=5, audio=audio)
    dest = tmp_path / "out.mkv"
    result = run_plan(
        build_plan(Request(str(source), str(dest), scale=0.5), tools), tools, tmp_path / "job"
    )
    assert all(result["assertions"].values())
    info = analyze(dest, tools)
    assert len(info.audio) == int(audio)
    assert (
        abs(
            info.video["width"] / info.video["height"]
            - int(size.split("x")[0]) / int(size.split("x")[1])
        )
        < 0.01
    )


def test_color_controls(source, tmp_path, tools):
    plan = build_plan(
        Request(
            str(source),
            str(tmp_path / "color.mp4"),
            brightness=0.02,
            contrast=1.02,
            saturation=1.01,
        ),
        tools,
    )
    assert "eq=" in ",".join(plan.filters)
    assert run_plan(plan, tools, tmp_path / "job")["status"] == "PASS"


@pytest.mark.parametrize(
    "field,value",
    [
        ("scale", 0),
        ("scale", float("nan")),
        ("brightness", 2),
        ("contrast", -1),
        ("crf", 31),
        ("denoise", "injected"),
    ],
)
def test_invalid_parameters(source, tmp_path, tools, field, value):
    request = replace(Request(str(source), str(tmp_path / "out.mp4")), **{field: value})
    with pytest.raises(StudioError):
        build_plan(request, tools)


def test_refuse_existing_or_source(source, tmp_path, tools):
    before = sha256(source)
    with pytest.raises(StudioError):
        build_plan(Request(str(source), str(source)), tools)
    existing = tmp_path / "existing.mp4"
    existing.write_bytes(b"keep me")
    with pytest.raises(StudioError):
        build_plan(Request(str(source), str(existing)), tools)
    assert existing.read_bytes() == b"keep me" and sha256(source) == before


def test_race_no_clobber(source, tmp_path, tools):
    dest = tmp_path / "raced.mp4"
    plan = build_plan(Request(str(source), str(dest)), tools)

    def stage(state):
        if state == "VERIFYING":
            dest.write_bytes(b"another application created this")

    with pytest.raises(StudioError, match="finalisation"):
        run_plan(plan, tools, tmp_path / "job", on_stage=stage)
    assert dest.read_bytes() == b"another application created this"


def test_corrupt_missing_and_bad_destination(source, tmp_path, tools):
    with pytest.raises((StudioError, OSError)):
        analyze(tmp_path / "missing.mp4", tools)
    corrupt = tmp_path / "F04.mp4"
    corrupt.write_bytes(source.read_bytes()[:100])
    with pytest.raises(StudioError):
        analyze(corrupt, tools)
    with pytest.raises(StudioError):
        build_plan(Request(str(source), str(tmp_path / "nonexistent" / "out.mp4")), tools)


def test_missing_encoder_and_filter(source, tmp_path, tools):
    caps = capabilities(tools)
    for kind, missing in (("encoders", "libx264"), ("filters", "hqdn3d")):
        incomplete = {**caps, kind: [x for x in caps[kind] if x != missing]}
        with pytest.raises(StudioError, match="absent"):
            build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools, incomplete)


def test_cancel_real_process(source, tmp_path, tools):
    dest = tmp_path / "cancelled.mp4"
    plan = build_plan(Request(str(source), str(dest), scale=4), tools)
    cancel = Cancellation()
    timer = threading.Timer(0.2, cancel.request)
    timer.start()
    with pytest.raises(Cancelled):
        run_plan(plan, tools, tmp_path / "job", cancel)
    timer.join()
    assert not dest.exists() and not list(tmp_path.glob(".studio-ia-*"))
    assert (tmp_path / "job" / "pipeline.log").exists()


def test_source_change_rejects_export(source, tmp_path, tools):
    copied = tmp_path / "source.mp4"
    copied.write_bytes(source.read_bytes())
    dest = tmp_path / "out.mp4"

    def stage(state):
        if state == "VERIFYING":
            with copied.open("ab") as file:
                file.write(b"external edit")

    with pytest.raises(StudioError, match="source a changé"):
        run_plan(
            build_plan(Request(str(copied), str(dest)), tools),
            tools,
            tmp_path / "job",
            on_stage=stage,
        )
    assert not dest.exists()


def test_disk_exhaustion_and_write_failure(source, tmp_path, tools, monkeypatch):
    import studio_ia.pipeline as pipeline

    disk = pipeline.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(pipeline.shutil, "disk_usage", lambda _: disk._replace(free=0))
    with pytest.raises(StudioError, match="disque"):
        build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools)
    monkeypatch.undo()
    plan = build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools)

    def disk_full(*_):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(pipeline, "publish_no_replace", disk_full)
    with pytest.raises(StudioError, match="Stockage"):
        run_plan(plan, tools, tmp_path / "job")
    assert not (tmp_path / "out.mp4").exists()


def test_failed_full_decode_never_promotes(source, tmp_path, tools, monkeypatch):
    import studio_ia.pipeline as pipeline

    original_execute = pipeline.execute

    def fail_verify(args, *positional, **kwargs):
        if "-xerror" in args:
            raise StudioError("décodage complet échoué")
        return original_execute(args, *positional, **kwargs)

    monkeypatch.setattr(pipeline, "execute", fail_verify)
    dest = tmp_path / "out.mp4"
    with pytest.raises(StudioError, match="décodage"):
        run_plan(build_plan(Request(str(source), str(dest)), tools), tools, tmp_path / "job")
    assert not dest.exists()


def test_plan_is_serializable(source, tmp_path, tools):
    plan = build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools)
    assert json.loads(json.dumps(plan.to_dict()))["request"]["schema_version"] == 1

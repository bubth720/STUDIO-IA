"""realesrgan-x4plus catalogue contract (LOT 03).

Synthetic bytes and an explicitly NON-NEURAL FFmpeg test double only: these tests
check validation, ×4 → ×2 transport, PTS and audio. They never qualify Real-ESRGAN,
a GPU or image quality.
"""

import copy
from pathlib import Path

import pytest
from test_models import make_model
from test_neural_failures import neural_transport  # noqa: F401  (fixture)

from studio_ia import neural
from studio_ia.core import StudioError
from studio_ia.media import analyze, sha256
from studio_ia.models import CATALOG, inspect, native_scale
from studio_ia.plans_v2 import compare_timing, frame_table


@pytest.fixture
def model(tmp_path):
    # Overrides the animation fixture for neural_transport in this module only.
    return make_model(tmp_path, "realesrgan-x4plus")


def test_x4plus_manifest_is_accepted_with_native_scale_4(model):
    root, manifest = model
    record = inspect(root, manifest)
    assert native_scale(record.manifest) == 4
    assert {f["path"] for f in record.manifest["files"]} == {
        "realesrgan-x4plus.param",
        "realesrgan-x4plus.bin",
    }


@pytest.mark.parametrize("scale", [2, 3, 4.0, "4"])
def test_x4plus_refuses_any_other_declared_scale(model, scale):
    root, manifest = model
    manifest["scale"] = scale
    with pytest.raises(StudioError, match="Échelle|mal typé"):
        inspect(root, manifest)


def test_model_names_and_file_names_cannot_be_mixed(model):
    root, manifest = model
    mixed = copy.deepcopy(manifest)
    mixed["name"] = "realesr-animevideov3"
    mixed["scale"] = 2
    with pytest.raises(StudioError, match="Noms NCNN exacts"):
        inspect(root, mixed)
    unknown = copy.deepcopy(manifest)
    unknown["name"] = "realesr-general-x4v3"
    with pytest.raises(StudioError, match="non pris en charge"):
        inspect(root, unknown)


def test_catalogue_is_closed_and_matches_official_cli_names():
    assert set(CATALOG) == {"realesr-animevideov3", "realesrgan-x4plus"}
    assert CATALOG["realesr-animevideov3"]["param"] == "realesr-animevideov3-x2.param"
    assert CATALOG["realesrgan-x4plus"]["weights"] == "realesrgan-x4plus.bin"


def test_real_image_command_passes_native_scale_to_ncnn(model, tmp_path):
    root, manifest = model
    record = inspect(root, manifest)
    command = neural.image_command(
        {"path": "/pinned/realesrgan-ncnn-vulkan"},
        record,
        root,
        tmp_path / "in.png",
        tmp_path / "out.png",
        tile=64,
        gpu=0,
    )
    assert command[command.index("-s") + 1] == "4"
    assert command[command.index("-n") + 1] == "realesrgan-x4plus"


def test_x4plus_plan_records_lanczos_reduction_to_x2(request):
    plan, *_ = request.getfixturevalue("neural_transport")
    scaling = plan.data["policies"]["scaling"]
    assert scaling == {
        "native_scale": 4,
        "output_scale": 2,
        "post_inference": "LANCZOS_TO_OUTPUT",
    }
    assert any("×4" in w and "Lanczos" in w for w in plan.cpu_plan().warnings)
    # Budget accounts for 16× native frames, larger than the ×2 animation contract.
    source_pixels = 64 * 48
    frames = len(plan.data["timing"]["frames"])
    assert plan.data["budgets"]["estimated_bytes"] >= frames * source_pixels * 17 * 4


def test_x4plus_transport_double_outputs_x2_with_exact_pts_and_audio(request, tools, tmp_path):
    plan, source, *_ = request.getfixturevalue("neural_transport")
    before = sha256(source)
    result = neural.run_neural_plan(plan, tools, tmp_path / "x4-job")
    assert result["qualification"]["test_double"] is True
    assert result["status"] == "PASS" and all(result["assertions"].values())
    output = Path(plan.request.destination)
    info = analyze(output, tools)
    assert (info.video["width"], info.video["height"]) == (128, 96)
    assert len(result["ffprobe_after"]["streams"]) == 3
    compare_timing(frame_table(source, tools), frame_table(output, tools))
    assert sha256(source) == before
    assert not list(tmp_path.glob(".studio-ia-nn-*"))


def test_x4plus_refuses_frames_that_are_not_native_x4(request, tools, tmp_path, monkeypatch):
    plan, *_ = request.getfixturevalue("neural_transport")
    monkeypatch.setattr(
        neural,
        "image_command",
        lambda engine, record, root, src, out, **k: [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-i",
            str(src),
            "-vf",
            "scale=iw*2:ih*2:flags=neighbor",
            str(out),
        ],
    )
    with pytest.raises(StudioError, match="Frame neuronale invalide"):
        neural.run_neural_plan(plan, tools, tmp_path / "wrong-scale-job")
    assert not Path(plan.request.destination).exists()

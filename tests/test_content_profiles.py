"""LOT 03 step 3: « Animation » / « Vidéos réelles » content profiles.

Synthetic models and an explicitly NON-NEURAL FFmpeg double only (see
test_neural_failures). These tests check selection, persistence, plan/job/report
traceability and refusals; they never qualify Real-ESRGAN or a GPU.
"""

import json
from pathlib import Path

import pytest
from test_models import (
    make_model,
    model,  # noqa: F401  (fixture)
)
from test_neural_failures import neural_transport  # noqa: F401  (fixture)

from studio_ia import content_profiles, neural
from studio_ia.core import StudioError
from studio_ia.models import CATALOG, inspect
from studio_ia.pipeline import Request


def test_each_profile_is_bound_to_one_catalogued_model():
    assert set(content_profiles.PROFILES) == {"animation", "live-action"}
    models = [p["model"] for p in content_profiles.PROFILES.values()]
    assert sorted(models) == sorted(CATALOG)
    for profile in content_profiles.PROFILES.values():
        assert Path(profile["manifest"]).name.startswith(profile["model"])
        assert (Path(__file__).parents[1] / profile["manifest"]).is_file()


def test_unknown_profile_is_refused():
    with pytest.raises(StudioError, match="inconnu"):
        content_profiles.validate_profile("cinéma")
    with pytest.raises(StudioError, match="inconnu"):
        content_profiles.save_settings(Path("."), content_profile="cinéma")


def test_mismatch_gives_a_concrete_resolution_message():
    message = content_profiles.resolution("live-action", found="realesr-animevideov3")
    assert "realesr-animevideov3" in message and "Vidéos réelles" in message
    assert "manifests/realesrgan-x4plus.json" in message
    assert "realesrgan-x4plus.param" in message and "GPU Vulkan physique" in message
    with pytest.raises(StudioError, match="ne convient pas"):
        content_profiles.check_model("live-action", {"name": "realesr-animevideov3"})


def test_settings_round_trip_unicode_root_and_corruption_fallback(tmp_path):
    root = tmp_path / "état utilisateur 日本語"
    assert content_profiles.load_settings(root)["content_profile"] == "animation"
    content_profiles.save_settings(root, content_profile="live-action")
    assert content_profiles.load_settings(root)["content_profile"] == "live-action"
    (root / content_profiles.SETTINGS_NAME).write_text("{corrompu", encoding="utf-8")
    assert content_profiles.load_settings(root)["content_profile"] == "animation"
    (root / content_profiles.SETTINGS_NAME).write_text(
        json.dumps({"schema_version": 1, "content_profile": "inconnu"}), encoding="utf-8"
    )
    assert content_profiles.load_settings(root)["content_profile"] == "animation"


def test_plan_records_profile_and_refuses_incompatible_one(request, tools, tmp_path):
    plan, source, root, manifest, binary = request.getfixturevalue("neural_transport")
    assert plan.data["content_profile"] == {
        "id": "animation",
        "label": "Animation",
        "model": "realesr-animevideov3",
    }
    record = inspect(root, manifest)
    with pytest.raises(StudioError, match="ne convient pas"):
        neural.build_neural_plan(
            Request(str(source), str(tmp_path / "x.mp4"), scale=2, denoise="off"),
            tools,
            record,
            binary,
            content_profile="live-action",
        )


def test_live_action_profile_is_derived_from_x4plus(tmp_path):
    root, manifest = make_model(tmp_path, "realesrgan-x4plus")
    record = inspect(root, manifest)
    assert content_profiles.profile_for_model(record.manifest) == "live-action"
    content_profiles.check_model("live-action", record.manifest)


def test_profile_reaches_job_result_and_report(request, tools, tmp_path):
    plan, *_ = request.getfixturevalue("neural_transport")
    result = neural.run_neural_plan(plan, tools, tmp_path / "job")
    assert result["neural_plan"]["content_profile"]["id"] == "animation"
    saved = json.loads((tmp_path / "job" / "result.json").read_text(encoding="utf-8"))
    assert saved["neural_plan"]["content_profile"]["label"] == "Animation"
    assert result["qualification"]["test_double"] is True


def test_tampered_profile_in_frozen_plan_is_refused(request, tools, tmp_path):
    from studio_ia.plans_v2 import load_plan

    plan, *_ = request.getfixturevalue("neural_transport")
    data = plan.to_dict()
    data["content_profile"] = {"id": "live-action", "label": "x", "model": "x"}
    with pytest.raises(StudioError):
        neural.run_neural_plan(load_plan(data), tools, tmp_path / "tampered")


@pytest.mark.gui
def test_ui_profile_is_exclusive_persistent_and_editable_before_launch(tmp_path, qapp):
    from PySide6.QtTest import QTest

    from studio_ia.ui import Window

    state = tmp_path / "ui état"

    def open_window():
        window = Window(state)
        window.show()
        QTest.qWait(50)
        return window

    def close(window):
        window.pool.shutdown(wait=True)
        qapp.processEvents()
        window.manager.close()
        window.close()

    window = open_window()
    try:
        buttons = window.content_buttons
        assert buttons["animation"].isChecked() and not buttons["live-action"].isChecked()
        assert window.content_group.exclusive()
        buttons["live-action"].click()
        assert window.content_profile() == "live-action"
        assert not buttons["animation"].isChecked()
        assert "realesrgan-x4plus" in window.content_summary.text()
        assert "manifests/realesrgan-x4plus.json" in window.content_resolution.text()
        # The neural engine stays unavailable without a qualified model: no false success.
        assert not window.engine.model().item(1).isEnabled()
        assert all(b.isEnabled() for b in buttons.values())
        import os

        evidence = Path(os.environ.get("STUDIO_IA_GUI_EVIDENCE", tmp_path))
        evidence.mkdir(parents=True, exist_ok=True)
        window.settings_scroll.ensureWidgetVisible(window.content_resolution)
        assert window.grab().save(str(evidence / "lot03-profile-live-action.png"))
    finally:
        close(window)
    reopened = open_window()
    try:
        assert reopened.content_profile() == "live-action"
        reopened.content_buttons["animation"].click()
        assert reopened.content_profile() == "animation"
        reopened.settings_scroll.ensureWidgetVisible(reopened.content_resolution)
        assert reopened.grab().save(str(evidence / "lot03-profile-animation.png"))
    finally:
        close(reopened)

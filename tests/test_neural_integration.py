"""UI/CLI/job contracts, not real NCNN or GPU qualification."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_models import model as model
from test_neural_failures import neural_transport as neural_transport

from studio_ia import neural
from studio_ia.core import StudioError
from studio_ia.jobs import Manager


def test_unknown_binary_is_refused_without_executing_it(tmp_path, monkeypatch):
    p = tmp_path / "arbitrary-program"
    p.write_bytes(b"untrusted executable payload")
    monkeypatch.setattr(neural.subprocess, "run", lambda *a, **k: pytest.fail("must not execute"))
    with pytest.raises(StudioError, match="épinglé"):
        neural.probe(p)


def test_cli_doctor_has_no_qt_dependency_or_gpu_promotion(tmp_path):
    p = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from studio_ia.cli import main; "
            "sys.argv=['studio-ia','doctor','neural']; main(); assert 'PySide6' not in sys.modules",
        ],
        text=True,
        capture_output=True,
        env={**os.environ, "STUDIO_IA_HOME": str(tmp_path / "cli-state")},
    )
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert data["neural"]["real_video_validated"] is False
    assert data["neural"]["inference"] == "NOT_RUN"
    assert data["ncnn"]["status"] == "NOT_CONFIGURED"


def test_manager_neural_failure_never_falls_back_to_cpu(request, tools, tmp_path, monkeypatch):
    from test_jobs import wait_job

    import studio_ia.jobs as jobs

    frozen, source, *_ = request.getfixturevalue("neural_transport")

    def blocked(*a, **k):
        raise StudioError("BLOCKED TEST CONTRACT ONLY")

    monkeypatch.setattr(neural, "run_neural_plan", blocked)
    monkeypatch.setattr(jobs, "run_plan", lambda *a, **k: pytest.fail("silent CPU fallback"))
    manager = Manager(tmp_path / "manager", tools)
    try:
        job = manager.submit(frozen.request, neural_plan=frozen.to_dict())
        row = wait_job(manager, job)
        assert row["state"] == "FAILED" and "BLOCKED" in row["error"]
        assert row["neural_plan"] == frozen.to_dict()
        assert not Path(frozen.request.destination).exists() and source.exists()
    finally:
        manager.close()


def test_preview_rejects_source_change_before_any_inference(request, tools, tmp_path, monkeypatch):
    frozen, source, *_ = request.getfixturevalue("neural_transport")
    source.write_bytes(b"changed source")
    monkeypatch.setattr(
        neural, "qualify", lambda *a, **k: pytest.fail("source must be checked first")
    )
    with pytest.raises(StudioError, match="modifié"):
        neural.preview_neural(frozen, tools, tmp_path / "changed-preview")


def test_preview_uses_current_segment_and_records_actual_timestamp(request, tools, tmp_path):
    frozen, *_ = request.getfixturevalue("neural_transport")
    result = neural.preview_neural(frozen, tools, tmp_path / "preview", seconds=0.2, duration=1)
    assert result["requested_source_seconds"] == 0.2
    assert result["actual_sample_source_seconds_rational"] == "1/4"
    assert result["scope"] == "SHORT_SEGMENT_ONLY_NOT_FULL_VIDEO_QUALIFICATION"
    assert result["settings_changed"] is False
    for name in ["source-segment", "cpu", "neural"]:
        assert (tmp_path / "preview" / f"{name}.png").stat().st_size > 0


@pytest.mark.gui
def test_ui_cpu_default_neural_disabled_and_stale_preview_refused(tmp_path, qapp):
    from PySide6.QtTest import QTest

    from studio_ia.ui import Window

    window = Window(tmp_path / "ui-state")
    try:
        window.show()
        QTest.qWait(50)
        assert window.engine.currentIndex() == 0
        assert all(not window.engine.model().item(i).isEnabled() for i in [1, 2, 3])
        assert not window.neural_preview_button.isEnabled()
        old_version = window.versions.get("neural_preview", 0)
        window.invalidate()
        window.status.setText("Current source")
        window.receive("neural_preview", old_version, {"status": "PASS"}, "")
        assert window.status.text() == "Current source"
        output = Path(os.environ.get("STUDIO_IA_GUI_EVIDENCE", tmp_path))
        output.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(output / "m004-neural-selector.png"))
    finally:
        window.pool.shutdown(wait=True)
        qapp.processEvents()
        window.manager.close()
        window.close()

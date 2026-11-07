"""Regressions found while consolidating the first build."""

import json
import shutil
from pathlib import Path

import pytest

from studio_ia.core import StudioError
from studio_ia.pipeline import Request, build_plan, run_plan


def test_destination_added_as_symlink_cannot_redirect_export(source, tmp_path, tools):
    destination = tmp_path / "requested.mp4"
    unexpected = tmp_path / "unexpected.mp4"
    plan = build_plan(Request(str(source), str(destination)), tools)
    try:
        destination.symlink_to(unexpected)
    except OSError:
        pytest.skip("This account/filesystem cannot create symbolic links")
    with pytest.raises(StudioError):
        run_plan(plan, tools, tmp_path / "job")
    assert destination.is_symlink()
    assert not unexpected.exists()


def test_failed_commit_never_leaves_success_report(source, tmp_path, tools):
    destination = tmp_path / "conflict.mp4"
    plan = build_plan(Request(str(source), str(destination)), tools)

    def conflict(stage):
        if stage == "VERIFYING":
            destination.write_bytes(b"file belonging to another application")

    with pytest.raises(StudioError):
        run_plan(plan, tools, tmp_path / "job", on_stage=conflict)
    assert not (tmp_path / "job/result.json").exists()
    assert destination.read_bytes() == b"file belonging to another application"


def test_cleanup_failure_does_not_misreport_verified_export(source, tmp_path, tools, monkeypatch):
    import studio_ia.pipeline as pipeline

    original = shutil.rmtree

    def fail_owned_cleanup(path, *args, **kwargs):
        if Path(path).name.startswith(".studio-ia-"):
            raise PermissionError("Cleanup temporarily denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pipeline.shutil, "rmtree", fail_owned_cleanup)
    destination = tmp_path / "verified.mp4"
    try:
        result = run_plan(
            build_plan(Request(str(source), str(destination)), tools), tools, tmp_path / "job"
        )
        assert result["status"] == "PASS" and destination.is_file()
        assert result["warnings"]
        assert json.loads((tmp_path / "job/result.json").read_text(encoding="utf-8"))["warnings"]
    finally:
        for path in tmp_path.glob(".studio-ia-*"):
            original(path)

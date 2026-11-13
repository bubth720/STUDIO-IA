import os

import pytest

from studio_ia.core import Cancellation, StudioError, execute
from studio_ia.pipeline import Request, build_plan, run_plan


def test_actual_invalid_filter_fails_without_export(source, tmp_path, tools):
    output = tmp_path / "no-export.mp4"
    plan = build_plan(Request(str(source), str(output)), tools)
    plan.filters = ["this_filter_does_not_exist"]
    with pytest.raises(StudioError, match="FFmpeg a échoué"):
        run_plan(plan, tools, tmp_path / "job")
    assert not output.exists()
    assert "No such filter" in (tmp_path / "job/pipeline.log").read_text()


def test_unwritable_destination(source, tmp_path, tools):
    if os.name == "nt":
        pytest.skip("POSIX directory permissions are not Windows ACLs")
    directory = tmp_path / "read-only"
    directory.mkdir()
    directory.chmod(0o500)
    try:
        with pytest.raises((StudioError, OSError)):
            plan = build_plan(Request(str(source), str(directory / "out.mp4")), tools)
            run_plan(plan, tools, tmp_path / "job")
        assert not (directory / "out.mp4").exists()
    finally:
        directory.chmod(0o700)


def test_process_timeout_is_enforced(tmp_path, tools):
    args = [
        tools.ffmpeg,
        "-v",
        "error",
        "-re",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=duration=5:size=320x180",
        "-f",
        "null",
        "-",
    ]
    with pytest.raises(StudioError, match="Délai"):
        execute(args, tmp_path / "timeout.log", Cancellation(), timeout=0.1)

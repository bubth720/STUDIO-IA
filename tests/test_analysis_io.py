"""Exercise real child processes: bounded output, timeout and cancellation."""

import sys
import threading
import time
from dataclasses import FrozenInstanceError

import pytest

from studio_ia.analysis_io import capture_local
from studio_ia.core import Cancellation, Cancelled, StudioError
from studio_ia.temporal import FrameRecord, parse_frame_timeline


def test_capture_real_stdout_and_nonzero_stderr():
    assert capture_local([sys.executable, "-c", 'print("réel")']) == "réel\n"
    with pytest.raises(StudioError, match="code 3.*diagnostic"):
        capture_local(
            [sys.executable, "-c", 'import sys; sys.stderr.write("diagnostic"); sys.exit(3)']
        )


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_bounded_real_child_output(stream):
    with pytest.raises(StudioError, match="hors budget"):
        capture_local(
            [sys.executable, "-c", f'import sys; sys.{stream}.write("x" * 70000)'], max_bytes=100
        )


def test_real_child_timeout_and_cancel():
    started = time.monotonic()
    with pytest.raises(StudioError, match="Délai"):
        capture_local([sys.executable, "-c", "import time; time.sleep(20)"], timeout=0.1)
    assert time.monotonic() - started < 8
    cancel = Cancellation()
    timer = threading.Timer(0.1, cancel.request)
    timer.start()
    try:
        with pytest.raises(Cancelled):
            capture_local([sys.executable, "-c", "import time; time.sleep(20)"], cancel)
    finally:
        timer.join()


def test_frame_identity_is_exact_and_immutable():
    record = FrameRecord(0, -1001, 1, 24000, None, False)
    assert str(record.presentation_time) == "-1001/24000"
    with pytest.raises(FrozenInstanceError):
        record.pts_int = 0
    with pytest.raises(StudioError):
        FrameRecord(0, 1.5, 1, 24, None, False)
    with pytest.raises(StudioError, match="Timebase"):
        parse_frame_timeline(
            {"streams": [{"time_base": 0.04}], "frames": [{"best_effort_timestamp": 0}]}
        )

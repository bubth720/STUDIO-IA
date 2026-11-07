import time

import pytest
from PySide6.QtTest import QTest

from studio_ia.pipeline import Request, build_plan, run_plan
from studio_ia.ui import Window


@pytest.mark.gui
def test_history_loading_invalidates_a_different_pending_plan(source, tools, tmp_path, qapp):
    saved_plan = build_plan(Request(str(source), str(tmp_path / "saved.mp4")), tools)
    saved_result = run_plan(saved_plan, tools, tmp_path / "saved-job")
    window = Window(tmp_path / "ui-state")
    window.show()

    def wait(predicate):
        deadline = time.monotonic() + 30
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError(window.status.text())
            QTest.qWait(20)

    try:
        window.import_source(str(source))
        wait(lambda: window.source is not None)
        window.destination.setText(str(tmp_path / "a-different-output.mp4"))
        window.validate_plan()
        wait(lambda: window.plan is not None)
        window.manager.store.put(
            {
                "id": "saved",
                "state": "SUCCEEDED",
                "request": saved_plan.to_dict()["request"],
                "result": saved_result,
            }
        )
        window.refresh()
        window.history.setCurrentRow(0)
        window.load_history()
        assert window.plan is None and not window.start_button.isEnabled()
        wait(lambda: window.last_result is not None)
        assert window.plan is None and not window.start_button.isEnabled()
    finally:
        wait(lambda: all(future.done() for future in window.futures))
        window.manager.close()
        window.close()
        qapp.processEvents()

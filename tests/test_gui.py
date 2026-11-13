import os
from pathlib import Path

import pytest

from studio_ia.smoke import run_smoke
from studio_ia.ui import Window


@pytest.mark.gui
@pytest.mark.integration
def test_gui_real_pipeline_and_cancel(tmp_path, qapp):
    root = Path(os.environ.get("STUDIO_IA_GUI_EVIDENCE", tmp_path / "gui"))
    report = run_smoke(root)
    assert report["status"] == "PASS"
    assert report["no_cancelled_output"]


@pytest.mark.gui
def test_deband_is_disabled_by_default_and_only_editable_in_custom_profile(tmp_path, qapp):
    """UI cannot silently enable smoothing for preservation/control profiles."""
    window = Window(tmp_path / "deband-ui-state")
    try:
        assert window.deband.currentIndex() == 0
        assert not window.deband.isEnabled()
        window.profile.setCurrentIndex(1)
        assert window.deband.isEnabled()
        window.deband.setCurrentIndex(2)
        assert window.deband.currentIndex() == 2
        window.profile.setCurrentIndex(0)
        assert window.deband.currentIndex() == 0
        assert not window.deband.isEnabled()
    finally:
        window.pool.shutdown(wait=True)
        qapp.processEvents()
        window.manager.close()
        window.close()


@pytest.mark.gui
def test_small_window_settings_keep_readable_height(tmp_path, qapp):
    from PySide6.QtTest import QTest

    window = Window(tmp_path / "small-window-state")
    try:
        window.resize(1024, 720)
        window.show()
        QTest.qWait(100)
        assert window.settings_scroll.verticalScrollBar().maximum() > 0
        for control in (
            window.profile,
            window.denoise,
            window.brightness,
            window.destination,
            window.plan_button,
            window.start_button,
        ):
            window.settings_scroll.ensureWidgetVisible(control)
            qapp.processEvents()
            assert control.height() >= control.sizeHint().height()
            assert (
                window.settings_scroll.viewport()
                .rect()
                .contains(control.mapTo(window.settings_scroll.viewport(), control.rect().center()))
            )
    finally:
        window.pool.shutdown(wait=True)
        qapp.processEvents()
        window.manager.close()
        window.close()

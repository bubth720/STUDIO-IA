import os
from pathlib import Path

import pytest

from studio_ia.smoke import run_smoke


@pytest.mark.gui
@pytest.mark.integration
def test_gui_real_pipeline_and_cancel(tmp_path, qapp):
    root = Path(os.environ.get("STUDIO_IA_GUI_EVIDENCE", tmp_path / "gui"))
    report = run_smoke(root)
    assert report["status"] == "PASS"
    assert report["no_cancelled_output"]

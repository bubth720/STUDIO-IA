import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_fixtures import fixture  # noqa: E402

from studio_ia.core import Tools  # noqa: E402


@pytest.fixture(scope="session")
def tools():
    return Tools.discover()


@pytest.fixture(scope="session")
def source(tmp_path_factory, tools):
    return fixture(tools, tmp_path_factory.mktemp("media") / "entrée avec espaces.mp4")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_IA_HOME", str(tmp_path / "state"))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application

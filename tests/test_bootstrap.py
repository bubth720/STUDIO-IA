from importlib.metadata import version

from studio_ia import __version__


def test_version():
    assert __version__ == version("studio-ia")

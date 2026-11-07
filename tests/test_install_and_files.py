import errno
import json
import os
import shutil
import subprocess
import sys

import pytest

from studio_ia.core import StudioError, Tools, state_dir
from studio_ia.files import publish_no_replace
from studio_ia.media import sha256


def test_configuration_rejects_non_object_json():
    (state_dir() / "config.json").write_text("[]", encoding="utf-8")
    with pytest.raises(StudioError, match="Configuration illisible"):
        Tools.discover()


def test_single_unicode_ffmpeg_path_finds_sibling_probe(tmp_path, tools, monkeypatch):
    folder = tmp_path / "outils 日本語 été"
    folder.mkdir()
    ffmpeg = folder / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    ffprobe = folder / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
    shutil.copy2(tools.ffmpeg, ffmpeg)
    shutil.copy2(tools.ffprobe, ffprobe)
    (state_dir() / "config.json").write_text(
        json.dumps({"ffmpeg": str(ffmpeg)}, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setenv("PATH", "")
    discovered = Tools.discover()
    assert discovered.ffmpeg == str(ffmpeg) and discovered.ffprobe == str(ffprobe)


def test_utf8_json_independent_of_process_locale(tmp_path):
    script = r"""
import json,sys
from pathlib import Path
from studio_ia.files import write_json
path=Path(sys.argv[1])
write_json(path, {"name":"\u65e5\u672c\u8a9e \u00e9t\u00e9"})
assert json.loads(path.read_bytes().decode("utf-8"))["name"] == "\u65e5\u672c\u8a9e \u00e9t\u00e9"
"""
    env = {**os.environ, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "record.json")],
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize("mode", ["source", "existing_report", "destination"])
def test_cli_report_cannot_destroy_media_or_existing_file(source, tmp_path, mode):
    before = sha256(source)
    destination = tmp_path / "out.mp4"
    report = source if mode == "source" else destination
    if mode == "existing_report":
        report = tmp_path / "old-report.json"
        report.write_text("keep this report", encoding="utf-8")
    args = [
        sys.executable,
        "-m",
        "studio_ia.cli",
        "process",
        str(source),
        str(destination),
        "--json",
        str(report),
    ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode != 0 and sha256(source) == before
    assert not destination.exists()
    if mode == "existing_report":
        assert report.read_text() == "keep this report"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux renameat2 fallback qualification")
def test_unsupported_links_use_real_no_replace_rename(tmp_path, monkeypatch):
    import studio_ia.files as files

    def unsupported(*_):
        raise OSError(errno.EOPNOTSUPP, "Hard links unavailable")

    monkeypatch.setattr(files.os, "link", unsupported)
    source, destination = tmp_path / "temporary", tmp_path / "final"
    source.write_bytes(b"verified output")
    assert publish_no_replace(source, destination) == "linux_renameat2_no_replace"
    assert destination.read_bytes() == b"verified output"
    second = tmp_path / "second"
    second.write_bytes(b"do not replace the first output")
    with pytest.raises(FileExistsError):
        publish_no_replace(second, destination)
    assert destination.read_bytes() == b"verified output" and second.exists()


def test_publication_primitive_never_replaces_destination(tmp_path):
    source, destination = tmp_path / "temporary", tmp_path / "final"
    source.write_bytes(b"new")
    destination.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        publish_no_replace(source, destination)
    assert destination.read_bytes() == b"existing" and source.exists()


def test_cli_unicode_metadata_on_ascii_stdout(source):
    result = subprocess.run(
        [sys.executable, "-m", "studio_ia.cli", "analyze", str(source)],
        env={**os.environ, "PYTHONIOENCODING": "ascii"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["path"] == str(source)

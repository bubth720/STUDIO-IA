"""Synthetic bytes test storage security only, never neural inference."""

import copy
import zipfile

import pytest

from studio_ia.core import StudioError
from studio_ia.media import sha256
from studio_ia.models import BACKEND, inspect, inspect_archive, read_manifest, register


@pytest.fixture
def model(tmp_path):
    root = tmp_path / "modèles 日本語"
    root.mkdir()
    files = []
    for role, suffix in [("param", "param"), ("weights", "bin")]:
        p = root / f"realesr-animevideov3-x2.{suffix}"
        p.write_bytes(b"SYNTHETIC CONTRACT TEST ONLY " + role.encode())
        files.append({"role": role, "path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)})
    license_info = {
        "spdx": "CC0-1.0",
        "source": "https://example.org/synthetic-fixture",
        "reviewed": True,
    }
    manifest = {
        "schema_version": 2,
        "id": "synthetic-contract-test",
        "name": "realesr-animevideov3",
        "version": "synthetic-not-a-model",
        "backend": BACKEND,
        "loader": "ncnn-param-bin",
        "scale": 2,
        "source": {
            "origin": "https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0",
            "source_ref": "fixture-not-upstream-weights",
        },
        "licenses": {k: copy.deepcopy(license_info) for k in ["code", "weights", "shaders"]},
        "files": files,
    }
    return root, manifest


def test_unicode_inspection_snapshot_and_immutable_identity(model, tmp_path):
    root, manifest = model
    record = inspect(root, manifest)
    identity = record.identity
    manifest["version"] = "changed-caller-dict"
    assert record.identity == identity
    record.manifest["files"][0]["sha256"] = "0" * 64
    record.revalidate()
    record.snapshot(tmp_path / "owned-job-model")
    assert (
        sha256(tmp_path / "owned-job-model" / record.manifest["files"][0]["path"])
        == record.manifest["files"][0]["sha256"]
    )


def test_missing_model_and_mutation_after_validation(model):
    root, manifest = model
    record = inspect(root, manifest)
    p = root / manifest["files"][1]["path"]
    p.write_bytes(b"altered")
    with pytest.raises(StudioError, match="modifié"):
        record.revalidate()
    p.unlink()
    with pytest.raises(StudioError, match="absent"):
        record.revalidate()


@pytest.mark.parametrize("component", ["code", "weights", "shaders"])
def test_separate_licenses_are_mandatory(model, component):
    root, manifest = model
    manifest["licenses"][component]["reviewed"] = False
    with pytest.raises(StudioError, match="Licence"):
        inspect(root, manifest)


@pytest.mark.parametrize(
    "path",
    ["../escape.bin", "/tmp/escape.bin", "C:/escape.bin", "..\\escape.bin", "a/../escape.bin"],
)
def test_traversal_is_refused(model, path):
    root, manifest = model
    manifest["files"][1]["path"] = path
    with pytest.raises(StudioError):
        inspect(root, manifest)


def test_symlink_and_linked_root_refused(model, tmp_path):
    root, manifest = model
    p = root / manifest["files"][1]["path"]
    target = tmp_path / "outside.bin"
    p.rename(target)
    try:
        p.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation unavailable in this test environment")
    with pytest.raises(StudioError, match="Lien"):
        inspect(root, manifest)
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(root, target_is_directory=True)
    with pytest.raises(StudioError, match="Racine"):
        inspect(linked_root, manifest)


def test_registry_duplicate_id_preserves_first_record(model, tmp_path):
    root, manifest = model
    registry = tmp_path / "registry.json"
    assert register(root, manifest, registry)["real_video_validated"] is False
    before = registry.read_bytes()
    with pytest.raises(StudioError, match="dupliqué"):
        register(root, manifest, registry)
    assert registry.read_bytes() == before


def test_duplicate_json_and_unsafe_loader_refused(model, tmp_path):
    root, manifest = model
    p = tmp_path / "manifest.json"
    p.write_text('{"schema_version":2,"schema_version":1}')
    with pytest.raises(StudioError, match="dupliquée"):
        read_manifest(p)
    manifest["loader"] = "python-pickle"
    with pytest.raises(StudioError, match="chargeur"):
        inspect(root, manifest)


@pytest.mark.parametrize(
    "name", ["../escape.bin", "a/../../escape.bin", "C:/escape.bin", "evil.py", "model.pth"]
)
def test_archive_rejects_traversal_and_code_without_extraction(tmp_path, name):
    archive = tmp_path / "model.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(name, b"bad")
    with pytest.raises(StudioError):
        inspect_archive(archive)
    assert not (tmp_path / "escape.bin").exists()


def test_corrupt_archive_and_budget(tmp_path):
    p = tmp_path / "broken.zip"
    p.write_bytes(b"not a zip")
    with pytest.raises(StudioError, match="malformée"):
        inspect_archive(p)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("model.bin", b"x" * 128)
    with pytest.raises(StudioError, match="budget"):
        inspect_archive(p, max_bytes=64)


def test_archive_inspection_never_extracts(tmp_path):
    p = tmp_path / "model.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("model.bin", b"fixture")
    assert inspect_archive(p) == ["model.bin"]
    assert not (tmp_path / "model.bin").exists()

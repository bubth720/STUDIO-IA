"""Local NCNN manifests. Never downloads, unpickles or executes model code."""

import hashlib
import json
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from studio_ia.core import StudioError
from studio_ia.files import write_json
from studio_ia.media import sha256

BACKEND = "realesrgan-ncnn-vulkan/0.2.0"
OFFICIAL = "https://github.com/xinntao/Real-ESRGAN"


def canonical(data: dict) -> str:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StudioError("Manifeste : clé JSON dupliquée.")
        result[key] = value
    return result


def read_manifest(path: Path) -> dict:
    if path.stat().st_size > 1024 * 1024:
        raise StudioError("Manifeste trop volumineux.")
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    validate_manifest(data)
    return data


def relative_path(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise StudioError("Chemin de modèle relatif POSIX requis.")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or PureWindowsPath(name).drive
        or any(p in (".", "..", "") for p in name.split("/"))
    ):
        raise StudioError("Chemin hors racine interdit.")
    return path


def validate_manifest(data: dict) -> None:
    try:
        if data["schema_version"] != 2 or data["loader"] != "ncnn-param-bin":
            raise StudioError("Schéma/chargeur non accepté ; aucun pickle, PTH ou code Python.")
        if not re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", data["id"]):
            raise StudioError("Identifiant de modèle invalide.")
        if data["backend"] != BACKEND or data["name"] != "realesr-animevideov3":
            raise StudioError("Backend/modèle non pris en charge par cet adaptateur.")
        if data["scale"] != 2 or type(data["scale"]) is not int:
            raise StudioError("Ce contrat qualifie uniquement le modèle natif ×2.")
        if not data["version"] or not data["source"]["source_ref"]:
            raise StudioError("Version et source_ref obligatoires.")
        origin = data["source"]["origin"]
        if not (origin.startswith(OFFICIAL + "/") or origin.startswith(OFFICIAL + "-ncnn-vulkan/")):
            raise StudioError("Origine officielle Real-ESRGAN requise.")
        for component in ("code", "weights", "shaders"):
            license_info = data["licenses"][component]
            if license_info.get("spdx") in (None, "", "UNKNOWN", "UNVERIFIED") or not (
                license_info.get("source", "").startswith("https://")
                and license_info.get("reviewed") is True
            ):
                raise StudioError(f"Licence {component} absente ou non vérifiée.")
        files = data["files"]
        if len(files) != 2 or {f["role"] for f in files} != {"param", "weights"}:
            raise StudioError("Paire NCNN .param/.bin obligatoire.")
        expected_names = {
            "param": "realesr-animevideov3-x2.param",
            "weights": "realesr-animevideov3-x2.bin",
        }
        for item in files:
            path = relative_path(item["path"])
            if str(path) != expected_names[item["role"]]:
                raise StudioError("Noms NCNN exacts requis ; aucun fichier exécutable.")
            if not re.fullmatch("[0-9a-f]{64}", item["sha256"]):
                raise StudioError("SHA-256 attendu obligatoire.")
            if type(item["bytes"]) is not int or not 0 < item["bytes"] <= 512 * 1024**2:
                raise StudioError("Taille de modèle hors budget.")
        if data["files"][0]["path"] == data["files"][1]["path"]:
            raise StudioError("Fichier dupliqué.")
    except (KeyError, TypeError, AttributeError) as exc:
        raise StudioError("Manifeste incomplet ou mal typé.") from exc


def safe_file(root: Path, relative: str) -> Path:
    relative_path(relative)
    if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise StudioError("Racine de modèles liée interdite.")
    root = root.resolve(strict=True)
    path = root
    for part in PurePosixPath(relative).parts:
        path /= part
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise StudioError("Lien de modèle interdit.")
    if not path.resolve(strict=True).is_relative_to(root) or not path.is_file():
        raise StudioError("Fichier modèle absent ou hors racine.")
    return path


@dataclass(frozen=True)
class ModelRecord:
    root: str
    manifest_json: str

    @property
    def manifest(self) -> dict:
        return json.loads(self.manifest_json)

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.manifest_json.encode()).hexdigest()

    def revalidate(self) -> None:
        data = self.manifest
        validate_manifest(data)
        for item in data["files"]:
            try:
                path = safe_file(Path(self.root), item["path"])
                if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                    raise StudioError("Modèle modifié après validation : hash/taille incorrect.")
            except OSError as exc:
                raise StudioError("Modèle absent ou inaccessible.") from exc

    def snapshot(self, destination: Path) -> None:
        """Copy to an owned fresh job directory, then hash the bytes actually consumed."""
        self.revalidate()
        destination.mkdir(mode=0o700, exist_ok=False)
        for item in self.manifest["files"]:
            original = safe_file(Path(self.root), item["path"])
            target = destination / item["path"]
            with original.open("rb") as source, target.open("xb") as out:
                while chunk := source.read(1024 * 1024):
                    out.write(chunk)
                    if out.tell() > item["bytes"]:
                        raise StudioError("Modèle modifié pendant la copie.")
            if target.stat().st_size != item["bytes"] or sha256(target) != item["sha256"]:
                raise StudioError("Modèle modifié pendant la copie.")


def inspect(root: Path, manifest: dict) -> ModelRecord:
    validate_manifest(manifest)
    # Preserve the entered root until symlink validation has completed.
    if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise StudioError("Racine de modèles liée interdite.")
    record = ModelRecord(str(root.resolve(strict=True)), canonical(manifest))
    record.revalidate()
    return record


def register(root: Path, manifest: dict, registry: Path) -> dict:
    record = inspect(root, manifest)
    rows = json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else []
    if not isinstance(rows, list) or any(r["manifest"]["id"] == manifest["id"] for r in rows):
        raise StudioError("Registre invalide ou identifiant dupliqué.")
    result = {
        "schema_version": 2,
        "root": record.root,
        "manifest": record.manifest,
        "manifest_sha256": record.identity,
        "integrity": "VERIFIED_LOCAL_FILES",
        "hardware": "NOT_TESTED",
        "real_video_validated": False,
    }
    write_json(registry, [*rows, result])
    return result


def inspect_archive(path: Path, *, max_bytes: int = 512 * 1024**2) -> list[str]:
    """Validate a ZIP without extracting it. Import never executes or silently unpacks."""
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 128 or sum(e.file_size for e in entries) > max_bytes:
                raise StudioError("Archive hors budget.")
            names = set()
            for entry in entries:
                name = str(relative_path(entry.filename.rstrip("/")))
                if name.casefold() in names:
                    raise StudioError("Archive : entrée dupliquée.")
                names.add(name.casefold())
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode) or entry.flag_bits & 1:
                    raise StudioError("Archive liée/chiffrée interdite.")
                if not entry.is_dir() and Path(name).suffix not in (
                    ".param",
                    ".bin",
                    ".json",
                    ".txt",
                ):
                    raise StudioError("Archive : type de fichier non accepté.")
            if archive.testzip() is not None:
                raise StudioError("Archive corrompue.")
            return sorted(names)
    except (zipfile.BadZipFile, OSError) as exc:
        raise StudioError("Archive malformée ou inaccessible.") from exc

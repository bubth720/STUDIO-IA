"""Copy actual Debian/Ubuntu binary copyright notices into an experimental bundle."""

import ast
import json
import platform
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote


def collect(toc: Path, folder: Path) -> dict:
    data = ast.literal_eval(toc.read_text(encoding="utf-8"))
    entries = []

    def visit(value):
        if isinstance(value, (list, tuple)):
            if (
                len(value) == 3
                and isinstance(value[1], str)
                and value[1].startswith(("/lib/", "/usr/lib/"))
                and value[2] in ("BINARY", "EXTENSION")
            ):
                entries.append(value)
            for child in value:
                visit(child)

    visit(data)
    distro = platform.freedesktop_os_release().get("ID")
    if distro not in ("debian", "ubuntu"):
        raise RuntimeError("System library license inventory currently supports Debian/Ubuntu only")
    notices = folder / "licenses/system-libraries"
    notices.mkdir(parents=True, exist_ok=True)
    inventory = {}
    packages = {}
    for destination, source, _ in entries:
        actual = str(Path(source).resolve())
        candidates = [source, actual]
        if actual.startswith("/usr/lib/"):
            candidates.append(actual.removeprefix("/usr"))
        if source.startswith("/lib/"):
            candidates.append("/usr" + source)
        owner = None
        for candidate in dict.fromkeys(candidates):
            match = subprocess.run(
                ["dpkg-query", "-S", candidate], text=True, capture_output=True, check=False
            )
            if match.returncode == 0:
                owner = match.stdout.splitlines()[0].split(": /", 1)[0]
                break
        if not owner:
            raise RuntimeError(f"No package ownership found for distributed library: {source}")
        if owner not in packages:
            binary_name = owner.split(":", 1)[0]
            copyright_file = Path("/usr/share/doc") / binary_name / "copyright"
            if not copyright_file.is_file():
                raise RuntimeError(f"Copyright file missing for distributed library: {owner}")
            shutil.copy2(copyright_file, notices / (binary_name + ".copyright"))
            details = (
                subprocess.check_output(
                    [
                        "dpkg-query",
                        "-W",
                        "-f=${source:Package}\t${source:Version}",
                        owner,
                    ],
                    text=True,
                )
                .strip()
                .split("\t")
            )
            name, version = details
            source_url = (
                f"https://snapshot.debian.org/package/{name}/{quote(version, safe='')}/"
                if distro == "debian"
                else f"https://launchpad.net/ubuntu/+source/{name}/{quote(version, safe='')}"
            )
            packages[owner] = {
                "source_package": name,
                "source_version": version,
                "corresponding_source": source_url,
                "copyright": f"licenses/system-libraries/{binary_name}.copyright",
            }
        inventory[destination] = {"binary_package": owner, **packages[owner]}
    shutil.copytree(
        "/usr/share/common-licenses", folder / "licenses/common-licenses", dirs_exist_ok=True
    )
    report = {
        "distribution": distro,
        "library_count": len(inventory),
        "package_count": len(packages),
        "libraries": inventory,
        "note": "Qt/PySide, ICU, Python and bootloader have separate included notices.",
    }
    (folder / "BINARY_LICENSES.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

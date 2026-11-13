#!/bin/sh
set -eu
studio_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3.12 >/dev/null 2>&1; then
    studio_python=python3.12
else
    studio_python=python3
fi
"$studio_python" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 requis"'
"$studio_python" -m venv "$studio_root/.venv"
"$studio_root/.venv/bin/python" -m pip install pip==26.3
"$studio_root/.venv/bin/python" -m pip install "$studio_root[gui]"
printf '%s\n' 'Installation locale terminée. Lancez Lancer-sources.sh.'

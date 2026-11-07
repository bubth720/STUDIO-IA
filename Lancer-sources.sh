#!/bin/sh
set -eu
studio_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$studio_root/.venv/bin/python" -m studio_ia.ui

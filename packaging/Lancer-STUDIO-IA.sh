#!/bin/sh
set -eu
studio_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$studio_dir/STUDIO-IA" "$@"

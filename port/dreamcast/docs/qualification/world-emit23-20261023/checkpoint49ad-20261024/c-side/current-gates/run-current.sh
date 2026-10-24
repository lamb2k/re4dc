#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
exec python3 -B "$HERE/current_gates.py" "$@"

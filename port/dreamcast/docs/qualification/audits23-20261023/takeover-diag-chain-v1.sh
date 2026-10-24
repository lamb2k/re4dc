#!/usr/bin/env bash
set -euo pipefail
for mode in "$@";do bash '/mnt/c/Game Dev/Emulators/codex-lanes/audits23/takeover-diag-run-v1.sh' "$mode";done
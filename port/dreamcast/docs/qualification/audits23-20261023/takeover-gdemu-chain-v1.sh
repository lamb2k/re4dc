#!/usr/bin/env bash
set -euo pipefail
for seed in "$@";do bash '/mnt/c/Game Dev/Emulators/codex-lanes/audits23/takeover-gdemu-v1.sh' "$seed";done
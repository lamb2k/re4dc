#!/usr/bin/env bash
set -euo pipefail
A='/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23'
for arm in B L E; do bash "$A/takeover-build-current-v1.sh" "$arm"; done
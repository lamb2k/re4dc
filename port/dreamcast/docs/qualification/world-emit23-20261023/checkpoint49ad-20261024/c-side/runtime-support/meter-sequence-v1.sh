#!/usr/bin/env bash
set -euo pipefail
H='/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/qualified-run-v1.sh'
for ITEM in 'L b1' 'E b1' 'B b1' 'R s2' 'L s2' 'E s2' 'B s2';do
 read -r ARM SCENE <<< "$ITEM"
 bash "$H" "$ARM" m "$SCENE" "$ARM-m-$SCENE-q1"
done
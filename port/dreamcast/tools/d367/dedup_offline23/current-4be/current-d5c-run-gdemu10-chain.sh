#!/bin/bash
set -euo pipefail
C='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
for seed in 2 3 4 5 6 7 8 9 10;do
 bash "$C/current-d5c-run-gdemu10.sh" "$seed"
done
python3 "$C/current-d5c-gdemu10.py" summary


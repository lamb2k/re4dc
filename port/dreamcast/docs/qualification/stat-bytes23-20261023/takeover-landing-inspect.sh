#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete
printf 'TEST23 README ITEMS\n'
git -C "$T" show origin/t15/int:README.md | grep -n -A42 -B3 -i 'Coming soon' | head -75
printf 'DREAMCAST DOCS HEAD\n'
git -C "$T" rev-parse origin/dreamcast-port
printf 'TEST23 OTHER BRANCH ITEMS\n'
git -C "$T" show origin/dreamcast-port:README.md | grep -n -A40 -B2 -i 'Coming soon' | head -65
printf 'LOCAL LIVE NOTES\n'
rg -n -i 'Coming soon|stat|Mendez|byte|Test23|Test 23' '/mnt/c/Game Dev/Emulators/RE4DC-Test22-Candidate/RELEASE-NOTES-LIVE.md' | head -30
printf 'BRANCH STATUS\n'
git -C "$T" status --short --branch

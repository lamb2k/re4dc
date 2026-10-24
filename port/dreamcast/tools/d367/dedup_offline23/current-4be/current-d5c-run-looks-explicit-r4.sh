set -euo pipefail
for SCENE in cross-off cross-on farm-off farm-on forest-off forest-on;do
 bash '/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/current-d5c-run-look-explicit-r4.sh' "$SCENE"
done

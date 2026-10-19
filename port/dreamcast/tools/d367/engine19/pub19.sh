set -euo pipefail
# pub19.sh (WSL): copy the A/B bench discs to C: once (release rule 3), with SHA256SUMS.
K=/root/work/lanes/engine19-scratch/bench
P="/mnt/c/Game Dev/Emulators/RE4DC-Bench-T19-WallCheck-5edfcd12"
mkdir -p "$P/A" "$P/B"
cp -r $K/disc-e19bA/gdemu "$P/A/"
cp -r $K/disc-e19bB/gdemu "$P/B/"
cd "$P" && sha256sum A/gdemu/* B/gdemu/* > SHA256SUMS.txt
cat SHA256SUMS.txt

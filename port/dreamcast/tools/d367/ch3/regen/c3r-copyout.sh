set -euo pipefail
# c3r-copyout.sh: stage verified outputs on ext4, one bulk copy to C:, sha-check there
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
O=$L/out
python3 "$S/c3r_stage.py" "$S/cover.json" "$S/missing.json" "$O"
D="/mnt/c/Game Dev/Emulators/re4-assets-private/ch3regen-20261018"
mkdir -p "$D"
cp -r "$O/." "$D/"
cd "$D" && sha256sum -c --quiet SHA256SUMS && echo "C: SHA CHECK OK $(wc -l < SHA256SUMS) files"
touch "$D/KEEP"

set -euo pipefail
# c3r-land.sh MSG: copyout (cover.json from Windows python c3r_cover.py), commit+push
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
cd /tmp
bash "$S/c3r-copyout.sh" 2>&1 | tail -2
bash "$S/c3r-commit.sh" "$1" 2>&1 | tail -2
git -C /root/probe/lanes-20261018/ch3regen/lane log --oneline -1

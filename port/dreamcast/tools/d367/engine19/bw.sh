set -euo pipefail
D=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/engine19
sed 's/\r$//' $D/b1.sh > /root/probe/lanes-20261019/engine19/k/b1.sh
bash /root/probe/lanes-20261019/engine19/k/b1.sh "$@" 2>&1 | tail -25

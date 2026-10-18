set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
R=/root/work/re4-dreamcast
cd $L/tools
git -C $R show origin/lane/ch5found16:port/dreamcast/tools/d367/st3firstpass/codex-tools-8bf46efe-st3.diff > $L/st3-tools.diff
git apply --stat $L/st3-tools.diff
git apply --check -v $L/st3-tools.diff 2>&1 | grep -iE 'error|fail|cleanly' | head -20

set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
D=$L/tree/port/dreamcast/tools/d367/ch5/regen
MSG=${1:?message}
mkdir -p $D
for f in $S/*.sh $S/*.py $S/README.md; do
  b=$(basename $f)
  case $b in c5r*|README.md) cp $f $D/$b; sed -i 's/\r$//' $D/$b;; esac
done
cd $L/tree
git add port/dreamcast/tools/d367/ch5/regen
git -c user.name=lamb2k -c user.email=nansenlamb1@gmail.com commit -q -F - <<M || true
$MSG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0161knP9yvavohe6o4n2fpoV
M
git log --oneline -1
git push -q origin HEAD:refs/heads/wip/ch5regen-20261018 2>&1 | tail -2
git ls-remote origin wip/ch5regen-20261018

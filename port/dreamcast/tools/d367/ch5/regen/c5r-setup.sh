set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
R=/root/work/re4-dreamcast
mkdir -p $L
[ -d $L/tools ] && [ ! -e $L/tools/port ] && rm -rf "${L:?}/tools"
if [ ! -d $L/tools ]; then
  git clone -q --shared --no-checkout $R $L/tools
  cd $L/tools
  git fetch -q "/mnt/c/Game Dev/Emulators/re4dc-recovery/gitdig18/90606dcf.bundle" '+refs/*:refs/bundle/*'
  git checkout -q --detach 90606dcf
  git -C $R show origin/wip/ch4regen-20261018:port/dreamcast/tools/d367/ch4found/regen/cxfix/le_mirror-67524643.diff > $L/le_mirror-67524643.diff
  git apply $L/le_mirror-67524643.diff
  sha256sum port/dreamcast/tools/le_mirror.py | cut -c1-12
  git -C $R show origin/lane/ch5found16:port/dreamcast/tools/d367/st3firstpass/codex-tools-8bf46efe-st3.diff > $L/st3-tools.diff
  git apply --check $L/st3-tools.diff && echo st3diff-applies || git apply --stat $L/st3-tools.diff
fi
git -C $L/tree log --oneline -1

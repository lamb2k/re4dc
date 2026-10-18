set -uo pipefail
L4=/root/probe/lanes-20261018/ch4regen
ls $L4/cxrun | head; ls $L4/cxextra | head
find $L4 -maxdepth 3 -name 'cx_room_fixtures*.py' | head
F=$(find $L4 -maxdepth 6 -name 'cx_room_fixtures.py' | head -1); echo F=$F
grep -n "package\|convert_room_bins\|MAINSCENARIO\|def prepare_room" $F | head -40
cd /root/work/re4-dreamcast; git show origin/wip/ch4regen-20261018:port/dreamcast/tools/d367/ch4found/regen/cxfix/cx-jobs.txt | head -20
git show origin/wip/ch4regen-20261018:port/dreamcast/tools/d367/ch4found/regen/cxfix/cxall.sh | head -40

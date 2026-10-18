set -euo pipefail
W=/root/probe/lanes-20261018/ch5tex; C=/root/probe/lanes-20261018/ch5regen
mkdir -p $W/tools
rsync -a --exclude=.assets $C/tools/ $W/tools/
mkdir -p $W/tools/.assets; rsync -a $C/tools/.assets/tools $W/tools/.assets/ 2>/dev/null || true
cd /root/work/re4-dreamcast
git show origin/wip/ch5regen-20261018:port/dreamcast/tools/d367/ch5/regen/c5r_run_rooms_st3.py | sed "s#^ROOT=Path('/root/probe/lanes-20261018/ch5regen')#ROOT=Path('/root/probe/lanes-20261018/ch5tex')#" > $W/run_rooms_st3.py
grep -n "^ROOT" $W/run_rooms_st3.py
cd $W
PYTHONDONTWRITEBYTECODE=1 nice $C/venv/bin/python run_rooms_st3.py r333 r332 > $W/ps2w.log 2>&1 || true
grep -E 'ROOM_READY|ROOM_BLOCKED|PREFLIGHT|Error' $W/ps2w.log | cut -c1-250 | tail -8
ls $W/tools/.assets/rooms-r333/work/r333/ 2>&1 | head
cmp $W/tools/.assets/rooms-r332/work/r332/r332.dat $C/tools/.assets/rooms-r332/work/r332/r332.dat && echo r332dat-same

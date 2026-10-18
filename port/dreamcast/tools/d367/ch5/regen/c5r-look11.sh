set -uo pipefail
G=/root/probe/lanes-20261018/ch5regen/game-249effe5
T=$G/port/dreamcast/tools
ls $T/d367/motion/hot/ | grep -E 'em3|em1d|em1e'
grep -n "em36.drs\|em39.drs" $T/prepare_enemy_motions.py | head
git -C $G log --oneline -3 -- port/dreamcast/tools/prepare_enemy_motions.py port/dreamcast/tools/d367/motion/hot
cd /mnt/c/tmp/ch5; grep -l "preph-em36\|em36-r3" * 2>/dev/null | head

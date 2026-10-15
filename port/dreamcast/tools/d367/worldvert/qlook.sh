#!/bin/bash
# qlook.sh <jobs file> (Git Bash): lane worldvert look runs, at most 2 at once, 60 s each, shots every 15 s
G=/c/Flycast-Evidence/re4-dreamcast/worldvert-20261015/_tools
F=/root/probe/lanes-20261015/worldvert-work/fix
run1() { n=$1; l=$2
  until [ $(df -BG /c | awk 'NR==2{print $4+0}') -ge ${MINGB:-19} ]; do sleep 30; done
  PERIOD=15 PURPOSE="worldvert look $n: arm $l, fixture $F/$n.json, 60 s, frozen at global tick 700" bash $G/wv-run.sh $n $l $F/$n.json 60 > $G/q-$n.log 2>&1
  echo "$(date +%T) $n $(tail -1 $G/q-$n.log)" >> $G/qdone.txt; }
while read -r n l; do
  [ -z "$n" ] && continue
  grep -q "moved to" $G/q-$n.log 2>/dev/null && continue
  while [ $(jobs -r | wc -l) -ge 2 ]; do sleep 5; done
  run1 $n $l < /dev/null &
  sleep 25
done < $1
wait
echo QLOOK DONE

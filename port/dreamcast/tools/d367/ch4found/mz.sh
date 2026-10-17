set -e
W=/root/probe/lanes-20261016/ch4found/warps
mk() { cat > $W/em11-$1.txt <<X
name em11-$1
# ch4found16 em11 hot list (MOTION_MISS_LOG): $1 from the Codex walk entry, kill rig on em11 (0x11) from room frame 120
room 0x${1#r}
pos $2
ang $3
inv default
god
alivelog 150
kill 0x11 120 0x${1#r}
killrep 10 30
dump
X
}
mk r222 "1340 54 -4343" -1.5340
mk r217 "5134 8021 -1025" -1.7800
mk r212 "4060 0 1980" -1.5710
bash /mnt/c/tmp/ch4/mkh.sh cxc4zmW | tail -1
cd /mnt/c/tmp/ch4
echo "r226 z1 $(ARM=cxc4zmW WARPTXT=$W/dec3-r226.txt bash mkfix.sh r226 z1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|exists.*\|Error.*' | tr '\n' ' ')"
for r in r222 r217 r212; do echo "$r z1 $(ARM=cxc4zmW WARPTXT=$W/em11-$r.txt bash mkfix.sh $r z1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|exists.*\|Error.*' | tr '\n' ' ')"; done

set -euo pipefail
# gates.sh (WSL; lane logiclod20): gameplay-equivalence gate warps + fixtures for arms <label>rW (K = recipe, B = bundle).
# Scenes: gR r101 kill rig to the bell, gA r103 kill rig, gC chickens, gW cows, gD r103 -> r106 door, gS r11c siege.
D=/root/work/lanes/logiclod20/port/dreamcast/tools/d367
W=/root/work/lanes/logiclod20-scratch/gates; mkdir -p $W
R103="room 0x103
pos -47609 12 7084
ang 1.889
inv default
god
alivelog 150"
cat > $W/gR.txt <<EOF
name ll20-gR
room 0x101
pos -7914 0 2000
ang 1.5708
find 0x00002000
inv default
god
alert 30
alivelog 150
kill 0 150 0x101
killrep 40 40
EOF
printf 'name ll20-gA\n%s\nkill 0 150 0x103\nkillrep 8 60\n' "$R103" > $W/gA.txt
printf 'name ll20-gC\n%s\nkill 0x28 100 0x103\nkillrep 2 90\n' "$R103" > $W/gC.txt
printf 'name ll20-gW\n%s\nkill 0x26 100 0x103\nkillrep 2 90\n' "$R103" > $W/gW.txt
printf 'name ll20-gD\nroom 0x103\npos 9470 38 -759\nang 0.8406\ninv default\ngod\nalivelog 150\nact 30 fwd 20\nact 60 a 4\nact 150 a 4\nact 240 a 4\n' > $W/gD.txt
grep -v '^name' $D/ch2/warps/s-siegek.txt | sed '1i name ll20-gS' > $W/gS.txt
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $D/rr/recipe.conf)"
for a in ${ARMS:-K B}; do for g in gR gA gC gW gD gS; do
  L=ll20g${a}rW; RAW=$W/$a-$g.raw.json
  python3 $D/test11/t11-fix.py $L $RAW --base payload --data "$DATA" --warp $W/$g.txt > $W/$a-$g.log 2>&1 || { tail -3 $W/$a-$g.log; exit 1; }
  python3 $D/texchk/fixture_arm.py $RAW $W/$a-$g.json $L --programs-dir "$RE4DC_PROGRAMS_DIR" >> $W/$a-$g.log 2>&1
  echo "fix $a-$g"
done; done

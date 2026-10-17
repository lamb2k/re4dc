#!/bin/bash
# snd5.sh: AICA banks + stream file for the island (lane ch5found16), the castle lane's snd31 method on the ch22 mirror-c23:
# room .dar (st3 rel33) + island enemy archives as an overlay, nested --fixed-route (test 15 layout frozen), --streams ch5.
set -e
L=/root/probe/lanes-20261016/ch5found
T=$L/tree/port/dreamcast/tools
W=$L/snd; mkdir -p $W; cd $W
C23=/root/probe/lanes-20261014/ch22/snd
S=/root/probe/lanes-20261014/st3
ISL="r300 r301 r303 r304 r305 r306 r307 r308 r30b r30c r30e r309 r30a r310 r311 r30d r312 r30f r315 r316 r317 r318 r31a r31b r31d r31c r320 r321 r325 r326 r327 r329 r330"
rm -rf ovl-c5 mirror-c5 aica-c5 str-c5; mkdir -p ovl-c5/st3 ovl-c5/em
for r in $ISL; do ln $S/rel33/rel-$r/st3/$r.dar ovl-c5/st3/$r.dar; done
for e in em1d em1e em1f; do ln $S/emprep/outT-$e/$e.drs ovl-c5/em/$e.drs; done
for e in em25 em32 em39 em3a em3d em3b; do ln $S/deps2/prepared/em/$e.drs ovl-c5/em/$e.drs; done
[ -d aica-cache ] || cp -al $C23/aica-cache aica-cache
python3 $T/aica_banks.py merge --mirror $C23/mirror-c23 --overlay ovl-c5 --out mirror-c5
R0='title,r100,r101,r103'
R1="$R0,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a,r119,r118,r117,r112,r111,r113,r11c"
R2="$R1,r11d,r11e,r10f,r11f,r200"
R="$R2,$(echo $ISL | tr ' ' ',')"
nice python3 $T/aica_banks.py build --mirror mirror-c5 --out aica-c5 --route $R --fixed-route "$R0;$R1;$R2" --weapons --cache aica-cache --json aica-c5.json > aica-c5.log 2>&1 || { tail -30 aica-c5.log; exit 1; }
grep -E "^  r3|does not fit|silent|missing|skip" aica-c5.log | head -60
cd aica-c5 && find . -type f | sort | xargs sha256sum > ../aica-c5.sha; cd $W
echo "== vs ch22 aica-c23 (only island files may differ)"
diff <(cd $C23/aica-c23 && find . -type f | sort | xargs sha256sum) aica-c5.sha | grep '^<' | head -10
nice python3 $T/aica_banks.py streams --mirror mirror-c5 --out str-c5 --streams ch5 > str-c5.log 2>&1 || { tail str-c5.log; exit 1; }
tail -3 str-c5.log
ls -la str-c5/bgm/aica_str.dat
rm -rf mirror-c5

#!/bin/bash
# snd.sh: AICA banks for the final chapter rooms (lane final16): ch5found16's snd5.sh method (the castle lane's snd31
# method on the ch22 mirror-c23, test 15 layout frozen with --fixed-route), route = test 15 + the island + r331 r332,
# overlay = the island room .dar files + island enemies + Saddler's prepared em31.drs (streamed motions).
set -e
L=/root/probe/lanes-20261016/final16
C5=/root/probe/lanes-20261016/ch5found
T=$L/tree/port/dreamcast/tools
W=$L/snd; mkdir -p $W; cd $W
C23=/root/probe/lanes-20261014/ch22/snd
S=/root/probe/lanes-20261014/st3
PREP=${PREP:-$L/prepem/prepc-em31}
ISL="r300 r301 r303 r304 r305 r306 r307 r308 r30b r30c r30e r309 r30a r310 r311 r30d r312 r30f r315 r316 r317 r318 r31a r31b r31d r31c r320 r321 r325 r326 r327 r329 r330"
FIN="r331 r332"
rm -rf ovl-f mirror-f aica-f; mkdir -p ovl-f/st3 ovl-f/em
for r in $ISL $FIN; do ln $S/rel33/rel-$r/st3/$r.dar ovl-f/st3/$r.dar; done
for e in em1d em1e em1f; do ln $S/emprep/outT-$e/$e.drs ovl-f/em/$e.drs; done
for e in em25 em32 em39 em3a em3d em3b; do ln $S/deps2/prepared/em/$e.drs ovl-f/em/$e.drs; done
cp $PREP/em31.drs ovl-f/em/em31.drs
[ -d aica-cache ] || cp -al $C5/snd/aica-cache aica-cache
python3 $T/aica_banks.py merge --mirror $C23/mirror-c23 --overlay ovl-f --out mirror-f
R0='title,r100,r101,r103'
R1="$R0,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a,r119,r118,r117,r112,r111,r113,r11c"
R2="$R1,r11d,r11e,r10f,r11f,r200"
R="$R2,$(echo $ISL $FIN | tr ' ' ',')"
nice python3 $T/aica_banks.py build --mirror mirror-f --out aica-f --route $R --fixed-route "$R0;$R1;$R2" --weapons --cache aica-cache --json aica-f.json > aica-f.log 2>&1 || { tail -30 aica-f.log; exit 1; }
grep -E "^  r33|^  r329|does not fit|silent|missing|skip|layout" aica-f.log | head -40
cd aica-f && find . -type f | sort | xargs sha256sum > ../aica-f.sha; cd $W
echo "== vs ch5found aica-c5 (only r331 / r332 / em31 may differ)"
diff <(cut -c67- $C5/snd/aica-c5.sha | sort; ) <(cut -c67- aica-f.sha | sort) | head
diff $C5/snd/aica-c5.sha aica-f.sha | grep '^<' | head -10
ls -la aica-f/em/em31.drs aica-f/st3/r33*.dar 2>/dev/null
rm -rf mirror-f

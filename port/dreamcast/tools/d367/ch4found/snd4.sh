#!/bin/bash
# snd4.sh: AICA banks + stream file for chapter 4 (lane ch4found16), the ch5found16 island method (snd5.sh) on the
# castle lane's c33 overlay: ch4 room .dar (lane rel31) + em16 / em1c (lane prepem) on top of ovl-c33, nested
# --fixed-route (the c33 levels frozen), --streams ch4. Every aica-c33 file must stay byte-identical.
set -e
L=/root/probe/lanes-20261016/ch4found
T=$L/tree/port/dreamcast/tools
W=$L/snd; mkdir -p $W; cd $W
C23=/root/probe/lanes-20261014/ch22/snd
C33=/root/probe/lanes-20261015/castle/snd
CH4="r210 r211 r212 r213 r214 r215 r216 r217 r218 r219 r21b r21d r220 r222 r223 r224 r225 r226 r227 r229 r22a r22b"
rm -rf ovl-c4 mirror-c4 aica-c4 str-c4; mkdir -p ovl-c4/st2 ovl-c4/em
cp -al $C33/ovl-c33/st2/. ovl-c4/st2/; cp -al $C33/ovl-c33/em/. ovl-c4/em/
for r in $CH4; do ln $L/rel31/rel-$r/st2/$r.dar ovl-c4/st2/$r.dar; done
for e in em16 em1c; do ln $L/prepem/prep-$e/$e.drs ovl-c4/em/$e.drs; done
[ -d aica-cache ] || cp -al $C33/aica-cache aica-cache
python3 $T/aica_banks.py merge --mirror $C23/mirror-c23 --overlay ovl-c4 --out mirror-c4
R0='title,r100,r101,r103'
R1="$R0,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a,r119,r118,r117,r112,r111,r113,r11c"
R2="$R1,r11d,r11e,r10f,r11f,r200"
R3="$R2,r202,r207,r203,r201,r208,r204"
R33="$R3,r205,r209,r20a,r20b,r20c,r20f,r206,r20d,r20e"
R="$R33,$(echo $CH4 | tr ' ' ',')"
nice python3 $T/aica_banks.py build --mirror mirror-c4 --out aica-c4 --route $R --fixed-route "$R0;$R1;$R2;$R3;$R33" --weapons --cache aica-cache --json aica-c4.json > aica-c4.log 2>&1 || { tail -30 aica-c4.log; exit 1; }
grep -E "^  r21|^  r22|does not fit|silent|missing|skip" aica-c4.log | head -60
cd aica-c4 && find . -type f | sort | xargs sha256sum > ../aica-c4.sha; cd $W
echo "== vs castle aica-c33 (only chapter 4 files may differ)"
diff <(cd $C33/aica-c33 && find . -type f | sort | xargs sha256sum) aica-c4.sha | grep '^<' | head -20
nice python3 $T/aica_banks.py streams --mirror mirror-c4 --out str-c4 --streams ch4 > str-c4.log 2>&1 || { tail str-c4.log; exit 1; }
tail -3 str-c4.log
ls -la str-c4/bgm/aica_str.dat
rm -rf mirror-c4

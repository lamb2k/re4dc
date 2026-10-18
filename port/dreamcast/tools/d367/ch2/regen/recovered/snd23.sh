# snd23.sh: AICA banks for chapter 2-3 (r11d r11e r10f r11f r200) on the ch22w 10-13 mirror (its snd.sh recipe)
set -e
LANE=/root/probe/lanes-20261014/ch22
T=$LANE/tree/port/dreamcast/tools
W=$LANE/snd; mkdir -p $W; cd $W
C22=/root/probe/lanes-20261013/ch22w/rooms
rm -rf ovl-c23 mirror-c23 aica-c23 str-c23
mkdir -p ovl-c23/st1 ovl-c23/st2 ovl-c23/em
python3 - <<'P'
import json, os
v = json.load(open('/root/probe/lanes-20261014/ch22/fix/route-v4.json'))['replace']
for k in ['st1/r11d.dar', 'st1/r11e.dar', 'st1/r10f.dar', 'st1/r11f.dar', 'st2/r200.dar', 'em/em16.drs', 'em/em35.drs']:
    os.link(v[k], 'ovl-c23/' + k)
    print(k, v[k])
P
[ -d aica-cache ] || cp -al /root/probe/lanes-20261010/r11a/rooms/aica-cache aica-cache
python3 $T/aica_banks.py merge --mirror $C22/mirror-aica-c22 --overlay ovl-c23 --out mirror-c23
R=title,r100,r101,r103,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a,r119,r118,r117,r112,r111,r113,r11c,r11d,r11e,r10f,r11f,r200
python3 $T/aica_banks.py build --mirror mirror-c23 --out aica-c23 --route $R --fixed-route 'title,r100,r101,r103;title,r100,r101,r103,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a,r119,r118,r117,r112,r111,r113,r11c' --weapons --cache aica-cache --json aica-c23.json > aica-c23.log 2>&1 || { tail -20 aica-c23.log; exit 1; }
grep -E "^  r1|^  r2|WEP slot" aica-c23.log
cd aica-c23 && find . -type f | sort | xargs sha256sum > ../aica-c23.sha
cd $W
echo "== vs ch22w aica-c22"
diff <(cd $C22/aica-c22 && find . -type f | sort | xargs sha256sum) aica-c23.sha || true
python3 $T/aica_banks.py streams --mirror mirror-c23 --out str-c23 --streams ch23 > str-c23.log 2>&1 || { tail str-c23.log; exit 1; }
tail -4 str-c23.log
cmp -n 2048 str-c23/bgm/aica_str.dat $C22/str-c22/bgm/aica_str.dat && echo "first 2048 B = ch22w str-c22"; ls -la str-c23/bgm/aica_str.dat $C22/str-c22/bgm/aica_str.dat

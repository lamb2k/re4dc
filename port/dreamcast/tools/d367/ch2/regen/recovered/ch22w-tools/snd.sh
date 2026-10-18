# snd.sh: AICA banks + streams for chapter 2-2 (r117 lane snd.sh recipe, on the r117 AICA mirror)
set -e
T=/root/probe/lanes-20261013/ch22/port/dreamcast/tools
W=/root/probe/lanes-20261013/ch22w/rooms
A=/root/probe/lanes-20261010/r11a/rooms
B=/root/probe/lanes-20261010/r117/rooms
ROOMS_NEW=${ROOMS_NEW:-r112 r111 r113}
cd $W
rm -rf ovl-c22 mirror-aica-c22 aica-c22 str-c22
mkdir -p ovl-c22/st1 ovl-c22/em
for r in $ROOMS_NEW; do ln rel-$r/st1/$r.dar ovl-c22/st1/$r.dar; done
ls -la $B/mirror-aica-r117/em/em17.drs $B/mirror-aica-r117/em/em18.drs $B/mirror-aica-r117/em/em2a.drs $B/mirror-aica-r117/em/pl11.drs
python3 $T/aica_banks.py merge --mirror $B/mirror-aica-r117 --overlay ovl-c22 --out mirror-aica-c22
R=$(echo $ROOMS_NEW | tr ' ' ',')
python3 $T/aica_banks.py build --mirror mirror-aica-c22 --out aica-c22 --route title,r100,r101,r103,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a,r119,r118,r117,r118c22,$R --fixed-route title,r100,r101,r103 --weapons --cache $A/aica-cache --json aica-c22.json > aica-c22.log 2>&1 || { tail -20 aica-c22.log; exit 1; }
grep -i "r11[1238]\|pl11\|em17\|em18\|arena\|error\|fail" aica-c22.log | head -30
cd aica-c22 && find . -type f | sort | xargs sha256sum > ../aica-c22.sha
diff $B/aica-r117.sha $W/aica-c22.sha || true
cd $W
python3 $T/aica_banks.py streams --mirror mirror-aica-c22 --out str-c22 --streams ch22 > str-c22.log 2>&1 || { tail str-c22.log; exit 1; }
tail -8 str-c22.log
cmp -n 2048 str-c22/bgm/aica_str.dat /root/probe/lanes-20261011/p2d/d2/str-d2/bgm/aica_str.dat; ls -la str-c22/bgm/aica_str.dat /root/probe/lanes-20261011/p2d/d2/str-d2/bgm/aica_str.dat

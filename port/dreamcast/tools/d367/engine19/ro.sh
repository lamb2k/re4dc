set -euo pipefail
# ro.sh: room files with OCCL (option C) for every r1xx/r2xx room, three compiles in parallel.
T=/root/work/lanes/engine19
O=/root/re4data/private/rc19o2-20261019
W=/root/work/lanes/engine19-scratch/wv
mkdir -p "$O"
cd $T/port/dreamcast/tools/enginebake
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
A="r101 r104 r107 r10a r10d r111 r117 r11a r11d r200 r203 r206 r209 r20c r20f r212 r215 r218 r21b r221 r224 r227 r22a"
B="r100 r105 r108 r10b r10e r112 r118 r11b r11e r201 r204 r207 r20a r20d r210 r213 r216 r219 r21d r222 r225 r228 r22b"
C="r103 r102 r106 r109 r10c r10f r113 r119 r11c r11f r202 r205 r208 r20b r20e r211 r214 r217 r21a r220 r223 r226 r229 r22c"
python3 room_compile.py --iso $ISO --world "$W" --out "$O" $A > "$O/compile-a.log" 2>&1 &
python3 room_compile.py --iso $ISO --world "$W" --out "$O" $B > "$O/compile-b.log" 2>&1 &
python3 room_compile.py --iso $ISO --world "$W" --out "$O" $C > "$O/compile-c.log" 2>&1 &
wait
(cd "$O" && sha256sum */room.r4rc > SHA256SUMS)
echo done

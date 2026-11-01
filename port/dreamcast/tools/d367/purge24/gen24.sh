set -euo pipefail
# gen24.sh: ch2 room objects (non-breakable ETM + room BIN pairs) to PS2 geometry. lane purge-props24
T=/root/work/lanes/purge-props24/port/dreamcast/tools
O=/root/work/lanes/purge-props24-scratch/${OUTD:-g}
mkdir -p "$O"
BRK="et0100.bin et0200.bin et1100.bin et1200.bin et1e00.bin et1f00.bin et2d00.bin et2e00.bin et2e01.bin et2f00.bin et2f01.bin et3c00.bin et0000.bin et2500.bin et1400.bin"
declare -A ETM PAIRS SRC EMP
# EMP (window panes et0000 / et2500 emptied) retired 2026-10-26 (lane windows26): the user requires glass and bars;
# the panes stay GC (GC-ASSET allowlist). Already emptied dars: ps2_objects.py --etm-restore-gc (windows26/gen26.sh).
REL=/root/work/lanes/purge-props24-scratch/rel/tree
for r in r100 r101 r105 r107; do SRC[$r]=$REL/st1/$r.dar; ETM[$r]=""; PAIRS[$r]=""; done
ETM[r10c]=""; PAIRS[r10c]=""  # BIN 0x1f extended weights: converter refuses
ETM[r10d]="et1000.bin,et1500.bin"; PAIRS[r10d]=""
ETM[r10e]="et1000.bin"; PAIRS[r10e]=""
ETM[r10f]="et2900.bin,et2901.bin,et2b00.bin"; PAIRS[r10f]=1f:1f,22:22,23:23
ETM[r111]="et0001.bin,et0300.bin,et0400.bin,et0500.bin,et0600.bin,et0700.bin,et0701.bin,et0800.bin,et0d00.bin"; PAIRS[r111]=""
ETM[r112]="et0a00.bin,et0d00.bin,et1300.bin,et2c00.bin,et2c01.bin"; PAIRS[r112]=""
ETM[r113]="et0500.bin,et0600.bin,et1a00.bin"; PAIRS[r113]=""
ETM[r11c]="et0001.bin,et0500.bin,et0700.bin,et0701.bin,et0800.bin,et1700.bin"; PAIRS[r11c]=""  # BIN 0x1f PS2 placeholder (no triangles)
ETM[r11d]="et0600.bin,et0700.bin,et0701.bin,et1000.bin,et1300.bin,et2400.bin"; PAIRS[r11d]=21:21
ETM[r11e]="et0900.bin,obm4c00.bin"; PAIRS[r11e]=20:20,23:23
ETM[r11f]="et0001.bin"; PAIRS[r11f]=1f:1f,22:22,25:25,28:28,2b:2b
ETM[r200]="et1000.bin"; PAIRS[r200]=""
for r in r10c r10d r10e; do SRC[$r]=/root/re4data/private/ch21r-20261020/st1/$r.dar; done
for r in r10f r111 r112 r113 r11c r11d r11e r11f; do SRC[$r]=/root/re4data/private/ch2data-20261018/files/st1/$r.dar; done
SRC[r200]=/root/re4data/private/ch2data-20261018/files/st2/r200.dar
cd "$T"
for r in ${ROOMS:-r10c r10d r10e r10f r111 r112 r113 r11c r11d r11e r11f r200}; do
  echo "== $r"
  a=(room --dar "${SRC[$r]}" --room "$r" --keep-larger --out "$O/$r.dar" --json "$O/$r.json")
  if [ -n "${ETM[$r]}" ]; then a+=(--etm "${ETM[$r]}"); elif [ -n "${EMPTY:-}" ] && [ -n "${EMP[$r]:-}" ]; then a+=(--etm "${EMP[$r]}"); fi
  [ -n "${PAIRS[$r]}" ] && a+=(--pairs "${PAIRS[$r]}")
  [ -n "${EMPTY:-}" ] && [ -n "${EMP[$r]:-}" ] && a+=(--etm-empty "${EMP[$r]}")
  python3 ps2_objects.py "${a[@]}" 2>&1 | tail -20 || echo "FAIL $r"
done

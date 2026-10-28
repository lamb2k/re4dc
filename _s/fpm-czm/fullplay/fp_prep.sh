#!/bin/bash
# fp_prep.sh <gdemu dir> <track03 sha256> <label> <evidence dir>   (WSL; called by fp_gate.py)
# 1. extracts the release game tree from track03 (cached by the track's sha256 under $FP_WORK),
# 2. finds the route build whose binary is the disc's 1ST_READ.BIN (FP_BUILD=<out dir> overrides the search),
# 3. builds the twin + the identity image (fp_twin.sh), 4. masters the twin and release-binary bases (fp_master.sh),
# 5. writes <evidence>/prep.json. Exit 0 only when every step and proof passed.
set -euo pipefail
G=${1:?gdemu}; TSHA=${2:?sha}; LAB=${3:?label}; EV=${4:?evidence}
here=$(cd "$(dirname "$0")" && pwd)
FP_WORK=${FP_WORK:-/root/probe/lanes-20261014/fullplay/work}
TOOL=/opt/toolchains/dc/sh-elf/bin
C=$FP_WORK/rel-${TSHA:0:16}
mkdir -p $C "$EV/_discs"
if [ ! -s $C/manifest.json ]; then
  rm -rf $C/tree
  python3 $here/fp_iso.py extract "$G/$(awk 'NR==4{print $5}' "$G/disc.gdi")" $C/tree --manifest $C/manifest.json.tmp --ipbin $C/IP.BIN
  mv $C/manifest.json.tmp $C/manifest.json
fi
BIN=$(sha256sum < $C/tree/1ST_READ.BIN | cut -c1-64)
echo "release 1ST_READ.BIN $BIN"
binsha() { $TOOL/sh-elf-objcopy -R .stack -O binary $1 /tmp/fpb-$$.bin && sha256sum < /tmp/fpb-$$.bin | cut -c1-64; rm -f /tmp/fpb-$$.bin; }
OUT=${FP_BUILD:-}
if [ -z "$OUT" ]; then
  CACHE=$FP_WORK/bincache.tsv; touch $CACHE
  # the gate's own fp* builds come last (they reproduce a release; prefer the build that made it)
  for e in $(ls -t /root/probe/lanes/route/out-*/re4dc-game.elf | grep -v /out-fp; ls -t /root/probe/lanes/route/out-fp*/re4dc-game.elf 2>/dev/null); do
    k="$e $(stat -c %Y $e)"
    s=$(awk -v k="$k" '$1" "$2==k{print $3}' $CACHE | tail -1)
    [ -n "$s" ] || { s=$(binsha $e); echo "$k $s" >> $CACHE; }
    if [ "$s" = "$BIN" ] && [ -s $(dirname $e)/stack.txt ] && [ $(wc -l < $(dirname $e)/stack.txt) -le 1 ] && grep -q 'DBG_WARP=0' $(dirname $e)/candidate.txt; then
      OUT=$(dirname $e); break
    fi
  done
fi
[ -n "$OUT" ] || { echo "fp_prep: no route build out-* (clean tree, DBG_WARP=0) has the disc's binary $BIN; set FP_BUILD" >&2; exit 2; }
[ "$(binsha $OUT/re4dc-game.elf)" = "$BIN" ] || { echo "fp_prep: $OUT is not the disc's binary" >&2; exit 2; }
for o in $C/tree/dc/*.ovl; do cmp -s $o $OUT/$(basename $o) || { echo "fp_prep: overlay $(basename $o) on the disc differs from $OUT" >&2; exit 2; }; done
echo "release build $OUT"
# FP_TWIN_EXTRA="K=V ...": extra diagnostic knobs for the twin only (e.g. WEP_TARGET_GUARD=2); the release image and
# its identity build are unchanged. Empty by default.
bash $here/fp_twin.sh $OUT $LAB ${FP_TWIN_EXTRA:-} | tee $C/twin-$LAB.txt
TW=/root/probe/lanes/route/out-fp${LAB}W
bash $here/fp_master.sh $C/tree $C/manifest.json $C/IP.BIN "$EV/_discs/twin" $TW &
P1=$!
bash $here/fp_master.sh $C/tree $C/manifest.json $C/IP.BIN "$EV/_discs/rel" &
P2=$!
wait $P1; wait $P2
python3 - "$EV/prep.json" "$OUT" "$TW" "$BIN" "$C" "$TSHA" "$C/twin-$LAB.txt" "$EV/_discs" <<'E'
import json, sys
o, out, tw, binsha, c, tsha, twinrep, discs = sys.argv[1:9]
rd = lambda p: open(p).read().strip()
json.dump(dict(release_build=out, release_binary_sha256=binsha, release_candidate=rd(out + '/candidate.txt'),
               release_tree_commit=rd(out + '/stack.txt'), twin_build=tw, twin_candidate=rd(tw + '/candidate.txt'),
               syms_release=rd(out + '/syms.txt'), syms_twin=rd(tw + '/syms.txt'), track03_sha256=tsha, cache=c,
               twin_report=rd(twinrep).splitlines(), twin_base_diff=rd(discs + '/twin/base-diff.txt').splitlines(),
               rel_base_diff=rd(discs + '/rel/base-diff.txt').splitlines()), open(o, 'w'), indent=1)
E
grep -q '^IDENTITY OK' $C/twin-$LAB.txt || { echo "fp_prep: identity proof failed" >&2; exit 1; }
echo PREP_OK

#!/bin/bash
# merchant_package.sh <work dir> [codex regcast-merchant18 dir]   (PS2_CAST_MERCHANT, lane ps2cast2 2026-10-14)
# The r102 merchant package: Codex's CH23 em18 conversion (regcast-merchant18: merchant18-c0 / -o0, built by
# ps2_cast.py) copied with r102 (and r10e) added to each descriptor's rooms, then model_registry.py with
# model-registry/ps2-merchant-ch1.json (its cast_dir names <work>/regcast-merchant18; edit it for another work dir).
# Disc files: <work>/reg-r102-m1/package/r102/registry.re4nmr -> dc/native/r102/registry.re4nmr and
# <work>/reg-r102-m1/tex/*.re4tex -> dc/tex/<first hex digit>/ (4 atlases not on the test 10 disc).
# VQ_CHROMA=W (default 3; 0 = Codex's pvrtex atlas as is): the atlas re-encoded by vq_chroma.py (chroma-weighted VQ):
# pvrtex's plain-RGB codebook turned the purple scarf tan on screen. The cast copy's texture packages, their sha256 and
# the catalog / manifest package paths are rewritten to the re-encoded files.
# Proof 2026-10-14 (VQ_CHROMA=0): 105,088 B package, heap-4 arena 113,248 B, registry.re4nmr sha256 006e00eb32156977...
set -euo pipefail
W=$1; SRC=${2:-/root/probe/codex-ch23-enemies-20261013/regcast-merchant18}
HERE=$(cd "$(dirname "$0")" && pwd); D=$HERE/..; T=$(cd "$HERE/../../../../.." && pwd)
mkdir -p "$W"; rm -rf "$W/regcast-merchant18" "$W/reg-r102-m1"
cp -a "$SRC" "$W/regcast-merchant18"
python3 - "$W/regcast-merchant18" <<'P'
import glob, json, os, sys
W = sys.argv[1]
for m in ('merchant18-c0', 'merchant18-o0'):
    p = os.path.join(W, m, 'source.json'); s = json.load(open(p))
    s['rooms'] = ['r102', 'r10d', 'r10e', 'r112']; json.dump(s, open(p, 'w'))
def fix(o):   # every other room list naming r10d (revision manifests, the overlay catalog, nested source rows) gains r102
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'rooms' and isinstance(v, list) and 'r10d' in v and 'r102' not in v: v.insert(0, 'r102'); n += 1
            else: n += fix(v)
    elif isinstance(o, list):
        for v in o: n += fix(v)
    return n
for p in sorted(glob.glob(W + '/**/*.json', recursive=True)):
    s = json.load(open(p))
    if fix(s): json.dump(s, open(p, 'w'), indent=1)
P
VQ_CHROMA=${VQ_CHROMA:-3}
MODELS=${MODELS:-$(dirname "$SRC")/models}
if [ "$VQ_CHROMA" != 0 ]; then
  for m in c0 o0; do
    tdir="$W/regcast-merchant18/merchant18-$m/ps2-v1/texture"; key=$(basename "$tdir"/*.re4tex .re4tex)
    old=$(sha256sum "$tdir/$key.re4tex" | cut -d' ' -f1)
    # vq_chroma.py needs numpy (Windows python on this host, the ps2_cast.py stage-1 convention): run it first, e.g.
    #   python vq_chroma.py <MODELS>/merchant18-c0/atlas.png <MODELS>/merchant18-c0/texture/atlas.dt <W>/vq-c0.dt --chroma 3
    [ -s "$W/vq-$m.dt" ] || python3 $HERE/vq_chroma.py "$MODELS/merchant18-$m/atlas.png" "$MODELS/merchant18-$m/texture/atlas.dt" "$W/vq-$m.dt" --chroma $VQ_CHROMA
    tmp=$(mktemp -u "$W/vq-$m-XXXXXX.re4tex")
    python3 $D/../vq_export.py --pack-existing "$W/vq-$m.dt" --package "$tmp" --material ps2cast_merchant18_$m > /dev/null
    mv -f "$tmp" "$tdir/$key.re4tex"
    new=$(sha256sum "$tdir/$key.re4tex" | cut -d' ' -f1)
    grep -rl "$old" "$W/regcast-merchant18" --include=*.json | xargs -r sed -i "s/$old/$new/g"
  done
  grep -rl "$SRC/" "$W/regcast-merchant18" --include=*.json | xargs -r sed -i "s#$SRC/#$W/regcast-merchant18/#g"
fi
cd "$T" && python3 $D/model_registry.py $D/model-registry/ps2-merchant-ch1.json "$W/reg-r102-m1" --tree "$T" --package-room 102 \
    --pack-bones 64 --wide-identity --source-normal-length --ch23-facts > "$W/reg-r102-m1.log" 2>&1 || { tail -20 "$W/reg-r102-m1.log"; exit 1; }
sha256sum "$W/reg-r102-m1/package/r102/registry.re4nmr" "$W"/reg-r102-m1/tex/*

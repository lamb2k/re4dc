#!/bin/bash
# cast-ps2-25 r18: both compiled Leon digests (mesh, skeleton side) for one build's hand-pack header + arm dir.
# qsk.sh <out dir of build> <PS2_LEON_DIR>
set -euo pipefail
O=${1:?out}; A=${2:?arm}
L=/root/work/lanes/cast-ps2-25; S=$L/_s/r18/qsk; mkdir -p $S
Q=$L/port/dreamcast/tools/d367/gc_port23/qualify_actor_compiled.py
sed -e 's#for(auto b:row.digest.bytes)printf("%02x",b);puts("");#for(auto b:row.digest.bytes)printf("%02x",b);putchar(32);AssetDescription sk;assert(describe_checked(gcasset_compiled_actor.layout_asset,\&sk));for(auto b:sk.digest.bytes)printf("%02x",b);puts("");#' \
    -e "s#^HERE = .*#HERE = Path('$L/port/dreamcast/tools/d367/gc_port23')#" $Q > $S/q.py
grep -q layout_asset $S/q.py
H=$O/obj/leon_hands/ps2leon_runtime_handpack.h
printf 'COARSE_LEON=1\nACTOR_TRANSACTION=1\nLEON_HAND_PACK=1\nLEON_LOD=0\nLEON_HAND_PACK_HDR=%s\nPS2_LEON_DIR=%s\n' $H $A > $S/profile.txt
sh(){ sha256sum "$1" | cut -c1-64; }
python3 $S/q.py --profile $S/profile.txt --profile-sha $(sh $S/profile.txt) --runtime-sha $(sh $H) --hair-sha $(sh $A/ps2leon_hair_runs.h) | python3 -c "import json,sys;print(json.load(sys.stdin)['geometry_sha256'])"

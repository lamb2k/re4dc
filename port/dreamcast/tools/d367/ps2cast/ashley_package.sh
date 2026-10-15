#!/bin/bash
# ashley_package.sh <work dir> [stage]   (PS2_ASHLEY, lane ps2cast 2026-10-14; offline: nothing reaches a disc by itself)
# Ashley's r117 room package from her PS2 model: three descriptors, one per cSubAshley::setHand set (ashley11 = hands
# 0xC/0xF, ashley11-h1 = 0xD/0x10, ashley11-h3 = 0xE/0xF); the chunks they share are stored once. Stages (default: all
# WSL stages; a missing Windows stage prints its commands):
#   win1  (Windows Python: numpy / PIL) for H in 0 1 3: ps2_ashley.py convert <W>/conv<S> --hands H
#         (<S> = "" / -h1 / -h3)                     -> PS2 mesh on 64 draw slots + atlas (+ atlas-rgba.png)
#   native (WSL)  ps2_cast_native.sh <W>/conv<S>     -> runtime header, VQ atlas package (the same atlas for all three)
#   win2  (Windows Python) per <S>: ps2_cast.py finish <W>/conv<S>;
#           ps2_mask_runs.py <W>/conv<S> <pl11 GC drs> 7 0xB 1 <W>/mask<S>-head
#           ps2_mask_runs.py <W>/conv<S> <pl11 GC drs> 6 8 2 <W>/mask<S>-hair
#           ps2_mask_runs.py <W>/conv<S> <pl11 GC drs> 9 5 3 <W>/mask<S>-extra9 --atlas-rgba <W>/conv<S>/atlas-rgba.png --size 128x128
#         then ps2_cast.py regcast <W>/regcast-ashley11 ps2-ashley <W>/conv <W>/conv-h1 <W>/conv-h3
#   registry (WSL) model_registry.py model-registry/ps2-ashley-r117.json (its cast_dir / mask_runs name
#         /root/probe/lanes-20261014/ps2cast/ashley with conv4 / mask-*: edit them for another work dir) --package-room 117
#         --pack-bones 64 --slots ... -> <W>/reg-r117/package/r117/registry.re4nmr + tex/
#   hosttest (WSL) model_registry_pack_test.py --slots on that package (9 cases + two readers without the rules)
#   prep  (WSL) prep_archive.sh pl11 <pl11 GC drs> <release em/pl11.drs> <W>/pl11prep -> texture-prepared em/pl11.drs
# Disc files (recipe delta, with PS2_ASHLEY=1|2): dc/native/r117/registry.re4nmr, <W>/reg-r117/tex/*.re4tex
# (dc/tex/<first hex digit>/), em/pl11.drs from <W>/pl11prep.
# Proof 2026-10-14: registry.re4nmr 229,952 B (c1e2d47f; heap-4 arena 239,656 B), prepared pl11.drs 2,214,112 B
# (596b29aa) whose resident body is 828,384 B (the release archive's 1,069,792 B: -241,408 B), all 25 pl11 GC textures
# already on the release disc. Modelled r117 heap-4 change: +239,656 - 241,408 = -1,752 B (file sizes; not measured).
set -euo pipefail
W=$1; STAGE=${2:-all}
HERE=$(cd "$(dirname "$0")" && pwd); D=$HERE/..; TOOLS=$D/..; T=$(cd "$HERE/../../../../.." && pwd)
GCDRS=${PL11_GC_DRS:-/root/probe/codex-ashley-bone-audit-20261014/pl11-GC.drs}
REL=${PL11_RELEASE_DRS:-/root/probe/lanes-20261014/t11/pkgtree/em/pl11.drs}
win() { echo "run on Windows: $*"; }
case $STAGE in all|native)
  for s in "" -h1 -h3; do
    [ -s "$W/conv$s/mesh.json" ] || { win "python ps2_ashley.py convert $W/conv$s --hands ${s#-h}"; exit 1; }
    bash "$TOOLS/ps2_cast_native.sh" "$W/conv$s"
  done ;; esac
case $STAGE in all|registry)
  for s in "" -h1 -h3; do for m in head hair extra9; do
    [ -s "$W/mask$s-$m/mask-runs.json" ] || { win "the win2 stage (ps2_cast.py finish / regcast, ps2_mask_runs.py)"; exit 1; }
  done; done
  rm -rf "$W/reg-r117"
  (cd "$T" && python3 "$D/model_registry.py" "$D/model-registry/ps2-ashley-r117.json" "$W/reg-r117" --tree "$T" --package-room 117 \
      --pack-bones 64 --wide-identity --source-normal-length --ch23-facts --slots > "$W/reg-r117.log" 2>&1) || { tail -20 "$W/reg-r117.log"; exit 1; }
  sha256sum "$W/reg-r117/package/r117/registry.re4nmr" "$W"/reg-r117/tex/* ;; esac
case $STAGE in all|hosttest) rm -rf "$W/packtest"
  python3 "$D/model_registry_pack_test.py" "$W/reg-r117/package/r117/registry.re4nmr" "$W/packtest" --room 117 --slots ;; esac
case $STAGE in all|prep) bash "$HERE/prep_archive.sh" pl11 "$GCDRS" "$REL" "$W/pl11prep" ;; esac

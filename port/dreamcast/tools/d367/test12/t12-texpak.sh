#!/bin/bash
# t12-texpak.sh (WSL): the test 12 dc/tex.pak (t11-fix.py data set t12tex), deterministic, built on ext4.
#   base   tex-t11.pak            test 11 (GC bake textures + Leon's 2x packages), sha256 1582e5c5
#   + fx   tex-t11-ps2lib-d5.pak  PS2 effect library pictures under the GameCube keys (FX_PS2_PACK / PAL4): fx12's set
#                                 plus (lane vram12 D5, 10-15) the swizzled / 8 bpp PS2 pictures (40 ids that were
#                                 NOT_CONVERTED) and the enemies' own EFFs (em11..em35); fx_ps2_pack.py pack of
#                                 tex-t11.pak with ps2lib (was fx12's tex-t11-ps2lib.pak 653e622b)
#   + vram tex-vr12-d5.pak        blackgc14vl: r101's 12 large PS2 world textures + Leon's atlas ec255e66-76812316 as VQ
#                                 (Leon VQ: user decision 2026-10-14 23:58) + (D5) the 52 r101 16-bit twiddled source
#                                 textures >= 64x64 (not effect pictures) as full-codebook VQ (614,400 -> 183,296 B of VRAM,
#                                 PSNR 29.0..50.2 dB; vram/vq_pak.py, keys in vram/vq16-r101.txt)
#   + merchant 4 texture keys     ps2lib/cast/r102/merchant-em18/dc/tex (PS2_CAST_MERCHANT), packed instead of loose
#   + items tex-items.pak         lane items (24526dfb, ps2_items-v2): tex-t11.pak + the PS2 pickup / debris packages
#                                 (re4-assets-private/items-20261014, sha256 in SHA256SUMS)
#   + acc12 8 texture keys        lane acc12 (fdc16424): PS2 Ganado accessory pictures, ps2lib/cast/common/acc12/tex,
#                                 packed instead of loose
#   then tex_wrapsafe.py marks the uniform 16-bit packages (TEX_WRAP_SAFE=1).
# tex_merge.py refuses a key two inputs change differently. Output: $OUT (default /root/probe/lanes-20261014/t12rc/data).
# Also $OUT/resident.bin (dc/resident.bin, ROOM_RESIDENT=1): vram/resident_keys.py pack of vram/resident/r*.tsv.
set -euo pipefail
D=$(cd "$(dirname "$0")/.." && pwd)
OUT=${OUT:-/root/probe/lanes-20261014/t12rc/data}
NAME=${T12_PAK_NAME:-tex-t12d}  # not $NAME: WSL sets NAME to the host name
BASE=/root/probe/lanes-20261014/t11/data/tex-t11.pak
FX=${FX:-/root/probe/lanes-20261014/vram12/data/tex-t11-ps2lib-d5.pak}
VR=${VR:-/root/probe/lanes-20261014/vram12/data/tex-vr12-d5.pak}
MER="/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/cast/r102/merchant-em18/dc/tex"
ITM="/mnt/c/Game Dev/Emulators/re4-assets-private/items-20261014/tex-items.pak"
ACC="/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/cast/common/acc12/tex"
mkdir -p $OUT
sha256sum $BASE $FX $VR "$ITM" | cut -c1-16 | paste -sd' '
python3 $D/texpack.py "$MER" $OUT/tex-merchant.pak
python3 $D/texpack.py "$ACC" $OUT/tex-acc12.pak
python3 $D/tex_merge.py $BASE $OUT/$NAME-merge.pak $FX $VR $OUT/tex-merchant.pak "$ITM" $OUT/tex-acc12.pak
python3 $D/tex_wrapsafe.py $OUT/$NAME-merge.pak $OUT/$NAME.pak > $OUT/ws-$NAME.txt
tail -1 $OUT/ws-$NAME.txt
python3 $D/texpack.py --verify $OUT/$NAME.pak
rm -f $OUT/$NAME-merge.pak $OUT/tex-merchant.pak $OUT/tex-acc12.pak
python3 $D/vram/resident_keys.py pack $OUT/resident.bin $D/vram/resident/r*.tsv
sha256sum $OUT/$NAME.pak $OUT/resident.bin

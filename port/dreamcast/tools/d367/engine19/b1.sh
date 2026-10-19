set -euo pipefail
T=/root/work/lanes/engine19
B=/root/work/lanes/engine19-base
export K=/root/probe/lanes-20261019/engine19/k
mkdir -p "$K"
RC=/root/re4data/private/rc19-20261019
R="r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r10c r10d r10e r10f r111 r112 r113 r117 r118 r119 r11a r11b r11c r11d r11e r11f r200 r201 r202 r203 r204 r205 r206 r207 r208 r209 r20a r20b r20c r20d r20e r20f r210 r211 r212 r213 r214 r215 r216 r217 r218 r219 r21a r21b r21d r220 r221 r222 r223 r224 r225 r226 r227 r228 r229 r22a r22b r22c"
if [ ! -f "$RC/MANIFEST.tsv" ]; then
  mkdir -p "$RC"
  python3 $T/port/dreamcast/tools/enginebake/room_compile.py --iso /root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso --out "$RC" $R > "$RC/compile.log"
  (cd "$RC" && sha256sum */room.r4rc > SHA256SUMS)
  P="/mnt/c/Game Dev/Emulators/re4-assets-private/rc19-20261019"
  mkdir -p "$P" && cp -r "$RC"/. "$P"/
fi
[ -d $B ] || git -C $T worktree add -q --detach $B origin/t15/int
(cd $B && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
(cd $T && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
PE=/root/re4data/private/ps2enemy-ch2-20261016
eval "$(grep '^CH2REC=' $T/port/dreamcast/tools/d367/ch2/ch2-build.sh)"
T18="MOVIE_AUDIO_PRIME=1 ROOM_LEFTOVER_FIT=1 PS2_WORLD_SOURCE_TEX_VQ=1 LEON_SKIN_SLOTS=2 ROUTE_SOON_RETURN=1 LEON_HEADLESS=1 LEON_HEADLESS_DIR=/root/re4data/private/garr18-head-20261019 LEON_CLOTH_DRAWN=1 FX_MIST_PS2=1 PS2_HDR_SETS=128"
echo "$T18" > $K/t18-knobs.txt
for a in "$@"; do case $a in
  k) T=$B LP=e19k CH2="$CH2REC $T18" bash $B/port/dreamcast/tools/d367/ch2/ch2-build.sh rP | cut -c1-120 ;;
  x) T=$T LP=e19x CH2="$CH2REC $T18" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP | cut -c1-120 ;;
  e) T=$T LP=e19e CH2="$CH2REC $T18 ENGINE_PREVIEW=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP | cut -c1-120 ;;
  eW) T=$T LP=e19e XON="$T18 ENGINE_PREVIEW=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  kW) T=$T LP=e19k XON="$T18" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  eT) T=$T LP=e19e XON="$T18 ENGINE_PREVIEW=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rT | cut -c1-120 ;;
  kT) T=$T LP=e19k XON="$T18" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rT | cut -c1-120 ;;
  eM) T=$T LP=e19e XON="$T18 ENGINE_PREVIEW=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh mW | cut -c1-120 ;;
  v) T=$T LP=e19v XON="$T18 PS2_PVS=1 PS2_PVS_DEFAULT=2 ENGINE_VIS_LOG=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  kC) T=$T LP=e19kc XON="$T18 ALIVE_CAP_LOG=1 R101_CAP_LOG=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  eC) T=$T LP=e19ec XON="$T18 ENGINE_PREVIEW=1 ALIVE_CAP_LOG=1 R101_CAP_LOG=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  w) T=$T LP=e19w CH2="$CH2REC $T18 ENEMY_VIS_CULL=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP | cut -c1-120 ;;
  wW) T=$T LP=e19w XON="$T18 ENEMY_VIS_CULL=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  wT) T=$T LP=e19w XON="$T18 ENEMY_VIS_CULL=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rT | cut -c1-120 ;;
  dW) T=$T LP=e19d XON="$T18 ENEMY_VIS_CULL=1 ENEMY_VIS_DEBUG=1 PS2_PVS=1 PS2_PVS_DEFAULT=2 ENGINE_VIS_LOG=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  kM) T=$T LP=e19k XON="$T18" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh mW | cut -c1-120 ;;
  wM) T=$T LP=e19w XON="$T18 ENEMY_VIS_CULL=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh mW | cut -c1-120 ;;
  kS) T=$T LP=e19ks XON="$T18 PACE_MODE=off ENEMY_VIS_DEBUG=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  wS) T=$T LP=e19ws XON="$T18 PACE_MODE=off ENEMY_VIS_CULL=1 ENEMY_VIS_DEBUG=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  wK) T=$T LP=e19wk XON="$T18 ENEMY_VIS_CULL=1 KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 WARP_JUMP=1" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120 ;;
  *) echo "arm? $a" ;;
esac; done

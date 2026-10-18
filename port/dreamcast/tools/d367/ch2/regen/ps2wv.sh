# ps2wv.sh <room> <tree> <variant> [extra r4im args...] (Git Bash): PS2 world recipe variants to find a lost recipe by sha
set -euo pipefail
R=${1:?room}; TREE=${2:?tree}; V=${3:?variant}; shift 3
LW=/root/probe/lanes-20261017r/ch2regen
L=//wsl.localhost/Ubuntu-24.04$LW
W=$LW/worlds/$TREE-$V; MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- mkdir -p $W
X="C:/Game Dev/Emulators/re4-assets-private/ps2rooms-20260930/inputs/$R"
LIT=()
case $V in
  all) MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- python3 $LW/$TREE/port/dreamcast/tools/gc_room_lit.py $R $W/$R-gc-lit.json --iso $LW/iso/re4_debug_disc1.iso --all > /dev/null; LIT=(--gc-lit "//wsl.localhost/Ubuntu-24.04$W/$R-gc-lit.json") ;;
  cut0) MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- python3 $LW/$TREE/port/dreamcast/tools/gc_room_lit.py $R $W/$R-gc-lit.json --iso $LW/iso/re4_debug_disc1.iso > /dev/null; LIT=(--gc-lit "//wsl.localhost/Ubuntu-24.04$W/$R-gc-lit.json") ;;
  nolit) ;;
esac
out="//wsl.localhost/Ubuntu-24.04$W/$R-ps2"; MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- rm -rf "${W:?}/$R-ps2"
python "$L/$TREE/port/dreamcast/tools/ps2_room_r4im.py" $R "$X" "$out" --lights 0,5 --color-light ps2 "${LIT[@]}" --lod-uv-guard 0.002 --vertex-alpha tr4 --cutout-max-alpha 224 "$@" > "//wsl.localhost/Ubuntu-24.04$W/$R-ps2.log" 2>&1 || { tail -5 "//wsl.localhost/Ubuntu-24.04$W/$R-ps2.log"; exit 1; }
sha256sum "$out"/ps2-world.re4mesh "$out"/ps2-world.r4pw "$out"/ps2-world.ids | cut -c1-16

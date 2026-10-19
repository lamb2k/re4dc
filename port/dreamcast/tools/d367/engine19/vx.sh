set -euo pipefail
# vx.sh <tag> <room> [ENV=VAL ...]: one VIS parameter experiment into engine19-scratch/vx/<tag>
TAG=${1:?}; ROOM=${2:?}; shift 2
O=/root/work/lanes/engine19-scratch/vx/${TAG:?}
mkdir -p "$O"
cd /root/work/lanes/engine19/port/dreamcast/tools/enginebake
env "$@" python3 room_compile.py --iso /root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso --world /root/work/lanes/engine19-scratch/wv --threads 8 --out "$O" "$ROOM" > "$O/log" 2>&1
python3 -c "import json,sys;r=json.load(open(sys.argv[1]));v=r['vis'];print(sys.argv[2],r['file_bytes'],v)" "$O/$ROOM/report.json" "$TAG"

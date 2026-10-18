# vq.sh <room> <log>...: VQ of the room's textures (room + PS2 world + pairs) that the runs loaded
# (vq_native_ui --model-min-bytes 32768, texture-vq-rooms.sh's room rule; r117 lane vq.sh + the PS2 world tex)
set -e
R=$1; shift
T=/root/probe/lanes-20261013/ch22/port/dreamcast/tools
W=/root/probe/lanes-20261013/ch22w/rooms
cd $W
rm -rf vqsrc-$R tex-$R-vq
mkdir vqsrc-$R
for d in tex-$R $R-ps2/tex pairs-$R; do [ -d $d ] && for f in $d/*.re4tex; do ln -sf $W/$f vqsrc-$R/; done; done
LOGS=()
for L in "$@"; do LOGS+=(--log "$L"); done
python3 $T/vq_native_ui.py --textures vqsrc-$R "${LOGS[@]}" --output tex-$R-vq --previews tex-$R-vq/previews --model-min-bytes 32768 | tail -3
ls tex-$R-vq/*.re4tex | wc -l

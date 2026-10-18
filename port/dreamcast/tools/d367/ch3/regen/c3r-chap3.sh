set -euo pipefail
# c3r-chap3.sh COMMIT: castle chap3.sh (chap03.dat textures + vq_native_ui) and pairs2.sh (pairs-c31) replay
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
C=${1:?}; T=$L/trees/$C/port/dreamcast/tools
TAG=$(echo "$C" | tr '/' '_')
W=$L/extra/chap3-$TAG; rm -rf "${W:?}"; mkdir -p "$W"
python3 "$S/c3r_gcx.py" "$ISO" "$W/src" ss/eng/chap03.dat > /dev/null
echo ss/eng/chap03.dat > "$W/m.txt"
( cd /tmp && PYTHONDONTWRITEBYTECODE=1 python3 "$T/prepare_native_ui.py" "$W/src" "$W/m.txt" "$W/tex-chap03" | tail -1 )
E="/mnt/c/Flycast-Evidence/re4-dreamcast/castle-20261015/h-cx32b/scenarios/cx-r206-c32a-01/capture/run-output.txt"
tr -d '\r' < "$E" > "$W/r206.log"
PV=/root/work/kos-re4dc-d336/utils/pvrtex/pvrtex; ls -la "$PV" || true
( cd /tmp && PYTHONDONTWRITEBYTECODE=1 python3 "$T/vq_native_ui.py" --textures "$W/tex-chap03" --log "$W/r206.log" --output "$W/tex-chap03-vq" \
  --model-min-bytes 8192 --pvrtex "$PV" --previews "$W/prev" 2>&1 | tail -2 ) || true
O=$L/extra/pairs-c31-$TAG; rm -rf "${O:?}"
E="/mnt/c/Flycast-Evidence/re4-dreamcast/castle-20261015/h-cxt12c/scenarios"
( cd /tmp && nice python3 "$T/d367/pairs_from_log.py" --iso "$ISO" --output "$O" \
  --log "$E/cx-r208-t12b-01/capture/run-output.txt" --log "$E/cx-r201-t12b-01/capture/run-output.txt" \
  --file em/em1a.drs --file em/em1b.drs --file em/em14.drs --file st2/r208.das --file st2/r201.das --file em/pl11.drs --file em/pl00.drs --file etc/core.das 2>&1 | tail -3 ) || true
ls "$O" | head

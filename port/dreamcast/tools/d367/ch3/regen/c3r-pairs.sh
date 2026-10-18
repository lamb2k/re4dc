set -euo pipefail
# c3r-pairs.sh COMMIT: castle pairs3.sh (pairs-c32) + pairs4.sh (pairs-c33) replay with COMMIT's pairs_from_log.py
L=/root/probe/lanes-20261018/ch3regen
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
C=${1:?}; T=$L/trees/$C/port/dreamcast/tools/d367
[ -d "$L/trees/$C" ] || git -C "$L/git" worktree add -q --detach "$L/trees/$C" "$C"
TAG=$(echo "$C" | tr '/' '_')
E=/mnt/c/Flycast-Evidence/re4-dreamcast/castle-20261015
O=$L/extra/pairs-c32-$TAG; rm -rf "${O:?}"
A=(); for l in h-cx32b/scenarios/cx-r205-c32a-01 h-cx32b/scenarios/cx-r209-c32a-01 h-cx32b/scenarios/cx-r20a-c32a-01 h-cx32b/scenarios/cx-r20b-c32a-01 h-cx32b/scenarios/cx-r206-c32a-01 h-cx32c/scenarios/cx-r20e-c32c-01; do A+=(--log "$E/$l/capture/run-output.txt"); done
F=(); for f in st2/r205.das st2/r209.das st2/r20a.das st2/r20b.das st2/r20e.das st2/r206.das em/em2d.drs em/em25.drs em/em3c.drs em/em19.drs em/em23.drs em/em18.drs em/em22.drs em/em1a.drs em/em1b.drs em/em14.drs em/pl11.drs em/pl00.drs etc/core.das; do F+=(--file "$f"); done
( cd /tmp && nice python3 "$T/pairs_from_log.py" --iso "$ISO" --output "$O" "${A[@]}" "${F[@]}" 2>&1 | tail -2 ) || true
tr -d '\r' < "$E/h-cx32g/scenarios/cx-r206-g32a-01/capture/run-output.txt" > "$L/extra/g32-206.txt"
O=$L/extra/pairs-c33-$TAG; rm -rf "${O:?}"
( cd /tmp && nice python3 "$T/pairs_from_log.py" --iso "$ISO" --output "$O" --log "$L/extra/g32-206.txt" \
  --file st2/r206.das --file em/em11.drs --file em/pl11.drs --file st2/r20d.das --file etc/core.das 2>&1 | tail -2 ) || true

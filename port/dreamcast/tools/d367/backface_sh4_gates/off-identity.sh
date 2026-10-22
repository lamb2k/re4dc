#!/bin/bash
# MAIN-ALLOCATED OFF gate: root approved 16GiB unit / dedicated2GiB build cap.
# Main must keep its aggregate2GiB output monitor active; this script is no budget waiver.
set -euo pipefail
tree=/root/probe/codex-backface-sh4zam
expected_source=8ddb0e228f46ea21c191b31b8a579eb1b27fbc33
base=/root/probe/lanes/route/out-rr64a28a7rP
outroot=/root/probe/codex-backface-sh4zam-builds
programs=/root/probe/codex-backface-sh4zam-programs
label=bfs4idP
out=$outroot/out-$label
program=$programs/candidate-route$label
expected=97beeb54a66f787bc5c4c40159f922bb204c94a2fcec5103ee92cb4df505e723
candidate_pin=3d772ff93dcd104d76a18ba1200a5e2f8c9d2ce8b93b8ae59d6e6704225634e4
[ "$(git -C "$tree" rev-parse HEAD)" = "$expected_source" ] || { echo 'source moved; root reviews a NEW source pin first' >&2; exit 1; }
[ "$(sha256sum "$base/candidate.txt" | cut -d' ' -f1)" = "$candidate_pin" ]
for path in "$tree" "$outroot" "$programs" "$out" "$program"; do
 [ "$(realpath -m "$path")" = "$path" ] || { echo "alias/containment refused: $path" >&2; exit 1; }
done
[ "$out" = /root/probe/codex-backface-sh4zam-builds/out-bfs4idP ]
[ "$program" = /root/probe/codex-backface-sh4zam-programs/candidate-routebfs4idP ]
[ ! -e "$out" ] && [ ! -L "$out" ] && [ ! -e "$program" ] && [ ! -L "$program" ] || { echo 'preserve existing output/program label; no retry' >&2; exit 1; }
read -r -a knobs < "$base/candidate.txt"
mkdir -p "$outroot" "$programs"
exec 7>"$outroot/backface-root-tree.lock"
flock -n 7 || { echo 'root tree build lease occupied' >&2; exit 1; }
export SOURCE_DATE_EPOCH=1760000000
bash /root/probe/d367-buildslot.sh env TREE="$tree" ROUTE_OUT_ROOT="$outroot" ROUTE_PROGRAMS_DIR="$programs" ROUTE_PROGRAMS_JSON= \
 bash "$tree/port/dreamcast/tools/d367/route/route-build.sh" "$label" "${knobs[@]}" CPU_BACKFACE=0 ACTOR_BACKFACE=0 BACKFACE_CENSUS=0
[ -f "$out/missing.txt" ] && [ ! -s "$out/missing.txt" ]
for knob in CPU_BACKFACE ACTOR_BACKFACE BACKFACE_CENSUS; do grep -qx "$knob=0" "$out/resolved-knobs.txt"; done
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$out/re4dc-game.elf" "$outroot/patched-off.bin"
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$base/re4dc-game.elf" "$outroot/int64a-off.bin"
[ "$(sha256sum "$outroot/int64a-off.bin" | cut -d' ' -f1)" = "$expected" ]
cmp "$outroot/int64a-off.bin" "$outroot/patched-off.bin"
for file in "$base"/*.ovl; do cmp "$file" "$out/${file##*/}"; done
sha256sum "$outroot/int64a-off.bin" "$outroot/patched-off.bin" > "$outroot/full-program-identity.sha256"
echo 'FULL rP objcopy/overlay identity PASS; no staged image or guest was created'

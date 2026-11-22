#!/bin/bash
# room_capture.sh: how a room capture of the old game is made for the engine's room bake (lane eng-rec1).
#
#   room_capture.sh build   build the capture image (WSL): the release recipe of tools/d367/test15/t15-build.sh plus
#                           the logic capture (M1_FRAME_CAPTURE=3: bench/r3_capture.hpp, r3_guest.inc,
#                           r3_inputs.inc) and the warp rig (DBG_WARP=1), from this tree, objects in $OUT (RAM)
#   room_capture.sh disc    stage the capture disc from the pristine disc tree by hard links (the pristine tree is
#                           never written): track03.iso with /dc/warp.txt and /dc/padscript.txt redirected to LBAs
#                           400 and 420 of track01, the track01 template, the zero filler track02, base.json, and the
#                           image's symbols (control block, player, model managers) -> $DEST/capbase
#   then, from Windows:     py tools/engine/room_capture.py <room> <slot> --warp <warp.txt> --out <dir>   (one run a room)
#
# The old game is run as it is: a recorder and a reference, never changed or tuned. The capture records 300
# consecutive ticks of the room once 300 pictures have passed in it (r3_guest.inc), the host acknowledging each.
# Control (the check that a capture belongs to its room): bake/room_bake.py --controls bakes r100 from another
# room's capture and must be refused (native_pack.build: "logic discontinuity", the LOG3 room differs).
#
# Environment: TREE (this worktree), OUT (default /dev/shm/eng-rec1), DEST (default /mnt/e/RE4DC-Lanes/eng-rec1),
# PRISTINE (default the eng-bench pristine tree), STAGE (default /root/work/lanes/eng-rec1-stage: same file system
# as PRISTINE, for the hard links), JOBS (default 4).
set -euo pipefail
TREE=${TREE:-$(cd "$(dirname "$0")/../../../.." && pwd)}
OUT=${OUT:-/dev/shm/eng-rec1}
DEST=${DEST:-/mnt/e/RE4DC-Lanes/eng-rec1}
PRISTINE=${PRISTINE:-/root/work/lanes/eng-bench/.m1/pristine}
PRISTINE_IP=${PRISTINE_IP:-/root/work/lanes/eng-bench/.m1/pristine-ip.bin}
STAGE=${STAGE:-/root/work/lanes/eng-rec1-stage}
JOBS=${JOBS:-4}
LP=roomcap
BIN=/opt/toolchains/dc/sh-elf/bin

build() {
    cd "$TREE"
    export T=$TREE ROUTE_OUT_ROOT="$OUT" ROUTE_PROGRAMS_JSON="" ROUTE_PROGRAMS_DIR="$OUT/programs"
    export K=$OUT/k LP JOBS MAKEFLAGS=-j$JOBS
    mkdir -p "$K" "$ROUTE_PROGRAMS_DIR"
    . port/dreamcast/tools/d367/rr/recipe.conf
    export CH2
    sed '/^b() {/,$d' port/dreamcast/tools/d367/test15/t15-build.sh > "$K/capture-flags.sh"
    . "$K/capture-flags.sh"
    export TREE
    bash port/dreamcast/tools/d367/route/route-build.sh $LP $F $LOOK $BASE $T13 $T14 $T15REC $CH2 \
        M1_FRAME_CAPTURE=3 IMAGE_PAD_BYTES=0 $WP > "$K/$LP.log" 2>&1 || { tail -30 "$K/$LP.log" | cut -c1-250; exit 1; }
    cat "$OUT/out-$LP/elf.sha256"
}

disc() {
    cd "$TREE"
    local o=$OUT/out-$LP base=$DEST/capbase
    test -s "$o/re4dc-game.elf"
    rm -rf "${STAGE:?}"; mkdir -p "$STAGE/tree" "$STAGE/t1" "$base"
    cp -al "$PRISTINE/." "$STAGE/tree/"
    for f in warp.txt padscript.txt w11.txt qa-menu.txt 1ST_READ.BIN; do rm -f "$STAGE/tree/dc/$f" "$STAGE/tree/$f"; done
    $BIN/sh-elf-objcopy -R .stack -O binary "$o/re4dc-game.elf" "$STAGE/tree/1ST_READ.BIN"
    for f in "$o"/*.ovl; do rm -f "$STAGE/tree/dc/${f##*/}"; cp "$f" "$STAGE/tree/dc/"; done
    for name in warp.txt padscript.txt; do head -c 8192 /dev/zero > "$STAGE/tree/dc/$name"; done
    genisoimage -quiet -C 0,45000 -G "$PRISTINE_IP" -r -J -l -input-charset iso8859-1 -V RE4DCROOM -o "$STAGE/track03.iso" "$STAGE/tree"
    local fp=port/dreamcast/tools/d367/fullplay/fp_iso.py
    python3 "$fp" redirect "$STAGE/track03.iso" /dc/warp.txt 400 8192
    python3 "$fp" redirect "$STAGE/track03.iso" /dc/padscript.txt 420 8192
    touch "$STAGE/t1/README.TXT"
    genisoimage -quiet -G "$PRISTINE_IP" -V RE4DCLD -o "$base/track01-template.iso" "$STAGE/t1"
    truncate -s 1241088 "$base/track01-template.iso"
    head -c 710304 /dev/zero > "$base/track02.raw"
    mv "$STAGE/track03.iso" "$base/track03.iso"
    printf '%s\n' '{"warp_lba":400,"pad_lba":420,"fixture_bytes":8192,"gdi":"3\n1 0 4 2048 track01.iso 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2048 track03.iso 0\n"}' > "$base/base.json"
    # symbols the collector reads: the capture control block, the player, the model managers walked for the props
    $BIN/sh-elf-nm "$o/re4dc-game.elf" | awk '$3 ~ /^_(m1r3_control|pPL|ObjMgr|EmMgr|ItemMgr|pG)$/ {print substr($3,2), $1}' > "$base/symbols.txt"
    cp "$o/elf.sha256" "$base/elf.sha256"
    (cd "$TREE" && git rev-parse HEAD) > "$base/tree-commit.txt"
    sha256sum "$base/track03.iso" | cut -d' ' -f1 > "$base/track03.sha256"
    rm -rf "${STAGE:?}"
    cat "$base/symbols.txt" "$base/elf.sha256"
}

case "${1:-}" in
    build) build ;;
    disc) disc ;;
    *) sed -n '2,20p' "$0"; exit 2 ;;
esac

#!/bin/bash
set -euo pipefail
TREE=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=${1:?Pass a new owned output directory}
test ! -e "$OUT"
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
DC="$TREE/port/dreamcast"
SDK="$DC/tools/d367/backface_sh4zam_fused"
CC=${SH4_CC:-/opt/toolchains/dc/sh-elf/bin/sh-elf-gcc}
CXX=${SH4_CXX:-/opt/toolchains/dc/sh-elf/bin/sh-elf-g++}
LD=${SH4_LD:-/opt/toolchains/dc/sh-elf/bin/sh-elf-ld}
EARLY_CLIP=${BACKFACE_EARLY_CLIP:-0}
case "$EARLY_CLIP" in 0|1) ;; *) echo 'BACKFACE_EARLY_CLIP must be 0 or 1' >&2; exit 2 ;; esac
ASM_FLAGS=()
CALLER_FLAGS=()
if [[ "$EARLY_CLIP" == 1 ]]; then
    ASM_FLAGS+=(-DSHZ_STRIP_EARLY_CLIP=1)
    CALLER_FLAGS+=(--early-clip)
fi
python3 "$SDK/materialize.py" --output "$OUT/sdk" --receipt "$OUT/sdk-receipt.json"
(
    exec 9>"${D367_BUILD_LOCK:-/root/probe/d367-build2.lock}"
    flock -x 9
    exec 8>"$TREE/.backface-kernel-build.lock"
    flock -x 8
    python3 "$DC/tools/d367/backface_sh4zam_sdk/generate.py" --check --compiler "$CXX" --receipt "$OUT/arithmetic-receipt.json"
    python3 "$SDK/check_area.py" --overlay "$OUT/sdk"
    "$CC" -m4-single -ml -O2 "${ASM_FLAGS[@]}" -c "$OUT/sdk/source/shz_strip.S" -o "$OUT/kernel-trace0.o"
    python3 "$SDK/check_area.py" --overlay "$OUT/sdk"
    "$CC" -m4-single -ml -O2 "${ASM_FLAGS[@]}" -DSHZ_STRIP_TRACE=1 -DSHZ_STRIP_TRACE_CALLBACK=_re4dc_backface_sh4_trace -c "$OUT/sdk/source/shz_strip.S" -o "$OUT/kernel-trace1.o"
    "$CXX" -m4-single -ml -O2 -std=gnu++17 -I"$OUT/sdk/include" -fno-fast-math -ffp-contract=fast -c "$OUT/sdk/source/shz_strip.cpp" -o "$OUT/sdk-walk.o"
    for t in 0 1; do
        "$LD" -EL -Ttext=0x100000 --entry=_shz_strip_walk_sq --defsym=_re4dc_backface_sh4_trace=0x700000 "$OUT/sdk-walk.o" "$OUT/kernel-trace$t.o" -o "$OUT/walk-trace$t.elf"
    done
    python3 "$DC/tools/d367/backface_sh4_kernel/build_oracle.py" --output "$OUT"
    D367_SLOT_HELD=1 BACKFACE_ACTOR_OUTPUT="$OUT/actor-dispatch" BACKFACE_SDK_INCLUDE="$OUT/sdk/include" python3 "$DC/tools/d367/backface_sh4_actors/check_actor_dispatch.py"
)
python3 "$DC/tools/d367/backface_sh4_kernel/object_test.py" --objects "$OUT" --report "$OUT/sdk-kernel-controls.json"
python3 "$SDK/caller_test.py" --objects "$OUT" --report "$OUT/sdk-caller-controls.json" "${CALLER_FLAGS[@]}"
python3 "$SDK/fused_test.py" --objects "$OUT" --report "$OUT/sdk-fused-controls.json"
python3 "$SDK/sq_guard_test.py" --objects "$OUT" --report "$OUT/sdk-sq-guard-controls.json"

#!/bin/bash
# build.sh <build dir> (lane eng-sched1): the PC check's two programs, sched_ref (the reference layer) and sched_nat
# (the engine's layer), from the original units unchanged (host copies by hostref/prep.py copy, as the PC reference
# builds them) and the harness. The units' unresolved references become generated zero stubs (hostref/gen_stubs.py);
# the data objects they name are zeroed storage (data.txt). Called by ../sched_check.sh.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../../.." && pwd)
B=${1:?build dir}
ENG=$ROOT/port/dreamcast/engine
GAME=$ROOT/port/dreamcast/game
mkdir -p "$B/gen" "$B/o"
# each unit's game settings, as the engine images build it (game/game_settings.mk SET_<dir>_<name>)
setting() { printf 'include %s\nall:\n\t@echo $(SET_%s)\n' "$ENG/game/game_settings.mk" "$1" | make -s -f - all; }
ARCH="-m32 -msse2 -mfpmath=sse -malign-double -fno-pie -fno-stack-protector -O1 -g -fno-strict-aliasing -ffunction-sections -fdata-sections -ffp-contract=off"
GINC="-include $GAME/platform/include/re4dc_prelude.h -I$ROOT/include -I$ROOT/src -I$ROOT/src/game -I$GAME/platform/include -DRE4DC_GAME -DRE4DC_STAT_ROUTINE_BYTES=1 -include $ENG/host/corrections.h"
PCF="-isystem /usr/include/x86_64-linux-gnu/c++/13 -std=gnu++20 -fno-exceptions -fno-rtti -Wall"
GFLAGS="-std=gnu++20 -fpermissive -w -fno-exceptions -fno-rtti -fno-threadsafe-statics $GINC"
# the original units (host copies), r101's module entry under its own name as the engine images link it
UNITS="game/scheduler game/sce_sys st1/r101 game/libgpu"
for u in $UNITS; do
    n=$(echo $u | tr / _)
    python3 "$ENG/hostref/prep.py" copy "$ROOT/src/$u.cpp" "$B/gen/$n.cpp"
    extra=$(setting $n)
    [ $u = st1/r101 ] && extra="$extra -D_prolog=r101_prolog -D_epilog=r101_epilog -D_unresolved=r101_unresolved"
    g++ $ARCH $GFLAGS $extra -c "$B/gen/$n.cpp" -o "$B/o/$n.o"
done
# the engine's list and lifted layer (native), the reference layer, the harness
g++ $ARCH $GFLAGS -I$ENG/host -c "$ENG/services/scene/at_list.cpp" -o "$B/o/at_list.o"
g++ $ARCH $PCF -Wno-unused -I"$HERE/kos_pc" -I"$ENG/core" -c "$ENG/core/os_threads.cpp" -o "$B/o/os_threads.o"
g++ $ARCH $PCF -I"$HERE" -c "$HERE/kos_pc.cpp" -o "$B/o/kos_pc.o"
g++ $ARCH $PCF -I"$HERE" -I"$ENG/core" -c "$HERE/native_boot.cpp" -o "$B/o/native_boot.o"
g++ $ARCH $PCF -c "$HERE/gc_os.cpp" -o "$B/o/gc_os.o"
for L in ref nat; do
    g++ $ARCH -isystem /usr/include/x86_64-linux-gnu/c++/13 $GFLAGS -I$ENG/hostref -I$ENG/host "-DSCHED_LAYER=\"$L\"" -c "$HERE/sched_main.cpp" -o "$B/o/main_$L.o"
done
g++ $ARCH $GFLAGS -I$ENG/hostref -c "$HERE/data.cpp" -o "$B/o/data.o"
LD="-m32 -no-pie -Wl,-Ttext-segment=0x88000000 -Wl,--gc-sections -Wl,--wrap=TaskSchedulerMain -Wl,--wrap=_Z9TaskSleepi -Wl,--wrap=AddPrim -lm"
OREF="$B/o/main_ref.o $B/o/data.o $B/o/game_scheduler.o $B/o/game_sce_sys.o $B/o/st1_r101.o $B/o/game_libgpu.o $B/o/gc_os.o"
ONAT="$B/o/main_nat.o $B/o/data.o $B/o/game_scheduler.o $B/o/game_sce_sys.o $B/o/st1_r101.o $B/o/at_list.o $B/o/os_threads.o $B/o/kos_pc.o $B/o/native_boot.o"
# the stubs: one set for both programs (the union of what each leaves unresolved)
: > "$B/undef.txt"
for objs in "$OREF" "$ONAT"; do
    gcc -o "$B/probe" $objs $LD -Wl,--no-demangle 2>&1 | sed -n "s/.*undefined reference to \`\([^']*\)'.*/\1/p" >> "$B/undef.txt" || true
done
sort -u "$B/undef.txt" -o "$B/undef.txt"
# (two names the units declare with the old compiler's mangling in asm labels: no declaration to take a type from)
# A name gen_stubs.py's headers do not declare (a C function, or a member of a class they leave out) cannot take
# its type from them: each compile names them (fallback.py), and they are generated again as int-returning stubs
# (zero in the return register: right for void, integer and pointer returns; a float return would read the x87
# stack, so stubs_int.txt lists them for review)
FB=save__9cGameSavePv,setCloseLock__7cEmDoori
for pass in 1 2 3 4; do
    python3 "$ENG/hostref/gen_stubs.py" "$B/undef.txt" "$B/gen/sched_stubs.cpp" $FB
    g++ $ARCH $GFLAGS -I$ENG/hostref -c "$B/gen/sched_stubs.cpp" -o "$B/o/sched_stubs.o" 2> "$B/stubs_err.txt" && break
    [ $pass = 4 ] && { tail -20 "$B/stubs_err.txt"; exit 1; }
    FB=$(python3 "$HERE/fallback.py" "$B/gen/sched_stubs.cpp" "$B/stubs_err.txt" $FB)
done
echo "$FB" | tr , '
' > "$B/stubs_int.txt"
gcc -o "$B/sched_ref" $OREF "$B/o/sched_stubs.o" $LD
gcc -o "$B/sched_nat" $ONAT "$B/o/sched_stubs.o" $LD
echo "build: $(wc -l < "$B/undef.txt") stubs; sched_ref sched_nat in $B"

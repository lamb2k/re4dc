#!/usr/bin/env bash
# Reproduce the bounded CPU fixture only. No game assets/dependency downloads,
# toolchain installs, emulator launch or recovered-game changes are performed.
# Usage: build_room_layout_probe.sh PACKAGE_ROOT SH4ZAM_CHECKOUT NEW_OUTPUT_DIR
#   (SH4ZAM_CHECKOUT: port/dreamcast/game/third_party/sh4zam after git submodule update --init)
# PACKAGE_ROOT is the four-owner bake/compact output described in D364.
set -euo pipefail
if [[ $# != 3 ]]; then
    echo "usage: $0 PACKAGE_ROOT SH4ZAM_CHECKOUT NEW_OUTPUT_DIR" >&2
    exit 2
fi
project_port=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
private_packages=$(realpath -- "$1")
candidate_shz=$(realpath -- "$2")
probe_output=$(realpath -m -- "$3")
if [[ -e "$probe_output" ]]; then
    echo "refusing to overwrite probe output: $probe_output" >&2; exit 2
fi
# SH4ZAM_CHECKOUT is normally the submodule game/third_party/sh4zam. Its pin is the submodule commit recorded in this
# repository (2026-10-16; the probe was first measured at 0fd3a1e1, R4_ROOM_PACKAGE_V4_CHECKPOINT.md).
shz_pin=$(git -C "$project_port" rev-parse HEAD:port/dreamcast/game/third_party/sh4zam)
[[ $(git -C "$candidate_shz" rev-parse HEAD) == "$shz_pin" ]] || { echo "SH4ZAM pin mismatch (want the submodule commit $shz_pin)" >&2; exit 2; }
[[ -z $(git -C "$candidate_shz" diff --name-only HEAD) ]] || { echo 'SH4ZAM tracked source is dirty' >&2; exit 2; }
: "${RE4DC_KOS_BASE:?Set RE4DC_KOS_BASE to the existing pinned KOS checkout}"
source "$project_port/kos-env.sh"
[[ $($KOS_CC_BASE/bin/sh-elf-g++ -dumpfullversion) == 15.2.0 ]] || { echo 'requires the pinned GCC15.2' >&2; exit 2; }
[[ $(git -C "$KOS_BASE" rev-parse HEAD) == 804b3195ebd1a06a27cc2b3a5eacf7a2429040a3 ]] || { echo 'KOS pin mismatch' >&2; exit 2; }
mkdir -p -- "$probe_output"
cp -- "$candidate_shz/LICENSE" "$probe_output/SH4ZAM-LICENSE.txt"
echo "$shz_pin" > "$probe_output/sh4zam-commit.txt"
flags=(-std=c++20 -O3 -fno-predictive-commoning -flto=1 -ffat-lto-objects
       -fno-strict-aliasing -fno-fast-math -Wall -Wextra
       -DRE4DC_STATIC_SH4ZAM=1 -DRE4DC_NATIVE_RENDER_PROFILE=1
       -I"$project_port/room" -I"$project_port/game/platform/include" -I"$candidate_shz/include")
kos-c++ "${flags[@]}" -c "$project_port/room/static_room_prepare.cpp" -o "$probe_output/prepare.o"
kos-c++ -std=c++20 -O2 -fno-fast-math -I"$project_port/room" -c "$project_port/room/room_package.cpp" -o "$probe_output/package.o"
kos-c++ "${flags[@]}" -c "$project_port/tests/room_layout_probe.cpp" -o "$probe_output/probe.o"
kos-cc -I"$candidate_shz/include" -c "$candidate_shz/source/sh4/shz_mem_sh4.s" -o "$probe_output/shz_mem.o"
for layout in v3 aos20 split24; do
    arm="$probe_output/$layout"
    mkdir -p -- "$arm/romdisk"
    for owner in MAINSCENARIO FILE_00 FILE_01 FILE_02; do
        if [[ $layout == v3 ]]; then src="$private_packages/$owner-bake/r100-prelit.re4room"
        else src="$private_packages/$owner-$layout.re4room"; fi
        cp -- "$src" "$arm/romdisk/$owner.re4room"
    done
    cd -- "$arm"
    printf '%s\n' 'KOS_ROMDISK_DIR = romdisk' 'include $(KOS_BASE)/Makefile.rules' 'all: romdisk.o' > Makefile
    make romdisk.o
    kos-c++ -O3 -flto=1 -o probe.elf "$probe_output/probe.o" "$probe_output/prepare.o" "$probe_output/package.o" "$probe_output/shz_mem.o" romdisk.o
    "$KOS_CC_BASE/bin/sh-elf-nm" -n probe.elf > symbols.txt
    "$KOS_CC_BASE/bin/sh-elf-size" probe.elf
    sha256sum probe.elf romdisk/*.re4room > sha256.txt
done

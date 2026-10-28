#!/usr/bin/env bash
set -euo pipefail
HERE=/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367/gc_port23
GAME=$(CDPATH= cd -- "$HERE/../../../game" && pwd)
SCRATCH=$(mktemp -d /dev/shm/gc-port23-host-XXXXXX)
case "$SCRATCH" in /dev/shm/gc-port23-host-*) ;; *) exit 2 ;; esac
trap 'rm -rf -- "${SCRATCH:?}"' EXIT
export PYTHONDONTWRITEBYTECODE=1
: skipped
g++ -std=c++17 -O2 -Wall -Wextra -Werror -DRE4DC_GC_ASSET_GATE=1 -DRE4DC_GC_ASSET_TEST=1 \
    "$HERE/test_gate.cpp" "$GAME/platform/gc_asset_gate.cpp" -o "$SCRATCH/test_gate"
if test -x /lib64/ld-linux-x86-64.so.2; then
    /lib64/ld-linux-x86-64.so.2 "$SCRATCH/test_gate"
else
    "$SCRATCH/test_gate"
fi
# Sparse catalog index (gc-catalog24b): verdicts equal the exact lookup for every row.
# GC24_CATALOG=<gc-assets.idx> also checks every row of a real catalog.
g++ -std=c++17 -O2 -Wall -Wextra -Werror -DRE4DC_GC_ASSET_GATE=1 \
    "$HERE/test_index_sparse.cpp" "$GAME/platform/gc_asset_gate.cpp" -o "$SCRATCH/test_index_sparse"
/lib64/ld-linux-x86-64.so.2 "$SCRATCH/test_index_sparse" ${GC24_CATALOG:+"$GC24_CATALOG"}
g++ -std=c++17 -O2 -Wall -Wextra -Werror "$HERE/test_packet_cursor.cpp" -o "$SCRATCH/test_packet_cursor"
/lib64/ld-linux-x86-64.so.2 "$SCRATCH/test_packet_cursor"
g++ -std=c++17 -O2 -Wall -Wextra -Werror -DRE4DC_GC_ASSET_GATE=1 -DRE4DC_GC_ASSET_TEST=1 \
    "$HERE/test_members.cpp" "$GAME/platform/gc_asset_members.cpp" "$GAME/platform/gc_asset_gate.cpp" -o "$SCRATCH/test_members"
/lib64/ld-linux-x86-64.so.2 "$SCRATCH/test_members"
g++ -std=c++17 -Os -Wall -Wextra -Werror -c "$GAME/platform/gc_asset_gate.cpp" -o "$SCRATCH/off.o"
if nm --defined-only "$SCRATCH/off.o" | grep -q .; then
    printf 'Default-off gate contains linked symbols\n' >&2
    exit 1
fi
g++ -std=c++17 -Os -DRE4DC_GC_ASSET_GATE=1 -c "$GAME/platform/gc_asset_gate.cpp" -o "$SCRATCH/on.o"
size "$SCRATCH/off.o" "$SCRATCH/on.o"
g++ -std=c++17 -Os -Wall -Wextra -Werror -c "$GAME/platform/gc_asset_members.cpp" -o "$SCRATCH/members-off.o"
if nm --defined-only "$SCRATCH/members-off.o" | grep -q .; then exit 1; fi
g++ -std=c++17 -Os -Wall -Wextra -Werror -DRE4DC_GC_ASSET_GATE=1 -c "$GAME/platform/gc_asset_members.cpp" -o "$SCRATCH/members-on.o"
size "$SCRATCH/members-off.o" "$SCRATCH/members-on.o"
g++ -std=c++17 -Os -Wall -Wextra -Werror -c "$GAME/platform/gc_asset_disc.cpp" -o "$SCRATCH/disc-off.o"
if nm --defined-only "$SCRATCH/disc-off.o" | grep -q .; then exit 1; fi
g++ -std=c++17 -Os -Wall -Wextra -Werror -c "$GAME/platform/gc_asset_payloads.cpp" -o "$SCRATCH/payloads-off.o"
if nm --defined-only "$SCRATCH/payloads-off.o" | grep -q .; then exit 1; fi
g++ -std=c++17 -Os -Wall -Wextra -Werror -DRE4DC_GC_ASSET_GATE=1 -c "$GAME/platform/gc_asset_payloads.cpp" -o "$SCRATCH/payloads-on.o"
size "$SCRATCH/payloads-off.o" "$SCRATCH/payloads-on.o"
g++ -std=c++17 -Os -Wall -Wextra -Werror -c "$GAME/platform/gc_asset_audio.cpp" -o "$SCRATCH/audio-off.o"
if nm --defined-only "$SCRATCH/audio-off.o" | grep -q .; then exit 1; fi
g++ -std=c++17 -Os -Wall -Wextra -Werror -DRE4DC_GC_ASSET_GATE=1 -c "$GAME/platform/gc_asset_audio.cpp" -o "$SCRATCH/audio-on.o"
size "$SCRATCH/audio-off.o" "$SCRATCH/audio-on.o"
printf 'GC-ASSET host core and judge tests PASS; target and runtime gates not run.\n'

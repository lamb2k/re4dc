#!/usr/bin/env bash
# install-sh4zam.sh [KOS_PORTS]: SH4ZAM (gyrovorbis/sh4zam, MIT) from kos-ports at the pins in toolchain.lock.
#
# Checks out kos-ports at KOS_PORTS_SHA (cloning it if the directory does not exist), then runs the port's own
# `make install` in kos-ports/sh4zam with GIT_CHANGESET=SH4ZAM_SHA. That installs the headers into
# KOS_PORTS/include/sh4zam and libsh4zam.a into KOS_PORTS/lib, where the game build finds them (game30.mk SH4ZAM_INC).
# Needs a KOS environment (RE4DC_KOS_BASE / RE4DC_KOS_CC_BASE, i.e. the toolchain's env.sh) and cmake.
# KOS_PORTS defaults to $RE4DC_KOS_PORTS, then the kos-ports directory next to KOS.
# Updating SH4ZAM: bump SH4ZAM_SHA (and KOS_PORTS_SHA if the port itself changed) in toolchain.lock and run this again.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PORT=$(cd "$HERE/.." && pwd)
# shellcheck disable=SC1091
. "$PORT/toolchain.lock"
: "${RE4DC_KOS_BASE:?source the toolchain env.sh first}"
KP=${1:-${RE4DC_KOS_PORTS:-$RE4DC_KOS_BASE/../kos-ports}}
KOS_PORTS_URL=${KOS_PORTS_URL:-https://github.com/KallistiOS/kos-ports.git}
command -v cmake >/dev/null || { echo "install-sh4zam: needs cmake (sudo apt install cmake)" >&2; exit 1; }

if [ ! -d "$KP/.git" ]; then
  git init -q "$KP"
  git -C "$KP" remote add origin "$KOS_PORTS_URL"
fi
if [ "$(git -C "$KP" rev-parse HEAD 2>/dev/null)" != "$KOS_PORTS_SHA" ]; then
  git -C "$KP" fetch -q --depth 1 origin "$KOS_PORTS_SHA"
  git -C "$KP" checkout -q --detach FETCH_HEAD
fi
test "$(git -C "$KP" rev-parse HEAD)" = "$KOS_PORTS_SHA"
KP=$(cd "$KP" && pwd)

export RE4DC_KOS_PORTS="$KP"
# shellcheck disable=SC1091
. "$PORT/kos-env.sh"
have=$(git -C "$KP/sh4zam/dist/sh4zam-" rev-parse HEAD 2>/dev/null || true)
if [ "$have" = "$SH4ZAM_SHA" ] && [ -f "$KP/lib/libsh4zam.a" ] && [ -f "$KP/include/sh4zam/shz_xmtrx.h" ]; then
  echo "   sh4zam $SH4ZAM_SHA already installed in $KP"
  exit 0
fi
# A different pin: start from a clean port directory so the clone is reset to the new changeset.
make -C "$KP/sh4zam" clean >/dev/null 2>&1 || true
rm -rf "$KP/sh4zam/dist" "$KP/sh4zam/build" "$KP/sh4zam/inst"
make -C "$KP/sh4zam" install GIT_CHANGESET="$SH4ZAM_SHA" >/dev/null
test "$(git -C "$KP/sh4zam/dist/sh4zam-" rev-parse HEAD)" = "$SH4ZAM_SHA"
echo "   sh4zam $SH4ZAM_SHA installed in $KP (include/sh4zam, lib/libsh4zam.a)"

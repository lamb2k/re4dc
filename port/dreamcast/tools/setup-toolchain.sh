#!/usr/bin/env bash
# setup-toolchain.sh [PREFIX]: the RE4 Dreamcast port toolchain from scratch, without Docker.
#
# Builds what the maintainers use (port/dreamcast/toolchain.lock):
#   KallistiOS 804b3195 with the three port patches (port/dreamcast/patches), and the
#   SH4 cross compiler from KOS kos-chain, profile "stable": GCC 15.2.0, binutils 2.45.1,
#   newlib 4.6.0.20260123, thread model kos, multilibs m4-single and m4-single-only.
#
# Layout (PREFIX defaults to $HOME/re4dc-toolchain):
#   PREFIX/sh-elf   the cross compiler (sh-elf-gcc ...)
#   PREFIX/kos      the patched KallistiOS tree, built
#   PREFIX/env.sh   source this before building the game
# SH4ZAM is not part of the toolchain: it is the git submodule game/third_party/sh4zam (clone with
# --recurse-submodules, or git submodule update --init).
#
# Host packages (Ubuntu 24.04 names):
#   build-essential bison flex texinfo libgmp-dev libmpfr-dev libmpc-dev libelf-dev
#   libjpeg-dev libpng-dev git curl wget python3 python3-pip genisoimage
#   (port/dreamcast/docker/Dockerfile installs exactly these.)
#
# Takes about 25 to 40 minutes on 16 threads; needs about 6 GB free while building,
# about 0.9 GB after (sources and build dirs are removed). JOBS=<n> sets the parallelism.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PORT=$(cd "$HERE/.." && pwd)
# shellcheck disable=SC1091
. "$PORT/toolchain.lock"
PREFIX=${1:-${PREFIX:-$HOME/re4dc-toolchain}}
JOBS=${JOBS:-$(nproc)}
KOS_URL=${KOS_URL:-https://github.com/KallistiOS/KallistiOS.git}
mkdir -p "$PREFIX"
PREFIX=$(cd "$PREFIX" && pwd)
KOS=$PREFIX/kos
CC_BASE=$PREFIX/sh-elf

for c in make gcc g++ bison flex makeinfo git curl python3 patch genisoimage; do
  command -v "$c" >/dev/null || { echo "setup-toolchain: missing host tool: $c" >&2; exit 1; }
done

t0=$(date +%s)
echo "== KallistiOS $KOS_SHA into $KOS"
if [ ! -d "$KOS/.git" ]; then
  git init -q "$KOS"
  git -C "$KOS" remote add origin "$KOS_URL"
fi
git -C "$KOS" fetch -q --depth 1 origin "$KOS_SHA"
git -C "$KOS" checkout -q --detach FETCH_HEAD
test "$(git -C "$KOS" rev-parse HEAD)" = "$KOS_SHA"
# Patches in order (patches/README.md). Skip if this tree already carries them.
if git -C "$KOS" diff --quiet; then
  for p in manual-flip async-present vbuf-switch; do
    git -C "$KOS" apply "$PORT/patches/kos-804b319-$p.patch"
  done
else
  echo "   (KOS tree already modified: patches assumed applied)"
fi

echo "== SH4 compiler (kos-chain, profile stable) into $CC_BASE"
if [ ! -x "$CC_BASE/bin/sh-elf-gcc" ]; then
  cd "$KOS/utils/kos-chain"
  cp Makefile.dreamcast.cfg Makefile.cfg
  make build platform=dreamcast toolchain_profile=stable toolchain_path="$CC_BASE" \
       makejobs="$JOBS" verbose=0 install_mode=install-strip
  # Downloaded tarballs and build trees are large; keep only the installed compiler.
  git -C "$KOS/utils/kos-chain" clean -fdxq
fi
"$CC_BASE/bin/sh-elf-gcc" --version | head -1

cat > "$PREFIX/env.sh" <<ENV
# Source this, then build: bash port/dreamcast/build-public.sh
export RE4DC_KOS_BASE="$KOS"
export RE4DC_KOS_CC_BASE="$CC_BASE"
export KOS_TOOLS_BASE="$KOS"
export PATH="$CC_BASE/bin:\$PATH"
ENV

echo "== KallistiOS library"
# shellcheck disable=SC1091
( . "$PREFIX/env.sh" && . "$PORT/kos-env.sh" && make -C "$KOS" -j"$JOBS" >/dev/null )
# The game links against the patched entry points; fail here, not at link time.
SYMS=$("$CC_BASE/bin/sh-elf-nm" "$KOS/lib/dreamcast/libkallisti.a" 2>/dev/null)
for s in _pvr_present_async _pvr_present_wait _pvr_present_pending _pvr_set_vbuf_doublebuf; do
  grep -q " T $s\$" <<<"$SYMS" ||
    { echo "setup-toolchain: libkallisti.a lacks $s (patches not applied?)" >&2; exit 1; }
done
# Host tools the disc tools use (makeip, scramble).
make -C "$KOS/utils/makeip" >/dev/null
make -C "$KOS/utils/scramble" >/dev/null

echo "== Python packages (asset tools only; the game build needs just python3)"
if python3 -m pip --version >/dev/null 2>&1; then
  python3 -m pip install --user --quiet -r "$PORT/requirements.txt" 2>/dev/null ||
    python3 -m pip install --user --quiet --break-system-packages -r "$PORT/requirements.txt"
else
  echo "   no pip: skipped (install python3-pip, then: python3 -m pip install --user -r port/dreamcast/requirements.txt)"
fi

echo "setup-toolchain: done in $(( $(date +%s) - t0 )) s; size $(du -sh "$PREFIX" | cut -f1)"
echo "next: . $PREFIX/env.sh && bash port/dreamcast/build-public.sh"

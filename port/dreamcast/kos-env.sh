#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "source this file instead of executing it" >&2
    exit 2
fi

export KOS_ARCH="dreamcast"
export KOS_SUBARCH="pristine"
export KOS_BASE="${RE4DC_KOS_BASE:-/root/work/kos}"
export KOS_PORTS="${RE4DC_KOS_PORTS:-/root/work/kos-ports}"
export KOS_CC_BASE="${RE4DC_KOS_CC_BASE:-/opt/toolchains/dc/sh-elf}"
export KOS_CC_PREFIX="sh-elf"
export DC_ARM_BASE="${RE4DC_ARM_BASE:-/opt/toolchains/dc/arm-eabi}"
export DC_ARM_PREFIX="arm-eabi"
export DC_TOOLS_BASE="${RE4DC_DC_TOOLS_BASE:-/opt/toolchains/dc/bin}"
export KOS_CMAKE_TOOLCHAIN="${KOS_BASE}/utils/cmake/kallistios.toolchain.cmake"
export KOS_GENROMFS="${KOS_BASE}/utils/genromfs/genromfs"
export KOS_MAKE="make"
export KOS_LOADER="${RE4DC_KOS_LOADER:-dc-tool -x}"

export KOS_INC_PATHS=""
export KOS_INC_PATHS_CPP=""
export KOS_CFLAGS="-O2 -fno-PIC -fno-PIE -fomit-frame-pointer"
export KOS_CPPFLAGS=""
export KOS_LDFLAGS=""
export KOS_AFLAGS=""
export DC_ARM_LDFLAGS=""
export KOS_SH4_PRECISION="-m4-single"

# KOS resolves compilers, include paths, libraries, and architecture flags here.
# Global fast-math remains disabled until RE4 behavior comparisons justify it.
. "${KOS_BASE}/environ_base.sh"

# Shared compiler cache (lane buildcache, 2026-11-03). RE4DC_CCACHE=1 runs the real sh-elf compilers through ccache;
# the kos-cc / kos-c++ wrappers call $KOS_CC / $KOS_CCPLUS, so pointing those at tools/ccache/ hooks every compile
# without changing how builds are called. One shared cache (/root/.cache/ccache: base_dir=/root/work, hash_dir=false,
# compiler_check=content, max_size=60G) serves every OBJDIR and worktree; knob -D flags hit in preprocessor mode for
# files a knob does not change. Proven byte-identical (program image + overlays) against uncached builds.
# Opt-in (RE4DC_CCACHE=1) until the identity proof passes; without ccache installed the build runs uncached.
if [ "${RE4DC_CCACHE:-0}" = 1 ] && command -v ccache >/dev/null 2>&1; then
    _re4dc_ccdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tools/ccache"
    if [ -x "$_re4dc_ccdir/cc" ] && [ "${KOS_CC}" != "$_re4dc_ccdir/cc" ]; then
        export RE4DC_REAL_CC="${KOS_CC}" RE4DC_REAL_CCPLUS="${KOS_CCPLUS}"
        export KOS_CC="$_re4dc_ccdir/cc" KOS_CCPLUS="$_re4dc_ccdir/c++"
        export CCACHE_DIR="${CCACHE_DIR:-/root/.cache/ccache}"
    fi
    unset _re4dc_ccdir
fi

#!/bin/bash
# newlib_libm.sh [build dir] (lane eng-svc5): the toolchain's newlib release (4.6.0.20260123, as the KOS chain builds it:
# sh-elf-gcc's libm.a names it), its float math sources compiled for the PC with re4ref's flags, every global symbol
# prefixed nl_, into <build dir>/ext/nlobj (default: the worktree's build/), for svc.mk's libmtest. The download is
# public source (sourceware.org), checked against its sha256, kept under build/ (not in git).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
D=${1:-$ROOT/build}/ext
V=newlib-4.6.0.20260123
SHA=6ff27e3bf022666f43f7802255be680eeff722ac181b1725d21e2e8318604ee3
mkdir -p "$D" && cd "$D" || exit 2
[ -f newlib.tar.gz ] || curl -sSfL -o newlib.tar.gz "https://sourceware.org/pub/newlib/$V.tar.gz" || { echo "download failed"; exit 2; }
echo "$SHA  newlib.tar.gz" | sha256sum -c --quiet || { echo "newlib.tar.gz: sha256 mismatch"; exit 2; }
[ -d $V/newlib/libm/math ] || tar -xzf newlib.tar.gz "$V/newlib/libm/math" "$V/newlib/libm/common" "$V/newlib/libc/include" || exit 2
N=$D/$V/newlib
mkdir -p nlobj nlraw shim/machine
cp "$N/libc/include/machine/ieeefp.h" shim/machine/ieeefp.h
F="-m32 -msse2 -mfpmath=sse -fno-pie -fno-stack-protector -O1 -ffp-contract=off -fno-builtin -D_IEEE_LIBM -I$D/shim -I$N/libm/common -idirafter /usr/include/x86_64-linux-gnu"   # idirafter: <asm/errno.h> for the -m32 build on a host without the 32-bit kernel headers
for f in math/sf_sin math/sf_cos math/sf_tan math/sf_atan math/ef_atan2 math/ef_asin math/ef_acos math/ef_sqrt math/kf_sin \
         math/kf_cos math/kf_tan math/ef_rem_pio2 math/kf_rem_pio2 math/wf_atan2 math/wf_asin math/wf_acos math/wf_sqrt \
         common/sf_scalbn math/sf_floor math/sf_fabs common/sf_copysign; do
    b=$(basename $f)
    gcc $F -c "$N/libm/$f.c" -o nlobj/$b.raw.o || exit 1
    cp nlobj/$b.raw.o nlraw/$b.o   # unprefixed: the nlnative build links these in place of the game's fdlibm (svc.mk)
    objcopy --prefix-symbols=nl_ nlobj/$b.raw.o nlobj/$b.o && rm -f nlobj/$b.raw.o
done
echo "newlib float math: $(ls nlobj/*.o | wc -l) objects in $D/nlobj"

#!/bin/bash
# Links the E1 image (lane eng-e1). The recovered sources name some functions and globals by their PowerPC link names
# (asm("pG"), GCC 2.95 member names); the old port's generator (game/tools/gen_aliases.py) binds them to the SH-4
# symbols that define them, as a linker script of assignments. Nothing unresolved is stubbed automatically: a
# missing symbol fails the link (the engine's stubs are explicit, host/e1_stubs.cpp).
#   link.sh <out.elf> <ldflags...> -- <objects...>
set -e
OUT=$1; shift
LD=(); while [ "$1" != "--" ]; do LD+=("$1"); shift; done; shift
OBJS="$@"
D=$(dirname "$OUT")
GA=$(cd "$(dirname "$0")/../../game/tools" && pwd)/gen_aliases.py
sh-elf-nm $OBJS 2>/dev/null | grep -E " [TDBWRVC] " | awk '{print $3}' | sort -u > $D/defined.txt
sh-elf-c++filt < $D/defined.txt > $D/defined-dem.txt
paste $D/defined.txt $D/defined-dem.txt > $D/nm-pairs.txt
sh-elf-nm $OBJS 2>/dev/null | grep -E " U " | awk '{print $2}' | sort -u | comm -23 - $D/defined.txt > $D/undefined.txt
python3 "$GA" $D/undefined.txt $D/nm-pairs.txt $D/aliases.ld
cat "$(dirname "$0")/aliases-e1.ld" $D/aliases.ld > $D/aliases-all.ld
kos-c++ "${LD[@]}" -o "$OUT" $OBJS $D/aliases-all.ld

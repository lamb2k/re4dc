#!/bin/bash
# Links re4dc-game.elf from the game, SDK and platform objects.
#
# 1. the PowerPC link-name aliases are generated from the objects
#    (tools/gen_aliases.py -> obj/aliases.ld, an assignment-only script the
#    linker reads as an input file);
# 2. a first link with every unresolved symbol reported produces the list of
#    what the platform layer still lacks (obj/missing.txt);
# 3. those become loud stubs (tools/gen_missing.py -> obj/missing.cpp) and the
#    final link produces the ELF.
#
#   [GAME_LDFLAGS=..] link.sh <target.elf> <opt-flags> <objects...>
# GAME_LDFLAGS (from the Makefile) goes to both links, e.g. --wrap options.
set -e
TARGET=$1; OPT=$2; shift 2
OBJS="$@"
mkdir -p obj
sh-elf-nm $OBJS 2>/dev/null | grep -E " [TDBWRV] " | awk '{print $3}' | sort -u > obj/defined.txt
sh-elf-c++filt < obj/defined.txt > obj/defined-dem.txt
paste obj/defined.txt obj/defined-dem.txt > obj/nm-pairs.txt
sh-elf-nm $OBJS 2>/dev/null | grep -E " U " | awk '{print $2}' | sort -u | comm -23 - obj/defined.txt > obj/undefined.txt
python3 tools/gen_aliases.py obj/undefined.txt obj/nm-pairs.txt obj/aliases.ld
# RE4DC_LINK_OVERLAY=".ovl_<mod> ..." (subscreen.mk SUBSCREEN_OVL=1: .ovl_Sscrn; Makefile ROUTE_OVL=1:
# .ovl_pl0f .ovl_em2f): each section is placed outside RAM (after .ocram, so _end and the arena do
# not move), kept whole (--gc-sections would drop it: the image no longer references it), and
# turned into <dir of target>/<mod lower case>.ovl below. Overlay i links at 0x8E000000 + i * 4 MiB.
OVL=${RE4DC_LINK_OVERLAY:-}
OVL_DIR=$(dirname "$TARGET")
rm -f "$OVL_DIR"/*.ovl
# RE4DC_LINK_OVL_HELPERS=1 (Makefile LINK_OVL_HELPERS): image code that only one room overlay reaches moves into
# that overlay (tools/ovl_helpers.py, below); the overlay's output section also keeps <section>.h*.
HELPERS=${RE4DC_LINK_OVL_HELPERS:-0}
# ovl_script <file> [<index shifted by 1 MiB>]
ovl_script() {
    printf 'SECTIONS {\n' > "$1"
    local i=0 s
    for s in $OVL; do
        local at=$((0x8E000000 + i * 0x400000))
        [ "${2:-}" = "$i" ] && at=$((at + 0x100000))
        if [ "$HELPERS" = 1 ]; then
            printf '  %s 0x%X : { KEEP(*(%s)) KEEP(*(%s.h*)) }\n' "$s" $at "$s" "$s" >> "$1"
        else
            printf '  %s 0x%X : { KEEP(*(%s)) }\n' "$s" $at "$s" >> "$1"
        fi
        i=$((i + 1))
    done
    printf '}\nINSERT AFTER .ocram;\n' >> "$1"
}
OVL_LD=
if [ -n "$OVL" ]; then
    ovl_script obj/overlay-a.ld
    OVL_LD="-Wl,-T,obj/overlay-a.ld"
fi
# manual aliases (platform/aliases-manual.ld) come first so they win
cat platform/aliases-manual.ld obj/aliases.ld > obj/aliases-all.ld
# pass 1: what is still unresolved after the aliases and the libraries
if ! kos-c++ $OPT ${GAME_LDFLAGS:-} $OVL_LD -Wl,--unresolved-symbols=ignore-all -o obj/pass1.elf $OBJS obj/aliases-all.ld > obj/pass1.log 2>&1; then
    cat obj/pass1.log; exit 1
fi
sh-elf-nm obj/pass1.elf | grep -E " [Uw] " | awk '{print $2}' | sort -u > obj/missing.txt
# Registered stage entry points must never become generated trap stubs.
if grep -Eq '^_st[0-9]+_[0-9]+_(prolog|epilog)$' obj/missing.txt; then
    echo "stage module entry points missing after partial link:" >&2
    grep -E '^_st[0-9]+_[0-9]+_(prolog|epilog)$' obj/missing.txt >&2
    exit 1
fi
# trans.cpp's sub screen guard (RE4DC_TRANS_SS_GUARD, SUBSCREEN=1) must reach the real hook in sscrn_bridge.cpp:
# a stub returns 0 and Trans walks the swapped room lists again (r21v console fault 0xE0).
if grep -qx '_re4dc_trans_ss_guard' obj/defined.txt && grep -qx '_re4dc_ss_ui_order' obj/missing.txt; then
    echo "re4dc_ss_ui_order is missing but trans.cpp's sub screen guard needs it (sscrn_bridge.cpp)" >&2
    exit 1
fi
python3 tools/gen_missing.py obj/missing.txt obj/missing.cpp
kos-c++ $KOS_CFLAGS $OPT -Iplatform/include -c obj/missing.cpp -o obj/missing.o
if [ "$HELPERS" = 1 ] && [ -n "$OVL" ]; then
    # Room overlays only (not the sub screen's .ovl_Sscrn, which lives on its own schedule): per overlay, the same
    # link with that overlay discarded; the .text sections it alone reached move into it. gen_overlay.py below still
    # proves every overlay relocatable and unreferenced by the image.
    H=obj/ovlh
    rm -rf $H; mkdir -p $H
    kos-c++ $OPT ${GAME_LDFLAGS:-} $OVL_LD -Wl,--print-gc-sections -o $H/x.elf $OBJS obj/missing.o obj/aliases-all.ld 2> $H/base.gc
    ROOM_OVL=
    for s in $OVL; do
        [ "$s" = .ovl_Sscrn ] && continue
        ROOM_OVL="$ROOM_OVL $s"
        { echo 'SECTIONS {'; echo "  /DISCARD/ : { *($s) }"; grep -v "^  $s " obj/overlay-a.ld | grep -v '^SECTIONS'; } > $H/discard.ld
        kos-c++ $OPT ${GAME_LDFLAGS:-} -Wl,-T,$H/discard.ld -Wl,--print-gc-sections -o $H/x.elf $OBJS obj/missing.o obj/aliases-all.ld 2> $H/$s.gc
    done
    rm -f $H/x.elf
    OBJS=$(printf '%s\n' $OBJS | python3 tools/ovl_helpers.py $H $ROOM_OVL)
fi
kos-c++ $OPT ${GAME_LDFLAGS:-} $OVL_LD -o $TARGET $OBJS obj/missing.o obj/aliases-all.ld
if [ -n "$OVL" ]; then
    # Per overlay, a second link with only that overlay 1 MiB higher: gen_overlay.py takes every
    # overlay word that moved by exactly that as a relocation, and fails on any other difference
    # (a PC-relative reference across the overlay boundary, or an image word - other overlays
    # included - that points into the overlay).
    i=0
    for s in $OVL; do
        a=$((0x8E000000 + i * 0x400000))
        ovl_script obj/overlay-b.ld $i
        kos-c++ $OPT ${GAME_LDFLAGS:-} -Wl,-T,obj/overlay-b.ld -o obj/overlay-b.elf $OBJS obj/missing.o obj/aliases-all.ld
        m=${s#.ovl_}
        python3 tools/gen_overlay.py "$TARGET" obj/overlay-b.elf "$s" $a $((a + 0x100000)) "$OVL_DIR/${m,,}.ovl" || exit 1
        rm -f obj/overlay-b.elf
        i=$((i + 1))
    done
    for s in $OVL; do sh-elf-objcopy -R "$s" "$TARGET"; done
fi
sh-elf-size $TARGET

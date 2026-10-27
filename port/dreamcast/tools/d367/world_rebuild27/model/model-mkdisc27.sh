#!/bin/bash
# Build a bootable Dreamcast disc image (CUE/BIN) from an ELF plus a data
# directory.  mkdisc.sh <elf> <datadir> <outdir> [fixturesdir]
#
# Deliberately a single-session CD-R layout rather than a GD-ROM (GDI) image.
# KOS mounts /cd by reading the *low density* table of contents
# (fs_iso9660.c calls cdrom_read_toc(&toc, false)) and taking the last data
# track it finds there. In a GDI the payload track lives in the high density
# area, so KOS never sees it and every fs_open("/cd/...") returns -1 even
# though the same image boots: the bootstrap reads the high density track
# directly. A CD-R image keeps the one data track where KOS looks for it.
# D367 W10: the game now wraps cdrom_read_toc (game/platform/gdrom_mount.cpp),
# so the GDEMU image is a GDI built by mkgdi.sh from the same inputs.
set -euo pipefail
ELF="$1"
DATA="$2"
OUTDIR="$3"
[ ! -e "$OUTDIR" ] || { echo "model packer preserves existing output: $OUTDIR" >&2; exit 1; }
[ $# -eq 3 ] || { echo "Prepare fixtures by unlink-before-copy in the owned data clone" >&2; exit 1; }
KOS=${KOS_TOOLS_BASE:-/root/work/kos}
# Per-run scratch directory so two builds cannot share or clobber a tree, and
# every copy below is fatal: a disc missing a file would boot and fail later
# in a way that looks like a game bug.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/re4dc-disc.XXXXXX")"
trap 'rm -rf "${WORK:?}"' EXIT

mkdir -p "$WORK/cdroot" "$OUTDIR"

# 1ST_READ.BIN: raw binary from the ELF.
if ! bash "$KOS/utils/elf2bin/elf2bin" "$ELF" "$WORK/prog.bin" >/dev/null 2>&1 || [ ! -s "$WORK/prog.bin" ]; then
  sh-elf-objcopy -R .stack -O binary "$ELF" "$WORK/prog.bin"
fi
test -s "$WORK/prog.bin"
# A CD-R bootstrap expects 1ST_READ.BIN scrambled, and descrambles it on load;
# that holds for the real BIOS and for Flycast's replacement alike. (A GD-ROM
# image is the other way round, which is why an unscrambled binary booted from
# the earlier GDI and produces a wedged machine here.)
if [ "${SCRAMBLE:-}" = "0" ]; then
  cp "$WORK/prog.bin" "$WORK/cdroot/1ST_READ.BIN"
else
  chmod +x "$KOS/utils/scramble/scramble" 2>/dev/null || true
  "$KOS/utils/scramble/scramble" "$WORK/prog.bin" "$WORK/cdroot/1ST_READ.BIN"
fi

cat > "$WORK/ip.txt" <<'IPTXT'
Hardware ID   : SEGA SEGAKATANA
Maker ID      : SEGA ENTERPRISES
Device Info   : 0000 CD-ROM1/1
Area Symbols  : JUE
Peripherals   : E000F10
Product No    : T0000
Version       : V1.000
Release Date  : 20260920
Boot Filename : 1ST_READ.BIN
SW Maker Name : RE4DC
Game Title    : RE4DC ROOM
IPTXT
chmod +x "$KOS/utils/makeip/makeip" 2>/dev/null || true
"$KOS/utils/makeip/makeip" -f "$WORK/ip.txt" "$WORK/IP.BIN" >/dev/null

if [ ! -d "$DATA" ]; then
  echo "mkdisc: data directory $DATA missing" >&2
  exit 1
fi
# the whole tree: the game target keeps the GameCube directory layout
cp -al "$DATA"/. "$WORK/cdroot/"
# Optional fixtures directory (port/dreamcast/fixtures): scripted input and
# other Dreamcast-only test files, published under /cd/dc/.
EXTRA="${4:-}"
if [ -n "$EXTRA" ]; then
  if [ ! -d "$EXTRA" ]; then
    echo "mkdisc: fixtures directory $EXTRA missing" >&2
    exit 1
  fi
  mkdir -p "$WORK/cdroot/dc"
  cp -r "$EXTRA"/. "$WORK/cdroot/dc/"
fi

# One MODE1/2048 data track starting at LBA 0, with IP.BIN occupying the first
# sixteen sectors. Rock Ridge and Joliet both carry the real (lower case, long)
# names; KOS reads either.
genisoimage -quiet -G "$WORK/IP.BIN" -r -J -l \
  -input-charset iso8859-1 -V RE4DCROOM -o "$OUTDIR/disc.bin" "$WORK/cdroot"

cat > "$OUTDIR/disc.cue" <<'CUE'
FILE "disc.bin" BINARY
  TRACK 01 MODE1/2048
    INDEX 01 00:00:00
CUE

echo "built $OUTDIR/disc.cue"
ls -l "$OUTDIR"

#!/bin/bash
# ps2snd24-regen.sh <final disc track03 (.bin/.iso)> [store dir]   (WSL; lane purge-audio24, 2026-10-24)
# Rebuilds data set ps2snd24 (test11/t11-fix.py) in one command from a FINAL disc: the PS2 sound banks and disc streams
# written in place into that disc's prebuilt AICA banks (tools/ps2_audio.py banks + streams). Run it again whenever a
# DATA set that rewrites one of the set's files (st1/*.dar, em/*.drs, ...) lands before it in the DATA line.
# Env: PS2ISO (the PS2 USA ISO), WORK (scratch on ext4), JOBS (default 6), PS2SND_MUSIC (default 1: the PS2 songs,
# sequences and instruments, into bgm/bio4midi.dat with ps2_audio.py music; 0 = sample matching only). Data only.
set -euo pipefail
TRACK=${1:?track03 of the final disc}
OUT=${2:-/root/re4data/private/ps2snd24-$(date +%Y%m%d)}
PS2ISO=${PS2ISO:-"/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso"}
WORK=${WORK:-/root/work/ps2snd24-regen}
JOBS=${JOBS:-6}
here=$(cd "$(dirname "$0")" && pwd)
PA=$here/../ps2_audio.py
rm -rf "${WORK:?}"; mkdir -p "$WORK"
python3 "$PA" afs --iso "$PS2ISO" --out "$WORK/ps2" '*.snd' '*.adx'
python3 "$here/fullplay/fp_iso.py" extract "$TRACK" "$WORK/tree" --manifest "$WORK/manifest.json" | tail -1
python3 "$PA" banks --tree "$WORK/tree" --ps2 "$WORK/ps2" --out "$WORK/ov" --json "$WORK/banks-map.json" --jobs "$JOBS" > "$WORK/banks.txt"
tail -1 "$WORK/banks.txt"
python3 "$PA" streams --tree "$WORK/tree" --ps2 "$WORK/ps2" --out "$WORK/ov" --json "$WORK/streams-map.json" --jobs "$JOBS" | tail -1
if [ "${PS2SND_MUSIC:-1}" = 1 ]; then
  python3 "$PA" music --tree "$WORK/tree" --ps2 "$WORK/ps2" --out "$WORK/ov" --json "$WORK/music-map.json" | tail -1
fi
# keep only files that changed; every kept file must have its source's size
rm -rf "${OUT:?}"; mkdir -p "$OUT/_map"
( cd "$WORK/ov" && find . -type f -printf '%P\n' ) | while read -r f; do
  src="$WORK/tree/$f"
  [ -f "$src" ] || src=$(find "$WORK/tree" -ipath "$WORK/tree/$f" | head -1)
  cmp -s "$WORK/ov/$f" "$src" && continue
  [ "$(stat -c %s "$WORK/ov/$f")" = "$(stat -c %s "$src")" ] || { echo "size differs: $f" >&2; exit 1; }
  mkdir -p "$OUT/$(dirname "$f")"; cp "$WORK/ov/$f" "$OUT/$f"
done
cp "$WORK"/*-map.json "$WORK/banks.txt" "$OUT/_map/"
{ echo "ps2snd24 regenerated $(date -u +%FT%TZ) from $TRACK (sha256 $(sha256sum "$TRACK" | cut -c1-16))"
  echo "tool: $(cd "$here" && git rev-parse --short HEAD) tools/ps2_audio.py; PS2: $PS2ISO; music: ${PS2SND_MUSIC:-1}"
  echo "files:"; ( cd "$OUT" && find . -type f ! -path './_map/*' ! -name RECIPE.txt ! -name SHA256SUMS -printf '  %P\n' | sort ); } > "$OUT/RECIPE.txt"
( cd "$OUT" && find . -type f ! -name SHA256SUMS -printf '%P\n' | sort | xargs sha256sum > SHA256SUMS )
echo "ps2snd24: $(grep -c '^  ' "$OUT/RECIPE.txt") files in $OUT (compare with DATA['ps2snd24'] in test11/t11-fix.py)"
rm -rf "${WORK:?}"

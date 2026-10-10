#!/bin/bash
# D367 disc: selected source mirror + fixtures overlay + native packages under
# /cd/dc/native/<room>/. Inputs are hard-linked or copied, never modified.
# usage: [MIRROR=.. FIXTURES_SRC=.. KEYED=.. MESHDIR=.. TEXDIRS="d1 d2"
#         MESHROOMS="r101=dir .." ROOMFILES="st1/r101.dar=file .."] stage.sh <build-dir> <disc-dir>
# MIRROR, FIXTURES_SRC and KEYED are private (locally extracted game data); defaults are
# the original D367 workstation paths. TEXDIRS overlays *.re4tex files onto /cd/dc/tex/
# (e.g. the PS2 tree bark replacing its GC source key); later TEXDIRS win. MESHDIR holds the r100
# packages; MESHROOMS adds other rooms' *.re4mesh (convert_room_bins.py --smd) under
# /cd/dc/native/<room>/. ROOMFILES replaces mirror files (a released room archive from
# room_smd.py release: st1/<room>.dar, and its .arc) in a hard-linked copy of the mirror;
# a released archive is only valid with its packages and NATIVE_MESH=1.
# MIRROR_OVERLAYS="d1 d2" adds or replaces mirror files with every file under each
# directory, at the same relative path (e.g. the converted sub screen ss/ and codec
# op/ trees that SUBSCREEN=1 reads; ROOMFILES entries still win).
# Default recipe (README.md): TEXDIRS="<tex-vq3 VQ overlay> <PS2 bark>". The inputs are
# recorded in <disc-dir>/stage-inputs.txt.
# GDI=1 also writes the GDEMU image (mkgdi.sh) from the same tree to GDI_OUT
# (default <disc-dir>/gdi; put it on /mnt/d when WSL's host drive is short).
# AICA_BANKS=1 (default) converts the route's sound banks to AICA ADPCM in place and
# adds bgm/aica_str.dat (the disc streams), tools/aica_banks.py disc, for AICA_AUDIO=1
# images (the silent audio_stub.cpp never reads either). AICA_CACHE (private, default
# /root/probe/d367-aica-cache) keeps the conversions: ~25 s the first time, ~2 s after.
# AICA_CALL_VOICES=1 (default 0) also streams the radio call voices (aica_banks.py CALL_VOICE_STREAMS);
# without them every call screen is silent (BGM ducked, SEs paused, no voice).
# AICA_WEAPONS=1 (default 0) also prebuilds Leon's other stage-1 weapon SE banks (aica_banks.py --weapons) into
# the WEP slot; without them every weapon but the handgun fires silently (issue lamb2k/re4dc#1).
# EFFECT_SPRITES=1 builds get the effect texture packages (tex_fx.sh) first in TEXDIRS.
# ASSETS=<dir> sources <dir>/stage.env from the asset pipeline (tools/d367/assets.sh; its
# MESHDIR/MESHROOMS/TEXDIRS/ROOMFILES/KEYED); variables set explicitly still win.
# UI_OVERRIDES=<dir> (private) replaces source UI images with edited PNGs named and placed
# as extract_ui_images.py writes them (<dir>/ss/eng/title_eff0_tpl31_tex00_CMPR_640x360.png),
# encoded by tools/ui_overrides.py exactly as the package they replace (16-bit or the
# TEXDIRS VQ overlay; same size or it fails). It wins over TEXDIRS. UI_SOURCE is the GC
# source tree (default /root/re4data). Unset: staging is unchanged.
# QUALITY=1 builds also stage the Standard asset set of every room in STDROOMS="r100=<dir> .."
# (<dir> = out/standard/<room> of tools/d367/assets.sh; docs/D367_ASSET_PIPELINE.md s16):
# <dir>/low/ -> /cd/dc/native/<room>/low/ (Standard packages, index.txt, plan.json) and
# <dir>/texlow/ -> /cd/dc/texlow/ (tools/d367/stage_std.py; checked against the staged Original
# packages, sizes reported and recorded). STD_ASSETS=<out/standard/<route>> takes STDROOMS from
# that stage.env (only that variable). ASSETS stays the Original set. Builds without QUALITY=1
# ignore STDROOMS: their disc is unchanged.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
if [ -n "${ASSETS:-}" ]; then
  test -f "$ASSETS/stage.env" || { echo "stage: no $ASSETS/stage.env (run tools/d367/assets.sh)" >&2; exit 1; }
  # shellcheck disable=SC1091
  . "$ASSETS/stage.env"
fi
if [ -n "${STD_ASSETS:-}" ] && [ -z "${STDROOMS:-}" ]; then
  test -f "$STD_ASSETS/stage.env" || { echo "stage: no $STD_ASSETS/stage.env (run tools/d367/assets.sh)" >&2; exit 1; }
  STDROOMS=$(unset STDROOMS; . "$STD_ASSETS/stage.env"; echo "${STDROOMS:-}")
fi
build=${1:?usage: stage.sh <build-dir> <disc-dir>}
out=${2:?usage: stage.sh <build-dir> <disc-dir>}
base=${D367_BASE:-/root/probe/d367-native-static}
mirror=${MIRROR:-/root/probe/d362-mirror}
fixtures=$(mktemp -d "${TMPDIR:-/tmp}/re4dc-fixtures.XXXXXX")
overlay=
aica=
trap 'rm -rf "$fixtures" ${overlay:+"$overlay"} ${aica:+"$aica" "$aica.json"}' EXIT
export RE4DC_KOS_BASE=${RE4DC_KOS_BASE:-/root/work/kos-re4dc-d336}
set +u; source "$here/../../kos-env.sh"; set -u
rmdir "$fixtures"; cp -al "${FIXTURES_SRC:-/root/probe/d354v7-fixtures}" "$fixtures"
mkdir -p "$fixtures/native/r100"
for o in MAINSCENARIO FILE_00 FILE_01 FILE_02; do
  cp "${KEYED:-$base/keyed12}/$o.re4room" "$fixtures/native/r100/$o.re4room"
done
# SUBSCREEN_OVL=1 / ROUTE_OVL=1 builds read their overlays from /cd/dc/<mod>.ovl (build.sh copies them).
for f in "$build"/*.ovl; do [ -f "$f" ] && cp "$f" "$fixtures/"; done
if [ -n "${MESHDIR:-}" ]; then cp "$MESHDIR"/*.re4mesh "$fixtures/native/r100/"; fi
for spec in ${MESHROOMS:-}; do
  room=${spec%%=*}; dir=${spec#*=}
  case $room in r[0-9a-f][0-9a-f][0-9a-f]) ;; *) echo "stage: bad MESHROOMS room $room" >&2; exit 1;; esac
  mkdir -p "$fixtures/native/$room"
  rm -f "$fixtures/native/$room"/*.re4mesh
  cp "$dir"/*.re4mesh "$fixtures/native/$room/"
done
# TA_VERTBUF_KB above 1024 shrinks the PVR texture pool (2.6 MB at 2048); the title/menu
# images then fit only as VQ (README.md: tex-vq3). Flycast without it: 1,884 upload failures.
ta_kb=$(grep -o 'TA_VERTBUF_KB=[0-9]*' "$build/candidate.txt" 2>/dev/null | head -1 | cut -d= -f2 || true)
vq_overlay=
# EFFECT_SPRITES=1 builds draw effect sprites from their TPL images: stage the effect texture
# packages first in TEXDIRS (tex_fx.sh; FX_CACHE, private, default /root/probe/d367-fx-cache,
# is generated once from RE4DATA), so the VQ overlay and later directories still win.
if grep -q 'EFFECT_SPRITES=1' "$build/candidate.txt" 2>/dev/null; then
  fx=${FX_CACHE:-/root/probe/d367-fx-cache}
  bash "$here/tex_fx.sh" "$fx"
  TEXDIRS="$fx ${TEXDIRS:-}"
fi
for d in ${TEXDIRS:-}; do if [ -e "$d/vq-native-ui-report.json" ]; then vq_overlay=$d; fi; done
if [ "${ta_kb:-1024}" -gt 1024 ] && [ -z "$vq_overlay" ]; then
  echo "stage.sh: WARNING: TA_VERTBUF_KB=$ta_kb build staged without a VQ texture overlay in TEXDIRS (README.md: tex-vq3)" >&2
fi
for d in ${TEXDIRS:-}; do
  mkdir -p "$fixtures/tex"
  for f in "$d"/*.re4tex; do rm -f "$fixtures/tex/$(basename "$f")"; cp "$f" "$fixtures/tex/"; done
done
ui_report=
if [ -n "${UI_OVERRIDES:-}" ]; then
  ui_out=$(mktemp -d "${TMPDIR:-/tmp}/re4dc-uiov.XXXXXX"); rmdir "$ui_out"
  ui_args=(); for d in ${TEXDIRS:-}; do ui_args+=(--texdir "$d"); done
  python3 -B "$here/../ui_overrides.py" --overrides "$UI_OVERRIDES" --source "${UI_SOURCE:-/root/re4data}" \
    --textures "${FIXTURES_SRC:-/root/probe/d354v7-fixtures}/tex" "${ui_args[@]}" --output "$ui_out" >&2
  mkdir -p "$fixtures/tex"
  for f in "$ui_out"/*.re4tex; do rm -f "$fixtures/tex/$(basename "$f")"; cp "$f" "$fixtures/tex/"; done
  ui_report=$(cat "$ui_out/ui-overrides-report.json"); rm -rf "$ui_out"
fi
# TEX_RESIDENT builds skip the runtime payload CRC: verify every staged texture package here
# (header payload_crc32 = CRC-32 of the bytes after the header). A mismatch stops staging.
if [ -d "$fixtures/tex" ]; then
  python3 - "$fixtures/tex" <<'PY'
import os, struct, sys, zlib
d = sys.argv[1]; bad = []; n = 0
for f in sorted(os.listdir(d)):
    if not f.endswith(".re4tex"): continue
    b = open(os.path.join(d, f), "rb").read(); n += 1
    size, crc = struct.unpack_from("<I", b, 12)[0], struct.unpack_from("<I", b, 36)[0]
    if len(b) < 48 or zlib.crc32(b[size:]) != crc: bad.append(f)
print("stage: %d texture packages, payload CRC %s" % (n, "ok" if not bad else "MISMATCH: " + " ".join(bad[:8])), file=sys.stderr)
sys.exit(1 if bad else 0)
PY
fi
# TEX_RESIDENT builds open /cd/dc/tex/<first hex digit>/<crc>-<fnv>.re4tex: the flat directory
# (~550 packages, 17+ sectors) overflowed the iso9660 16-sector inode cache, so every open
# re-read the directory from the disc (~0.2 s per first-sight texture in Flycast).
if grep -q 'TEX_RESIDENT=1' "$build/candidate.txt" 2>/dev/null && [ -d "$fixtures/tex" ]; then
  for f in "$fixtures"/tex/*.re4tex; do b=$(basename "$f"); mkdir -p "$fixtures/tex/${b:0:1}"; mv "$f" "$fixtures/tex/${b:0:1}/"; done
  echo "stage: TEX_RESIDENT build: texture packages fanned out into tex/0..f" >&2
fi
std_inputs=
if grep -Eq '(^|[[:space:]])QUALITY=1([[:space:]]|$)' "$build/candidate.txt" 2>/dev/null; then
  if [ -n "${STDROOMS:-}" ]; then
    std_args=(); grep -q 'TEX_RESIDENT=1' "$build/candidate.txt" 2>/dev/null && std_args+=(--tex-resident)
    # shellcheck disable=SC2086
    std_inputs=$(python3 -B "$here/stage_std.py" "$fixtures" "${std_args[@]}" $STDROOMS)
  else
    echo "stage.sh: WARNING: QUALITY=1 build staged without STDROOMS: Standard mode uses the Original packages" >&2
  fi
elif [ -n "${STDROOMS:-}" ]; then
  echo "stage: STDROOMS ignored (build without QUALITY=1)" >&2
fi
if [ -n "${ROOMFILES:-}${MIRROR_OVERLAYS:-}" ]; then
  overlay=$(mktemp -d "${TMPDIR:-/tmp}/re4dc-mirror.XXXXXX")
  cp -al "$mirror"/. "$overlay/"
  for d in ${MIRROR_OVERLAYS:-}; do
    test -d "$d" || { echo "stage: overlay $d is not a directory" >&2; exit 1; }
    (cd "$d" && find . -type f) | while read -r rel; do
      rel=${rel#./}; mkdir -p "$overlay/$(dirname "$rel")"; rm -f "$overlay/$rel"
      ln "$d/$rel" "$overlay/$rel" 2>/dev/null || cp "$d/$rel" "$overlay/$rel"
    done
  done
  for spec in ${ROOMFILES:-}; do
    rel=${spec%%=*}; src=${spec#*=}
    test -e "$overlay/$rel" || { echo "stage: $rel not in the mirror" >&2; exit 1; }
    rm -f "$overlay/$rel"; cp "$src" "$overlay/$rel"
  done
  mirror=$overlay
fi
if [ "${AICA_BANKS:-1}" = 1 ]; then
  aica=$(mktemp -d "${TMPDIR:-/tmp}/re4dc-aica.XXXXXX"); rmdir "$aica"
  python3 "$here/../aica_banks.py" disc --mirror "$mirror" --out "$aica" \
    --cache "${AICA_CACHE:-/root/probe/d367-aica-cache}" --json "$aica.json" \
    $([ "${AICA_CALL_VOICES:-0}" = 1 ] && echo --call-voices) \
    $([ "${AICA_WEAPONS:-0}" = 1 ] && echo --weapons) | tail -1
  mirror=$aica
fi
bash "$here/mkdisc-hardlink.sh" "$build/re4dc-game.elf" "$mirror" "$out" "$fixtures"
if [ -n "$aica" ]; then mv "$aica.json" "$out/aica-budget.json"; fi
{
  echo "build=$build candidate=$(cat "$build/candidate.txt" 2>/dev/null || echo '?')"
  if [ -n "${ASSETS:-}" ]; then echo "ASSETS=$ASSETS manifest-sha256=$(grep -o '"manifest_sha256": "[0-9a-f]*"' "$ASSETS"/manifest.json 2>/dev/null | cut -d'"' -f4 | cut -c1-16 | tr '
' ' ')"; fi
  if [ -n "$std_inputs" ]; then printf '%s\n' "$std_inputs"; fi
  echo "MIRROR=${MIRROR:-/root/probe/d362-mirror} ROOMFILES=${ROOMFILES:-} FIXTURES_SRC=${FIXTURES_SRC:-/root/probe/d354v7-fixtures} KEYED=${KEYED:-$base/keyed12} MESHDIR=${MESHDIR:-} MESHROOMS=${MESHROOMS:-}"
  for d in ${TEXDIRS:-}; do
    echo "TEXDIR $d re4tex=$(ls "$d"/*.re4tex | wc -l)$([ "$d" = "$vq_overlay" ] && echo " vq-report-sha256=$(sha256sum < "$d/vq-native-ui-report.json" | cut -c1-16)")"
  done
  if [ -n "$ui_report" ]; then
    echo "UI_OVERRIDES=$UI_OVERRIDES UI_SOURCE=${UI_SOURCE:-/root/re4data}"
    printf '%s\n' "$ui_report" | python3 -c 'import json,sys
for e in json.load(sys.stdin)["overrides"]:
    print("UI_OVERRIDE %(override)s sha256=%(override_sha256)s key=%(key)s %(encoding)s package-sha256=%(package_sha256)s" % e)'
  fi
} > "$out/stage-inputs.txt"
if [ -n "$ui_report" ]; then printf '%s\n' "$ui_report" > "$out/ui-overrides-report.json"; fi
if [ -n "${GDI:-}" ]; then
  gdi=${GDI_OUT:-$out/gdi}
  KOS_TOOLS_BASE=${KOS_TOOLS_BASE:-$RE4DC_KOS_BASE} \
    bash "$here/mkgdi.sh" "$build/re4dc-game.elf" "$mirror" "$gdi" "$fixtures"
  (cd "$gdi" && sha256sum disc.gdi IP.BIN track0[123].*) | tee "$gdi/gdi.sha256"
fi
bash "$here/syms.sh" "$build"
"$KOS_CC_BASE/bin/sh-elf-nm" -C "$build/re4dc-game.elf" > "$build/symbols-demangled.txt"
sha256sum "$out/disc.bin" | tee "$out/disc.sha256"

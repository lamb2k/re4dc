#!/bin/bash
# D367 recovered-game build: the D361/D362 ELF flag set plus the native static/mesh
# renderer. usage: [OWNERS=0x7F STATIC=1 MESH=1 EXTRA_MAKE="..."] build.sh <dest-dir>
# Candidate flag sets are listed in README.md (LF is the current default).
set -euo pipefail
REPO=${REPO:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
cd "$REPO"
# One build per tree (a per-tree lock, so other trees can build at the same time), and at most
# two game builds host-wide through the shared slot helper when it exists.
exec 7>"/tmp/d367-build-$(printf %s "$REPO" | md5sum | cut -c1-12).lock"
flock -n 7 || { echo "another game build is running in this tree" >&2; exit 1; }
SLOT=; [ -x /root/probe/d367-buildslot.sh ] && SLOT=/root/probe/d367-buildslot.sh
# Reproducible images: GCC takes __DATE__/__TIME__ from SOURCE_DATE_EPOCH (the VMU debug slot
# prints them). Fixed by default so A/B and knob-off identity checks compare equal; a release
# build may pass its own value.
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1790000000}
# PVR_PIPELINE=2 needs the async-present KOS (patches/README.md); other sets keep d336.
case " ${EXTRA_MAKE:-} " in *" PVR_PIPELINE=2 "*) kos_default=/root/work/kos-re4dc-d367 ;; *) kos_default=/root/work/kos-re4dc-d336 ;; esac
export RE4DC_KOS_BASE=${RE4DC_KOS_BASE:-$kos_default}
source port/dreamcast/kos-env.sh
dest=${1:?usage: build.sh <dest-dir>}
mkdir -p "$dest"
$SLOT make NATIVE_REUSE_AUDIT=0 NATIVE_RENDER_PROFILE=0 -C port/dreamcast/game -j${JOBS:-4} \
  CORE_RESIDENT_BYTES=1360608 OPTION_RESIDENT_BYTES=149920 PLAYER_RESIDENT_BYTES=846656 WEAPON_RESIDENT_BYTES=247776 \
  PARTS_DEMAND=1 MODELINFO_DEMAND=1 OBJECT_DEMAND=1 ENEMY_DEMAND=1 PVR_STREAM=1 MODEL_POSITION_CACHE=1 \
  EVENT_FILES=1 R100_DEFER_EVENTS=1 MODEL_ROOM_STRIPS=1 MODEL_DRAW_PLANS=0 D349_RENDERER_STACK=1 \
  NATIVE_STATIC=${STATIC:-1} NATIVE_STATIC_OWNERS=${OWNERS:-1} NATIVE_MESH=${MESH:-0} NATIVE_STATIC_PROBE_SKIP=${PROBE_SKIP:-0} \
  ${EXTRA_MAKE:-} >"$dest/build.log" 2>&1 || { tail -40 "$dest/build.log"; exit 1; }
cp port/dreamcast/game/re4dc-game.elf "$dest/re4dc-game.elf"
# SUBSCREEN_OVL=1 / ROUTE_OVL=1 builds: the overlays tools/link.sh wrote next to the ELF (sscrn.ovl, pl0f.ovl, em2f.ovl).
rm -f "$dest"/*.ovl
for f in port/dreamcast/game/*.ovl; do [ -f "$f" ] && { cp "$f" "$dest/"; sha256sum "$dest/${f##*/}"; }; done
"$KOS_CC_BASE/bin/sh-elf-size" "$dest/re4dc-game.elf" | tee "$dest/size.txt"
sha256sum "$dest/re4dc-game.elf" | tee "$dest/elf.sha256"
git diff --binary > "$dest/tracked.patch"
git rev-parse HEAD > "$dest/head.txt"
echo "${EXTRA_MAKE:-}" > "$dest/candidate.txt"
grep -c "warning" "$dest/build.log" || true

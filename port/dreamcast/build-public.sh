#!/usr/bin/env bash
# build-public.sh [extra make knobs...]: the play program from the public repository alone.
#
# Builds the current test release's recipe: tools/d367/build-r21.sh plus the knobs in the release's knob file
# (RELEASE_KNOBS below, written from the release build by tools/d367/release-knobs.py; nothing is copied by hand).
# ASSETS is the unpacked Build-Assets zip of that release (re4dc-assets/); without it the build uses the neutral
# headers of game/public-assets and switches off the knobs in PRIVATE_OFF below. See CONTRIBUTING-PORT.md.
#
# Output (OUT, default port/dreamcast/out-public): re4dc-game.elf, the room overlays (*.ovl) linked
# against it, resolved-knobs.txt (every knob as make resolved it) and build.log. Put it on a disc with
#   python3 port/dreamcast/tools/swap-program.py <release zip> <OUT> <new disc dir>
# and check it with python3 port/dreamcast/tools/d367/disc_lint.py <new disc dir>/disc.gdi (CONTRIBUTING-PORT.md section 8).
#
# Env: RE4DC_KOS_BASE / RE4DC_KOS_CC_BASE (from setup-toolchain.sh's env.sh or the Docker image),
#      OUT, OBJDIR (default OUT/obj; always rebuilt from scratch), JOBS (default 4),
#      ASSETS (default game/public-assets; contrib.sh points it at the release's Build-Assets zip),
#      RELEASE_KNOBS (default the line below).
# Extra arguments are make knobs and override the recipe, e.g. MY_FEATURE=1.
set -euo pipefail
PORT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# The current test release. At each test release, point this at the new test's knob file (one line).
RELEASE_KNOBS=${RELEASE_KNOBS:-$PORT/tools/d367/test24b/release-knobs.txt}

OUT=${OUT:-$PORT/out-public}
OBJDIR=${OBJDIR:-$OUT/obj}
ASSETS=${ASSETS:-$PORT/game/public-assets}
case "$OUT$OBJDIR$ASSETS" in *' '*) echo "build-public: OUT, OBJDIR and ASSETS must not contain spaces" >&2; exit 2 ;; esac
: "${RE4DC_KOS_BASE:?source the toolchain env first (tools/setup-toolchain.sh writes PREFIX/env.sh)}"
[ -f "$RE4DC_KOS_BASE/lib/dreamcast/libkallisti.a" ] || { echo "build-public: $RE4DC_KOS_BASE is not a built KOS" >&2; exit 2; }
[ -f "$RELEASE_KNOBS" ] || { echo "build-public: no knob file $RELEASE_KNOBS" >&2; exit 2; }
[ -f "$PORT/game/third_party/sh4zam/include/sh4zam/shz_xmtrx.h" ] || { echo "build-public: the SH4ZAM submodule" \
  "(port/dreamcast/game/third_party/sh4zam) is empty: run git submodule update --init" >&2; exit 2; }
ASSETS=$(cd "$ASSETS" && pwd)
rm -rf "$OBJDIR"; mkdir -p "$OUT" "$OBJDIR"
rm -f "$OUT"/re4dc-game.elf "$OUT"/*.ovl

# The release's knobs, @ASSETS@ = the Build-Assets zip's re4dc-assets/ directory.
RECIPE=$(python3 "$PORT/tools/d367/release-knobs.py" args "$RELEASE_KNOBS" "$ASSETS")
# PRIVATE_OFF: without the PS2 character data of the Build-Assets zip (ASSETS/ps2leon, ASSETS/ps2ganado: meshes compiled
# into the program) these knobs are switched off, and the program differs from the release in what it draws (gameplay
# is the same):
#   PS2_LEON=0 LEON_HAND_PACK=0      Leon is the GameCube model (the release draws the PS2 Leon, also in hand poses).
#   PS2_GANADO=0 PS2_GANADO_LIT=0    the male villagers are the GameCube models (the release: PS2 models, PS2-lit).
#   GANADO_LOD=0                     (test 15 on) no lighter villager meshes: they need the PS2 villager models and
#                                    the Build-Assets zip's glod/ganado_lod.re4gl (GANADO_LOD_PACK).
#   GANADO_EVENT_KEEP_LOD=0          (test 22 on) Ganados keep their LOD through events: needs GANADO_LOD.
#   ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 (test 15 on) only Leon takes the room-light probe (the release: the PS2 villagers
#                                    too, which needs PS2_GANADO_LIT).
#   NATIVE_MODEL_REGISTRY_DYING=0    (test 17 on) a dying Ganado fades on the GameCube model (the release keeps the PS2
#                                    model through the fade, which needs PS2_GANADO_LIT).
# The release knobs PS2_LEON_DIR / PS2_GANADO_DIR / GANADO_LOD_PACK are dropped then. The other PS2 models (El Gigante,
# Del Lago, the female villagers, animals) and the PS2 world are disc data, so they stay on and draw as in the release.
PRIVATE_OFF=
if [ ! -f "$ASSETS/ps2leon/ps2leon_runtime.h" ] || [ ! -f "$ASSETS/ps2ganado/ganado_cast_runtime.h" ]; then
  RECIPE=$(tr ' ' '\n' <<<"$RECIPE" | grep -vE '^(PS2_(LEON|GANADO)_DIR|GANADO_LOD_PACK|LEON_HEADLESS_DIR)=' | tr '\n' ' ')
  PRIVATE_OFF="PS2_LEON=0 LEON_PS2_RIG=0 LEON_PS2_PORTRAIT_HAIR=0 LEON_HAND_PACK=0 PS2_GANADO=0 PS2_GANADO_LIT=0 GANADO_LOD=0 NMR_POOL_LOD=0 GANADO_EVENT_KEEP_LOD=0 ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 NATIVE_MODEL_REGISTRY_DYING=0 LEON_HEADLESS=0"
  echo "build-public: no PS2 character data in $ASSETS: $PRIVATE_OFF (GameCube character models; see CONTRIBUTING-PORT.md)"
fi
# Test 17 on: the chapter 2-2 / 2-3 PS2 enemy rows (ASSETS/ps2enemych2/ps2_enemy_ch22_data.inc and
# ps2_enemy_ch23_data.inc, generated from the PS2 disc and compiled into the program; the knob file maps
# PS2_ENEMY_CH22_DIR / PS2_ENEMY_CH23_DIR to @ASSETS@/ps2enemych2). Without them the knobs are dropped and
#   PS2_CH2_ENEMY=0                  chapters 2-2 / 2-3 keep the GameCube enemy lists and room code (the release: the
#                                    PS2 ones, at most 6 Ganados alive), so the enemies there differ from the release.
if grep -qE '(^| )PS2_ENEMY_CH2[23]_DIR=' <<<"$RECIPE" &&
   { [ ! -f "$ASSETS/ps2enemych2/ps2_enemy_ch22_data.inc" ] || [ ! -f "$ASSETS/ps2enemych2/ps2_enemy_ch23_data.inc" ]; }; then
  RECIPE=$(tr ' ' '\n' <<<"$RECIPE" | grep -vE '^PS2_ENEMY_CH2[23]_DIR=' | tr '\n' ' ')
  PRIVATE_OFF="${PRIVATE_OFF:+$PRIVATE_OFF }PS2_CH2_ENEMY=0"
  echo "build-public: no PS2 chapter 2 enemy rows in $ASSETS: PS2_CH2_ENEMY=0 (GameCube enemy lists in 2-2 / 2-3; see CONTRIBUTING-PORT.md)"
fi


# Test 17 on: the PS2 stump / hand-pose layout header is supplied by the Build-Assets zip.
# The mesh package stays on the release disc; without the header these variant plans use the source path.
if grep -qE '(^| )ACTOR_GANADO_PS2_STUMP_DIR=' <<<"$RECIPE" &&
   [ ! -f "$ASSETS/ps2stump/ganado_ps2_stump_runtime.h" ]; then
  RECIPE=$(tr ' ' '\n' <<<"$RECIPE" | grep -vE '^ACTOR_GANADO_PS2_STUMP_DIR=' | tr '\n' ' ')
  PRIVATE_OFF="${PRIVATE_OFF:+$PRIVATE_OFF }ACTOR_GANADO_PS2_STUMP=0 ACTOR_GANADO_PS2_GRIP=0"
  echo "build-public: no PS2 stump header in $ASSETS: ACTOR_GANADO_PS2_STUMP=0 ACTOR_GANADO_PS2_GRIP=0 (GameCube stump / hand poses; see CONTRIBUTING-PORT.md)"
fi

# Test 18 on: Leon after his head comes off (LEON_HEADLESS) compiles in the PS2 neck header ASSETS/ps2leonhead/ps2leon_neck.h
# (the knob file maps LEON_HEADLESS_DIR to @ASSETS@/ps2leonhead). The head archives em/pl00.drs / em/pl08.drs are disc data
# (set garr18h). Without the header: LEON_HEADLESS=0 (that death draws Leon on the GameCube path, as in Test 17).
if grep -qE '(^| )LEON_HEADLESS_DIR=' <<<"$RECIPE" && [ ! -f "$ASSETS/ps2leonhead/ps2leon_neck.h" ]; then
  RECIPE=$(tr ' ' '\n' <<<"$RECIPE" | grep -vE '^LEON_HEADLESS_DIR=' | tr '\n' ' ')
  PRIVATE_OFF="${PRIVATE_OFF:+$PRIVATE_OFF }LEON_HEADLESS=0"
  echo "build-public: no PS2 neck header in $ASSETS: LEON_HEADLESS=0 (see CONTRIBUTING-PORT.md)"
fi

# The release builds pin __DATE__ / __TIME__ (the crash screen prints them) to this instant.
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1760000000}
t0=$(date +%s)
echo "build-public: $(sed -n 's/^# test: /test /p' "$RELEASE_KNOBS") knobs ($RELEASE_KNOBS) ASSETS=$ASSETS OUT=$OUT"
# shellcheck disable=SC2086
ASSETS=$ASSETS OBJDIR=$OBJDIR OUT=$OUT JOBS=${JOBS:-4} \
  bash "$PORT/tools/d367/build-r21.sh" $RECIPE $PRIVATE_OFF "$@" > "$OUT/build.log" 2>&1 ||
  { tail -40 "$OUT/build.log"; echo "build-public: FAILED (full log $OUT/build.log)" >&2; exit 1; }
MISSING=$PORT/game/obj/missing.txt
if [ -s "$MISSING" ]; then
  cp "$MISSING" "$OUT/missing.txt"
  echo "build-public: unresolved symbols (they link to silent stubs):"; cat "$OUT/missing.txt"
fi
echo "$RECIPE $PRIVATE_OFF $*" > "$OUT/candidate.txt"
ls "$OUT"/re4dc-game.elf "$OUT"/*.ovl >/dev/null
(cd "$OUT" && sha256sum re4dc-game.elf ./*.ovl > SHA256SUMS)
echo "build-public: ok in $(( $(date +%s) - t0 )) s"
cat "$OUT/SHA256SUMS"

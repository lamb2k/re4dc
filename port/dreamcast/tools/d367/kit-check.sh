#!/usr/bin/env bash
# kit-check.sh <knob file> <release play build dir> <release package dir>   (WSL, maintainers; CLAUDE.md rule 4)
#
# The publish gate for the public contributor kit: a test release does not publish until this passes and the two
# discs it prints boot (tools/d367/kit-boot.sh). Run it from the checkout that is being published, after the release
# commit and the kit refresh are committed (it builds a clean checkout of HEAD, not the working tree).
#   <knob file>          tools/d367/<test>/release-knobs.txt, written from the release build by
#                        release-knobs.py write (path relative to port/dreamcast, or absolute)
#   <release play build> the recipe's play build (route-build.sh out-<label>: candidate.txt, re4dc-game.elf, obj/)
#   <release package>    the directory with the release's *-GDEMU.zip and *-Build-Assets.zip
# Checks, in order (each failure stops it):
#   1 build-public.sh's default RELEASE_KNOBS is this knob file;
#   2 the knob file holds exactly the play build's knobs (release-knobs.py check);
#   3 the Build-Assets zip holds exactly the recipe's private directories and everything the release build read
#     from them (release-knobs.py zipcheck), and is the zip the knob file names;
#   4 CONTRIBUTING.md and CONTRIBUTING-PORT.md name no older test or release (release-knobs.py doclint);
#   5 a clean checkout of HEAD builds with build-public.sh: with the Build-Assets zip the program image
#     (sh-elf-objcopy -O binary) equals the release's, and the overlays too; with no assets (game/public-assets,
#     PRIVATE_OFF) it builds; the warp twin (DBG_WARP=1 TEX_CHECK=2 MCHECK_LEONGC=1) builds;
#   6 swap-program.py puts the play program (+ padscript-newgame.txt) and the warp twin (+ warp r101-entry) on the
#     release disc, on ext4 under WORK; with RACE_FIXTURE=<door103 warp fixture> also the warp twin + that fixture
#     (disc-race, for the GDEMU race gate fullplay/gdemu_gate.sh: copy it to C: once, pass - as the fixture);
#   7 every swapped disc passes disc_lint.py, loader and standard profiles (KIT_LINT_STANDARD= skips the standard
#     profile, for a release made before test 16 in the legacy layout).
# Then run, in Git Bash:  bash port/dreamcast/tools/d367/kit-boot.sh <WORK>   (Flycast: title, New Game, r101).
# Env: WORK (default /root/probe/kit-check-<test>), JOBS, RE4DC_KOS_BASE (default the maintainers' KOS), RACE_FIXTURE,
#      KIT_LINT_STANDARD.
# Builds go through /root/probe/d367-buildslot.sh when it exists (one at a time per slot).
set -euo pipefail
PORT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ROOT=$(cd "$PORT/../.." && pwd)
KF=$1; OUTR=$(cd "$2" && pwd); PKG=$(cd "$3" && pwd)
case "$KF" in /*) ;; *) KF=$PORT/$KF ;; esac
[ -f "$KF" ] || { echo "kit-check: no knob file $KF" >&2; exit 2; }
RK="python3 $PORT/tools/d367/release-knobs.py"
TEST=$(sed -n 's/^# test: //p' "$KF")
WORK=${WORK:-/root/probe/kit-check-test$TEST}
export RE4DC_KOS_BASE=${RE4DC_KOS_BASE:-/root/work/kos-re4dc-d367}
export PATH=${RE4DC_KOS_CC_BASE:-/opt/toolchains/dc/sh-elf}/bin:$PATH
SLOT=; [ -f /root/probe/d367-buildslot.sh ] && SLOT="bash /root/probe/d367-buildslot.sh"
step() { echo; echo "== kit-check $*"; }
img() { sh-elf-objcopy -R .stack -O binary "$1" "$WORK/img.bin"; sha256sum "$WORK/img.bin" | cut -c1-64; rm -f "$WORK/img.bin"; }
rm -rf "$WORK"; mkdir -p "$WORK"

step "1 build-public.sh points at $(basename "$(dirname "$KF")")/release-knobs.txt"
rel=${KF#$PORT/}
grep -q "RELEASE_KNOBS:-\$PORT/$rel}" "$PORT/build-public.sh" ||
  { echo "kit-check: build-public.sh's default RELEASE_KNOBS is not $rel:"; grep -n 'RELEASE_KNOBS:-' "$PORT/build-public.sh"; exit 1; }
echo "ok"

step "2 knob file = release recipe"
$RK check "$OUTR/candidate.txt" "$KF"

step "3 Build-Assets zip"
BA=$(ls "$PKG"/*-Build-Assets.zip); GD=$(ls "$PKG"/*-GDEMU.zip | grep -v "/RE4DC-QA-")   # not the QA disc zip
want=$(sed -n 's/^# assets-zip: //p' "$KF")
[ "$(basename "$BA")" = "$want" ] || { echo "kit-check: package has $(basename "$BA"), the knob file names $want"; exit 1; }
DS=$(sed -n 's/^# disc-sets: //p' "$KF")   # test 15 on: the disc data files carried in re4dc-assets/disc/
$RK zipcheck "$OUTR/candidate.txt" "$BA" --objdir "$OUTR/obj" ${DS:+--disc-sets "$DS"}

step "4 contributor docs"
$RK doclint "$KF" "$ROOT/CONTRIBUTING.md" "$PORT/CONTRIBUTING-PORT.md"

step "5 clean checkout of HEAD ($(git -C "$ROOT" rev-parse --short=8 HEAD)) builds"
[ -z "$(git -C "$ROOT" status --short -- port/dreamcast/build-public.sh port/dreamcast/tools/d367/release-knobs.py "$KF")" ] ||
  { echo "kit-check: commit the kit files first"; exit 1; }
git -C "$ROOT" worktree add -q --detach "$WORK/clean" HEAD
git -C "$WORK/clean" submodule update -q --init   # SH4ZAM (port/dreamcast/game/third_party/sh4zam), from its public URL
trap 'git -C "$ROOT" worktree remove --force "$WORK/clean" 2>/dev/null || true' EXIT
mkdir -p "$WORK/assets"; python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$BA" "$WORK/assets"
A=$WORK/assets/re4dc-assets
BP="bash $WORK/clean/port/dreamcast/build-public.sh"
ASSETS=$A OUT=$WORK/out-play $SLOT $BP | tail -1
ASSETS= OUT=$WORK/out-bare $SLOT $BP | grep -E 'no PS2|ok in'
ASSETS=$A OUT=$WORK/out-warp $SLOT $BP DBG_WARP=1 PC_SAMPLER=1 MCHECK_LEONGC=1 TEX_CHECK=2 | tail -1
want=$(sed -n 's/^# image-sha256: //p' "$KF"); have=$(img "$WORK/out-play/re4dc-game.elf"); rel_img=$(img "$OUTR/re4dc-game.elf")
echo "image: kit $have / release build $rel_img / knob file $want"
[ "$have" = "$want" ] && [ "$have" = "$rel_img" ] || { echo "kit-check: the kit's program image is not the release's"; exit 1; }
for f in "$OUTR"/*.ovl; do cmp "$f" "$WORK/out-play/$(basename "$f")" || { echo "kit-check: overlay $(basename "$f") differs"; exit 1; }; done
echo "overlays identical: $(cd "$OUTR" && ls ./*.ovl | xargs -n1 basename | tr '\n' ' ')"

step "6 swap onto $(basename "$GD")"
for o in play warp; do   # the log symbols for the boot gate's log reader (as route-build.sh writes syms.txt)
  sh-elf-nm "$WORK/out-$o/re4dc-game.elf" | python3 -c "
import sys; s = {f[2]: int(f[0], 16) for f in (l.split() for l in sys.stdin) if len(f) == 3}
print(' '.join(hex(s[n] - 0x8c000000) for n in ('_re4dc_logbuf', '_re4dc_log_head', '_re4dc_stage')))" > "$WORK/out-$o/syms.txt"
done
python3 "$PORT/tools/d367/warp.py" r101-entry -o "$WORK/warp.txt" >/dev/null
python3 "$PORT/tools/swap-program.py" "$GD" "$WORK/out-play" "$WORK/disc-play" \
  --add dc/padscript.txt="$PORT/tools/padscript-newgame.txt" | tail -1
python3 "$PORT/tools/swap-program.py" "$GD" "$WORK/out-warp" "$WORK/disc-warp" --add dc/warp.txt="$WORK/warp.txt" | tail -1
cp "$WORK/out-play/syms.txt" "$WORK/disc-play/syms.txt"; cp "$WORK/out-warp/syms.txt" "$WORK/disc-warp/syms.txt"
DISCS="play warp"
if [ -n "${RACE_FIXTURE:-}" ]; then   # the warp twin + a door103 fixture: the disc the GDEMU race gate runs (rule 5)
  python3 "$PORT/tools/swap-program.py" "$GD" "$WORK/out-warp" "$WORK/disc-race" --add dc/warp.txt="$RACE_FIXTURE" | tail -1
  cp "$WORK/out-warp/syms.txt" "$WORK/disc-race/syms.txt"; DISCS="$DISCS race"
fi
rm -rf "$WORK/out-bare/obj" "$WORK/out-play/obj" "$WORK/out-warp/obj"

step "7 disc_lint the swapped discs (loader + standard profiles)"
for d in $DISCS; do
  for prof in loader ${KIT_LINT_STANDARD-standard}; do
    python3 "$PORT/tools/d367/disc_lint.py" --profile $prof "$WORK/disc-$d/disc.gdi" > "$WORK/disc_lint-$prof-$d.txt" ||
      { grep -vE '^(ok|WARN) ' "$WORK/disc_lint-$prof-$d.txt"; echo "kit-check: disc-$d fails disc_lint ($prof)"; exit 1; }
    echo "disc-$d: $(tail -1 "$WORK/disc_lint-$prof-$d.txt" | sed 's#/.*/##')"
  done
done
echo
echo "KIT-CHECK BUILD OK (test $TEST). Boot gate, in Git Bash: bash port/dreamcast/tools/d367/kit-boot.sh $WORK"

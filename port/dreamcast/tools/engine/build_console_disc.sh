#!/bin/bash
# build_console_disc.sh: ONE GDEMU disc that holds every engine scene and runs them unattended in one boot
# (lane eng-loop2, 2026-11-20; docs/engine/CONSOLE_LOOP.md section 10). Run it in WSL.
#
#   build_console_disc.sh [--ref <git ref>] [--out <dir>] [--scenes A,B,..] [--drop <disc path>]...
#                         [--put <disc path>]... [--no-precheck] [--layout standard|legacy] [--title <text>]
#                         [--plan-control longcomment|fivefield|sectorend] [--r103 <farm pack> <farm visibility>]
#
# From a clean checkout of <ref> (default origin/engine: git archive of the commit, plus the SH4ZAM submodule at the
# commit <ref> records, from the local submodule clone; nothing from the working tree) it builds:
#   - the scene runner (engine/loader/selector.c): the disc's 1ST_READ.BIN and /LOADER.BIN;
#   - the engine images with SENDABLE=1 (engine/loader/sendable.mk: the console loop's client, so each hands its
#     report back): the bench (engine/bench), the E1 image (engine/game), FIGHT=1 and BOSS=1;
# and stages them with the private packs and game files below, one folder per scene, then the disc (mkgdi.sh), its
# SHA256SUMS, MANIFEST.txt (commit, program and input hashes) and a KEEP file.
#
# Scenes, in this order (the selector runs them one after another and shows the summary at the end):
#   BENCH       the E0 bench: village cross and farm hay-fork view, the cache-staging (a) and short-loop (b) arms
#               A/B/A, then the 5 ms delay / held picture control window (c0dh)
#   LEON        Leon in the village (E1 image, village route)
#   HILL        Leon and Ashley on the hill (E1 image, root file HILL)
#   FIGHT       the four-Ganado fight at the village cross (FIGHT=1)
#   BOSS-BENCH  El Gigante on the bench (the bench image with the boss pack; c0 cn c0 c0dh)
#   BOSS        El Gigante hosted (BOSS=1, headless: its drawing row is the bench's)
#   SHOT        (only when --scenes names it; lane eng-e1k) the FIGHT image playing the re4ref fixture file SHOT.TXT
#               (default tools/plays_right/fixtures/shot-ganado.txt; SHOT_FIXTURE=<file> for a control), traced: a
#               function run judged against the PC reference by tools/plays_right/shot_engine.sh, never a timing run
# FIGHTT      (only when --scenes names it; lane eng-e1p) the FIGHT image traced: a function run whose CAMLOG lines
#             (serial) check the fight's camera cut against earlier runs
# The E1-family scenes run with NOTRACE (no trace lines formatted inside the pictures). The bench scenes keep their
# ROW and MEMBLK lines out of the report (serial still has them): the report holds the WINDOW rows.
#
# Controls: --drop <disc path> removes one staged file (for example FIGHT/CROSS.PAK): the selector reports that scene
# FAILED ("missing ..."); with --no-precheck the selector does not check the files and the program itself must refuse
# (for example --drop BOSSB/FARM.PAK: "M1 native pack REFUSED"). --scenes picks a subset (short control discs).
# --plan-control (lane eng-e1p, H-018.3): a control schedule the selector must refuse whole (nothing runs).
# longcomment: the scheduled entries (name eight), then a comment line of 5,000 bytes, then a ninth entry (a copy of the
# first, named NINTH): the selector must read past 4,096 bytes and refuse nine scenes. fivefield: the scheduled entries,
# then the last one again with only its first five fields (named <name>5): a line that does not parse refuses the
# schedule (before, both were run as if the extra entry were not there). sectorend (lane eng-mem2): SCENES.TXT padded to
# 2,045 bytes mod 2,048 by a comment line: the selector must read it and run (not a refusal).
# --put <disc path> adds an empty boot-option file (lane eng-e1f), for example the late-picture control of the E1
# images: --put E1/LATEPIC --put FIGHT/LATEPIC --put BOSS/LATEPIC (picture or tick 300 held 100 ms: every E1-family
# scene must then show its worst interval, at least five fields, at picture 301, or at tick 300 when headless).
#
# Private inputs (never in git; override with the environment): PRISTINE (the little-endian game tree: st1, etc,
# em, dc/mot), LKG (E0 packs and visibility), HILL_PAK, HILL_VIS, FIGHT_PAK, FIGHT_FXMAP, BOSS_PAK, BOSS_VIS,
# BOSS_EMLIST, BOSS_EMARC. Defaults: the shared pack sets $LANES/packs/e1-wep-20261121 and e1-base-20261121 (below;
# built by the integration lane, with a receipt, from the files the lanes staged their discs with).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
REPO=$(git -C "$here" rev-parse --show-toplevel)
REF=origin/engine
OUT=
SCENES=BENCH,LEON,HILL,FIGHT,BOSS-BENCH,BOSS
TIER=plain
DROPS=()
PUTS=()
PRECHECK=1
LAYOUT=standard
TITLE='RE4DC ENGINE CONSOLE DISC'
PLANCTL=
while [ $# -gt 0 ]; do
  case $1 in
    --ref) REF=$2; shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    --scenes) SCENES=$2; shift 2 ;;
    --tier) TIER=$2; shift 2 ;;   # lane eng-mem1 (H-031): calibrated | console | plain (default): see TIERCAL below
    --drop) DROPS+=("$2"); shift 2 ;;
    --put) PUTS+=("$2"); shift 2 ;;
    --no-precheck) PRECHECK=0; shift ;;
    --layout) LAYOUT=$2; shift 2 ;;
    --title) TITLE=$2; shift 2 ;;
    --plan-control) PLANCTL=$2; shift 2 ;;
    --r103) R103_PAK=$2; R103_VIS=$3; shift 3 ;;   # lane eng-mem2: DOOR's farm pack and visibility (default: the shared set's)
    *) echo "build_console_disc: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$OUT" ] || { echo "build_console_disc: --out <dir> is required" >&2; exit 2; }

PRISTINE=${PRISTINE:-/root/work/lanes/eng-bench/.m1/pristine}
# Default packs live in shared, immutable sets under $LANES/packs/<set>/, written only by the integration lane with a
# receipt (integrator, 2026-11-21); no default points into a lane folder.
#   e1-wep-20261121: eng-e1i's packs after bake/hud_fix.py (the HUD widgets made right; SERVICES.md 45) with Leon's PS2
#     handgun models added by bake/weapon_model.py (lane eng-look1): lkg-wep/ (CROSS.PAK; FARM.PAK and the .VIS files are
#     eng-look's unchanged), hill2-wep.pak, fight-wep.pak
#   e1-base-20261121: the other inputs as the lanes staged them (hill visibility eng-e1d, the fight's effect map eng-e2,
#     El Gigante's bench pack eng-e1f's re-bake with the effect records' glow header (eng-boss's boss2-full.pak is refused
#     at pack-loader stage 5, the control), its visibility and archives eng-boss)
LANES=${LANES:-/mnt/e/RE4DC-Lanes}
WEPSET=$LANES/packs/e1-wep-20261121
BASESET=$LANES/packs/e1-base-20261121
LKG=${LKG:-$WEPSET/lkg-wep}
HILL_PAK=${HILL_PAK:-$WEPSET/hill2-wep.pak}
HILL_VIS=${HILL_VIS:-$BASESET/hill1.vis}
FIGHT_PAK=${FIGHT_PAK:-$WEPSET/fight-wep.pak}
FIGHT_FXMAP=${FIGHT_FXMAP:-$BASESET/FXMAP.BIN}
BOSS_PAK=${BOSS_PAK:-$BASESET/boss3-full.pak}
BOSS_VIS=${BOSS_VIS:-$BASESET/boss2-full.vis}
BOSS_EMLIST=${BOSS_EMLIST:-$BASESET/EMLIST.BIN}
BOSS_EMARC=${BOSS_EMARC:-$BASESET/EM2B.ARC}
for f in "$LKG/CROSS.PAK" "$LKG/FARM.PAK" "$LKG/CROSS.VIS" "$LKG/FARM.VIS" "$HILL_PAK" "$HILL_VIS" "$FIGHT_PAK" \
         "$FIGHT_FXMAP" "$BOSS_PAK" "$BOSS_VIS" "$BOSS_EMLIST" "$BOSS_EMARC" "$PRISTINE/etc/core.das"; do
  [ -s "$f" ] || { echo "build_console_disc: private input missing: $f" >&2; exit 1; }
done

WORK=${WORK:-$REPO/.cdisc-work}
SRC=$WORK/src; B=$WORK/build; D=$WORK/data
rm -rf "$WORK"; mkdir -p "$SRC" "$B" "$D"
log() { echo "[cdisc $(date +%H:%M:%S)] $*"; }

# ---- clean checkout of REF (and the SH4ZAM submodule at the recorded commit)
COMMIT=$(git -C "$REPO" rev-parse --verify "$REF^{commit}")
SHORT=$(git -C "$REPO" rev-parse --short=9 "$COMMIT")
log "checkout $REF = $COMMIT"
# lane eng-e1n: the selector runs at most SEL_MAX scenes (engine/loader/selector.c, as REF has it); a longer list is
# refused here, before anything is built (no disc). The selector refuses such a SCENES.TXT itself too.
SELMAX=$(git -C "$REPO" show "$COMMIT:port/dreamcast/engine/loader/selector.c" | sed -n 's/^#define SEL_MAX \([0-9][0-9]*\).*/\1/p')
NSCENES=$(echo "$SCENES" | tr ',' '\n' | grep -c .)
[ -n "$SELMAX" ] || { echo "build_console_disc: SEL_MAX not found in $REF's engine/loader/selector.c" >&2; exit 1; }
if [ "$NSCENES" -gt "$SELMAX" ]; then
  echo "build_console_disc: --scenes names $NSCENES scenes, the selector runs at most $SELMAX (SEL_MAX): refused, no disc" >&2
  exit 1
fi
git -C "$REPO" archive --format=tar "$COMMIT" | tar -x -C "$SRC"
SZP=port/dreamcast/game/third_party/sh4zam
SZC=$(git -C "$REPO" ls-tree "$COMMIT" "$SZP" | awk '{print $3}')
[ -n "$SZC" ] || { echo "build_console_disc: $REF records no SH4ZAM commit" >&2; exit 1; }
git -C "$REPO/$SZP" cat-file -e "$SZC^{commit}" 2>/dev/null ||
  { echo "build_console_disc: SH4ZAM commit $SZC is not in $REPO/$SZP (git -C $SZP fetch)" >&2; exit 1; }
mkdir -p "$SRC/$SZP"; git -C "$REPO/$SZP" archive --format=tar "$SZC" | tar -x -C "$SRC/$SZP"

# ---- build (KOS d367, the release toolchain)
export RE4DC_KOS_BASE=${RE4DC_KOS_BASE:-/root/work/kos-re4dc-d367}
cd "$SRC"
set +u; . port/dreamcast/kos-env.sh; set -u
ENG=port/dreamcast/engine
BUILD="cdisc-$SHORT"
mk() {   # mk <name> <dir> <args...>
  local name=$1 dir=$2; shift 2
  log "build $name"
  # -j4: the shared machine's limit (the lanes' common brief)
  make -C "$dir" -j4 "$@" > "$B/$name-make.log" 2>&1 || { grep -n "error" "$B/$name-make.log" | head -20; tail -5 "$B/$name-make.log"; exit 1; }
}
mk selector $ENG/loader OUT="$B/loader" BUILD="$BUILD" selector
mkdir -p "$B/packdir"; ln -sf "$LKG/CROSS.PAK" "$B/packdir/cross.pak"; ln -sf "$LKG/FARM.PAK" "$B/packdir/hayfork.pak"
mk bench $ENG/bench OUT="$B/bench" PRIVATE_PACK_DIR="$B/packdir" SENDABLE=1 native
mk e1 $ENG/game OUT="$B/e1" SENDABLE=1
mk fight $ENG/game OUT="$B/fight" FIGHT=1 SENDABLE=1
mk boss $ENG/game OUT="$B/boss" BOSS=1 SENDABLE=1
for e in "$B/bench/native.elf" "$B/e1/e1.elf" "$B/fight/e1.elf" "$B/boss/e1.elf"; do
  grep -q '_cl_send_start$' <(sh-elf-nm "$e") || { echo "build_console_disc: $e has no console loop client" >&2; exit 1; }
done

# ---- stage: one folder per scene (the programs open /cd/<file>; root=<dir> makes it /cd/<dir>/<file> first)
log "stage"
bin() { sh-elf-objcopy -R .stack -O binary "$1" "$2"; }
mkdir -p "$D/PROG"
cp "$B/loader/SELECTOR.BIN" "$D/LOADER.BIN"
bin "$B/bench/native.elf" "$D/PROG/BENCH.BIN"
bin "$B/e1/e1.elf" "$D/PROG/E1.BIN"
bin "$B/fight/e1.elf" "$D/PROG/FIGHT.BIN"
bin "$B/boss/e1.elf" "$D/PROG/BOSS.BIN"
P=$PRISTINE
put() { mkdir -p "$(dirname "$D/$2")"; cp "$1" "$D/$2"; }
# lane eng-load2: the engine images' packs, version 5 (frame 0 of the recording only; bake/engine_pack.py, converted here
# from the shared set's whole packs, each with a receipt line in MANIFEST.txt). The bench scenes (BENCH, BOSSB) keep the
# whole packs: the bench plays the recording and refuses a version 5 pack.
epack() {   # epack <whole pack> <disc path> [--stream-end]
  mkdir -p "$(dirname "$D/$2")"
  python3 "$SRC/port/dreamcast/engine/bake/engine_pack.py" "$1" "$D/$2" --receipt "$WORK/PACKS.txt" ${3:-} > /dev/null ||
    { echo "build_console_disc: engine_pack refused $1" >&2; exit 1; }
}
mots() {   # mots <archive> <scene dir>: the motion clips the archive lists
  python3 "$SRC/port/dreamcast/tools/engine/mot_list.py" "$1" | while read -r m; do put "$P/dc/mot/$m" "$2/dc/mot/$m"; done
}
# BENCH: the E0 bench
# lane eng-mem1 (H-031 ruling 2): the run's tier, declared on the disc. The selector applies H-025.1's sound ceilings only
# on a disc that declares the calibrated tier (TIERCAL: the console-like Flycast, dynarec on, Sh4Clock 70) or the console
# (TIERCON); a plain disc prints the sound row "not judged (plain run)".
case $TIER in
  calibrated) mkdir -p "$D"; echo "calibrated tier: console-like Flycast, Dynarec.Enabled yes, Sh4Clock 70" > "$D/TIERCAL" ;;
  console) mkdir -p "$D"; echo "console" > "$D/TIERCON" ;;
  plain) ;;
  *) echo "build_console_disc: --tier calibrated|console|plain, not '$TIER'"; exit 2 ;;
esac
put "$LKG/CROSS.PAK" BENCH/CROSS.PAK; put "$LKG/FARM.PAK" BENCH/FARM.PAK
put "$LKG/CROSS.VIS" BENCH/CROSS.VIS; put "$LKG/FARM.VIS" BENCH/FARM.VIS
printf 'c0 f0 ca c0 cb c0 fa f0 fb f0 c0dh\n' > "$D/BENCH/SCHEDULE.TXT"
# E1: Leon in the village and (with E1H/HILL in front) Leon and Ashley on the hill. The renderer sizes its pack buffer
# from CROSS.PAK and FARM.PAK, so FARM.PAK is the hill pack's twin (as lane eng-e1d's disc).
epack "$LKG/CROSS.PAK" E1/CROSS.PAK; put "$LKG/CROSS.VIS" E1/CROSS.VIS
epack "$HILL_PAK" E1/HILL.PAK; put "$D/E1/HILL.PAK" E1/FARM.PAK; put "$HILL_VIS" E1/HILL.VIS
for f in st1/r101.arc st1/r11d.arc etc/core.das em/pl00.drs em/wep02.drs em/pl11.drs; do put "$P/$f" "E1/$f"; done
mots "$P/em/pl11.drs" E1
mkdir -p "$D/E1H"; : > "$D/E1H/HILL"
# lane eng-snd1 (H-025.1): the sound the scenes load before play (services/sound/snd_svc.cpp): the rooms' ROOM and FOOT banks
# (st1/<room>.dar) and the sound system files; the characters' banks are in the archives above. From the game tree.
SNDSYS="bgm/bio4str.hed bgm/bio4midi.hed bgm/bio4midi.dat bgm/doorse.hed bgm/doorse.dat bgm/bgmtbl.dat"
for f in st1/r101.dar st1/r11d.dar $SNDSYS; do put "$P/$f" "E1/$f"; done
# lane eng-e1o: NOTRACE sits in each timing scene's own folder (E1L, E1H), not in E1, so the traced and stills scenes below
# can run the same files without it
mkdir -p "$D/E1L"; : > "$D/E1L/NOTRACE"; : > "$D/E1H/NOTRACE"
# FIGHT: the trimmed village pack, its effect map, the Ganado module and motion
epack "$FIGHT_PAK" FIGHT/CROSS.PAK; put "$D/FIGHT/CROSS.PAK" FIGHT/FARM.PAK; put "$FIGHT_FXMAP" FIGHT/FXMAP.BIN
put "$LKG/CROSS.VIS" FIGHT/CROSS.VIS
for f in st1/r101.arc etc/core.das etc/emleon00.esl em/pl00.drs em/wep02.drs em/em15.drs; do put "$P/$f" "FIGHT/$f"; done
mots "$P/em/em15.drs" FIGHT
# lane eng-e1p: NOTRACE in FIGHT's own folder FIGHTL (as E1L, E1H), so FIGHTT can run the same files traced
mkdir -p "$D/FIGHTL"; : > "$D/FIGHTL/NOTRACE"
for f in st1/r101.dar $SNDSYS; do put "$P/$f" "FIGHT/$f"; done   # lane eng-snd1: the fight's sound
# BOSSB: the bench image with El Gigante's pack in both slots (the buffer is sized once)
put "$BOSS_PAK" BOSSB/CROSS.PAK; put "$BOSS_PAK" BOSSB/FARM.PAK; put "$BOSS_VIS" BOSSB/CROSS.VIS; put "$BOSS_VIS" BOSSB/FARM.VIS
printf 'c0 cn c0 c0dh\n' > "$D/BOSSB/SCHEDULE.TXT"
# BOSS: El Gigante hosted, headless
put "$BOSS_EMARC" BOSS/EM2B.ARC; put "$BOSS_EMLIST" BOSS/EMLIST.BIN
for f in st1/r119.arc etc/core.das em/pl08.drs em/wep02.drs em/em2b.drs; do put "$P/$f" "BOSS/$f"; done
: > "$D/BOSS/HEADLESS"; : > "$D/BOSS/NOTRACE"
for f in st1/r119.dar $SNDSYS; do put "$P/$f" "BOSS/$f"; done   # lane eng-snd1: the arena's sound
# SHOT (lane eng-e1k; not in the default scene list): the FIGHT image playing a re4ref fixture file, the shot judged
# against the PC reference's trace (tools/plays_right/shot_engine.sh). SHOT_FIXTURE overrides the fixture (a control).
# Its controls, each a scene of its own (every one must FAIL the judgement): SHOTNP the fixture without the press at
# tick 160 (no hit), SHOTDMG a wrong damage amount planted in the engine, SHOTLATE every hit taken 30 ticks late.
case ",$SCENES," in *,SHOT*)
  put "${SHOT_FIXTURE:-$SRC/port/dreamcast/tools/plays_right/fixtures/shot-ganado.txt}" SHOT/SHOT.TXT
  mkdir -p "$D/SHOTNP" "$D/SHOTD" "$D/SHOTL"
  grep -v -E '^pad 16[02] ' "$D/SHOT/SHOT.TXT" > "$D/SHOTNP/SHOT.TXT"
  : > "$D/SHOTD/SHOTDMG"; : > "$D/SHOTL/SHOTLATE" ;;
esac
# KNOCK (lane eng-e2f; only when --scenes names it): the FIGHT image playing tools/plays_right/fixtures/knock-ganado.txt
# (the knock-down: one Ganado dies beside another), judged against the PC reference by tools/plays_right/shot_engine.py
# --fixture <that file> --scenes KNOCK:PASS,KNOCKNT:FAIL:knock --main KNOCK. Its control KNOCKNT, a scene of its own, runs
# without the damage table's tick (boot file DMGNOTICK) and must FAIL.
case ",$SCENES," in *,KNOCK*)
  put "$SRC/port/dreamcast/tools/plays_right/fixtures/knock-ganado.txt" KNOCK/SHOT.TXT
  mkdir -p "$D/KNOCKN"; : > "$D/KNOCKN/DMGNOTICK" ;;
esac

# The record's controls (lane eng-e1k: CROWDUP to CSTACK; lane eng-e1o, H-017.6 and H-017.7: CCAM0 to CKIND), each the
# Leon scene (E1 image, village route) run from its own folder with one boot file (core/e1_core.h lists them), staged
# only when --scenes names it. <name>|<folder>|<boot file>|<schedule kind>|<title>. Each must FAIL with the reason
# CONSOLE_LOOP.md section 12 gives; CKIND is refused by the selector before it runs (a kind without run and mode).
CONTROLS=(
  "CROWDUP|CRD|ROWDUP|e1:timing:drawn|Control:_repeated_row"
  "CNOFLIP|CNF|NOFLIP|e1:timing:drawn|Control:_no_flips"
  "CQDROP|CQD|QDROP|e1:timing:drawn|Control:_queue_drop"
  "CSTACK|CSX|STACKX|e1:timing:drawn|Control:_stack_overrun"
  "CCAM0|CC0|CAMREC0|e1:timing:drawn|Control:_no_camera_tick_checked"
  "CMEMCUT|CMC|MEMCUT|e1:timing:drawn|Control:_memory_line_cut"
  "CRUNFN|CRF|RUNFUNC|e1:timing:drawn|Control:_function_label_on_a_timing_scene"
  "CNUMTXT|CNT|NUMTEXT|e1:timing:drawn|Control:_text_where_a_number_belongs"
  "COPENX|COX|OPENX|e1:timing:drawn|Control:_boot_file_opened_at_picture_100"
  "CHEADM|CHM|HEADLESS|e1:timing:drawn|Control:_headless_image_on_a_drawn_scene"
  "CKIND|CKD|NOTRACE|e1|Control:_schedule_kind_without_run_and_mode"
)
for c in "${CONTROLS[@]}"; do
  IFS='|' read -r cn cdir cfile ckind ctitle <<< "$c"
  case ",$SCENES," in *,$cn,*) mkdir -p "$D/$cdir"; : > "$D/$cdir/$cfile" ;; esac
done
# Lane eng-e1n (H-017.4, H-017.5): the publication and HUD controls, each a scene of its own staged only when --scenes
# names it. <name>|<folder>|<boot files>|<schedule kind>|<title>|<program>|<the folders behind it>. CPUBCP (the camera
# record copied once a tick, Leon's scene) and CLMISS (every light view refused, the hill: Ashley is lit through hers)
# must FAIL in the selector ("PUB: camera copies N" / "light-view misses N"); CHUDFZ (the HUD's ammo count frozen at
# open, the fight with stills) is a function run the selector passes: tools/engine/hudcheck.py must FAIL on its stills.
E1N_CONTROLS=(
  "CPUBCP|CPB|PUBCOPY|e1:timing:drawn|Control:_camera_record_copied_each_tick|PROG/E1.BIN|E1L:E1"
  "CLMISS|CLM|LIGHTMISS|e1:timing:drawn|Control:_light_view_refused|PROG/E1.BIN|E1H:E1"
  "CHUDFZ|CHF|HUDFREEZE,STILLS|e1:function:drawn|Control:_HUD_count_frozen_(hudcheck)|PROG/FIGHT.BIN|FIGHTL:FIGHT"
)
# Lane eng-e1p (H-018), same format: each must FAIL in the selector with the reason CONSOLE_LOOP.md section 13 gives.
# CCUTCONV the fight with its camera cut converted at the switch, in play ("camera tracks converted in play 1"); CTRKSZ
# the track store limited to 1024 bytes (the room refused at load: "E1 load: camera tracks refused"); CMALFREE the
# after-play line without mallinfo free; CTICK1 E1 DONE and E1 CAMREC both 1 (against 640 rows); CROWTOK row 300's
# fields value "2,missing"; CREADX a disc file opened before play and read at picture 100 (reads and sector requests).
E1P_CONTROLS=(
  "CCUTCONV|CCC|CUTCONV|e1:timing:drawn|Control:_camera_track_converted_at_the_cut|PROG/FIGHT.BIN|FIGHTL:FIGHT"
  "CTRKSZ|CTS|CAMSTORE|e1:timing:drawn|Control:_camera_track_store_too_small|PROG/E1.BIN|E1L:E1"
  "CMALFREE|CMF|MEMNOFREE|e1:timing:drawn|Control:_mallinfo_free_dropped|PROG/E1.BIN|E1L:E1"
  "CTICK1|CT1|TICKS1|e1:timing:drawn|Control:_tick_and_camera_counts_1|PROG/E1.BIN|E1L:E1"
  "CROWTOK|CRT|ROWTOKEN|e1:timing:drawn|Control:_row_value_with_a_trailing_token|PROG/E1.BIN|E1L:E1"
  "CREADX|CRX|READX|e1:timing:drawn|Control:_disc_file_read_at_picture_100|PROG/E1.BIN|E1L:E1"
)
# Lane eng-look1, same format: Leon's weapon. NOWEP (boot file) leaves every weapon undrawn. CNOWEP, CNOWEPH, CNOWEPF
# (village, hill, fight timing runs) must FAIL in the selector ("weapon: visible N drawn 0"); they are also the "without"
# arm of the weapon's drawing cost. CNWLS, CNWHS, CNWFS are the same scenes' stills runs with the weapon undrawn:
# the reference tools/engine/wepcheck.py compares LEONS, HILLS and FIGHTS against, and its control (wepcheck must FAIL
# when one is checked against itself or put in place of the scene with the weapon). They FAIL in the selector too.
ELOOK_CONTROLS=(
  "CNOWEP|CNW|NOWEP|e1:timing:drawn|Control:_weapon_undrawn|PROG/E1.BIN|E1L:E1"
  "CNOWEPH|CNH|NOWEP|e1:timing:drawn|Control:_weapon_undrawn_(hill)|PROG/E1.BIN|E1H:E1"
  "CNOWEPF|CNF2|NOWEP|e1:timing:drawn|Control:_weapon_undrawn_(fight)|PROG/FIGHT.BIN|FIGHTL:FIGHT"
  "CNWLS|CNWL|NOWEP,STILLS|e1:function:drawn|Control:_weapon_undrawn_stills_(wepcheck)|PROG/E1.BIN|E1L:E1"
  "CNWHS|CNWH|NOWEP,STILLS|e1:function:drawn|Control:_weapon_undrawn_stills_(hill)|PROG/E1.BIN|E1H:E1"
  "CNWFS|CNWF|NOWEP,STILLS|e1:function:drawn|Control:_weapon_undrawn_stills_(fight)|PROG/FIGHT.BIN|FIGHTL:FIGHT"
)
# Lane eng-snd1 (H-025.1): the sound's controls, same format. CSNDSLOW (1,500 us inside every audio step): the selector
# must FAIL it ("sound over H-025.1"). CSNDMUTE (every channel at total attenuation, the fight, a run with the audio
# capture): the scene runs, engine/services/sound/tools/audiocheck.py must FAIL its capture. CSNDDROP (the first request
# from tick 100 not passed on, the traced village): engine/services/sound/tools/sndreq_check.py must FAIL it against the
# PC reference. CSEED0 (the traced village with its behaviour generator left at 0, as before request R9): the same
# check must FAIL on the footsteps' positions (ticks 547-569). ASNDOFF is not a control but the "off" arm of the cost comparison (no sound started): it must stay OK.
SND_CONTROLS=(
  "CSNDSLOW|CSS|SNDSLOW|e1:timing:drawn|Control:_sound_over_its_ceiling|PROG/E1.BIN|E1L:E1"
  "CSNDMUTE|CSM|SNDMUTE|e1:timing:drawn|Control:_sound_muted_(audiocheck)|PROG/FIGHT.BIN|FIGHTL:FIGHT"
  "CSNDDROP|CSD|SNDDROP|e1:function:drawn|Control:_a_sound_request_dropped_(sndreq_check)|PROG/E1.BIN|E1"
  "ASNDOFF|ASO|SNDOFF|e1:timing:drawn|Arm:_sound_off_(cost_comparison)|PROG/E1.BIN|E1L:E1"
  "CSEED0|CS0|SEED0|e1:function:drawn|Control:_village_seed_left_at_0_(sndreq_check)|PROG/E1.BIN|E1"
)
for c in "${E1N_CONTROLS[@]}" "${E1P_CONTROLS[@]}" "${ELOOK_CONTROLS[@]}" "${SND_CONTROLS[@]}"; do
  IFS='|' read -r cn cdir cfiles ckind ctitle cprog croot <<< "$c"
  case ",$SCENES," in *,$cn,*) mkdir -p "$D/$cdir"; for f in ${cfiles//,/ }; do : > "$D/$cdir/$f"; done ;; esac
done
# DOOR (lane eng-load1; only when --scenes names it): the E1 image walking Leon from the village square (r101) to the farm
# (r103) through the game's door and back, the fixture tools/plays_right/fixtures/door-r101-r103.txt (DOOR_FIXTURE=<file>
# overrides) as /cd/DOOR.TXT; the farm's archive and whole-room bake (the bench's FARM.PAK and FARM.VIS) beside it. A
# traced function run: the selector judges the loads, both rooms' ticks, the round trip's memory marks and play's disc
# counters (door=2); tools/plays_right judges Leon against the PC reference on the serial line's LT lines.
# Its controls, each a scene of its own (DOOR_CONTROLS): CDOORPK the farm's archive absent (FAILED: "E1 load: missing", no
# hang), CDOORRD a disc read placed in play after the first door (FAILED: disc in play), CDOORLK one block kept across
# the first leave (FAILED: round trip LEAK), and CDISCF (must stay OK) the first DMA transfer of the first load reported
# done without it: the read-safety layer must catch it and read again (E1 DISCSAFE not-landed 1, latched 1).
DOOR_CONTROLS=(
  "CDOORRD|CDR|DOORREADX|Control:_disc_read_in_play_after_the_door"
  "CDOORLK|CDL|MEMKEEP|Control:_a_block_kept_across_the_leave"
  "CDISCF|CDF|DISCFAIL|Check:_DMA_reported_done_without_the_transfer"
)
case ",$SCENES," in *,DOOR*|*,CDOOR*|*,CDISCF,*)
  put "${DOOR_FIXTURE:-$SRC/port/dreamcast/tools/plays_right/fixtures/door-r101-r103.txt}" DOOR/DOOR.TXT
  # the farm's bake as R103.PAK, not FARM.PAK: the renderer sizes its resident block from CROSS.PAK and FARM.PAK (E1's
  # FARM.PAK is the hill pack's twin); the bench's farm bake there needs 1.88 MB more and put the KOS heap into the
  # behaviour arena (lane eng-load1, run 2). Default: the farm bake of the shared set ($LKG, never a lane folder);
  # R103_PAK / R103_VIS override it
  R103_PAK=${R103_PAK:-$LKG/FARM.PAK}; R103_VIS=${R103_VIS:-$LKG/FARM.VIS}
  epack "$R103_PAK" DOOR/R103.PAK; put "$R103_VIS" DOOR/R103.VIS; put "$P/st1/r103.arc" DOOR/st1/r103.arc
  # CDOORPK: its own folder with the fixture and the farm's bake but not its archive (E1 has none either)
  put "$D/DOOR/DOOR.TXT" CDP/DOOR.TXT; put "$D/DOOR/R103.PAK" CDP/R103.PAK; put "$R103_VIS" CDP/R103.VIS
  # lane eng-load2: DOORV4 (a lab arm, the load-time comparison's base): the same scene with the whole version 4 packs
  # (the frame-0 path over the recording, as before this lane). DOORSE: the farm's pack converted with --stream-end (its
  # size 2,017..2,047 modulo 2,048: its last bytes end the DMA stream through fs_iso9660's 32-byte request), which must
  # load; its control CDOORSE (boot file DISCNB: that request passed on non-blocking, as KOS makes it) must stop there
  # (no result: run it last, or on a disc of its own)
  put "$LKG/CROSS.PAK" DV4/CROSS.PAK; put "$R103_PAK" DV4/R103.PAK
  epack "$R103_PAK" DSE/R103.PAK --stream-end; put "$D/DSE/R103.PAK" CDSE/R103.PAK; : > "$D/CDSE/DISCNB"
  for c in "${DOOR_CONTROLS[@]}"; do IFS='|' read -r cn cdir cfile ctitle <<< "$c"; mkdir -p "$D/$cdir"; : > "$D/$cdir/$cfile"; done ;;
esac
case ",$SCENES," in *,HILLT,*) mkdir -p "$D/E1HT"; : > "$D/E1HT/HILL" ;; esac
case ",$SCENES," in *,LEONS,*) mkdir -p "$D/E1LS"; : > "$D/E1LS/STILLS" ;; esac
case ",$SCENES," in *,HILLS,*) mkdir -p "$D/E1HS"; : > "$D/E1HS/STILLS" ;; esac
case ",$SCENES," in *,FIGHTS,*) mkdir -p "$D/FIGHTS"; : > "$D/FIGHTS/STILLS" ;; esac

# ---- the plan: <name> <title> <program> <deadline s> <kind> <files that must exist> <args>
need() { [ "$PRECHECK" = 1 ] && echo "$1" || echo -; }
{
  echo "# RE4DC console disc $SHORT ($REF), $(date -u +%FT%TZ). Selector: engine/loader/selector.c"
  echo "BENCH Bench:_village_cross,_hay-fork PROG/BENCH.BIN 900 bench $(need BENCH/CROSS.PAK,BENCH/FARM.PAK,BENCH/CROSS.VIS,BENCH/FARM.VIS,BENCH/SCHEDULE.TXT) root=BENCH rows=skip skip=T,MEMBLK"
  echo "LEON Leon_in_the_village PROG/E1.BIN 300 e1:timing:drawn $(need E1L/NOTRACE,E1/CROSS.PAK,E1/CROSS.VIS,E1/FARM.PAK,E1/st1/r101.arc,E1/etc/core.das,E1/em/pl00.drs,E1/em/wep02.drs) root=E1L:E1 rows=compact"
  echo "HILL Leon_and_Ashley_on_the_hill PROG/E1.BIN 300 e1:timing:drawn $(need E1H/HILL,E1H/NOTRACE,E1/HILL.PAK,E1/HILL.VIS,E1/FARM.PAK,E1/st1/r11d.arc,E1/etc/core.das,E1/em/pl00.drs,E1/em/pl11.drs) root=E1H:E1 rows=compact"
  echo "FIGHT Four_Ganados_at_the_cross PROG/FIGHT.BIN 300 e1:timing:drawn $(need FIGHTL/NOTRACE,FIGHT/CROSS.PAK,FIGHT/FARM.PAK,FIGHT/FXMAP.BIN,FIGHT/st1/r101.arc,FIGHT/etc/core.das,FIGHT/etc/emleon00.esl,FIGHT/em/em15.drs) root=FIGHTL:FIGHT rows=compact"
  echo "BOSS-BENCH El_Gigante_on_the_bench PROG/BENCH.BIN 600 bench $(need BOSSB/CROSS.PAK,BOSSB/FARM.PAK,BOSSB/CROSS.VIS,BOSSB/SCHEDULE.TXT) root=BOSSB rows=skip skip=T,MEMBLK"
  echo "BOSS El_Gigante_hosted_(headless) PROG/BOSS.BIN 300 e1:timing:headless $(need BOSS/EM2B.ARC,BOSS/EMLIST.BIN,BOSS/st1/r119.arc,BOSS/etc/core.das,BOSS/em/em2b.drs,BOSS/em/pl08.drs) root=BOSS rows=compact"
  SHOTNEED=FIGHT/CROSS.PAK,FIGHT/FARM.PAK,FIGHT/FXMAP.BIN,FIGHT/st1/r101.arc,FIGHT/etc/core.das,FIGHT/etc/emleon00.esl,FIGHT/em/em15.drs
  echo "SHOT Shot_fixture_(traced,_not_timing) PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOT/SHOT.TXT,$SHOTNEED) root=SHOT:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "SHOTNP Shot_control:_no_press PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOTNP/SHOT.TXT,$SHOTNEED) root=SHOTNP:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "SHOTDMG Shot_control:_wrong_damage PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOTD/SHOTDMG,SHOT/SHOT.TXT,$SHOTNEED) root=SHOTD:SHOT:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "SHOTLATE Shot_control:_hit_1_s_late PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOTL/SHOTLATE,SHOT/SHOT.TXT,$SHOTNEED) root=SHOTL:SHOT:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "KNOCK Knock-down_fixture_(traced,_not_timing) PROG/FIGHT.BIN 300 e1:function:drawn $(need KNOCK/SHOT.TXT,$SHOTNEED) root=KNOCK:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "KNOCKNT Knock-down_control:_no_damage_tick PROG/FIGHT.BIN 300 e1:function:drawn $(need KNOCKN/DMGNOTICK,KNOCK/SHOT.TXT,$SHOTNEED) root=KNOCKN:KNOCK:FIGHT rows=compact skip=T,LT,LE,LL"
  # lane eng-e1o: function runs of the same images (only when --scenes names them; never timing): LEONT and HILLT traced
  # (no NOTRACE: the trace lines go to the serial line, kept out of the report), LEONS, HILLS and FIGHTS hand over stills
  # (STILLS: tick 1 and every 40th; the Flycast runner reads them)
  TSKIP="skip=T,LT,LE,LL,A,R,CAMLOG,CD"
  echo "LEONT Leon_traced_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1/CROSS.PAK,E1/st1/r101.arc) root=E1 rows=compact $TSKIP"
  echo "HILLT Hill_traced_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1HT/HILL,E1/HILL.PAK,E1/st1/r11d.arc) root=E1HT:E1 rows=compact $TSKIP"
  echo "LEONS Leon_stills_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1LS/STILLS,E1L/NOTRACE,E1/CROSS.PAK) root=E1LS:E1L:E1 rows=compact"
  echo "HILLS Hill_stills_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1HS/STILLS,E1H/HILL,E1/HILL.PAK) root=E1HS:E1H:E1 rows=compact"
  echo "FIGHTS Fight_stills_(function_run) PROG/FIGHT.BIN 300 e1:function:drawn $(need FIGHTS/STILLS,FIGHTL/NOTRACE,FIGHT/CROSS.PAK) root=FIGHTS:FIGHTL:FIGHT rows=compact"
  echo "FIGHTT Fight_traced_(function_run) PROG/FIGHT.BIN 300 e1:function:drawn $(need FIGHT/CROSS.PAK,FIGHT/st1/r101.arc,FIGHT/em/em15.drs) root=FIGHT rows=compact $TSKIP"
  # lane eng-load1: the DOOR scene and its controls (door=2: two room loads, three visits, the round trip)
  DNEED=DOOR/DOOR.TXT,DOOR/R103.PAK,DOOR/R103.VIS,DOOR/st1/r103.arc,E1/CROSS.PAK,E1/FARM.PAK,E1/st1/r101.arc,E1/etc/core.das,E1/em/pl00.drs,E1/em/wep02.drs
  echo "DOOR Village_to_farm_and_back_(traced,_function_run) PROG/E1.BIN 300 e1:function:drawn $(need $DNEED) root=DOOR:E1 rows=compact $TSKIP door=2"
  echo "DOORV4 Lab_arm:_door,_version_4_packs PROG/E1.BIN 300 e1:function:drawn $(need DV4/CROSS.PAK,DV4/R103.PAK,$DNEED) root=DV4:DOOR:E1 rows=compact $TSKIP door=2"
  echo "DOORSE Door,_farm_pack_ending_the_stream PROG/E1.BIN 300 e1:function:drawn $(need DSE/R103.PAK,$DNEED) root=DSE:DOOR:E1 rows=compact $TSKIP door=2"
  echo "CDOORSE Control:_stream_end_non-blocking_(stops) PROG/E1.BIN 300 e1:function:drawn $(need CDSE/DISCNB,CDSE/R103.PAK,$DNEED) root=CDSE:DOOR:E1 rows=compact $TSKIP door=2"
  echo "CDOORPK Control:_farm_archive_absent PROG/E1.BIN 300 e1:function:drawn $(need CDP/DOOR.TXT,CDP/R103.PAK,E1/CROSS.PAK,E1/st1/r101.arc) root=CDP:E1 rows=compact $TSKIP door=2"
  for c in "${DOOR_CONTROLS[@]}"; do
    IFS='|' read -r cn cdir cfile ctitle <<< "$c"
    echo "$cn $ctitle PROG/E1.BIN 300 e1:function:drawn $(need $cdir/$cfile,$DNEED) root=$cdir:DOOR:E1 rows=compact $TSKIP door=2"
  done
  # the record's controls (lanes eng-e1k, eng-e1o; only when --scenes names them): the Leon scene with one boot file
  # each, every one must FAIL with its reason (CONSOLE_LOOP.md section 12); LEON beside them must stay OK
  for c in "${CONTROLS[@]}"; do
    IFS='|' read -r cn cdir cfile ckind ctitle <<< "$c"
    echo "$cn $ctitle PROG/E1.BIN 300 $ckind $(need $cdir/$cfile,E1L/NOTRACE,E1/CROSS.PAK,E1/st1/r101.arc) root=$cdir:E1L:E1 rows=compact"
  done
  # lane eng-e1n: the publication and HUD controls (above); lane eng-e1p: the camera track, record and disc read controls
  for c in "${E1N_CONTROLS[@]}" "${E1P_CONTROLS[@]}" "${ELOOK_CONTROLS[@]}" "${SND_CONTROLS[@]}"; do
    IFS='|' read -r cn cdir cfiles ckind ctitle cprog croot <<< "$c"
    cskip=
    case $croot in
      E1) cneed=E1/CROSS.PAK,E1/st1/r101.arc; cskip=" $TSKIP" ;;   # lane eng-snd1: a traced village control, as LEONT
      E1H:E1) cneed=E1H/HILL,E1H/NOTRACE,E1/HILL.PAK,E1/st1/r11d.arc ;;
      E1L:E1) cneed=E1L/NOTRACE,E1/CROSS.PAK,E1/st1/r101.arc ;;
      *) cneed=FIGHTL/NOTRACE,FIGHT/CROSS.PAK,FIGHT/FXMAP.BIN,FIGHT/st1/r101.arc ;;
    esac
    cneed=$cdir/${cfiles%%,*},$cneed
    echo "$cn $ctitle $cprog 300 $ckind $(need $cneed) root=$cdir:$croot rows=compact$cskip"
  done
} > "$WORK/SCENES.all"
( grep '^#' "$WORK/SCENES.all"; IFS=, ; for s in $SCENES; do grep "^$s " "$WORK/SCENES.all" || { echo "unknown scene $s" >&2; exit 1; }; done ) > "$D/SCENES.TXT"
# lane eng-e1p (H-018.3): the control schedules (above); the selector must refuse each whole
case $PLANCTL in
  '') ;;
  longcomment)
    [ "$NSCENES" = 8 ] || { echo "build_console_disc: --plan-control longcomment needs eight scenes" >&2; exit 1; }
    { printf '#'; head -c 4999 /dev/zero | tr '\0' 'x'; printf '\n'
      grep -v '^#' "$D/SCENES.TXT" | head -1 | sed 's/^[^ ]* /NINTH /'; } >> "$D/SCENES.TXT"
    log "control schedule: eight entries, a 5,000-byte comment, a ninth entry" ;;
  fivefield)
    grep -v '^#' "$D/SCENES.TXT" | tail -1 | awk '{ print $1 "5", $2, $3, $4, $5 }' >> "$D/SCENES.TXT"
    log "control schedule: a five-field line after the entries" ;;
  sectorend)
    # lane eng-mem2 (the d6 boot hang): a comment line that brings SCENES.TXT to 2,045 bytes mod 2,048, the size whose
    # last 29 bytes end fs_iso9660's DMA stream through its 32-byte non-blocking request (engine/loader/selector.c
    # disc_read). Not a refusal: the selector must read it and run every scene; a selector that reads the schedule in
    # one aligned call stops at boot (the control: the selector of 8d0fe36e0 or fa2b14aba on this disc)
    sz=$(stat -c %s "$D/SCENES.TXT"); pad=$(( (2045 - sz % 2048 + 2048) % 2048 )); [ $pad -lt 2 ] && pad=$((pad + 2048))
    { printf '#'; head -c $((pad - 2)) /dev/zero | tr '\0' 'x'; printf '\n'; } >> "$D/SCENES.TXT"
    log "control schedule: SCENES.TXT padded to $(stat -c %s "$D/SCENES.TXT") bytes (2045 mod 2048)" ;;
  *) echo "build_console_disc: --plan-control $PLANCTL: longcomment, fivefield or sectorend" >&2; exit 2 ;;
esac
for f in "${PUTS[@]}"; do
  [ -d "$(dirname "$D/$f")" ] || { echo "build_console_disc: --put $f: no such scene folder" >&2; exit 1; }
  : > "$D/$f"; log "boot option: put $f"
done
for f in "${DROPS[@]}"; do
  [ -e "$D/$f" ] || { echo "build_console_disc: --drop $f: not staged" >&2; exit 1; }
  rm -f "$D/$f"; log "control: dropped $f"
done

# ---- the disc
log "disc ($LAYOUT)"
rm -rf "$OUT"; mkdir -p "$OUT"
SECTOR=2352; [ "$LAYOUT" = legacy ] && SECTOR=2048
TMPDIR="$WORK" TITLE="$TITLE" LAYOUT=$LAYOUT SECTOR=$SECTOR PAD_1ST=1 \
  bash "$SRC/port/dreamcast/tools/d367/mkgdi.sh" "$B/loader/selector.elf" "$D" "$WORK/disc" > "$OUT/mkgdi.log" 2>&1 ||
  { tail -20 "$OUT/mkgdi.log"; exit 1; }
cp "$WORK/disc/disc.gdi" "$WORK"/disc/track0* "$OUT/"
cp "$WORK/disc/layout.txt" "$WORK/disc/disc_lint.txt" "$OUT/" 2>/dev/null || true
(cd "$OUT" && sha256sum disc.gdi track0* > SHA256SUMS && sha256sum -c --quiet SHA256SUMS)
mkdir -p "$OUT/elf"
cp "$B/loader/selector.elf" "$B/bench/native.elf" "$OUT/elf/"
cp "$B/e1/e1.elf" "$OUT/elf/e1.elf"; cp "$B/fight/e1.elf" "$OUT/elf/fight.elf"; cp "$B/boss/e1.elf" "$OUT/elf/boss.elf"
cp "$D/SCENES.TXT" "$OUT/"
{
  echo "RE4DC console disc: $REF = $COMMIT (build \"$BUILD\"), staged $(date -u +%FT%TZ)"
  echo "scenes: $SCENES  precheck: $PRECHECK  layout: $LAYOUT  drops: ${DROPS[*]:-none}  puts: ${PUTS[*]:-none}  plan control: ${PLANCTL:-none}"
  echo "## programs"; (cd "$D" && sha256sum LOADER.BIN PROG/*.BIN)
  echo "## private inputs"; sha256sum "$LKG/CROSS.PAK" "$LKG/FARM.PAK" "$LKG/CROSS.VIS" "$LKG/FARM.VIS" "$HILL_PAK" "$HILL_VIS" \
    "$FIGHT_PAK" "$FIGHT_FXMAP" "$BOSS_PAK" "$BOSS_VIS" "$BOSS_EMLIST" "$BOSS_EMARC"
  echo "## engine packs (bake/engine_pack.py, version 5)"; cat "$WORK/PACKS.txt" 2>/dev/null || echo none
  echo "## disc tree"; (cd "$D" && find . -type f | sort | xargs sha256sum)
} > "$OUT/MANIFEST.txt"
echo "KEEP: RE4DC console disc $SHORT ($REF), $(date -u +%F). Queued for the console; remove when superseded." > "$OUT/KEEP"
rm -rf "$WORK/disc" "$WORK/data" "$SRC"
log "done: $OUT"
cat "$OUT/SHA256SUMS"
grep -i "lint\|PASS\|FAIL" "$OUT/mkgdi.log" | tail -3 || true

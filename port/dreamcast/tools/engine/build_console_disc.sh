#!/bin/bash
# build_console_disc.sh: ONE GDEMU disc that holds every engine scene and runs them unattended in one boot
# (lane eng-loop2, 2026-11-20; docs/engine/CONSOLE_LOOP.md section 10). Run it in WSL.
#
#   build_console_disc.sh [--ref <git ref>] [--out <dir>] [--scenes A,B,..] [--drop <disc path>]...
#                         [--put <disc path>]... [--no-precheck] [--layout standard|legacy] [--title <text>]
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
# The E1-family scenes run with NOTRACE (no trace lines formatted inside the pictures). The bench scenes keep their
# ROW and MEMBLK lines out of the report (serial still has them): the report holds the WINDOW rows.
#
# Controls: --drop <disc path> removes one staged file (for example FIGHT/CROSS.PAK): the selector reports that scene
# FAILED ("missing ..."); with --no-precheck the selector does not check the files and the program itself must refuse
# (for example --drop BOSSB/FARM.PAK: "M1 native pack REFUSED"). --scenes picks a subset (short control discs).
# --put <disc path> adds an empty boot-option file (lane eng-e1f), for example the late-picture control of the E1
# images: --put E1/LATEPIC --put FIGHT/LATEPIC --put BOSS/LATEPIC (picture or tick 300 held 100 ms: every E1-family
# scene must then show its worst interval, at least five fields, at picture 301, or at tick 300 when headless).
#
# Private inputs (never in git; override with the environment): PRISTINE (the little-endian game tree: st1, etc,
# em, dc/mot), LKG (E0 packs and visibility), HILL_PAK, HILL_VIS, FIGHT_PAK, FIGHT_FXMAP, BOSS_PAK, BOSS_VIS,
# BOSS_EMLIST, BOSS_EMARC. Defaults: the files the lanes eng-look, eng-e1d, eng-e2 and eng-boss staged their discs
# with (checked by hash against those discs on 2026-11-20).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
REPO=$(git -C "$here" rev-parse --show-toplevel)
REF=origin/engine
OUT=
SCENES=BENCH,LEON,HILL,FIGHT,BOSS-BENCH,BOSS
DROPS=()
PUTS=()
PRECHECK=1
LAYOUT=standard
TITLE='RE4DC ENGINE CONSOLE DISC'
while [ $# -gt 0 ]; do
  case $1 in
    --ref) REF=$2; shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    --scenes) SCENES=$2; shift 2 ;;
    --drop) DROPS+=("$2"); shift 2 ;;
    --put) PUTS+=("$2"); shift 2 ;;
    --no-precheck) PRECHECK=0; shift ;;
    --layout) LAYOUT=$2; shift 2 ;;
    --title) TITLE=$2; shift 2 ;;
    *) echo "build_console_disc: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$OUT" ] || { echo "build_console_disc: --out <dir> is required" >&2; exit 2; }

PRISTINE=${PRISTINE:-/root/work/lanes/eng-bench/.m1/pristine}
# lane eng-e1i: the packs after bake/hud_fix.py (the HUD widgets made right; docs/engine/SERVICES.md 45). FARM.PAK and
# the .VIS files are eng-look's unchanged.
LKG=${LKG:-${LANES:-/mnt/e/RE4DC-Lanes}/eng-e1i/packs/lkg-hud}
LANES=${LANES:-/mnt/e/RE4DC-Lanes}
HILL_PAK=${HILL_PAK:-$LANES/eng-e1i/packs/hill2-hud.pak}
HILL_VIS=${HILL_VIS:-$LANES/eng-e1d/build/vis/hill1.vis}
FIGHT_PAK=${FIGHT_PAK:-$LANES/eng-e1i/packs/fight-hud.pak}
FIGHT_FXMAP=${FIGHT_FXMAP:-$LANES/eng-e2/build/pack/FXMAP.BIN}
# El Gigante's bench pack: lane eng-e1f's re-bake with the engine's bake/boss_pack.py (the effect records' glow header;
# eng-boss's boss2-full.pak is refused at pack-loader stage 5, the control)
BOSS_PAK=${BOSS_PAK:-$LANES/eng-e1f/build/packs/boss3-full.pak}
BOSS_VIS=${BOSS_VIS:-$LANES/eng-boss/build/vis/boss2-full.vis}
BOSS_EMLIST=${BOSS_EMLIST:-$LANES/eng-boss/build/EMLIST.BIN}
BOSS_EMARC=${BOSS_EMARC:-$LANES/eng-boss/build/EM2B.ARC}
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
  make -C "$dir" -j6 "$@" > "$B/$name-make.log" 2>&1 || { grep -n "error" "$B/$name-make.log" | head -20; tail -5 "$B/$name-make.log"; exit 1; }
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
mots() {   # mots <archive> <scene dir>: the motion clips the archive lists
  python3 "$SRC/port/dreamcast/tools/engine/mot_list.py" "$1" | while read -r m; do put "$P/dc/mot/$m" "$2/dc/mot/$m"; done
}
# BENCH: the E0 bench
put "$LKG/CROSS.PAK" BENCH/CROSS.PAK; put "$LKG/FARM.PAK" BENCH/FARM.PAK
put "$LKG/CROSS.VIS" BENCH/CROSS.VIS; put "$LKG/FARM.VIS" BENCH/FARM.VIS
printf 'c0 f0 ca c0 cb c0 fa f0 fb f0 c0dh\n' > "$D/BENCH/SCHEDULE.TXT"
# E1: Leon in the village and (with E1H/HILL in front) Leon and Ashley on the hill. The renderer sizes its pack buffer
# from CROSS.PAK and FARM.PAK, so FARM.PAK is the hill pack's twin (as lane eng-e1d's disc).
put "$LKG/CROSS.PAK" E1/CROSS.PAK; put "$LKG/CROSS.VIS" E1/CROSS.VIS
put "$HILL_PAK" E1/HILL.PAK; put "$HILL_PAK" E1/FARM.PAK; put "$HILL_VIS" E1/HILL.VIS
for f in st1/r101.arc st1/r11d.arc etc/core.das em/pl00.drs em/wep02.drs em/pl11.drs; do put "$P/$f" "E1/$f"; done
mots "$P/em/pl11.drs" E1
mkdir -p "$D/E1H"; : > "$D/E1H/HILL"
# lane eng-e1o: NOTRACE sits in each timing scene's own folder (E1L, E1H), not in E1, so the traced and stills scenes below
# can run the same files without it
mkdir -p "$D/E1L"; : > "$D/E1L/NOTRACE"; : > "$D/E1H/NOTRACE"
# FIGHT: the trimmed village pack, its effect map, the Ganado module and motion
put "$FIGHT_PAK" FIGHT/CROSS.PAK; put "$FIGHT_PAK" FIGHT/FARM.PAK; put "$FIGHT_FXMAP" FIGHT/FXMAP.BIN
put "$LKG/CROSS.VIS" FIGHT/CROSS.VIS
for f in st1/r101.arc etc/core.das etc/emleon00.esl em/pl00.drs em/wep02.drs em/em15.drs; do put "$P/$f" "FIGHT/$f"; done
mots "$P/em/em15.drs" FIGHT
: > "$D/FIGHT/NOTRACE"
# BOSSB: the bench image with El Gigante's pack in both slots (the buffer is sized once)
put "$BOSS_PAK" BOSSB/CROSS.PAK; put "$BOSS_PAK" BOSSB/FARM.PAK; put "$BOSS_VIS" BOSSB/CROSS.VIS; put "$BOSS_VIS" BOSSB/FARM.VIS
printf 'c0 cn c0 c0dh\n' > "$D/BOSSB/SCHEDULE.TXT"
# BOSS: El Gigante hosted, headless
put "$BOSS_EMARC" BOSS/EM2B.ARC; put "$BOSS_EMLIST" BOSS/EMLIST.BIN
for f in st1/r119.arc etc/core.das em/pl08.drs em/wep02.drs em/em2b.drs; do put "$P/$f" "BOSS/$f"; done
: > "$D/BOSS/HEADLESS"; : > "$D/BOSS/NOTRACE"
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
  "CHUDFZ|CHF|HUDFREEZE,STILLS|e1:function:drawn|Control:_HUD_count_frozen_(hudcheck)|PROG/FIGHT.BIN|FIGHT"
)
for c in "${E1N_CONTROLS[@]}"; do
  IFS='|' read -r cn cdir cfiles ckind ctitle cprog croot <<< "$c"
  case ",$SCENES," in *,$cn,*) mkdir -p "$D/$cdir"; for f in ${cfiles//,/ }; do : > "$D/$cdir/$f"; done ;; esac
done
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
  echo "FIGHT Four_Ganados_at_the_cross PROG/FIGHT.BIN 300 e1:timing:drawn $(need FIGHT/CROSS.PAK,FIGHT/FARM.PAK,FIGHT/FXMAP.BIN,FIGHT/st1/r101.arc,FIGHT/etc/core.das,FIGHT/etc/emleon00.esl,FIGHT/em/em15.drs) root=FIGHT rows=compact"
  echo "BOSS-BENCH El_Gigante_on_the_bench PROG/BENCH.BIN 600 bench $(need BOSSB/CROSS.PAK,BOSSB/FARM.PAK,BOSSB/CROSS.VIS,BOSSB/SCHEDULE.TXT) root=BOSSB rows=skip skip=T,MEMBLK"
  echo "BOSS El_Gigante_hosted_(headless) PROG/BOSS.BIN 300 e1:timing:headless $(need BOSS/EM2B.ARC,BOSS/EMLIST.BIN,BOSS/st1/r119.arc,BOSS/etc/core.das,BOSS/em/em2b.drs,BOSS/em/pl08.drs) root=BOSS rows=compact"
  SHOTNEED=FIGHT/CROSS.PAK,FIGHT/FARM.PAK,FIGHT/FXMAP.BIN,FIGHT/st1/r101.arc,FIGHT/etc/core.das,FIGHT/etc/emleon00.esl,FIGHT/em/em15.drs
  echo "SHOT Shot_fixture_(traced,_not_timing) PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOT/SHOT.TXT,$SHOTNEED) root=SHOT:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "SHOTNP Shot_control:_no_press PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOTNP/SHOT.TXT,$SHOTNEED) root=SHOTNP:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "SHOTDMG Shot_control:_wrong_damage PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOTD/SHOTDMG,SHOT/SHOT.TXT,$SHOTNEED) root=SHOTD:SHOT:FIGHT rows=compact skip=T,LT,LE,LL"
  echo "SHOTLATE Shot_control:_hit_1_s_late PROG/FIGHT.BIN 300 e1:function:drawn $(need SHOTL/SHOTLATE,SHOT/SHOT.TXT,$SHOTNEED) root=SHOTL:SHOT:FIGHT rows=compact skip=T,LT,LE,LL"
  # lane eng-e1o: function runs of the same images (only when --scenes names them; never timing): LEONT and HILLT traced
  # (no NOTRACE: the trace lines go to the serial line, kept out of the report), LEONS, HILLS and FIGHTS hand over stills
  # (STILLS: tick 1 and every 40th; the Flycast runner reads them)
  TSKIP="skip=T,LT,LE,LL,A,R,CAMLOG,CD"
  echo "LEONT Leon_traced_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1/CROSS.PAK,E1/st1/r101.arc) root=E1 rows=compact $TSKIP"
  echo "HILLT Hill_traced_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1HT/HILL,E1/HILL.PAK,E1/st1/r11d.arc) root=E1HT:E1 rows=compact $TSKIP"
  echo "LEONS Leon_stills_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1LS/STILLS,E1L/NOTRACE,E1/CROSS.PAK) root=E1LS:E1L:E1 rows=compact"
  echo "HILLS Hill_stills_(function_run) PROG/E1.BIN 300 e1:function:drawn $(need E1HS/STILLS,E1H/HILL,E1/HILL.PAK) root=E1HS:E1H:E1 rows=compact"
  echo "FIGHTS Fight_stills_(function_run) PROG/FIGHT.BIN 300 e1:function:drawn $(need FIGHTS/STILLS,FIGHT/CROSS.PAK) root=FIGHTS:FIGHT rows=compact"
  # the record's controls (lanes eng-e1k, eng-e1o; only when --scenes names them): the Leon scene with one boot file
  # each, every one must FAIL with its reason (CONSOLE_LOOP.md section 12); LEON beside them must stay OK
  for c in "${CONTROLS[@]}"; do
    IFS='|' read -r cn cdir cfile ckind ctitle <<< "$c"
    echo "$cn $ctitle PROG/E1.BIN 300 $ckind $(need $cdir/$cfile,E1L/NOTRACE,E1/CROSS.PAK,E1/st1/r101.arc) root=$cdir:E1L:E1 rows=compact"
  done
  # lane eng-e1n: the publication and HUD controls (above)
  for c in "${E1N_CONTROLS[@]}"; do
    IFS='|' read -r cn cdir cfiles ckind ctitle cprog croot <<< "$c"
    case $croot in
      E1H:E1) cneed=E1H/HILL,E1H/NOTRACE,E1/HILL.PAK,E1/st1/r11d.arc ;;
      E1L:E1) cneed=E1L/NOTRACE,E1/CROSS.PAK,E1/st1/r101.arc ;;
      *) cneed=FIGHT/CROSS.PAK,FIGHT/FXMAP.BIN,FIGHT/st1/r101.arc ;;
    esac
    cneed=$cdir/${cfiles%%,*},$cneed
    echo "$cn $ctitle $cprog 300 $ckind $(need $cneed) root=$cdir:$croot rows=compact"
  done
} > "$WORK/SCENES.all"
( grep '^#' "$WORK/SCENES.all"; IFS=, ; for s in $SCENES; do grep "^$s " "$WORK/SCENES.all" || { echo "unknown scene $s" >&2; exit 1; }; done ) > "$D/SCENES.TXT"
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
  echo "scenes: $SCENES  precheck: $PRECHECK  layout: $LAYOUT  drops: ${DROPS[*]:-none}  puts: ${PUTS[*]:-none}"
  echo "## programs"; (cd "$D" && sha256sum LOADER.BIN PROG/*.BIN)
  echo "## private inputs"; sha256sum "$LKG/CROSS.PAK" "$LKG/FARM.PAK" "$LKG/CROSS.VIS" "$LKG/FARM.VIS" "$HILL_PAK" "$HILL_VIS" \
    "$FIGHT_PAK" "$FIGHT_FXMAP" "$BOSS_PAK" "$BOSS_VIS" "$BOSS_EMLIST" "$BOSS_EMARC"
  echo "## disc tree"; (cd "$D" && find . -type f | sort | xargs sha256sum)
} > "$OUT/MANIFEST.txt"
echo "KEEP: RE4DC console disc $SHORT ($REF), $(date -u +%F). Queued for the console; remove when superseded." > "$OUT/KEEP"
rm -rf "$WORK/disc" "$WORK/data" "$SRC"
log "done: $OUT"
cat "$OUT/SHA256SUMS"
grep -i "lint\|PASS\|FAIL" "$OUT/mkgdi.log" | tail -3 || true

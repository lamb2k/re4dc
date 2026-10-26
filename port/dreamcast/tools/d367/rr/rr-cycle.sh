#!/bin/bash
# rr-cycle.sh [--force] [--tier quick|full]   (WSL, root; lane rr "release-ready", 2026-10-19)
# One always-ready-candidate cycle: when origin/t15/int has moved (or --force), build the release recipe at its head,
# package the disc, run the QUICK tier (or the FULL tier) and write C:\Game Dev\Emulators\RELEASE-READY.md.
# Run by the watcher (cron, rr.sh install) or by hand (rr.sh cycle / rr.sh full). Reads origin only; never pushes.
# Layout: $RR_HOME (default /root/rr): bin/ (installed copy of these tools), state/, work/<id>/, logs/, rr.lock.
#   Trees: /root/work/lanes/rr (A) and /root/work/lanes/rr-b (B), detached, checked out per cycle (never the shared
#   main checkout). Builds: route-build.sh out-rr<sha7>rP (release) + fp_twin.sh twins fprr<sha7>{g,k,c}W.
#   Candidate: /mnt/c/Game Dev/Emulators/RE4DC-RR/cand-<sha8>/gdemu (the last good one only).
#   Evidence: /mnt/c/Flycast-Evidence/re4-dreamcast/rr/<id>/ (logs kept; disc links deleted after the checks).
set -euo pipefail
RR_HOME=${RR_HOME:-/root/rr}
BIN=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=/dev/null
. "$BIN/recipe.conf"
FORCE=0; TIER=quick
while [ $# -gt 0 ]; do case $1 in --force) FORCE=1 ;; --tier) TIER=$2; shift ;; *) echo "rr-cycle: arg? $1" >&2; exit 2 ;; esac; shift; done
MAIN=/root/work/re4-dreamcast
TA=/root/work/lanes/rr; TB=/root/work/lanes/rr-b
ROUTE=/root/probe/lanes/route
TOOL=/opt/toolchains/dc/sh-elf/bin
CBASE="/mnt/c/Game Dev/Emulators/RE4DC-RR"
EBASE=/mnt/c/Flycast-Evidence/re4-dreamcast/rr
GITBASH="/mnt/c/Program Files/Git/bin/bash.exe"
FLOOR_GB=${RR_FLOOR_GB:-20}
mkdir -p "$RR_HOME/state" "$RR_HOME/work" "$RR_HOME/logs"
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
export SOURCE_DATE_EPOCH=1760000000

# one instance (the cron line also takes this lock; nested calls from rr.sh pass RR_LOCKED=1)
if [ -z "${RR_LOCKED:-}" ]; then
  exec 7>"$RR_HOME/rr.lock"
  flock -n 7 || { echo "$(date -Is) rr-cycle: another cycle holds the lock; skip" >> "$RR_HOME/logs/watch.log"; exit 0; }
fi
log() { echo "$(date -Is) $*" | tee -a "$RR_HOME/logs/watch.log"; }
# the shared disc cache's own eviction (unreferenced entries only, LRU); then the floor check
python3 "$MAIN/port/dreamcast/tools/d367/stage_ext4/disccache.py" evict > /dev/null 2>&1 || true
free_gb=$(df --output=avail -BG /mnt/c | tail -1 | tr -dc 0-9)
if [ "$free_gb" -lt "$FLOOR_GB" ]; then log "skip: C: free ${free_gb} GB < ${FLOOR_GB} GB floor"; exit 0; fi

if [ "$TIER" = full ]; then
  SHA=$(sed -n 's/^sha=//p' "$RR_HOME/state/last-good" 2>/dev/null || true)
  [ -n "$SHA" ] || { log "full: no last good candidate"; exit 1; }
else
  git -C "$MAIN" fetch -q origin t15/int
  SHA=$(git -C "$MAIN" rev-parse origin/t15/int)
fi
S8=${SHA:0:8}; S7=${SHA:0:7}
LAST=$(cat "$RR_HOME/state/last-tried" 2>/dev/null || true)
if [ "$TIER" = quick ] && [ "$FORCE" = 0 ] && [ "$SHA" = "$LAST" ]; then exit 0; fi
[ "$TIER" = full ] || echo "$SHA" > "$RR_HOME/state/last-tried"
ID=$(date +%m%d-%H%M)-$S8; [ "$TIER" = quick ] || ID=$ID-full
W=$RR_HOME/work/$ID; EVU=$EBASE/$ID; EVW='C:\Flycast-Evidence\re4-dreamcast\rr\'$ID
mkdir -p "$W" "$EVU/_jobs" "$EVU/fixtures"
STEPS=$W/steps.tsv; : > "$STEPS"
exec > >(tee -a "$W/cycle.log") 2>&1
# the recipe of the commit being built (rr-wire 10-21): tools/d367/rr/recipe.conf at $SHA; the installed copy only when
# that commit has none. rr-jobs.sh, rr-qa.sh and rr-judge.py read $W/recipe.conf.
if git -C "$MAIN" show "$SHA:port/dreamcast/tools/d367/rr/recipe.conf" 2>/dev/null | tr -d '\r' > "$W/recipe.conf" && [ -s "$W/recipe.conf" ]; then
  echo "recipe.conf: from ${S8}"
else
  cp "$BIN/recipe.conf" "$W/recipe.conf"; echo "recipe.conf: installed copy (none at ${S8})"
fi
# shellcheck source=/dev/null
. "$W/recipe.conf"
log "cycle $ID tier=$TIER sha=$S8 recipe='$RR_RECIPE_NAME' free_c=${free_gb}G"
T0=$(date +%s)
step() { local _n=$1; shift; local _t0; _t0=$(date +%s); local _rc=0
  echo "== step $_n $(date +%T)"; "$@" || _rc=$?
  printf '%s\t%s\t%s\t%s\n' "$_n" "$_t0" "$(date +%s)" "$_rc" >> "$STEPS"; return $_rc; }
LG_SHA=$(sed -n 's/^sha=//p' "$RR_HOME/state/last-good" 2>/dev/null || true)
{ echo "id=$ID"; echo "sha=$SHA"; echo "tier=$TIER"; echo "last_good_sha=$LG_SHA"; echo "ev=$EVU"; echo "evw=$EVW"; } > "$W/cycle.env"

trees() {
  for t in "$TA" "$TB"; do
    [ -d "$t" ] || { git -C "$MAIN" worktree prune && git -C "$MAIN" worktree add -q --detach "$t" "$SHA"; } || return 1
    git -C "$t" checkout -q -f --detach "$SHA" || return 1
    git -C "$t" submodule update -q --init --recursive || return 1
    [ -z "$(git -C "$t" status --short --untracked-files=no)" ] || { echo "tree $t is not clean"; return 1; }
  done
  # rooms the diff since the last good candidate touches (census scope); "all" when unknown
  if [ -n "$LG_SHA" ] && git -C "$TA" cat-file -e "$LG_SHA" 2>/dev/null; then
    git -C "$TA" diff --name-only "$LG_SHA" "$SHA" > "$W/diff-files.txt"
    git -C "$TA" log --oneline "$LG_SHA..$SHA" > "$W/diff-log.txt"
  else echo "(no last good candidate)" > "$W/diff-log.txt"; : > "$W/diff-files.txt"; fi
}
build_release() {
  local tt=$TA/port/dreamcast/tools/d367
  K=$W/k T=$TA LP=rr$S7 CH2="$CH2" bash "$tt/ch2/ch2-build.sh" rP 2>&1 | grep '^rc=' | cut -c1-200 | tee "$W/build-rP.txt"
  local O=$ROUTE/out-rr${S7}rP
  grep -q '^rc=0 ' "$W/build-rP.txt" && [ -s "$O/re4dc-game.elf" ] || { echo "release build failed"; return 1; }
  [ ! -s "$O/missing.txt" ] || { echo "missing.txt not empty:"; head "$O/missing.txt"; return 1; }
  $TOOL/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$W/img.bin"
  sha256sum < "$W/img.bin" | cut -c1-64 > "$W/image.sha256"; rm -f "$W/img.bin"
  echo "image $(cut -c1-16 "$W/image.sha256") end $(cat "$O/end.txt")"
}
twin() { # twin <tree> <label> [knobs...]
  local t=$1 l=$2; shift 2
  FP_TREE=$t FP_SKIP_IDENTITY=1 bash "$t/port/dreamcast/tools/d367/fullplay/fp_twin.sh" "$ROUTE/out-rr${S7}rP" "$l" "$@" > "$W/twin-$l.txt" 2>&1
  [ -s "$ROUTE/out-fp${l}W/re4dc-game.elf" ] && [ ! -s "$ROUTE/out-fp${l}W/missing.txt" ]
}
build_twins() {
  # A: g (the full-play gate's twin: h2 + GDEMU). B: c (census + KOS squeeze: registry census, KOS watch / squeeze,
  # W11 fixture). Two bases only: C: space (each base is a ~1 GB track03 in the disc cache).
  twin "$TA" rr${S7}g & local pa=$!
  twin "$TB" rr${S7}c KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 & local pb=$!
  local rc=0; wait $pa || rc=1; wait $pb || rc=1
  tail -n 2 "$W"/twin-*.txt | cut -c1-200; return $rc
}
package() {
  local tt=$TA/port/dreamcast/tools/d367 O=$ROUTE/out-rr${S7}rP
  # the newest published knob file = the one most recently committed (names do not sort: test122 is 12.2)
  local newest; newest=$(for f in "$tt"/test*/release-knobs.txt; do echo "$(git -C "$TA" log -1 --format=%ct -- "$f") $f"; done | sort -n | tail -1 | cut -d' ' -f2-)
  mkdir -p "$W/kit" "$W/pkg/fix"
  cp "$(dirname "$newest")/README-package.txt" "$W/kit/README-package.txt"
  python3 "$tt/release-knobs.py" write "$O/candidate.txt" "$W/kit/release-knobs.txt" --test rr --tag "rr-$S8" --source "$S8" \
    --recipe port/dreamcast/tools/d367/ch2/ch2-build.sh --image-sha256 "$(cat "$W/image.sha256")" \
    --assets-zip "RE4DC-TestRR-$S8-Build-Assets.zip" --disc-sets "$KSETS" > /dev/null
  { echo "newest published knob file: ${newest#$TA/}"
    diff <(grep -v '^#' "$newest") <(grep -v '^#' "$W/kit/release-knobs.txt") || true; } > "$W/knobs-diff.txt"
  RE4DC_RESIDENT_STRICT=1 python3 "$tt/test11/t11-fix.py" rr${S7}rP "$W/pkg/fix/pkg-rr${S7}rP.json" --base payload --data "$DATA" | tail -1 | cut -c1-200
  local CAND="$CBASE/cand-$S8"; mkdir -p "$CAND"
  R=$W/pkg L=rr${S7}rP P="$CAND" SRC_SHA=$S8 TN=RR PKG_KIT_DIR=$W/kit KSETS=$KSETS NOZIP=1 bash "$tt/test16/t16-package.sh" > "$W/package.txt" 2>&1 \
    || { tail -20 "$W/package.txt"; return 1; }
  grep -E 'disc_lint|boot file|PACKAGE|tracks-match' "$W/package.txt" | cut -c1-200
  cp "$W/pkg/logs/"disc_lint-*.txt "$EVU/" 2>/dev/null || true
  # the game tracks' sums for fp_gate (NOZIP=1 package has no zip to carry them)
  (cd "$CAND/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  gdemu/#') > "$CAND/SHA256SUMS.txt"
  echo "$CAND" > "$W/cand.txt"
}
bases() {
  local F=$TA/port/dreamcast/tools/d367/fullplay CAND; CAND=$(cat "$W/cand.txt")
  python3 "$F/fp_iso.py" extract "$CAND/gdemu/track03.bin" "$W/rel/tree" --manifest "$W/rel/manifest.json" --ipbin "$W/rel/IP.BIN" | tail -1
  local rc=0
  for x in g c; do
    bash "$F/fp_master.sh" "$W/rel/tree" "$W/rel/manifest.json" "$W/rel/IP.BIN" "$EVU/_discs/$x" "$ROUTE/out-fprr${S7}${x}W" > "$W/master-$x.txt" 2>&1 || rc=1
  done   # one at a time: each base peaks ~2 GB on C: (ext4 vhdx + disc cache)
  # MEMBER-CENSUS (lane fix-r100-props26 10-26): every file / room-archive member / tex.pak key that differs from the
  # last published release tree ($MC_REF_TREE, recipe.conf) must be claimed by a row of $MC_CLAIMS (rr/member_census.py).
  if [ -n "${MC_REF_TREE:-}" ] && [ -d "$MC_REF_TREE" ]; then
    python3 "$TA/port/dreamcast/tools/d367/rr/member_census.py" "$MC_REF_TREE" "$W/rel/tree" \
      "$TA/port/dreamcast/tools/d367/rr/${MC_CLAIMS:-member-claims.tsv}" --json "$W/member-census.json" > "$W/member-census.txt" 2>&1 || true
    tail -n 1 "$W/member-census.txt"
  else echo "MEMBER-CENSUS skipped: no reference tree (MC_REF_TREE=${MC_REF_TREE:-})" > "$W/member-census.txt"; fi
  tail -qn 1 "$W"/master-*.txt | cut -c1-200; rm -rf "${W:?}/rel/tree"; return $rc
}
jobs_quick() { bash "$BIN/rr-jobs.sh" quick "$W" "$TA" "$S7" "$EVU" "$EVW"; }
jobs_full() { bash "$BIN/rr-jobs.sh" full "$W" "$TA" "$S7" "$EVU" "$EVW"; }
flycasts() {
  local evg; evg=/c/${EVU#/mnt/c/}
  "$GITBASH" "//wsl.localhost/Ubuntu-24.04$BIN/rr-flycast.sh" "$evg" "${RR_JOBS:-12}"
}
judge() { python3 "$BIN/rr-judge.py" "$W" "$TA" "$BIN"; }
# GC-ASSET gate (cast-ps2-25 10-26): catalog from the recipe + gate-ON twin + base a (rr-gca.sh); RR_GCA=0 skips it
gca() { bash "$BIN/rr-gca.sh" "$W" "$TA" "$S7" "$EVU"; }

trace_arms() { # full tier: the recipe's trace arm (A) and the reference recipe's (B), then their bases
  local rc=0
  K=$W/k T=$TA LP=rr$S7 CH2="$CH2" bash "$TA/port/dreamcast/tools/d367/ch2/ch2-build.sh" rT 2>&1 | grep '^rc=' | cut -c1-120 > "$W/build-rT.txt" &
  local pa=$!
  K=$W/kb T=$TB LP=rr${S7}ref CH2="$CH2_REF" bash "$TB/port/dreamcast/tools/d367/ch2/ch2-build.sh" rT 2>&1 | grep '^rc=' | cut -c1-120 > "$W/build-refrT.txt" &
  wait $pa || rc=1; wait $! || rc=1
  cat "$W/build-rT.txt" "$W/build-refrT.txt"
  grep -q '^rc=0 ' "$W/build-rT.txt" && grep -q '^rc=0 ' "$W/build-refrT.txt" || return 1
  local F=$TA/port/dreamcast/tools/d367/fullplay CAND; CAND=$(cat "$W/cand.txt")
  [ -d "$W/rel/tree" ] || python3 "$F/fp_iso.py" extract "$CAND/gdemu/track03.bin" "$W/rel/tree" --manifest "$W/rel/manifest.json" --ipbin "$W/rel/IP.BIN" | tail -1
  bash "$F/fp_master.sh" "$W/rel/tree" "$W/rel/manifest.json" "$W/rel/IP.BIN" "$EVU/_discs/tT" "$ROUTE/out-rr${S7}rT" > "$W/master-tT.txt" 2>&1 &
  pa=$!
  bash "$F/fp_master.sh" "$W/rel/tree" "$W/rel/manifest.json" "$W/rel/IP.BIN" "$EVU/_discs/tR" "$ROUTE/out-rr${S7}refrT" > "$W/master-tR.txt" 2>&1 || rc=1
  wait $pa || rc=1
  rm -rf "${W:?}/rel/tree"; return $rc
}

ok=1
step trees trees || ok=0
if [ "$TIER" = full ]; then
  # the FULL tier re-checks the last good candidate (no rebuild of the release image)
  LGW=$(sed -n 's/^work=//p' "$RR_HOME/state/last-good")
  for f in cand.txt image.sha256 knobs-diff.txt diff-log.txt; do cp "$LGW/$f" "$W/" 2>/dev/null || true; done
  [ -s "$ROUTE/out-rr${S7}rP/re4dc-game.elf" ] || { echo "full: release build out-rr${S7}rP is gone"; ok=0; }
  if [ $ok = 1 ] && { ! [ -s "$ROUTE/out-fprr${S7}gW/re4dc-game.elf" ] || ! [ -s "$ROUTE/out-fprr${S7}cW/re4dc-game.elf" ]; }; then
    step build-twins build_twins || ok=0
  fi
  [ $ok = 1 ] && { step bases bases || ok=0; }
  if [ $ok = 1 ] && [ -n "${CH2_REF:-}" ]; then step trace-arms trace_arms || echo "trace arms failed: decisions not run"; fi
else
  [ $ok = 1 ] && { step build-release build_release || ok=0; }
  [ $ok = 1 ] && { step build-twins build_twins || ok=0; }
  [ $ok = 1 ] && { step package package || ok=0; }
  [ $ok = 1 ] && { step bases bases || ok=0; }
  if [ $ok = 1 ] && [ "${RR_GCA:-1}" != 0 ]; then step gca gca || echo "gca prep failed: the GC-ASSET check reports it"; fi
fi
if [ $ok = 1 ]; then
  if [ "$TIER" = full ]; then step jobs jobs_full || ok=0; else step jobs jobs_quick || ok=0; fi
fi
[ $ok = 1 ] && { step flycast flycasts || true; }
echo "build_ok=$ok" >> "$W/cycle.env"
printf 'total\t%s\t%s\t0\n' "$T0" "$(date +%s)" >> "$STEPS"
step judge judge || true
VERDICT=$(cat "$W/verdict.txt" 2>/dev/null || echo FAIL)
log "cycle $ID verdict $VERDICT ($(( $(date +%s) - T0 )) s)"
if [ "$TIER" = full ]; then
  cp "$W/RELEASE-READY.md" "$RR_HOME/state/full-last.md" 2>/dev/null || true
  rm -rf "${EVU:?}/_discs"
  find "$EVU" \( -name 'track0*.iso' -o -name 'track03.bin' -o -name 'disc.bin' \) -delete
  for a in rT refrT; do [ -d "$ROUTE/out-rr${S7}$a" ] && rm -rf "${ROUTE:?}/out-rr${S7}${a:?}"; done
  exit 0
fi

# keep one candidate: a PASS replaces the last good; a FAIL keeps the last good and drops its own discs
rm -rf "${EVU:?}/_discs"
find "$EVU" -name 'track0*.iso' -o -name 'track03.bin' -o -name 'disc.bin' | while read -r f; do rm -f "$f"; done
if [ "$VERDICT" = PASS ]; then
  OLD=$(sed -n 's/^cand=//p' "$RR_HOME/state/last-good" 2>/dev/null || true)
  OLDS7=$(sed -n 's/^s7=//p' "$RR_HOME/state/last-good" 2>/dev/null || true)
  { echo "sha=$SHA"; echo "s7=$S7"; echo "id=$ID"; echo "cand=$(cat "$W/cand.txt")"; echo "image=$(cat "$W/image.sha256")"; echo "work=$W"; echo "ev=$EVU"; } > "$RR_HOME/state/last-good"
  if [ -n "$OLD" ] && [ "$OLD" != "$(cat "$W/cand.txt")" ]; then
    case "$OLD" in "$CBASE"/cand-*) rm -rf "${OLD:?}"; log "deleted old candidate $OLD" ;; esac
  fi
  [ -z "$OLDS7" ] || [ "$OLDS7" = "$S7" ] || bash "$BIN/rr-clean-builds.sh" "$OLDS7"
else
  CAND=$(cat "$W/cand.txt" 2>/dev/null || true)
  LGC=$(sed -n 's/^cand=//p' "$RR_HOME/state/last-good" 2>/dev/null || true)
  if [ -n "$CAND" ] && [ "$CAND" != "$LGC" ]; then case "$CAND" in "$CBASE"/cand-*) rm -rf "${CAND:?}" ;; esac; fi
  LGS7=$(sed -n 's/^s7=//p' "$RR_HOME/state/last-good" 2>/dev/null || true)
  [ "$LGS7" = "$S7" ] || bash "$BIN/rr-clean-builds.sh" "$S7"
fi
# QA disc (standing rule 8; user 10-21: right after the quick smoke test, first thing on the new candidate, before
# the full tier). Never blocks: its own QA rows in RELEASE-READY.md; the game verdict and last-good stay as they are.
# The QA zip stays in the candidate dir (RE4DC-QA-TestRR-<sha8>-<date>-GDEMU.zip) so it can go to testers first.
if [ "$VERDICT" = PASS ]; then
  QV=$(bash "$BIN/rr-qa-tier.sh" "$W" "$TA" "$SHA" "$ID" 2>&1 | tee -a "$W/cycle.log" | tail -1) || true
  log "cycle $ID QA ${QV:-FAIL} (reported only; the game verdict is unchanged)"
fi
# keep the last 10 work dirs (logs only; the pkg trees are deleted by t16-package.sh)
ls -dt "$RR_HOME"/work/*/ 2>/dev/null | tail -n +11 | while read -r d; do
  [ "$d" = "$(sed -n 's/^work=//p' "$RR_HOME/state/last-good" 2>/dev/null)/" ] || rm -rf "${d:?}"; done
exit 0

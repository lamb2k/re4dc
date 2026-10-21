#!/bin/bash
# rr-qa-tier.sh <work dir> <tree> <sha> <cycle id>   (WSL; lane rr, standing rule 8, user 10-21 order)
# The QA step of a candidate: rr-qa.sh (build, presets, mkgdi, disc_lint, zip kept in the candidate dir), the QA Flycast
# jobs (rr-jobs.sh qa: qa-boot, qa-warp, qa-gdemu; 3 slots) and rr-judge.py qa (the "QA disc" section of
# RELEASE-READY.md). Never changes the game verdict or last good. Run by rr-cycle.sh after a quick-tier PASS, or by
# hand: rr.sh qa (the last good candidate).
set -euo pipefail
W=${1:?work}; TA=${2:?tree}; SHA=${3:?sha}; ID=${4:?id}
BIN=$(cd "$(dirname "$0")" && pwd)
S7=${SHA:0:7}
EVQ=/mnt/c/Flycast-Evidence/re4-dreamcast/rr/$ID-qa
EVQW='C:\Flycast-Evidence\re4-dreamcast\rr\'$ID-qa
GITBASH="/mnt/c/Program Files/Git/bin/bash.exe"
CAND=$(cat "$W/cand.txt")
mkdir -p "$EVQ/_jobs" "$EVQ/fixtures"
t0=$(date +%s); rc=0
bash "$BIN/rr-qa.sh" "$W" "$TA" "$SHA" RR "$CAND" "$EVQ" > "$W/qa.txt" 2>&1 || rc=$?
echo "$rc" > "$W/qa-rc"; tail -8 "$W/qa.txt"
printf 'qa-disc\t%s\t%s\t%s\n' "$t0" "$(date +%s)" "$rc" > "$W/qa-steps.tsv"
if [ "$rc" = 0 ]; then
  t0=$(date +%s)
  if bash "$BIN/rr-jobs.sh" qa "$W" "$TA" "$S7" "$EVQ" "$EVQW" > /dev/null; then
    "$GITBASH" "//wsl.localhost/Ubuntu-24.04$BIN/rr-flycast.sh" "/c/${EVQ#/mnt/c/}" 3 || true
  fi
  printf 'qa-flycast\t%s\t%s\t0\n' "$t0" "$(date +%s)" >> "$W/qa-steps.tsv"
fi
python3 "$BIN/rr-judge.py" "$W" "$TA" "$BIN" qa "$EVQ" || true
rm -rf "${EVQ:?}/_discs"
find "$EVQ" \( -name 'track0*.iso' -o -name 'track03.bin' -o -name 'disc.bin' \) -delete
cat "$W/qa-verdict.txt" 2>/dev/null || echo FAIL

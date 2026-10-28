#!/bin/bash
# rr.sh status | cycle | full | qa | package <tag> [test name] | install | uninstall   (WSL, root; lane rr, 2026-10-19)
# The always-ready release candidate. From Windows:
#   MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root bash /root/rr/bin/rr.sh status
#   status            last good candidate, last cycle, whether a cycle runs now (C:\Game Dev\Emulators\RELEASE-READY.md)
#   cycle             a QUICK-tier cycle now on origin/t15/int head, even when it has not moved (waits for a running one)
#   full              the FULL tier against the last good candidate (release checks, census, KOS 10/10, GDEMU 10 seeds,
#                     decisions pairs, kit when packaged with a committed knob file); report in RELEASE-READY.md
#   package <tag> [N] the GDEMU zip + Build-Assets zip of the last good candidate (knob file tag <tag>, zip test name N,
#                     default RR) in its candidate dir
#   install           copy these tools to /root/rr/bin and add the cron watcher (every 10 min); uninstall removes the line
set -euo pipefail
RR_HOME=${RR_HOME:-/root/rr}
HERE=$(cd "$(dirname "$0")" && pwd)
CRON="*/10 * * * * /usr/bin/flock -n $RR_HOME/rr.lock /usr/bin/env RR_LOCKED=1 /bin/bash $RR_HOME/bin/rr-cycle.sh >> $RR_HOME/logs/cron.log 2>&1"
lg() { sed -n "s/^$1=//p" "$RR_HOME/state/last-good" 2>/dev/null || true; }
case "${1:-status}" in
  status)
    echo "last good: sha $(lg sha | cut -c1-8) image $(lg image | cut -c1-16) cycle $(lg id) disc $(lg cand)/gdemu"
    echo "last tried: $(cut -c1-8 "$RR_HOME/state/last-tried" 2>/dev/null || echo none); origin/t15/int: $(git -C /root/work/re4-dreamcast rev-parse --short=8 origin/t15/int)"
    if flock -n "$RR_HOME/rr.lock" true; then echo "cycle running: no"; else echo "cycle running: yes ($(ls -t "$RR_HOME/work" | head -1))"; fi
    crontab -l 2>/dev/null | grep -q rr-cycle.sh && echo "watcher: cron installed" || echo "watcher: NOT installed"
    tail -3 "$RR_HOME/logs/watch.log" 2>/dev/null || true
    sed -n '1,12p' "/mnt/c/Game Dev/Emulators/RELEASE-READY.md" 2>/dev/null | grep -E '^\*\*|^## This' || true ;;
  cycle)
    exec 7>"$RR_HOME/rr.lock"; flock 7; RR_LOCKED=1 bash "$RR_HOME/bin/rr-cycle.sh" --force ;;
  full)
    exec 7>"$RR_HOME/rr.lock"; flock 7; RR_LOCKED=1 bash "$RR_HOME/bin/rr-cycle.sh" --tier full ;;
  package)
    TAG=${2:?tag}; TN=${3:-RR}
    exec 7>"$RR_HOME/rr.lock"; flock 7
    S7=$(lg s7); W=$(lg work); CAND=$(lg cand); SHA=$(lg sha)
    [ -n "$S7" ] && [ -d "$W" ] || { echo "rr: no last good candidate"; exit 1; }
    # the recipe of the built commit (fallback: the installed copy)
    git -C /root/work/re4-dreamcast show "$SHA:port/dreamcast/tools/d367/rr/recipe.conf" 2>/dev/null | tr -d '\r' > "$W/recipe.conf" \
      && [ -s "$W/recipe.conf" ] || cp "$RR_HOME/bin/recipe.conf" "$W/recipe.conf"
    . "$W/recipe.conf"
    # package README: the newest committed test<N>/README-package.txt on origin/t15/int (same rule as the knob file)
    git -C /root/work/re4-dreamcast fetch -q origin t15/int || true
    mkdir -p "$W/kit"; echo "README: $(bash "$RR_HOME/bin/rr-newest.sh" 'test[^/]*' README-package.txt "$W/kit/README-package.txt")"
    TT=/root/work/lanes/rr/port/dreamcast/tools/d367; O=/root/probe/lanes/route/out-rr${S7}rP
    [ "$(git -C /root/work/lanes/rr rev-parse HEAD)" = "$SHA" ] || git -C /root/work/lanes/rr checkout -q -f --detach "$SHA"
    python3 "$TT/release-knobs.py" write "$O/candidate.txt" "$W/kit/release-knobs.txt" --test "$TN" --tag "$TAG" --source "${SHA:0:8}" \
      --recipe port/dreamcast/tools/d367/ch2/ch2-build.sh --image-sha256 "$(lg image)" \
      --assets-zip "RE4DC-Test$TN-${SHA:0:8}-Build-Assets.zip" --disc-sets "$KSETS"
    R=$W/pkg L=rr${S7}rP P="$CAND" SRC_SHA=${SHA:0:8} TN=$TN PKG_KIT_DIR=$W/kit KSETS=$KSETS bash "$TT/test16/t16-package.sh" 2>&1 | tail -8
    echo "knob file for the release lane: $W/kit/release-knobs.txt"
    # the QA disc zip beside the game zip (standing rule 8)
    { bash "$RR_HOME/bin/rr-qa.sh" "$W" /root/work/lanes/rr "$SHA" "$TN" "$CAND" 2>&1 | tail -6; } \
      || echo "QA disc: FAIL (reported only; the game package above is unaffected)" ;;
  qa)
    # the QA disc step of the last good candidate again (rr-qa-tier.sh; reports its own QA rows)
    exec 7>"$RR_HOME/rr.lock"; flock 7
    SHA=$(lg sha); W=$(lg work); ID=$(lg id)
    [ -n "$SHA" ] && [ -d "$W" ] || { echo "rr: no last good candidate"; exit 1; }
    bash "$RR_HOME/bin/rr-qa-tier.sh" "$W" /root/work/lanes/rr "$SHA" "$ID" ;;
  install)
    [ "$HERE" != "$(cd "$RR_HOME/bin" 2>/dev/null && pwd)" ] || { echo "rr: run install from a source tree (tools/d367/rr/rr.sh install), not from $RR_HOME/bin"; exit 2; }
    mkdir -p "$RR_HOME/bin" "$RR_HOME/logs" "$RR_HOME/state"
    for f in "$HERE"/*; do [ -f "$f" ] || continue; tr -d '\r' < "$f" > "$RR_HOME/bin/$(basename "$f")"; done
    # speed/ (lane guards28 10-28): the SPEED row's scripts and scene warps
    mkdir -p "$RR_HOME/bin/speed/warps"
    for f in "$HERE"/speed/* "$HERE"/speed/warps/*; do [ -f "$f" ] || continue; tr -d '\r' < "$f" > "$RR_HOME/bin/${f#"$HERE"/}"; done
    chmod +x "$RR_HOME"/bin/*.sh "$RR_HOME"/bin/speed/*.sh
    ( crontab -l 2>/dev/null | grep -v 'rr-cycle.sh' || true; echo "$CRON" ) | crontab -
    echo "installed $(ls "$RR_HOME/bin" | wc -l) files; cron: $(crontab -l | grep -c rr-cycle.sh) line" ;;
  uninstall)
    ( crontab -l 2>/dev/null | grep -v 'rr-cycle.sh' || true ) | crontab -; echo "cron line removed" ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac

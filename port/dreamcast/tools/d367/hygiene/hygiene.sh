#!/bin/bash
# hygiene.sh [--apply]: hourly disk hygiene for RE4 DC lanes (CLAUDE.md disk hygiene rule; user 2026-11-03
# "ensure we have the right clean up process in place on the new disk"). Dry run by default.
# Deletes ONLY rebuildable outputs; never logs, captures, results, flycast*.exe, git trees or unpushed work.
#  1. lane disc-cache entries (E:/D: RE4DC-Lanes/*/{_dc,disccache,_disccache}/<sha>) untouched 3 h
#  2. staged disc images (track0*, disc.gdi, *.iso) under E:/D: RE4DC-Lanes untouched 6 h, unless the dir or a
#     parent has a KEEP file or the path is listed in /root/probe/keep.txt
#  3. rr work dirs except last good and the newest 2
#  4. raw trace dumps (*.trace, *.lt, trace-*.bin) older than 24 h under lane folders, unless in keep.txt
#  5. idle build objdirs (out-*/objs, build-*) under /root/work/lanes/*-scratch untouched 6 h
#  6. fstrim; warn file when E: < 100 GB free
set -u
APPLY=0; [ "${1:-}" = --apply ] && APPLY=1
M=/root/probe/_prune-manifests/hygiene-$(date +%Y%m%d).tsv
WARN=/root/probe/HYGIENE-WARN.txt
KEEP=/root/probe/keep.txt
mkdir -p /root/probe/_prune-manifests
LOCK=/root/probe/hygiene.lock
exec 8>"$LOCK"; flock -n 8 || exit 0

kept() { # path -> 0 if protected
  local p=$1 d
  [ -f "$KEEP" ] && grep -qxF "$p" "$KEEP" && return 0
  d=$(dirname "$p")
  while [ "$d" != / ] && [ "$d" != . ]; do [ -e "$d/KEEP" ] && return 0; d=$(dirname "$d"); done
  return 1
}
. "$(dirname "$(readlink -f "$0")")/delguard.sh"  # shared guard: never orig/, re4data, keep*, big non-staging files
del() { # kind path
  guarded_rm "$1" "$2" "$M" || true
}

for B in /mnt/e/RE4DC-Lanes /mnt/d/RE4DC-Lanes; do
  [ -d "$B" ] || continue
  # 1. disc caches
  for c in "$B"/*/_dc "$B"/*/disccache "$B"/*/_disccache; do
    [ -d "$c" ] || continue
    for e in "$c"/*/; do
      e=${e%/}; [ -d "$e" ] || continue
      [ -n "$(find "$e" -type f -mmin -180 -print -quit)" ] && continue
      kept "$e" && continue
      del disccache "$e"
    done
  done
  # 2. staged discs
  find "$B" -type f -mmin +360 \( -iname 'track0*' -o -iname 'disc.gdi' -o -iname '*.iso' \) \
       -not -path '*/_dc/*' -not -path '*/disccache/*' -not -path '*/_disccache/*' -print 2>/dev/null |
  while IFS= read -r f; do kept "$f" || del disc "$f"; done
  # 4. raw traces
  find "$B" -type f -mmin +1440 \( -iname '*.trace' -o -iname '*.lt' -o -iname 'trace-*.bin' \) -print 2>/dev/null |
  while IFS= read -r f; do kept "$f" || del trace "$f"; done
done

# 3. rr work dirs
LG=$(sed -n 's/^id=//p' /root/rr/state/last-good 2>/dev/null)
if [ -d /root/rr/work ] && [ -n "$LG" ]; then
  ls -1t /root/rr/work | tail -n +3 | while read -r w; do
    [ "$w" = "$LG" ] && continue
    kept "/root/rr/work/$w" || del rrwork "/root/rr/work/$w"
  done
fi

# 5. idle objdirs in lane scratch
for s in /root/work/lanes/*-scratch; do
  [ -d "$s" ] || continue
  find "$s" -maxdepth 2 -type d \( -name 'out-*' -o -name 'objs' -o -name 'build-*' \) -print 2>/dev/null |
  while IFS= read -r o; do
    [ -n "$(find "$o" -type f -mmin -360 -print -quit)" ] && continue
    kept "$o" || del objdir "$o"
  done
done

[ "$APPLY" = 1 ] && fstrim / >/dev/null 2>&1
e=$(df --output=avail -BG /mnt/e | tail -1 | tr -dc 0-9)
if [ "${e:-0}" -lt 100 ]; then echo "$(date '+%F %T') E: ${e}G free (< 100G)" >> "$WARN"; fi
exit 0

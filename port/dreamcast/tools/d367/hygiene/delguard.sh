#!/bin/bash
# delguard.sh: shared delete guard for every RE4 DC cleanup (incident 2026-11-03: a name-pattern cleanup deleted the
# GameCube source image orig/G4BE08/re4_debug_disc1.iso). Source it and call `guarded_rm <kind> <path>`; it refuses
# protected paths and logs the refusal instead of deleting.
#   - orig/, re4data/, re4-assets-private, any dir named keep*, KEEP files up the tree, /root/probe/keep.txt
#   - single files over 500 MB outside known staging dirs (_dc, disccache, _discs, cand-*, fpimages, out-*, objs)
DELGUARD_KEEP=${DELGUARD_KEEP:-/root/probe/keep.txt}
delguard_protected() { # path -> 0 (and reason on stdout) if it must not be deleted
  local p=$1 d
  case "$p" in
    */orig|*/orig/*) echo "source images (orig/)"; return 0;;
    */re4data|*/re4data/*|*/re4-assets-private|*/re4-assets-private/*) echo "private asset store"; return 0;;
    */keep|*/keep/*|*/keep-*|*/keep-*/*) echo "keep dir"; return 0;;
    *flycast*.exe) echo "flycast.exe"; return 0;;
  esac
  [ -f "$DELGUARD_KEEP" ] && grep -qxF "$p" "$DELGUARD_KEEP" && { echo "keep.txt"; return 0; }
  d=$p; [ -d "$d" ] || d=$(dirname "$p")
  while [ "$d" != / ] && [ "$d" != . ]; do
    [ -e "$d/KEEP" ] && { echo "KEEP file in $d"; return 0; }
    [ -f "$DELGUARD_KEEP" ] && grep -qxF "$d" "$DELGUARD_KEEP" && { echo "keep.txt ($d)"; return 0; }
    d=$(dirname "$d")
  done
  if [ -f "$p" ] && [ "$(stat -c %s "$p" 2>/dev/null || echo 0)" -gt 524288000 ]; then
    case "$p" in
      */_dc/*|*/disccache/*|*/_disccache/*|*/_discs/*|*/cand-*|*/fpimages/*|*/out-*|*/objs/*) ;;
      *) echo "file > 500 MB outside staging dirs"; return 0;;
    esac
  fi
  return 1
}
guarded_rm() { # kind path [manifest]: delete unless protected; APPLY=1 to really delete
  local kind=$1 p=$2 m=${3:-${M:-/dev/null}} why
  if why=$(delguard_protected "$p"); then
    printf '%s\tREFUSED\t%s\t%s\n' "$(date '+%F %T')" "$why" "$p" >> "$m"
    return 1
  fi
  local sz; sz=$(du -sb "$p" 2>/dev/null | cut -f1)
  printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$kind" "${sz:-0}" "$p" >> "$m"
  [ "${APPLY:-0}" = 1 ] && rm -rf -- "${p:?}"
  return 0
}

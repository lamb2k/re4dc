#!/bin/bash
# D367 host-wide trace slots (2026-10-13 dettrace rule; 12 from 10-19, user): at most TRACE_SLOTS (default 12) logic-trace Flycast runs
# (STRICT pairs, decision traces) at a time on this host, across Claude and Codex lanes. Trace runs are deterministic
# in emulated time, so they may run in parallel; the cap only protects host memory. Other Flycast runs need no slot.
# Every trace run sets RE4DC_LOG_STOP_TICK (same N for both runs of a pair); a "[LOG OVERRUN" line or a tick gap
# makes the run invalid. Never hold a slot around a wait loop or staging: wrap only the Flycast run.
#
#   trace_lock.sh <command> [args...]   run the command while holding one slot (waits for a free one)
#   trace_lock.sh --status              "free" when a slot is free, else "held"; then one line per held slot
#
# Slot 0 is /root/probe/.trace.lock (the old single lock, so copies of the old script in lane trees take slot 0 and
# the cap still holds); slot k > 0 is /root/probe/.trace.lock.k. Holders: /root/probe/.trace.holder[.k].
set -u
N=${TRACE_SLOTS:-16}
lockf() { [ "$1" -eq 0 ] && echo /root/probe/.trace.lock || echo "/root/probe/.trace.lock.$1"; }
holdf() { [ "$1" -eq 0 ] && echo /root/probe/.trace.holder || echo "/root/probe/.trace.holder.$1"; }
if [ "${1:-}" = "--status" ]; then
    free=0; lines=""
    for k in $(seq 0 $((N - 1))); do
        if flock -n "$(lockf $k)" true; then free=$((free + 1))
        else lines="$lines  slot $k: $(cat "$(holdf $k)" 2>/dev/null)"$'\n'; fi
    done
    if [ $free -gt 0 ]; then echo "free"; else echo "held"; fi
    echo "slots $((N - free))/$N in use"
    printf '%s' "$lines"
    exit 0
fi
[ $# -ge 1 ] || { echo "usage: trace_lock.sh <command> [args...] | --status" >&2; exit 2; }
slot=-1; said=0
while :; do
    for k in $(seq 0 $((N - 1))); do
        exec 9>"$(lockf $k)"
        if flock -n 9; then slot=$k; break; fi
        exec 9>&-
    done
    [ $slot -ge 0 ] && break
    [ $said -eq 0 ] && { echo "trace_lock: all $N slots busy, waiting" >&2; said=1; }
    sleep 3
done
H=$(holdf $slot)
echo "$(date -Is) pid=$$ ${TRACE_LOCK_OWNER:-unknown} :: $*" > "$H"
"$@"
rc=$?
: > "$H"
exit $rc

#!/bin/bash
# batch.sh <prefix> <seconds> <label> <room>...: runs 2 at a time (agent cap), fixtures /root/probe/d367-agents/rsweep17/fix/<room>-<label>.json
P=$1; S=$2; L=$3; shift 3
cd "/c/Flycast-Evidence/re4-dreamcast/rsweep17-20261017/_tools"
run1() { PERIOD=30 PURPOSE="rsweep17 render sweep $P-$1 on $L, $S s (OT_PROF/PROP_PROF, Flycast)" bash t-run.sh $P-$1 $L /root/probe/d367-agents/rsweep17/fix/$1-$L.json $S > run-$P-$1.log 2>&1; }
set -- "$@"
while [ $# -gt 0 ]; do
  a=$1; shift; b=${1:-}; [ -n "$b" ] && shift
  run1 $a & pa=$!
  [ -n "$b" ] && { sleep 3; run1 $b & pb=$!; }
  wait $pa; [ -n "$b" ] && wait $pb
  tail -n 2 run-$P-$a.log | head -1; [ -n "$b" ] && tail -n 2 run-$P-$b.log | head -1
done

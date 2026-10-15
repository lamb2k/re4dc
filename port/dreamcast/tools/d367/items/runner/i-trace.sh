#!/bin/bash
# i-trace.sh <name> <label> <fixture> <stop tick> [seconds] (Git Bash): one lane items logic-trace run (i-run.sh) under a
# trace slot (trace_lock.sh, held only around the run). Both runs of a STRICT pair use the same stop tick.
N=$1; L=$2; FIX=$3; STOP=$4; SECS=${5:-600}
K=/root/probe/lanes-20261014/items/tree/port/dreamcast/tools/d367
G=/c/Flycast-Evidence/re4-dreamcast/items-20261014/_tools
cat > $G/tr-$N.sh <<EOS
cd $G && RE4DC_LOG_STOP_TICK=$STOP PURPOSE='items trace $N: $L, $FIX, stop $STOP' bash i-run.sh $N $L $FIX $SECS > $G/run-$N.log 2>&1
EOS
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- env TRACE_LOCK_OWNER=claude-items-$N bash $K/trace_lock.sh "/mnt/c/Program Files/Git/bin/bash.exe" $(cygpath -m $G/tr-$N.sh | sed 's#^C:#/c#')
tail -3 $G/run-$N.log

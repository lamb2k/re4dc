#!/bin/bash
# qjob3.sh "<kind> args...": one lane items job (kind run | trc | hw), launched behind the slot lock
G=/c/Flycast-Evidence/re4-dreamcast/items-20261014/_tools
set -- $1
cd $G
slot() { until mkdir $G/.lk 2>/dev/null; do sleep 10; [ -d $G/.lk ] && [ $(( $(date +%s) - $(stat -c %Y $G/.lk 2>/dev/null || date +%s) )) -gt 300 ] && rmdir $G/.lk 2>/dev/null; done
  while :; do n=$(tasklist 2>/dev/null | grep -ci flycast); f=$(df -BG /c | awk 'NR==2{print $4+0}'); [ "$n" -lt 8 ] && [ "$f" -ge 20 ] && break; sleep 30; done
  (sleep 150; rmdir $G/.lk) & }
k=$1; shift
[ -e $G/q-$1.log ] && grep -q "moved to\|done " $G/q-$1.log && { echo "skip $1 (done)"; exit 0; }
# yield (coordinator 10-14): crash lane and test 11 lead first; a trace waits while 2+ of the 4 trace slots are held
if [ $k = trc ]; then
  while :; do u=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /root/probe/lanes-20261014/items/tree/port/dreamcast/tools/d367/trace_lock.sh --status 2>&1 | tr -d '\r' | sed -n 's/^slots \([0-9]*\)\/.*/\1/p'); [ "${u:-4}" -lt 2 ] && break; sleep 60; done
fi
# my own concurrency cap (coordinator 10-14 19:40): at most MAXMINE (2) of this lane's jobs running
until [ $(ls -d $G/.run-* 2>/dev/null | wc -l) -lt ${MAXMINE:-2} ]; do sleep 20; done
slot
touch $G/.run-$1
case $k in
  run) PERIOD=${PERIOD:-15} bash i-run.sh "$@" > $G/q-$1.log 2>&1 ;;
  trc) bash i-trace.sh "$@" > $G/q-$1.log 2>&1 ;;
  gpu) RE4DC_TA_STATS=ta-stats.txt RE4DC_TA_STATS_ALL=1 RE4DC_TA_FRAMEADDR=$5 RUNNER=run-emulator-objsta.py PERIOD=30 bash i-run.sh $1 $2 $3 $4 > $G/q-$1.log 2>&1 ;;   # name label fixture secs frameaddr: TA stats v6
  bench) X=$4; [ "$X" = - ] && X=; BENCH_DATA_EXTRA=$X bash //wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/items/tree/port/dreamcast/tools/d367/benchmark/bench-run.sh r101 $2 $3 ${5:-220} > $G/q-$1.log 2>&1 ;;   # name label benchname extra-data
  hw) MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /root/probe/lanes-20261014/objs/work/o-hw.sh $2 $3 hw-$1 $4 ${5:-7} > $G/q-$1.log 2>&1 ;;
esac
rm -f $G/.run-$1
st=$(grep -ao 'RUN_FAILED[^]]*]' $G/q-$1.log | head -1)
if [ -n "$st" ]; then mv $G/q-$1.log $G/q-$1.failed-$(date +%H%M%S).log; echo "$(date +%T) $k $1: FAILED $st" | tee -a $G/qdone.txt
else echo "$(date +%T) $k $1: $(tail -2 $G/q-$1.log | tr '\n' ' ')" | tee -a $G/qdone.txt; fi

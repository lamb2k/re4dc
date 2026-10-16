#!/bin/bash
# gd.sh <prefix> <label> <fixture-name> <secs> <seed...>: GDEMU race gate on harness scenarios (lane ch2code16 10-16):
# flycast-console (run-emulator-novsync-i26-console.py) with RE4DC_GD_PROFILE=gdemu RE4DC_GD_JITTER=20000, one run per seed.
P=$1; L=$2; N=$3; S=$4; shift 4
cd "/c/Flycast-Evidence/re4-dreamcast/ch2code-20261016/_tools"
for s in "$@"; do (RUNNER=run-emulator-novsync-i26-console.py RE4DC_GD_PROFILE=gdemu RE4DC_GD_JITTER=20000 RE4DC_GD_SEED=$s \
  PURPOSE="ch2code16 GDEMU race gate seed $s, $N on $L" bash t-run.sh $P-s$s $L /root/probe/lanes-20261016/ch2/k/fix/$N-$L.json $S > run-$P-s$s.log 2>&1 &); sleep 20; done
while :; do k=0; for s in "$@"; do grep -q -E "moved to|failed|exists" run-$P-s$s.log 2>/dev/null && k=$((k+1)); done; [ $k -ge $# ] && break; sleep 10; done
BADRE='MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))'
fail=0
for s in "$@"; do d=../$P-s$s; o=$d/capture/run-output.txt
  stop=$(grep -a -m1 -E 'HALT|FAULT|Out of memory' $o 2>/dev/null | cut -c1-80); nbad=$(grep -a -c -E "$BADRE" $o 2>/dev/null)
  rooms=$(grep -aoE 'room enter [0-9a-f]+' $o 2>/dev/null | awk '{print $3}' | awk '!s[$0]++' | tr '\n' ,)
  prof=$(cat $d/capture/serial*.txt $d/capture/flycast.log 2>/dev/null | grep -a -m1 -o 'GDCONSOLE profile=[a-z]*')
  ok=1; [ -n "$stop" ] && ok=0; [ "${nbad:-0}" != 0 ] && ok=0; case "$rooms" in *11d*) ;; *) ok=0;; esac
  [ $ok = 1 ] || fail=$((fail+1)); echo "seed $s $([ $ok = 1 ] && echo ok || echo FAIL) rooms=$rooms bad=${nbad:-0} stop=${stop:--} ${prof:-noprofile}"
done
echo "GDEMU RACE GATE (gdemu, ch2 door r11c<->r11d) $([ $fail = 0 ] && echo PASS || echo FAIL) $fail/$# failed"

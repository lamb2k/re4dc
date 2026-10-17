# vsum.sh <harness> <suffix> rooms: TEXCHK + vram_gate per run (WSL)
H=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/$1; S=$2; shift 2
G=/root/probe/lanes-20261016/ch4found/tree/port/dreamcast/tools/d367/vram/vram_gate.py
for r in "$@"; do
  d=$H/scenarios/cx-$r-walk-$S; L=$d/capture/run-output.txt
  [ -f $L ] || { echo "$r $S no log"; continue; }
  tc=$(python3 -c "import json;d=json.load(open('$d/rfp-result.json'));c=d.get('checks',{});print(d.get('overall'),'tex_check='+str(c.get('tex_check')),'no_fatal='+str(c.get('no_fatal')))" 2>/dev/null)
  tx=$(grep -a 'texchk: room' $L | tail -1 | grep -o 'total_fails=[0-9]*')
  vr=$(grep -a "vram room: r=${r#r}" $L | tail -1 | grep -o 'pinned=[0-9]* dynamic=[0-9]* other=[0-9]* free=[0-9]* largest=[0-9]*\|min_free=[0-9]* min_largest=[0-9]*\|evicted=[0-9]*' | tr '\n' ' ')
  vg=$(python3 $G $L 2>&1 | grep -E 'PASS|FAIL' | tail -1 | cut -c1-120)
  echo "$r $S | $tc | $tx | $vr | gate: $vg"
done

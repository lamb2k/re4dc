#!/bin/bash
# stfix.sh (WSL): STRICT trio fixtures (h2 / bell / door103eq) for the off / on trace arms, T17V_DATA, armed.
T=/root/probe/lanes-20261016/farmprop17/port/dreamcast/tools/d367
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
F=/root/probe/lanes-20261016/fp17/fix
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17V_DATA)")
export RE4DC_RESIDENT_STRICT=1
S=$T/fullplay/segments
mk() { # label out warp [pad]
  local P=""; [ -n "${4:-}" ] && P="--pad $4"
  python3 $T/test11/t11-fix.py $1 $2.raw.json --data $D --warp $3 $P > $2.log 2>&1 &&
  python3 $T/texchk/fixture_arm.py $2.raw.json $2 $1 --programs-dir "$HW/programs" >> $2.log 2>&1 && echo "ok $2" || { echo "FAIL $2"; tail -3 $2.log; }
}
for a in o q; do
  mk fp17${a}rT $F/sta-$a.json $S/h2-warp.txt $S/h2-pad.txt &
  mk fp17${a}rT $F/stb-$a.json $S/bell-warp.txt &
  mk fp17${a}rT $F/stc-$a.json /mnt/c/Flycast-Evidence/re4-dreamcast/radiosub-20261016/_warps/door103eq.txt &
done
wait

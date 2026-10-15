#!/bin/bash
# hw.sh <scene> <arm label> <name> <count A:B> <stride> (WSL): one MODELLED hw-model run on the T15 data set, traces KEPT
# for the call-tree pass (cg.sh), which deletes them after.
set -u
T=/root/probe/lanes-20261015/actorplan/port/dreamcast/tools/d367
export BENCH_EV=/mnt/c/Flycast-Evidence/re4-dreamcast/actorplan-20261015
export BENCH_DATA=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA)")
mkdir -p /root/probe/lanes-20261015/actorplan-k/hw
sed 's/ --drop-traces / /' $T/benchmark/bench-hw.sh > /root/probe/lanes-20261015/actorplan-k/bench-hw-keep.sh
cp $T/benchmark/benchmark-$1-warp.txt /root/probe/lanes-20261015/actorplan-k/ 2>/dev/null
# bench-hw.sh resolves HERE from its own path: run the copy with HERE pointing at the tree's benchmark dir
sed -i "s|^HERE=.*|HERE=$T/benchmark|" /root/probe/lanes-20261015/actorplan-k/bench-hw-keep.sh
sed -i "s|^TREE=.*|TREE=/root/probe/lanes-20261015/actorplan|" /root/probe/lanes-20261015/actorplan-k/bench-hw-keep.sh
bash /root/probe/lanes-20261015/actorplan-k/bench-hw-keep.sh "$1" "$2" "$3" "$4" "$5" > /root/probe/lanes-20261015/actorplan-k/hw/hw-$3.log 2>&1
tail -6 /root/probe/lanes-20261015/actorplan-k/hw/hw-$3.log

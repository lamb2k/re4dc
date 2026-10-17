set -e
L=/root/probe/lanes-20261016/ch4found; cd $L/tree
mkdir -p $L/hot11; git show origin/land/t17-pak17-motion:port/dreamcast/tools/d367/motion/motion_hot.py > $L/hot11/motion_hot.py
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4zmW/scenarios
python3 $L/hot11/motion_hot.py /root/probe/lanes-20261010/r117/rooms/prep-em11/motion-residency-report.json $L/hot11/em11-ch4.json $E/cx-r226-walk-z1/capture/run-output.txt $E/cx-r222-walk-z1/capture/run-output.txt $E/cx-r212-walk-z1/capture/run-output.txt --profile "run-derived hot set: chapter 4 em11 (r226 dec3 kill rig + B3/B5, r222 / r212 kill rigs; ch4found16 z1, Flycast, MOTION_COLD_POOL_CASTLE=131072)"
python3 -c "
import json;d=json.load(open('$L/hot11/em11-ch4.json'));print(d['union'],d['hot_payload_bytes'],d['cold_clips'])"

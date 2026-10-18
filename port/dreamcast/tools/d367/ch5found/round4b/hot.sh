#!/bin/bash
# em36 hot set from the r307 MOTION_MISS_LOG runs (m4c..m8c), then the hot-list preparation
set -e
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016/h-cx5mmW/scenarios
T=/root/probe/lanes-20261016/ch5found/tree/port/dreamcast/tools/d367/motion
mkdir -p $T/hot
python3 $T/motion_hot.py /root/probe/lanes-20261016/ch5found/prepem/prepc-em36/motion-residency-report.json $T/hot/em36-r307.json \
  $E/cx-r307-walk-m4c/capture/run-output.txt $E/cx-r307-walk-m5c/capture/run-output.txt $E/cx-r307-walk-m6c/capture/run-output.txt \
  $E/cx-r307-walk-m7c/capture/run-output.txt $E/cx-r307-walk-m8c/capture/run-output.txt \
  --profile 'run-derived hot set: r307 MOTION_MISS_LOG runs (spawn, release walk, hit reactions, death; ch5found16 m4c..m8c, Flycast)'
sed -i 's#/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016/h-cx5mmW/scenarios/##' $T/hot/em36-r307.json
python3 -c "import json;d=json.load(open('$T/hot/em36-r307.json'));print(d['union'],d['hot_payload_bytes'])"
bash /mnt/c/tmp/ch5b/prepc.sh preph $T/hot/em36-r307.json em36

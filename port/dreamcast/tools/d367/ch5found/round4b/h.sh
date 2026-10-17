#!/bin/bash
# h.sh <arm>: clone the lane harness for an arm (round 4 B)
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
[ -d $E/h-$1 ] || python3 /mnt/c/tmp/ch5/clone_h.py "/mnt/c/Game Dev/Emulators/re4-rfp-20261015-st3e3" $E/h-$1 $1 /root/probe/lanes-20261016/ch5found/build | cut -c1-150

#!/bin/bash
# eq4.sh (Git Bash): eq3 scenes with a disk wait (stage floor 16 GiB + 807 MB) and up to 4 tries per scene.
SCR=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261015/sh4zam/scr
E=/c/Flycast-Evidence/re4-dreamcast/sh4zam-skin-20261015
for s in ${SCENES:-bell h2 door103 call}; do
  for try in 1 2 3 4; do
    for i in $(seq 1 120); do f=$(df -k /c | awk 'NR==2{print $4}'); [ "$f" -ge 18200000 ] && break; sleep 30; done
    rm -rf $E/eq3-$s-zm
    SCENES=$s bash $E/_tools/eq3.sh
    grep -q "^.* $s: eq3-$s-zm halt=" $SCR/eq3.log && tail -1 $SCR/eq3.log | grep -q "eq3 finished" && grep "$s: eq3-$s-zm halt=" $SCR/eq3.log | tail -1 && break
    [ -d $E/eq3-$s-zm/capture ] && break
    sleep 60
  done
done
echo "$(date +%T) eq4 finished" >> $SCR/eq3.log

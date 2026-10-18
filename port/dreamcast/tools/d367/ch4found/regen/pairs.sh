set -uo pipefail
S0=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4amW/scenarios
bash /mnt/c/tmp/ch4/pairs.sh r214:$E/cx-r214-walk-a1/capture/run-output.txt:em/em14.drs,em/em1a.drs,em/em25.drs r216:$E/cx-r216-walk-a1/capture/run-output.txt:em/em3c.drs r224:$E/cx-r224-walk-a1/capture/run-output.txt:em/em2b.drs r226:$E/cx-r226-walk-a1/capture/run-output.txt:em/em11.drs r227:$E/cx-r227-walk-a1/capture/run-output.txt:em/em14.drs r229:$E/cx-r229-walk-a1/capture/run-output.txt:em/em29.drs,em/em18.drs r22b:/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4bmW/scenarios/cx-r22b-walk-a2/capture/run-output.txt | cut -c1-80
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016
bash /mnt/c/tmp/ch4/pairs.sh r229:$E/h-cxc4amW/scenarios/cx-r229-walk-a1/capture/run-output.txt:em/em29.drs,em/em18.drs,st2/r221.das,st2/r215.das,st2/r22b.das,evd/r22bs00.evd r22b:$E/h-cxc4bmW/scenarios/cx-r22b-walk-a2/capture/run-output.txt:evd/r22bs00.evd,st2/r221.das,st2/r229.das,em/em2c.drs | cut -c1-80
E1=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4amW/scenarios/cx-r229-walk-a1/capture/run-output.txt
grep 'pair missing' $E1 | grep -v -e 215466cb -e 971b53b9 > /root/probe/lanes-20261016/ch4found/pairs/r229-3.log
bash /mnt/c/tmp/ch4/pairs.sh r229:/root/probe/lanes-20261016/ch4found/pairs/r229-3.log:em/em29.drs,em/em18.drs | cut -c1-80
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4cmW/scenarios
bash /mnt/c/tmp/ch4/pairs.sh r21b:$E/cx-r21b-walk-a3/capture/run-output.txt:em/em15.drs | cut -c1-80
L=/root/probe/lanes-20261016/ch4found
cd $L/tree/port/dreamcast/tools/d367
LOG=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4vmW/scenarios/cx-r229-walk-l3/capture/run-output.txt
rm -rf "${L:?}/pairs/r229c"
python3 pairs_from_log.py --iso /root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso --output $L/pairs/r229c --log "$LOG" --file ss/cmn/ss_oc205.dat --file ss/cmn/ss_oc206.dat --file ss/eng/ss_term.dat > $L/pairs/r229c.log 2>&1; echo r229c rc=$?
python3 $S0/c4r-v4.py $S0/c4r-missing-src.tsv ch4found/pairs

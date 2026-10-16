#!/bin/bash
# pkc.sh (WSL): r101 C16 landing (landA 37bcf721, w16crP, twin w16sq3, evidence kosc); copy of pk.sh: test 16 r101 world landing KOS squeeze + GDEMU twin base (copy of mist16 pk3.sh): rP w16lrP (T15REC, tree
# lane/worldtest16 t15/int 189ac886 + the T15_DATA swap), the T15_DATA set packaged on the test 14 candidate tree
# (t8-pkgtree + mkgdi), twin KOS_WATCH/KOS_SQUEEZE/W11_FIXTURE, master on ext4.
set -e
K=/root/probe/worldtest16-20261016/k; R=$K/kosc; TR=/root/probe/worldtest16-20261016/landA; T=$TR/port/dreamcast/tools/d367
L=w16crP; O=/root/probe/lanes/route/out-$L
head -3 $O/stack.txt
rm -rf $R; mkdir -p $R/fix $R/logs
python3 $T/fullplay/fp_iso.py extract "/mnt/c/Game Dev/Emulators/RE4DC-Test14-Candidate/gdemu/track03.bin" $R/t14tree --manifest $R/t14man.json --ipbin $R/t14ip.bin | tail -1
rm -f $R/t14tree/1ST_READ.BIN
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA)")
echo "data $D"
python3 $T/test11/t11-fix.py $L $R/fix/pkg-$L.json --data $D | tail -c 60
PKG_SRC=$R/t14tree PKG_K=$R python3 /root/probe/lanes-20261011/test8/t8-pkgtree.py $L $R/fix/pkg-$L.json > $R/logs/pkgtree.txt; tail -1 $R/logs/pkgtree.txt
(cd $T && bash mkgdi.sh $O/re4dc-game.elf $R/pkgtree $R/gdemu | tail -1)
G=$R/gdemu; C=$R/rel
python3 $T/fullplay/fp_iso.py extract "$G/$(awk 'NR==4{print $5}' "$G/disc.gdi")" $C/tree --manifest $C/manifest.json --ipbin $C/IP.BIN | tail -1
sha256sum $C/tree/dc/native/r101/* | cut -c1-16
FP_TREES=$R/trees bash $T/fullplay/fp_twin.sh $O w16sq3 KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 2>&1 | grep -E "IDENTITY|TWIN" | cut -c1-160
EV=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/kosc
rm -rf $EV/_discs; mkdir -p $EV/_discs
bash $T/fullplay/fp_master.sh $C/tree $C/manifest.json $C/IP.BIN $EV/_discs/twin /root/probe/lanes/route/out-fpw16sq3W | tail -1
echo PK_DONE
rm -rf "$R/gdemu" "$R/pkgtree" "$R/t14tree"

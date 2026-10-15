#!/bin/bash
# kos1.sh: KOS squeeze twin of szmrP (t14/rc recipe + GAME_SHZ_MEMSET=1, adopt da53973d), mastered on the t14 release tree
set -u
A=/root/probe/lanes-20261015/sh4zam/adopt
F=$A/port/dreamcast/tools/d367/fullplay
R=/root/probe/lanes-20261014/fullplay/work/rel-45fa2c732061d975
FP_TREE=$A bash $F/fp_twin.sh /root/probe/lanes/route/out-szmrP szmsq KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 || { echo "TWIN FAIL"; exit 1; }
bash $F/fp_master.sh $R/tree $R/manifest.json $R/IP.BIN /mnt/c/Flycast-Evidence/re4-dreamcast/sh4zam-skin-20261015/_discs/szmsq /root/probe/lanes/route/out-fpszmsqW || { echo "MASTER FAIL"; exit 1; }
echo TWIN DONE

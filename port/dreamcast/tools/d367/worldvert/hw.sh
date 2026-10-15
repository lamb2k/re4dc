#!/bin/bash
# hw.sh <arm label> <name> <cross|house> [window] [stride] (WSL): lane worldvert hw-model (MODELLED) of one cost arm, test 13
# data + wv101. Evidence C:\Flycast-Evidence\re4-dreamcast\worldvert-20261015\hwmodel-<name>.
L=$1; N=$2; SC=$3; WIN=${4:-500:799}; ST=${5:-30}
export HWM_EVROOT=/mnt/c/Flycast-Evidence/re4-dreamcast
K=/root/probe/lanes-20261015/worldvert-work; T=/root/probe/lanes-20261015/worldvert
case $SC in cross) WF=/root/probe/lanes-20261015/worldlod-work/cross-warp.txt ;; house) WF=$T/port/dreamcast/tools/d367/benchmark/benchmark-r101house-v3-warp.txt ;; esac
mkdir -p /mnt/c/Flycast-Evidence/re4-dreamcast/worldvert-20261015
BENCH_EV=/mnt/c/Flycast-Evidence/re4-dreamcast/worldvert-20261015 BENCH_DATA=r119c,em29,fbec,r100tr4,smx101,sg101,t12tex,objs12b,merchant,items12,acc12d,blackps2w,t121tex,objs13d,ashley13,bake13,t13tex,wv101 BENCH_WARP=$WF \
  bash $T/port/dreamcast/tools/d367/benchmark/bench-hw.sh r101 $L $N $WIN $ST

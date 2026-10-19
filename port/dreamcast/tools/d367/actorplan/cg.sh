#!/bin/bash
# cg.sh <hwmodel dir> (WSL): call-tree pass (design-logic hwsim_cg, nominal) over the kept traces -> <dir>/cg, then
# deletes the raw traces (hwmodel: a size list stays).
set -euo pipefail
E=$1; A=/root/probe/d367-agents/design-logic/tools; P=$E/cg
N=/opt/toolchains/dc/sh-elf/bin/sh-elf-nm; ELF=$E/re4dc-game.elf; mkdir -p $P
$N -n $ELF | awk '$2 ~ /^[TtWw]$/ {print $1}' | sort -u > $P/cg.funcs.txt
$N -n -C $ELF | awk '$2 ~ /^[TtWw]$/' > $P/cg.syms.txt
VBR=$($N $ELF | awk '$3=="_irq_vma_table"{print $1}')
: > $P/cg.watch.txt
TR=$(ls $E/trace/trace-*.bin)
$A/hwsim_cg --elf $ELF --out $P/cgsim --cg $P/cg --cg-vbr ${VBR:-0} --cg-funcs $P/cg.funcs.txt --cg-watch $P/cg.watch.txt $TR > $P/cg.log 2>&1
ls -la $E/trace/*.bin > $E/trace/sizes.txt; rm -f $E/trace/trace-*.bin
tail -2 $P/cg.log

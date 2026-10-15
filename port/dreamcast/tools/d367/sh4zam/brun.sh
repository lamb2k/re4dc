#!/bin/bash
# brun.sh <kind r1|r2|align|kos0|kos1>  (Git Bash; lane sh4zam-direct) ZAMR2 benchmark disc (szbB / szbQ, FIXSET 1 2 6,
# bench program 472c4496 = bench/definitive 702d82ef + lane/sh4zam-direct) through fp_run.py, as the Part 1 gates.
K=$1
FP="C:/Game Dev/Emulators/RE4DC-Test13-Release"
FPR=$(cygpath -w "//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261015/sh4zam/tree/port/dreamcast/tools/d367/fullplay/fp_run.py")
KEYS='C:\Users\lambd\.claude\jobs\1e668c67\tmp\crowd12\keys-def.txt'
E='C:\Flycast-Evidence\re4-dreamcast'
SB="$(cat //wsl.localhost/Ubuntu-24.04/root/probe/lanes/route/out-szbB/syms.txt)"
SQ="$(cat //wsl.localhost/Ubuntu-24.04/root/probe/lanes/route/out-szbQ/syms.txt)"
case $K in
  r1|r2) python "$FPR" --disc 'C:\Flycast-Evidence\_bench-discs\szbB-s126' --cap "$E\zamr2-s126-$K-472c4496" --syms "$SB" --seconds 1500 --keys "$KEYS" --stop "bench: A pressed" --name zamr2-$K ;;
  align) python "$FPR" --disc 'C:\Flycast-Evidence\_bench-discs\szbB-s126' --cap "$E\zamr2-s126-align-472c4496" --syms "$SB" --seconds 4000 --keys "$KEYS" --stop "bench: results page 2" --align --name zamr2-al ;;
  kos0|kos1) f=${K#kos}; python "$FPR" --disc "C:\Flycast-Evidence\_bench-discs\szbQ-s126-sq49152-$f" --cap "$E\zamr2-s126-kos49152-$f-472c4496" --syms "$SQ" --seconds 1500 --keys "$KEYS" --stop "bench: results page 2" --name zamr2-sq$f ;;
esac

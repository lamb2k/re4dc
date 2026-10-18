set -uo pipefail
L=/root/probe/lanes-20261017r/ch2regen; S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen
python3 $L/tools/gcx.py $L/src st1/r111.das st1/r112.das > /dev/null 2>&1 || python3 $L/tools/gcx.py $L/src St1/r111.das St1/r112.das 2>&1 | tail -2
ls $L/src/st1
for r in r10f r111 r112 r11f r200; do echo "== $r"; bash $S/room.sh $r $L/t-ch2code16 2>&1 | tail -2; ls $L/rooms/t-ch2code16/tex-$r 2>/dev/null | wc -l; done

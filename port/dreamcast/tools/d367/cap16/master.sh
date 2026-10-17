# master.sh <fly|console> [begin end killstart gap count]: GDI of the cap comparison disc on ext4
set -e
S=/root/probe/lanes-20261016/cap16
O=/root/probe/lanes/route/out-cap16brW
M=$S/tree/port/dreamcast/tools/d367/mkgdi.sh
case $1 in
 fly) python3 "/mnt/c/Game Dev/Emulators/cap16-20261016/py/mkfix.py" $S/fix/flycast ${2:-300} ${3:-480} ${4:-330} ${5:-60} ${6:-3} >/dev/null
      rm -rf $S/disc-fly; LAYOUT=legacy TITLE="RE4DC CAP COMPARE FLYCAST" PRODUCT=T0004 bash $M $O/re4dc-game.elf $S/pkg-cap16brW/pkgtree $S/disc-fly $S/fix/flycast > $S/master-fly.log 2>&1 || { tail -20 $S/master-fly.log; exit 1; }
      E=/mnt/c/Flycast-Evidence/re4-dreamcast/cap16-20261016/disc-fly; mkdir -p $E; rm -f $E/*; cp $S/disc-fly/disc.gdi $S/disc-fly/track0* $E/; D=$S/disc-fly ;;
 console) python3 "/mnt/c/Game Dev/Emulators/cap16-20261016/py/mkfix.py" $S/fix/console 450 1350 750 150 4 >/dev/null
      rm -rf $S/disc-console; TITLE="RE4DC CAP COMPARE (NOT THE GAME)" PRODUCT=T0004 bash $M $O/re4dc-game.elf $S/pkg-cap16brW/pkgtree $S/disc-console $S/fix/console > $S/master-console.log 2>&1 || { tail -20 $S/master-console.log; exit 1; }; D=$S/disc-console ;;
esac
tail -3 $S/master-$1.log; ls -la $D | head

# gate.sh: bell-gate warp discs (G build = test 16 rW + CAP_COMPARE runtime cap + cap logs), caps 3/4/6, Flycast legacy layout
set -e
S=/root/probe/lanes-20261016/cap16
O=/root/probe/lanes/route/out-cap16grW
M=$S/tree/port/dreamcast/tools/d367/mkgdi.sh
[ -d $S/pkg-cap16grW/pkgtree ] || bash "/mnt/c/Game Dev/Emulators/cap16-20261016/sh/pkg.sh" cap16grW
for c in 3 4 6; do
  F=$S/fix/gate$c; mkdir -p $F
  cat > $F/warp.txt <<EOT
name cap16-gate-c$c
# lane cap16 bell gate (benchmark-r101capgate setup: Leon walks into PS2 area 0x21) at runtime cap $c, fast kill rig
room 0x101
pos -7914 0 -254
ang 2.9600
find 0x00002000
inv default
god
cap $c
alivelog 150
kill 0 60 0x101
killrep 24 20
goto 300 17486 700 -16680
EOT
  rm -rf $S/disc-gate$c
  LAYOUT=legacy TITLE="RE4DC CAP GATE $c" PRODUCT=T0004 bash $M $O/re4dc-game.elf $S/pkg-cap16grW/pkgtree $S/disc-gate$c $F > $S/master-gate$c.log 2>&1 || { tail -20 $S/master-gate$c.log; exit 1; }
  E=/mnt/c/Flycast-Evidence/re4-dreamcast/cap16-20261016/disc-gate$c; mkdir -p $E; rm -f $E/*; cp $S/disc-gate$c/disc.gdi $S/disc-gate$c/track0* $E/
  rm -rf $S/disc-gate$c
done
ls -la /mnt/c/Flycast-Evidence/re4-dreamcast/cap16-20261016/disc-gate3

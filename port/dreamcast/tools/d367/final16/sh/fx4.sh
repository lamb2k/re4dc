W="/mnt/c/Game Dev/Emulators/final16-20261016/warps"; L=/root/probe/lanes-20261016/final16
cp "$W"/*.txt $L/warps/
ARM=${ARM:-f2mW}
E=/mnt/c/Flycast-Evidence/re4-dreamcast/final16-20261016
[ -d $E/h-$ARM ] || bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/h.sh" $ARM
ARM=$ARM bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/mkfix.sh" ${V:-m3} $L/warps/fx-r332-${W2:-m3}.txt ${PREP:-$L/prepem/prepc-em31} r332s00,r332s10,r332s20 | tail -2
python3 "/mnt/c/Game Dev/Emulators/final16-20261016/py/padfx.py" $L/fixtures/r332/fx-r332-${V:-m3}.armed.json $L/warps/padskip-s00.txt

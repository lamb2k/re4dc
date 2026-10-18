# prep4.sh: em31 hot-set preparation (preph-em31) and AICA banks for the all-hot (aica-fa) and hot (aica-f) archives
set -e
L=/root/probe/lanes-20261016/final16
bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/prep3.sh" preph-em31 $L/tree/port/dreamcast/tools/d367/motion/hot/em31-r332.json
cd $L/snd
PREP=$L/prepem/prepa-em31 bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/snd.sh" > snd-fa.log 2>&1 || { tail snd-fa.log; exit 1; }
rm -rf aica-fa; cp -al aica-f aica-fa; ls -la aica-fa/em/em31.drs
PREP=$L/prepem/preph-em31 bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/snd.sh" > snd-fh.log 2>&1 || { tail snd-fh.log; exit 1; }
ls -la aica-f/em/em31.drs; grep -E "^  r332" snd-fh.log

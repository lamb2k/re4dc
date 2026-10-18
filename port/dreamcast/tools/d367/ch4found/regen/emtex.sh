set -euo pipefail
S0=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261016/ch4found; TT=$L/tree/port/dreamcast/tools; S=/root/probe/codex-cx-fixtures-20261013/dependencies/source
mkdir -p $L/emtex4; cd $L/emtex4
for e in em3c em11 em13 em14 em15 em18 em1a em25 em29 em2b em2d; do
  [ -d tex-$e ] && continue
  [ -f $S/em/$e.drs ] || { echo "no src $e"; continue; }
  echo em/$e.drs > $e.manifest
  python3 $TT/prepare_native_ui.py $S $e.manifest $L/emtex4/tex-$e > $e.log 2>&1 || true; echo "$e $(tail -1 $e.log | cut -c1-80)"
done
python3 $S0/c4r-v4.py $S0/c4r-missing-src.tsv /emtex4/

set -euo pipefail
S0=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261016/ch4found; TT=$L/tree/port/dreamcast; R=r226
A=/root/probe/codex-cx-fixtures-20261013/output/$R/ancillary
S=$TT/tools-ch4shadow5; rm -rf "${S:?}"; mkdir -p $S
cp -r $TT/tools/*.py $S/; cp -r $TT/tools/assetpipe $S/ 2>/dev/null || true
cp $S0/lm-b47.py $S/le_mirror.py
X=$L/statue; rm -rf "${X:?}"; mkdir -p $X/tex
cp -rs $A/tex/. $X/tex/
cd $S
python3 /mnt/c/tmp/ch4/cast/genpkg.py $X/tex -- --compact-room $A/source/st2/$R.das --compact-room-mips --textures $X/tex --output $X/gen > $X/gen.log 2>&1 || { tail -3 $X/gen.log; exit 1; }
rm -rf $L/compact5/$R; mkdir -p $L/compact5
python3 prepare_native_ui.py --compact-room $A/source/st2/$R.das --compact-room-mips --textures $X/tex --output $L/compact5/$R > $L/compact5/$R.log 2>&1
tail -1 $L/compact5/$R.log | cut -c1-200
mkdir -p $L/st5
SRC=$A/source/st2/$R.das CDIR=$L/compact5 bash $TT/tools/d367/castle/release31.sh $L/st5 r226 2>&1 | tail -1 | cut -c1-200
python3 $S0/c4r-v4.py $S0/c4r-missing-src.tsv ch4found/st5
python3 $S0/c4r-v4.py $S0/c4r-missing-src.tsv ch4found/pairs/r226

set -uo pipefail
# replay of /c/tmp/ch4/compact.sh + compact2.sh (10-16 23:40Z..10-17 13:45Z); A from the cx replay (or cxextra for r21a)
S0=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261016/ch4found
TT=$L/tree/port/dreamcast
X=/root/probe/lanes-20261018/ch4regen/cxextra
[ -d $X/r21a/ancillary/tex ] || python3 $S0/c4r-cxrun.py v0 $X r21a
SH=$TT/tools-ch4shadow; rm -rf "${SH:?}"; mkdir -p $SH
cp -r $TT/tools/*.py $SH/; cp -r $TT/tools/assetpipe $SH/; cp $S0/lm-b47.py $SH/le_mirror.py
mkdir -p $L/compact4
one() { R=$1; T=$2
  A=/root/probe/codex-cx-fixtures-20261013/output/$R/ancillary; [ -d $A ] || A=$X/$R/ancillary
  rm -rf "${L:?}/compact4/$R"
  (cd $T && python3 prepare_native_ui.py --compact-room $A/source/st2/$R.das --compact-room-mips --textures $A/tex --output $L/compact4/$R > $L/compact4/$R.log 2>&1) || { echo "$R FAIL $(tail -1 $L/compact4/$R.log)"; return; }
  SRC=$A/source/st2/$R.das CDIR=$L/compact4 bash $TT/tools/d367/castle/release31.sh $L $R 2>&1 | tail -2 | tr '\n' ' '; echo
}
:
for R in r212 r215 r22b r224 r226; do one $R $SH; done
python3 $S0/c4r-v4.py $S0/c4r-missing-src.tsv ch4found/rel31

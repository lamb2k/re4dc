set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261016/ch4found; TT=$L/tree/port/dreamcast/tools; S2=/root/probe/codex-cx-fixtures-20261013/dependencies/source
mkdir -p $L/evt4; cd $L/evt4
ls $S2/evd | grep -E '^r2(1[0-9a-f]|2[0-9a-f])s' | sed 's#^#evd/#' > evd4.manifest; tr '\n' ' ' < evd4.manifest; echo
[ -d tex ] || python3 $TT/prepare_native_ui.py $S2 evd4.manifest $L/evt4/tex > tex.log 2>&1 || true; tail -c 300 tex.log; echo
find tex -name '*.re4tex' | wc -l
python3 $S/c4r-v4.py $S/c4r-missing-src.tsv /evt4/

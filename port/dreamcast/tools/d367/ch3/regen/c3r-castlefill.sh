set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
cd /tmp
python3 "$S/c3r_gdix.py" "/mnt/c/Flycast-Evidence/_bench-discs/bfc-r209-final/track03.bin" "$L/extra/hunt/8479815d-291af55c.re4tex" dc/tex/8/8479815D_291AF55C.RE4TEX
python3 "$S/c3r_gdix.py" "/mnt/c/Flycast-Evidence/_bench-discs/bfc-r209-final/track03.bin" "$L/extra/hunt/67a581c9-a3339122.re4tex" dc/tex/6/67A581C9_A3339122.RE4TEX
sha256sum "$L/extra/hunt/67a581c9-a3339122.re4tex" | cut -c1-8
sha256sum "$L/extra/hunt/8479815d-291af55c.re4tex" | cut -c1-8
python3 "$S/c3r_castlefill.py" "$L/trees/origin/lane/castle-1015/port/dreamcast/tools" "$L/extra/vq-c34/tex-c34.pak" "$L/extra/hunt" "$S/castleloose.json" "$L/extra/base/p-51f1f7a4.pak"
bash "$S/c3r-castlepak.sh" 2>&1 | tail -6

set -euo pipefail
# c3r-t12d.sh: recover tex-t12d.pak (43be4b59) from the harvested tex-t121.pak (b097d061)
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
B=$L/extra/base; mkdir -p "$B"
[ -e "$B/t121-b097d061.pak" ] || python3 "$S/c3r_gdix.py" "/mnt/c/Game Dev/Emulators/RE4DC-Benchmark-WLODP-7d987c3d/gdemu/track03.bin" "$B/t121-b097d061.pak" dc/tex.pak
sha256sum "$B/t121-b097d061.pak" | cut -c1-16
T=$L/trees/origin/lane/castle-1015/port/dreamcast/tools
NT="/mnt/c/Game Dev/Emulators/re4-assets-private/t11-20261014/blackps2/newtex"
ls "$NT" | wc -l
cd /tmp && python3 "$S/c3r_gdix.py" --help > /dev/null 2>&1 || true
python3 "$S/c3r_t12d.py" "$T" "$B/t121-b097d061.pak" "$NT" "$B/t12d-rebuilt.pak"

set -euo pipefail
# c3r-emtex.sh: prepare_native_ui over every GC em/*.drs, etc/core.das and st1/st2 room .das (broad net for Codex-era loose textures)
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
T=$L/trees/origin/lane/castle-1015/port/dreamcast/tools
W=$L/extra/emtex; rm -rf "${W:?}"; mkdir -p "$W"
python3 "$S/c3r_gcx.py" "$ISO" "$W" | awk '{print $1}' | grep -E '^(em/(em|pl)[0-9a-f]+\.drs|etc/core\.das|st1/r1[0-9a-f]+\.das|st2/r2[0-9a-f]+\.das)$' > "$W/list.txt"
wc -l < "$W/list.txt"
mkdir -p "$W/src"
python3 "$S/c3r_gcx.py" "$ISO" "$W/src" $(cat "$W/list.txt") > /dev/null
while read -r f; do
  n=$(echo "$f" | tr '/.' '__'); echo "$f" > "$W/$n.m"
  ( cd /tmp && python3 "$T/prepare_native_ui.py" "$W/src" "$W/$n.m" "$W/tex-$n" > "$W/$n.log" 2>&1 ) || true
done < "$W/list.txt"
find "$W" -name '*.re4tex' | wc -l

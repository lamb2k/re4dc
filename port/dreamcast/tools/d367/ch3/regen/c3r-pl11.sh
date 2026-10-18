set -euo pipefail
# c3r-pl11.sh: castle pl11hot.sh + pl11c2.sh replay (bounded pl11-hot profile in the r117 AICA pl11 container)
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
T=$L/trees/origin/lane/castle-1015/port/dreamcast/tools
W=$L/extra/pl11hot; rm -rf "${W:?}"; mkdir -p "$W/src/em"
[ -e "$L/src/em/pl11.drs" ] || python3 "$S/c3r_gcx.py" "$ISO" "$L/src" em/pl11.drs > /dev/null
ln -sf "$L/src/em/pl11.drs" "$W/src/em/pl11.drs"; echo em/pl11.drs > "$W/m.txt"
printf '{"source_complete": false, "profile": "diagnostic: no hot set (every streamed clip loads on first use)", "union": {"source_arc_indices": []}}\n' > "$W/empty-hot.json"
cd "$T"
python3 prepare_native_ui.py "$W/src" "$W/m.txt" "$W/tex" > "$W/tex.log" 2>&1 || tail -2 "$W/tex.log"
for P in pl11-r11f pl11-hot; do
  nice python3 prepare_enemy_motions.py --source "$W/src/em/pl11.drs" --output "$W/$P" --textures "$W/tex" --hot-audit "$W/empty-hot.json" --diagnostic-incomplete-prefetch --bounded-profile $P > "$W/$P.log" 2>&1 || tail -3 "$W/$P.log"
done
H="/mnt/c/Game Dev/Emulators/re4-assets-private"
python3 - "$T" "$W" <<'P'
import sys, hashlib, glob
T, W = sys.argv[1:3]; sys.path[:0] = [T, T + '/d367']
import le_mirror as m
sha = lambda b: hashlib.sha256(b).hexdigest()
ref = open('/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018/discmatch/em/pl11.drs', 'rb').read()
r11f = open(W + '/pl11-r11f/pl11.arc', 'rb').read(); hot = open(W + '/pl11-hot/pl11.arc', 'rb').read()
for st in ['/mnt/c/Game Dev/Emulators/re4-assets-private/p2d3-ch22-20261012/aica/em/pl11.drs']:
    s = open(st, 'rb').read()
    print(st[-50:], 'r11f container == ch2 discmatch:', m.replace_native_payload(s, r11f) == ref)
    c = m.replace_native_payload(s, hot); open(W + '/pl11.drs', 'wb').write(c); print('hot', len(c), sha(c)[:16])
P

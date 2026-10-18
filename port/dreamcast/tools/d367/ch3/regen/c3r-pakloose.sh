set -euo pipefail
# c3r-pakloose.sh: VQ (vq_pak.py, pinned pvrtex) the 16-bit sources of the ch3found castle-pak-loose keys; split to loose files
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
C=origin/lane/castle-1015; T=$L/trees/$C/port/dreamcast/tools
W=$L/extra/pakloose; rm -rf "${W:?}"; mkdir -p "$W"
python3 -c "
import json;m=json.load(open('$S/srcmap.json'))
print('\n'.join(sorted(p.split('/')[-1][:-7] for p,v in m.items() if v['src'] and 'castle-pak-loose' in v['src'])))" > "$W/keys.txt"
wc -l < "$W/keys.txt"
H="/mnt/c/Game Dev/Emulators/re4-assets-private/harvest18-20261018"
( cd /tmp && python3 "$S/c3r_paksrc.py" "$T" "$W/src.pak" "$W/keys.txt" "$L/tex1" "$L/prepem" "$L/extra" /root/re4data/private/cxfix-replay-20261018/output "$H/castle-20261015/dc/tex" "$H/ch3found-20261016/dc/tex" )
( cd /tmp && nice python3 "$T/d367/vram/vq_pak.py" "$W/src.pak" "$W/vq.pak" "$W/work" $(cat "$W/src.pak.keys") > "$W/vq.log" 2>&1 ) || { tail -5 "$W/vq.log"; exit 1; }
tail -1 "$W/vq.log"
python3 - "$T" "$W" <<'P'
import sys, os
T, W = sys.argv[1:3]; sys.path[:0] = [T + '/d367/vram', T + '/d367', T]
from vq_pak import read_pak
p = read_pak(open(W + '/vq.pak', 'rb').read()); os.makedirs(W + '/loose', exist_ok=True)
for (c, f), b in p.items(): open('%s/loose/%08x-%08x.re4tex' % (W, c, f), 'wb').write(b)
print('loose', len(p))
P

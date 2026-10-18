set -euo pipefail
# c3r-c34b.sh: replay ch3found vq16-r204 (2026-10-16 22:14): tex-c34 -> src.pak -> vq_pak (24 kept keys) -> PSNR<29 reverted -> tex-c34b
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
TR=$L/trees/035c58e2; [ -d "$TR" ] || git -C "$L/git" worktree add -q --detach "$TR" 035c58e2
T=$TR/port/dreamcast/tools
W=$L/extra/vq-r204; mkdir -p "$W"; rm -rf "${W:?}/work"; mkdir -p "$W/work"
grep -v '^#' "$T/d367/vram/vq16-r204.txt" | cut -d' ' -f1 > "$W/keys.txt"
cd /tmp
python3 -I - "$T" "$L/extra/vq-c34/tex-c34.pak" "$W/src.pak" <<'PY'
import sys
T, a, b = sys.argv[1:4]; sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
import texpack
from vq_pak import read_pak
o, _ = texpack.build(read_pak(open(a, 'rb').read())); texpack.verify(o); open(b, 'wb').write(o)
PY
( cd "$T/d367" && python3 vram/vq_pak.py "$W/src.pak" "$W/vq.pak" "$W/work" $(cat "$W/keys.txt") 2>&1 | tail -1 | cut -c1-120 )
python3 -I - "$T" "$W" <<'PY'
import sys, json, pathlib, hashlib
T, W = sys.argv[1:3]; sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
import texpack
from vq_pak import read_pak
W = pathlib.Path(W); src = read_pak((W/'src.pak').read_bytes()); vqp = read_pak((W/'vq.pak').read_bytes())
r = json.load(open(W/'work/vq-report.json')); nm = lambda e: e.get('key') or e.get('name')
for e in r['images']:
    if e['psnr_db'] < 29.0:
        kk = tuple(int(x, 16) for x in nm(e).split('-')); vqp[kk] = src[kk]
out, _ = texpack.build(vqp); texpack.verify(out); (W/'tex-c34b.pak').write_bytes(out)
print('tex-c34b', len(out), hashlib.sha256(out).hexdigest()[:16])
PY

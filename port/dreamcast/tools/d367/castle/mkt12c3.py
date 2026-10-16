"""castle-t12c = castle-t12b + (1) dc/tex.pak: test 12's tex-t12d.pak + 124 castle 16-bit textures as full-codebook VQ
(PSNR >= 29 dB, the vram12 D5 rule; 58 castle loose keys moved into the pak), (2) dc/resident.bin: r101 + castle 3-1
first-sight lists (r200 r201 r202 r203 r204 r207 r208), (3) em/pl11.drs: the ch22 lane's bounded pl11 (MRAM 384,064
instead of 1,069,792; audio bytes = r117 AICA pl11; needs MOTION_BOUNDED_R11F=1, in the cxt12c recipe), (4) the 5
material-pair packages r201/r208 asked for (pairs_from_log.py)."""
import json, hashlib
from pathlib import Path
L = Path('/root/probe/lanes-20261015/castle')
src = L / 'fix/castle-t12b.json'; out = L / 'fix/castle-t12c.json'; assert not out.exists()
d = json.loads(src.read_text()); r = d['replace']
r['dc/tex.pak'] = str(L / 'vq-c31/tex-c31vq.pak')
r['dc/resident.bin'] = str(L / 'vq-c31/resident.bin')
r['em/pl11.drs'] = '/root/probe/codex-em35-cap128-20261013/motion-assets/em/pl11.drs'
n = 0
for f in sorted((L / 'pairs-c31').glob('*.re4tex')):
    k = 'dc/tex/%s/%s' % (f.name[0], f.name); assert k not in r, k; r[k] = str(f); n += 1
# loose keys now packed: drop the loose copies the pak supersedes (pak wins at runtime; keep the disc lean)
moved = [k for k in (L / 'vq-c31/vq-c31-final-keys.txt').read_text().split() if 'dc/tex/%s/%s.re4tex' % (k[0], k) in r]
for k in moved: del r['dc/tex/%s/%s.re4tex' % (k[0], k)]
d['remove'] = sorted(set(d.get('remove', [])) - set(r))
d.setdefault('provenance', {})['castle_t12c'] = dict(base=str(src), base_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    pak_sha256=hashlib.sha256((L / 'vq-c31/tex-c31vq.pak').read_bytes()).hexdigest(), pairs=n, loose_moved_to_pak=len(moved))
out.write_text(json.dumps(d, indent=1, sort_keys=True) + '\n')
print(out, hashlib.sha256(out.read_bytes()).hexdigest(), 'pairs', n, 'moved', len(moved))

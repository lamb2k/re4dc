"""hide_check.py <pkg dir> <run-output>: every runtime cull (ENEMYVIS hide line, ENEMY_VIS_DEBUG=1) checked by the
back-face-aware oracle on a dense 7x7x7 grid over the culled box itself. Any point visible = BUG."""
import re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'vis'))
import occ_eval as oe

T, F = oe.load_tris_cull(sys.argv[1])
text = Path(sys.argv[2]).read_text(errors='replace')
rows = re.findall(r'ENEMYVIS hide f=(\d+) occ=(\d+) eye=(-?\d+),(-?\d+),(-?\d+) lo=(-?\d+),(-?\d+),(-?\d+) hi=(-?\d+),(-?\d+),(-?\d+)', text)
g = np.linspace(0, 1, 7)
bugs = 0
frames = set()
for r in rows:
    v = [int(x) for x in r]
    E = np.array(v[2:5], float); lo = np.array(v[5:8], float); hi = np.array(v[8:11], float)
    pts = np.array([lo + (hi - lo) * np.array([a, b, c]) for a in g for b in g for c in g])
    if not oe.blocked_cull(E, pts, T, F).all():
        bugs += 1
        print('BUG', r)
    frames.add(v[0])
print(dict(culls=len(rows), frames_with_culls=len(frames), bugs=bugs))

#!/bin/bash
# priv_t17.sh (WSL): terrain-only world level 5 for r102 + r108 + r10a (test 17), locked borders, into
# re4-assets-private/world-terrain-wt17-20261016 (replaces the unlocked first copy, never used by a build).
set -e
S=/root/probe/worldtest16-20261016/terrainL; P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-terrain-wt17-20261016"
rm -rf "$P"; mkdir -p "$P"
for r in r102 r108 r10a; do mkdir -p "$P/$r"; cp $S/$r/out/ps2-wv5.re4mesh $S/$r/class.json $S/$r/L2.json $S/$r/job.log "$P/$r/"; done
cp "/mnt/c/Game Dev/Emulators/worldtest-20261016/price-terrainL.json" "$P/price-MODELLED.json"
cat > "$P/RECIPE.txt" <<'R'
r102 + r108 + r10a world level 5, test 17 (lane/worldtest16 B, 2026-10-16): terrain-only reduction of the shipping PS2
world (level 0 unchanged, /root/probe/world16-20261016/rooms/<room>/src.*): ps2_world_vert_ladder.py --mode terrain
--keep-walk-mm 1500 --keep-pieces --lock-borders --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 --uv-per-m 0.05
--per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --baked 0 --protect-last 0 (tool: lane/worldtest16
3978474f; script worldtest16/terrainL.sh). Only parts classed terrain/rock/cliff move (class.json per room).
--lock-borders keeps every open-border vertex: the unlocked first run opened a seam on the r102 merchant-cave wall.
No strip groups (these rooms ship none). WORLD_VERT=1 WORLD_VERT_LEVEL=5 (recipe default) loads ps2-wv5.re4mesh.
Kept share of corners: r102 0.762, r108 0.964, r10a 0.967.
MODELLED, not measured (price-MODELLED.json; 1.1 ms per 1k on-screen world TA vertices): world p90 r102 -4.23 ms
(10.18 -> 5.95), r108 -0.87 (12.91 -> 12.04), r10a -0.47 (14.58 -> 14.11).
R
cd "$P" && sha256sum RECIPE.txt price-MODELLED.json */* > /tmp/s && mv /tmp/s SHA256SUMS && cut -c1-16,65- SHA256SUMS
python3 - <<'PY'
p = '/root/probe/worldtest16-20261016/land17/port/dreamcast/tools/d367/test11/t11-fix.py'
s = open(p, encoding='utf-8').read()
a = """# Test 17 terrain-only world level 5 for r108 + r10a (lane/worldtest16 B, user plan 10-16: terrain/rock only, no structural
# cuts; coordinator 10-16: land r108 -1.01 and r10a -0.56 ms MODELLED). Level 0 is unchanged; WORLD_VERT_LEVEL=5 loads these.
# re4-assets-private/world-terrain-wt17-20261016 (SHA256SUMS, RECIPE.txt, class.json per room).
WT17TD = os.environ.get('WT17TD', PRIV + '/world-terrain-wt17-20261016')
DATA['wt17terr'] = {'dc/native/' + _r + '/ps2-wv5.re4mesh': WT17TD + '/' + _r + '/ps2-wv5.re4mesh' for _r in ('r108', 'r10a')}
"""
b = """# Test 17 terrain-only world level 5 for r102 + r108 + r10a (lane/worldtest16 B, user plan 10-16: terrain/rock only, no
# structural cuts; coordinator 10-16: r108 and r10a, r102 GO; MODELLED world p90 -4.23 / -0.87 / -0.47 ms). Only terrain
# parts move, open borders locked (no seams). Level 0 is unchanged; WORLD_VERT_LEVEL=5 loads these.
# re4-assets-private/world-terrain-wt17-20261016 (SHA256SUMS, RECIPE.txt, class.json per room).
WT17TD = os.environ.get('WT17TD', PRIV + '/world-terrain-wt17-20261016')
DATA['wt17terr'] = {'dc/native/' + _r + '/ps2-wv5.re4mesh': WT17TD + '/' + _r + '/ps2-wv5.re4mesh' for _r in ('r102', 'r108', 'r10a')}
"""
assert s.count(a) == 1
open(p, 'w', encoding='utf-8').write(s.replace(a, b)); print('t11-fix ok')
PY

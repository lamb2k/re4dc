"""updroute.py: fill ISLAND-ROUTE-20261016.md's first-pass column with the round 2 results (Flycast, 60 s)."""
import re, pathlib
p = pathlib.Path(r'C:\Game Dev\Emulators\ISLAND-ROUTE-20261016.md')
t = p.read_text(encoding='utf-8')
R = {
 'r305': 'ENTRY OK; FAIL em1e GC model. Peak 4, 7 kills',
 'r306': 'ENTRY OK (no em36 yet: appears after r309). Stream 0:26 was missing: fixed',
 'r307': 'ENTRY OK; **em36.drs not on disc** (regenerator archive not prepared)',
 'r308': 'ENTRY OK; **em36.drs not on disc**',
 'r30b': 'ENTRY OK; FAIL em1f GC model. Peak 4, 4 kills, room waves not reached in the window',
 'r30c': 'ENTRY OK. Peak 2, 2 kills (s00 cell event not reached)',
 'r30e': 'ENTRY OK. Peak 6, 6 kills, held 0',
 'r309': 'ENTRY OK; **em36.drs not on disc** (appearance event cannot spawn it)',
 'r30a': 'ENTRY OK. BGM0 #7 was missing: fixed',
 'r310': 'ENTRY OK; **em36.drs not on disc**',
 'r311': '**FAIL tex_check**: 1 key missing (5ec91893-07ced5eb 64x64). Peak 3. BGM0 #14 + stream 0:39: fixed',
 'r312': 'ENTRY OK',
 'r30f': 'ENTRY OK; **heap 4 min free 290,272 B** (tightest). Peak 6, held 0, 6 kills (soldiers enter at room frame ~800)',
 'r315': 'ENTRY OK; FAIL em1e GC model (sound run). BGM0 #5 fixed',
 'r316': 'ENTRY OK (post-s00 warp). Peak 5, 7 kills',
 'r317': 'ENTRY OK; STRICT with the round-10 hooks (1,516 ticks)',
 'r318': 'ENTRY OK',
 'r31a': 'ENTRY OK',
 'r31b': 'ENTRY OK (em32 not loaded in the window); STRICT with hooks',
 'r31d': '**CAP 6 PASS**: 9 at entry, 3 held, released one per kill, 9/9 killed, 0 left. FAIL em1e GC model; thrash guard 13',
 'r31c': 'ENTRY OK; **em39 / em3a not on disc** (Krauser archives not staged); STRICT with hooks',
 'r320': 'ENTRY OK (soldiers not sent in the window); STRICT with hooks',
 'r321': 'ENTRY OK; STRICT with hooks',
 'r325': 'ENTRY OK; STRICT with hooks',
 'r326': 'ENTRY OK; **em36.drs not on disc**',
 'r327': '**CAP 6 PASS at entry** (PS2 first table 9: 3 deferred, all released); 10 kills; later waves need PS2 area 0x1C (not reached); FAIL em1d GC model, tex_check; KOS min 61,824',
 'r329': 'ENTRY OK (post-s00 warp); **thrash guard 55**, VRAM free 897,152',
 'r330': 'ENTRY OK; FAIL em1f GC model. Peak 4, 4/4 killed; STRICT with hooks',
}
n = 0
lines = t.split('\n')
for i, l in enumerate(lines):
    m = re.match(r'\| (r3[0-9a-f]{2}) \|', l)
    if m and m.group(1) in R and l.rstrip().endswith('| UNPROVEN |'):
        lines[i] = l.rstrip()[:-len('UNPROVEN |')] + R[m.group(1)] + ' |'; n += 1
t = '\n'.join(lines)
old = "- 30 route rooms 5-1..5-4: 5 PASS on first pass (r300, r301, r303, r304, r30d), 25 UNPROVEN, 0 FAIL at entry."
assert old in t
t = t.replace(old, "- 33 route rooms 5-1..5-4 (round 2, 2026-10-16 evening): **all 33 enter with no halt** on cx5cmW (Flycast, 60 s).\n"
  "  Round 1: r300 r301 r303 r304 r30d. Round 2: the other 28 (and r31d / r327 cap runs, 10 sound runs on cx5vmW).\n"
  "  Gate FAILs left: GC soldier models (r305 r30b r31d r315 r327 r330, ps2cast), tex_check r311 / r327, em36 / em39 / em3a\n"
  "  archives not on the disc. Details per room: CH5-FOUNDATIONS-20261016.md round 2.")
p.write_text(t, encoding='utf-8')
print('rows updated', n)

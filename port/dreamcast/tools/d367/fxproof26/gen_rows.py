"""gen_rows.py: fxproof26 drop-proof rows for the 210 unproven FX_PS2_NONE_CUT rows + the EFM_PS2_CUT knob."""
import csv, collections
D = '/root/work/lanes/fxproof26/'
L = '/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/effects-tex/KEYS.tsv'
keys = collections.defaultdict(list)
for r in list(csv.reader(open(L), delimiter='\t'))[1:]:
    keys[r[0]].append((r[1], r[2]))
near = {}
for l in open(D + 'match-q.tsv'):
    f = l.rstrip('\n').split('\t')
    b = f[3].split()
    if len(b) < 2:
        continue
    near[f[0]] = (b[0], b[1].split('@')[0] + '@' + b[1].split('@')[1], b[3] if len(b) > 3 else '')
SCAN = 'fxproof26 content match over all 22177 PS2 PSMT4/PSMT8 pictures in BIO4DAT.AFS (every .dat entry incl. ETM etc effect files, Core, em, wep, .tpl/.eff; NCC distance, same picture <=8, none >=25)'
EV = {
    '0xd1': 'correct cut: PS2 deleted the glass-shard records. GC et00.eff EST0/1/3/6/7 draw 0xd1 (19/19/20/18/18 records); PS2 r100.dat ETM(dat#9) et00.eff +0x1640 has the same sets with 10/11/11/11/11 records and no Tex_id 0xd1, tex table [0x2,0x14] (r101/r105/r107 dat#10 same member). Picture exists only in PS2 r20c.dat EFF(dat#7) 0xd1 (castle), d=%s; no PS2 etc eff or Core holds it',
    '0xea': 'correct cut: PS2 r107.dat EFF(dat#7) tex table [0xfe] only (GC [0xcc,0xd0,0xea,0xfe]); no PS2 r107 record uses 0xea. Picture exists only in PS2 r30c.dat EFF(dat#7) 0xea (stage 3), d=%s',
    '0xab': 'correct cut: PS2 draws no r11b lightning. GC r11b EFF #7 EST6/7/8/9 (9/15/9/14 records, Tex_id 0xaa/0xab + efm 0xfc) are the only users; PS2 r11b.dat EFF(dat#7) has no EST6-9 and tex table [0xc0,0xc4,0xc5,0xef,0xf2,0xfe]. No PS2 picture is a bolt: nearest %s %s (0xab frames d 18.0-36.8, median 26.3, best = a Core fire frame by eye; 0xaa nearest d=37.4)',
    '0x70': 'correct cut: PS2 r225.dat EFF(dat#7) tex table [0x29] only; GC SST1 (61 records, 0x70/0x71) is gone. No PS2 picture matches: nearest %s %s',
    '0x71': 'correct cut: PS2 r225.dat EFF(dat#7) tex table [0x29] only; GC SST1 (61 records, 0x70/0x71) is gone. No PS2 picture matches: nearest %s %s',
}
out = ['# --- fxproof26 block (lane fxproof26 2026-10-26; content proof of the FX_PS2_NONE_CUT "unproven" rows + EFM_PS2_CUT). %s.' % SCAN,
       '# Evidence tools + raw results: tools/d367/fxproof26/ (match-q.tsv, efminv.txt, efmlist.txt, estrecs.txt).',
       '# WRONG cuts fixed by data set fxp26 (fx_cross_room.py PAIRS + regenerated fx_none_cut.inc / _pack.inc): these rows leave the table',
       '#   212e55c1-ad1637c7 (r100 r101 r102 r105 r107 any): window-break glass crack, GC ETM et00.eff/et2c.eff 0x14 = PS2 r100.dat ETM(dat#9) et00.eff 0x14 TPL @0x3852c0 (et00.eff+0x2180), d=8.2; PS2 EST5 still draws 0x14',
       '#   fef62a48-df2e5199 (r206 any): castle candle glow, GC r206 EFF #7 0xe6 = PS2 r50c.dat EFF(dat#7) 0xe6 TPL @0x1ba5e0, d=4.1 (PS2 r206 SST1-5 draw it as Core.dat EFF#1 0xe9 @0xa7de0, d=4.2)']
FIXED = {'212e55c1-ad1637c7', 'fef62a48-df2e5199'}
for line in open(D + 'dp.tsv'):
    f = line.rstrip('\n').split('\t')
    if len(f) < 5 or f[0] != 'fxnone' or f[3] != 'unproven':
        continue
    k = f[2]
    if k in FIXED:
        continue
    gid = keys[k][0][1].rsplit(':', 1)[1]
    d, loc, idv = near[k]
    tmpl = EV[gid]
    ev = tmpl % ((d,) if tmpl.count('%s') == 1 else (loc, 'd=' + d))
    gc = sorted(set(g for _, g in keys[k]))
    out.append('fxnone\t%s\t%s\tdrop-ok\t%s; GC use %s' % (f[1], k, ev, ' '.join(gc)))
EFM = ('drop-ok\tfxproof26 geometry proof (tools/d367/fxproof26/efminv.py: pose-invariant triangle edge keys vs all 849 PS2 efm models '
       'in every room EFF, ETM etc eff and Core; same model scores 1.000): r101 0x02 (141 tris) best 0.071; r106 0x5a (78) 0.038; '
       'r10a/r10b 0x7b (702) 0.010; r10b 0x7c (12) 0.000; r119 0x14/0x16/0x17 (52/52/90) best 0.019/0.019/0.011 and vs PS2-only '
       'r119 0xc9 (768 tris) below 0.02 (0xc9 is not a renumbered copy); core 0x3e (52) 0.077. r11a et10 0x0f: the model exists on '
       'PS2 (r109/r10d/r10e/r20d ETM et10.eff 0xf, score 1.000) but PS2 r11a.dat ETM drops the et10/et14 members (GC 12 members, '
       'PS2 7), so the PS2 does not place it in r11a: correct cut')
out.append('knob\t-\tEFM_PS2_CUT=1\t' + EFM)
open(D + 'fxproof26-rows.tsv', 'w').write('\n'.join(out) + '\n')
print(len(out) - 6, 'fxnone rows')

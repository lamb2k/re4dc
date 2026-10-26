import re, sys
sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '../rr'))
import drop_proofs as dp
from pathlib import Path
L = '/root/work/lanes/purge-audit26/'
import os; ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../..')) + '/'
tree = Path(ROOT)
kn = {'PS2_ETS_MATCH': '2', 'FX_PS2_NONE_CUT': '1'}
for k in dp.DROP_KNOBS:
    kn.setdefault(k, '1')
kn['FX_LEVEL'] = '3'; kn['FX_SPRITE_TRIM'] = '2'; kn['FOLIAGE_TRIM'] = '2'; kn['GANADO_ATLAS_DROP'] = '3'
ev = {}
for line in open(ROOT + 'port/dreamcast/tools/d367/purge-audit26/ets-evidence-20261026.txt'):
    m = re.match(r'(r[0-9a-f]{3}) (et[0-9a-f]{4}#\d+) pos (\([^)]*\)) \| GC ETS rec (\S+) \| PS2 SMD\(dat#4\) (.*?) \| PS2 EFF fx (.*)$', line.strip())
    if m:
        ev[(m.group(1), m.group(2))] = m.groups()
fx = {}
for line in open(ROOT + 'port/dreamcast/tools/d367/purge-audit26/fxmatch-fix-r100-props26.txt'):
    f = line.split()
    if 'skipped' in line or len(f) < 6:
        continue
    fx.setdefault(f[2], []).append((f[0], f[1], float(f[4]), f[5]))
rows = ['# DROP-PROOF rows (tools/d367/rr/drop_proofs.py; lane purge-audit26 2026-10-26). <kind>\t<room>\t<item>\t<verdict>\t<evidence>.',
        '# PS2 = Resident Evil 4 (USA) PS2 ISO, BIO4DAT.AFS; "dat#N" = entry N of the room .dat; offsets are inside that entry.',
        '# Torch evidence: purge-audit26 p9 (GC gcarc ETS vs PS2 SMD placements + PS2 room EFF EST/SST records within 500 units).',
        '# No PS2 room ETS (171 rooms) places et1400 / et1c00 / et3800; et0c00 only r531; PS2 ELF still has Et14_init etc.']
for d in dp.drops(tree, kn):
    kind, room, item = d
    verdict, e = 'unproven', ''
    if kind == 'ets':
        g = ev.get((room, item))
        ident = item[:6]
        if room == 'r11f' and ident == 'et0000':
            verdict, e = 'delegated:windows26', 'r11f et0000 pane: PS2 draws the window with et0001 (windows26 finding)'
        elif g is None:
            verdict, e = 'unproven', 'not found in GC ETS'
        else:
            _, _, pos, gcrec, smd, eff = g
            if eff.startswith('[') and ident in ('et1400', 'et0c00', 'et3800', 'et1c00'):
                verdict = 'fixed:PS2_FIRE_SST=1'
                e = ('WRONG drop. PS2 %s.dat EFF(dat#7) %s draws the flame (room SST set, started by EAR area); body: %s. '
                     'GC ETS %s pos %s. Restored by data set pfire26 (that SST set in ETM et14.eff, pfire26.py) + PS2_FIRE_SST'
                     % (room, eff.strip("[]").replace("'", '').split(',')[0], 'PS2 scenario SMD(dat#4) ' + smd
                        if smd != 'NONE' else 'not located in PS2 scenario SMD (unproven)', gcrec, pos))
                _ss = re.search(r'SST(\d+)\.', e)
                if _ss and (room, int(_ss.group(1))) in (('r10c', 13), ('r10c', 14), ('r10f', 8)):
                    e += ('. APPROXIMATION (accepted under PS2_FIRE_SST, coordinator 10-26): %s starts at room entry; '
                          'its PS2 area is missing from the GC area table' % ('SST' + _ss.group(1)))
            elif eff == 'NONE' and smd != 'NONE':
                verdict = 'drop-ok'
                e = 'PS2 %s.dat SMD(dat#4) %s draws it as world scenery (our PS2 world); no PS2 EFF record within 500 units; PS2 ETS has no %s' % (room, smd, ident)
            elif eff == 'NONE' and smd == 'NONE':
                verdict = 'drop-ok'
                e = 'PS2 %s.dat: no ETS %s, no scenario SMD placement at %s, no EFF(dat#7) EST/SST record within 500 units' % (room, ident, pos)
    elif kind == 'etmempty':
        verdict, e = 'delegated:windows26', 'window pane %s emptied by props24p; windows26 owns et0000/et2500' % item
    elif kind == 'fxnone':
        hits = fx.get(item, [])
        mine = [h for h in hits if h[0] == room] if room != 'any' else hits
        if mine:
            dmin = min(h[2] for h in mine)
            h = min(mine, key=lambda x: x[2])
            if dmin >= 28:
                verdict = 'drop-ok'
                e = ('no PS2 picture matches anywhere in the ISO: nearest %s d=%.1f (same picture <=12.2; fix-r100-props26 fxmatch '
                     'over every PS2 room/Core/em EFF); GC use %s' % (h[3], dmin, h[1]))
            else:
                verdict = 'wrong'
                e = 'PS2 has the same picture: %s d=%.1f' % (h[3], dmin)
        else:
            verdict = 'unproven'
            e = 'fx_none_cut.py claim only (ps2lib INDEX NONE in every library row); no picture or record match run'
    elif kind == 'knob':
        k = item.split('=')[0]
        if k in ('FX_LEVEL', 'FX_TRIM', 'HAZE_SPRITE_CUT', 'ESP_CUT_EARLY', 'FX_SPRITE_TRIM', 'FX_STRIP21', 'FOLIAGE_TRIM'):
            verdict, e = 'speed-cut', 'deliberate speed / look cut (user calls: fx-trim23 "Essential only", nohaze16, mist16); not a PS2-absence claim'
        elif k == 'PS2_ETS_MATCH':
            verdict, e = 'drop-ok', 'covered row by row by the ets rows of this table'
        elif k == 'FX_PS2_NONE_CUT':
            verdict, e = 'drop-ok', 'covered key by key by the fxnone rows of this table'
        elif k in ('GANADO_ATLAS_DROP', 'PRELOAD_SKIP_GCIDLE', 'GC_STUB_SKIP'):
            verdict, e = 'drop-ok', 'skips GameCube data that is never drawn (replaced by PS2 data or degenerate parts); no PS2-drawn content dropped'
        elif k == 'EFM_PS2_CUT':
            verdict, e = 'unproven', ('pre-T22 (items 2026-10-14). kEfmPs2Cut ids matched by id only; r119: GC efm 0x14/0x16/0x17 absent '
                                      'from PS2 r119.dat EFF(dat#7) efm table, which adds 0xc9 (possible replacement, not checked)')
    rows.append('\t'.join([kind, room, item, verdict, e]))
# all knob rows so the table covers knobs that are off in a given recipe too
out = Path(ROOT + 'port/dreamcast/tools/d367/rr/drop-proofs.tsv')
out.write_text('\n'.join(rows) + '\n')
import collections
print(collections.Counter(r.split('\t')[3] for r in rows if not r.startswith('#')))

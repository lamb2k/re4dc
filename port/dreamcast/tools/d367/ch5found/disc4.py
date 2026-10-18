"""disc4.py: per-disc sizes for the three-disc layout from real file lists (MB = 10^6 B).
Sources: t15rc.manifest.json (test 15 RC disc, measured), castle.manifest.json (ch3found castle test disc, measured),
island run manifests (ch5found16, measured), sizes.out numbers (st3 lane outputs, measured) and MODELLED items."""
import json, re, sys, glob, collections
MB = 1e6
t15 = {k: v['size'] for k, v in json.load(open('t15rc.manifest.json')).items()}
cas = {k: v['size'] for k, v in json.load(open('castle.manifest.json')).items()}
isl = {}
for f in glob.glob(sys.argv[1]):
    for k, v in json.load(open(f)).items(): isl[k] = v['size']
DEBUG = {'dc/warp.txt', 'dc/codec_ready.txt', 'dc/diagnostic-scope.txt', 'dc/model-diagnostic.flag', 'dc/padscript.txt'}
def stage(k):
    m = re.match(r'(?:st|St)([1-4])/', k) or re.match(r'rel/st([1-4])_', k)
    if m: return int(m.group(1))
    m = re.match(r'(?:evd|event|dc/movie|dc/native)/(?:.*/)?r([1-3])[0-9a-f]{2}', k)
    return int(m.group(1)) if m else 0
def em(k):
    m = re.match(r'em/(\w+?)\.(drs|das)$', k); return m.group(1) if m else None
COMMON_EM = lambda e: e.startswith('wep') or e in ('pl00', 'pl08', 'pl11', 'em18', 'em23')
COSTUME = lambda e: re.match(r'pl(0[1-79a-e]|1[0245])$', e)   # costume / other-character player archives
def shared(files):
    """files every disc carries (program, core, sub screen, fonts, bgm minus the stream file, Leon / Ashley / weapons,
    merchant, crows, motion keys, low textures), from a manifest."""
    out = collections.Counter()
    for k, s in files.items():
        if k in DEBUG or stage(k) or k in ('dc/tex.pak', 'dc/resident.bin', 'bgm/aica_str.dat'): continue
        if k.startswith('dc/tex/'): continue
        e = em(k)
        if e is not None:
            if COMMON_EM(e): out['em common (Leon, Ashley, weapons, merchant, crows)'] += s
            elif COSTUME(e): out['em costumes / other players'] += s
            continue
        if re.match(r'dc/\w+\.ovl$', k): out['program overlays'] += s; continue
        out[k.split('/')[0] if not k.startswith('dc/') else '/'.join(k.split('/')[:2])] += s
    return out
sh = shared(t15)
SH = sum(sh.values())
def rows_of(files, pred):
    return sum(s for k, s in files.items() if pred(k))
loose_t15 = rows_of(t15, lambda k: k.startswith('dc/tex/'))
loose_cas = rows_of(cas, lambda k: k.startswith('dc/tex/') and k not in t15)
loose_isl = rows_of(isl, lambda k: k.startswith('dc/tex/') and k not in t15 and k not in cas)
em_t15 = rows_of(t15, lambda k: em(k) and not COMMON_EM(em(k)) and not COSTUME(em(k)))
em_cas_new = rows_of(cas, lambda k: em(k) and k not in t15 and not COMMON_EM(em(k)) and not COSTUME(em(k)))
VILLAGE_IN_CAS = ('em16', 'em35')          # chapter 2-3 enemies that arrived with the ch2 lane (r11d, r11f)
em_ch2 = rows_of(cas, lambda k: em(k) in VILLAGE_IN_CAS and k not in t15)
CASTLE_EM = ('em11', 'em12', 'em14', 'em19', 'em1a', 'em1b', 'em25', 'em2d', 'em3c', 'em3b', 'em13', 'em15')
em_castle = rows_of(cas, lambda k: em(k) in CASTLE_EM)
st1 = rows_of(cas, lambda k: stage(k) == 1)                 # test 15 + chapter 2-2 / 2-3 rooms
r200 = rows_of(cas, lambda k: stage(k) == 2 and 'r200' in k) + cas.get('rel/st2_0.rel', 0)
st2 = rows_of(cas, lambda k: stage(k) == 2 and 'r22c' not in k)
isl_rooms = rows_of(isl, lambda k: stage(k) == 3 and not k.startswith('dc/movie/'))
d = {}
d[1] = [('shared (program, core, ss, font, bgm banks, common em, costumes)', SH, 'measured t15 RC'),
        ('stage 1 rooms + movies + events, ch1-1..2-3', st1, 'measured castle test disc (t15 + ch2 lane)'),
        ('r200 (2-3 end) + st2_0', r200, 'measured'),
        ('village enemies', em_t15 + em_ch2, 'measured'),
        ('tex.pak (village)', t15['dc/tex.pak'], 'measured t15 RC'),
        ('loose textures (test 15)', loose_t15, 'measured; chapter 2-2/2-3 loose keys are counted on disc 2 (upper bound)'),
        ('aica_str.dat (ch2 file, 53 entries)', cas['bgm/aica_str.dat'], 'measured castle test disc'),
        ('resident.bin', cas['dc/resident.bin'], 'measured')]
CH4 = 340e6
d[2] = [('shared', SH, 'measured t15 RC'),
        ('castle chapter 3 rooms + movies + events (incl. r200, st2 modules)', st2, 'measured castle test disc'),
        ('castle chapter 4 rooms + movies (not converted yet)', CH4, 'MODELLED (CASTLE-ROUTE estimate)'),
        ('castle enemies (chapter 3 set)', em_castle, 'measured; chapter 4 bosses inside the 340 MB'),
        ('tex.pak (castle; today test 15 pak + castle keys loose)', t15['dc/tex.pak'], 'measured size of the pak it ships with today'),
        ('loose textures (castle + chapter 2 keys)', loose_cas + loose_t15, 'measured upper bound'),
        ('aica_str.dat (ch3 file)', cas['bgm/aica_str.dat'], 'measured')]
ISL_MOVIES = 181044664 - (5.36e6 + 32.28e6)       # 17 converted movies minus r331 / r332 (sizes.out)
FINAL = (0.60 + 2.62 + 0.87 + 0.80 + 5.36) + (1.91 + 5.41 + 0.86 + 1.04 + 32.28) + (1.11 + 4.07 + 0.87 + 0.87)
ISL_EM = (9602496 + 9439360 + 8957600) + (6251168 + 6799072 + 5085664 + 590176 + 359104 + 337472 + 1336128)
d[3] = [('shared', SH, 'measured t15 RC'),
        ('island rooms r300..r330 (arc/dar, worlds, native, evd)', isl_rooms, 'measured island run discs (33 rooms)'),
        ('island movies (15 of 17; r331/r332 below)', ISL_MOVIES, 'measured converted .seq'),
        ('final chapter r331..r333 (rooms + 2 movies)', FINAL * MB, 'measured st3 lane outputs (stress16b scope)'),
        ('r317 QTE movie set (not converted)', 25e6, 'MODELLED from GC evd sizes'),
        ('r22c + st2_4 (shooting range)', 3e6, 'MODELLED (GC das size, not converted)'),
        ('island enemies (em1d/e/f prepared, em36 em32 em39 em3a em3d em3b em25)', ISL_EM, 'measured archives'),
        ('Saddler em31 + em0e', 5.2e6 + 1e6, 'GC sizes (stress16b)'),
        ('tex.pak (island: st3 VQ pak)', 113066366 + 2048 * 4539 // 1, 'measured key bytes + index'),
        ('loose textures (island fixtures beyond test 15 / castle)', loose_isl, 'measured upper bound'),
        ('aica_str.dat (ch5 file, 37 entries)', float(sys.argv[2]) if len(sys.argv) > 2 else 30e6, 'measured' if len(sys.argv) > 2 else 'MODELLED')]
CAP = 504150 * 2048
for n in (1, 2, 3):
    tot = sum(r[1] for r in d[n])
    print('DISC %d: %.0f MB of %.0f MB (%.0f%%)' % (n, tot / MB, CAP / MB, 100 * tot / CAP))
    for name, s, src in d[n]: print('   %-72s %7.1f  %s' % (name, s / MB, src))
print('shared detail:', {k: round(v / MB, 1) for k, v in sh.most_common()})

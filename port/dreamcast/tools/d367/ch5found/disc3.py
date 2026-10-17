"""disc3.py: per-disc sizes for the three-disc layout (user decision 2026-10-16, option B) from real staged-disc file lists.
Inputs (payload-manifest.json of Flycast runs, {path: {size, sha256}}):
  t15rc.manifest.json   test 15 release candidate disc (chapters 1-1..2-1)
  castle.manifest.json  ch3found castle test disc (test 15 + chapter 2-2/2-3 + castle chapter 3)
  island manifests      every ch5found16 island run (base + one room's island files)
Rules: a file belongs to the disc(s) whose rooms use it; shared files (program, core, ss, font, bgm, Leon / Ashley /
weapons, merchant) are duplicated on every disc. Prints MB per disc and per part, measured vs modelled."""
import json, re, sys, glob, collections
MB = 1e6
t15 = {k: v['size'] for k, v in json.load(open('t15rc.manifest.json')).items()}
cas = {k: v['size'] for k, v in json.load(open('castle.manifest.json')).items()}
isl = {}
for p in sys.argv[1:]:
    for f in glob.glob(p):
        for k, v in json.load(open(f)).items(): isl[k] = v['size']
DEBUG = {'dc/warp.txt', 'dc/codec_ready.txt', 'dc/diagnostic-scope.txt', 'dc/model-diagnostic.flag', 'dc/padscript.txt'}
def stage(k):
    m = re.match(r'(?:st|St)([1-4])/', k) or re.match(r'rel/st([1-4])_', k)
    if m: return int(m.group(1))
    m = re.match(r'(?:evd|event|dc/movie|dc/native)/(?:.*/)?r([1-3])[0-9a-f]{2}', k)
    return int(m.group(1)) if m else 0
EM_CASTLE = {'em14', 'em19', 'em1a', 'em1b', 'em25', 'em2d', 'em3c', 'em16x', 'em38', 'em2c', 'em13x'}
EM_VILLAGE = {'em12', 'em13', 'em15', 'em16', 'em17', 'em21', 'em24', 'em26', 'em27', 'em28', 'em29', 'em2a', 'em2b',
              'em2e', 'em2f', 'em35', 'em22', 'pl0f'}
EM_ISLAND = {'em1d', 'em1e', 'em1f', 'em36', 'em32', 'em39', 'em3a', 'em3d', 'em3b', 'em25', 'em23', 'em11', 'em31', 'em0e'}
EM_SHARED = {'em18', 'em23', 'em11'}   # merchant, crows (village / castle r20a / island r30a), em11 (village r117, castle, r328)
def emid(k):
    m = re.match(r'em/(\w+?)\.(drs|das)$', k) or re.match(r'dc/(\w+)\.ovl$', k)
    return m.group(1) if m else None
def disc_of(k, src):
    """set of discs (1, 2, 3) a file of manifest `src` goes to; empty = not on any (debug / other chapter)."""
    if k in DEBUG: return set()
    s = stage(k)
    if s == 1: return {1}
    if s == 2:
        if 'r200' in k or k == 'rel/st2_0.rel': return {1, 2}   # r200: 2-3 end (disc 1) and 3-1 (disc 2); st2_0 its module
        if 'r22c' in k or k == 'rel/st2_4.rel': return {3}       # r22c (shooting range) as on GC disc 2
        return {2}
    if s == 3: return {3}
    if s == 4: return set()                                       # St4 (not in scope)
    e = emid(k)
    if e and k.startswith('em/'):
        if e.startswith(('pl', 'wep')) and e != 'pl0f': return {1, 2, 3}
        out = set()
        if e in EM_VILLAGE or e in EM_SHARED: out.add(1)
        if e in EM_CASTLE or e in EM_SHARED or e in ('em11', 'em12', 'em18', 'em23'): out.add(2)
        if e in EM_ISLAND or e in EM_SHARED: out.add(3)
        return out or {1}
    return {1, 2, 3}
discs = {1: collections.Counter(), 2: collections.Counter(), 3: collections.Counter()}
seen = {1: set(), 2: set(), 3: set()}
def part(k):
    if k.startswith('dc/tex/'): return 'dc/tex (loose)'
    if k.startswith('dc/'): return '/'.join(k.split('/')[:2]) if '/' in k[3:] else 'dc/(files)'
    return k.split('/')[0]
for src, files in (('t15', t15), ('castle', cas), ('island', isl)):
    for k, s in files.items():
        for d in disc_of(k, src):
            if k in seen[d]: continue
            # per-disc data from the right source: texture pack, resident lists and stream file are per disc
            if k in ('dc/tex.pak', 'dc/resident.bin', 'bgm/aica_str.dat'):
                want = {1: 't15', 2: 'castle', 3: 'island'}[d]
                if src != want: continue
            if k.startswith('dc/tex/') and d == 1 and src != 't15' and k not in t15:
                # loose keys added after test 15 (chapter 2-2/2-3 and castle): counted on disc 1 only when a village
                # disc already had them; the castle / island ones go to disc 2 / 3
                continue
            seen[d].add(k); discs[d][part(k)] += s
# castle disc: the castle test disc's tex.pak is test 15's (castle keys loose): replace it by the castle keys only
for d in (1, 2, 3):
    tot = sum(discs[d].values())
    print('DISC %d  %.1f MB measured' % (d, tot / MB))
    for p, s in discs[d].most_common(14): print('   %-22s %7.1f' % (p, s / MB))

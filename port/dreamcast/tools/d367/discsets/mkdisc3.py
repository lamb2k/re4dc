#!/usr/bin/env python3
"""mkdisc3.py D1TREE FIXTURE PROGOUT OUTDIR SETID  (lane world-ch5, 2026-11-02; the island twin of mkdisc2.py)
Disc 3 tree = Disc 1 (release candidate) tree + the island fixture (disc3_fixture.py, fixture wins)
- village rooms (stage 1: st1/, r1xx movies / worlds / events, st1 overlays)
- castle rooms (stage 2 r200-r22b: st2/, their movies / worlds / events, st2_0..3 overlays). r22c (the shooting range,
  st2_4) stays: its doors open from r305 and r31d (DISC-LAYOUT-20261016.md section 2).
+ the Disc 3 program (1ST_READ.BIN + overlays from PROGOUT) + dc/disc.id (disc=3). Writes OUTDIR/tree, manifest.json,
report.json."""
import json, os, re, shutil, subprocess, sys, hashlib

d1, fixture, prog, out, setid = sys.argv[1:6]
tree = os.path.join(out, 'tree')
if os.path.exists(tree):
    shutil.rmtree(tree)
os.makedirs(out, exist_ok=True)
subprocess.check_call(['cp', '-al', d1, tree])
fx = json.load(open(fixture))
SKIP = re.compile(r'^(1ST_READ\.BIN|dc/[^/]+\.ovl|dc/warp\.txt|dc/padscript\.txt|dc/w11\.txt|dc/diag\.txt|dc/disc\.id)$')
rep = {'removed_fixture': 0, 'replaced': 0, 'added': 0, 'skipped': 0, 'village_pruned': 0, 'village_bytes': 0,
       'castle_pruned': 0, 'castle_bytes': 0}


def drop(p):
    if os.path.lexists(p):
        os.remove(p)
        return True
    return False


for k in fx.get('remove', []):
    if drop(os.path.join(tree, k)):
        rep['removed_fixture'] += 1
for k, src in fx['replace'].items():
    if SKIP.match(k):
        rep['skipped'] += 1
        continue
    dst = os.path.join(tree, k)
    existed = drop(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    rep['replaced' if existed else 'added'] += 1
VILLAGE = re.compile(r'^(st1/.*|dc/movie/r1[0-2][0-9a-f]s.*|dc/native/r1[0-2][0-9a-f]/.*|evd/r1[0-2][0-9a-f]s.*|'
                     r'event/evd/r1[0-2][0-9a-f].*|dc/st1_[0-3]\.ovl)$')
# castle r200-r22b; r22c (st2_4 shooting range) is an island-reachable room and stays
CR = r'r2(?:[01][0-9a-f]|2[0-9ab])'
CASTLE = re.compile(r'^(st2/%s[^/]*|dc/movie/%ss.*|dc/native/%s/.*|evd/%ss.*|event/evd/%s.*|dc/st2_[0-3]\.ovl)$'
                    % (CR, CR, CR, CR, CR))
# enemy / partner archives no island or final-chapter room loads: the village and castle enemy sets (their modules are
# dropped by DISC3_MODULES or never linked on the island), Del Lago + Leon's boat (r10b), Luis (pl14, 2-2 .. 3-1)
UNUSED_EM = re.compile(r'^em/(em1[1-7]|em2[1-9a-f]|em35|em3b|pl0f|pl14)\.(drs|das)$')
rep['em_pruned'] = 0; rep['em_bytes'] = 0
# D3_ARCDROP (default 1; lane assets-dc arcdrop 11-02): no game path reads st%x/r%03x.arc (ReadAreaData opens the .dar
# only, src/game/read.cpp), so the room .arc sidecars stay off Disc 3.
ARCDROP = os.environ.get('D3_ARCDROP', '1') == '1'
rep['arc_pruned'] = 0; rep['arc_bytes'] = 0
for d, _, fs in os.walk(tree):
    for f in fs:
        p = os.path.join(d, f)
        rel = os.path.relpath(p, tree)
        if ARCDROP and re.match(r'^st[1-3]/r[0-9a-f]{3}\.arc$', rel):   # assets-dc arcdrop: only .dar is read
            rep['arc_pruned'] += 1; rep['arc_bytes'] += os.path.getsize(p); os.remove(p)
            continue
        if UNUSED_EM.match(rel) and rel not in ('em/em23.drs', 'em/em25.drs'):
            rep['em_pruned'] += 1; rep['em_bytes'] += os.path.getsize(p); os.remove(p)
            continue
        for name, rx in (('village', VILLAGE), ('castle', CASTLE)):
            if rx.match(rel):
                rep[name + '_pruned'] += 1
                rep[name + '_bytes'] += os.path.getsize(p)
                os.remove(p)
                break
for d, ds, fs in os.walk(tree, topdown=False):
    if not os.listdir(d):
        os.rmdir(d)
drop(os.path.join(tree, '1ST_READ.BIN'))
subprocess.check_call(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy', '-R', '.stack', '-O', 'binary',
                       os.path.join(prog, 're4dc-game.elf'), os.path.join(tree, '1ST_READ.BIN')])
for f in os.listdir(os.path.join(tree, 'dc')):
    if f.endswith('.ovl'):
        os.remove(os.path.join(tree, 'dc', f))
for f in os.listdir(prog):
    if f.endswith('.ovl') and not re.match(r'st1_[0-3]\.ovl$|st2_[0-3]\.ovl$', f):
        shutil.copyfile(os.path.join(prog, f), os.path.join(tree, 'dc', f))
drop(os.path.join(tree, 'dc', 'disc.id'))
open(os.path.join(tree, 'dc', 'disc.id'), 'w').write(f'RE4DC disc=3 of=3 set={setid}\n')
# D3_PAK_LIVE (default 1; coordinator 11-02, Disc 3 space): Disc 3's tex.pak keeps only the keys some file Disc 3 ships
# can ask for (vram/texpak_live.py, the static liveness scan: raw key words, R4NREF/R4PREF records, GC TPL source
# identities, material pairs) plus every key an r000 / island / r22c resident list names (UI, fonts, core effects).
# A key pruned wrongly shows as a GC-ASSET / TEXCHK row in the room census (the gate). D3_PAK_LIVE=0 keeps the pack.
if os.environ.get('D3_PAK_LIVE', '1') == '1':
    import glob, struct
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, '..'))
    import texpack
    lo = os.path.join(out, 'paklive')
    # The composed pack may hold more than the runtime's 8,192 keys before this prune (Disc 1's pack + the island keys):
    # read it with texpak_live in-process with the reader's count limit lifted; the pruned pack written below is
    # texpack.build + verify at the runtime limit.
    sys.path.insert(0, os.path.join(here, '..', 'vram'))
    import texpak_live
    _mc = texpack.MAX_COUNT; texpack.MAX_COUNT = 1 << 20
    try:
        rc = texpak_live.main([tree, '--out', lo])
    finally:
        texpack.MAX_COUNT = _mc
    if rc not in (0, 1):
        raise SystemExit('mkdisc3: texpak_live rc %d' % rc)
    live = {ln.split('	')[0] for ln in open(os.path.join(lo, 'live.tsv')).read().splitlines()[1:]
            if ln.split('	')[2] == '1'}
    # crc-only references (lane world-ch5 11-03, TEXCHK 0/33 on the first prune): resident.bin, registry.re4nmr, r4pw
    # parts and the enemy / room archives name many pack keys by their crc word alone (the runtime resolves the second
    # word), so texpak_live's both-words scan missed 32 keys the island rooms load. A key stays when its crc word
    # appears, little- or big-endian at any byte offset, in any shipped file other than the pack, loose tex, movies, bgm.
    import array
    pb = open(os.path.join(tree, 'dc', 'tex.pak'), 'rb').read(); _, _, pc, pio, _ = struct.unpack_from('<8s4I', pb, 0)
    allk = ['%08x-%08x' % struct.unpack_from('<2I', pb, pio + 16 * i) for i in range(pc)]
    cand = {int(k[:8], 16) for k in allk if k not in live}; found = set()
    for d_, _, fs_ in os.walk(tree):
        for fn in fs_:
            rel = os.path.relpath(os.path.join(d_, fn), tree)
            if rel == 'dc/tex.pak' or rel.startswith(('dc/tex/', 'dc/movie/', 'bgm/')):
                continue
            b_ = open(os.path.join(d_, fn), 'rb').read()
            for off in range(4):
                n_ = (len(b_) - off) // 4
                if n_ > 0:
                    a_ = array.array('I'); a_.frombytes(b_[off:off + 4 * n_])
                    found |= cand.intersection(a_); a_.byteswap(); found |= cand.intersection(a_)
    crc_kept = {k for k in allk if k not in live and int(k[:8], 16) in found}
    live |= crc_kept
    # census keep list (coordinator 11-03, safety net): every key a Disc 3 census run asked for is never pruned
    seen = os.path.join(here, '..', 'island5', 'd3-pak-seen.txt')
    census_kept = {l.strip() for l in open(seen) if l.strip()} - live if os.path.exists(seen) else set()
    live |= census_kept
    rep['pak_crc_kept'] = len(crc_kept); rep['pak_census_kept'] = len(census_kept)
    keep = set()
    for t in glob.glob(os.path.join(here, '..', 'vram', 'resident', '**', 'r*.tsv'), recursive=True):
        if re.match(r'r(000|3[0-3][0-9a-f]|22c)', os.path.basename(t)):
            keep |= {ln.split('	')[0] for ln in open(t).read().splitlines()[1:] if ln.strip()}
    pp = os.path.join(tree, 'dc', 'tex.pak'); blob = open(pp, 'rb').read()
    _, _, cnt, ioff, _ = struct.unpack_from('<8s4I', blob, 0); pk = {}
    for i in range(cnt):
        c, f, o_, n = struct.unpack_from('<4I', blob, ioff + 16 * i)
        if '%08x-%08x' % (c, f) in live | keep:
            pk[(c, f)] = blob[o_:o_ + n]
    nb = texpack.build(pk)[0]; texpack.verify(nb)
    drop(pp); open(pp, 'wb').write(nb)
    rep['pak_live_keys'] = len(pk); rep['pak_keys_in'] = cnt; rep['pak_bytes_in'] = len(blob); rep['pak_bytes'] = len(nb)
man, sectors = {}, 0
for d, _, fs in os.walk(tree):
    for f in fs:
        p = os.path.join(d, f)
        rel = os.path.relpath(p, tree)
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        sz = os.path.getsize(p)
        man[rel] = {'sha256': h, 'size': sz}
        sectors += (sz + 2047) // 2048
json.dump(dict(sorted(man.items())), open(os.path.join(out, 'manifest.json'), 'w'), indent=0)
rep['files'] = len(man)
rep['data_sectors'] = sectors
rep['limit'] = 504000
print(json.dumps(rep))
json.dump(rep, open(os.path.join(out, 'report.json'), 'w'), indent=1)
if sectors > rep['limit']:
    sys.exit('mkdisc3: %d data sectors exceed the GD-ROM limit %d' % (sectors, rep['limit']))

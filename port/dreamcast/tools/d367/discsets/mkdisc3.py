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
for d, _, fs in os.walk(tree):
    for f in fs:
        p = os.path.join(d, f)
        rel = os.path.relpath(p, tree)
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

#!/usr/bin/env python3
"""mkdisc2.py D1TREE FIXTURE PROGOUT OUTDIR SETID  (lane discsets20)
Disc 2 tree = disc 1 (release) tree + the castle fixture (castle18 r200b: castle chapter 3-1 data, fixture wins)
- village-only room data (stage-1 rooms r100-r120: st1/, their movies, worlds, events, stage-1 overlays)
+ the disc-2 program (1ST_READ.BIN + overlays from PROGOUT) + dc/disc.id. Writes OUTDIR/tree, manifest.json, report."""
import json, os, re, shutil, subprocess, sys, hashlib

d1, fixtures, prog, out, setid = sys.argv[1:6]
tree = os.path.join(out, 'tree')
if os.path.exists(tree):
    shutil.rmtree(tree)
os.makedirs(out, exist_ok=True)
subprocess.check_call(['cp', '-al', d1, tree])
fx = {'remove': [], 'replace': {}}
extra = {}
for i, fp in enumerate(fixtures.split(',')):
    f_ = json.load(open(fp))
    if i == 0:  # the base castle fixture (castle18 r200b): its removes and replacements
        fx['remove'] += f_.get('remove', [])
        fx['replace'].update(f_['replace'])
    else:  # later fixtures (castle18 r201j): add-only, files the base fixture lacks (their pak/resident stay out)
        extra.update(f_['replace'])
SKIP = re.compile(r'^(1ST_READ\.BIN|dc/[^/]+\.ovl|dc/warp\.txt|dc/padscript\.txt|dc/w11\.txt|dc/diag\.txt)$')
rep = {'removed_fixture': 0, 'replaced': 0, 'added': 0, 'skipped': [], 'village_pruned': 0, 'village_bytes': 0}


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
        rep['skipped'].append(k)
        continue
    dst = os.path.join(tree, k)
    existed = drop(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    rep['replaced' if existed else 'added'] += 1
for k, src in extra.items():
    dst = os.path.join(tree, k)
    if SKIP.match(k) or k in fx['replace'] or os.path.lexists(dst):
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    rep['added_extra'] = rep.get('added_extra', 0) + 1
VILLAGE = re.compile(r'^(st1/.*|dc/movie/r1[0-2][0-9a-f]s.*|dc/native/r1[0-2][0-9a-f]/.*|evd/r1[0-2][0-9a-f]s.*|'
                     r'event/evd/r1[0-2][0-9a-f].*|dc/st1_[0-3]\.ovl)$')
for d, _, fs in os.walk(tree):
    for f in fs:
        p = os.path.join(d, f)
        rel = os.path.relpath(p, tree)
        if VILLAGE.match(rel):
            rep['village_pruned'] += 1
            rep['village_bytes'] += os.path.getsize(p)
            os.remove(p)
for d, ds, fs in os.walk(tree, topdown=False):
    if not os.listdir(d):
        os.rmdir(d)
# program
drop(os.path.join(tree, '1ST_READ.BIN'))
subprocess.check_call(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy', '-R', '.stack', '-O', 'binary',
                       os.path.join(prog, 're4dc-game.elf'), os.path.join(tree, '1ST_READ.BIN')])
for f in os.listdir(os.path.join(tree, 'dc')):
    if f.endswith('.ovl'):
        os.remove(os.path.join(tree, 'dc', f))
for f in os.listdir(prog):
    if f.endswith('.ovl') and not re.match(r'st1_[0-3]\.ovl$', f):
        shutil.copyfile(os.path.join(prog, f), os.path.join(tree, 'dc', f))
open(os.path.join(tree, 'dc', 'disc.id'), 'w').write(f'RE4DC disc=2 of=3 set={setid}\n')
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
rep['skipped'] = len(rep['skipped'])
json.dump(rep, open(os.path.join(out, 'report.json'), 'w'), indent=1)
print(json.dumps(rep))

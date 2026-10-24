from pathlib import Path
import hashlib, json, subprocess, tempfile
BASE = Path('/root/probe/lanes/route/out-dd23stdbaseearP')
OFF = Path('/root/probe/lanes/route/out-dd23stdoff5be3rP')
DEST = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/repair5be-ea-off-identity.json')
OBJCOPY = '/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def programme(p, work):
    image = work / (p.name + '.bin')
    subprocess.run([OBJCOPY, '-R', '.stack', '-O', 'binary', str(p / 're4dc-game.elf'), str(image)], check=True)
    return {'elf_sha256': sha(p / 're4dc-game.elf'), 'raw_no_stack_sha256': sha(image), 'raw_bytes': image.stat().st_size, 'source': (p / 'stack.txt').read_text().strip(), 'end': (p / 'end.txt').read_text().strip(), 'knobs_sha256': sha(p / 'resolved-knobs.txt'), 'candidate_sha256': sha(p / 'candidate.txt')}
for p in (BASE, OFF):
    assert (p / 're4dc-game.elf').is_file()
    assert not (p / 'missing.txt').read_text().strip(), p
    knobs = (p / 'resolved-knobs.txt').read_text().splitlines()
    for required in ('SCENERY_DEDUP=0', 'QA_MENU=0', 'PC_SAMPLER=0', 'WORLD_METER=0'):
        assert required in knobs, (p, required)
with tempfile.TemporaryDirectory(prefix='dd23identity-', dir='/dev/shm') as tmp:
    a, b = (programme(p, Path(tmp)) for p in (BASE, OFF))
assert a['source'] == 'ea969bb241f77291d2ca43d706c9dc2d1226ee76'
assert b['source'] == '5be38f009f9ae4d42daff69dacc537e8230bcfca'
assert a['raw_no_stack_sha256'] == b['raw_no_stack_sha256']
names = sorted(p.name for p in BASE.glob('*.ovl'))
assert len(names) == 14, names
assert names == sorted(p.name for p in OFF.glob('*.ovl'))
rows = [{'name': n, 'baseline': sha(BASE / n), 'off': sha(OFF / n)} for n in names]
assert all(r['baseline'] == r['off'] for r in rows)
r = {'baseline': a, 'dedup_off': b, 'overlays': rows, 'verdict': 'PASS_CURRENT_OFF_RAW_AND_ALL_14_OVERLAYS_IDENTICAL', 'limits': 'SH4 link identity only; no ON correctness, memory, release or hardware acceptance.'}
assert not DEST.exists(), DEST
DEST.write_text(json.dumps(r, indent=2) + '\n')
print(r['verdict'], a['raw_no_stack_sha256'])
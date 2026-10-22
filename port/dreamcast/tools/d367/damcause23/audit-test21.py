"""Bounded read-only Test21 source/evidence audit. No compiler, guest or process probe."""
from pathlib import Path
import hashlib, json, subprocess

REPO = Path('/root/probe/codex-damcause23')
BASE = 'f047721fb138b9d7c1a4bf2edf217f76beda4d6c'
TEST21 = 'fe0efcddc736c49861b51988593629ca04ced336'
OLD = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-crash-20261021')
OUT = REPO / 'port/dreamcast/tools/d367/damcause23'

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()

paths = [
    'src/st1/r10c.cpp', 'src/game/read.cpp', 'src/game/em_set.cpp',
    'src/game/em.cpp', 'include/cManager.h', 'src/game/dvd.cpp',
    'port/dreamcast/game/platform/native_ui.cpp',
    'port/dreamcast/game/platform/crash_screen.cpp',
]
sources = {}
pins = []
for revision in (TEST21, BASE):
    for path in paths:
        data = git('show', revision + ':' + path)
        sources[revision, path] = data.decode()
        pins.append(dict(commit=revision, path=path, bytes=len(data), sha256=digest(data)))
assert not git('diff', BASE, '--', *paths), 'Runtime changes are outside this unit'

binding = json.loads((OLD / 'exact-test21-binding.json').read_text())
assert binding['accepted'] and len(binding['files']) == 15
assert all(row['exact'] and row['public_sha256'] == row['rebuilt_sha256'] for row in binding['files'])
candidate = json.loads((OLD / 'hardware-relocation-candidates.json').read_text())
assert candidate['accepted_source_mapping'] is False
module = next(x for x in candidate['candidates'] if x['section'] == '.ovl_st1_2')
assert module['offset'] == '0x42ba' and module['inferred_runtime_base'] == '0x8c88cae0'
disassembly = (OLD / 'exact-test21-build/st1_2-disassembly.txt').read_text().splitlines()
snippet = '\n'.join(row for row in disassembly
                    if any(('9080' + offset + ':') in row for offset in
                           ('42a6','42a8','42aa','42ac','42ae','42b0','42b2','42b4','42b6','42b8','42ba','42bc','42be','42c0')))
checks = {
    'actor_return_saved_r8': 'mov\tr0,r8',
    'r9_explicitly_zero': 'mov\t#0,r9',
    'r0_clobbered_after_return': 'mov\tr9,r0',
    'actor_vptr_read': 'mov.l\t@r8,r1',
    'vptr_slot24_read': 'mov.l\t@(24,r1),r1',
    'this_argument_r8': 'mov\tr8,r4',
}
for label, needle in checks.items():
    assert needle in snippet, (label, snippet)
assert 0x8c88cae0 + 0x42ba == 0x8c890d9a
assert 0x8c88cae0 + 0x42ac == 0x8c890d8c
assert 0x4328e3ff + 24 == 0x4328e417
old_ui = sources[TEST21, paths[6]]
assert 'SB_ISTERR bits seen since boot' in old_ui
assert 'pvr_ready::ta_timeouts,pvr_ready::render_timeouts' in old_ui
old_room = sources[TEST21, paths[0]]
assert 'EmReadSearch(0x12, 0, 0);' in old_room
assert 'em = EmSetFromList2(2, 1);' in old_room
current_room = sources[BASE, paths[0]]
assert 'RE4DC_EM_READ_RETRY' in sources[BASE, paths[1]]
assert 'if (!em)' in current_room or 'if (em == 0)' in current_room or 'if (em == NULL)' in current_room

receipts = [
    'exact-test21-binding.json', 'exact-test21-overlay-binding.json',
    'final-full-identity-verification.json', 'hardware-relocation-candidates.json',
    'photographed-word-search.json', 'dam-first-event-trigger-plan.json',
    'exact-public-archive-source-bounds.json',
]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'exact-dispatch.txt').write_text(snippet + '\n')
report = dict(
    schema='damcause23-source-evidence-v1', base=BASE, test21_source=TEST21,
    verdict='source-confirmed unchecked refusal; photographed hardware cause remains unproven',
    accepted_hardware_source_mapping=False,
    hardware=dict(pc='8c890d9a', pr='8c890d8c', address='4328e417',
                  r0='00000000', r1='4328e3ff', actor_r8='not visible in cropped photograph'),
    conditional_module=module, instruction_checks={key: True for key in checks},
    conclusions=[
        'Visible r0 was overwritten after EmSetFromList2; it cannot establish the return value.',
        'Visible r1 is a loaded word, not the actor pointer; nonzero r1 cannot establish nonnull actor.',
        'Photographed er and rdy rows report PVR errors/timeouts, not an enemy read result.',
        'No physical-console BIOS/low-address identity or value has been bound.',
        'No new runtime fix is justified by these source-only discriminants.',
    ],
    source_pins=pins,
    preserved_evidence=[dict(path=str(OLD / name), bytes=(OLD/name).stat().st_size,
                             sha256=sha(OLD/name)) for name in receipts],
    preserved_photo=dict(path='/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-20261021/issue52-01.png',
        sha256=sha(Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-20261021/issue52-01.png'))),
    unchanged_runtime_paths=paths,
    limits=['No compile, build, image, guest, runtime edit or native-process query.',
            'No new hardware acceptance, release check, Flycast result or performance result.',
            'No substitution of local emulator BIOS for the photographed console.'],
)
(OUT / 'source-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(verdict=report['verdict'], pins=len(pins),
    receipt_sha256=sha(OUT/'source-receipt.json'),
    dispatch_sha256=sha(OUT/'exact-dispatch.txt'),
    runtime_unchanged=True), indent=2))

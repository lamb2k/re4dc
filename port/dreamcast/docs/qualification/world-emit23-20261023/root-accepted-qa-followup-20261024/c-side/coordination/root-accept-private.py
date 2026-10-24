"""Root delivery metadata, preserving the worker's sealed package metadata."""
from pathlib import Path
import hashlib, json, shutil, sys

e = Path(r'C:\Flycast-Evidence\re4-dreamcast\world-emit23-takeover\49ad20f9\final-qa-stage')
review = Path(sys.argv[1])
assert review.is_file()
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
h = e / 'FINAL-PAIR-HANDBACK.json'
assert sha(h) == '86609ae3b217369c7bb34dd898fd4edbc614f7a7fc0c530df9a25b15270c72f0'
j = json.loads(h.read_text())
assert j['source'] == '49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
out = e / 'root-delivery'
out.mkdir(exist_ok=False)
receipt = dict(status='ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK',
 source=j['source'], worker_handback_sha256=sha(h), independent_review_sha256=sha(review),
 scope='Two private discs; actual final-GDI boot and separately identified fixture-proxy menu-warp/H2.',
 production_enabled=False, physical_console_acceptance=False, hardware_gain_claim=False,
 qa_mendez_tested=False, look_approved=False,
 limitations=['PS2 candidate is common to both arms and proves load/upload only; visible use unproven.',
              'QA heap observations do not replace production-profile KOS/H2 qualification.',
              'Earlier timing is MODELLED and from the earlier recipe; no hardware improvement established.'])
rp = out / 'ROOT-ACCEPTANCE.json'
rp.write_text(json.dumps(receipt, indent=2) + '\n')
deliveries = {}
for arm, label in [('off', 'Off'), ('both', 'Both')]:
    d = Path(r'C:\Game Dev\Emulators') / f'RE4DC-QA23-WorldEmit-{label}-49ad20f9'
    old = out / arm
    old.mkdir()
    for name in ['README.md', 'IDENTITY.json', 'SHA256SUMS.txt']:
        shutil.copyfile(d / name, old / name)
    ident = json.loads((d / 'IDENTITY.json').read_text())
    for name, pin in ident['programme_readback']['tracks'].items():
        p = d / 'gdemu' / name
        assert p.stat().st_size == pin['size'] and sha(p) == pin['sha256'], str(p)
    for kind, gate in ident['gates'].items():
        assert gate['guest_seconds'] < 55, kind
    assert ident['gates']['h2']['observed']['full340']
    assert ident['gates']['h2']['observed']['matching_arena_return_restored']
    r = (d / 'README.md').read_text()
    r = r.replace('pending root review', 'root-reviewed for private console feedback')
    r = r.replace('Pending root review', 'Root-reviewed for private console feedback')
    r = r.replace('PENDING ROOT REVIEW', 'ROOT REVIEW COMPLETE: PRIVATE CONSOLE FEEDBACK ONLY')
    (d / 'README.md').write_text(r)
    ident['root_review'] = 'ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK'
    ident['root_acceptance_sha256'] = sha(rp)
    ident['readme'] = dict(size=(d / 'README.md').stat().st_size, sha256=sha(d / 'README.md'))
    (d / 'IDENTITY.json').write_text(json.dumps(ident, indent=2) + '\n')
    shutil.copyfile(rp, d / 'ROOT-ACCEPTANCE.json')
    sums = []
    for p in sorted(d.rglob('*')):
        if p.is_file() and p.name != 'SHA256SUMS.txt':
            sums.append(sha(p) + '  ' + p.relative_to(d).as_posix())
    (d / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
    for line in sums:
        pin, rel = line.split('  ', 1)
        assert sha(d / rel) == pin
    deliveries[arm] = dict(path=str(d), identity_sha256=sha(d / 'IDENTITY.json'),
                            sums_sha256=sha(d / 'SHA256SUMS.txt'), files=len(sums))
(out / 'DELIVERY-READBACK.json').write_text(json.dumps(dict(root_receipt_sha256=sha(rp), arms=deliveries), indent=2)+'\n')
print(json.dumps(deliveries, indent=2))

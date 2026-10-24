"""Dated source/evidence checkpoint, without target execution or private payloads."""
from pathlib import Path
import ast, datetime, hashlib, json, os, subprocess

T = Path('/root/work/lanes/gc23-evidence-tools')
C = Path('/mnt/c/Game Dev/Emulators/codex-lanes')
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024')
HERE = Path(__file__).resolve().parent
PARENT = '8b7b01d535f02bf4bbdcdbf7d7ece16de010d132'
PREFIX = 'port/dreamcast/tools/d367/gc23_evidence'
DEST = T / PREFIX / '20261024-integration-normal-QA-profile-hold-v1'
GUARD = '8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
MATH = '28c739468ae7d2d2d3c09f81330015e7769dc824'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())

def git(tree, *a): return subprocess.check_output(['git', '-C', str(tree), *a])
def raw(path):
    a = path.stat(); b = path.read_bytes(); z = path.stat()
    assert not path.is_symlink() and (a.st_size, a.st_mtime_ns) == (z.st_size, z.st_mtime_ns), path
    return b, a.st_mtime_ns
def identity(path):
    a = path.stat()
    with path.open('rb') as f: h = hashlib.file_digest(f, 'sha256').hexdigest()
    z = path.stat(); assert (a.st_size, a.st_mtime_ns) == (z.st_size, z.st_mtime_ns)
    return {'source': str(path), 'bytes': a.st_size, 'sha256': h, 'source_mtime_ns': a.st_mtime_ns}
def decode(b, name):
    try: return b.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        assert name.endswith('.md'); return b.decode('cp1252'), 'non-UTF8 original; cp1252-compatible diagnostic only'

def main():
    assert git(T, 'rev-parse', 'HEAD').decode().strip() == PARENT and not git(T, 'status', '--porcelain')
    assert not DEST.exists() and os.statvfs('/mnt/c').f_bavail * os.statvfs('/mnt/c').f_frsize >= 24 * 1024**3
    selected = []; references = []; hashes = []; verified = []; prior = {}
    for mp in (T / PREFIX).glob('*/SOURCE-MANIFEST.json'):
        for r in read(mp)['files']:
            p = mp.parent / r['destination']; key = (r['bytes'], r['sha256'])
            assert len(p.read_bytes()) == key[0] and sha(p.read_bytes()) == key[1]
            prior.setdefault(key, p.relative_to(T).as_posix())
    def add(p, rel, pin=None, dedup=False):
        b, stamp = raw(p)
        if pin: assert len(b) == pin['bytes'] and sha(b) == pin['sha256'], p
        key = (len(b), sha(b))
        if dedup and key in prior:
            references.append({'source': str(p), 'logical_destination': rel, 'bytes': key[0], 'sha256': key[1],
                'prior_archive_path': prior[key], 'prior_evidence_ancestor': PARENT}); return
        assert len(b) < 3 * 1024**2 and b'\0' not in b
        decode(b, str(p)); selected.append((str(p), rel, b, stamp))
    def member(p, rel, pin=None):
        if p.suffix in {'.elf', '.bin', '.ovl', '.o', '.a'} or (p.suffix == '.log' and p.stat().st_size > 16384) or p.stat().st_size > 3 * 1024**2:
            row = identity(p)
            if pin: assert row['bytes'] == pin['bytes'] and row['sha256'] == pin['sha256'], p
            hashes.append(dict(row, logical_destination=rel, payload_copied=False)); return
        add(p, rel, pin, dedup=True)
    def dictmanifest(root, filename, label):
        pins = read(root / filename)
        for name, pin in pins.items(): member(root / name, label + '/' + name, pin)
        add(root / filename, label + '/' + filename)
        verified.append({'source': str(root / filename), 'members': len(pins), 'sha256': sha((root / filename).read_bytes())})
    def listmanifest(root, label):
        pins = read(root / 'MANIFEST.json')
        for row in pins: member(root / row['file'], label + '/' + row['file'], row)
        add(root / 'MANIFEST.json', label + '/MANIFEST.json')
        verified.append({'source': str(root / 'MANIFEST.json'), 'members': len(pins), 'sha256': sha((root / 'MANIFEST.json').read_bytes())})
    docs = read(HERE / 'stable-dated-inputs/CAPTURED-DOCS.json')
    for r in docs['files']: add(HERE / 'stable-dated-inputs' / r['snapshot'], 'dated-root-docs/' + r['snapshot'], r)
    add(HERE / 'stable-dated-inputs/CAPTURED-DOCS.json', 'dated-root-docs/CAPTURED-DOCS.json')
    for n in ['apply-composition-integration-guards-20261024.py', 'commit-composition-integration-prep-20261024.py',
              'create-composition-integration-prep-20261024.py', 'fix-composition-fixture-projection-20261024.py',
              'ROOT-COMPOSITION-INTEGRATION-PREP-20261024.json', 'integration-preview-vis-compose-20261024.py',
              'ROOT-INTEGRATION-PREVIEW-VIS-COMPOSE-20261024.json']:
        add(C / n, 'root-integration-preparation/' + n)
    for n in ['check-guard-mutants.py', 'FAILED-FIXTURE-v1.json', 'failed-fixture-v1.py', 'GUARD-MUTANTS.json',
              'HOST-v2.json', 'HOST-v2.log', 'Make-GC-admission.log', 'ROOT-CHECKPOINT.json',
              'Static-GC-admission.log', 'STATUS.md', 'UI-GC-admission.log']:
        add(C / 'composition-int24' / n, 'root-guarded-composition/' + n)
    review = C / 'interior-vis23/composition-int24-review'
    listmanifest(review, 'independent-composition-review')
    receipt = read(review / 'RECEIPT.json'); assert receipt['source'] == GUARD
    for path, pin in receipt['source_members'].items():
        b = git('/root/work/lanes/codex-composition-int24', 'show', GUARD + ':' + path); assert sha(b) == pin
        selected.append(('git:' + GUARD + ':' + path, 'frozen-composition-source/' + path, b, None))
    for path in ['REVIEW.md', 'review_host.py']:
        gpath = 'port/dreamcast/tools/d367/interior_vis23/reviews/composition_int24/' + path
        b = git('/root/probe/codex-triangle-shadow24', 'show', '03ac75c7f50b3438b46096e847fb15901db63e98:' + gpath)
        assert b == (review / path).read_bytes()

    math = C / 'triangle-shadow24'; seal = read(math / 'SOURCE-SEAL.json')
    assert seal['source_revision'] == MATH
    for row in seal['members']:
        b = git('/root/probe/codex-triangle-shadow24', 'show', MATH + ':' + row['path'])
        assert len(b) == row['bytes'] and sha(b) == row['sha256']
        selected.append(('git:' + MATH + ':' + row['path'], 'generic-triangle-source/' + row['path'], b, None))
    for n in ['SOURCE-SEAL.json', 'HOST-RESULTS.json', 'HANDBACK.md', 'STATUS.md']:
        add(math / n, 'generic-triangle-receipts/' + n)
    listmanifest(math / 'review-implementation', 'generic-triangle-independent-review')
    for row in seal['design_inputs']: add(Path(row['path']), 'generic-triangle-design/' + Path(row['path']).name, row)
    # The design MANIFEST and REVIEW above are already selected; add only its other authenticated members.
    design = C / 'interior-discovery24/review-actual-triangle-shadow'
    for row in read(design / 'MANIFEST.json'):
        if row['file'] != 'REVIEW.md': add(design / row['file'], 'generic-triangle-design/' + row['file'], row)
    add(C / 'interior-vis23/STATUS.md', 'dated-lane-status/interior-vis23-STATUS.md')
    add(C / 'gc-motion24/STATUS.md', 'dated-lane-status/gc-motion24-STATUS.md')

    # Durable private bundle manifests: binaries and bulk logs are verified hash-only.
    for dirname, label, expected, count in [
        ('full-normal-aab-current-v1', 'durable-normal', 'a307ae69c26cdac34671f0819c25345369e0a2741775e96bb04c004f0af47a67', 52),
        ('qa-memory-aab-v2/programmes', 'durable-QA-three', 'bc0f03701b3014f1cf5040c086f18b455da9c436620c0626a54cda9c74ae65b1', 70)]:
        root = E / dirname; pins = read(root / 'MANIFEST.json')
        assert sha((root / 'MANIFEST.json').read_bytes()) == expected and len(pins['files']) == count
        for row in pins['files']: member(root / row['path'], label + '/' + row['path'], row)
        add(root / 'MANIFEST.json', label + '/MANIFEST.json')
        verified.append({'source': str(root / 'MANIFEST.json'), 'members': count, 'sha256': expected})
    normal = E / 'full-normal-aab-current-v1'
    assert sha((normal / 'review/root-followup-v1/ROOT-GIT-EXPORT-BINDING.json').read_bytes()) == 'c95d8dd0960db0e0215c130202a57c11b2175221702109bc8650acf2f45406f7'
    assert sha((normal / 'receipts/continuation-v1/receipt.json').read_bytes()) == '1a546adada1d1555c3b28909f52d39007cb31bf4f269d480fc442d07b4ac2465'
    assert read(normal / 'receipts/continuation-v1/receipt.json')['complete']
    motion = C / 'gc-motion24'
    dictmanifest(motion / 'full-link-continuation', 'SHA256-MANIFEST.json', 'normal-continuation-source')
    add(motion / 'full-link-continuation/ROOT-GRANT.json', 'normal-continuation-source/ROOT-GRANT.json')
    for n in ['PLAN.md', 'PROPOSAL.json']: add(motion / 'memory-qualification-prep' / n, 'memory-plan/' + n)
    for version in ['v1', 'v2']:
        root = motion / 'memory-qualification-prep' / ('qa-pair-' + version)
        dictmanifest(root, 'SHA256-MANIFEST.json', 'QA-preparation-' + version)
        add(root / 'ROOT-GRANT.json', 'QA-preparation-' + version + '/ROOT-GRANT.json')
    failed = Path('/dev/shm/gc-motion24-qa-memory-2ugz4ae8')
    add(failed / 'qa-receipt.json', 'QA-original-preflight-failure/qa-receipt.json')
    add(failed / 'baseline/build.log', 'QA-original-preflight-failure/build.log')
    assert not read(failed / 'qa-receipt.json')['complete']
    qroot = Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8')
    qr = read(qroot / 'qa-receipt.json')
    assert qr['complete'] and all(qr['arms'][n]['complete'] for n in ['baseline', 'off', 'on'])
    assert [qr['arms'][n]['raw_sha256'] for n in ['baseline','off','on']] == [
        'e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5',
        'e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5',
        '02a14f20f815607da8caa6b118e775a2f567b0f85a067f28c00c1cc6b14251ae']
    qreview = motion / 'qa-memory-media-prep'
    for n in ['FAILED-BROAD-PROFILE-v1.json', 'failed-broad-profile-v1.py', 'QA-READBACK.json', 'verify_qa_three.py']:
        add(qreview / n, 'QA-independent-profile-HOLD/' + n)
    broad = read(qreview / 'FAILED-BROAD-PROFILE-v1.json'); current = read(qreview / 'QA-READBACK.json')
    assert len(broad['differences']) == 6 and broad['differences']['PS2_ENEMY_ROOMS'] == ['0x3f', '0x3ff']
    assert current['status'] == 'INDEPENDENT_QA_PROGRAMME_READBACK_PASS_PROFILE_PIN_CLOSURE_PENDING'
    assert current['QA_receipt_sha256'] == sha((qroot / 'qa-receipt.json').read_bytes())
    assert all(current['resolved_report_exceptions'][n] == broad['differences'] for n in ['baseline','off','on'])
    assert 'PENDING' in current['full_private_input_closure']
    rainreview = motion / 'review-rain-target846'
    dictmanifest(rainreview, 'SHA256-MANIFEST.json', 'rain846-HOLD-review')
    dictmanifest(rainreview, 'VALID-EXTENT-MANIFEST.json', 'rain846-HOLD-review')
    # Source-only collector itself; no author tool payloads, actual triangle geometry or active stage preparation.
    add(Path(__file__).resolve(), 'collect.py')
    assert len({rel for _, rel, _, _ in selected}) == len(selected)
    assert sum(len(b) for _, _, b, _ in selected) < 12 * 1024**2
    DEST.mkdir(parents=True); (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []; syntax = []
    for source, rel, b, stamp in selected:
        assert b'\0' not in b; text, encoding = decode(b, rel)
        if rel.endswith('.py'): ast.parse(text, filename=source); syntax.append(rel)
        if rel.endswith('.sh'): subprocess.run(['bash','-n'],input=b,check=True); syntax.append(rel)
        out = DEST / rel; out.parent.mkdir(parents=True,exist_ok=True); out.open('xb').write(b)
        rows.append({'source':source,'destination':rel,'bytes':len(b),'sha256':sha(b),'lf_sha256':sha(b.replace(b'\r\n',b'\n')),
            'crlf_count':b.count(b'\r\n'),'text_encoding':encoding,'source_mtime_ns':stamp})
    def emit(n,j): (DEST/n).write_text(json.dumps(j,indent=2)+'\n')
    emit('SOURCE-MANIFEST.json',{'parent_evidence_commit':PARENT,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'root_docs_frozen_utc':docs['captured_utc'],'files':rows})
    emit('PRIOR-ARCHIVE-REFERENCES.json',{'files':references,'disclosure':'Exact bytes already retained in unchanged ancestor snapshots; logical destinations reconstruct by path/hash.'})
    emit('HASH-ONLY-ARTIFACTS.json',{'files':hashes,'disclosure':'Private binaries/objects/bulk build logs and large metadata plans verified read-only; no payload archived.'})
    emit('VALIDATION.json',{'verified_manifests':verified,'syntax_only_checked':syntax,'root_guard_source':GUARD,'generic_math_source':MATH,
        'composition_review_commit':'03ac75c7f50b3438b46096e847fb15901db63e98','generic_math_review_reference':'dd61a3fb14f14dd9d6099b34bb466d926c315607 (producer-reported origin/codex/pvs23-data; object unavailable in local pool, exact C manifest and bytes verified)',
        'QA_raw_three_complete':True,'QA_full_profile_PIN_closure':'HOLD/PENDING; six resolved-map differences and historical external neck-header pin absent',
        'memory_or_media_or_guest_acceptance':False,'rain846_tools':'HOLD plus valid-extent addendum; active repair payload excluded',
        'SDK_or_guest_runs':0,'runtime_or_integration_mutation':False,'private_actual_geometry_copied':False})
    (DEST/'README.md').write_text('''# Dated integration preparation, completed links, and QA profile HOLD

Append-only successor to evidence8b7b. Root STATUS/updater/CARRY frozen08:46:14.372882Z on2026-10-24; moving docs remain independent. Root guarded integration8ce5, owned synthetic adapter/tests/docs and independent review03ac are source/host preparation only, with initial rejected fixture preserved. Four exact generic triangle math28c files and dd61 review/design3cd9/c22 are synthetic source records; no actual private geometry or actual source report is included.

Durable normal52-member and QA70-member programme manifests are preserved. All manifest members are independently byte-hashed; only compact text metadata is copied, with identical earlier archive bytes referenced and binaries/objects/bulk build logs/large plans hash-only. Normal original runner failure and later completed continuation1a546 remain distinct. Normal root export-bindingc95d8 preserves its exact scope. QA original baseline dead-knob preflight failure remains distinct from correctedv2 three completed programme links (baseline/off e016, on02a14f). No SDK or guest was invoked by this preservation.

QA programme identity readback is complete; full profile/input closure remains HOLD/PENDING. Exact original broad-profile failure records six common differences: PS2_ENEMY_ROOMS expected0x3f versus resolved0x3ff and five keys absent from resolved reports. Corrected independent receipt checks programme/source/critical subset only and explicitly retains all six exceptions. Historical external neck-header pin absent from QA input_pins is also pending. No staging/media/memory/heap/KOS/H2/guest/physical acceptance follows. Future stage preparation is excluded. Rain846 tool review remains HOLD, with separate valid-extent controls; moving author repair tools are excluded. No runtime/default/recipe/source or active runner mutation, no SDK, no guest and no integration push.

Every copied original retains raw bytes, including CRLF and non-UTF8 CARRY bytes; LF hashes are diagnostic only. Prior archive paths remain unchanged. Compact host-control logs may be retained; full game logs and private source/SDK exports, asset data, programmes, objects, ELF and captures are excluded.
''')
    files=sorted(p for p in DEST.rglob('*') if p.is_file())
    (DEST/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.relative_to(DEST).as_posix()+'\n' for p in files))
    print(json.dumps({'snapshot':str(DEST),'original_inputs':len(rows),'original_bytes':sum(r['bytes'] for r in rows),
        'files':len(files)+1,'hash_only_artifacts':len(hashes),'prior_exact_references':len(references),
        'seal_sha256':sha((DEST/'SHA256SUMS').read_bytes()),'CRLF_inputs':sum(bool(r['crlf_count']) for r in rows),'syntax_checks':len(syntax)},indent=2))

if __name__=='__main__':main()

"""Read-only frozen-host-helper and capture-inventory checks after media review."""
from pathlib import Path
import hashlib, json, subprocess

HERE = Path(__file__).resolve().parent
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
C = HERE.parent
COMMIT = '2472ccfd6e120a10e15443506b11687330beb49c'
REPO = '/root/work/lanes/dedup-offline23'
PREFIX = 'port/dreamcast/tools/d367/dedup_offline23/current-4be/'
EXPECTED = {
    'run.sh': 'fb96df1a4231aa8d4b03ec0724196e4933617f9e57e5ca3cda9c0c0fae1c39d2',
    'judge.py': 'f1ec34949f885bb474b734519d9f779f6c64b49eafb7f57a9082905dee4eb8f2',
    'stage.py': '712dcd2cbdf48b9545a306c6a901ef1d342f594d0d8e0125a158453016203f4f',
    'seal.py': 'e36b4cecb0c66702a25ae79e0d56d36e2921c7b7e2e88764f1c485abb08addf1',
    'proxy.py': 'f5afc0bd04fa742c428ba5b3bc9b3290b53830ec6066a1dca0ad6f3785be5074',
    'retire-proxy.py': 'f95483eef9d0cbf95b7cfd248f85a47a6c6324c4e12c6935697c35a8e7315b32',
}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rows = {}
for suffix, expected in EXPECTED.items():
    name = 'current-d5c-qa-' + suffix
    frozen = subprocess.check_output(['git', '-C', REPO, 'show', COMMIT + ':' + PREFIX + name])
    assert frozen == (C / name).read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == expected
    rows[name] = expected
runner = (C / 'current-d5c-qa-run.sh').read_text()
assert 'stat-guest-slot.sh' in runner and 'trace_lock.sh' in runner and 'census-bound-run.py' in runner
assert 'FP_NOLIMIT=1 TRACE_SLOTS=16' in runner and 'RE4DC_MAX_FLYCASTS=16' in runner
assert '--seconds 50 --period 10' in runner and 'flock -n 7' in runner
checksum = E / 'qa-delivery-checksum-readback-r1.json'
assert sha(checksum) == '3d6fdd9c846792cf297b3e2ca061bca516695e81d0f610aca74f3fc0ce3e763f'
j = json.loads(checksum.read_text())
assert j['status'] == 'PASS_INDEPENDENT_SHA256SUM_DELIVERY_READBACK'
assert j['seal_sha256'] == sha(E / 'private-qa-pair-seal-r1.json')
results = json.loads((HERE / 'RESULTS.json').read_text())
for arm, row in j['arms'].items():
    assert row['sha256sum_check_exit_code'] == 0
    assert row['manifest_sha256'] == results['arms'][arm]['sha256sums_sha256']
inventory = E / 'qa-capture-inventory-r1.json'
assert sha(inventory) == '97e4a2ff8a283c02c313d3a4b13e3ee822e04a840da4f0d8f146ca611a7fa164'
captures = json.loads(inventory.read_text())
count = total = 0
for name, row in captures['captures'].items():
    assert row['gate_sha256'] == sha(E / ('qa-' + name + '-console-r1/qa-gate.json'))
    for image in row['screenshots']:
        path = Path(image['path'])
        assert path.stat().st_size == image['bytes'] and sha(path) == image['sha256']
        count += 1; total += image['bytes']
assert count == 24
report = {
    'status': 'FROZEN_HOST_HELPERS_AND_INVENTORY_CLEAR',
    'media_review_sha256': sha(HERE / 'RESULTS.json'), 'source_helper_commit': COMMIT,
    'host_helper_hashes': rows, 'native_checksum_readback_sha256': sha(checksum),
    'capture_inventory_sha256': sha(inventory), 'actual_png_count': count, 'actual_png_bytes': total,
    'stat_slot_helper_sha256': sha(C.parent / 'stat-bytes23/stat-guest-slot.sh'),
    'scope': '24 PNG identities checked only; no additional visual review, wall-time pixel comparison or guest execution. Frozen host runner shows own lock/stat3/trace16 and exact-child bounded guard; raw capture bound receipts were separately checked.'
}
with (HERE / 'SUPPLEMENT.json').open('x') as out:
    out.write(json.dumps(report, indent=2) + '\n')
print(report['status'], sha(HERE / 'SUPPLEMENT.json'))

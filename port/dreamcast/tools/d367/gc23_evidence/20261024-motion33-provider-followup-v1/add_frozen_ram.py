"""Append the late root-admitted frozen RAM source audit without rewriting core bytes."""
from pathlib import Path
import ast, datetime, hashlib, json

ROOT = Path('/root/work/lanes/gc23-evidence-tools/port/dreamcast/tools/d367/gc23_evidence/20261024-motion33-provider-followup-v1')
SOURCE = Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/ram-budget-next-audit')
CORE = 'b18b3f5cde5d7ce5058f29df3bdeae12a4b9ac5a5f3d52effc0c05e42cc39404'
RECEIPT = '9e6d9516260704e5f1e2fb032688d90a08e5f24e8aac3efc1eccd8b564377ab7'
sha = lambda data: hashlib.sha256(data).hexdigest()

def main():
    assert sha((ROOT / 'SHA256SUMS').read_bytes()) == CORE
    assert sha((SOURCE / 'RECEIPT.json').read_bytes()) == RECEIPT
    receipt = json.loads((SOURCE / 'RECEIPT.json').read_text())
    assert receipt['status'] == 'SOURCE_BOUND_AUDIT_COMPLETE'
    assert receipt['source'] == 'aab201ceac0e18107f64a3212398afe916793327'
    assert receipt['full_link_metadata_members_reverified'] == 26
    names = ['audit_budget.py', 'RAM-BUDGET.md', 'READBACK.json', 'RECEIPT.json', 'STATUS.md']
    assert sum((SOURCE / name).stat().st_size for name in names) == 53396
    for pin in receipt['review_files']:
        data = (SOURCE / pin['path']).read_bytes()
        assert len(data) == pin['bytes'] and sha(data) == pin['sha256']
    target = ROOT / 'late-frozen-ram-source-audit'
    target.mkdir(exist_ok=False)
    rows = []
    for name in names:
        path = SOURCE / name; before = path.stat(); data = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        assert b'\x00' not in data; data.decode('utf-8')
        if path.suffix == '.py': ast.parse(data.decode(), filename=name)
        (target / name).write_bytes(data)
        rows.append({'source': str(path), 'destination': 'late-frozen-ram-source-audit/' + name,
            'bytes': len(data), 'sha256': sha(data), 'lf_sha256': sha(data.replace(b'\r\n', b'\n')),
            'crlf_count': data.count(b'\r\n'), 'source_mtime_ns': before.st_mtime_ns})
    own = Path(__file__).resolve(); (ROOT / 'add_frozen_ram.py').write_bytes(own.read_bytes())
    addition = {'status': 'LATE_ROOT_ADMITTED_FROZEN_RAM_SOURCE_ONLY_ADDITION',
        'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'core_seal_sha256_unchanged': CORE, 'frozen_receipt_sha256': RECEIPT,
        'sealed_audit_members': 5, 'sealed_audit_bytes': 53396, 'files': rows,
        'preservation_script_sha256': sha(own.read_bytes()),
        'root_moving_docs_refreshed': False, 'RAM_audit_included_in_final_archive': True,
        'core_RAM_exclusion_statement_scope': 'Core excluded the then-unfrozen audit; this later admitted five-file source addition is explicitly separate.',
        'binary_object_SDK_bytes_read_or_copied': 0,
        'qualification': 'Source-bound arithmetic audit only; computed4KiB reserve is not a spare pool. Preserves corrected UI-array arithmetic and original26-metadata hash references. No new whole-link, measured heap/KOS loss, SDK, guest or runtime acceptance.'}
    (ROOT / 'LATE-RAM-ADDITION-MANIFEST.json').write_text(json.dumps(addition, indent=2) + '\n')
    (ROOT / 'FINAL-HANDBACK.md').write_text('''# Final aggregate source/metadata handback

This archive preserves its original Motion33 core seal unchanged and appends the root's subsequently frozen RAM source audit. The core's then-unfrozen RAM exclusion remains a dated statement; `LATE-RAM-ADDITION-MANIFEST.json` explicitly admits the final five source/JSON/MD files,53,396 bytes, receipt9e6d9516. No root STATUS/updater/CARRY refresh occurred after07:33:28Z.

The added audit retains original26 full-link metadata identities as hash references only. Its actual-fit arithmetic preserves the computed4KiB reserve; it is not a new spare pool or a measured heap/KOS budget. The earlier nominal UI field arithmetic is corrected by unchanged full-array size. No ELF/mm object, SDK bytes, runtime-source export payload, live RAM audit output or binary is copied. Audit source is syntax-parsed, never executed here.

All Motion/provider, partial UNKNOWN-only, stack-chain/IRQ, full-link, producer-terminal, provenance, runtime/physical and hardware limitations remain. PVSb93 and Rain plan016757 stay reference-only; mutable discovery and Rain diagnostic implementation remain excluded.

`SHA256SUMS` is the immutable core seal. `FINAL-SHA256SUMS` seals the complete aggregate including this late addition and the core seal. Exact Git export must verify copied inputs, all new metadata and all397 independent shared-member references before the origin-only push. No SDK, guest, source/runtime or integration mutation follows from this preservation.
''')
    assert sha((ROOT / 'SHA256SUMS').read_bytes()) == CORE
    lines = [sha(p.read_bytes()) + '  ' + p.relative_to(ROOT).as_posix() for p in sorted(ROOT.rglob('*')) if p.is_file()]
    (ROOT / 'FINAL-SHA256SUMS').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'late_frozen_audit_members': len(rows), 'late_frozen_audit_bytes': 53396,
        'core_seal_unchanged': CORE, 'final_seal_sha256': sha((ROOT / 'FINAL-SHA256SUMS').read_bytes())}, indent=2))

if __name__ == '__main__': main()

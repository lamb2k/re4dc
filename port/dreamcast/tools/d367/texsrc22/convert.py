#!/usr/bin/env python3
"""Prepare a reviewed texsrc22 mip candidate with existing encoders.

OFF copies the source pack byte for byte. ON requires an explicit selection:
  {"schema": "re4dc-texsrc22-selection-1", "base_pack_sha256": "...",
   "quality_gate_sha256": "...", "hold_keys_sha256": "...",
   "approved_keys": ["01234567-89abcdef"]}

Pass the current reviewed mip_quality.py as --quality-gate and the explicit
room selection TSV as --hold-keys. The branch's first-pass classification TSV
is not an approval manifest. Source labels do not prove live sampling, and
shared GC Ganado consumers must be resolved before their keys are approved.

The external gate is intentional: the parked texsrc22 branch does not carry
mipfix22 or the current room policy. No private worktree is imported. Outputs
are private candidates, not release assets; runtime and room budgets remain
separate acceptance checks. No recovery encoder or automatic re-encoding is
used. Every gate failure retains its exact original package bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import ModuleType

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'd367'))
import convert_tpl as tpl
import mipmap_vq as vq
import mipmap_twiddled as tw
import mipmap_pal4 as pal4
import texpack
from vram.vq_pak import read_pak

SCHEMA = 're4dc-texsrc22-selection-1'
KEY = re.compile(r'[0-9a-f]{8}-[0-9a-f]{8}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
ENCODERS = {
    'vq': (vq.read_native_vq, vq.decode_level, vq.add_mipmaps,
           lambda n: n.codebook + n.base_indices),
    'twiddled': (tw.read_native_twiddled, tw.decode_level, tw.add_mipmaps,
                 lambda n: n.base_texels),
    'pal4': (pal4.read_native_pal4, pal4.decode_level, pal4.add_mipmaps,
             lambda n: n.base_indices + n.palette),
}


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def repository_source_hashes(*modules):
    """Record the actual imported helper sources, including a gate's helpers.

    Gate hashes pin its policy source, while this receipt makes its resolved
    repository dependencies visible without hashing Python's standard library.
    Follow imported functions too: read_pak comes from vram.vq_pak.
    """
    roots = {TOOLS.resolve()}
    for module in modules:
        root = getattr(module, 'TOOLS', None)
        if root is not None:
            roots.add(Path(root).resolve())
    pending, hashes = list(modules), {}
    while pending:
        module = pending.pop()
        if module.__name__ in hashes:
            continue
        path = Path(module.__file__).resolve()
        hashes[module.__name__] = digest(path.read_bytes())
        for value in vars(module).values():
            dependency = value if isinstance(value, ModuleType) else sys.modules.get(getattr(value, '__module__', ''))
            source = getattr(dependency, '__file__', None)
            if source is not None and any(Path(source).resolve().is_relative_to(root) for root in roots):
                if dependency.__name__ not in hashes:
                    pending.append(dependency)
    return dict(sorted(hashes.items()))


def key_tuple(name):
    if not isinstance(name, str) or not KEY.fullmatch(name):
        raise ValueError('invalid lowercase texture key: %r' % name)
    return tuple(int(x, 16) for x in name.split('-'))


def hold_keys(blob):
    keys = set()
    for line in blob.decode('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.split('\t')[0] == 'key':
            continue
        name = line.split('\t')[0]
        key_tuple(name)
        keys.add(name)
    return keys


def validate_selection(selection, source, gate_bytes, hold_bytes):
    if not isinstance(selection, dict) or selection.get('schema') != SCHEMA:
        raise ValueError('a reviewed %s selection is required' % SCHEMA)
    for field, blob in (('base_pack_sha256', source),
                        ('quality_gate_sha256', gate_bytes),
                        ('hold_keys_sha256', hold_bytes)):
        expected = selection.get(field)
        if not isinstance(expected, str) or not SHA.fullmatch(expected):
            raise ValueError('selection requires a lowercase SHA256: ' + field)
        if digest(blob) != expected:
            raise ValueError('selection input identity mismatch: ' + field)
    names = selection.get('approved_keys')
    if not isinstance(names, list) or not names:
        raise ValueError('selection requires a nonempty approved_keys list')
    for name in names:
        key_tuple(name)
    if len(set(names)) != len(names):
        raise ValueError('duplicate approved key')
    return sorted(names)


def load_gate(path, expected_sha256):
    """Load only the caller-pinned, reviewed gate; report dependency hashes too."""
    path = Path(path).resolve()
    if digest(path.read_bytes()) != expected_sha256:
        raise ValueError('quality gate identity changed before import')
    # Execute the exact bytes whose identity was checked, never a cached .pyc.
    raw = path.read_bytes()
    if digest(raw) != expected_sha256:
        raise ValueError('quality gate identity changed before execution')
    module = ModuleType('texsrc22_quality_gate')
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    try:
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(module.__name__, None)
        raise
    if not callable(getattr(module, 'audit', None)):
        raise ValueError('quality gate does not expose audit(item)')
    return module


def identify(blob):
    if len(blob) < tpl.HEADER.size + tpl.TEXTURE.size:
        raise ValueError('selected package is shorter than its descriptors')
    header = tpl.HEADER.unpack_from(blob)
    if header[4] != 1:
        raise ValueError('selected package must contain exactly one texture')
    for name, (read, decode, generate, base) in ENCODERS.items():
        try:
            return name, read(blob), decode, generate, base
        except ValueError:
            pass
    raise ValueError('selected package is unsupported, malformed or non-square')


def unchanged_base(before, after, decode, base):
    if (before.texture[:5] != after.texture[:5]
            or before.texture[7:] != after.texture[7:]
            or before.texture[6] | tpl.FLAG_MIPMAP != after.texture[6]
            or before.header[:7] != after.header[:7]
            or before.header[9:] != after.header[9:]
            or base(before) != base(after)
            or decode(before, before.size) != decode(after, after.size)):
        raise ValueError('generator changed selected base pixels or material identity')


def build_candidate(source, *, enabled=False, selection=None, gate_path=None,
                    hold_bytes=None, engine='auto'):
    texpack.verify(source)
    packages = read_pak(source)
    report = dict(schema='re4dc-texsrc22-candidate-1', enabled=bool(enabled),
                  candidate_only=True, source_pack_sha256=digest(source),
                  converter_sha256=digest(Path(__file__).read_bytes()),
                  members=len(packages), selected=0, changed=0,
                  unchanged=len(packages), unselected=len(packages),
                  unselected_exact=len(packages), extra_payload_bytes=0,
                  extra_alloc32_bytes=0, rows=[])
    if not enabled:
        report.update(output_pack_sha256=digest(source), reason='disabled; exact pack identity')
        return source, report
    if gate_path is None or hold_bytes is None:
        raise ValueError('enabled conversion requires an explicit gate and room hold manifest')
    gate_path = Path(gate_path)
    gate_bytes = gate_path.read_bytes()
    names = validate_selection(selection, source, gate_bytes, hold_bytes)
    holds = hold_keys(hold_bytes)
    selected = {key_tuple(name) for name in names}
    missing = selected.difference(packages)
    if missing:
        raise ValueError('approved keys absent from pack: ' + ', '.join('%08x-%08x' % k for k in sorted(missing)))
    # Validate the whole cohort before generating any output; unsupported keys
    # do not turn into a silently smaller candidate.
    inputs = {name: identify(packages[key_tuple(name)]) for name in names}
    gate = load_gate(gate_path, selection['quality_gate_sha256'])
    if hasattr(gate, 'HOLD_KEYS'):
        gate.HOLD_KEYS.clear()
        gate.HOLD_KEYS.update(holds)
    result = dict(packages)
    rows = []
    for name in names:
        k = key_tuple(name)
        original = packages[k]
        kind, native, decode, generate, base = inputs[name]
        row = dict(key=name, generator=kind, source_package_sha256=digest(original),
                   before_payload_bytes=len(native.payload), base_level_exact=True)
        if name in holds:
            row.update(verdict='held', reasons=['room-select'])
        elif native.mipmapped:
            row.update(verdict='unchanged', reasons=['already-mipped'])
        else:
            candidate, evidence = generate(original, enabled=True, engine=engine)
            candidate = tpl.canonical_native_crc(candidate)
            checked = ENCODERS[kind][0](candidate)
            unchanged_base(native, checked, decode, base)
            audited = gate.audit((k, candidate))
            if not isinstance(audited, tuple) or len(audited) != 3 or audited[0] != k:
                raise ValueError('quality gate did not audit selected key: ' + name)
            quality = audited[1]
            expected_levels = [native.size >> i for i in range(1, native.size.bit_length())]
            if [x.get('side') for x in quality.get('levels', [])] != expected_levels:
                raise ValueError('quality gate did not inspect every level through 1x1: ' + name)
            if quality.get('verdict') not in ('pass', 'held'):
                raise ValueError('unknown quality verdict for ' + name)
            row.update(verdict=quality['verdict'], reasons=quality.get('reasons', []),
                       quality=quality, generator_evidence=evidence)
            if quality['verdict'] == 'pass':
                result[k] = candidate
        out = result[k]
        out_native = ENCODERS[kind][0](out)
        row.update(output_package_sha256=digest(out), changed=out != original,
                   after_payload_bytes=len(out_native.payload),
                   extra_payload_bytes=len(out_native.payload) - len(native.payload),
                   extra_alloc32_bytes=((len(out_native.payload) + 31) // 32
                                        - (len(native.payload) + 31) // 32) * 32)
        rows.append(row)
    changed = sorted(k for k in packages if packages[k] != result[k])
    if any(result[k] != packages[k] for k in packages.keys() - selected):
        raise ValueError('an unselected package changed')
    # An all-held/no-op candidate retains even source archive padding exactly.
    output = texpack.build(result)[0] if changed else source
    texpack.verify(output)
    if read_pak(output) != result:
        raise ValueError('rebuilt pack member verification failed')
    modules = (tpl, vq, tw, pal4, texpack)
    report.update(output_pack_sha256=digest(output), selected=len(names),
                  changed=len(changed), unchanged=len(packages) - len(changed),
                  changed_keys=['%08x-%08x' % k for k in changed],
                  unselected=len(packages) - len(names),
                  unselected_exact=len(packages) - len(names),
                  extra_payload_bytes=sum(r['extra_payload_bytes'] for r in rows),
                  extra_alloc32_bytes=sum(r['extra_alloc32_bytes'] for r in rows),
                  quality_gate_sha256=digest(gate_bytes), hold_keys_sha256=digest(hold_bytes),
                  selection_canonical_sha256=digest(json.dumps(selection, sort_keys=True, separators=(',', ':')).encode()),
                  implementation_sha256=repository_source_hashes(*modules),
                  quality_gate_dependencies_sha256=repository_source_hashes(gate),
                  rows=rows)
    return output, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', required=True, type=Path)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--quality-gate', type=Path)
    parser.add_argument('--hold-keys', type=Path)
    parser.add_argument('--enable', action='store_true', help='enable reviewed candidate conversion; default OFF')
    parser.add_argument('--engine', choices=('auto', 'python', 'numpy'), default='auto')
    parser.add_argument('--dry-run', action='store_true', help='run encoding and checks, write report only')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.enable and not all((args.selection, args.quality_gate, args.hold_keys)):
        parser.error('--enable requires --selection, --quality-gate and --hold-keys')
    if not args.dry_run and args.out is None:
        parser.error('--out is required unless --dry-run is used')
    inputs = {p.resolve() for p in (args.pack, args.selection, args.quality_gate, args.hold_keys) if p}
    outputs = [args.report] + ([args.out] if args.out and not args.dry_run else [])
    if len({p.resolve() for p in outputs}) != len(outputs):
        parser.error('output pack and report must be different paths')
    for path in outputs:
        if path.resolve() in inputs or path.exists():
            parser.error('use a new output path: ' + str(path))
    selection = json.loads(args.selection.read_text()) if args.enable else None
    output, report = build_candidate(args.pack.read_bytes(), enabled=args.enable,
        selection=selection, gate_path=args.quality_gate,
        hold_bytes=args.hold_keys.read_bytes() if args.enable else None, engine=args.engine)
    report['dry_run'] = args.dry_run
    if args.enable:
        report['selection_file_sha256'] = digest(args.selection.read_bytes())
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        with args.out.open('xb') as stream:
            stream.write(output)
    with args.report.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('enabled', 'members', 'selected', 'changed',
          'unchanged', 'extra_alloc32_bytes', 'output_pack_sha256', 'dry_run')}, sort_keys=True))


if __name__ == '__main__':
    main()

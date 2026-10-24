#!/usr/bin/env python3
"""Verify archive bytes without executing archived helpers or opening game fixtures."""
import argparse
import ast
import hashlib
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def validate(root, manifest, live=False, syntax=False):
    seen = set()
    for row in manifest['copied']:
        rel = pathlib.PurePosixPath(row['path'])
        if rel.is_absolute() or '..' in rel.parts or rel.parts[:1] != ('c-side',):
            raise ValueError('unsafe archive path')
        if str(rel) in seen:
            raise ValueError('duplicate archive path')
        seen.add(str(rel))
        path = root / rel
        if path.is_symlink() or not path.is_file() or path.resolve().is_relative_to(root.resolve()) is False:
            raise ValueError('missing or aliased archive file')
        data = path.read_bytes()
        if len(data) != row['bytes'] or digest(data) != row['sha256']:
            raise ValueError('archive bytes changed: ' + str(rel))
        if live and pathlib.Path(row['origin']).read_bytes() != data:
            raise ValueError('live source changed: ' + row['origin'])
        if syntax:
            if path.suffix == '.py':
                ast.parse(data, filename=str(rel))
            elif path.suffix == '.json':
                json.loads(data)
            elif path.suffix == '.sh':
                subprocess.run(['bash', '-n', str(path)], check=True, capture_output=True)
    actual = {str(p.relative_to(root).as_posix()) for p in (root / 'c-side').rglob('*') if p.is_file()}
    if actual != seen:
        raise ValueError('archive file set differs')
    return len(seen)

def controls():
    # A preservation verifier must detect corruption, omissions, additions and escaping paths.
    with tempfile.TemporaryDirectory(prefix='worldemit-archive-controls-', dir='/dev/shm') as tmp:
        root = pathlib.Path(tmp)
        (root / 'c-side').mkdir()
        target = root / 'c-side/control.py'
        data = b'assert True\n'
        target.write_bytes(data)
        row = {'path': 'c-side/control.py', 'bytes': len(data), 'sha256': digest(data)}
        manifest = {'copied': [row]}
        assert validate(root, manifest) == 1
        cases = 0
        def rejects(m):
            nonlocal cases
            try:
                validate(root, m)
            except (ValueError, FileNotFoundError):
                cases += 1
            else:
                raise AssertionError('negative accepted')
        target.write_bytes(data + b'# changed\n')
        rejects(manifest)
        target.write_bytes(data)
        rejects({'copied': []})
        rejects({'copied': [row, row]})
        rejects({'copied': [dict(row, path='../escape')]})
        (root / 'c-side/extra.py').write_bytes(b'pass\n')
        rejects(manifest)
        return {'positive': 1, 'negative': cases}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-source', action='store_true')
    parser.add_argument('--syntax', action='store_true')
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    count = validate(ROOT, manifest, args.live_source, args.syntax)
    result = {'status': 'PASS', 'files': count, 'archive_bytes': sum(r['bytes'] for r in manifest['copied']),
              'source': manifest['base_source'], 'live_source_compared': args.live_source,
              'syntax_only': args.syntax, 'archived_helpers_executed': False, 'private_fixtures_opened': False}
    if args.controls:
        result['verifier_controls'] = controls()
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()

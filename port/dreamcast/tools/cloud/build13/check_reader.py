#!/usr/bin/env python3
"""Actual split reader and source-extracted R4SG admission controls.

Uses the public genuine-builder fixtures. Malformed bodies have recomputed
checksums unless the checksum itself is under test. The file-open/owner
lifecycle is outside this host adapter; actual bounded reader, source-header
predicate, production CRC and loader R4SG gate are executed unchanged.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
STATIC = DC/'game/platform/native_static.cpp'
HEADER = DC/'room/scenery_record_split.hpp'
spec = importlib.util.spec_from_file_location('split_reader_prior', HERE.parent/'build5/check_geometry.py')
prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)

def sha(data): return hashlib.sha256(data).hexdigest()

def group_gate(raw):
    start = raw.index('std::uint32_t w[8]={};', raw.index('// PS2_STRIP_GROUPS: tools/ps2_strip_groups.py'))
    end = raw.index('        if(gwhy){if(gb)', start)
    return raw[start:end]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixtures', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--sanitize', action='store_true')
    a = ap.parse_args(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    watched = [STATIC, HEADER, DC/'room/instanced_mesh.hpp', Path(__file__), HERE/'fixture_reader.cpp.in']
    frozen = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in watched}
    raw = STATIC.read_text(); values = {'ROOT': str(ROOT), 'CRC': prior.function(raw, 'std::uint32_t ps2_crc32('), 'GROUP_GATE': group_gate(raw)}
    text = (HERE/'fixture_reader.cpp.in').read_text()
    for k, v in values.items(): text = text.replace('@'+k+'@', v)
    source = out/'reader.cpp'; source.write_text(text)
    (out/'shim/kos').mkdir(parents=True)
    (out/'shim/kos/fs.h').write_text('#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n')
    binary = out/'reader'
    command = ['g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-DRE4DC_SCENERY_RECORD_SPLIT=1',
               '-I'+str(out/'shim'), str(source), '-o', str(binary)]
    env = dict(os.environ)
    if a.sanitize:
        command[3:3] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        env['ASAN_OPTIONS'] = 'detect_leaks=0'
    run = subprocess.run(command, capture_output=True, env=env)
    (out/'compile.log').write_bytes(run.stdout+run.stderr); assert run.returncode == 0, run.stderr.decode()
    fixtures = json.loads(a.fixtures.read_text())['fixtures']; observations = []
    def check(label, mesh, original, policy, groups, expected=0, message=None):
        args = [binary, mesh, original, policy, groups]
        run = subprocess.run([str(x) for x in args], capture_output=True, env=env)
        assert run.returncode == expected, (label, run.returncode, expected, run.stderr)
        if message: assert message.encode() in run.stderr, (label, run.stderr)
        observations.append(dict(label=label, expected=expected, stderr=run.stderr.decode(), stdout=run.stdout.decode(),
            mesh_sha256=sha(Path(mesh).read_bytes()), groups_sha256=sha(Path(groups).read_bytes())))
    for f in fixtures:
        for kind in ('ordinary', 'split'):
            check(str(f['limit'])+'-'+kind, f[kind], f['ordinary'], f['policy'], f[kind+'_groups'])
    f = fixtures[1]; good = Path(f['split']).read_bytes(); h = struct.unpack_from('<4s19I', good)
    lod = struct.unpack_from('<8I', good, 80); mutations = []
    for name, at, fmt, value, code, message in (
        ('bounds-offset', 68, 'I', h[17]+4, 1, 'split section layout'),
        ('meshlet-capacity', 24, 'I', 65537, 1, 'split meshlet id capacity'),
        ('color-mode', 64, 'I', 0, 1, 'split header'),
        ('extension-header', 108, 'I', 32, 1, 'split header'),
        ('emit-count', h[12]+12, 'H', 257, 1, 'split emit range'),
        ('source-crc', 72, 'I', h[18]^1, 4, None),
        ('source-extent', 76, 'I', h[19]+32, 4, None)):
        data = bytearray(good); struct.pack_into('<'+fmt, data, at, value)
        struct.pack_into('<I', data, 12, zlib.crc32(data[80:])); mutations.append((name, data, code, message))
    data = bytearray(good); data[h[13]+6] ^= 1; mutations.append(('body-crc', data, 2, None))
    # Preserve actual indexed references while moving a declared part pool
    # base into its predecessor: the conservative generic-v3 rule must refuse.
    for li in range(h[6]):
        e = struct.unpack_from('<IIIHH', good, h[12]+16*li)
        if e[4]&0x8000 and e[0]>0:
            data = bytearray(good); struct.pack_into('<I', data, h[12]+16*li, e[0]-1)
            refs = struct.unpack_from('<'+'H'*e[3], good, h[14]+e[1])
            if max(refs)<65535:
                struct.pack_into('<'+'H'*e[3], data, h[14]+e[1], *(v+1 for v in refs))
                struct.pack_into('<I', data, 12, zlib.crc32(data[80:])); mutations.append(('part-pool', data, 1, 'split part pool')); break
    assert any(x[0]=='part-pool' for x in mutations)
    data = bytearray(good)
    struct.pack_into('<I', data, lod[2]+4, 2)
    data[lod[3]+20:lod[3]+40] = data[lod[3]:lod[3]+20]
    struct.pack_into('<I', data, 12, zlib.crc32(data[80:])); mutations.append(('pick-capacity', data, 1, 'split pick capacity'))
    for name, data, code, message in mutations:
        path = out/(name+'.re4mesh'); path.write_bytes(data)
        check(name, path, f['ordinary'], f['policy'], f['split_groups'], code, message)
    groups = Path(f['split_groups']).read_bytes(); gh = struct.unpack_from('<8I', groups)
    # The first emitted group contains a nontrivial strip and box in this
    # genuine-builder fixture. Each malformed sidecar keeps a valid CRC.
    g0 = struct.unpack_from('<6HHBB', groups, 32); assert g0[6]>4 and g0[7]<g0[8]
    group_mutations = []
    e = struct.unpack_from('<IIIHH', good, h[12])
    for name, at, fmt, value, message in (
        ('sg-strip-boundary', 44, 'H', g0[6]-1, 'split group strip boundary'),
        ('sg-extent', 44, 'H', e[2]+1, 'split group extent'),
        ('sg-corner-range', 46, 'B', g0[7]+1, 'split group corner range'),
        ('sg-enclosure', 38, 'H', g0[0], 'split group enclosure'),
        ('sg-binding', 16, 'I', h[3]^1, 'header')):
        data = bytearray(groups); struct.pack_into('<'+fmt, data, at, value)
        struct.pack_into('<I', data, 28, zlib.crc32(data[32:])); group_mutations.append((name, data, message))
    for name, data, message in group_mutations:
        path = out/(name+'.r4sg'); path.write_bytes(data)
        check(name, f['split'], f['ordinary'], f['policy'], path, 5, message)
    assert frozen == {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in watched}, 'source changed during reader gate'
    report = dict(status='PASS', scope=__doc__, sanitized=a.sanitize, source_sha256=frozen,
        extracted_sha256={k:sha(v.encode()) for k,v in values.items() if k!='ROOT'},
        fixture_manifest_sha256=sha(a.fixtures.read_bytes()), observations=observations,
        group_malformed_crc_recomputed=True, command=command)
    (out/'reader-controls.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status='PASS', cases=len(observations), sanitized=a.sanitize)))

if __name__ == '__main__': main()

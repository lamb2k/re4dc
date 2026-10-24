#!/usr/bin/env python3
"""Source-extracted host controls for captured PS2 PVS affine provenance.

All compiler outputs live in /dev/shm. This is not a target-image check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def function(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def extract(native, runtime):
    start = native.index('namespace dyn {')
    end = native.index('\n}\n#endif', native.index('unsigned query(unsigned id)', start)) + 2
    dyn = native[start:end]
    sel_start = native.index('#if RE4DC_PS2_WORLD_DYNAMIC\n        const float* affine=pl.affine;')
    sel_end = native.index('\n#endif', native.index('const unsigned pvs_source_placement=', sel_start)) + len('\n#endif')
    select = native[sel_start:sel_end]
    assignments = re.findall(r'\b(?:x\.placement|d\.pvs_placement)=[^;]+;', native[sel_end:])
    if len(assignments) != 3:
        raise AssertionError(f'expected three source assignment paths, got {assignments}')
    # Exact assignment text is compiled, rather than asserting the patched RHS.
    queue = [a for a in assignments if a.startswith('x.')]
    direct = [a for a in assignments if a.startswith('d.')]
    return {
        'DYN': dyn,
        'INTACT': function(native, 'extern "C" int re4dc_ps2_placements_intact('),
        'SOURCES': function(runtime, 'bool sources()'),
        'SYNC': function(runtime, 'bool sync(unsigned epoch[2])'),
        'OBSERVE': function(runtime, 'extern "C" void re4dc_pvs23_observe('),
        'COMMIT': function(runtime, 'extern "C" void re4dc_pvs23_commit('),
        'CUT': function(runtime, 'bool pvs::can_cut('),
        'FINISH': function(native, 'void pvs_finish(bool success)'),
        'OBSERVED': function(native, 'void pvs_observed('),
        'RESTART': function(native, '[[gnu::always_inline]] void chunk_restart()'),
        'SELECT': select,
        'QUEUE_SELECT': queue[0], 'QUEUE_LEGACY': queue[1], 'DIRECT': direct[0],
        'REPLAY': re.search(r'e\.pvs_placement=x\.placement;', native).group(),
    }


def preprocess_off(native, base, work):
    # Full translation-unit directive/text comparison. Include directives are
    # removed identically so unavailable SDK headers cannot affect the check.
    # Every RE4DC feature condition defaults off except each explicit matrix.
    def pp(source, knobs):
        source = re.sub(r'^\s*#\s*include[^\n]*', '', source, flags=re.M)
        names = sorted(set(re.findall(r'\bRE4DC_[A-Z0-9_]+\b', source)))
        defines = ''.join(f'#define {n} {knobs.get(n, 0)}\n' for n in names)
        result = subprocess.run(['g++', '-E', '-P', '-x', 'c++', '-'], input=defines+source,
                                text=True, capture_output=True, check=True)
        return result.stdout
    outputs = []
    for dynamic in (0, 1):
        for lean in (0, 1):
            for select in (0, 1):
                knobs = dict(RE4DC_PS2_WORLD_DYNAMIC=dynamic, RE4DC_PS2_WORLD_LEAN=lean,
                             RE4DC_SCENERY_SELECT_ONLY=select, RE4DC_PS2_PVS=0,
                             RE4DC_PS2_WORLD_MESH=1, RE4DC_SCENERY_CHUNK=1)
                before, after = pp(base, knobs), pp(native, knobs)
                if before != after:
                    raise AssertionError(f'PVS-off source preprocessing changed: {knobs}')
                outputs.append({'dynamic': dynamic, 'lean': lean, 'select_only': select,
                                'sha256': hashlib.sha256(after.encode()).hexdigest()})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--base', default='831a2115e78e762f5a14886e3b1a4b17dbf9fab1')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[4]
    platform = repo / 'port/dreamcast/game/platform'
    native_path = platform / 'native_static.cpp'
    native = native_path.read_text()
    runtime = (platform / 'include/pvs23_runtime.inc').read_text()
    template = (here / 'fixture_queued_affine.cpp.in').read_text()
    excerpts = extract(native, runtime)
    # Header is copied whole, so Panel, Receipts, numeric and panel_sent are
    # production definitions. No private game geometry enters the fixture.
    header = (platform / 'include/pvs23_proof.hpp').read_text()
    generated = template.replace('@PROOF_HEADER@', '#include "pvs23_proof.hpp"')
    for key, value in excerpts.items():
        generated = generated.replace('@' + key + '@', value)
    if re.search(r'@[A-Z_]+@', generated):
        raise AssertionError('unexpanded fixture placeholder')
    base = subprocess.check_output(['git', 'show', args.base+':port/dreamcast/game/platform/native_static.cpp'], cwd=repo, text=True)
    results = {'native_sha256': hashlib.sha256(native.encode()).hexdigest(),
               'runtime_sha256': hashlib.sha256(runtime.encode()).hexdigest(),
               'proof_header_sha256': hashlib.sha256(header.encode()).hexdigest(),
               'fixture_sha256': hashlib.sha256(generated.encode()).hexdigest(),
               'compiler': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
               'base': args.base, 'host_only': True, 'runs': []}
    with tempfile.TemporaryDirectory(prefix='queued-affine-', dir='/dev/shm') as tmp:
        work = Path(tmp)
        (work / 'pvs23_proof.hpp').write_text(header)
        results['pvs0_source_preprocess'] = preprocess_off(native, base, work)
        for lean in (0, 1):
            for root in (0, 1):
                source = work / 'fixture.cpp'
                source.write_text(generated)
                exe = work / 'fixture'
                subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                                f'-DRE4DC_PS2_WORLD_LEAN={lean}', f'-DRE4DC_PS2_WORLD_ROOT_POSE={root}',
                                str(source), '-o', str(exe)], check=True)
                output = subprocess.check_output([str(exe)], text=True)
                results['runs'].append({'lean': lean, 'root_pose': root, 'output': output.strip()})
        # Each independent old-i regression must compile but fail its controls.
        results['mutations'] = []
        for key in ('QUEUE_SELECT', 'QUEUE_LEGACY', 'DIRECT'):
            mutated = template.replace('@PROOF_HEADER@', '#include "pvs23_proof.hpp"')
            for name, value in excerpts.items():
                if name == key:
                    value = value.replace('pvs_source_placement', 'i')
                mutated = mutated.replace('@' + name + '@', value)
            source.write_text(mutated)
            subprocess.run(['g++', '-std=c++17', '-O2', '-DRE4DC_PS2_WORLD_LEAN=1',
                            '-DRE4DC_PS2_WORLD_ROOT_POSE=1', str(source), '-o', str(exe)], check=True)
            run = subprocess.run([str(exe)], text=True, capture_output=True)
            if run.returncode == 0:
                raise AssertionError('old-i mutation escaped: ' + key)
            results['mutations'].append({'path': key, 'exit': run.returncode, 'output': run.stderr.strip()})
    result = json.dumps(results, indent=2) + '\n'
    print(result, end='')
    if args.evidence:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / 'queued-affine-host.json').write_text(result)
        (args.evidence / 'queued-affine-excerpts.json').write_text(json.dumps(excerpts, indent=2)+'\n')


if __name__ == '__main__':
    main()

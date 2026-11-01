#!/usr/bin/env python3
"""Reproduce the opt-in index-layout adapter's public host and Blender gates.

Requires the official pinned Blender archive and a fresh output directory.
Reconstructs the old bridge from an immutable git baseline. Receipts contain
commands, complete package hashes, actual host process timing/RSS and limits.
No game assets, console model or runtime build is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time

import blender_bridge as bridge
import fixtures
import index_layout_fixtures as layout_fixtures
import package as p
import sidecars
import validate as original

HERE, REPO = original.HERE, original.REPO
REL = HERE.relative_to(REPO)
EXTRA_DEPENDENCIES = [p.TOOLS/'ps2_world_append.py', p.TOOLS/'ps2_strip_groups.py']


def hashes():
    paths = set(HERE.glob('*.py')) | set(original.DEPENDENCIES+EXTRA_DEPENDENCIES)
    return {path.relative_to(REPO).as_posix(): original.file_sha(path) for path in sorted(paths)}


def run(command, work, name, env=None, expected_error=None):
    """Wait4 gives measured child CPU/RSS; never infer success from a log token."""
    log = work/(name+'.log')
    start = time.perf_counter()
    command = list(map(str, command))
    with log.open('wb') as output:
        proc = subprocess.Popen(command, cwd=REPO, stdout=output,
                                stderr=subprocess.STDOUT, env=env)
        _, status, usage = os.wait4(proc.pid, 0)
        proc.returncode = os.waitstatus_to_exitcode(status)
    result = dict(command=command, exit_code=proc.returncode,
        elapsed_seconds=round(time.perf_counter()-start, 6),
        user_seconds=round(usage.ru_utime, 6), system_seconds=round(usage.ru_stime, 6),
        peak_resident_kib=usage.ru_maxrss, log_sha256=original.file_sha(log))
    if expected_error is None:
        p.require(proc.returncode == 0, name+' failed:\n'+log.read_text(errors='replace')[-12000:])
    else:
        content = log.read_text(errors='replace')
        p.require(proc.returncode != 0 and expected_error in content,
                  name+' did not reject for '+repr(expected_error)+':\n'+content[-12000:])
        result['expected_rejection'] = expected_error
    return result


def extract_baseline(work, baseline):
    """Extract only public code from Git, with paths inspected before writing."""
    destination = work/'baseline-source'
    destination.mkdir()
    archive = work/'baseline-source.tar'
    command = ['git', 'archive', baseline, 'port/dreamcast/tools', 'port/dreamcast/room']
    with archive.open('wb') as out:
        subprocess.run(command, cwd=REPO, stdout=out, check=True)
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            path = Path(member.name)
            p.require(not path.is_absolute() and '..' not in path.parts and
                      not member.isdev(), 'unsafe baseline archive entry')
        source.extractall(destination, filter='data')
    return destination, dict(command=command, archive_sha256=original.file_sha(archive),
        entries=len(members), baseline_commit=baseline,
        scope='Original tracked public tools/room code, no private fixture or saved blend')


def old_decode_probe(old_here, source, output, work, name):
    # A separate interpreter prevents current modules in sys.modules from
    # contaminating the historical codec or changing its original rejection.
    script = work/'baseline-decode.py'
    if not script.exists():
        script.write_text('''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import package as p
root=Path(sys.argv[2])
try:
 d=p.decode((root/'ps2-world.re4mesh').read_bytes(),(root/'ps2-world.r4pw').read_bytes())
 r=dict(accepted=True,document=d)
except ValueError as e:r=dict(accepted=False,error=str(e))
Path(sys.argv[3]).write_text(json.dumps(r,sort_keys=True,allow_nan=False)+'\\n')
''')
    result = run([sys.executable, script, old_here, source, output], work, name)
    return json.loads(output.read_text()), result


def file_records(files):
    return {name: dict(bytes=len(blob), sha256=p.sha(blob))
            for name, blob in sorted(files.items())}


def assert_bundle(source, destination, files):
    p.require(sidecars.inventory(source) == files, 'source bundle changed')
    p.require(sidecars.inventory(destination) == files, 'complete exported bundle differs')


def target_identity(baseline):
    changed = original.git('diff', '--name-only', baseline).decode().splitlines()
    allowed = [name for name in changed if name.startswith(REL.as_posix()+'/') or
               (name.startswith('port/dreamcast/docs/cloud/') and name.endswith('.md'))]
    p.require(allowed == changed, 'runtime/build or unrelated tracked change: '+repr(changed))
    stable = {}
    for path in original.DEPENDENCIES+EXTRA_DEPENDENCIES:
        name = path.relative_to(REPO).as_posix()
        original_data = original.git('show', baseline+':'+name)
        p.require(original_data == path.read_bytes(), 'dependency changed '+name)
        stable[name] = p.sha(original_data)
    return dict(baseline_commit=baseline, changed_tracked_paths=changed,
        only_tool_and_report_paths_changed=True, existing_dependencies_byte_identical=stable,
        basis='All tracked paths outside the explicit tool directory and cloud Markdown reports match baseline; '
              'no runtime, build or default pipeline integration. No target rebuild is claimed.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--blender', type=Path, required=True)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    ap.add_argument('--baseline', default='9c2c83dba00ba219fbb135503aa508975fe4855c')
    args = ap.parse_args()
    for name in ('blender', 'archive', 'work', 'receipt'):
        setattr(args, name, getattr(args, name).resolve())
    p.require(not args.work.exists(), 'refuse existing validation directory')
    p.require(not args.receipt.exists(), 'refuse existing receipt')
    p.require(original.file_sha(args.archive) == original.ARCHIVE_SHA256, 'archive SHA256 pin')
    binary = original.file_sha(args.blender)
    p.require(binary == '2de8d1e2d358e52f88ecb18a31439a4f12da5858c82218e91fa8b4e6cdb365f6',
              'Blender executable SHA256 pin')
    version = subprocess.check_output([str(args.blender), '--background', '--version']).decode()
    p.require('Blender 4.4.3' in version and 'build hash: 802179c51ccc' in version, 'Blender version/build pin')
    baseline = original.git('rev-parse', args.baseline).decode().strip()
    source_before = hashes()
    args.work.mkdir(parents=True)
    work = args.work
    env = dict(os.environ, BLENDER_USER_CONFIG=str(work/'blender-config'),
               BLENDER_USER_SCRIPTS=str(work/'blender-scripts'))
    common = [args.blender, '--background', '--factory-startup', '--disable-autoexec',
              '--python-exit-code', '1']

    # Preserve the complete historical public gate in the current default mode.
    original_receipt = work/'original-gate-receipt.json'
    original_process = run([sys.executable, HERE/'validate.py', '--blender', args.blender,
        '--archive', args.archive, '--work', work/'original-gate', '--receipt', original_receipt,
        '--baseline', baseline], work, 'original-gate', env)
    old_root, old_source = extract_baseline(work, baseline)
    old_here = old_root/REL
    host_path = work/'layout-host.json'
    host_process = run([sys.executable, HERE/'test_index_layout.py', '--report', host_path],
                       work, 'layout-host')
    host = json.loads(host_path.read_text())
    canonical, new_suites, negatives, adoptions = [], [], [], []
    inputs = {}
    canonical_makers = [('complete_v2', fixtures.complete_files),
                        ('legacy_v1', lambda: fixtures.complete_files(True)),
                        ('existing_converter', fixtures.converter_files)]

    def command(action, source, blend, out=None, mode=None, script=None):
        result = [*common, '--python', script or HERE/'blender_bridge.py', '--', action,
                  '--source', source, '--blend', blend]
        if out is not None:
            result += ['--out', out]
        if mode is not None:
            result += ['--preserve-index-layout', str(mode)]
        return result

    for name, make in canonical_makers:
        files = make()
        source = work/(name+'-input')
        fixtures.write(source, files)
        inputs[name] = (source, files)
        old_doc, old_probe = old_decode_probe(old_here, source, work/(name+'-old-doc.json'),
                                            work, name+'-baseline-decode')
        p.require(old_doc['accepted'], 'historical canonical source was refused')
        before = json.dumps(old_doc['document'], sort_keys=True, allow_nan=False)
        docs = []
        for mode in (None, 0):
            d = p.decode(files['ps2-world.re4mesh'], files['ps2-world.r4pw']) if mode is None else \
                p.decode(files['ps2-world.re4mesh'], files['ps2-world.r4pw'], mode)
            p.require(json.dumps(d, sort_keys=True, allow_nan=False) == before,
                      'historical complete decoded document changed')
            docs.append(dict(mode='absent' if mode is None else mode, complete_document_identity=True,
                             document_sha256=p.sha(before.encode())))
        old_blend = work/(name+'-baseline.blend')
        old_import = run(command('import', source, old_blend, script=old_here/'blender_bridge.py'),
                         work, name+'-baseline-import', env)
        compatibility = []
        for mode in (None, 0):
            tag = 'absent' if mode is None else str(mode)
            destination = work/(name+'-old-blend-current-'+tag)
            result = run(command('export', source, old_blend, destination, mode), work,
                         name+'-old-blend-export-'+tag, env)
            assert_bundle(source, destination, files)
            compatibility.append(dict(mode=tag, process=result, full_bundle_identity=True))
        arms = []
        for mode in (None, 0, 1):
            tag = 'absent' if mode is None else str(mode)
            blend, out = work/(name+'-'+tag+'.blend'), work/(name+'-output-'+tag)
            imported = run(command('import', source, blend, mode=mode), work,
                           name+'-import-'+tag, env)
            exported = run(command('export', source, blend, out, mode), work,
                           name+'-export-'+tag, env)
            assert_bundle(source, out, files)
            arms.append(dict(mode=tag, import_process=imported, export_process=exported,
                             blend_bytes=blend.stat().st_size, full_bundle_identity=True))
            adoptions.append(out/'ps2-world.re4mesh')
        canonical.append(dict(name=name, files=file_records(files), input_bytes=sum(map(len, files.values())),
            decoded_document_controls=docs, baseline_decode_process=old_probe,
            baseline_import_process=old_import, old_blend_current_exports=compatibility,
            current_import_export_arms=arms))

    for name, make in layout_fixtures.suites():
        started = time.perf_counter()
        files = make()
        generated_seconds = time.perf_counter()-started
        source, blend, out = work/(name+'-input'), work/(name+'.blend'), work/(name+'-output')
        fixtures.write(source, files)
        inputs[name] = (source, files)
        historical, old_probe = old_decode_probe(old_here, source, work/(name+'-old-doc.json'),
                                                work, name+'-baseline-refusal')
        p.require(not historical['accepted'], 'fixture does not reproduce the old refusal: '+name)
        for mode in (None, 0):
            tag = 'absent' if mode is None else str(mode)
            try:
                if mode is None:
                    p.decode(files['ps2-world.re4mesh'], files['ps2-world.r4pw'])
                else:
                    p.decode(files['ps2-world.re4mesh'], files['ps2-world.r4pw'], mode)
            except ValueError as error:
                p.require(str(error) == historical['error'], 'default rejection changed')
            else:
                raise AssertionError('default mode admitted '+name)
            bad_blend = work/(name+'-refused-'+tag+'.blend')
            result = run(command('import', source, bad_blend, mode=mode), work,
                         name+'-refused-import-'+tag, env, historical['error'])
            p.require(not bad_blend.exists(), 'failed import created blend')
            negatives.append(dict(name=name+'-default-import-'+tag, process=result,
                                  no_destination_created=True))
        imported = run(command('import', source, blend, mode=1), work, name+'-import', env)
        exported = run(command('export', source, blend, out, 1), work, name+'-export', env)
        assert_bundle(source, out, files)
        adoptions.append(out/'ps2-world.re4mesh')
        d = p.decode(files['ps2-world.re4mesh'], files['ps2-world.r4pw'], True)
        new_suites.append(dict(name=name, files=file_records(files), input_bytes=sum(map(len, files.values())),
            output_bytes=sum(map(len, sidecars.inventory(out).values())), blend_bytes=blend.stat().st_size,
            fixture_build_seconds=round(generated_seconds, 6), index_layout=d['index_layout'],
            counts={key:len(d[key]) for key in ('meshes','parts','meshlets','vertices','placements','clusters','levels')},
            baseline_refusal=historical['error'], baseline_probe=old_probe,
            import_process=imported, export_process=exported, complete_bundle_identity=True))
        for mode in (None, 0):
            tag = 'absent' if mode is None else str(mode)
            destination = work/(name+'-refused-export-'+tag)
            result = run(command('export', source, blend, destination, mode), work,
                         name+'-refused-export-'+tag, env, historical['error'])
            p.require(not destination.exists(), 'failed export created output')
            negatives.append(dict(name=name+'-default-export-'+tag, process=result,
                                  no_destination_created=True))

    source, files = inputs['complete_v2']
    for action in ('import', 'export'):
        blend = work/'invalid-option.blend' if action == 'import' else work/'complete_v2-1.blend'
        out = None if action == 'import' else work/'invalid-option-output'
        result = run(command(action, source, blend, out, 2), work, 'invalid-option-'+action,
                     env, 'invalid choice: 2')
        p.require(not (blend if action == 'import' else out).exists(), 'invalid option created output')
        negatives.append(dict(name='invalid-option-'+action, process=result, no_destination_created=True))
    for imported, exported in ((1, None), (1, 0), (0, 1)):
        tag = str(imported)+'-to-'+('absent' if exported is None else str(exported))
        out = work/('mode-mismatch-'+tag)
        result = run(command('export', source, work/('complete_v2-'+str(imported)+'.blend'), out, exported),
                     work, 'mode-mismatch-'+tag, env, 'property r4_schema')
        p.require(not out.exists(), 'mode mismatch created output')
        negatives.append(dict(name='mode-mismatch-'+tag, process=result, no_destination_created=True))
    blend = work/'complete_v2-1.blend'
    before_blend = original.file_sha(blend)
    result = run(command('import', source, blend, mode=1), work, 'refuse-overwrite-blend', env,
                 'refuse to overwrite blend')
    p.require(original.file_sha(blend) == before_blend, 'refused import changed existing blend')
    negatives.append(dict(name='no-overwrite-blend', process=result, existing_destination_unchanged=True))
    destination = work/'complete_v2-output-1'
    result = run(command('export', source, blend, destination, 1), work, 'refuse-overwrite-output',
                 env, 'new output directory required')
    assert_bundle(source, destination, files)
    negatives.append(dict(name='no-overwrite-output', process=result, existing_destination_unchanged=True))

    mutations_path = work/'layout-blender-mutations.json'
    mutation_process = run([*common, '--python', HERE/'blender_index_layout_controls.py', '--',
        '--source', source, '--other-source', inputs['legacy_v1'][0], '--blend', blend,
        '--report', mutations_path], work, 'layout-blender-mutations', env)
    adoption_work = work/'current-runtime-adoption'
    adoption_work.mkdir()
    adoption = original.host_adoption(adoption_work, adoptions)
    adoption['complete_exported_meshes'] = len(adoptions)
    for source, files in inputs.values():
        p.require(sidecars.inventory(source) == files, 'input changed during gate')
    target = target_identity(baseline)
    p.require(source_before == hashes(), 'source files changed during gate')
    p.require(binary == original.file_sha(args.blender), 'Blender executable changed during gate')
    report = dict(status='PASS_PUBLIC_INDEX_LAYOUT_IDENTITY_ONLY', baseline_commit=baseline,
        source_sha256=source_before,
        blender=dict(version='4.4.3', build_hash='802179c51ccc', archive_url=original.ARCHIVE_URL,
            archive_sha256=original.ARCHIVE_SHA256, executable_sha256=binary, pre_post_identity=True),
        host_platform=dict(system=platform.system(), machine=platform.machine(), python=platform.python_version(),
            timing_scope='Measured host process wall/user/system and peak KiB RSS; not Dreamcast performance'),
        original_gate=dict(process=original_process, receipt=json.loads(original_receipt.read_text())),
        baseline_source=old_source, canonical_suites=canonical, index_layout_suites=new_suites,
        host_layout_controls=dict(process=host_process, **host),
        cli_negative_controls=negatives, cli_negative_control_count=len(negatives),
        blender_layout_controls=dict(process=mutation_process, receipt=json.loads(mutations_path.read_text())),
        runtime_host_admission=adoption, runtime_build_source_identity=target,
        source_and_input_pre_post_identity=True,
        runtime_delta=dict(warm_i_cycles=0, cold_i_cycles=0, loads=0, stores=0,
            demanded_32byte_lines=0, executable_bytes=0, static_stack_bytes=0, main_ram_bytes=0,
            vram_bytes=0, MODELLED_whole_frame_delta_ms=0.0,
            basis='Architectural deduction from unchanged runtime/build inputs and byte-identical accepted '
                  'packages. No target rebuild, opcode run or performance measurement is claimed.'),
        limits=['No private r101 admission or full-room Blender scale claim.',
                'No geometry/look/STRICT/PVS/lost-part or console qualification.',
                'Unknown formats, nonzero holes and overlapping index spans still refuse.',
                'Policy provenance and remapped-policy companion handling are separate contracts.'])
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(status=report['status'], canonical_suites=len(canonical),
        index_layout_roundtrips=len(new_suites), cli_negative_controls=len(negatives),
        layout_host_test_methods=host['test_methods'],
        blender_on_mode_mutations=report['blender_layout_controls']['receipt']['total_controls'],
        receipt=str(args.receipt)), sort_keys=True))


if __name__ == '__main__':
    main()

"""Actual bpy mutations for the explicit index-layout identity scene.

The existing 43 controls run unchanged through a test-only ON-mode loader.
Additional controls target the new metadata and independent-source boundary.
This file is a validation harness, not part of the importer or runtime.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_bridge as bridge
import blender_controls
import package as p
import sidecars


def main():
    import bpy
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--other-source', type=Path, required=True)
    ap.add_argument('--blend', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    bridge.check(bpy.app.version == bridge.PIN_VERSION and
                 bpy.app.build_hash.decode() == bridge.PIN_HASH, 'pinned Blender')
    doc, files = bridge.load_bundle(args.source, True)
    other_doc, other_files = bridge.load_bundle(args.other_source, True)
    p.require(sidecars.hashes(files) != sidecars.hashes(other_files),
              'source-context control must use a distinct, valid bundle')

    # Reuse every original mutation without modifying production/default code.
    legacy_report = args.report.with_name(args.report.stem+'-legacy.json')
    old_loader, old_argv = bridge.load_bundle, sys.argv
    try:
        bridge.load_bundle = lambda folder: old_loader(folder, True)
        sys.argv = [str(Path(blender_controls.__file__)), '--', '--source', str(args.source),
                    '--blend', str(args.blend), '--report', str(legacy_report)]
        blender_controls.main()
    finally:
        bridge.load_bundle, sys.argv = old_loader, old_argv
    legacy = json.loads(legacy_report.read_text())

    def aux(change):
        value = json.loads(bpy.context.scene['r4_aux'])
        change(value)
        bpy.context.scene['r4_aux'] = bridge.js(value)

    def record(index, value, name='draw.000001.000000'):
        ob = bpy.data.objects[name]
        row = json.loads(ob['r4_record'])
        row[index] = value
        ob['r4_record'] = bridge.js(row)

    def command(change, name='draw.000001.000000'):
        ob = bpy.data.objects[name]
        value = json.loads(ob['r4_commands'])
        change(value)
        ob['r4_commands'] = bridge.js(value)

    def source_hash():
        value = json.loads(bpy.context.scene['r4_sources'])
        value['ps2-world.re4mesh'] = '0'*64
        bpy.context.scene['r4_sources'] = bridge.js(value)

    controls = [
        ('layout-missing', lambda: aux(lambda a: a.pop('index_layout'))),
        ('layout-extent', lambda: aux(lambda a: a['index_layout'].__setitem__('index_bytes',
                                      a['index_layout']['index_bytes']+4))),
        ('layout-extent-negative', lambda: aux(lambda a: a['index_layout'].__setitem__('index_bytes', -1))),
        ('layout-extent-type', lambda: aux(lambda a: a['index_layout'].__setitem__('index_bytes', '66'))),
        ('layout-extra-field', lambda: aux(lambda a: a['index_layout'].__setitem__('raw', '00'))),
        ('schema-old-mode', lambda: bpy.context.scene.__setitem__('r4_schema', p.SCHEMA)),
        ('schema-missing', lambda: bpy.context.scene.__delitem__('r4_schema')),
        ('first-strip', lambda: record(1, doc['meshlets'][0][1]+4)),
        ('strip-byte-count', lambda: record(2, doc['meshlets'][0][2]+1)),
        ('strip-command-order', lambda: command(lambda c: c['strips'].reverse())),
        ('strip-command-index', lambda: command(lambda c: c['strips'][0].__setitem__(0, 1))),
        ('indexed-pool', lambda: command(lambda c: c['pool'].__setitem__(0, 1),
                                          'draw.000001.000001')),
        ('source-hash', source_hash),
    ]
    results = []
    for name, mutate in controls:
        bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False, use_scripts=False)
        mutate()
        try:
            rebuilt = bridge.validate_scene(bpy, doc, files)
            sidecars.rebuild(files, rebuilt, p.serialize_mesh(rebuilt), p.serialize_policy(rebuilt))
        except ValueError as error:
            results.append(dict(control=name, rejected=True, reason=str(error)))
        else:
            raise AssertionError('layout mutation escaped validator: '+name)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False, use_scripts=False)
    try:
        bridge.validate_scene(bpy, other_doc, other_files)
    except ValueError as error:
        results.append(dict(control='different-valid-independent-source', rejected=True,
                            reason=str(error)))
    else:
        raise AssertionError('different valid source was accepted')
    bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False, use_scripts=False)
    rebuilt = bridge.validate_scene(bpy, doc, files)
    p.require(sidecars.rebuild(files, rebuilt, p.serialize_mesh(rebuilt),
                              p.serialize_policy(rebuilt)) == files,
              'restored scene lost complete bundle identity')
    report = dict(status='PASS_PUBLIC_BPY_ONLY', blender_version=list(bpy.app.version),
        build_hash=bpy.app.build_hash.decode(),
        original_on_mode_controls=legacy,
        layout_negative_controls=results,
        layout_controls=len(results),
        total_controls=legacy['controls']+len(results), restored_identity=True,
        scope='Actual saved/reopened bpy scenes; no private asset or appearance acceptance')
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print('BUILD11_INDEX_LAYOUT_MUTATIONS_OK '+str(report['total_controls']))


if __name__ == '__main__':
    main()

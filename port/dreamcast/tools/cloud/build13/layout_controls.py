#!/usr/bin/env python3
"""Public production-exporter sweep and fail-closed v4 representation controls.

Writes generated assets only to the explicitly supplied output directory. No
console timings or renderer speedups are inferred from these host controls.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(TOOLS))
import convert_room_bins as crb
import mesh_lod
import scenery_record_split as split
from source_fixture import generate

BASE = '9b248c5b40a49e4c954ea834fdf665fdbbc314f0'
COMMON = ['--lod-floor', '0', '--lod-eps', '24,96,384', '--lod-min-gain', '0.8']


def run(argv, log):
    """Real process execution, with Linux per-child resource accounting."""
    t = time.perf_counter()
    with open(log, 'w') as out:
        p = subprocess.Popen(list(map(str, argv)), stdout=out, stderr=subprocess.STDOUT,
                             env=dict(os.environ, PYTHONPATH=str(TOOLS)))
        _, status, usage = os.wait4(p.pid, 0)
        p.returncode = os.waitstatus_to_exitcode(status)
    split.require(p.returncode == 0, 'command failed: '+str(log)+'\n'+Path(log).read_text())
    return dict(argv=list(map(str, argv)), host_wall_seconds=time.perf_counter()-t,
                host_process_peak_rss_kib=usage.ru_maxrss, log=str(log))


def load(stem, candidate=False):
    return split.Package(stem.with_suffix('.re4mesh').read_bytes(), allow_split=candidate)


def triangles(pkg, ids):
    out, degenerates = [], 0
    for li in ids:
        refs = pkg.refs(li)
        for raw in pkg.strips(li):
            corners = [pkg.vertices[refs[k]] for k in raw[1:]]
            for tri in crb.strip_triangles(corners):
                # Count repeated-position triangles separately; preserve them
                # in the exact stream and multiset proofs below.
                degenerates += len({v[:6] for v in tri}) < 3
                out.append(tri)
    return out, degenerates


def oriented(tri):
    return min(tri, tri[1:]+tri[:1], tri[2:]+tri[:2])


def streams(pkg):
    result = {}
    for pi, (fc, cc) in enumerate(pkg.tables['part_lod']):
        for ci in range(cc):
            c = pkg.tables['cluster'][fc+ci]
            for ki in range(c[7]):
                first, count, error = pkg.tables['level'][c[6]+ki]
                result[(pi, ci, ki)] = (tuple(range(first, first+count)), error)
    return result


def compare_geometry(reference, candidate, side):
    a, b = streams(reference), streams(candidate)
    split.require(a.keys() == b.keys(), 'sweep source/LOD key identity')
    split.require(reference.sections['mesh'] == candidate.sections['mesh'], 'sweep source/grid identity')
    split.require([p[:6]+p[8:] for p in reference.parts] == [p[:6]+p[8:] for p in candidate.parts],
                  'sweep part/source/UV identity')
    split.require(reference.tables['part_lod'] == candidate.tables['part_lod'] and
                  reference.tables['cluster'] == candidate.tables['cluster'], 'sweep cluster identity')
    rows = []
    for key in a:
        ids_a, err_a = a[key]; ids_b, err_b = b[key]
        split.require(struct.pack('<f', err_a) == struct.pack('<f', err_b), 'sweep LOD error identity')
        ta, da = triangles(reference, ids_a); tb, db = triangles(candidate, ids_b)
        ca, cb = list(map(oriented, ta)), list(map(oriented, tb))
        equal = Counter(ca) == Counter(cb)
        split.require(equal, 'sweep oriented triangle multiset: '+str(key))
        pi, ci, ki = key; pass_ = side[32+16*pi+12]
        rows.append(dict(part=pi, cluster=ci, lod=ki, pass_=pass_, triangles=len(tb),
                         degenerates=db, degenerates_reference=da,
                         ordered_exact_corners=ta == tb, ordered_oriented_triangles=ca == cb,
                         oriented_triangle_multiset=equal,
                         order_qualification='identical' if ta == tb else
                         ('translucent order changed: NOT QUALIFIED' if pass_ == 2 else
                          'order changed: visual/order acceptance required')))
    return rows


def counts(pkg, ids):
    ids = list(ids)
    strips = [raw for li in ids for raw in pkg.strips(li)]
    refs = [r for li in ids for r in pkg.refs(li)]
    return dict(meshlets=len(ids), meshlet_setup_calls=len(ids),
                strip_headers=len(strips),
                submitted_corners=sum(len(s)-1 for s in strips),
                transformed_local_vertices=sum(pkg.meshlets[li][3] for li in ids),
                referenced_pool_records=len(set(refs)),
                repeated_transform_references=len(refs)-len(set(refs)),
                indexed_meshlets=sum(bool(pkg.meshlets[li][4] & split.INDEXED) for li in ids),
                pool_offset_bytes=sum(2*pkg.meshlets[li][3] for li in ids
                                      if pkg.meshlets[li][4] & split.INDEXED),
                triangles_including_degenerate=sum(len(s)-3 for s in strips))


def demand_lines(base, stride, width, ids):
    lines = set()
    independent = 0
    for li in ids:
        first = base+li*stride
        touched = set(range(first//32, (first+width-1)//32+1))
        independent += len(touched); lines.update(touched)
    return dict(architectural_32B_line_union=len(lines), per_record_line_sum=independent,
                records=len(ids), architectural_bytes=len(ids)*width)


def metrics(pkg, candidate, side):
    placement = split.policy(side, pkg)
    all_ids = list(range(pkg.h[6]))
    lod0 = [li for (_, _, k), (ids, _) in streams(pkg).items() if k == 0 for li in ids]
    part_vertex_sets = []
    for p in pkg.parts:
        refs = {r for li in range(p[6], p[6]+p[7]) for r in pkg.refs(li)}
        part_vertex_sets.append((len(refs), len({pkg.vertices[r] for r in refs})))
    tests = {}
    for name, ids in [('dense_all', all_ids), ('sparse_every_fourth', all_ids[::4]), ('lod0_selected', lod0)]:
        tests[name] = dict(aos_emit_prefix=demand_lines(pkg.h[12], 28, 16, ids),
                           split_emit=demand_lines(candidate.h[12], 16, 16, ids),
                           aos_full_record=demand_lines(pkg.h[12], 28, 28, ids),
                           split_bounds=demand_lines(candidate.h[17], 12, 12, ids),
                           split_emit_and_bounds_union=len(
                               {n for li in ids for n in range((candidate.h[12]+16*li)//32,
                                                              (candidate.h[12]+16*li+15)//32+1)} |
                               {n for li in ids for n in range((candidate.h[17]+12*li)//32,
                                                              (candidate.h[17]+12*li+11)//32+1)}))
    # This public fixture has one mesh instanced twice. State the multiplier
    # instead of disguising asset counts as a measured game-frame census.
    split.require(pkg.h[4] == 1, 'fixture frame multiplier assumes one mesh')
    additive = ('meshlets', 'meshlet_setup_calls', 'strip_headers', 'submitted_corners',
                'transformed_local_vertices', 'indexed_meshlets', 'pool_offset_bytes',
                'triangles_including_degenerate')
    frame = {k: v*placement[2] for k, v in counts(pkg, lod0).items() if k in additive}
    frame.update(placement_visits=placement[2], part_visits=pkg.h[5]*placement[2],
                 polygon_header_upper_bound=pkg.h[5]*placement[2],
                 assumption='all fixture placements/parts/LOD0 meshlets visible; no clipping; header upper bound only')
    return dict(mesh_count=pkg.h[4], part_count=pkg.h[5], placement_count=placement[2],
                resident_mesh_bytes=len(pkg.data), split_resident_mesh_bytes=len(candidate.data),
                split_record_padding_delta=len(candidate.data)-len(pkg.data),
                stored_vertex_records=pkg.h[7], stored_vertex_bytes=12*pkg.h[7],
                repeated_stored_records_within_parts=sum(n-u for n, u in part_vertex_sets),
                ordinary_aos_table_bytes=28*pkg.h[6], split_emit_table_bytes=16*pkg.h[6],
                split_bounds_table_bytes=12*pkg.h[6], all_lods=counts(pkg, all_ids),
                asset_lod0=counts(pkg, lod0), synthetic_frame_lod0=frame,
                metadata_demand_lines=tests)


def patch_crc(blob, offset, fmt, *values):
    data = bytearray(blob); struct.pack_into(fmt, data, offset, *values)
    struct.pack_into('<I', data, 12, split.crc(data[80:]))
    return bytes(data)


def negatives(mesh, side, groups, out):
    p = split.Package(mesh); candidate, sg, _ = split.convert(mesh, side, groups)
    failures = []
    def reject(name, action):
        try:
            action()
        except (ValueError, struct.error) as error:
            failures.append(dict(case=name, diagnostic=str(error)))
        else:
            raise AssertionError('accepted invalid fixture: '+name)
    reject('body CRC', lambda: split.convert(mesh[:-1]+bytes([mesh[-1]^1]), side))
    reject('global meshlet 65537', lambda: split.convert(patch_crc(mesh, 24, '<I', 65537), side))
    reject('Build12 SDS1 lineage words', lambda: split.convert(patch_crc(mesh, 68, '<III', 1, 2, 3), side))
    reject('Build12 SDO3 marker', lambda: split.convert(patch_crc(mesh, 76, '<I', 0x334f4453), side))
    reject('appended runtime extension', lambda: split.convert(patch_crc(mesh, 108, '<I', 128), side))
    reject('unknown trailing extension', lambda: split.convert(
        patch_crc(mesh+bytes(32), 8, '<I', len(mesh)+32), side))
    reject('nonprelit encoding', lambda: split.convert(patch_crc(mesh, 64, '<I', 1), side))
    reject('nonzero part state', lambda: split.convert(patch_crc(mesh, p.h[11]+11, '<B', 1), side))
    reject('bad source owner', lambda: split.convert(patch_crc(mesh, p.h[10]+3, '<B', 0), side))
    reject('meshlet 257 vertices', lambda: split.convert(patch_crc(mesh, p.h[12]+12, '<H', 257), side))
    reject('bad local strip reference', lambda: split.convert(patch_crc(
        mesh, p.h[14]+p.meshlets[0][1]+1, '<B', 255), side))
    reject('stale R4PW', lambda: split.convert(mesh, side[:-1]+bytes([side[-1]^1])))
    stale_groups = bytearray(groups); struct.pack_into('<I', stale_groups, 16, 0)
    reject('stale R4SG', lambda: split.convert(mesh, side, stale_groups))
    reject('truncated R4SG', lambda: split.convert(mesh, side, groups[:-1]))
    altered = bytearray(groups)
    # Group enclosure mutation with a valid checksum cannot be blessed.
    struct.pack_into('<H', altered, 32+6, 0)
    struct.pack_into('<I', altered, 28, split.crc(altered[32:]))
    reject('R4SG bounds do not enclose', lambda: split.convert(mesh, side, altered))
    q = split.Package(candidate, allow_split=True)
    reject('nonadjacent split bounds', lambda: split.Package(patch_crc(candidate, 68, '<I', q.h[17]+32), True))
    reject('v4 cannot be input to converter', lambda: split.convert(candidate, side))
    reject('wrong split lineage', lambda: split.verify_identity(p,
        split.Package(patch_crc(candidate, 72, '<I', 0), True)))
    reject('unsupported physical proof sibling', lambda: _proof_refusal(out))
    # Serialized overlapping-cluster mutation: both individual level ranges
    # fit part0, but selecting one level from each exceeds its Pick reserve.
    altered = bytearray(mesh)
    struct.pack_into('<I', altered, p.l[2]+4, 2)
    altered[p.l[3]+20:p.l[3]+40] = altered[p.l[3]:p.l[3]+20]
    struct.pack_into('<I', altered, 12, split.crc(altered[80:]))
    reject('overlapping cluster selected Pick overflow', lambda: split.convert(altered, side))
    # Keep all actual referenced vertices unchanged, but move an indexed
    # record's declared base into an earlier part. Generic part_pool rejects
    # that conservative interval overlap even when offset zero is unused.
    altered = bytearray(mesh)
    part = p.parts[1]
    li = next(i for i in range(part[6], part[6]+part[7]) if p.meshlets[i][4] & split.INDEXED)
    fv, fs, _, vc, _ = p.meshlets[li][:5]
    offsets = struct.unpack_from('<%dH' % vc, mesh, p.h[14]+fs)
    struct.pack_into('<I', altered, p.h[12]+28*li, 0)
    struct.pack_into('<%dH' % vc, altered, p.h[14]+fs, *(fv+k for k in offsets))
    struct.pack_into('<I', altered, 12, split.crc(altered[80:]))
    reject('indexed conservative part-pool base overlap', lambda: split.convert(altered, side))
    return failures


def _proof_refusal(out):
    mesh = out/'unknown.re4mesh'
    proof = out/'unknown.r4pvs'
    proof.write_bytes(b'public unsupported proof fixture')
    try:
        split.refuse_extra_sidecars(mesh)
    finally:
        proof.unlink()


def source_admission(fixture, out):
    stub = out/'kos'; stub.mkdir(exist_ok=True)
    (stub/'fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n')
    src = out/'source-admission.cpp'
    src.write_text('''#include "ps2_source_package.hpp"
#include "instanced_mesh.hpp"
#include <fstream>
#include <iterator>
#include <vector>
#include <cstdio>
int main(int argc,char**argv){
 std::ifstream f(argv[1],std::ios::binary);
 std::vector<unsigned char>b((std::istreambuf_iterator<char>(f)),{});
 re4dc::room::ps2::SpanPackage p;
 auto e=p.adopt({b.data(),b.size()},{0x123,0x50,1U<<24},{0x123,1});
 if(e!=re4dc::room::ps2::PackageError::ok){std::printf("source error %u\\n",unsigned(e));return 1;}
 for(int i=2;i<argc;++i){
  std::ifstream mf(argv[i],std::ios::binary);
  std::vector<unsigned char>m((std::istreambuf_iterator<char>(mf)),{});
  re4dc::room::MeshPackage mp;
  if(!mp.adopt(m.data(),m.size(),true,true)){std::printf("mesh error %s\\n",mp.error());return 2;}
 }
 std::puts("SOURCE_AND_ORDINARY_MESH_ADMISSION PASS");
}
''')
    binary = out/'source-admission'
    compile_result = run(['g++', '-std=c++17', '-O2', '-I'+str(TOOLS.parent/'room'), '-I'+str(out),
                          src, '-o', binary], out/'source-admission-compile.log')
    return binary, compile_result


def nonsequential_index_control(pkg, side, out):
    """Real valid offsets need not follow meshlet order; retain raw indices."""
    pair = next((i, j) for i, a in enumerate(pkg.meshlets) for j, b in enumerate(pkg.meshlets)
                if i < j and not (a[4] & split.INDEXED) and not (b[4] & split.INDEXED)
                and a[2] == b[2] and pkg.strips(i) != pkg.strips(j))
    i, j = pair; a, b = pkg.meshlets[i], pkg.meshlets[j]
    oa, ob, size = pkg.h[14]+a[1], pkg.h[14]+b[1], a[2]
    split.require(oa+size <= ob or ob+size <= oa, 'test strip spans must not overlap')
    altered = bytearray(pkg.data)
    altered[oa:oa+size], altered[ob:ob+size] = altered[ob:ob+size], altered[oa:oa+size]
    struct.pack_into('<I', altered, pkg.h[12]+28*i+4, b[1])
    struct.pack_into('<I', altered, pkg.h[12]+28*j+4, a[1])
    struct.pack_into('<I', altered, 12, split.crc(altered[80:]))
    source = split.Package(altered)
    split.require([triangles(pkg, [li]) for li in range(pkg.h[6])] ==
                  [triangles(source, [li]) for li in range(pkg.h[6])], 'nonsequential fixture changed geometry')
    candidate, _, _ = split.convert(altered, side)
    target = split.Package(candidate, True)
    split.verify_identity(source, target)
    split.require(source.sections['index'] == target.sections['index'], 'raw index section preservation')
    path = out/'nonsequential.re4mesh'; path.write_bytes(altered)
    return dict(path=str(path), swapped_meshlets=list(pair), source_sha256=split.sha(altered),
                candidate_sha256=split.sha(candidate), raw_index_section_identity=True,
                exact_per_meshlet_triangle_order=True, private_admission_claim=False)


def off_controls(source, out):
    old = out/'baseline-exporter.py'
    old.write_bytes(subprocess.check_output(['git', 'show', BASE+':port/dreamcast/tools/ps2_world_r4im.py'], cwd=ROOT))
    stem = out/'off-identity'
    paths = [stem.with_suffix(s) for s in ('.re4mesh', '.r4pw', '.json')]
    base_args = [source['wrapper'], source['inc'], stem, *COMMON]
    receipts = [run([sys.executable, old, *base_args], out/'off-base.log')]
    wanted = [p.read_bytes() for p in paths]
    for name, args in [('absent', []), ('explicit0', ['--scenery-record-split', '0']),
                       ('explicit64', ['--meshlet-vertices', '64'])]:
        receipts.append(run([sys.executable, TOOLS/'ps2_world_r4im.py', *base_args, *args], out/('off-'+name+'.log')))
        split.require([p.read_bytes() for p in paths] == wanted, 'default/off identity: '+name)
    build12 = []
    for flag, name in [('--scenery-local-indexed', 'ps2-sli1'), ('--scenery-direct-strips', 'ps2-sds1')]:
        comparison_paths = [*paths, out/(name+'.re4mesh')]
        receipts.append(run([sys.executable, old, *base_args, flag], out/('off-base-'+name+'.log')))
        expected = [p.read_bytes() for p in comparison_paths]
        for suffix in ([], ['--scenery-record-split', '0']):
            receipts.append(run([sys.executable, TOOLS/'ps2_world_r4im.py', *base_args, flag, *suffix],
                                out/('off-current-'+name+('-zero' if suffix else '')+'.log')))
            split.require([p.read_bytes() for p in comparison_paths] == expected, 'Build12 output/report identity: '+name)
        build12.append(dict(flag=flag, output_hashes={p.name: split.sha(b) for p, b in zip(comparison_paths, expected)},
                            absent_and_explicit0_identity=True))
    early_refusals = []
    for flag in ('--scenery-local-indexed', '--scenery-direct-strips'):
        argv = [sys.executable, str(TOOLS/'ps2_world_r4im.py'), '/does/not/exist.r4p',
                '/does/not/exist.inc', str(out/'must-not-write'), flag, '--scenery-record-split', '1']
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        split.require(result.returncode != 0 and 'cannot be composed with Build12' in result.stdout and
                      not list(out.glob('must-not-write*')), 'combined flag must reject before source access/output')
        early_refusals.append(dict(flag=flag, diagnostic=result.stdout.strip(), no_source_read_or_output=True))
    return dict(base=BASE, compared=['absent', 'explicit0', 'explicit64'],
                output_hashes={p.suffix: split.sha(v) for p, v in zip(paths, wanted)},
                ordinary_json_args_identity=True, build12_existing_flags=build12,
                build12_composition_early_refusals=early_refusals, commands=receipts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--receipt', type=Path)
    a = ap.parse_args(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    source = generate(out/'source')
    off = off_controls(source, out)
    entries, packages, commands = [], {}, []
    for limit in (32, 64, 128, 256):
        folder = out/str(limit); folder.mkdir(exist_ok=True); stem = folder/'ps2-world'
        commands.append(run([sys.executable, TOOLS/'ps2_world_r4im.py', source['wrapper'], source['inc'], stem,
                             *COMMON, '--meshlet-vertices', limit, '--scenery-record-split', '1'], folder/'export.log'))
        p = load(stem); candidate_stem = folder/'ps2-world-split'; q = load(candidate_stem, True)
        side = stem.with_suffix('.r4pw').read_bytes()
        ordinary_groups = split.build_groups(p, side)
        stem.with_suffix('.r4sg').write_bytes(ordinary_groups)
        split.verify_identity(p, q)
        split.validate_groups(candidate_stem.with_suffix('.r4sg').read_bytes(), q, side)
        candidate_bytes, sg, _ = split.convert(p.data, side, ordinary_groups)
        split.require(candidate_bytes == q.data and sg == candidate_stem.with_suffix('.r4sg').read_bytes(),
                      'supplied/group-generated candidate identity')
        packages[limit] = (p, q, side)
        entry = dict(limit=limit, ordinary=str(stem.with_suffix('.re4mesh')),
                     split=str(candidate_stem.with_suffix('.re4mesh')), policy=str(stem.with_suffix('.r4pw')),
                     ordinary_groups=str(stem.with_suffix('.r4sg')), split_groups=str(candidate_stem.with_suffix('.r4sg')),
                     r4sg_record_offset=32, r4sg_record_bytes=16, r4sg_group_count=4,
                     ordinary_emit_offset=p.h[12], ordinary_emit_stride=28,
                     split_emit_offset=q.h[12], split_emit_stride=16, split_bounds_offset=q.h[17], split_bounds_stride=12,
                     meshlet_count=p.h[6], part_count=p.h[5], mesh_count=p.h[4],
                     file_hashes={path.name: split.sha(path.read_bytes()) for path in folder.glob('*.re4mesh')},
                     metrics=metrics(p, q, side))
        entries.append(entry)
    # Save paths early for the independent target-cost/reader lane.
    manifest = dict(schema='re4dc.build13.fixture-paths.v1', base=BASE, fixtures=entries)
    (out/'fixtures.json').write_text(json.dumps(manifest, indent=2)+'\n')
    ref = packages[256][0]
    for e in entries:
        p, q, side = packages[e['limit']]
        e['geometry_vs_256'] = compare_geometry(ref, p, side)
        all_counts = e['metrics']['all_lods']; ref_counts = entries[-1]['metrics']['all_lods']
        delta_strips = all_counts['strip_headers']-ref_counts['strip_headers']
        delta_corners = all_counts['submitted_corners']-ref_counts['submitted_corners']
        split.require(delta_corners == 2*delta_strips, 'restart corner accounting')
        e['restart_delta_vs_256'] = dict(additional_strips=delta_strips, additional_corners=delta_corners,
                                       two_repeat_corners_per_restart=True)
    p, q, side = packages[64]
    negative = negatives(p.data, side, (out/'64/ps2-world.r4sg').read_bytes(), out)
    nonsequential = nonsequential_index_control(p, side, out)
    # Exact existing preserve-order R4SG generator is an independent oracle.
    from d367.visibility23.metadata import build as established_groups
    established, _ = established_groups(p.data, side, 4)
    split.require(established == split.build_groups(p, side), 'existing R4SG generator identity')
    # A real post-spatial-group source must retain its original records. This
    # exercises the standalone adapter at the pipeline's actual ordering edge.
    grouped = out/'post-group'; grouped.mkdir(exist_ok=True)
    group_mesh = grouped/'world.re4mesh'; group_side = grouped/'world.r4pw'; group_sg = grouped/'world.r4sg'
    group_side.write_bytes(side)
    commands.append(run([sys.executable, TOOLS/'ps2_strip_groups.py', out/'64/ps2-world.re4mesh',
                         out/'64/ps2-world.r4pw', group_mesh, group_sg], grouped/'group.log'))
    post_stem = grouped/'world-split'
    # Standalone command deliberately refuses pre-existing outputs.
    for suffix in ('.re4mesh', '.r4sg', '.json'):
        post_stem.with_suffix(suffix).unlink(missing_ok=True)
    commands.append(run([sys.executable, TOOLS/'scenery_record_split.py', group_mesh, group_side, post_stem],
                        grouped/'split.log'))
    split.verify_identity(split.Package(group_mesh.read_bytes()), load(post_stem, True))
    split.require(group_sg.read_bytes()[32:] == post_stem.with_suffix('.r4sg').read_bytes()[32:],
                  'post-group supplied R4SG payload identity')
    # Plain v2 conversion is required: never pretend plain output is v3.
    plain = out/'plain'; plain.mkdir(exist_ok=True); stem = plain/'ps2-world'
    commands.append(run([sys.executable, TOOLS/'ps2_world_r4im.py', source['wrapper'], source['inc'], stem,
                         *COMMON, '--no-share', '--scenery-record-split', '1'], plain/'export.log'))
    split.require(load(stem).h[1] == 2 and load(plain/'ps2-world-split', True).h[1] == 4, 'plain v2->v4')
    binary, compile_result = source_admission(source, out)
    admission = run([binary, source['wrapper'], *[e['ordinary'] for e in entries], stem.with_suffix('.re4mesh'),
                     nonsequential['path']],
                    out/'source-admission.log')
    # Restart primitive parity is checked independently of the grid sweep.
    chain = tuple(range(401)); chain_controls = []
    for limit in (32, 64, 128, 256):
        baseline = [s for s in (crb.split_strip(chain))]
        result = [s for original in baseline for s in mesh_lod.split_to_limit(original, limit)]
        wanted = list(crb.strip_triangles(chain)); got = [t for s in result for t in crb.strip_triangles(s)]
        split.require(got == wanted, 'minimal restart exact winding/order')
        split.require(sum(map(len, result))-len(chain) == 2*(len(result)-1), 'minimal restart repeated corners')
        chain_controls.append(dict(limit=limit, original_corners=len(chain), strips=len(result),
                                   corners=sum(map(len, result)), exact_ordered_triangles=True))
    receipt = dict(schema='re4dc.build13.layout-controls.v1', base=BASE, fixture=dict(source, wrapper=str(source['wrapper']),
                   inc=str(source['inc'])), off_identity=off, fixtures=entries, negative_controls=negative,
                   plain_v2_supported=True, established_preserve_order_r4sg_identity=True,
                   production_post_group_standalone_identity=True,
                   nonsequential_index_control=nonsequential,
                   restart_primitive_controls=chain_controls, commands=commands,
                   source_admission_compile=compile_result, source_admission=admission,
                   runtime_performance_claim=False,
                   limitations=['Public synthetic geometry; no r101 or private assets tested.',
                                'Meshlet size can change ordering; per-LOD order results are explicit.',
                                '32B demand-line counts are architectural unions, not misses or timings.',
                                'Host wall/RSS values describe conversion only, not SH4 performance.',
                                'Known private proof sidecars and Build12 composition are not rebound.'])
    hashes = {}
    for path in [Path(__file__), HERE/'source_fixture.py', TOOLS/'scenery_record_split.py', TOOLS/'ps2_world_r4im.py']:
        hashes[str(path.relative_to(ROOT))] = split.sha(path.read_bytes())
    receipt['tool_source_sha256'] = hashes
    target = a.receipt or out/'layout-controls.json'
    target.write_text(json.dumps(receipt, indent=2, default=str)+'\n')
    (out/'fixtures.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(status='PASS', receipt=str(target), manifest=str(out/'fixtures.json'),
                          limits=[e['limit'] for e in entries], negative_controls=len(negative))))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Export the exact PS2 source-selected Ganado variants (lost-head stumps and hand poses) as a disc package.

The PS2 Ganado cast (pg5: five appearances, body / head / hands 448 + 453) had no row for the infos em10 swaps in during
play, so those Ganados drew the GameCube model (CAST-GC, lanes castgc17 / stump17, 10-17):
  - em10HeadSet (src/em10/em10.cpp) swaps the head to mot[3], the appearance's lost-head stump, when the head is shot
    off: BIN 475 / 447 / 479 / 483 / 460 for appearances 0..4 (em12/13/15/16/17 _set.cpp; Codex 10-13 did 479 only);
  - em10HandSet swaps the hands to mot[7] / mot[12] (type 1: back-hold / bomb-hold, BIN 449 / 454) and mot[8] /
    mot[13] (type 2: the alert routine, BIN 450 / 455), on every appearance.

  geometry  app  role   BIN  ps2_cast.py preset (stage 1 + ps2_cast_native.sh)
  0         0    head   475  ganado-em12-01-stump
  1         1    head   447  ganado-em15-00-stump
  2         2    head   479  ganado-em13-03-stump   (Codex's reviewed conversion, native header abcc4603...)
  3         3    head   483  ganado-em15-04-stump
  4         4    head   460  ganado-em15-0b-stump
  5         all  right  449  ganado-<app>-h1 (identical in all five)
  6         all  right  450  ganado-<app>-h2
  7         all  left   454  ganado-<app>-h1
  8         all  left   455  ganado-<app>-h2

Every PS2 stump equals its GC stump exactly (0 mm both ways); the hands are the PS2 meshes (97 triangles; GC 217) bound
to the GC skeleton. Each preset's atlas must be its appearance's normal pg5 atlas byte for byte (no new texture), and a
hand chunk (geometry and UVs) must be identical in all five appearances' conversions.

Outputs (lane stump17; the coordinator 10-17: tables and meshes out of the program image, only code static):
  <out>/ganado_var.re4gv           private disc package, staged at dc/native/ganado/ganado_var.re4gv (data set stump17)
  <out>/ganado_ps2_stump_runtime.h private image header: counts, array sizes and FNV-1a digests only (no mesh bytes)
  game/actor_material_records_ps2_stump.inc  public GC BIN facts (the role rows' admission seal), --write-public
"""
import argparse
import json
from pathlib import Path
import re
import struct

import model_registry as mr

APPS = [  # app, appearance, stump BIN, TPL, stump preset, hand preset stem, archives carrying the stump BIN
    (0, 'ganado-em12-01', 475, 473, 'ganado-em12-01-stump', 'ganado-em12-01', ('em12', 'em13', 'em17')),
    (1, 'ganado-em15-00', 447, 445, 'ganado-em15-00-stump', 'ganado-em15-00', ('em12', 'em13', 'em15', 'em17')),
    (2, 'ganado-em15-03', 479, 477, 'ganado-em13-03-stump', 'ganado-em15-03', ('em12', 'em13', 'em15', 'em16', 'em17')),
    (3, 'ganado-em15-04', 483, 481, 'ganado-em15-04-stump', 'ganado-em15-04', ('em12', 'em13', 'em15', 'em16')),
    (4, 'ganado-em15-0b', 460, 458, 'ganado-em15-0b-stump', 'ganado-em15-0b', ('em15', 'em16')),
]
HANDS = [(2, 449, 'h1'), (2, 450, 'h2'), (3, 454, 'h1'), (3, 455, 'h2')]  # role, BIN, preset suffix
HAND_ARCHIVES = ('em12', 'em13', 'em15', 'em16', 'em17')
# --grip (lane purge-cast24 10-24, GC purge; ACTOR_GANADO_PS2_GRIP): the grip hands em10HandSet selects for a held weapon /
# torch (BIN 451 / 456, mot[9] / mot[14]), which otherwise draw the GameCube geometry (ganado_extra). Appended after the
# nine stump17 geometries, so the package without --grip is byte-identical to stump17's.
GRIP_HANDS = [(2, 451, 'h3'), (3, 456, 'h3')]
# Reviewed 10-17 (lane stump17): GC BIN sha256 prefix, normalized load digest, native header sha256 prefix, triangles,
# palettes. Hands: the native header differs per preset (other roles), so the chunk digest is pinned instead.
REVIEWED_STUMP = {
    0: ('42824bb6bcc9a833', [3200, 1128395770, 2403039293], 'b7e31389f85975e5', 90, 6),
    1: ('1ca4956d37975b12', [2944, 1978383310, 1061756992], '827657e809cd79ba', 88, 6),
    2: ('9876c71e4c4480aa', [2976, 1450011754, 3920562518], 'abcc46030280e07e', 90, 6),
    3: ('fdcdf13afa7e354a', [2912, 1990468374, 1286629251], '4df53411ee47282f', 88, 2),
    4: ('ec61f2457689b028', [3040, 1374730771, 2938463957], '2a1910ada78ffe42', 88, 1),
}
REVIEWED_HAND = {
    449: ('4541745ec85ddce0', [5888, 2529276789, 3486964274], 97, 3),
    450: ('2d144319f4c74120', [5888, 3608060527, 2496883440], 97, 2),
    454: ('1ea733068edc17e2', [5952, 1963098602, 1580596659], 97, 2),
    455: ('e2100862a42f15c7', [5952, 4022166836, 2700100576], 97, 2),
    # lane purge-cast24 (10-24): the grip hands (one PS2 mesh of 101 triangles each, identical in all five conversions)
    451: ('b2dc2451d5f2a9e1', [5888, 3446078520, 2841889831], 101, 2),
    456: ('561ea79403e407cd', [5952, 3566550875, 4284573839], 101, 2),
}
# em13 / em15 pins of the appearance-2 host test (tests/test_actor_ganado_ps2_stump.py, Codex 10-13).
PINS = {
    'em13.drs': '7e2266f4c404264f97bd29c07225d6e069d828c3728a2001570b314e6cce132d',
    'em13.dat': 'd2f71183ae1921fddec626b5e72b5c40df937aa30bd3e0508c528fc3aa4aa6ed',
    'em15.drs': 'b6a4cfbe7d517728de72cb1081b833af2911e59967a4fecbd84013be09730874',
    'em15.dat': '4dcfa55f6825b91949fe67a59d04d02678e44b24c42e9a50017c2d58be265415',
}
CAST_SHA = 'aa47772e4366f54d4ace27f8be4613c99f7d3f7b4f3561e00c2c48f6649e0bb4'  # pg5 ganado_cast_runtime.h
PUBLIC = 'port/dreamcast/game/actor_material_records_ps2_stump.inc'
MAGIC, VERSION, HEADER, RECORD = 0x31564752, 1, 64, 64  # 'RGV1'


def require(ok, message):
    if not ok:
        raise mr.Fail(message)


def fnv(data, h=0x811c9dc5):
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h


def arrays(c):
    w = b''.join(struct.pack('<4B3f', *bb, n, *ww) for bb, n, ww in c['weights'])
    return [bytes(c['positions']), bytes(c['normals']), bytes(c['uv']), bytes(c['stream']), w]


def public_facts(facts):
    u = lambda xs: ','.join(str(x) + 'u' for x in xs)
    lines = ['// Exact original GC BIN facts of the source-selected Ganado variants (em10HeadSet mot[3] lost-head stumps,',
             '// em10HandSet hand poses 449 / 450 / 454 / 455), derived by tools/d367/ps2_ganado_stump.py. Mesh bytes remain',
             '// private; this table only certifies the source-selected infos (one Part / Model per BIN; each BIN is identical',
             '// in every archive carrying it).']
    for b, f in facts:
        lines.append(f'static const Part p_ps2_var_{b}[] = {{')
        for part in f['parts']:
            lines.append('{{' + u(bytes.fromhex(part[0])) + '},' + u(part[1:]) + '},')
        lines += ['};', f'static const Model m_ps2_var_{b} = {{{{' + u(f['header']) + '},' +
                  ','.join('{' + u(f[k]) + '}' for k in ('positions', 'normals', 'weights', 'uv')) + f',p_ps2_var_{b}}};']
    return '\n'.join(lines) + '\n'


def chunk_of(conv, role, normal_atlas_root, appearance, key):
    native = conv / 'runtime/castmodel_runtime.h'
    chunks, bones = mr.parse_header(native)
    require(bones == 34 and len(chunks) == 4, f'{conv.name}: unexpected skeleton / role layout')
    c = chunks[role]
    require(c['source_info'] == role, f'{conv.name}: role {role} is not source info {role}')
    mr.preflight_chunk(c, bones)
    v = json.loads((conv / 'validation.json').read_text())
    require(not v['winding_flipped'] and v['texture']['key'] == key, f'{conv.name}: winding / atlas key differs')
    tex = (conv / f'texture/{key}.re4tex').read_bytes()
    base = (normal_atlas_root / appearance / f'texture/{key}.re4tex').read_bytes()
    # RE4DCTX v2: bytes 48..95 are the diagnostic label, 36..39 its CRC; everything else must agree.
    require(len(tex) == len(base) and tex[:36] == base[:36] and tex[40:48] == base[40:48] and tex[96:] == base[96:],
            f'{conv.name}: atlas payload differs from the normal {appearance} atlas')
    return c, v, native


def generate(inputs, converted, cast_header, normal_atlas_root, out, write_public, grip=False):
    tree = Path(__file__).resolve().parents[4]
    archive, parse_tpl, le_mirror = mr.archive_facts(str(tree))
    arcs = {}

    def facts_of(name, b):
        arc = arcs.get(name) or arcs.setdefault(name, archive.Archive(str(inputs / (name + '.drs'))))
        return mr.bin_facts(arc, le_mirror, name, b)

    require(mr.sha(cast_header.read_bytes()) == CAST_SHA, 'cast header is not the reviewed pg5 bundle')
    gc = cast_header.read_text()
    names = [n.strip().strip('"') for n in re.search(r'appearance_names\[5\] = \{([^}]*)\}', gc).group(1).split(',')]
    keys = re.findall(r'\{0x([0-9a-f]{8})u,0x([0-9a-f]{8})u,512,512\}', gc.split('static const Texture textures[] =')[1].split(';')[0])
    require(len(keys) == 5, 'cast atlas table differs')
    geoms, facts, report = [], [], []
    for app, appearance, b, tpl, preset, stem, archs in APPS:
        gc_sha, normalized, native_sha, tris, pals = REVIEWED_STUMP[app]
        require(names[app] == appearance, f'app {app}: cast appearance {names[app]} != {appearance}')
        f = None
        for name in archs:
            g = facts_of(name, b)
            require(g['sha256'].startswith(gc_sha) and g['normalized'] == normalized, f'{name}/{b}: source identity differs')
            f = f or g
        facts.append((b, f))
        key = '%s-%s' % keys[app]
        c, v, native = chunk_of(converted / preset, 1, normal_atlas_root, appearance, key)
        require(mr.sha(native.read_bytes()).startswith(native_sha), f'{preset}: native header differs from the reviewed conversion')
        h = v['sections'][1]
        require(c['triangles'] == tris and c['palette_count'] == pals and h['ps2_triangles'] == h['gc_triangles'] == tris and
                h['rest_ps2_to_gc_surface_mm']['max'] == 0.0 and h['rest_gc_to_ps2_surface_mm']['max'] == 0.0,
                f'{preset}: the PS2 stump is not the GC stump exactly')
        geoms.append(dict(role=1, bin=b, apps=1 << app, chunk=c, source=preset))
    for role, b, suffix in HANDS + (GRIP_HANDS if grip else []):
        gc_sha, normalized, tris, pals = REVIEWED_HAND[b]
        f = None
        for name in HAND_ARCHIVES:
            g = facts_of(name, b)
            require(g['sha256'].startswith(gc_sha) and g['normalized'] == normalized, f'{name}/{b}: source identity differs')
            f = f or g
        facts.append((b, f))
        first = None
        for app, appearance, _, _, _, stem, _ in APPS:
            c, v, _ = chunk_of(converted / f'{stem}-{suffix}', role, normal_atlas_root, appearance, '%s-%s' % keys[app])
            require(c['triangles'] == tris and c['palette_count'] == pals, f'{stem}-{suffix}: not the reviewed hand')
            if first is None:
                first = c
            require(arrays(c) == arrays(first), f'{stem}-{suffix}: hand {b} differs between appearances')
        geoms.append(dict(role=role, bin=b, apps=0x1f, chunk=first, source='ganado-*-' + suffix))
    # the disc package: header, records, 32-aligned arrays
    blob, recs = bytearray(), []
    data_off = HEADER + RECORD * len(geoms)
    data_off = (data_off + 31) & ~31
    for gm in geoms:
        c = gm['chunk']
        offs, sizes = [], []
        for a in arrays(c):
            while (data_off + len(blob)) % 32:
                blob.append(0)
            offs.append(data_off + len(blob)); sizes.append(len(a)); blob += a
        gm['offs'], gm['sizes'] = offs, sizes
        gm['digest'] = fnv(b''.join(arrays(c)))
        gm['skin'] = mr.skin_stream_bytes(c['weights'])
        recs.append(struct.pack('<16I', gm['role'], c['position_count'], c['normal_count'], c['palette_count'],
                                c['triangles'], c['stream_bytes'], *offs, *sizes))
    total = data_off + len(blob)
    head = struct.pack('<16I', MAGIC, VERSION, len(geoms), total, data_off, *([0] * 11))
    pkg = head + b''.join(recs)
    pkg += b'\0' * (data_off - len(pkg)) + bytes(blob)
    require(len(pkg) == total, 'package layout')
    # the grip BINs' source facts are already in the image (ganado_extra rows), so the public include stays stump17's
    text = public_facts(facts[:len(facts) - (len(GRIP_HANDS) if grip else 0)])
    pub = tree / PUBLIC
    if write_public:
        pub.write_text(text)
    require(pub.read_text() == text, 'public material facts differ from the pinned archives (run with --write-public)')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ganado_var.re4gv').write_bytes(pkg)
    u = lambda xs: ','.join(str(x) + 'u' for x in xs)
    G = geoms
    lines = ['// Private generated asset (tools/d367/ps2_ganado_stump.py). Do not commit. No mesh bytes: the meshes are the',
             '// disc package dc/native/ganado/ganado_var.re4gv; this header pins its layout and digests.',
             '#pragma once', 'namespace ganado_ps2_stump {',
             'static constexpr unsigned apps=5,count=%u,file_bytes=%uu,data_off=%uu,magic=0x%08xu,version=%uu;' %
             (len(G), total, data_off, MAGIC, VERSION),
             'static const char* const names[5]={%s};' % ','.join('"%s"' % a[1] for a in APPS),
             'static const unsigned atlas_crc[5]={%s};' % ','.join('0x%su' % k[0] for k in keys),
             'static const unsigned atlas_fnv[5]={%s};' % ','.join('0x%su' % k[1] for k in keys),
             'static const unsigned char role[%u]={%s};' % (len(G), u(g['role'] for g in G)),
             'static const unsigned short bin[%u]={%s};' % (len(G), u(g['bin'] for g in G)),
             'static const unsigned char app_mask[%u]={%s};' % (len(G), u(g['apps'] for g in G)),
             'static const unsigned positions[%u]={%s};' % (len(G), u(g['chunk']['position_count'] for g in G)),
             'static const unsigned normals[%u]={%s};' % (len(G), u(g['chunk']['normal_count'] for g in G)),
             'static const unsigned palettes[%u]={%s};' % (len(G), u(g['chunk']['palette_count'] for g in G)),
             'static const unsigned triangles[%u]={%s};' % (len(G), u(g['chunk']['triangles'] for g in G)),
             'static const unsigned stream_bytes[%u]={%s};' % (len(G), u(g['chunk']['stream_bytes'] for g in G)),
             'static const unsigned offset[%u][5]={%s};' % (len(G), ','.join('{%s}' % u(g['offs']) for g in G)),
             'static const unsigned size[%u][5]={%s};' % (len(G), ','.join('{%s}' % u(g['sizes']) for g in G)),
             'static const unsigned digest[%u]={%s};' % (len(G), ','.join('0x%08xu' % g['digest'] for g in G)),
             'static const unsigned skin_bytes[%u]={%s};' % (len(G), u(g['skin'] for g in G)),
             'static constexpr unsigned skin_total=%uu;' % sum((g['skin'] + 31) & ~31 for g in G), '}']
    target = out / 'ganado_ps2_stump_runtime.h'
    target.write_text('\n'.join(lines) + '\n')
    manifest = dict(format='ganado-ps2-var-v1', cast_header_sha256=CAST_SHA, package_bytes=total,
                    package_sha256=mr.sha(pkg), runtime_sha256=mr.sha(target.read_bytes()), public_facts_sha256=mr.sha(text.encode()),
                    geometries=[dict(k=k, role=g['role'], bin=g['bin'], app_mask=g['apps'], source=g['source'],
                                     triangles=g['chunk']['triangles'], palettes=g['chunk']['palette_count'],
                                     bytes=sum(g['sizes']), skin_bytes=g['skin'], digest='%08x' % g['digest'])
                                for k, g in enumerate(G)])
    (out / 'stump-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(package_bytes=total, skin_total=sum((g['skin'] + 31) & ~31 for g in G), package_sha256=manifest['package_sha256'][:16],
                          geometries=[(g['bin'], g['chunk']['triangles'], sum(g['sizes'])) for g in G])))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--inputs', type=Path, required=True, help='GC emXX.drs dir (em12 em13 em15 em16 em17)')
    p.add_argument('--converted', type=Path, required=True, help='dir holding the ps2_cast.py preset outputs')
    p.add_argument('--cast-header', type=Path, required=True, help='pg5 ganado_cast_runtime.h')
    p.add_argument('--normal-atlas-root', type=Path, required=True, help='cast5 dir: <appearance>/texture/<key>.re4tex')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--write-public', action='store_true')
    p.add_argument('--grip', action='store_true', help='append the grip hands 451 / 456 (ACTOR_GANADO_PS2_GRIP)')
    a = p.parse_args()
    generate(a.inputs, a.converted, a.cast_header, a.normal_atlas_root, a.out, a.write_public, a.grip)

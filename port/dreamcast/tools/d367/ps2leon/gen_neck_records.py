#!/usr/bin/env python3
"""LEON_HEADLESS (lane garr18, 2026-10-19): the GameCube identity rows of Leon's neck (setHead(0): player archive arc 0xB,
TPL 7) in coarse_actor_material.inc's types, from the original archive by model_registry.py's bin_facts (the
actor-material inspect rules, imported, not copied).

  gen_neck_records.py <tree> <player.drs> <out.inc> [--check-arc 8 --check-name pl00]

--check-arc: also emit that arc's Model row and compare it with actor_material_records.inc's m_<name>_<arc> (the
generator matches the committed gen_records.py rows). The neck is identical in pl00.drs and pl08.drs (checked by the
caller passing both); the rows are named m_pl00_11 / p_pl00_11 like the other shared pl00 rows.
"""
import argparse, importlib.util, os, re, sys


def load(tree):
    p = os.path.join(tree, 'port/dreamcast/tools/d367/model_registry.py')
    s = importlib.util.spec_from_file_location('model_registry', p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def rows(mr, arc, le, name, no):
    f = mr.bin_facts(arc, le, name, no)
    P = ['static const Part p_%s_%d[] = {' % (name, no)]
    for material, size, poly, crc, fnv in f['parts']:
        P.append('{{' + ','.join(str(v) + 'u' for v in bytes.fromhex(material)) + '},' + ','.join(str(v) + 'u' for v in (size, poly, crc, fnv)) + '},')
    P.append('};')
    M = ('static const Model m_%s_%d = {' % (name, no) + ','.join('{' + ','.join(str(v) + 'u' for v in f[k]) + '}'
         for k in ('header', 'positions', 'normals', 'weights', 'uv')) + ',p_%s_%d};' % (name, no))
    B = '{&m_%s_%d,1u,%du,{%s}},' % (name, no, no, ','.join(str(v) + 'u' for v in f['normalized']))
    return P, M, B, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tree'); ap.add_argument('drs'); ap.add_argument('out', nargs='?')
    ap.add_argument('--other'); ap.add_argument('--check-arc', type=int); ap.add_argument('--check-name', default='pl00')
    a = ap.parse_args()
    mr = load(a.tree)
    archive, _parse_tpl, le = mr.archive_facts(a.tree)
    arc = archive.Archive(a.drs)
    if a.check_arc is not None:
        _, M, _, _ = rows(mr, arc, le, a.check_name, a.check_arc)
        text = open(os.path.join(a.tree, 'port/dreamcast/game/actor_material_records.inc')).read()
        want = re.search(r'^static const Model m_%s_%d = .*$' % (a.check_name, a.check_arc), text, re.M).group(0)
        assert M == want, 'generator check failed:\n%s\n%s' % (M, want)
        print('check m_%s_%d: identical to actor_material_records.inc' % (a.check_name, a.check_arc))
    P, M, B, f = rows(mr, arc, le, 'pl00', 11)
    if a.other:
        _, M2, B2, f2 = rows(mr, archive.Archive(a.other), le, 'pl00', 11)
        assert (M2, B2) == (M, B), 'neck differs between %s and %s' % (a.drs, a.other)
        print('neck arc 0xB identical in both archives')
    if a.out:
        hdr = ['// LEON_HEADLESS (gen_neck_records.py, lane garr18): Leon\'s neck, player archive arc 0xB (pl00 / pl08 identical),',
               '// source BIN sha256 %s. Generated from the original archive; do not edit.' % f['sha256']]
        open(a.out, 'w').write('\n'.join(hdr + P + [M, '#define RE4DC_LEON_NECK_BLOB ' + B.rstrip(',')]) + '\n')
        print('wrote', a.out)


if __name__ == '__main__':
    main()

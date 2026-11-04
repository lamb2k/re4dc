#!/usr/bin/env python3
"""LEON_WOUND (lane bosscast-wound, 2026-11-03): the GameCube identity rows of Leon's chapter 5 wound overlay
(cPlLeon::setWound(): player archive arc 0xE with TPL 0xF, added as a tenth info when pG->Scenario_flg[0] & 0x20, i.e.
after the r317 Krauser knife fight and in every later room) in coarse_actor_material.inc's types, from the original
archive by model_registry.py's bin_facts / tpl_facts (the actor-material inspect rules, imported, not copied).

  gen_wound_records.py <tree> <pl08.drs> [<out.inc>] [--other <pl00.drs>] [--check-arc 8 --check-name pl00]

--check-arc: also emit that arc's Model row and compare it with actor_material_records.inc (generator check, as
gen_neck_records.py). --other: the wound must be identical in the other player archive (pl00 / pl08). The rows are
named m_pl08_14 / p_pl08_14 / t_pl08_15.
"""
import argparse, importlib.util, os, re


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


def tex_rows(mr, arc, parse_tpl, name, no):
    t = mr.tpl_facts(arc, parse_tpl, name, no)
    T = ['static const Texture t_%s_%d[] = {' % (name, no)]
    for r in t['textures']:
        pal = r['palette']
        pf, pd = (0xffffffff, (0, 0, 0)) if not pal else (pal[0], pal[1:])
        T.append('{%uu,%uu,%uu,%uu,%uu,{%s},%uu,{%s}},' % (r['key'][0], r['key'][1], *r['whf'],
                 ','.join(str(v) + 'u' for v in r['sampler']), pf, ','.join(str(v) + 'u' for v in pd)))
    T.append('};')
    return T, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tree'); ap.add_argument('drs'); ap.add_argument('out', nargs='?')
    ap.add_argument('--other'); ap.add_argument('--check-arc', type=int); ap.add_argument('--check-name', default='pl00')
    a = ap.parse_args()
    mr = load(a.tree)
    archive, parse_tpl, le = mr.archive_facts(a.tree)
    arc = archive.Archive(a.drs)
    if a.check_arc is not None:
        _, M, _, _ = rows(mr, arc, le, a.check_name, a.check_arc)
        text = open(os.path.join(a.tree, 'port/dreamcast/game/actor_material_records.inc')).read()
        want = re.search(r'^static const Model m_%s_%d = .*$' % (a.check_name, a.check_arc), text, re.M).group(0)
        assert M == want, 'generator check failed:\n%s\n%s' % (M, want)
        print('check m_%s_%d: identical to actor_material_records.inc' % (a.check_name, a.check_arc))
    P, M, B, f = rows(mr, arc, le, 'pl08', 14)
    T, t = tex_rows(mr, arc, parse_tpl, 'pl08', 15)
    if a.other:
        o = archive.Archive(a.other)
        _, M2, B2, _ = rows(mr, o, le, 'pl08', 14)
        T2, _ = tex_rows(mr, o, parse_tpl, 'pl08', 15)
        assert (M2, B2, T2) == (M, B, T), 'wound differs between %s and %s' % (a.drs, a.other)
        print('wound arc 0xE / TPL 0xF identical in both archives')
    print('parts', f['parts']); print('textures', t['textures'])
    if a.out:
        hdr = ['// LEON_WOUND (gen_wound_records.py, lane bosscast-wound): Leon\'s chapter 5 wound overlay, player archive arc',
               '// 0xE / TPL 0xF (pl00 / pl08 identical), source BIN sha256 %s, TPL sha256 %s.' % (f['sha256'], t['sha256']),
               '// Generated from the original archive; do not edit.']
        open(a.out, 'w').write('\n'.join(hdr + P + [M] + T + ['#define RE4DC_LEON_WOUND_BLOB ' + B.rstrip(',')]) + '\n')
        print('wrote', a.out)


if __name__ == '__main__':
    main()

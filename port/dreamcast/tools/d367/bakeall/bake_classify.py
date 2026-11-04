#!/usr/bin/env python3
"""bake_classify.py (lane bakeall, phase 1): which PS2 world rows of each room can be baked into the room's static
world mesh (ps2_room_r4im.py --bake-static), why the others stay live, and the draw pieces before / after.

    python3 bake_classify.py --src-root <dir with <room>/ or in-<room>/ input sets> ... --repo <repo> --out <dir>

A row is one PS2 SMD row = one OBJ group `PS2SCENARIO#SMD_n#SMX_id#TYPE_t#BIN_b#` (ps2_room_extract.py inputs).
Rules (a row is BAKE only when every one holds; the first failing rule is its reason):
  addr     id < 250: the scroll object table (scroll.cpp scrObjTbl, 250 ids) gives room code, scenario commands
           (sce_com.cpp d->objId), effects (db_port.cpp Parent_no) and PS2_WORLD_DYNAMIC an object to move / hide /
           attach to. Sub-reasons from the room's own source (src/stN/<room>.cpp): code-const (a constant id passed to
           SmdGetObjPtr / SmdSetTrans / SmdTransOff / SmdGetWorkPtr / SmdGetGroupObjPtr), code-var (the room passes a
           variable id), smx-anim; otherwise addr-unref (no reference found in room code; event / effect data not yet
           proven: phase 2 candidate, kept live).
  smx-anim the row's SMX record has a scroll mode (byte 1 != 0: t_scroll swing / rotate / ...) or a UV scroll
           (floats at 0x88 / 0x8C): animated, stays its own placement.
Everything else (id >= 250, no animation) is static: no code can address it (SmdGetObjPtr refuses ids > 0xF9).

Draw pieces (the runtime's part draws, one per placement x material): before = sum over rows of their materials;
after = live rows' pieces + one per material of the baked mesh (its 3 m clusters are cull units inside a part, counted
separately as baked_clusters / baked_cluster_parts).
"""
import argparse, collections, json, re, struct, sys
from pathlib import Path

GROUP = re.compile(r'#SMD_(\d+)#SMX_(\d+)#TYPE_([0-9A-Fa-f]+)#BIN_(\d+)')
CALL = re.compile(r'Smd(GetObjPtr|SetTrans|TransOff|GetWorkPtr|GetGroupObjPtr2?)\(\s*([^,)]+)')
CLUSTER = 3000.0     # --lod-cluster of r10dbake23 (converter world units = OBJ units x 100)


def smx(path):
    d = path.read_bytes()
    out = {}
    for i in range(d[1]):
        e = d[16 + 144 * i:16 + 144 * (i + 1)]
        if len(e) < 144:
            break
        u, v = struct.unpack_from('<ff', e, 0x88)
        out[e[0]] = dict(mode=e[1], uv=(u != 0.0 or v != 0.0))
    return out


def read_obj(path):
    vs, groups, cur, mat = [], [], None, None
    with open(path, encoding='latin-1') as f:
        for line in f:
            if line.startswith('v '):
                vs.append(tuple(float(x) for x in line.split()[1:4]))
            elif line.startswith('g '):
                m = GROUP.search(line)
                if not m:
                    raise SystemExit('%s: unparsed group %s' % (path, line.strip()))
                cur = dict(smd=int(m.group(1)), id=int(m.group(2)), type=m.group(3), bin=int(m.group(4)),
                           faces=[])
                groups.append(cur)
            elif line.startswith('usemtl'):
                mat = line.split(None, 1)[1].strip()
            elif line.startswith('f ') and cur is not None:
                idx = [int(t.split('/')[0]) for t in line.split()[1:]]
                for k in range(1, len(idx) - 1):           # fan, as the converter's reader
                    cur['faces'].append((mat, idx[0], idx[k], idx[k + 1]))
    return vs, groups


def code_refs(repo, room):
    src = repo / 'src' / ('st' + room[1]) / (room + '.cpp')
    const, var, lits = set(), False, set()
    if src.exists():
        text = re.sub(r'//[^\n]*', '', src.read_text(errors='replace'))
        for _, arg in CALL.findall(text):
            arg = arg.strip()
            try:
                const.add(int(arg, 0))
            except ValueError:
                var = True
        if var:
            # a variable id comes from a table, a macro argument or a loop in this file: every integer literal
            # 0..249 in the file, plus every for-loop range, may be one (conservative superset)
            for t in re.findall(r'(?<![\w.])(0[xX][0-9a-fA-F]+|\d+)(?![\w.])', text):
                v = int(t, 0)
                if v < 250:
                    lits.add(v)
            for lo, hi in re.findall(r'for\s*\([^=;]*=\s*(0[xX][0-9a-fA-F]+|\d+)\s*;[^<;]*<=?\s*(0[xX][0-9a-fA-F]+|\d+)', text):
                lits.update(range(int(lo, 0), min(int(hi, 0) + 1, 250)))
    return src.exists(), const, lits


def classify(room, d, repo):
    vs, groups = read_obj(d / f'{room}_004.scenario.obj')
    sm = smx(d / f'{room}_005.SMX')
    has_src, const, var = code_refs(repo, room)
    rows, reasons = [], collections.Counter()
    for g in groups:
        e = sm.get(g['id'], dict(mode=0, uv=False))
        if e['mode'] or e['uv']:
            why = 'smx-anim'
        elif g['id'] < 250:
            why = ('code-const' if g['id'] in const else 'code-var' if g['id'] in var else
                   'addr-unref' if has_src else 'addr-nosrc')
        else:
            why = 'BAKE'
        g['why'] = why
        reasons[why] += 1
    before = sum(len({f[0] for f in g['faces']}) for g in groups)
    live = [g for g in groups if g['why'] != 'BAKE']
    baked_keys = set()
    for g in groups:
        if g['why'] != 'BAKE':
            continue
        for mat, a, b, c in g['faces']:
            p = [vs[i - 1] for i in (a, b, c)]
            cell = tuple(int((sum(q[k] for q in p) / 3 * 100) // CLUSTER) for k in range(3))
            baked_keys.add((cell, mat))
    baked_mats = {k[1] for k in baked_keys}
    after = sum(len({f[0] for f in g['faces']}) for g in live) + len(baked_mats)
    # unique (shared-mesh) triangles before vs after: baking un-instances repeated BINs (size growth)
    tri = lambda gs: sum(len(g['faces']) for g in gs)
    seen, uniq_before = set(), 0
    for g in groups:
        if g['bin'] not in seen:
            seen.add(g['bin']); uniq_before += len(g['faces'])
    seen, uniq_live = set(), 0
    for g in live:
        if g['bin'] not in seen:
            seen.add(g['bin']); uniq_live += len(g['faces'])
    nb = [g for g in groups if g['why'] == 'BAKE']
    return dict(room=room, rows=len(groups), bake_rows=len(nb), live_rows=len(live), reasons=dict(reasons),
                pieces_before=before, pieces_after=after, pieces_removed=before - after, baked_clusters=len({k[0] for k in baked_keys}),
                baked_cluster_parts=len(baked_keys),
                triangles=tri(groups), baked_triangles=tri(nb), mesh_tris_before=uniq_before,
                mesh_tris_after=uniq_live + tri(nb), room_src=has_src, code_const_ids=sorted(const), code_var=sorted(var),
                live=[dict(smd=g['smd'], id=g['id'], bin=g['bin'], why=g['why']) for g in live])


def find_inputs(roots):
    found = {}
    for r in roots:
        for obj in sorted(Path(r).rglob('*_004.scenario.obj')):
            room = obj.name[:4]
            if (obj.parent / f'{room}_005.SMX').exists():
                found.setdefault(room, obj.parent)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src-root', action='append', required=True)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--bytes-per-tri', type=float, default=27.2,
                    help='re4mesh bytes per level-0 triangle (r10dbake23: 1,168,832 B / 43,016 level-0)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    res = []
    for room, d in sorted(find_inputs(a.src_root).items()):
        r = classify(room, d, a.repo)
        r['inputs'] = str(d)
        r['mesh_bytes_before_est'] = int(r['mesh_tris_before'] * a.bytes_per_tri)
        r['mesh_bytes_after_est'] = int(r['mesh_tris_after'] * a.bytes_per_tri)
        res.append(r)
        print('%s rows %4d bake %4d pieces %5d -> %5d  tris %6d->%6d  %s' % (
            room, r['rows'], r['bake_rows'], r['pieces_before'], r['pieces_after'], r['mesh_tris_before'],
            r['mesh_tris_after'], r['reasons']), file=sys.stderr)
    (a.out / 'bake-classify.json').write_text(json.dumps(res, indent=1))
    with open(a.out / 'bake-classify.tsv', 'w') as f:
        f.write('room\trows\tbake\tlive\tpieces_before\tpieces_after\tremoved\tmesh_tris_before\tmesh_tris_after\t'
                'mesh_kb_before_est\tmesh_kb_after_est\tlive_reasons\n')
        for r in sorted(res, key=lambda r: -r['pieces_removed']):
            f.write('%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%s\n' % (
                r['room'], r['rows'], r['bake_rows'], r['live_rows'], r['pieces_before'], r['pieces_after'],
                r['pieces_removed'], r['mesh_tris_before'], r['mesh_tris_after'], r['mesh_bytes_before_est'] // 1024,
                r['mesh_bytes_after_est'] // 1024,
                ','.join('%s=%d' % kv for kv in sorted(r['reasons'].items()) if kv[0] != 'BAKE')))


if __name__ == '__main__':
    main()

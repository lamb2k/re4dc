#!/usr/bin/env python3
"""PS2 Ashley (pl11) converter (lane ps2cast, 2026-10-14; offline only, nothing reaches a disc by itself).

Ashley's GC model has 141 joints; the PS2 model 81. Joints 0..63 are identical (id, parent, rest translation);
GC 64..140 are the GC cloth links the source game solves every frame (pl_cloth.cpp: hair 21, skirt 48, sweater 8),
PS2 64..80 are the PS2's own cloth outputs (hair 5 pendulums, skirt 12), which the DC game never computes.

Cloth: a PS2 vertex's influence on a PS2 cloth joint is replaced by the skin weights of the GC role surface it lies
on (barycentric blend of the nearest GC triangle's corner weights; hair -> the GC extra9 hair cards, skirt -> the GC
extra9 skirt). The PS2 mesh then follows the GC cloth links the source solver already moved: no second solver, no
extra PenCloth calls, no game RNG, nothing per frame beyond the palettes. Non-cloth PS2 weights stay as authored.

Draw slots: the converted weights name at most --max-slots GC joints (default 64; over budget, the lightest GC cloth
links fold into their parents); the mesh is packed on those slots (slot k =
GC joint draw_slots[k]); source.json keeps the complete 141-joint skeleton for the runtime's full source proof
(NATIVE_MODEL_REGISTRY_SLOTS / PS2_ASHLEY: every source joint's parent + rest inverse checked, then the slots bound).

Sections: one per GC model info, in cSubAshley::modelSet order (body 4/5, head 7/0xB, hair 6/8, extra 9/5,
extra 0xA/5, right hand 0xC/5, left hand 0xF/5). PS2 triangles are assigned to the GC role they stand in for: each
PS2 material has a candidate role list and a triangle goes to the candidate whose GC surface is nearest its centroid
(the PS2 merged head + hair into one material; the skirt moved from GC extra 9 into the PS2 body BIN).

Outputs (the ps2_cast.py convert layout, so ps2_cast_native.sh / finish / regcast run unchanged):
  source.json (141 GC bones + draw_slots), mesh.json (slot bones, slot weights), atlas.png, native/, validation.json,
  source-bindings.json. validation.json adds the partition, the weight transfer and a posed check (random joint
  rotations, GC mesh skinned with GC weights vs PS2 mesh with converted weights, both on the same 141 matrices).

--rig selects the PS2 bind and authored weights through RIG_MAP instead of the
surface transfer above; folding is refused. Only the existing game cloth solver runs.

usage: ps2_ashley.py convert <out dir> [--ps2-dat P] [--gc-drs G] [--max-slots 64] [--poses 24] [--hands 0|1|3] [--rig]
Windows Python (numpy, PIL), like ps2_cast.py stage 1.
"""
import argparse, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import ps2_cast as pc  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

AUDIT = Path('//wsl.localhost/Ubuntu-24.04/root/probe/codex-ashley-bone-audit-20261014')
# GC model infos in cSubAshley::modelSet order: role, GC BIN, GC TPL
SECTIONS = [('body', 4, 5), ('head', 7, 0xB), ('hair', 6, 8), ('extra9', 9, 5), ('extraA', 0xA, 5),
            ('right-hand', 0xC, 5), ('left-hand', 0xF, 5)]
# PS2 sources: PS2 BIN, materials, PS2 TPL, candidate GC roles (nearest GC surface wins)
PS2_SOURCES = [(4, [2, 3, 4, 5, 6, 7], 5, ['body']), (4, [0], 5, ['head', 'hair']), (4, [1], 5, ['head']),
               (4, [8], 5, ['extra9', 'extraA']), (9, [0, 1, 2], 8, ['extra9', 'hair']), (9, [3], 8, ['head', 'hair']),
               (0xC, [0], 0x11, ['right-hand']), (0xF, [0], 0x11, ['left-hand'])]
SOURCE_JOINTS = 64          # 0..63 identical on both
CLOTH_DONOR = 'extra9'      # the GC role whose skin carries the GC hair + skirt cloth links
MODEL_ID = 3                # pSUB->id == 3: Ashley
PRESET = 'ashley11'         # ps2_cast.py PRESETS entry (finish / regcast metadata)
# cSubAshley::setHand(no): right / left hand BINs (TPL 5) for hand sets 0 (open), 1, 3; one descriptor per set
HAND_SETS = {0: (0xC, 0xF), 1: (0xD, 0x10), 3: (0xE, 0xF)}
# ASHLEY_PS2_RIG: PS2 hair 64..68 and skirt 69..80 take the skin delta of the
# nearest existing solver link in the same garment (pl_cloth.cpp girlHairP /
# girlSkirtP). Unlike surface transfer, each PS2 influence survives as authored.
# The simulation uses its own inverse bind, exactly as LEON_PS2_RIG does.
RIG_MAP = {64: 70, 65: 73, 66: 76, 67: 79, 68: 82, 69: 104, 70: 98,
           71: 95, 72: 140, 73: 136, 74: 133, 75: 110, 76: 116,
           77: 119, 78: 122, 79: 124, 80: 127}


def rig_weights(weights):
    """PS2 weights on the animation adapter; never surface-transfer or fold."""
    acc = {}
    for bone, weight in weights:
        if not isinstance(bone, int) or bone < 0 or not math.isfinite(weight) or weight < 0 or weight > 1:
            raise ValueError(f'Invalid PS2 skin influence {(bone, weight)}')
        if weight == 0:
            continue
        if bone >= SOURCE_JOINTS and bone not in RIG_MAP:
            raise ValueError(f'Unmapped PS2 cloth bone {bone}')
        joint = RIG_MAP.get(bone, bone)
        acc[joint] = acc.get(joint, 0.0) + weight
    if not 1 <= len(acc) <= 3 or abs(sum(acc.values()) - 1.0) > .002:
        raise ValueError(f'Invalid PS2 skin weights {weights}')
    total = sum(acc.values())
    return {b: w / total for b, w in acc.items()}


def select_hands(n):
    """the sections / PS2 sources / preset name of hand set n (0 = the defaults above)"""
    global SECTIONS, PS2_SOURCES, PRESET
    r, l = HAND_SETS[n]
    SECTIONS = SECTIONS[:5] + [('right-hand', r, 5), ('left-hand', l, 5)]
    PS2_SOURCES = PS2_SOURCES[:6] + [(r, [0], 0x11, ['right-hand']), (l, [0], 0x11, ['left-hand'])]
    PRESET = 'ashley11' if n == 0 else f'ashley11-h{n}'


def world_positions(bones):
    w = {}
    for b in bones:
        p = np.asarray(b['pos'], float)
        w[b['id']] = p + (w[b['parent']] if b['parent'] >= 0 else 0)
    return w


def nearest_surface(points, verts, tris, k=24):
    """per point: (distance, triangle index, barycentric (3,)) of the closest point on the mesh."""
    A, B, C = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    cen = (A + B + C) / 3
    out_d, out_t, out_b = [], [], []
    for s in range(0, len(points), 256):
        P = points[s:s + 256]
        cand = np.argsort(((P[:, None, :] - cen[None]) ** 2).sum(-1), axis=1)[:, :k]
        q = pc.closest_on_triangles(P[:, None, :], A[cand], B[cand], C[cand])
        d = np.sqrt(((q - P[:, None, :]) ** 2).sum(-1))
        j = d.argmin(1)
        ti = cand[np.arange(len(P)), j]; qq = q[np.arange(len(P)), j]
        a, b, c = A[ti], B[ti], C[ti]
        v0, v1, v2 = b - a, c - a, qq - a
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = np.where(np.abs(d00 * d11 - d01 * d01) < 1e-12, 1e-12, d00 * d11 - d01 * d01)
        bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den
        bary = np.clip(np.stack([1 - bv - bw, bv, bw], 1), 0, 1)
        bary /= bary.sum(1, keepdims=True)
        out_d.append(d.min(1)); out_t.append(ti); out_b.append(bary)
    return np.concatenate(out_d), np.concatenate(out_t), np.concatenate(out_b)


def top3(acc):
    w = sorted(((b, v) for b, v in acc.items() if v > 1e-6), key=lambda x: (-x[1], x[0]))[:3]
    s = sum(v for _, v in w)
    return [(b, v / s) for b, v in sorted(w)]


def pose_mats(gb, rng, body_deg=12.0, cloth_deg=30.0):
    """world matrices of a random pose: every joint rotated about a random axis in its parent frame."""
    W = []
    for b in gb:
        ang = math.radians(rng.uniform(-1, 1) * (cloth_deg if b['id'] >= SOURCE_JOINTS else body_deg))
        ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        L = np.eye(4); L[:3, :3] = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
        L[:3, 3] = b['translation']
        W.append(L if b['parent'] < 0 else W[b['parent']] @ L)
    rest = np.asarray([b['rest'] for b in gb])
    return np.asarray(W) @ np.linalg.inv(rest)


def convert(out, ps2_dat, gc_drs, max_slots=64, poses=24, bone_tol=0.001, rig=False):
    out.mkdir(parents=True, exist_ok=True)
    pd, gd = Path(ps2_dat).read_bytes(), Path(gc_drs).read_bytes()
    ps2 = {i: (t, b) for i, t, b in pc.pb.dat_entries(pd)}
    gc = pc.drs.Drs(gd)
    ptd = pc.load_module('ps2_tpl_decode', pc.WA / 'from-main/ps2-trees/tools/ps2_tpl_decode.py')
    # preset / inputs.gc.cache / sections[].bones + palettes: what ps2_cast.py finish and regcast read
    val = dict(tool='ps2_ashley.py', preset=PRESET, inputs=dict(ps2=dict(path=str(ps2_dat), bytes=len(pd), sha256=pc.sha(pd)),
                                                               gc=dict(cache=str(gc_drs), bytes=len(gd), sha256=pc.sha(gd))))
    # ---- skeletons
    gbody = pc.gc_entry(gc, 4, 'BIN')
    gb = pc.gc_skeleton(gbody)
    assert all(b['attach'] == b['id'] for b in gb), 'GC parts with attach != index'
    n_src = len(gb)
    gworld = np.asarray([np.asarray(b['rest'])[:3, 3] for b in gb])
    pbins = {arc: pc.pb.parse_bin(pc.ps2_entry(ps2, arc, 'BIN')) for arc in sorted({s[0] for s in PS2_SOURCES})}
    p4 = world_positions(pbins[4].bones)
    skel = dict(gc_joints=n_src, ps2_joints=len(pbins[4].bones))
    for arc, m in pbins.items():
        # a reduced bone table (BIN 9, the hands) roots its first bone at parent -1 with its model-space position
        full = len(m.bones) == len(pbins[4].bones)
        wp = world_positions(m.bones)
        for b in m.bones:
            if b['id'] < SOURCE_JOINTS:
                g = gb[b['id']]
                assert b['parent'] == g['parent'] or (not full and b['parent'] < 0), (hex(arc), b['id'], b['parent'], g['parent'])
                d = float(np.abs(wp[b['id']] - gworld[b['id']]).max())
            else:
                d = float(np.abs(wp[b['id']] - p4[b['id']]).max())
            assert d <= max(bone_tol, 0.01), (hex(arc), b['id'], 'joint position differs', d)
    skel['ps2_cloth_joints'] = {str(i): dict(parent=next(b['parent'] for b in pbins[4].bones if b['id'] == i),
                                             world=[round(float(x), 2) for x in p4[i]])
                                for i in sorted(p4) if i >= SOURCE_JOINTS}
    val['skeleton'] = skel
    # ---- GC role meshes (rest), every section's skeleton = the body's
    gmesh, gsig = {}, {}
    attach = {}
    for role, arc, tpl in SECTIONS:
        gbin = pc.gc_entry(gc, arc, 'BIN')
        parts = pc.modelbin.parse(gbin).parts
        g = pc.gc_mesh(gbin)
        if len(parts) == n_src:
            gsk = pc.gc_skeleton(gbin)
            assert all(a['parent'] == b['parent'] and max(abs(x - y) for x, y in zip(a['translation'], b['translation'])) <= bone_tol
                       for a, b in zip(gsk, gb)), role
        else:
            # an attachment model (head, hair, extra 0xA, hands): a local part table whose attach ids name the body's
            # joints; its skin weights already name those global joints
            amap = [p.attach for p in parts]
            assert all(0 <= a < n_src for a in amap) and len(set(amap)) == len(amap), (role, amap)
            assert {b for w in g['weights'] for b, _ in w} <= set(amap), (role, 'weights outside the attach table')
            attach[role] = amap
        gmesh[role] = g
        gsig[role] = (gbin, tpl)
    val['skeleton']['attachment_sections'] = attach
    # ---- textures: one atlas from the PS2 TPLs the sources use
    images, tpl_base = [], {}
    for tpl_arc in sorted({s[2] for s in PS2_SOURCES}):
        tpl = pc.ps2_entry(ps2, tpl_arc, 'TPL'); tp = ptd.parse_tpl(tpl)
        tpl_base[tpl_arc] = len(images)
        for h in tp['entries']:
            w, ht, rgba, st = ptd.decode(tpl, h)
            images.append(dict(index=len(images), tpl=hex(tpl_arc), width=w, height=ht, rgba=bytes(rgba),
                               alpha_raw=sorted(st['alpha_raw_hist'])))
    # ---- PS2 triangles -> GC roles
    role_index = {r: i for i, (r, _, _) in enumerate(SECTIONS)}
    tris_out, used_images, part = [], [], {}
    for arc, mats, tpl_arc, cands in PS2_SOURCES:
        m = pbins[arc]
        for mi, corners in pc.pb.triangles(m):
            if mi not in mats:
                continue
            img = tpl_base[tpl_arc] + m.materials[mi]['diffuse']
            assert img < len(images) and images[img]['tpl'] == hex(tpl_arc), (hex(arc), mi)
            if img not in used_images:
                used_images.append(img)
            tris_out.append(dict(arc=arc, mat=mi, img=img, cands=cands, corners=corners))
    cent = np.asarray([np.mean([c['p'] for c in t['corners']], 0) for t in tris_out])
    dist = {}
    for role in role_index:
        idx = [k for k, t in enumerate(tris_out) if role in t['cands']]
        if idx:
            g = gmesh[role]
            d, _, _ = nearest_surface(cent[idx], g['positions'], g['triangles'])
            for k, x in zip(idx, d):
                dist[(k, role)] = float(x)
    for k, t in enumerate(tris_out):
        t['role'] = min(t['cands'], key=lambda r: (dist[(k, r)], role_index[r]))
        key = f'{t["arc"]:x}.{t["mat"]}->{t["role"]}'
        part[key] = part.get(key, 0) + 1
    val['partition'] = dict(sorted(part.items()))
    missing = [r for r in role_index if not any(t['role'] == r for t in tris_out)]
    if missing:
        raise SystemExit(f'GC roles with no PS2 triangle: {missing} (a covered-role contract would be needed)')
    # ---- weights: PS2 non-cloth kept, PS2 cloth influence -> the GC donor surface's weights
    donor = gmesh[CLOTH_DONOR]
    cloth_pts, cloth_keys = [], []
    for t in tris_out:
        for c in t['corners']:
            if any(b >= SOURCE_JOINTS and v > 0 for b, v in c['w']):
                cloth_pts.append(c['p']); cloth_keys.append(id(c))
    tw = dict(cloth_corners=len(cloth_pts))
    if cloth_pts and not rig:
        d, ti, bary = nearest_surface(np.asarray(cloth_pts, float), donor['positions'], donor['triangles'])
        tw.update(donor=CLOTH_DONOR, donor_distance_mm=dict(median=float(np.median(d)), p95=float(np.percentile(d, 95)), max=float(d.max())))
        donor_w = {}
        for key, t3, bb in zip(cloth_keys, ti, bary):
            acc = {}
            for corner, f in zip(donor['triangles'][t3], bb):
                for b, v in donor['weights'][corner]:
                    acc[b] = acc.get(b, 0.0) + f * v
            donor_w[key] = acc
    truncated = 0
    for t in tris_out:
        for c in t['corners']:
            if rig:
                c['acc'] = rig_weights(c['w'])
                c['gw'] = sorted(c['acc'].items())
                continue
            acc = {}
            cloth = 0.0
            for b, v in c['w']:
                if v <= 0:
                    continue
                if b >= SOURCE_JOINTS:
                    cloth += v
                else:
                    acc[b] = acc.get(b, 0.0) + v
            if cloth:
                for b, v in donor_w[id(c)].items():
                    acc[b] = acc.get(b, 0.0) + cloth * v
            if sum(1 for v in acc.values() if v > 1e-6) > 3:
                truncated += 1
            c['acc'] = acc
            c['gw'] = top3(acc)
    tw['corners_truncated_to_3'] = truncated
    # Draw-slot budget (--max-slots, default 64 = the test 11 recipe's NATIVE_MODEL_REGISTRY_BONES, which PS2_GIGANTE
    # pins outside ROUTE_CH23): while over budget, the GC cloth link carrying the least total weight folds into its
    # parent (another solver-moved link, or the head / pelvis / thigh joint it hangs from).
    folded = []
    while True:
        slots = sorted({b for t in tris_out for c in t['corners'] for b, _ in c['gw']})
        if len(slots) <= max_slots:
            break
        if rig:
            raise ValueError(f'PS2 rig needs {len(slots)} slots; refusing to fold authored influences to {max_slots}')
        tot = {}
        for t in tris_out:
            for c in t['corners']:
                for b, v in c['gw']:
                    tot[b] = tot.get(b, 0.0) + v
        cloth = [b for b in slots if b >= SOURCE_JOINTS]
        if not cloth:
            raise SystemExit(f'{len(slots)} draw slots > {max_slots} and no cloth link left to fold')
        j = min(cloth, key=lambda b: (tot[b], b)); par = gb[j]['parent']
        folded.append(dict(joint=j, into=par, weight=round(tot[j], 3)))
        for t in tris_out:
            for c in t['corners']:
                if j in c['acc']:
                    c['acc'][par] = c['acc'].get(par, 0.0) + c['acc'].pop(j)
                    c['gw'] = top3(c['acc'])
    tw['folded_cloth_links'] = folded
    slot_of = {b: k for k, b in enumerate(slots)}
    tw['draw_slots'] = len(slots); tw['gc_cloth_slots'] = [b for b in slots if b >= SOURCE_JOINTS]
    val['weights'] = tw
    # ---- atlas
    used_images.sort()
    cells, (aw, ah) = pc.pack_atlas([(k, images[k]['width'], images[k]['height']) for k in used_images])
    atlas = Image.new('RGBA', (aw, ah), (0, 0, 0, 255))
    for k in used_images:
        im = images[k]
        atlas.paste(Image.frombytes('RGBA', (im['width'], im['height']), im['rgba']), cells[k][:2])
    atlas.convert('RGB').convert('RGBA').save(out / 'atlas.png')
    # the PS2 alpha (ps2_tpl_decode.py scales 0x80 to 255) for ps2_mask_runs.py --atlas-rgba (the hair cards' own alpha)
    atlas.save(out / 'atlas-rgba.png')
    val['texture'] = dict(images=[{k: v for k, v in im.items() if k != 'rgba'} for im in images], used=used_images,
                          atlas=[aw, ah], cells={str(k): v for k, v in cells.items()},
                          opaque=all(a >= 128 for k in used_images for a in images[k]['alpha_raw']))
    # ---- mesh (slot weights), winding as ps2_cast.py: follow the GC convention
    vert_index, positions, weights, gweights, triangles = {}, [], [], [], []
    degenerate = zero_n = 0
    for t in sorted(tris_out, key=lambda t: role_index[t['role']]):
        cx, cy, cw, ch = cells[t['img']]
        P3 = [np.asarray(c['p'], float) for c in t['corners']]
        face = np.cross(P3[1] - P3[0], P3[2] - P3[0])
        if not np.linalg.norm(face):
            degenerate += 1
            continue
        face /= np.linalg.norm(face)
        uvs = [c['raw']['uv'] for c in t['corners']]
        if any(not -1 <= x <= 257 for uv in uvs for x in uv):
            raise SystemExit(f'PS2 UV outside its image: {hex(t["arc"])} mat {t["mat"]} {uvs}')
        cs = []
        for c, (ru, rv) in zip(t['corners'], uvs):
            ru, rv = min(256, max(0, ru)), min(256, max(0, rv))
            n = c['n'] if any(c['n']) else tuple(face)
            zero_n += not any(c['n'])
            wk = tuple((slot_of[b], round(v, 6)) for b, v in c['gw'])
            key = (tuple(round(x, 5) for x in c['p']), wk)
            if key not in vert_index:
                vert_index[key] = len(positions)
                positions.append([float(x) for x in c['p']])
                weights.append([[s, v] for s, v in wk]); gweights.append(c['gw'])
            cs.append(dict(vertex=vert_index[key], normal=[float(x) for x in n],
                           uv=[(cx + ru * cw / 256.0) / aw, (cy + rv * ch / 256.0) / ah]))
        triangles.append(dict(source_info=role_index[t['role']], corners=cs))
    P = np.asarray(positions)
    val.update(degenerate_triangles_dropped=degenerate, zero_normals_replaced_by_face_normal=zero_n)
    flips = []
    for si, (role, _, _) in enumerate(SECTIONS):
        g = gmesh[role]
        ts = [t for t in triangles if t['source_info'] == si]
        g_ok = pc.winding_agreement(g['positions'], g['triangles'], g['corner_normals'])
        p_ok = pc.winding_agreement(P, np.asarray([[c['vertex'] for c in t['corners']] for t in ts]),
                                    [[np.asarray(c['normal']) for c in t['corners']] for t in ts])
        flips.append((p_ok > .5) != (g_ok > .5))
    assert len(set(flips)) == 1, f'sections disagree on the winding flip {flips}'
    if flips[0]:
        for t in triangles:
            t['corners'] = t['corners'][::-1]
    val['winding_flipped'] = bool(flips[0])
    # ---- source.json (full GC skeleton + slots) and mesh.json (slot bones)
    bones = [dict(id=b['id'], parent=b['parent'], address=f'pl11:part:{b["id"]}', rest=b['rest'], capture=b['capture']) for b in gb]
    if rig:
        # Shared animated bones are PS2 rests. Extra game parts remain solely the
        # source hierarchy proof; garment slots read the solver bind at runtime.
        for i in range(SOURCE_JOINTS):
            rest = np.eye(4); rest[:3, 3] = p4[i]
            bones[i].update(rest=rest.tolist(), capture=rest.tolist())
    infos = [dict(id=si, address=f'pl11:arc:{arc:03x}', source_data_address=f'pl11:arc:{arc:03x}', source_bin_arc=arc,
                  source_tpl_arc=tpl, source_sha256=pc.sha(pc.gc_entry(gc, arc, 'BIN')), role=role,
                  gc_positions=len(gmesh[role]['positions']), gc_triangles=len(gmesh[role]['triangles']))
             for si, (role, arc, tpl) in enumerate(SECTIONS)]
    source = dict(name=PRESET, schema='ps2cast-source-1', source_units='millimetres', source_archive='pl11',
                  source_archive_sha256=pc.sha(gd), ps2_archive_sha256=pc.sha(pd), bones=bones, draw_slots=slots,
                  infos=infos, category='registry', rooms=['r117'], types=[], source_model_id=MODEL_ID)
    if rig:
        source['ps2_rig'] = dict(schema='ashley-ps2-rig-1', ps2_archive_sha256=pc.sha(pd),
                                 shared_bones=SOURCE_JOINTS, ps2_bones=81, rig_map=RIG_MAP,
                                 simulation_bind='runtime lt_inv_mat', solver='existing game hair/skirt only')
        tw.update(mode='PS2 rig map; authored weights', rig_map=RIG_MAP)
    sp = out / 'source.json'
    sp.write_text(json.dumps(source))
    slot_bones = [dict(bones[b], id=k, parent=-1, source_joint=b) for k, b in enumerate(slots)]
    mesh = dict(schema='re4dc-approved-render-mesh-1', source_sha256=pc.sha(sp.read_bytes()), mesh='ashley11_ps2',
                positions_mm=positions, weights=weights, bones=slot_bones, triangles=triangles,
                policy='PS2 source geometry, normals, UVs and skin weights; PS2 cloth influences transferred to the GC '
                       'cloth links (barycentric GC extra9 skin); weights on draw slots (slot k = GC joint draw_slots[k]).')
    if rig:
        mesh['policy'] = ('PS2 pl11 geometry, textures, shared skeleton rests and authored weights; PS2 hair/skirt '
                          'driven through RIG_MAP by existing game simulation, with its own runtime bind. No folding.')
    (out / 'mesh.json').write_text(json.dumps(mesh))
    # ---- checks: rest + posed surface distance per section
    rng = np.random.default_rng(1014)
    mats = [pose_mats(gb, rng) for _ in range(poses)]
    secs = []
    for si, (role, arc, tpl) in enumerate(SECTIONS):
        g = gmesh[role]
        ts = [t for t in triangles if t['source_info'] == si]
        vids = sorted({c['vertex'] for t in ts for c in t['corners']})
        pv = P[vids]
        d0, cand = pc.surface_distance(pv, g['positions'], g['triangles'])
        remap = {v: i for i, v in enumerate(vids)}
        ptl = np.vectorize(remap.get)(np.asarray([[c['vertex'] for c in t['corners']] for t in ts]))
        g0, _ = pc.surface_distance(g['positions'], pv, ptl)
        worst = []
        for M in mats:
            pp = pc.skin(pv, [gweights[v] for v in vids], M)
            gp = pc.skin(g['positions'], g['weights'], M)
            dk, _ = pc.surface_distance(pp, gp, g['triangles'], cand)
            worst.append((float(np.percentile(dk, 95)), float(dk.max())))
        secs.append(dict(role=role, gc_bin=hex(arc), gc_tpl=hex(tpl), ps2_triangles=len(ts), gc_triangles=len(g['triangles']),
                         bones=len(slots), gc_palettes=g['palettes'],
                         ps2_palettes=len({tuple(map(tuple, gweights[v])) for v in vids}),
                         ps2_positions=len(vids), gc_positions=len(g['positions']),
                         rest_ps2_to_gc_mm=dict(median=float(np.median(d0)), p95=float(np.percentile(d0, 95))),
                         rest_gc_to_ps2_mm=dict(median=float(np.median(g0)), p95=float(np.percentile(g0, 95)),
                                                within_2mm=float((g0 < 2).mean()), within_5mm=float((g0 < 5).mean())),
                         posed_ps2_to_gc_mm=dict(poses=poses, p95_median=float(np.median([w[0] for w in worst])),
                                                 p95_max=max(w[0] for w in worst))))
    val['sections'] = secs
    # ---- pack (the cast packer, unchanged) on the slot skeleton + host fixture
    pk = pc.load_module('pack_coarse_actor', pc.PROTO / 'tools/pack_coarse_actor.py')
    native = out / 'native'
    if native.exists():
        shutil.rmtree(native)
    pk.pack(out / 'mesh.json', sp, native, 'castmodel')
    pc.host_fixture(native, dict(source, bones=slot_bones))
    report = json.loads((native / 'native-report.json').read_text())
    val['native'] = {k: v for k, v in report.items() if k != 'chunks'}
    val['native']['chunks'] = [{k: v for k, v in c.items() if k != 'palette_weights'} for c in report['chunks']]
    binds = [dict(bin=arc, tpl=tpl, role=role, **pc.gc_signature(pc.gc_entry(gc, arc, 'BIN')),
                  binding_scope='GC source array signature (the loaded model the PS2 mesh replaces)') for role, arc, tpl in SECTIONS]
    (out / 'source-bindings.json').write_text(json.dumps(binds, indent=2))
    val['texture']['key'] = pc.texture_key(out / 'atlas.png')
    (out / 'validation.json').write_text(json.dumps(val, indent=1))
    print(json.dumps(dict(partition=val['partition'], weights={k: v for k, v in tw.items() if k != 'gc_cloth_slots'},
                          atlas=[aw, ah], triangles=report['triangles'], array_bytes=report['array_bytes'],
                          sections=[{k: s[k] for k in ('role', 'ps2_triangles', 'gc_triangles', 'rest_ps2_to_gc_mm',
                                                       'rest_gc_to_ps2_mm', 'posed_ps2_to_gc_mm')} for s in secs]), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('convert')
    c.add_argument('out', type=Path)
    c.add_argument('--ps2-dat', default=str(AUDIT / 'pl11-PS2.dat'))
    c.add_argument('--gc-drs', default=str(AUDIT / 'pl11-GC.drs'))
    c.add_argument('--max-slots', type=int, default=64)
    c.add_argument('--poses', type=int, default=24)
    c.add_argument('--hands', type=int, default=0, choices=sorted(HAND_SETS))
    c.add_argument('--rig', action='store_true', help='PS2 bind/weights, existing hair/skirt solver through RIG_MAP')
    a = ap.parse_args()
    select_hands(a.hands)
    convert(a.out, a.ps2_dat, a.gc_drs, a.max_slots, a.poses, rig=a.rig)


if __name__ == '__main__':
    main()

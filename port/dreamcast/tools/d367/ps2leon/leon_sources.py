#!/usr/bin/env python3
"""Leon render-mesh sources for the ps2leon lane (2026-10-10): the eight roles of the play Leon (pl00, appearance
0x100) from the GameCube debug disc and the PS2 disc, plus today's play mesh (leon-hair-v2 mesh.json).

Role order = the runtime's leon4k chunk order (coarse_actor_owner_leon.inc), each role one GC model info:
  0 body       pl00 arc 0x004 (119 parts)          4 head        pl00 arc 0x006 (33 parts, attachment)
  1 jacket     pl00 arc 0x00a (117 parts)          5 right hand  wep02 arc 0x00a (2 parts; every weapon carries it)
  2 role 2     pl00 arc 0x00d (119 parts)          6 left hand   pl00 arc 0x018 (2 parts)
  3 face       pl00 arc 0x008 (35 parts, bone-driven expressions)   7 hair  pl00 arc 0x009 (33 parts, 2nd pass)
The PS2 disc has the same entries at the same arcs (pl00.dat / wep02.dat).

GC geometry: convert_character.parse_geometry (the native converter's reader). GC part attach ids map attachment
models' local parts to the 119-part skeleton. PS2 geometry: ps2_bin (JADERLINK BIN layout).

Paths (environment, defaults = the Windows host layout; the tools run with the host's Python, numpy, Pillow):
  PS2LEON_TREE  the checkout (default: the one holding this file)
  PS2LEON_WORK  the work dir: inputs/ (archives cut from the discs, cached), arms/, renders/, counts.json, sheets
  RE4_PRIVATE   re4-assets-private;  RE4_GC_ISO / RE4_PS2_ISO  the GameCube debug disc 1 / the PS2 USA disc
"""
import json, os, struct, sys
from pathlib import Path
import numpy as np

TREE = Path(os.environ.get('PS2LEON_TREE') or Path(__file__).resolve().parents[5])
sys.path[:0] = [str(TREE / 'port/dreamcast/tools'), str(TREE / 'tools')]
import ps2_bin as pb  # noqa: E402
import drs  # noqa: E402
from motion import modelbin  # noqa: E402
import convert_character as cc  # noqa: E402

WORK = Path(os.environ.get('PS2LEON_WORK', 'C:/Game Dev/Emulators/ps2leon-20261010'))
IN = WORK / 'inputs'
GC_ISO = os.environ.get('RE4_GC_ISO', 'C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso')
PS2_ISO = os.environ.get('RE4_PS2_ISO', 'C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso')
PRIV = Path(os.environ.get('RE4_PRIVATE', 'C:/Game Dev/Emulators/re4-assets-private'))
PROTO = PRIV / 'character-prototype-20260925'
LEON_MESH = PROTO / 'runtime/leon-hair-v2/mesh.json'
LEON_SOURCE = PROTO / 'source/leon-source.json'

ROLES = [(0x004, 'pl', 'body'), (0x00a, 'pl', 'jacket'), (0x00d, 'pl', 'role2'), (0x008, 'pl', 'face'),
         (0x006, 'pl', 'head'), (0x00a, 'wep', 'right-hand'), (0x018, 'pl', 'left-hand'), (0x009, 'pl', 'hair')]
REGIONS = ['head', 'torso', 'arms', 'legs']
REGION_TITLE = {'head': 'head/face/hair', 'torso': 'torso/back/shoulders', 'arms': 'arms/hands', 'legs': 'legs/feet'}


def _cached(name, fn):
    p = IN / name
    if not p.exists():
        IN.mkdir(parents=True, exist_ok=True)
        p.write_bytes(fn())
    return p.read_bytes()


def gc_archives():
    from assetpipe.rooms import GcIso
    iso = None

    def rd(n):
        nonlocal iso
        iso = iso or GcIso(GC_ISO)
        return iso.read(iso.find(n))
    return drs.Drs(_cached('pl00.drs', lambda: rd('em/pl00.drs'))), drs.Drs(_cached('wep02.drs', lambda: rd('em/wep02.drs')))


def ps2_archives():
    pl = {i: (t, b) for i, t, b in pb.dat_entries(_cached('ps2-pl00.dat', lambda: pb.afs_read(PS2_ISO, 'pl00.dat')))}
    wp = {i: (t, b) for i, t, b in pb.dat_entries(_cached('ps2-wep02.dat', lambda: pb.afs_read(PS2_ISO, 'wep02.dat')))}
    return pl, wp


def gc_skeleton():
    """The 119-part skeleton (pl00 body BIN): parents and accumulated rest translations (mm)."""
    gpl, _ = gc_archives()
    body = modelbin.parse(gpl.entries[0][1])
    rest = np.zeros((len(body.parts), 3))
    for p in body.parts:
        rest[p.no] = np.array(p.pos) + (rest[p.parent] if p.parent >= 0 else 0)
    return [p.parent for p in body.parts], rest


def bone_regions(parents):
    """Region of each of the 119 bones by skeleton structure (GC pl00): the head subtree (bone 3 neck and below:
    4 head, 26-28 / 32-33 head children, 64-85 face and hair bones), the legs (17 and its subtree: both legs, 31),
    the arms (the subtrees under the shoulder bones 5 / 11 except the shoulder bones themselves and their torso
    helpers 113 / 114), the torso (0, 1, 2, 5, 11, 29, 30 and the chest's jacket bones 86-112, 115, 116)."""
    n = len(parents)
    def subtree(r):
        out = {r}
        for i in range(n):
            j = i
            while j >= 0:
                if j == r:
                    out.add(i)
                    break
                j = parents[j]
        return out
    reg = ['torso'] * n
    for b in subtree(3):
        reg[b] = 'head'
    for b in subtree(17):
        reg[b] = 'legs'
    for s in (5, 11):
        for b in subtree(s):
            if b not in (5, 11, 113, 114):
                reg[b] = 'arms'
    return reg


def gc_role(role):
    """GC section: dict(positions (n,3) mm, weights [[(bone119, w)]] per position, tris [(i,j,k)] position ids,
    corners [(pos, normal(3), uv(2), material)] per triangle corner, materials, uvs raw)."""
    gpl, gwep = gc_archives()
    arc, src, name = ROLES[role]
    d = (gpl if src == 'pl' else gwep).entries[arc - 4][1]
    mdl = modelbin.parse(d)
    attach = [p.attach for p in mdl.parts]
    (positions, pal, ws, norm, normpal, ds, dn, nc, uv, indices, batches, bindings, *_rest) = cc.parse_geometry(d)
    # GC weight entries name skeleton bones directly (0..118), also in the attachment models (head, face, hair,
    # hands: e.g. the face [3, 4, 27, 28]); the attachment parts list only places the model.
    weights = []
    for ids, pct in ws:
        rates, total = [], 0.0
        for k, b in enumerate(ids):
            assert b < 119, (name, b)
            f = pct[k] * .01 if k < len(ids) - 1 else 1 - total
            rates.append((b, f)); total += f
        weights.append(rates)
    tri_material = []
    for first, count, material, part_index in batches:
        tri_material += [(material, part_index)] * (count // 3)
    nrm = np.asarray(norm, float)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    tris, corners = [], []
    for k in range(0, len(indices), 3):
        t = indices[k:k + 3]
        tris.append(tuple(ds[j] for j in t))
        corners.append([(ds[j], nrm[dn[j]], uv[j]) for j in t])
    return dict(role=role, name=name, positions=np.asarray(positions, float), weights=[weights[p] for p in pal],
                tris=np.asarray(tris, int), corners=corners, tri_material=tri_material, bindings=bindings, attach=attach,
                flags=struct.unpack_from('>I', d, 0x20)[0], data=d)


def ps2_role(role, rest119=None):
    """PS2 section: bones (id, parent, accumulated rest), triangles as corner dicts (ps2_bin.triangles)."""
    pl, wp = ps2_archives()
    arc, src, name = ROLES[role]
    t, d = (pl if src == 'pl' else wp)[arc - 4]
    assert t == 'BIN'
    m = pb.parse_bin(d)
    ids = [b['id'] for b in m.bones]
    rest = np.zeros((len(m.bones), 3))
    for i, b in enumerate(m.bones):
        par = b['parent']
        rest[i] = np.array(b['pos']) + (rest[ids.index(par)] if par >= 0 and par in ids else 0)
    tris = pb.triangles(m)
    return dict(role=role, name=name, bin=m, bone_ids=ids, bone_parents=[b['parent'] for b in m.bones], bone_rest=rest,
                tris=tris, data=d)


def leon_mesh():
    return json.loads(LEON_MESH.read_text())


def dominant_bone(weights):
    return max(weights, key=lambda bw: bw[1])[0]


def triangle_region(corner_weights, regions):
    """Region of a triangle: the region with the largest summed weight over its three corners."""
    acc = {}
    for ws in corner_weights:
        for b, w in ws:
            acc[regions[b]] = acc.get(regions[b], 0) + w
    return max(acc.items(), key=lambda kv: (kv[1], -REGIONS.index(kv[0])))[0]

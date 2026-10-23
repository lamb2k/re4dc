#!/usr/bin/env python3
"""Any PS2 room's authored scenario (JADERLINK OBJ export) -> R4IM v3 prelit mesh + R4PW sidecar + RE4DCTX
textures, for PS2_WORLD_MESH (native_static.cpp ps2_open / ps2_pass). The r101 package came from the
full-wrapper-v5 .r4p through ps2-world-20260927 prepare.py -> gain-v1 -> generate_data.py ->
world-mesh-r21/tools/ps2_world_r4im.py; this tool runs the same rules straight from the OBJ so r100 and r103
(and later rooms) get the same world:

* geometry: OBJ `v x y z r g b a` x100 = world millimetres; one OBJ group = one SMD row (BIN at its placement);
  UV = vt x 255/256 (prepare.py); faces keep the OBJ winding (checked against the r101 wrapper by
  validate_r101.py).
* colour: COLOR groups = authored vertex RGB (/128 already applied by the export, may exceed 1); NORMAL groups
  = the GameCube LIT cut-0 parallel sun + sky lights at the SMD origin (ow_extract.gx_light + prepare.py
  light_world; r101 used lights 0 and 5, --lights picks the room's pair).
* per-texture gain (gain_feasibility.py): g = min(max(1, max COLOR vertex channel), 255 / max texel channel);
  the texture is multiplied by g and every vertex colour by float32(1/g), clamped, rounded to 8 bits
  (ps2src.corner_rgba), then ARGB1555 prelit (convert_lod color_mode="prelit").
* textures: TPL decoded GS-swizzled (ps2_tpl_decode.cmd_decode); opaque -> VQ RGB565 (pack_vq.py k-means,
  seed 417, 16 rounds, exact codebook when <= 256 distinct blocks), cutout -> ARGB1555, graded -> ARGB4444
  (pack_textures.py), all on the gained image; VQ only when smaller than native16.
* pass = the texture's alpha mode (0 OP, 1 PT cutout, 2 TR graded) when material_flag & 4, else 0; cull from
  the SMX row (PS2 0 back-face cull -> part cull 2, 1 -> 1, 2 both -> 0), as generate_data.py.
* instancing: groups of the same BIN whose corners are an exact affine image of an earlier group (same
  faces, UVs, final colour bytes) share its mesh through an R4PW placement (the fitted affine); the rest get
  their own mesh in world space (identity placement).
usage: ps2_room_r4im.py <room> <input dir> <out dir> [--lights 0,4]
"""
import argparse, collections, hashlib, importlib.util, json, math, struct, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image

import os
HERE = Path(__file__).resolve().parent
# Runs on Windows Python (numpy, PIL). RE4_WORLD_AGENT: the private world-agent-20260926 tree (OBJ-reader,
# TPL decoder, RE4DCTX codec, gx_light and VQ helpers); RE4_TOOLS: the repo's port/dreamcast/tools
# (convert_room_bins, mesh_lod), this file's own directory when it sits there.
WA = Path(os.environ.get('RE4_WORLD_AGENT', 'C:/Game Dev/Emulators/re4-assets-private/world-agent-20260926'))
MESH_TOOLS = Path(os.environ.get('RE4_TOOLS', HERE if (HERE / 'convert_room_bins.py').exists() else
                                 '//wsl.localhost/Ubuntu-24.04/root/probe/d367-resume-20260928/step1/port/dreamcast/tools'))
sys.path.insert(0, str(MESH_TOOLS))
import convert_room_bins as crb  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def selected(path, names):
    import ast
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    env = {'math': math, 'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), env)
    return env


ps = load('ps2_tree_materials', WA / 'from-main/ps2-trees/tools/ps2_tree_materials.py')
tpl = load('ps2_tpl_decode', WA / 'from-main/ps2-trees/tools/ps2_tpl_decode.py')
codec = load('g_re4tex', WA.parent / 'character-prototype-20260925/tools/g_re4tex.py')
gx_light = selected(WA / 'from-main/original-world/reference/tools/ow_extract.py', {'gx_light'})['gx_light']
nearest = selected(WA / 'c1/tools/vq_review.py', {'nearest'})['nearest']

OWNER = 0x50
PS2_TO_PART_CULL = {0: 2, 1: 1, 2: 0}


def light_world(xyz, normals, lights, ambient):
    """prepare.py light_world (material 1)."""
    n = normals / np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-20)
    out = np.broadcast_to(np.asarray(ambient), xyz.shape).copy()
    for L in lights:
        delta = np.asarray(L['pos']) - xyz
        dist = np.linalg.norm(delta, axis=-1)
        direction = delta / np.maximum(dist[..., None], 1e-20)
        ld = np.asarray(L['dir'], float); ld /= max(np.linalg.norm(ld), 1e-20)
        cosine = np.maximum(0, np.sum(direction * ld, axis=-1))
        a, k = L['a'], L['k']
        gain = np.maximum(0, a[0] + a[1] * cosine + a[2] * cosine * cosine) / \
            np.maximum(k[0] + k[1] * dist + k[2] * dist * dist, 1e-20)
        out += np.asarray(L['col']) / 255 * gain[..., None] * np.maximum(0, np.sum(n * direction, axis=-1))[..., None]
    return np.clip(out, 0, 1)


def geometry_normals(pos, vidx, sign=1.0):
    """Smooth vertex normals of one group from its own triangles (area-weighted face normals summed per OBJ vertex,
    so a BIN's shared vertices are smoothed and its split vertices keep their edges); (F, 3, 3)."""
    fn = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0]) * sign
    uniq, inv = np.unique(vidx.ravel(), return_inverse=True)
    acc = np.zeros((len(uniq), 3))
    np.add.at(acc, inv, np.repeat(fn, 3, axis=0))
    n = acc[inv].reshape(pos.shape)
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    face = np.repeat(fn[:, None, :], 3, axis=1)                # a lone degenerate sum falls back to the face normal
    n = np.where(ln > 1e-12, n, face)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-20)


def gc_select(lights, sel, lo, hi):
    """ow_extract.py select() (light_house38.py rules: trans_lit.cpp LightSetModel / cLightMgr::setModel2 for
    scenery) with the PS2 SMX LightSwitch as the model's select mask and the group's world box standing in for the
    GC BIN light box; at most 8 lights."""
    out = []
    for l in lights:
        if (l['be'] & 3) != 3 or not (l['xF'] & 0x10) or l['type'] == 4:
            continue
        if l['i'] <= 31 and not (sel >> l['i']) & 1:
            continue
        if l['col'][:3] == [0, 0, 0]:
            continue
        if l['R'] and any(l['pos'][k] - l['R'] > hi[k] or l['pos'][k] + l['R'] < lo[k] for k in range(3)):
            continue
        out.append(l)
    return out[:8]


def gx_light_scenery(l, p):
    """trans_lit.cpp LightSetModel for scenery (obj_flag 0: brightness = Intensity, no radius fade) -> (GX light,
    local ambient): every LIT type the GC draws scenery with, for --a0-light gc. gx_light (ow_extract.py) covers 2
    quadratic, 3 spot, 5 parallel; added here: 0 constant (GXInitLightAttn(I, 0, 0, 1, 0, 0)), 1 linear (brightness
    I x (R - d) / R, d = placement to light), 6 spot-quad (lightSetSpotQuad: GXInitLightSpot(A0, COS2) +
    GXInitLightAttnK(1 / I, 0, (I - 0.1) / 0.1 / R^2 / I)), 7 local ambient (lightSetLocalAmb: the channel ambient
    becomes max(ambient, light colour)). 4 custom needs A2 / K0..K2, which the LIT json does not carry: (None, None)."""
    x = l['xD']
    if x in (2, 3, 5):
        return gx_light(l, p), None
    if x == 7:
        return None, np.asarray(l['col'][:3], float) / 255
    col = [min(255, int(c * l['col'][3] * 0.0078125)) for c in l['col'][:3]]
    I, R = l['intensity'], l['R']
    if x == 0:
        return dict(i=l['i'], kind='constant', col=col, pos=list(l['pos']), dir=[0.0, 0.0, 1.0],
                    a=[I, 0.0, 0.0], k=[1.0, 0.0, 0.0]), None
    if x == 1:
        d = math.dist(p['pos'], l['pos'])
        br = I * (R - d) / R if R else I
        return dict(i=l['i'], kind='linear', col=col, pos=list(l['pos']), dir=[0.0, 0.0, 1.0],
                    a=[br, 0.0, 0.0], k=[1.0, 0.0, 0.0]), None
    if x == 6:
        cut = l['A0']
        if cut <= 0.0 or cut > 90.0:
            a = [1.0, 0.0, 0.0]
        else:
            cr = math.cos(math.radians(cut))
            a = [0.0, -cr / (1.0 - cr), 1.0 / (1.0 - cr)]
        if I <= 0.0:
            return None, None
        k2 = (I - 0.1) / 0.1 / (R * R) / I if R else 0.0
        n = l['n']
        ln = math.sqrt(sum(v * v for v in n)) or 1.0
        return dict(i=l['i'], kind='spotquad', col=col, pos=list(l['pos']), dir=[-v / ln for v in n], a=a,
                    k=[1.0 / I, 0.0, k2]), None
    return None, None


# ------------------------------------------------------------------------------------------------ scene
def tev_multiplier(env):
    """cLightEnv tev_scale[0] (gxCsScale[0], scenery's TEV group): GX_CS_SCALE_1 / _2 / _4 = 0 / 1 / 2."""
    if 'tev_scale' not in env:
        raise SystemExit('the gc-lit json has no tev_scale: regenerate it with gc_room_lit.py (or pass --tev-scale)')
    return float(1 << env['tev_scale'][0])


def bin_light_flag(src, room, b):
    """The PS2 scenario BIN header word at 0x24 (little-endian): 0xa0000000 = a BIN the GameCube lights at run time
    (no colour stream on the GC), 0xe0000000 = a vertex-colour BIN, 0xb0000000 = a NORMAL BIN (CH1 audit 10-14)."""
    p = Path(src) / f'{room}_004_BIN' / ('%04d.BIN' % int(b))
    with open(p, 'rb') as fh:
        head = fh.read(0x28)
    return struct.unpack_from('<I', head, 0x24)[0]


A0_FLAG = 0xa0000000


def read_scene(room, src, light_ids, vc_scale=1.0, color_light='authored', normal_sign=1.0, gc_cut=0,
               gc_lit_path=None, tev_scale=None, vc_clamp=1.0, a0_ambient=False, stats=None, a0_light=None,
               a0_json=None, a0_own=False, a0_ps2_w=False):
    """color_light: 'authored' = COLOR groups keep the PS2 vertex colours (GS modulate; the landed packages);
    'gc' = the GameCube self-lit channel on PS2 geometry: material * clamp01(vertex colour + sum of the GC LIT
    cut-0 lights the model selects), with normals from the PS2 triangles (COLOR BINs carry no normals);
    'ps2' = the PS2 pattern, fully prelit: min(vertex colour, vc_clamp) * SMX colour * the room's TEV colour scale
    (the LIT cut's tev_scale[0] -> gxCsScale[0]: x1 / x2 / x4, light.cpp setEnv; the GC scales every scenery
    pixel by it, and the PS2 colours are authored before it: r106 x4 median 0.05, r101/r103 x1 0.40/0.60). No
    lights are added: the PS2 colours already carry the room's light.
    a0_ambient (--a0-ambient, test 11 item D, default off): COLOR groups whose BIN light flag is 0xa0000000 (the BINs
    the GameCube lights at run time; every black face of chapters 1 and 2-1 is in one) also get the room's LIT screen
    ambient (env ambient_scr / 255), as the GX channel does: 'ps2' min(vertex colour + ambient, vc_clamp) * SMX colour *
    TEV scale; 'authored' vertex colour + ambient * SMX colour * TEV scale. Other groups are unchanged.
    a0_light (--a0-light, default None = off): the light source of those 0xa0000000 groups. 'ambient' = a0_ambient
    above; 'gc' = the GameCube's own static result for a BIN without a colour stream (ow_extract.py lit(): GX channel,
    material register = SMX colour, ambient register = LIT ambient_scr): clamp01(ambient + sum over the static LIT
    lights the model selects (gc_select: scenery enable 0x10, SMX LightSwitch mask, light box, at most 8) of colour x
    distance / angle attenuation (gx_light: parallel, quadratic, spot COS2 + DistAttn MEDIUM) x max(0, N.L)) x SMX colour
    x TEV scale; the PS2 vertex colour is not used (the GC has none for these BINs). Normals from the PS2 triangles
    (geometry_normals, --normal-sign). a0_json (--a0-light-json): a measured / alternative light set merged over the
    LIT json before use - {"env": {...ambient_scr, tev_scale...}, "lights_cut": [...LIT-json lights...],
    "ambient_gain": k, "light_gain": k} - so PS2-measured values can replace the GC ones. a0_own (--a0-light-own):
    light every copy of an instanced BIN where it stands (exact, but the copies no longer share a mesh); default = the
    copies' mean."""
    obj = ps.read_obj(src / f'{room}_004.scenario.obj')
    mats = ps.read_idxmaterial(src / f'{room}_004.scenario.idxmaterial')
    mtl = ps.read_mtl(src / f'{room}_004.scenario.mtl')
    smd = ps.ps2_smd_lines(src / f'{room}_004.SMD')
    smx = ps.smx_entries(src / f'{room}_005.SMX', False)
    V = np.asarray(obj['v'], np.float64) * 100
    VT = np.asarray(obj['vt'], np.float64) * (255 / 256)
    VN = np.asarray(obj['vn'], np.float64) if obj['vn'] else np.zeros((1, 3))
    VC = np.asarray([c if c is not None else (1, 1, 1, 1) for c in obj['vc']], np.float64)
    for name, m in mats.items():
        assert int(m['diffuse_map']) == mtl[name]['tex'], name
    gl = None
    if a0_light is None and a0_ambient:
        a0_light = 'ambient'
    if a0_light not in (None, 'ambient', 'gc', 'ps2'):
        raise SystemExit('--a0-light: ambient, gc or ps2')
    if a0_light == 'ps2':
        # the PS2's own run-time result, measured in PCSX2 (CH1-AUDIT ps2-light.md: GS = 128 x W x smx x (VC +
        # (amb_scr + 1) / 256), no clamp but the GS 8-bit one, no lights): a0_json = ps2-light.json (a list of
        # {room, amb_scr, W}) or one {amb_scr, W} record
        pj = json.loads(Path(a0_json).read_text()) if a0_json else None
        if isinstance(pj, list):
            pj = next((x for x in pj if x.get('room') == room), None)
        if not pj or 'amb_scr' not in pj:
            raise SystemExit("--a0-light ps2 needs --a0-light-json with the room's PS2 amb_scr record (ps2-light.json)")
        amb_ps2 = (np.asarray(pj['amb_scr'], float) + 1) / 256
    a0_ambient = a0_light == 'ambient'
    if a0_light and color_light not in ('ps2', 'authored'):
        raise SystemExit('--a0-ambient / --a0-light need --color-light ps2 or authored')
    if color_light in ('gc', 'ps2') or a0_light:
        gc_lit_file = Path(gc_lit_path) if gc_lit_path else src / f'gc-lit-cut{gc_cut}.json'
        gc_lit = json.loads(gc_lit_file.read_text())
    a0_gain = (1.0, 1.0)
    cut_sets = None
    if a0_light == 'gc' and 'cut_sets' in gc_lit:
        # every LIT cut the player can switch to: cut 0 (room start, game.cpp LightMgr.update(0)) and the cut of each
        # camera area that can hit (attr 4 = never, cam_ctrl.cpp areaHit) and updates the light (attr 0x80 = no
        # update); an area_no outside the cuts is cut 0 (cLit::getSafeCutNo)
        reach = {0}
        for ar in gc_lit.get('cam_areas', []):
            if not ar['attr'] & 0x84 and ar['area_no'] >= 0:
                reach.add(ar['area_no'] if ar['area_no'] < gc_lit['cuts'] else 0)
        cut_sets = {c['cut']: c for c in gc_lit['cut_sets'] if c['cut'] in reach}
        # areaHitCheck order: the attr 0x20 areas first, then every area, each in file order (first hit wins)
        cam_polys = [(ar['area_no'] if 0 <= ar['area_no'] < gc_lit['cuts'] else 0, np.asarray(ar['points'], float))
                     for pri in (True, False) for ar in gc_lit.get('cam_areas', [])
                     if (not pri or ar['attr'] & 0x20) and not ar['attr'] & 0x84 and ar['area_no'] >= 0
                     and len(ar['points']) >= 3]
    if a0_light in ('ambient', 'gc') and a0_json:
        ov = json.loads(Path(a0_json).read_text())
        gc_lit = dict(gc_lit, env=dict(gc_lit['env'], **ov.get('env', {})),
                      lights_cut=ov.get('lights_cut', gc_lit['lights_cut']))
        a0_gain = (float(ov.get('ambient_gain', 1.0)), float(ov.get('light_gain', 1.0)))
        if cut_sets is not None:
            if 'lights_cut' in ov:
                cut_sets = None                        # a measured light set replaces the GC cuts
            else:
                cut_sets = {k: dict(c, env=dict(c['env'], **ov.get('env', {}))) for k, c in cut_sets.items()}
    if color_light == 'ps2' or a0_light:
        tev = float(tev_scale) if tev_scale else tev_multiplier(gc_lit['env'])
    if a0_light:
        amb0 = np.asarray(gc_lit['env']['ambient_scr'], float) / 255 * a0_gain[0]

    def inside(P, poly):
        """even-odd point-in-polygon on x/z (cam_ctrl.cpp area_hit_pN), P (N, 2)."""
        x, z = P[:, 0], P[:, 1]
        hit = np.zeros(len(P), bool)
        for k in range(len(poly)):
            (x1, z1), (x2, z2) = poly[k], poly[(k + 1) % len(poly)]
            if z1 == z2:
                continue
            cross = ((z1 > z) != (z2 > z)) & (x < x1 + (z - z1) * (x2 - x1) / (z2 - z1))
            hit ^= cross
        return hit

    def a0_cut(g, pos, sel, lo, hi):
        """The LIT cut that lights this group on the GC: the camera area the most of its corners stand in (the game
        switches the room light cut by camera area; a corner takes the area areaHitCheck would pick there), else the reachable cut that selects the most lights for it
        (its lights were placed for this part of the room), ties to the lowest cut (cut 0 first)."""
        P = pos.reshape(-1, 3)[:, [0, 2]]
        votes = collections.Counter()
        left = np.ones(len(P), bool)
        for c, poly in cam_polys:
            h = inside(P, poly) & left
            votes[c] += int(h.sum())
            left &= ~h
        if votes and max(votes.values()) > 0:
            return max(sorted(votes), key=lambda c: votes[c])
        n = {c: len(gc_select([l for l in cs['lights_cut'] if not l.get('parent_type', 0)], sel, lo, hi))
             for c, cs in cut_sets.items()}
        return max(sorted(n), key=lambda c: n[c])

    def a0_gc(g, pos, ix):
        """GC static channel of a 0xa0000000 group: (clamp01(ambient + sum of lights) x SMX colour, light ids)."""
        sem = smx.get(g['smx'])
        sel = int(sem['light_switch'], 16) if sem else 0xFFFFFFFF
        lo, hi = pos.reshape(-1, 3).min(0), pos.reshape(-1, 3).max(0)
        if cut_sets:
            c = a0_cut(g, pos, sel, lo, hi)
            if stats is not None:
                stats['a0_faces_cut%d' % c] += len(ix)
            lights_c = cut_sets[c]['lights_cut']
            amb = np.asarray(cut_sets[c]['env']['ambient_scr'], float) / 255 * a0_gain[0]
        else:
            lights_c, amb = gc_lit['lights_cut'], amb0.copy()
        # lights with a parent (1 enemy / player, 3 room etc model: lanterns and torches, 4 object) sit relative to a
        # moving or flickering model: not part of a static bake (their LIT position is parent-local)
        if stats is not None:
            stats['a0_parented_lights_left_out'] += sum(1 for l in lights_c if l.get('parent_type', 0))
        lights_c = [l for l in lights_c if not l.get('parent_type', 0)]
        chosen_gc = gc_select(lights_c, sel, lo, hi)
        lts = []
        for l in chosen_gc:
            gl_, la = gx_light_scenery(l, smd[g['smd']])
            if la is not None:
                amb = np.maximum(amb, la * a0_gain[0])
            elif gl_ is not None:
                lts.append(dict(gl_, col=[c * a0_gain[1] for c in gl_['col']]))
            elif stats is not None:
                stats['a0_unsupported_light_xD%d' % l['xD']] += 1
        nrm = geometry_normals(pos, ix[:, :, 0], normal_sign)
        ch = light_world(pos, nrm, lts, amb)
        mc = sem.get('smx_colour_rgb') if sem else None
        mcol = np.asarray(mc, float) / 255 if mc and any(mc) else np.ones(3)
        if stats is not None:
            stats['a0_faces'] += len(ix)
            stats['a0_lit_faces'] += len(ix) if lts else 0
        return ch * mcol, [l['i'] for l in chosen_gc]
    if any(g['kind'] == 'NORMAL' for g in obj['groups']):
        lit = json.loads((src / 'gc-lit-cut0.json').read_text())
        chosen = [l for l in lit['lights_cut'] if l['i'] in light_ids]
        assert len(chosen) == len(light_ids), 'lights'
        ambient = np.asarray(lit['env']['ambient_scr'], float) / 255
    groups = []
    for gi, g in enumerate(obj['groups']):
        faces = [f for f, _ in g['faces']]
        assert all(len(f) == 3 and all(c[1] >= 0 for c in f) for f in faces), g['name']
        ix = np.asarray(faces, int)
        mat = [m for _, m in g['faces']]
        pos = V[ix[:, :, 0]]
        gc_ids = None
        a0gc = False
        if g['kind'] == 'NORMAL':
            assert (ix[:, :, 2] >= 0).all(), g['name']
            lights = [gx_light(l, smd[g['smd']]) for l in chosen]
            assert all(not l['kind'].startswith('unsupported') for l in lights)
            rgb = light_world(pos, VN[ix[:, :, 2]], lights, ambient)
            if color_light == 'ps2':
                rgb = rgb * tev                         # the TEV colour scale covers every scenery pixel
        elif color_light == 'gc':
            sem = smx.get(g['smx'])
            sel = int(sem['light_switch'], 16) if sem else 0xFFFFFFFF
            chosen_gc = gc_select(gc_lit['lights_cut'], sel, pos.reshape(-1, 3).min(0), pos.reshape(-1, 3).max(0))
            lights = [gx_light(l, smd[g['smd']]) for l in chosen_gc]
            lights = [l for l in lights if not l['kind'].startswith('unsupported')]
            nrm = geometry_normals(pos, ix[:, :, 0], normal_sign)
            lsum = light_world(pos, nrm, lights, np.zeros(3)) if lights else np.zeros(pos.shape)
            mc = sem.get('smx_colour_rgb') if sem else None
            mcol = np.asarray(mc, float) / 255 if mc and any(mc) else np.ones(3)
            rgb = np.clip(VC[ix[:, :, 0], :3] * vc_scale + lsum, 0, 1) * mcol
            gc_ids = [l['i'] for l in chosen_gc]
        elif color_light == 'ps2':
            sem = smx.get(g['smx'])
            mc = sem.get('smx_colour_rgb') if sem else None
            mcol = np.asarray(mc, float) / 255 if mc and any(mc) else np.ones(3)
            if a0_light == 'ps2' and bin_light_flag(src, room, g['bin']) == A0_FLAG:
                rgb = (VC[ix[:, :, 0], :3] * vc_scale + amb_ps2) * mcol * (float(pj['W']) if a0_ps2_w else tev)
                if stats is not None:
                    stats['a0_faces'] += len(faces)
            elif a0_light == 'gc' and bin_light_flag(src, room, g['bin']) == A0_FLAG:
                ch, gc_ids = a0_gc(g, pos, ix)
                rgb = ch * tev
                a0gc = True
            elif a0_ambient and bin_light_flag(src, room, g['bin']) == A0_FLAG:
                rgb = np.minimum(VC[ix[:, :, 0], :3] * vc_scale + amb0, vc_clamp) * mcol * tev
                if stats is not None:
                    stats['a0_faces'] += len(faces)
            elif a0_light == 'ps2':
                # the measured PS2 rule has no clamp at 1.0 on the vertex colour of any COLOR BIN (0xe0 too: GS =
                # W x smx x VC up to the GS 8-bit limit)
                rgb = VC[ix[:, :, 0], :3] * vc_scale * mcol * (float(pj['W']) if a0_ps2_w else tev)
                if stats is not None:
                    stats['ps2_unclamped_faces'] += len(faces)
            else:
                rgb = np.minimum(VC[ix[:, :, 0], :3] * vc_scale, vc_clamp) * mcol * tev
        else:
            rgb = VC[ix[:, :, 0], :3] * vc_scale      # --vc-scale: a look-review lift, 1.0 = as authored
            if a0_light == 'ps2' and g['kind'] != 'NORMAL' and bin_light_flag(src, room, g['bin']) == A0_FLAG:
                sem = smx.get(g['smx'])
                mc = sem.get('smx_colour_rgb') if sem else None
                mcol = np.asarray(mc, float) / 255 if mc and any(mc) else np.ones(3)
                rgb = (rgb + amb_ps2) * mcol * (float(pj['W']) if a0_ps2_w else 1.0)
                if stats is not None:
                    stats['a0_faces'] += len(faces)
            elif a0_light == 'gc' and g['kind'] != 'NORMAL' and bin_light_flag(src, room, g['bin']) == A0_FLAG:
                ch, gc_ids = a0_gc(g, pos, ix)
                rgb = ch * tev
                a0gc = True
            elif a0_ambient and g['kind'] != 'NORMAL' and bin_light_flag(src, room, g['bin']) == A0_FLAG:
                sem = smx.get(g['smx'])
                mc = sem.get('smx_colour_rgb') if sem else None
                mcol = np.asarray(mc, float) / 255 if mc and any(mc) else np.ones(3)
                rgb = rgb + amb0 * mcol * tev
                if stats is not None:
                    stats['a0_faces'] += len(faces)
        sem = smx.get(g['smx'])
        cull = int(sem['face_culling'][2:4], 16) if sem else 0
        assert cull in (0, 1, 2)
        groups.append(dict(index=gi, name=g['name'], bin=g['bin'], kind=g['kind'], smd=g['smd'], vidx=ix[:, :, 0],
                           pos=pos, uv=VT[ix[:, :, 1]], rgb=rgb, alpha=VC[ix[:, :, 0], 3],
                           tex=np.array([int(mats[m]['diffuse_map']) for m in mat]),
                           blend=np.array([bool(int(mats[m]['material_flag'], 16) & 4) for m in mat]), cull=cull,
                           gc_lights=gc_ids, a0gc=a0gc))
    if a0_light == 'gc' and not a0_own:
        # instanced BINs (the same BIN placed more than once): one light result for every copy, the mean of the
        # copies' own results corner by corner, so build() still shares one mesh between them (the GC lights each
        # copy where it stands; lighting each copy apart breaks the instancing: r106 +438 KB of heap-4 mesh)
        by = collections.defaultdict(list)
        for g in groups:
            if g['a0gc']:
                by[(g['bin'], g['rgb'].shape, g['tex'].tobytes())].append(g)
        for k, gs in by.items():
            if len(gs) > 1:
                m = np.mean([g['rgb'] for g in gs], axis=0)
                for g in gs:
                    g['rgb'] = m
                if stats is not None:
                    stats['a0_instanced_groups'] += len(gs)
    return groups


# ------------------------------------------------------------------------------------------------ textures
def pack16(a, fmt):
    q = np.clip(np.rint(a), 0, 255).astype(np.uint32)
    if fmt == 0:
        return ((q[..., 0] * 31 + 127) // 255 << 11) | ((q[..., 1] * 63 + 127) // 255 << 5) | ((q[..., 2] * 31 + 127) // 255)
    if fmt == 1:
        return ((q[..., 3] > 127).astype(np.uint32) << 15) | ((q[..., 0] * 31 + 127) // 255 << 10) | \
            ((q[..., 1] * 31 + 127) // 255 << 5) | ((q[..., 2] * 31 + 127) // 255)
    return ((q[..., 3] * 15 + 127) // 255 << 12) | ((q[..., 0] * 15 + 127) // 255 << 8) | \
        ((q[..., 1] * 15 + 127) // 255 << 4) | ((q[..., 2] * 15 + 127) // 255)


def fnv(raw):
    n = 2166136261
    for x in raw:
        n = ((n ^ x) * 16777619) & 0xffffffff
    return n


def re4dctx_bytes(label, w, h, fmt, payload_type, payload):
    """(file bytes, key) of a one-descriptor RE4DCTX package. The key (file name) is CRC32-FNV1a of the texels, the
    identity the R4PW parts bind; the header's payload_crc32 is CRC32 of every byte after the 48-byte header, the
    runtime's rule (texture_package.cpp validate / open_streamed, convert_tpl.py, stage.sh). Packages written before
    2026-10-03 21:10 carry CRC32 of the texels alone in that field (legacy: they load only where the runtime skips the
    CRC, TEX_RESIDENT=1 without TEX_PAYLOAD_CRC); their texels and keys are the same."""
    crc = zlib.crc32(payload) & 0xffffffff
    key = f'{crc:08x}-{fnv(payload):08x}'
    desc = struct.pack('<64s8I', label.encode()[:63], w, h, fmt, 144, len(payload), 0, payload_type, 0)
    body = desc + payload
    head = struct.pack('<8s10I', b'RE4DCTX\0', 2, 48, 96, 1, 48, 144, len(payload), zlib.crc32(body) & 0xffffffff, 1, 0)
    return head + body, key


def emit(folder, label, w, h, fmt, payload_type, payload):
    data, key = re4dctx_bytes(label, w, h, fmt, payload_type, payload)
    crc, h2 = (int(x, 16) for x in key.split('-'))
    p = folder / (key + '.re4tex')
    p.write_bytes(data)
    pixels, meta = codec.decode(p)
    return p, (crc, h2), pixels


def vq_encode(a, fmt):
    """pack_vq.py main() for one image (fmt 0 or 2): codebook + twiddled indices."""
    h, w = a.shape[:2]
    q = pack16(a, fmt)
    qb = np.stack([q[::2, ::2], q[1::2, ::2], q[::2, 1::2], q[1::2, 1::2]], -1).reshape(-1, 4)
    exact, labels = np.unique(qb, axis=0, return_inverse=True)
    labels = labels.reshape(-1)
    if len(exact) <= 256:
        cb = np.zeros((256, 4), np.uint16); cb[:len(exact)] = exact
    else:
        blocks = np.stack([a[::2, ::2], a[1::2, ::2], a[::2, 1::2], a[1::2, 1::2]], 2).reshape(-1, 16).astype(np.float32)
        weights = np.tile([1, 1, 1, 2 if fmt == 2 else 0], 4).astype(np.float32)
        weighted = blocks * weights
        rng = np.random.default_rng(417)
        ix = rng.choice(len(blocks), min(16384, len(blocks)), replace=False)
        train = weighted[ix]
        centres = train[rng.choice(len(train), 256, replace=len(train) < 256)].copy()
        for _ in range(16):
            lab = nearest(train, centres)
            sums = np.zeros((256, 16), np.float64); np.add.at(sums, lab, train)
            counts = np.bincount(lab, minlength=256); live = counts > 0
            centres[live] = (sums[live] / counts[live, None]).astype(np.float32)
        raw = centres / np.maximum(weights, 1)
        if fmt != 2:
            raw[:, 3::4] = 255
        cb = pack16(raw.reshape(256, 4, 4), fmt).astype(np.uint16)
        centres = codec.px16(cb, fmt).reshape(256, 16).astype(np.float32) * weights
        labels = nearest(weighted, centres)
    tw = codec.untwiddle_index(w // 2, h // 2)
    idx = np.empty(w * h // 4, np.uint8); idx[tw.ravel()] = labels.astype(np.uint8)
    return cb.astype('<u2').tobytes() + idx.tobytes()


CUTOUT_MAX_ALPHA = 0   # --cutout-max-alpha (0: off, the historical packages)


def build_textures(room, src, out, used, gains):
    dec = tpl.cmd_decode(src / f'{room}_004.TPL', out / 'textures-source', set(used), False, False, 'gs')
    (out / 'tex').mkdir(exist_ok=True); (out / 'textures-packed').mkdir(exist_ok=True)
    rows = {}
    for t in sorted(used):
        base = next(r for r in dec['textures'] if r['entry'] == t and r['level'] == 'base')
        image = np.asarray(Image.open(out / 'textures-source' / base['file']).convert('RGBA'))
        h, w = image.shape[:2]
        assert w & (w - 1) == 0 and h & (h - 1) == 0 and w >= 8 and h >= 8 and w <= 1024 and h <= 1024, (t, w, h)
        alpha = np.unique(image[..., 3])
        mode = 'opaque' if alpha.min() == 255 else ('cutout' if np.all(np.isin(alpha, [0, 255])) else 'graded')
        if mode == 'graded' and CUTOUT_MAX_ALPHA and len(alpha) == 2 and alpha[0] == 0 and alpha[1] >= CUTOUT_MAX_ALPHA:
            # --cutout-max-alpha: a {0, max} alpha set (the PS2 cutouts store their opaque texels as 239) is a cutout:
            # the opaque texels become 255 (ARGB1555 alpha 1) and the material goes to the punch-through pass.
            image = image.copy(); image[..., 3] = np.where(image[..., 3] > 0, 255, 0).astype(image.dtype)
            mode = 'cutout'
        fmt = {'opaque': 0, 'cutout': 1, 'graded': 2}[mode]
        g = gains.get(t, np.ones(3))
        target = image.astype(np.float64); target[..., :3] *= g
        assert target[..., :3].max() <= 255 + 1e-6, (t, 'gain saturates')
        use_vq = fmt == 0 and 2048 + w * h // 4 < w * h * 2
        if use_vq:
            payload = vq_encode(target, fmt); ptype = 2
        else:
            q = pack16(target, fmt)
            raw = np.empty(w * h, dtype='<u2'); raw[codec.untwiddle_index(w, h).ravel()] = q.ravel()
            payload = raw.tobytes(); ptype = 1
        path, key, pixels = emit(out / 'tex', f'PS2 {room} texture {t}', w, h, fmt, ptype, payload)
        if not use_vq:
            assert np.array_equal(pixels, codec.px16(pack16(target, fmt), fmt).astype(np.uint8))
        assert pixels.shape == (h, w, 4)
        Image.fromarray(pixels).save(out / 'textures-packed' / f'{t:04d}.png')
        d = pixels[..., :3].astype(float) - np.clip(np.rint(target[..., :3]), 0, 255)
        vis = image[..., 3] > 0
        mse = float(np.mean(d[vis] ** 2)) if vis.any() else 0.0
        rows[t] = dict(texture=t, key=key, file=path.name, width=w, height=h, alpha_mode=mode, format=fmt,
                       payload='vq' if use_vq else 'native16', vram_bytes=len(payload), gain=list(map(float, g)),
                       psnr_vs_gained=10 * math.log10(255 ** 2 / max(mse, 1e-12)),
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return rows


# ------------------------------------------------------------------------------------------------ meshes
class Token:
    def __init__(self, mesh):
        self.mesh = mesh

    def __repr__(self):
        return 'ps2-room-mesh-%d' % self.mesh


def gains_for(groups):
    """gain_feasibility.py: per texture over COLOR faces; the headroom side is applied in build_textures."""
    vmax = {}
    for g in groups:
        if g['kind'] != 'COLOR':
            continue
        for t in np.unique(g['tex']):
            m = g['rgb'][g['tex'] == t].max(axis=(0, 1))
            vmax[int(t)] = np.maximum(vmax.get(int(t), np.zeros(3)), m)
    return vmax


def final_gains(room, src, out, groups):
    vmax = gains_for(groups)
    used = sorted({int(t) for g in groups for t in np.unique(g['tex'])})
    dec = tpl.cmd_decode(src / f'{room}_004.TPL', out / 'textures-source', set(used), False, False, 'gs')
    gains = {}
    for t in used:
        base = next(r for r in dec['textures'] if r['entry'] == t and r['level'] == 'base')
        image = np.asarray(Image.open(out / 'textures-source' / base['file']).convert('RGBA'))
        maximum = image[..., :3].max(axis=(0, 1)).astype(float) / 255
        desired = np.maximum(1, vmax.get(t, np.zeros(3)))
        headroom = np.divide(1, maximum, out=np.full(3, np.inf), where=maximum > 0)
        gains[t] = np.minimum(desired, headroom)
    return used, gains


def disguise_4444(c8):
    """--vertex-alpha tr4: 8-bit RGBA corners -> the 8-bit RGBA whose prelit ARGB1555 slot (convert_room_bins
    slot_of: bit 15 = a >= 128, then round(v * 31 / 255) per channel) is the corner's ARGB4444 word, so the shared
    converter stores the ARGB4444 word unchanged; the runtime decodes a marked part with its ARGB4444 LUT."""
    q4 = np.clip(np.floor(c8 * 15 / 255 + 0.5), 0, 15).astype(np.int64)
    w = (q4[..., 3] << 12) | (q4[..., 0] << 8) | (q4[..., 1] << 4) | q4[..., 2]
    five = lambda k: np.floor(k * 255 / 31 + 0.5).astype(np.int64)     # round(five(k) * 31 / 255) == k
    return np.stack([five((w >> 10) & 31), five((w >> 5) & 31), five(w & 31), np.where(w & 0x8000, 255, 0)], -1)


def face_colours(g, gains):
    """Final 8-bit corner RGBA (ps2src.corner_rgba): rgb * float32(1/gain), clamped; alpha /128 -> 255."""
    inv = np.stack([np.float32(1 / gains[int(t)]).astype(np.float64) for t in g['tex']])
    rgb = np.clip(g['rgb'] * inv[:, None, :], 0, 1)
    a = np.clip(g['alpha'], 0, 1)
    c = np.concatenate([rgb, a[..., None]], -1)
    return np.floor(c * 255 + 0.5).astype(np.int64)


def fit_affine(a, b):
    """world_b = M @ [world_a, 1]; None unless exact (residual < 0.5 mm) and well conditioned."""
    A = np.hstack([a, np.ones((len(a), 1))])
    if len(a) < 4 or np.linalg.svd(a - a.mean(0), compute_uv=False)[2] < 1.0:
        return None                                         # flat or tiny: the fit would not be unique
    M, *_ = np.linalg.lstsq(A, b, rcond=None)
    if np.abs(A @ M - b).max() > 0.5:
        return None
    return M.T                                              # 3 x 4


def bake_static(groups, obj_path, dynamic_below=250):
    """--bake-static: the static groups (scroll object id >= dynamic_below) as one world-space group placed once (the
    first static group's index, so ps2-world.ids gives it a static id); the other groups unchanged, in order."""
    import ps2_room_ids
    ids = ps2_room_ids.group_ids(obj_path)
    keep = [g for g in groups if ids[g['index']] < dynamic_below]
    stat = [g for g in groups if ids[g['index']] >= dynamic_below]
    if len(stat) < 2:
        return groups
    base, vidx = 0, []
    for g in stat:
        vidx.append(g['vidx'] + base)
        base += int(g['vidx'].max()) + 1
    cat = lambda k: np.concatenate([g[k] for g in stat])
    merged = dict(index=stat[0]['index'], name='baked-static', bin=-1, kind='BAKED', smd=stat[0]['smd'],
                  vidx=np.concatenate(vidx), pos=cat('pos'), uv=cat('uv'), rgb=cat('rgb'), alpha=cat('alpha'),
                  tex=cat('tex'), blend=cat('blend'), cull=stat[0]['cull'],
                  face_cull=np.concatenate([np.full(len(g['tex']), g['cull']) for g in stat]),
                  gc_lights=None, a0gc=False)
    print('bake-static: %d static groups (%d triangles) -> 1 mesh; %d groups kept' % (
        len(stat), len(merged['tex']), len(keep)), file=sys.stderr)
    return keep + [merged]


def build(groups, gains, textures, share=True, vertex_alpha='off'):
    meshes, placements, sources, parts_meta = [], [], {}, []
    by_bin = collections.defaultdict(list)                  # bin -> [(mesh index, group)]
    stats = collections.Counter()
    for g in groups:
        g['c8'] = face_colours(g, gains)
        inv = np.stack([np.float32(1 / gains[int(t)]).astype(np.float64) for t in g['tex']])
        clipped = int(((g['rgb'] * inv[:, None, :]) > 1 + 1e-6).any(-1).sum())   # light the texture gain can't carry
        if clipped:
            stats['corners_clipped'] += clipped
        g['pass'] = np.array([textures[int(t)]['format'] if b else 0 for t, b in zip(g['tex'], g['blend'])])
        if vertex_alpha != 'off':
            # --vertex-alpha (issue 20): the GS blends every triangle by its vertex alpha, so a face of a non-blend
            # material with a corner below 1.0 is a vertex-alpha overlay (the soft shadow / dirt layers drawn over
            # the base geometry). Drawn opaque, its dark corners show as solid black shapes; it goes to the
            # translucent pass (texture alpha off for an opaque texture: alpha = the vertex alpha).
            fade = (g['c8'][..., 3] < 255).any(-1) & (g['pass'] == 0)
            g['pass'] = np.where(fade, 2, g['pass'])
            stats['vertex_alpha_faces'] += int(fade.sum())
            g['mark'] = fade if vertex_alpha == 'tr4' else np.zeros(len(fade), bool)
            if vertex_alpha == 'tr4' and fade.any():
                g['c8'] = g['c8'].copy()
                g['c8'][fade] = disguise_4444(g['c8'][fade])
        else:
            g['mark'] = np.zeros(len(g['tex']), bool)
        stats['vertex_alpha_below_one'] += int((g['c8'][..., 3] < 255).sum())
        match = None
        if share:
            for mi, first in by_bin[g['bin']]:
                if (len(first['tex']) != len(g['tex']) or not np.array_equal(first['tex'], g['tex']) or
                        not np.array_equal(first['pass'], g['pass']) or first['cull'] != g['cull'] or
                        not np.array_equal(first['mark'], g['mark']) or
                        not np.array_equal(first['c8'], g['c8']) or np.abs(first['uv'] - g['uv']).max() > 1e-5):
                    continue
                M = fit_affine(first['pos'].reshape(-1, 3), g['pos'].reshape(-1, 3))
                if M is not None:
                    match = (mi, M)
                    break
        if match:
            placements.append((match[0], g['index'], match[1].tolist()))
            stats['instanced_groups'] += 1
            stats['instanced_triangles'] += len(g['tex'])
            continue
        mi = len(meshes)
        meshes.append(g)
        by_bin[g['bin']].append((mi, g))
        placements.append((mi, g['index'], [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0]]))
        # one mesh: local positions (OBJ vertex ids), parts by (texture, pass, cull) in first-use order
        vid = {}
        positions = []
        for f in range(len(g['tex'])):
            for c in range(3):
                v = int(g['vidx'][f, c])
                if v not in vid:
                    vid[v] = len(positions)
                    positions.append(tuple(float(x) for x in g['pos'][f, c]))
        uvs, uv_index, colors, color_index = [], {}, [], {}
        order, loose = [], {}
        for f in range(len(g['tex'])):
            key = (int(g['tex'][f]), int(g['pass'][f]), int(g['face_cull'][f]) if 'face_cull' in g else g['cull'],
                   bool(g['mark'][f]))
            if key not in loose:
                loose[key] = []
                order.append(key)
            corners = []
            for c in range(3):
                c8 = tuple(int(x) for x in g['c8'][f, c])
                uv = (float(g['uv'][f, c, 0]), float(g['uv'][f, c, 1]))
                if c8 not in color_index:
                    color_index[c8] = len(colors); colors.append(c8)
                if uv not in uv_index:
                    uv_index[uv] = len(uvs); uvs.append(uv)
                corners.append((vid[int(g['vidx'][f, c])], color_index[c8], uv_index[uv], 0))
            loose[key].append(tuple(corners))
        parts = []
        for k, key in enumerate(order):
            t, pas, cull, mark = key
            tex = textures[t]
            parts.append(dict(offset=32 * k, size=0, flags=0, texture=k & 255, alpha=255, strips=[], loose=loose[key]))
            parts_meta.append((tex['key'][0], tex['key'][1], tex['width'], tex['height'], pas, PS2_TO_PART_CULL[cull], t & 255,
                               int(mark)))
        sources[mi] = dict(flags=0, nvtx=min(65535, len(positions)), nparts=len(parts), positions=positions,
                           parts=parts, uv=uvs.__getitem__, color=colors.__getitem__,
                           normal=lambda n: (0.0, 1.0, 0.0), bytes=0)
    return meshes, placements, sources, parts_meta, stats


def placement_scale(affine):
    return max(math.sqrt(sum(affine[r][c] ** 2 for r in range(3))) for c in range(3))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('room')
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--lights', default='0,5', help='GC LIT cut-0 light indices for NORMAL groups (r101: 0,5)')
    ap.add_argument('--no-share', action='store_true', help='no BIN instancing (every group its own mesh)')
    ap.add_argument('--vc-scale', type=float, default=1.0,
                    help='multiply COLOR-group vertex colours (review lift for rooms whose PS2 colours are not the '
                         'final light, e.g. r106; 1.0 = as authored, the default and the landed packages)')
    ap.add_argument('--color-light', choices=('authored', 'gc', 'ps2'), default='authored',
                    help="COLOR groups: 'authored' PS2 vertex colours (default, the landed packages); 'gc': the "
                         "GameCube self-lit channel, clamp01(vertex colour + the GC LIT cut-0 lights the model "
                         "selects) x SMX colour, normals from the PS2 triangles; 'ps2': the PS2 pattern, prelit "
                         "min(vertex colour, --vc-clamp) x SMX colour x the room's TEV colour scale (LIT tev_scale). "
                         "gc / ps2 read <src>/gc-lit-cut<N>.json (gc_room_lit.py) or --gc-lit")
    ap.add_argument('--normal-sign', type=float, default=1.0, help='geometry normal orientation for --color-light gc')
    ap.add_argument('--gc-cut', type=int, default=0, help='--color-light gc/ps2: the LIT cut (<src>/gc-lit-cut<N>.json)')
    ap.add_argument('--gc-lit', type=Path, help='--color-light gc/ps2: the LIT cut json (instead of <src>/gc-lit-cut<N>)')
    ap.add_argument('--tev-scale', type=float, help='--color-light ps2: override the LIT tev_scale multiplier (1/2/4)')
    ap.add_argument('--vc-clamp', type=float, default=1.0,
                    help='--color-light ps2: clamp of the vertex colour before the SMX colour (1.0 = the GX channel '
                         'clamp, the default; 2.0 = the GS limit 0xFF/0x80)')
    ap.add_argument('--lod-eps', default='24,48,96,192,384')
    ap.add_argument('--lod-uv-guard', type=float, default=None,
                    help='refuse LOD collapses that move a corner\'s UV off its triangle\'s mapping by more than this '
                         '(UV units; e.g. 0.002); default off (the historical packages)')
    ap.add_argument('--lod-min-gain', type=float, default=0.4)
    ap.add_argument('--lod-max-levels', type=int, default=4)
    ap.add_argument('--lod-floor', type=float, default=2.0)
    ap.add_argument('--lod-cluster', type=float, default=20000.0)
    ap.add_argument('--meshlet-vertices', type=int, default=64)
    ap.add_argument('--cutout-max-alpha', type=int, default=0,
                    help="0 (default, the historical packages): only textures whose alpha is exactly {0, 255} are "
                         "cutouts. N (e.g. 224): a texture whose alpha set is exactly {0, max} with max >= N is a "
                         "cutout too (the PS2 cutouts top out at 239): max becomes opaque (ARGB1555) and its blend "
                         "materials draw in the punch-through pass instead of the translucent one (render only)")
    ap.add_argument('--vertex-alpha', choices=('off', 'tr', 'tr4'), default='off',
                    help="faces of non-blend materials with a corner alpha below 1.0 (the GS vertex-alpha overlays): "
                         "'off' keep them opaque (the historical packages, solid dark shapes); 'tr4' put them in the "
                         "translucent pass with ARGB4444 corner colours and mark their parts (R4PW part byte 15 bit "
                         "0) for game PS2_VERTEX_ALPHA=1 (issue 20); 'tr' the translucent pass only (test variant: "
                         "the PS2 world path forces alpha 1, so it draws as 'off')")
    ap.add_argument('--a0-ambient', action='store_true',
                    help="COLOR groups of BINs with light flag 0xa0000000 (run-time lit on the GameCube: the black faces) "
                         "also get the room's LIT screen ambient x SMX colour x TEV scale (GX channel rule); default off "
                         "(the historical packages, byte-identical)")
    ap.add_argument('--a0-light', choices=('ambient', 'gc', 'ps2'),
                    help="the light of the 0xa0000000 BINs (test 11 item D): 'ambient' = --a0-ambient; 'gc' = bake "
                         "the GameCube's own static result: clamp01(LIT ambient + the static LIT lights the model "
                         "selects, N.L with GX attenuation) x SMX colour x TEV scale (no PS2 vertex colour); default "
                         "off (the historical packages, byte-identical)")
    ap.add_argument('--a0-light-json', type=Path,
                    help="--a0-light: a light set merged over the LIT json ({env: {ambient_scr, tev_scale}, lights_cut: "
                         "[...], ambient_gain, light_gain}), e.g. PS2-measured values")
    ap.add_argument('--a0-ps2-w', action='store_true',
                    help="--a0-light ps2: scale by the PS2 room W (ps2-light.json) instead of the recipe's GC TEV scale")
    ap.add_argument('--a0-light-own', action='store_true',
                    help="--a0-light gc: light each copy of an instanced BIN at its own place (no mesh sharing for them; "
                         "default: the copies' mean, so they still share one mesh)")
    ap.add_argument('--bake-static', action='store_true',
                    help="merge every static group (SMD row whose scroll object id is >= 250: no room code moves or "
                         "hides it) into ONE world-space mesh, parts by material, placed once; groups with an id < 250 "
                         "(doors, PS2_WORLD_DYNAMIC binds, sky) stay their own placements. With --lod-cluster the merged "
                         "mesh is cut into spatial clusters, so culling and LOD still work per region (lane "
                         "fix-r10d-speed23: r10d, 167 static of 228 placements). Default off (byte-identical packages)")
    a = ap.parse_args()
    crb.MAX_MESHLET_VERTICES = a.meshlet_vertices
    global CUTOUT_MAX_ALPHA
    CUTOUT_MAX_ALPHA = a.cutout_max_alpha
    if a.lod_uv_guard is not None:
        import mesh_lod  # noqa: E402 (MESH_TOOLS is on sys.path)
        mesh_lod.UV_GUARD = a.lod_uv_guard
    a.out.mkdir(parents=True, exist_ok=True)
    a0_stats = collections.Counter()
    groups = read_scene(a.room, a.src, tuple(int(x) for x in a.lights.split(',')), a.vc_scale, a.color_light,
                        a.normal_sign, a.gc_cut, a.gc_lit, a.tev_scale, a.vc_clamp, a.a0_ambient, a0_stats,
                        a.a0_light, a.a0_light_json, a.a0_light_own, a.a0_ps2_w)
    used, gains = final_gains(a.room, a.src, a.out, groups)
    textures = build_textures(a.room, a.src, a.out, used, gains)
    if a.bake_static:
        groups = bake_static(groups, a.src / f'{a.room}_004.scenario.obj')
    meshes, placements, sources, parts_meta, stats = build(groups, gains, textures, share=not a.no_share,
                                                           vertex_alpha=a.vertex_alpha)
    scales = collections.defaultdict(float)
    for mi, _, aff in placements:
        scales[(OWNER, mi)] = max(scales[(OWNER, mi)], placement_scale(aff))
    entries = [(OWNER, 0, mi, Token(mi)) for mi in range(len(meshes))]
    eps = tuple(float(x) for x in a.lod_eps.split(','))
    blob, summary = crb.convert_lod(entries, 1.0, scales=dict(scales), eps_world=eps, cluster_world=a.lod_cluster,
                                    min_gain=a.lod_min_gain, max_levels=a.lod_max_levels,
                                    floor={None: a.lod_floor} if a.lod_floor > 0 else None, share=True,
                                    source=lambda token: sources[token.mesh], color_mode='prelit')
    if summary['parts'] != len(parts_meta):
        raise SystemExit('part count %d != %d (an empty mesh was skipped)' % (summary['parts'], len(parts_meta)))
    body = b''.join(struct.pack('<IIHHBBBB', *m) for m in parts_meta)
    body += b''.join(struct.pack('<HH12f', mi, gi, *[x for row in aff for x in row]) for mi, gi, aff in placements)
    side = struct.pack('<4s7I', b'R4PW', 1, len(placements), len(parts_meta), len(meshes), zlib.crc32(body), 0, 0) + body
    (a.out / 'ps2-world.re4mesh').write_bytes(blob)
    (a.out / 'ps2-world.r4pw').write_bytes(side)
    # the scroll id of each placement (PS2_WORLD_DYNAMIC: the runtime follows the objects the room code moves / hides)
    sys.path.insert(0, str(HERE))
    import ps2_room_ids
    ps2_room_ids.write(a.src / f'{a.room}_004.scenario.obj', a.out / 'ps2-world.r4pw', a.out / 'ps2-world.ids')
    summary.pop('meshes_detail', None)
    tri = collections.Counter()
    for g in groups:
        for p in g['pass']:
            tri[int(p)] += 1
    report = dict(room=a.room, args={k: str(v) for k, v in vars(a).items()
                                                  if k not in ('a0_ambient', 'a0_light', 'a0_light_json', 'a0_light_own', 'a0_ps2_w') or v},
                  groups=len(groups), meshes=len(meshes),
                  placements=len(placements), source_triangles=sum(len(g['tex']) for g in groups),
                  triangles_by_pass={['OP', 'PT', 'TR'][k]: v for k, v in sorted(tri.items())},
                  stats=dict(stats, **dict(a0_stats)),
                  gc_light_sets={','.join(map(str, k)): v for k, v in collections.Counter(
                      tuple(g['gc_lights']) for g in groups if g['gc_lights'] is not None).items()},
                  level0_triangles=summary['level0_triangles'], re4mesh_bytes=len(blob),
                  re4mesh_sha256=hashlib.sha256(blob).hexdigest(), r4pw_bytes=len(side),
                  r4pw_sha256=hashlib.sha256(side).hexdigest(), textures=len(textures),
                  texture_vram_bytes=sum(t['vram_bytes'] for t in textures.values()),
                  texture_rows=textures, summary=summary,
                  texture_crc_rule='header')   # payload_crc32 over every byte after the header (re4dctx_bytes)
    (a.out / 'ps2-world.json').write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: report[k] for k in ('room', 'groups', 'meshes', 'placements', 'source_triangles',
                                             'triangles_by_pass', 'stats', 'level0_triangles', 're4mesh_bytes',
                                             'r4pw_bytes', 'textures', 'texture_vram_bytes')}))


if __name__ == '__main__':
    main()

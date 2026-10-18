#!/usr/bin/env python3
"""edemo18 clip baker: Ganado FCV clips -> compact Dreamcast clip format (EDCL v1).

Ground truth is the game's own evaluator: tools/motion/evalhost.Player hosts src/game/motion.cpp
(MotionSetCore / MotionMove / MotionMoveCore / HermiteInterpolation), ik.cpp (InverseKinematics) and
the model's blend table, compiled for the host. Every clip is sampled at the game's 30 Hz frames
(0..maxFrame); the baker stores, per parts:

  rotation     smallest-three quaternion, 48 bits (2-bit dropped index + 3 x 15-bit), per key,
               or one key when the parts' rotation is constant over the clip
  translation  s16 x3 with a per-track scale, only when it differs from the rest pose
  root motion  separate track: MotionGetPosition root pos (f32 x3) + root rot (s16 x3, 1/10430 rad)
  gameplay     model-space tracks for the gameplay parts (em10.cpp getPartsPtr constants):
               s16 x3 position (1/8 mm) + 48-bit quaternion, per key
  events       SEQ tables are kept as the game's (frame 10.6 + Se + Free); markers = Se != 0

Errors are measured against the evaluator: at every key (quantization) and at every half frame
(runtime nlerp between 2 baked keys vs the game's Hermite at f + 0.5), in model space (parts
hierarchy composed from the baked locals), as max / mean rotation angle (deg) and position (mm).

Outputs go to a private directory (never git): bake.bin per archive + report.json.

Phase 1B: --pose-stage source-local disables offline IK and the blend table and
writes stage-tagged EDCL v2. Its current live-sampler contract accepts integer
source frames only; fractional source phases need the original evaluator, not
rounded clocks. Reports retain fractional errors, including excluded source
jumps, for diagnosis. Default demo-final EDCL v1 encoding is unchanged.
"""
import argparse
import hashlib
import json
import math
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
# Explicit historical evaluator roots remain available for reproducing old demo
# bytes. Phase 1B normally uses this tree's repaired current-source host helper.
MOTION_ROOT = os.path.abspath(os.environ.get('EDEMO_MOTION_ROOT', ROOT))
sys.path.insert(0, os.path.join(MOTION_ROOT, 'tools'))
from motion import archive, evalhost, fcv, modelbin  # noqa: E402

GAMEPLAY_PARTS = (0, 1, 2, 3, 4, 9, 10, 13, 16)   # em10.cpp getPartsPtr(<const>) users, < 34
GAMEPLAY_ROT = (4, 10, 16)   # head, left hand, right hand (em12:440 hierarchy: 4 = top of the spine chain; 10 / 16 = arm chain ends)
MAX_SHIFT = 3                # key stride up to 8 frames
ROT_TOL = 0.5                # deg, local, at every integer frame
POS_TOL = 0.5                # mm, local, at every integer frame
GP_POS_TOL = 2.0             # mm, model space, gameplay tracks
GP_ROT_TOL = 1.0             # deg
GP_BAKED = os.environ.get('EDEMO_GP', 'chain') == 'baked'   # chain: logic walks the head/hand chains from the pose tracks


# ---------------------------------------------------------------- maths (pure python)
def mat_quat(m):
    """3x4 row-major -> unit quaternion (x, y, z, w) of the column-normalised rotation."""
    c = [[m[0], m[4], m[8]], [m[1], m[5], m[9]], [m[2], m[6], m[10]]]   # columns
    s = [math.sqrt(sum(v * v for v in col)) or 1.0 for col in c]
    r = [[m[r * 4 + k] / s[k] for k in range(3)] for r in range(3)]
    tr = r[0][0] + r[1][1] + r[2][2]
    if tr > 0:
        t = math.sqrt(tr + 1.0) * 2
        q = ((r[2][1] - r[1][2]) / t, (r[0][2] - r[2][0]) / t, (r[1][0] - r[0][1]) / t, 0.25 * t)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        t = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2
        q = (0.25 * t, (r[0][1] + r[1][0]) / t, (r[0][2] + r[2][0]) / t, (r[2][1] - r[1][2]) / t)
    elif r[1][1] > r[2][2]:
        t = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2
        q = ((r[0][1] + r[1][0]) / t, 0.25 * t, (r[1][2] + r[2][1]) / t, (r[0][2] - r[2][0]) / t)
    else:
        t = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2
        q = ((r[0][2] + r[2][0]) / t, (r[1][2] + r[2][1]) / t, 0.25 * t, (r[1][0] - r[0][1]) / t)
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q), s


def quat_mat(q, t):
    x, y, z, w = q
    return [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), t[0],
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), t[1],
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), t[2]]


def mul(a, b):
    o = [0.0] * 12
    for r in range(3):
        for c in range(4):
            o[r * 4 + c] = a[r * 4] * b[c] + a[r * 4 + 1] * b[4 + c] + a[r * 4 + 2] * b[8 + c] + (a[r * 4 + 3] if c == 3 else 0.0)
    return o


def qangle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def nlerp(a, b, t):
    if sum(x * y for x, y in zip(a, b)) < 0:
        b = tuple(-v for v in b)
    q = tuple(x + (y - x) * t for x, y in zip(a, b))
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q)


# ---------------------------------------------------------------- quantization
def q48(q):
    """Smallest-three: drop the largest |component|, store sign-fixed others as 15-bit."""
    i = max(range(4), key=lambda k: abs(q[k]))
    if q[i] < 0:
        q = tuple(-v for v in q)
    lim = 1 / math.sqrt(2)
    vals = [q[k] for k in range(4) if k != i]
    enc = [max(0, min(32767, int(round((v + lim) / (2 * lim) * 32767)))) for v in vals]
    word = (i << 45) | (enc[0] << 30) | (enc[1] << 15) | enc[2]
    return word.to_bytes(6, 'little')


def dq48(b):
    word = int.from_bytes(b, 'little')
    i = word >> 45
    lim = 1 / math.sqrt(2)
    enc = [(word >> 30) & 0x7FFF, (word >> 15) & 0x7FFF, word & 0x7FFF]
    vals = [e / 32767 * 2 * lim - lim for e in enc]
    s = sum(v * v for v in vals)
    big = math.sqrt(max(0.0, 1 - s))
    out = []
    it = iter(vals)
    for k in range(4):
        out.append(big if k == i else next(it))
    return tuple(out)


def qvec(vals, scale):
    return [max(-32768, min(32767, int(round(v / scale)))) for v in vals]


# ---------------------------------------------------------------- baking
def sample(player, n_parts, f):
    pose = player.frame(f)
    return pose


def bake_clip(model, mot, rest, depth_parent, pose_stage='demo-final',
              rot_tol=ROT_TOL, pos_tol=POS_TOL, max_shift=MAX_SHIFT):
    n = model.n_parts
    if pose_stage not in ('demo-final', 'source-local'):
        raise ValueError('unknown pose stage')
    if not (math.isfinite(rot_tol) and math.isfinite(pos_tol) and
            rot_tol >= 0 and pos_tol >= 0 and 0 <= max_shift <= 3):
        raise ValueError('invalid local tolerances or key shift')
    source_local = pose_stage == 'source-local'
    # Live IK and the model's blend table must run exactly once, in the game.
    # Legacy demo output deliberately retains its post-IK/blend behavior.
    player = evalhost.Player(model, mot, loop=False, ik=not source_local,
                             blend_table=[] if source_local else None)
    nf = mot.max_frame + 1
    keys = []
    for f in range(nf):
        p = player.frame(float(f))
        locs = []
        for i in range(n):
            q, s = mat_quat(p.l_mat[i])
            locs.append((q, (p.l_mat[i][3], p.l_mat[i][7], p.l_mat[i][11]), s))
        keys.append((locs, p.mat, p.root_pos, p.root_rot))
    halves = []
    for f in range(nf - 1):
        p = player.frame(f + 0.5)
        halves.append(p.mat)
    out = bytearray()
    hdr_parts = []
    scaled = 0
    scaled_parts = [False] * n
    for i in range(n):
        qs = [k[0][i][0] for k in keys]
        ts = [k[0][i][1] for k in keys]
        if any(abs(c - 1) > 1e-3 for k in keys for c in k[0][i][2]):
            scaled += 1
            scaled_parts[i] = True
        rot_static = all(qangle(qs[0], q) < 0.01 for q in qs)
        tr_rest = all(max(abs(a - b) for a, b in zip(t, rest[i])) < 0.01 for t in ts)
        tr_static = all(max(abs(a - b) for a, b in zip(t, ts[0])) < 0.01 for t in ts)
        hdr_parts.append((rot_static, tr_rest, tr_static))
    # Encode: header + per part flags; tracks. Animated tracks pick the largest key stride
    # (shift 0..MAX_SHIFT: keys every 1/2/4/8 frames) whose runtime interpolation stays within
    # ROT_TOL deg / POS_TOL mm of the evaluator at every integer frame (local space).
    enc = bytearray(struct.pack('<HBB', nf, n, int(source_local)))
    rot_tracks = [None] * n   # (shift, [decoded quats])
    tr_tracks = [None] * n    # (shift, [decoded vecs])
    shifts = []
    sc_tracks = [None] * n

    def kidx(k, s):
        return min(k << s, nf - 1)

    def rot_at(tr, x):
        s, ks = tr
        if len(ks) == 1:
            return ks[0]
        u = x / (1 << s)
        k = min(int(u), len(ks) - 2)
        a, b = kidx(k, s), kidx(k + 1, s)
        t = 0.0 if b == a else (x - a) / (b - a)
        return nlerp(ks[k], ks[k + 1], max(0.0, min(1.0, t)))

    def vec_at(tr, x):
        s, ks = tr
        if len(ks) == 1:
            return ks[0]
        u = x / (1 << s)
        k = min(int(u), len(ks) - 2)
        a, b = kidx(k, s), kidx(k + 1, s)
        t = 0.0 if b == a else max(0.0, min(1.0, (x - a) / (b - a)))
        return tuple(p + (q - p) * t for p, q in zip(ks[k], ks[k + 1]))

    for i in range(n):
        rs, trr, trs = hdr_parts[i]
        qs = [keys[f][0][i][0] for f in range(nf)]
        if rs:
            b = q48(qs[0])
            rot_tracks[i] = (0, [dq48(b)])
            rbytes = b
            rshift = 0
        else:
            for s in range(max_shift, -1, -1):
                nk = ((nf - 1) + (1 << s) - 1 >> s) + 1
                bs = [q48(qs[kidx(k, s)]) for k in range(nk)]
                tr = (s, [dq48(b) for b in bs])
                if s == 0 or all(qangle(rot_at(tr, f), qs[f]) <= rot_tol for f in range(nf)):
                    break
            rot_tracks[i] = tr
            rbytes = b''.join(bs)
            rshift = s
        if trr:
            tr_tracks[i] = (0, [rest[i]])
            tbytes = b''
            tshift = 0
        else:
            ts = [keys[f][0][i][1] for f in range(nf)]
            mx = max(abs(c) for v in ts for c in v) or 1.0
            sc = mx / 32767.0
            if trs:
                iv = qvec(ts[0], sc)
                tr_tracks[i] = (0, [tuple(v * sc for v in iv)])
                tbytes = struct.pack('<f3h', sc, *iv)
                tshift = 0
            else:
                for s in range(max_shift, -1, -1):
                    nk = ((nf - 1) + (1 << s) - 1 >> s) + 1
                    ivs = [qvec(ts[kidx(k, s)], sc) for k in range(nk)]
                    tr = (s, [tuple(v * sc for v in iv) for iv in ivs])
                    if s == 0 or all(math.dist(vec_at(tr, f), ts[f]) <= pos_tol for f in range(nf)):
                        break
                tr_tracks[i] = tr
                tbytes = struct.pack('<f', sc) + b''.join(struct.pack('<3h', *iv) for iv in ivs)
                tshift = s
        shifts.append((rshift, tshift))
        sbytes = b''
        if scaled_parts[i]:
            # scale track (rare: the dismember / death clips scale parts to 0), every frame, 1/4096
            svals = [[max(-32768, min(32767, int(round(c * 4096)))) for c in keys[f][0][i][2]] for f in range(nf)]
            sc_tracks[i] = [tuple(c / 4096 for c in v) for v in svals]
            sbytes = b''.join(struct.pack('<3h', *v) for v in svals)
        fl = (0 if rs else 1) | (0 if trr else (2 if trs else 6)) | (rshift << 3) | (tshift << 5) | (0x80 if sbytes else 0)
        enc.append(fl)
        enc += rbytes + tbytes + sbytes
    while len(enc) % 4:
        enc.append(0)
    pose_bytes = len(enc)
    dec_q = [[rot_at(rot_tracks[i], f) for i in range(n)] for f in range(nf)]
    dec_t = [[vec_at(tr_tracks[i], f) for i in range(n)] for f in range(nf)]
    # root track (every frame: it drives movement)
    rmx = max(abs(c) for k in keys for c in k[2]) or 1.0
    rsc = rmx / 32767.0
    enc += struct.pack('<f', rsc)
    for f in range(nf):
        rp, rr = keys[f][2], keys[f][3]
        enc += struct.pack('<3h3h', *qvec(rp, rsc), *[max(-32768, min(32767, int(round(a * 10430.378)))) for a in rr])
    root_bytes = len(enc) - pose_bytes
    # gameplay tracks: model-space position for every gameplay parts, rotation only for the
    # GAMEPLAY_ROT parts (hands / weapon / head aim); logic ticks read them without any hierarchy
    # walk. Key stride chosen like the pose tracks, tolerance GP_POS_TOL mm / GP_ROT_TOL deg.
    gp = [g for g in GAMEPLAY_PARTS if g < n]
    gp_err = []
    gpb = bytearray()
    for g in gp:
        ps = [(keys[f][1][g][3], keys[f][1][g][7], keys[f][1][g][11]) for f in range(nf)]
        qs = [mat_quat(keys[f][1][g])[0] for f in range(nf)]
        for s in range(max_shift, -1, -1):
            nk = ((nf - 1) + (1 << s) - 1 >> s) + 1
            pt = (s, [tuple(v * 0.125 for v in qvec(ps[kidx(k, s)], 0.125)) for k in range(nk)])
            qt = (s, [dq48(q48(qs[kidx(k, s)])) for k in range(nk)])
            pe = max(math.dist(vec_at(pt, f), ps[f]) for f in range(nf))
            qe = max(qangle(rot_at(qt, f), qs[f]) for f in range(nf)) if g in GAMEPLAY_ROT else 0.0
            if s == 0 or (pe <= GP_POS_TOL and qe <= GP_ROT_TOL):
                break
        gp_err.append((pe, qe))
        gpb.append(s)
        for k in range(nk):
            gpb += struct.pack('<3h', *qvec(ps[kidx(k, s)], 0.125))
            if g in GAMEPLAY_ROT:
                gpb += q48(qs[kidx(k, s)])
    gp_bytes = len(gpb)
    if GP_BAKED:
        enc += gpb

    # errors
    def compose(qrow, trow, srow):
        mats = [None] * n
        for i in range(n):
            l = quat_mat(qrow[i], trow[i])
            if srow[i] is not None:
                for r in range(3):
                    for c in range(3):
                        l[r * 4 + c] *= srow[i][c]
            par = model.parts[i].parent
            mats[i] = l if par < 0 else mul(mats[par], l)
        return mats

    err = {'key_ang': [], 'key_pos': [], 'half_ang': [], 'half_pos': []}
    for f in range(nf):
        mats = compose(dec_q[f], dec_t[f], [sc_tracks[i][f] if sc_tracks[i] else None for i in range(n)])
        for i in range(n):
            ref = keys[f][1][i]
            err['key_ang'].append(qangle(mat_quat(ref)[0], mat_quat(mats[i])[0]))
            err['key_pos'].append(math.dist((ref[3], ref[7], ref[11]), (mats[i][3], mats[i][7], mats[i][11])))
    for f in range(nf - 1):
        # the runtime at frame f + 0.5: nlerp inside each track's own key segment
        qrow = [rot_at(rot_tracks[i], f + 0.5) for i in range(n)]
        trow = [vec_at(tr_tracks[i], f + 0.5) for i in range(n)]
        srow = [None if not sc_tracks[i] else tuple((a + b) / 2 for a, b in zip(sc_tracks[i][f], sc_tracks[i][f + 1])) for i in range(n)]
        mats = compose(qrow, trow, srow)
        for i in range(n):
            ref = halves[f][i]
            # the game's own evaluator jumps at a half frame (Euler keys across the +-pi wrap, cut
            # keys): the half pose lies far from both integer neighbours; counted, not scored
            a0, a1 = keys[f][1][i], keys[f + 1][1][i]
            gap = math.dist((a0[3], a0[7], a0[11]), (a1[3], a1[7], a1[11]))
            mid = ((a0[3] + a1[3]) / 2, (a0[7] + a1[7]) / 2, (a0[11] + a1[11]) / 2)
            if math.dist((ref[3], ref[7], ref[11]), mid) > gap + 20.0 or qangle(mat_quat(a0)[0], mat_quat(ref)[0]) > qangle(mat_quat(a0)[0], mat_quat(a1)[0]) + 20.0:
                err['src_jumps'] = err.get('src_jumps', 0) + 1
                continue
            err['half_ang'].append(qangle(mat_quat(ref)[0], mat_quat(mats[i])[0]))
            err['half_pos'].append(math.dist((ref[3], ref[7], ref[11]), (mats[i][3], mats[i][7], mats[i][11])))
    jumps = err.pop('src_jumps', 0)
    stats = {k: (max(v) if v else 0.0, sum(v) / len(v) if v else 0.0) for k, v in err.items()}
    static_rot = sum(1 for h in hdr_parts if h[0])
    hist = {}
    for i, (rsh, tsh) in enumerate(shifts):
        if not hdr_parts[i][0]:
            hist[f'rot_s{rsh}'] = hist.get(f'rot_s{rsh}', 0) + 1
    return bytes(enc), dict(frames=nf, parts=n, pose_bytes=pose_bytes, root_bytes=root_bytes,
                            gameplay_bytes=gp_bytes, static_rot_parts=static_rot, shift_hist=hist, src_half_jumps=jumps, gameplay_err_max=[max(e[0] for e in gp_err), max(e[1] for e in gp_err)],
                            scaled_parts=scaled, pose_stage=pose_stage, err=stats, raw_err=err)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', action='append', required=True, help='emNN.drs path (repeatable)')
    ap.add_argument('--skeleton', default='440', help='BIN entry index of the Ganado body skeleton')
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--pose-stage', choices=('demo-final', 'source-local'), default='demo-final',
                    help='source-local disables offline IK/blend and writes tagged EDCL v2; default retains v1')
    ap.add_argument('--entry', type=int, action='append', help='only these source FCV entry indices (repeatable)')
    ap.add_argument('--rotation-tolerance', type=float, default=ROT_TOL, help='local integer-key angular tolerance in degrees')
    ap.add_argument('--position-tolerance', type=float, default=POS_TOL, help='local integer-key translation tolerance in mm')
    ap.add_argument('--max-shift', type=int, choices=range(4), default=MAX_SHIFT)
    a = ap.parse_args()
    if not (math.isfinite(a.rotation_tolerance) and math.isfinite(a.position_tolerance) and
            a.rotation_tolerance >= 0 and a.position_tolerance >= 0):
        ap.error('local tolerances must be finite and nonnegative')
    os.makedirs(a.out, exist_ok=True)
    helper = evalhost.build('plain')
    source_files = ('src/game/motion.cpp', 'src/game/ik.cpp', 'src/game/model.cpp',
                    'src/game/math_sub.cpp', 'tools/motion/host/prepare.py',
                    'tools/motion/host/motion_host.cpp', 'tools/motion/host/stub/re4_host_stub.h')
    report = {'archives': {}, 'gameplay_parts': GAMEPLAY_PARTS, 'pose_stage': a.pose_stage,
              'rotation_tolerance_degrees': a.rotation_tolerance,
              'position_tolerance_mm': a.position_tolerance, 'max_shift': a.max_shift,
              'evaluator_root': MOTION_ROOT,
              'host_variant': 'plain, fno-fast-math, ffp-contract=off; no floor collision',
              'host_library_sha256': hashlib.sha256(open(helper, 'rb').read()).hexdigest(),
              'evaluator_sha256': {name: hashlib.sha256(open(os.path.join(MOTION_ROOT, name), 'rb').read()).hexdigest()
                                   for name in source_files}}
    seen = {}
    union_bytes = 0
    union_src = 0
    union_gp = 0
    union_jumps = 0
    all_err = {'key_ang': [], 'key_pos': [], 'half_ang': [], 'half_pos': []}
    for path in a.archive:
        arc = archive.Archive(path)
        model = modelbin.parse(arc.entry(int(a.skeleton)).data)
        model.check_tree()
        rest = [p.pos for p in model.parts]
        blob = bytearray(b'EDCL\x01\0\0\0')
        index = []
        clips = []
        skipped = []
        seq_bytes = 0
        events = 0
        for e in arc.entries():
            if e.tag == 'SEQ':
                seq_bytes += len(e.data)
                cnt = struct.unpack('>H', e.data[:2])[0]
                events += sum(1 for k in range(cnt) if e.data[4 + 4 * k + 2] != 0)
        n = 0
        for e in arc.entries('FCV'):
            if a.entry and e.index not in a.entry:
                continue
            if a.limit and n >= a.limit:
                break
            mot = fcv.parse(e.data)
            if not mot.joints or any(j.target() is not None and j.parts_no >= model.n_parts for j in mot.joints):
                skipped.append(e.index)
                continue
            h = hashlib.sha256(e.data).hexdigest()
            try:
                enc, info = bake_clip(model, mot, rest, None, pose_stage=a.pose_stage,
                                      rot_tol=a.rotation_tolerance, pos_tol=a.position_tolerance,
                                      max_shift=a.max_shift)
            except Exception as x:   # evaluator log errors etc.
                skipped.append(e.index)
                print(f'skip {arc.name}:{e.index}: {x}', file=sys.stderr)
                continue
            n += 1
            if h not in seen:
                seen[h] = len(enc)
                union_bytes += len(enc)
                union_src += len(e.data)
                union_gp += info['gameplay_bytes']
                union_jumps += info['src_half_jumps']
                for k in all_err:
                    all_err[k] += info['raw_err'][k]
            raw = info.pop('raw_err')
            info.update(index=e.index, src_bytes=len(e.data), bytes=len(enc), sha=h[:16])
            clips.append(info)
            index.append((e.index, len(blob)))
            blob += enc
            print(f"{arc.name}:{e.index} f={info['frames']} {len(e.data)}->{len(enc)} keyang={info['err']['key_ang'][0]:.3f} halfpos={info['err']['half_pos'][0]:.2f}", flush=True)
        # EDCL v1 file: 'EDCL' u16 version u16 count, count x {u16 entry, u16 frames, u32 offset}, then the
        # clips (offsets from the file start; each clip 4-byte aligned)
        # Distinct version as well as a per-clip stage: a live adapter must never
        # mistake the legacy demo's already-solved pose for source-local input.
        head = struct.pack('<4sHH', b'EDCL', 1 if a.pose_stage == 'demo-final' else 2, len(index))
        table_size = len(head) + 8 * len(index)
        body = bytes(blob[8:])
        table = b''.join(struct.pack('<HHI', ent, clips[k]['frames'], table_size + ofs - 8) for k, (ent, ofs) in enumerate(index))
        with open(os.path.join(a.out, arc.name.replace('.drs', '.edcl')), 'wb') as f:
            f.write(head + table + body)
        report['archives'][arc.name] = dict(
            source_archive_sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
            skeleton_sha256=hashlib.sha256(arc.entry(int(a.skeleton)).data).hexdigest(),
            skeleton_entry=int(a.skeleton), bones=model.n_parts, blend_joints=len(model.blend_table or []),
            clips=len(clips), skipped=skipped, fcv_src_bytes=sum(c['src_bytes'] for c in clips),
            baked_bytes=sum(c['bytes'] for c in clips),
            pose_bytes=sum(c['pose_bytes'] for c in clips), root_bytes=sum(c['root_bytes'] for c in clips),
            gameplay_bytes=sum(c['gameplay_bytes'] for c in clips),
            seq_bytes=seq_bytes, event_markers=events, clip_rows=clips)

    def st(v):
        v = sorted(v)
        return dict(max=v[-1], mean=sum(v) / len(v), p99=v[int(len(v) * 0.99)])
    report['union'] = dict(unique_clips=len(seen), baked_bytes=union_bytes, fcv_src_bytes=union_src,
                           gameplay_track_bytes=union_gp, gameplay_in_blob=GP_BAKED, src_half_jumps=union_jumps,
                           err={k: st(v) for k, v in all_err.items() if v})
    with open(os.path.join(a.out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report['union'], indent=1))
    for k, v in report['archives'].items():
        print(k, {x: y for x, y in v.items() if x != 'clip_rows'})


if __name__ == '__main__':
    main()

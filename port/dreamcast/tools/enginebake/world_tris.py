"""World occluder triangles from a PS2 world package (R4IM v3 ps2-world.re4mesh + R4PW sidecar + optional R4ID ids),
pure Python (no numpy). Layout as native_static.cpp ps2_open reads it (port of the world18 r4im_pkg.py reader).

occluders(dir, level) -> [(x0,y0,z0, x1,y1,z1, x2,y2,z2, cull)] world mm: opaque (pass 0) parts only, each cluster at
LOD level min(level, its last); every placement (the runtime re4dc_ps2_world_intact refuses a frame where any is
hidden, moved or gated). cull = the part's R4PW cull (0 two-sided, 1 CCW, 2 CW); -1.0 for a culled part of a mirrored
placement (negative determinant: its drawn face is not known here).
"""
import struct
from pathlib import Path


def _mul(A, B):   # 3x4 affines as nested lists
    return [[sum(A[r][k] * B[k][c] for k in range(3)) + (A[r][3] if c == 3 else 0.0) for c in range(4)] for r in range(3)]


class Pkg:
    def __init__(self, d):
        d = Path(d)
        m = (d / 'ps2-world.re4mesh').read_bytes()
        p = (d / 'ps2-world.r4pw').read_bytes()
        self.m = m
        h = struct.unpack_from('<4s15I4I', m, 0)
        (_, _, _, _, nmesh, npart, nlet, nvert, _, _, o_mesh, o_part, o_let, o_vert, o_strip, _) = h[:16]
        self.o_strip, self.o_vert = o_strip, o_vert
        ncl, nlv, o_plod, o_cl, o_lv = struct.unpack_from('<8I', m, 80)[:5]
        self.meshes = []
        for i in range(nmesh):
            r = struct.unpack_from('<HBBHHIII12f', m, o_mesh + 68 * i)
            self.meshes.append(dict(first_part=r[6], part_count=r[7], origin=r[8:11], step=r[11:14]))
        self.plod = [struct.unpack_from('<II', m, o_plod + 8 * i) for i in range(npart)]
        self.clusters = [struct.unpack_from('<6HII', m, o_cl + 20 * i)[6:8] for i in range(ncl)]
        self.levels = [struct.unpack_from('<IIf', m, o_lv + 12 * i)[:2] for i in range(nlv)]
        self.lets = [struct.unpack_from('<IIIHH', m, o_let + 28 * i) for i in range(nlet)]
        hp = struct.unpack_from('<4s7I', p, 0)
        assert hp[0] == b'R4PW'
        nplace, nparts = hp[2], hp[3]
        self.sidecar_crc = hp[5]
        self.pmeta = [struct.unpack_from('<IIHHBBBB', p, 32 + 16 * i)[4:6] for i in range(nparts)]
        base = 32 + 16 * nparts
        self.placements = []
        for i in range(nplace):
            r = struct.unpack_from('<HH12f', p, base + 52 * i)
            self.placements.append((r[0], r[1], [list(r[2 + 4 * k:6 + 4 * k]) for k in range(3)]))
        self.ids = None
        q = d / 'ps2-world.ids'
        if q.exists():
            b = q.read_bytes()
            mg, ver, count, crc = struct.unpack_from('<4sIII', b, 0)
            if mg == b'R4ID' and ver == 1 and count == nplace:
                self.ids = b[16:16 + count]

    def let_tris(self, li):
        fv, fs, sb, vc, sc = self.lets[li]
        m = self.m
        s = self.o_strip + fs
        if sc & 0x8000:
            off = struct.unpack_from('<%dH' % vc, m, s)
            corners = [struct.unpack_from('<3H', m, self.o_vert + 12 * (fv + o)) for o in off]
            s += 2 * vc
        else:
            corners = [struct.unpack_from('<3H', m, self.o_vert + 12 * (fv + k)) for k in range(vc)]
        end = s + sb
        tris = []
        while s < end:
            n = m[s]; s += 1
            idx = m[s:s + n]; s += n
            for k in range(n - 2):
                a, b, c = idx[k], idx[k + 1], idx[k + 2]
                tris.append((a, b, c) if k % 2 == 0 else (c, b, a))
        return corners, tris

    def occluders(self, level, exclude_dynamic=False, with_field=False):
        dynamic = set()
        if exclude_dynamic and self.ids is not None:
            cnt = {}
            for v in self.ids:
                cnt[v] = cnt.get(v, 0) + 1
            dynamic = {i for i, v in enumerate(self.ids) if v != 0xFF and cnt[v] == 1}
        out = []
        for mi, field, A in self.placements:
            if field in dynamic:
                continue
            mesh = self.meshes[mi]
            G = [[mesh['step'][0], 0, 0, mesh['origin'][0]], [0, mesh['step'][1], 0, mesh['origin'][1]],
                 [0, 0, mesh['step'][2], mesh['origin'][2]]]
            M = _mul(A, G)
            det = (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                   + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
            for k in range(mesh['part_count']):
                part = mesh['first_part'] + k
                ps, cull = self.pmeta[part]
                if ps != 0:
                    continue
                fc, cc = self.plod[part]
                for c in range(fc, fc + cc):
                    first, count = self.clusters[c]
                    fm, mc = self.levels[first + min(level, count - 1)]
                    for li in range(fm, fm + mc):
                        corners, tris = self.let_tris(li)
                        w = [[M[r][0] * x + M[r][1] * y + M[r][2] * z + M[r][3] for r in range(3)] for x, y, z in corners]
                        for a, b, cc2 in tris:
                            out.append(tuple(w[a]) + tuple(w[b]) + tuple(w[cc2]) +
                                       (float(cull) if det > 0 or not cull else -1.0,) + ((field,) if with_field else ()))
        return out

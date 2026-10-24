"""Read an R4IM v3 PS2 world package + R4PW sidecar (native_static.cpp ps2_open layout; room/instanced_mesh.hpp)."""
import struct
from pathlib import Path
import numpy as np


class Pkg:
    def __init__(self, mesh_path, sidecar_path):
        m = Path(mesh_path).read_bytes()
        p = Path(sidecar_path).read_bytes()
        self.mesh_crc = struct.unpack_from('<I', m, 12)[0]
        self.mesh_bytes = struct.unpack_from('<I', m, 8)[0]
        self.sidecar_crc = struct.unpack_from('<I', p, 20)[0]
        self.m = m
        h = struct.unpack_from('<4s15I4I', m, 0)
        (self.magic, self.version, _, _, self.nmesh, self.npart, self.nlet, self.nvert, self.nstrip, self.npal,
         self.o_mesh, self.o_part, self.o_let, self.o_vert, self.o_strip, self.o_pal) = h[:16]
        lh = struct.unpack_from('<8I', m, 80)
        self.ncl, self.nlv, self.o_plod, self.o_cl, self.o_lv = lh[:5]
        self.meshes = []
        for i in range(self.nmesh):
            r = struct.unpack_from('<HBBHHIII12f', m, self.o_mesh + 68 * i)
            self.meshes.append(dict(bin=r[0], first_part=r[6], part_count=r[7], origin=r[8:11], step=r[11:14],
                                    bmin=r[14:17], bmax=r[17:20]))
        self.parts = []
        for i in range(self.npart):
            r = struct.unpack_from('<IIBBBBII4f', m, self.o_part + 36 * i)
            self.parts.append(dict(first_let=r[6], let_count=r[7]))
        self.plod = [struct.unpack_from('<II', m, self.o_plod + 8 * i) for i in range(self.npart)]
        self.clusters = []
        for i in range(self.ncl):
            r = struct.unpack_from('<6HII', m, self.o_cl + 20 * i)
            self.clusters.append(dict(bmin=r[0:3], bmax=r[3:6], first_level=r[6], level_count=r[7]))
        self.levels = [struct.unpack_from('<IIf', m, self.o_lv + 12 * i) for i in range(self.nlv)]
        self.lets = []
        for i in range(self.nlet):
            r = struct.unpack_from('<IIIHH6H', m, self.o_let + 28 * i)
            self.lets.append(dict(first_vertex=r[0], first_strip=r[1], strip_bytes=r[2], vc=r[3], sc=r[4],
                                  bmin=r[5:8], bmax=r[8:11]))
        self.verts = np.frombuffer(m, dtype='<u2', count=self.nvert * 6, offset=self.o_vert).reshape(-1, 6)
        hp = struct.unpack_from('<4s7I', p, 0)
        assert hp[0] == b'R4PW'
        nplace, nparts = hp[2], hp[3]
        self.pmeta = []
        for i in range(nparts):
            r = struct.unpack_from('<IIHHBBBB', p, 32 + 16 * i)
            self.pmeta.append(dict(crc=r[0], fnv=r[1], w=r[2], h=r[3], pass_=r[4], cull=r[5]))
        base = 32 + 16 * nparts
        self.placements = []
        for i in range(nplace):
            r = struct.unpack_from('<HH12f', p, base + 52 * i)
            A = np.array(r[2:14], dtype=np.float64).reshape(3, 4)
            self.placements.append(dict(mesh=r[0], placement=r[1], affine=A))

    def grid(self, mesh):
        g = np.zeros((3, 4))
        for a in range(3):
            g[a, a] = mesh['step'][a]
            g[a, 3] = mesh['origin'][a]
        return g

    def wq(self, pl):
        """3x4 world-from-grid matrix for a placement."""
        A = pl['affine']
        G = self.grid(self.meshes[pl['mesh']])
        M = np.zeros((3, 4))
        M[:, :3] = A[:, :3] @ G[:, :3]
        M[:, 3] = A[:, :3] @ G[:, 3] + A[:, 3]
        return M

    def let_tris(self, li):
        """Level triangles of a meshlet as index triples into its corner list, plus the corners (grid u16)."""
        l = self.lets[li]
        indexed = bool(l['sc'] & 0x8000)
        fs = self.o_strip + l['first_strip']
        if indexed:
            off = np.frombuffer(self.m, dtype='<u2', count=l['vc'], offset=fs)
            corners = self.verts[l['first_vertex'] + off.astype(np.int64)]
            s = fs + 2 * l['vc']
        else:
            corners = self.verts[l['first_vertex']:l['first_vertex'] + l['vc']]
            s = fs
        end = s + l['strip_bytes']
        tris = []
        while s < end:
            n = self.m[s]; s += 1
            idx = self.m[s:s + n]; s += n
            for k in range(n - 2):
                a, b, c = idx[k], idx[k + 1], idx[k + 2]
                tris.append((a, b, c) if k % 2 == 0 else (c, b, a))
        return corners, tris

    def world_aabb(self, M, bmin, bmax):
        pts = []
        for bits in range(8):
            q = [bmax[a] if bits >> a & 1 else bmin[a] for a in range(3)]
            pts.append(M[:, :3] @ np.array(q, float) + M[:, 3])
        pts = np.array(pts)
        return pts.min(0), pts.max(0)

    def iter_clusters(self):
        """(placement index, part index, cluster index, pass, cull, world aabb) for every cluster."""
        for pi, pl in enumerate(self.placements):
            mesh = self.meshes[pl['mesh']]
            M = self.wq(pl)
            for k in range(mesh['part_count']):
                part = mesh['first_part'] + k
                fc, cc = self.plod[part]
                for c in range(fc, fc + cc):
                    cl = self.clusters[c]
                    lo, hi = self.world_aabb(M, cl['bmin'], cl['bmax'])
                    yield pi, part, c, self.pmeta[part]['pass_'], self.pmeta[part]['cull'], lo, hi

    def cluster_tris_world(self, pi, c, level=0):
        pl = self.placements[pi]
        M = self.wq(pl)
        cl = self.clusters[c]
        fm, mc, _ = self.levels[cl['first_level'] + level]
        out = []
        for li in range(fm, fm + mc):
            corners, tris = self.let_tris(li)
            w = corners[:, :3].astype(np.float64) @ M[:, :3].T + M[:, 3]
            for t in tris:
                out.append(w[list(t)])
        return np.array(out).reshape(-1, 3, 3)

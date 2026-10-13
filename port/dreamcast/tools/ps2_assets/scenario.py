"""Scenario readers retained from the September 2026 world converter; see README.md."""
import re
import struct
from pathlib import Path
GRP = re.compile(r'(PS2|GG)SCENARIO#SMD_(\d+)#SMX_(\d+)#TYPE_([0-9A-Fa-f]+)#BIN_(\d+)#(?:(COLOR|NORMAL)#)?')

def read_obj(path):
    v, vc, vt, vn, groups = [], [], [], [], []
    g = None
    mtl = None
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith('v '):
                p = line.split()
                v.append((float(p[1]), float(p[2]), float(p[3])))
                vc.append(tuple(float(x) for x in p[4:8]) if len(p) >= 8 else None)
            elif line.startswith('vt '):
                p = line.split(); vt.append((float(p[1]), float(p[2])))
            elif line.startswith('vn '):
                p = line.split(); vn.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith('g '):
                name = line[2:].strip()
                m = GRP.search(name)
                g = dict(name=name, smd=int(m.group(2)), smx=int(m.group(3)), type=m.group(4).upper(),
                         bin=int(m.group(5)), kind=m.group(6), faces=[])
                groups.append(g)
            elif line.startswith('usemtl'):
                mtl = line.split()[1]
            elif line.startswith('f '):
                cs = []
                for t in line.split()[1:]:
                    q = t.split('/')
                    cs.append((int(q[0]) - 1, int(q[1]) - 1 if len(q) > 1 and q[1] else -1,
                               int(q[2]) - 1 if len(q) > 2 and q[2] else -1))
                g['faces'].append((cs, mtl))
    return dict(v=v, vc=vc, vt=vt, vn=vn, groups=groups)

def read_mtl(path):
    out, cur = {}, None
    for line in open(path, encoding='utf-8', errors='replace'):
        s = line.strip()
        if s.startswith('newmtl'):
            cur = s.split()[1]; out[cur] = {}
        elif cur and s.startswith('map_Kd'):
            out[cur]['map_Kd'] = s.split(None, 1)[1]
            m = re.search(r'(\d+)\.(tga|png)$', s, re.I)
            out[cur]['tex'] = int(m.group(1)) if m else None
    return out

def read_idxmaterial(path):
    out, cur = {}, None
    for line in open(path, encoding='utf-8', errors='replace'):
        s = line.strip()
        if s.startswith('UseMaterial:'):
            cur = s.split(':', 1)[1]; out[cur] = {}
        elif cur and ':' in s and not s.startswith('#'):
            k, v = s.split(':', 1); out[cur][k] = v
    return out

def ps2_smd_lines(path):
    d = Path(path).read_bytes()
    magic, n, ob, ot, _ = struct.unpack_from('<HHIII', d, 0)
    rows = []
    for i in range(n):
        f = struct.unpack_from('<12fBBBBIII', d, 16 + 64 * i)
        rows.append(dict(pos=list(f[0:3]), ang=list(f[4:7]), scale=list(f[8:11]), bin=f[12], tpl=f[13],
                         smx=f[15], status=f[17]))
    return rows

def smx_entries(path, big_endian):
    """JADERLINK SMX layout: magic 0x10, count at byte 1, 144 B entries from 0x10."""
    d = Path(path).read_bytes()
    out = {}
    for i in range(d[1]):
        e = d[16 + 144 * i:16 + 144 * (i + 1)]
        out[e[0]] = dict(mode=e[1], opacity_hierarchy='0x%02x' % e[2],
                         face_culling={0: '0x00 front faces only (back-face cull)', 1: '0x01 back faces only',
                                       2: '0x02 both sides'}.get(e[3], '0x%02x' % e[3]),
                         light_switch='0x%08x' % struct.unpack('>I' if big_endian else '<I', e[4:8])[0],
                         alpha_hierarchy='0x%02x' % e[8], smx_colour_rgb=list(e[12:15]), smx_colour_a=e[15])
    return out

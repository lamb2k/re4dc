#!/usr/bin/env python3
"""Convert r100 scenery BINs into one instanced native mesh package per owner.

Each source BIN becomes one prelit mesh in its own model space, drawn by every
placement that uses it with the part's live source modelview. Placement,
visibility, collision and sequencing stay in the recovered game; only the GX
geometry representation changes. Source part identity is the part header's
byte offset from the BIN's first part header plus its stream size, which the
runtime compares against the live ModelData before drawing.

Package (little endian, sections 32-byte aligned):
  MeshHeader, MeshRecord[mesh], MeshPart[part], Meshlet[meshlet],
  CompactVertex12[vertex] (uint16 grid position, uint16 part UV, uint16 colour),
  strip bytes ([count][count local indices] per strip), palette ARGB words.
Meshlets hold at most 256 vertices so strip indices are single bytes.

Colour: r100 scenery takes its colour from GX lights (CLR0 is near-uniform and
often zero), so each vertex's colour slot carries its 12-bit octahedral source
normal under a 4-bit CLR0 palette index. The runtime lights every part once,
at its first draw, with the source's own evaluator and live light state, and
overwrites the slot with ARGB1555 (header reserved[0] = 1).
"""
import argparse
import hashlib
import math
import json
import re
import struct
import sys
import zlib
from pathlib import Path

MAGIC = b"R4IM"
VERSION = 1
HEADER = struct.Struct("<4s19I")          # 80 bytes, see pack below
MESH = struct.Struct("<HBBHHIII12f")       # 68 bytes
PART = struct.Struct("<IIBBBBII4f")        # 36 bytes
MESHLET = struct.Struct("<IIIHH6H")        # 28 bytes
VERTEX = struct.Struct("<6H")              # 12 bytes
MAX_MESHLET_VERTICES = 256
COLOR_OCT_NORMAL = 1  # header reserved[0]: colour slot = palette<<12 | oct normal, lit at runtime
COLOR_ARGB1555 = 2    # header reserved[0]: colour slot = prelit ARGB1555 (--color prelit; PS2 world)
COLOR_OCT_VERTEX = 3  # header reserved[0]: colour slot = oct normal (palette index 0), CLR0 per vertex in an ARGB8888
                      # table at header reserved[1] (--color oct-vertex: oct lighting without the 16-colour palette)
MAX_STRIP = 255


def f32(x):
    """The package stores grid parameters as float32; quantize with those."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def be16(d, o):
    return struct.unpack_from(">H", d, o)[0]


def be32(d, o):
    return struct.unpack_from(">I", d, o)[0]


def align(n, a=32):
    return (n + a - 1) & ~(a - 1)


def triangles_of(op, v):
    if op == 0x80:
        for i in range(0, len(v) - 3, 4):
            a, b, c, d = v[i:i + 4]
            yield a, b, c
            yield a, c, d
    elif op == 0x90:
        for i in range(0, len(v) - 2, 3):
            yield tuple(v[i:i + 3])
    else:
        raise ValueError(op)


def strip_triangles(s):
    """GX strip order: odd triangles swap their first two corners."""
    for k in range(len(s) - 2):
        yield (s[k + 1], s[k], s[k + 2]) if k & 1 else (s[k], s[k + 1], s[k + 2])


def canonical(t):
    i = t.index(min(t))
    return t[i:] + t[:i]


def stripify(tris):
    """Greedy directed-edge stripifier preserving GX winding."""
    tris = [t for t in tris if len(set(t)) == 3]
    edge = {}
    for n, (a, b, c) in enumerate(tris):
        for e, x in (((a, b), c), ((b, c), a), ((c, a), b)):
            edge.setdefault(e, []).append((n, x))
    used = [False] * len(tris)

    def grow(seed):
        s = list(seed)
        taken = []
        while True:
            k = len(s) - 2
            key = (s[k], s[k + 1]) if k % 2 == 0 else (s[k + 1], s[k])
            nxt = None
            for n, x in edge.get(key, ()):
                if not used[n] and n not in taken:
                    nxt = (n, x)
                    break
            if nxt is None:
                return s, taken
            taken.append(nxt[0])
            s.append(nxt[1])

    strips = []
    for n, t in enumerate(tris):
        if used[n]:
            continue
        used[n] = True
        best = None
        for r in range(3):
            seed = t[r:] + t[:r]
            s, taken = grow(seed)
            if best is None or len(taken) > len(best[1]):
                best = (s, taken)
        for m in best[1]:
            used[m] = True
        strips.append(best[0])
    return strips


def split_strip(s):
    """Chunks of <=MAX_STRIP corners; each restarts at an even triangle."""
    out = []
    start = 0
    while len(s) - start > MAX_STRIP:
        end = start + MAX_STRIP
        if (end - 2 - start) % 2:  # next chunk must begin at an even triangle
            end -= 1
        out.append(s[start:end])
        start = end - 2
    out.append(s[start:])
    return out


def parse_bin(data):
    flags = be32(data, 0x20)
    shift = data[0x28]
    clr = be32(data, 0x0C)
    tex = be32(data, 0x10)
    vtx = be32(data, 0x30)
    nvtx = be16(data, 0x38)
    nparts = be16(data, 0x1A)
    cursor = be32(data, 0x1C)
    record = 8 if flags & 0x80000000 else 6
    if data[0x19] != 1:
        raise ValueError("multi-node BIN")
    scale = 1.0 / (1 << shift)
    positions = [tuple(v * scale for v in struct.unpack_from(">3h", data, vtx + 8 * i)) for i in range(nvtx)]
    parts = []
    for _ in range(nparts):
        pflags = data[cursor + 0x0B]
        texture = data[cursor + 0x0C]
        alpha = data[cursor + 0x0E] if pflags & 4 else 0xFF
        size = be32(data, cursor + 0x18)
        s, end = cursor + 0x20, cursor + 0x20 + size
        strips, loose = [], []
        while s < end:
            op = data[s]
            s += 1
            if op == 0:
                continue
            if op not in (0x80, 0x90, 0x98):
                raise ValueError(f"GX opcode {op:#x}")
            n = be16(data, s)
            s += 2
            corners = []
            for i in range(n):
                r = s + i * record
                p = be16(data, r)
                c = be16(data, r + 4) if record == 8 else None
                t = be16(data, r + record - 2)
                corners.append((p, c, t, be16(data, r + 2)))
            if op == 0x98:
                strips.append(corners)
            else:
                loose.extend(triangles_of(op, corners))
            s += n * record
        # Identity is relative to the first part header: archive compaction may
        # move the part block inside a BIN, never reorder or resize its parts.
        parts.append(dict(offset=cursor - be32(data, 0x1C), size=size, flags=pflags, texture=texture, alpha=alpha,
                          strips=strips, loose=loose))
        cursor = end
    def uv(t):
        o = tex + 4 * t
        if flags & 0x80000000:
            a, b = struct.unpack_from(">2h", data, o)
            return a / 256.0, b / 256.0
        a, b = struct.unpack_from(">2H", data, o)
        return a / 32768.0, b / 32768.0

    def color(c):
        if c is None:
            return (255, 255, 255, 255)
        return tuple(data[clr + 4 * c:clr + 4 * c + 4])

    nrm = be32(data, 0x34)
    nrm8 = bool(flags & 0x20000000)

    def normal(n):
        if nrm8:
            v = struct.unpack_from(">3b", data, nrm + 4 * n)
        else:
            v = struct.unpack_from(">3h", data, nrm + 8 * n)
        length = sum(x * x for x in v) ** 0.5
        return tuple(x / length for x in v) if length else (0.0, 1.0, 0.0)

    return dict(flags=flags, nvtx=nvtx, nparts=nparts, positions=positions, parts=parts, uv=uv, color=color,
                normal=normal, bytes=len(data))


def oct12(n):
    """Unit normal -> 6+6-bit octahedral code (runtime: native_static.cpp oct_normal)."""
    x, y, z = n
    s = abs(x) + abs(y) + abs(z)
    x, y, z = x / s, y / s, z / s
    if z < 0:
        x, y = (1 - abs(y)) * (1 if x >= 0 else -1), (1 - abs(x)) * (1 if y >= 0 else -1)
    qx = min(63, max(0, round((x * 0.5 + 0.5) * 63)))
    qy = min(63, max(0, round((y * 0.5 + 0.5) * 63)))
    return qx | (qy << 6)


def convert(entries, color_scale, cell=0.0, min_fill=64):
    """entries: [(owner, common, bin, path)] -> package bytes, report.

    cell > 0 builds spatial meshlets: triangles are restripped per model-space
    cell and, once it holds min_fill corners, a meshlet closes rather than span
    more than cell units on any axis."""
    meshes, parts, meshlets, vertices, index_bytes = [], [], [], [], bytearray()
    palette, palette_index = [], {}
    report = []
    for owner, common, bin_no, path in entries:
        data = path.read_bytes()
        src = parse_bin(data)
        used = sorted({k[0] for p in src["parts"] for s in p["strips"] for k in s} |
                      {k[0] for p in src["parts"] for t in p["loose"] for k in t})
        if not used:
            continue
        pos = src["positions"]
        lo = [f32(min(pos[i][a] for i in used)) for a in range(3)]
        hi = [f32(max(pos[i][a] for i in used)) for a in range(3)]
        step = [f32(max((hi[a] - lo[a]) / 65535.0, 1e-6)) for a in range(3)]
        q = lambda i: tuple(min(65535, max(0, round((pos[i][a] - lo[a]) / step[a]))) for a in range(3))
        first_part = len(parts)
        mesh_tris = mesh_strips = 0
        for part in src["parts"]:
            if cell:
                # Spatial meshlets: restrip each model-space cell's triangles so a
                # meshlet's bounds describe a compact region the runtime can cull.
                tris = [t for s in part["strips"] for t in strip_triangles(s)]
                tris += [tuple(t) for t in part["loose"]]
                cells = {}
                for t in tris:
                    key = tuple(int(sum(pos[k[0]][a] for k in t) / 3 // cell) for a in range(3))
                    cells.setdefault(key, []).append(t)
                groups = [stripify(cells[key]) for key in sorted(cells)]
            else:
                strips = [list(s) for s in part["strips"]]
                if part["loose"]:
                    strips.extend(stripify([tuple(t) for t in part["loose"]]))
                groups = [strips]
            chunks = [c for g in groups for s in g for c in split_strip(s) if len(c) >= 3]
            uvs = [src["uv"](k[2]) for c in chunks for k in c]
            if uvs:
                ulo = [f32(min(u[a] for u in uvs)) for a in range(2)]
                uhi = [f32(max(u[a] for u in uvs)) for a in range(2)]
            else:
                ulo, uhi = [0.0, 0.0], [0.0, 0.0]
            uscale = [f32(max((uhi[a] - ulo[a]) / 65535.0, 1e-9)) for a in range(2)]
            first_meshlet = len(meshlets)
            current = None

            def close():
                if current and current["strips"]:
                    grid = [q(k[0]) for k in current["keys"]]
                    bmin = [min(g[a] for g in grid) for a in range(3)]
                    bmax = [max(g[a] for g in grid) for a in range(3)]
                    meshlets.append((current["first_vertex"], current["first_index"],
                                     len(index_bytes) - current["first_index"], len(current["keys"]),
                                     current["strips"], *bmin, *bmax))

            for chunk in chunks:
                fresh = [k for k in dict.fromkeys(chunk) if current is None or k not in current["local"]]
                clo = [min(pos[k[0]][a] for k in chunk) for a in range(3)]
                chi = [max(pos[k[0]][a] for k in chunk) for a in range(3)]
                # Large terrain triangles alone exceed a cell; a minimum fill keeps
                # them from becoming 28-byte meshlets of a few corners each.
                spread = current is not None and cell and len(current["keys"]) >= min_fill and \
                    max(max(chi[a], current["hi"][a]) - min(clo[a], current["lo"][a]) for a in range(3)) > cell
                if current is None or spread or len(current["keys"]) + len(fresh) > MAX_MESHLET_VERTICES:
                    close()
                    current = dict(first_vertex=len(vertices), first_index=len(index_bytes), keys=[], local={},
                                   strips=0, lo=clo, hi=chi)
                current["lo"] = [min(clo[a], current["lo"][a]) for a in range(3)]
                current["hi"] = [max(chi[a], current["hi"][a]) for a in range(3)]
                for k in dict.fromkeys(chunk):
                    if k in current["local"]:
                        continue
                    current["local"][k] = len(current["keys"])
                    current["keys"].append(k)
                    r, g, b, a = src["color"](k[1])
                    # Authored CLR0 alpha is kept: the runtime uses it only when the
                    # source selects vertex alpha for the part.
                    argb = (a << 24) | (min(255, round(r * color_scale)) << 16) | \
                           (min(255, round(g * color_scale)) << 8) | min(255, round(b * color_scale))
                    if argb not in palette_index:
                        palette_index[argb] = len(palette)
                        palette.append(argb)
                    if palette_index[argb] > 15:
                        raise ValueError("more than 16 CLR0 values in one package")
                    # Colour slot before the runtime light bake: CLR0 palette index
                    # (4 bits) over a 12-bit octahedral source normal.
                    slot = (palette_index[argb] << 12) | oct12(src["normal"](k[3]))
                    u, v = src["uv"](k[2])
                    qu = min(65535, max(0, round((u - ulo[0]) / uscale[0])))
                    qv = min(65535, max(0, round((v - ulo[1]) / uscale[1])))
                    vertices.append((*q(k[0]), qu, qv, slot))
                index_bytes.append(len(chunk))
                index_bytes.extend(current["local"][k] for k in chunk)
                current["strips"] += 1
                mesh_strips += 1
                mesh_tris += len(chunk) - 2
            close()
            parts.append((part["offset"], part["size"], part["texture"], part["alpha"], part["flags"], 0,
                          first_meshlet, len(meshlets) - first_meshlet, ulo[0], ulo[1], uscale[0], uscale[1]))
        meshes.append((bin_no, int(common), owner, src["nvtx"], src["nparts"], src["flags"],
                       first_part, len(parts) - first_part, *lo, *step, *lo, *hi))
        report.append(dict(owner=owner, common=bool(common), bin=bin_no, source_bytes=src["bytes"],
                           triangles=mesh_tris, strips=mesh_strips, parts=len(parts) - first_part))
    if len(palette) > 65536:
        raise ValueError("palette exceeds uint16")
    body = bytearray()
    offsets = {}
    for name, blob in (("mesh", b"".join(MESH.pack(*m) for m in meshes)),
                       ("part", b"".join(PART.pack(*p) for p in parts)),
                       ("meshlet", b"".join(MESHLET.pack(*m) for m in meshlets)),
                       ("vertex", b"".join(VERTEX.pack(*v) for v in vertices)),
                       ("index", bytes(index_bytes)),
                       ("palette", b"".join(struct.pack("<I", c) for c in palette))):
        start = align(HEADER.size + len(body)) - HEADER.size
        body.extend(b"\0" * (start - len(body)))
        offsets[name] = HEADER.size + len(body)
        body.extend(blob)
    body.extend(b"\0" * (align(HEADER.size + len(body)) - HEADER.size - len(body)))
    total = HEADER.size + len(body)
    header = HEADER.pack(MAGIC, VERSION, total, zlib.crc32(body),
                         len(meshes), len(parts), len(meshlets), len(vertices), len(index_bytes), len(palette),
                         offsets["mesh"], offsets["part"], offsets["meshlet"], offsets["vertex"],
                         offsets["index"], offsets["palette"], COLOR_OCT_NORMAL, 0, 0, 0)
    blob = header + bytes(body)
    summary = dict(package_bytes=total, meshes=len(meshes), parts=len(parts), meshlets=len(meshlets),
                   vertices=len(vertices), strip_bytes=len(index_bytes), palette=len(palette),
                   triangles=sum(r["triangles"] for r in report), strips=sum(r["strips"] for r in report),
                   source_bytes=sum(r["source_bytes"] for r in report), meshes_detail=report)
    return blob, summary


# ---- R4IM v2 (--lod): per-part clusters, each with levels of detail --------
#
# v2 keeps every v1 table and meaning (a part's meshlet range still covers all
# of its geometry, so the runtime lights it in one pass) and adds, after the
# 80-byte header, LodHeader{cluster_count, level_count, part_lod_offset,
# cluster_offset, level_offset, 3 reserved} and three tables:
#   PartLod[part]       {first_cluster, cluster_count}
#   Cluster[cluster]    {grid bounds min[3], max[3] (u16), first_level, level_count}
#   Level[level]        {first_meshlet, meshlet_count, error (model units, f32)}
# Levels of a cluster are ordered by increasing error, level 0 is the source
# geometry (error 0). The runtime draws, per visible cluster, the coarsest
# level whose error projects to at most MESH_LOD_PX pixels at the cluster's
# nearest depth; its meshlets are then culled one by one as in v1.
VERSION_LOD = 2
# v3 = v2 plus indexed meshlets: strip_count bit 15 set, first_vertex is the
# part's pool base and the meshlet's strip range starts with vertex_count u16
# pool offsets (2-byte aligned) before its strips (strip_bytes covers strips).
VERSION_SHARE = 3
INDEXED_MESHLET = 0x8000
LOD_HEADER = struct.Struct("<8I")          # 32 bytes
PART_LOD = struct.Struct("<II")            # 8 bytes
CLUSTER = struct.Struct("<6HII")           # 20 bytes
LEVEL = struct.Struct("<IIf")              # 12 bytes
# Scenery classes (v2/v3, optional). LodHeader reserved word 0 (class_offset)
# points at one u8 per mesh, in mesh order: the class a runtime distance rule
# keys on (0 = untagged: fog far only). Reserved word 1 (rule_offset) points at
# CLASS_RULES x {full_dm, cull_dm} (u16 decimetres; 0 = the runtime default),
# so each room package carries its own distances for one shared runtime rule.
MESH_CLASSES = {"default": 0, "ground": 1, "tree": 2, "landmark": 3, "clutter": 4, "structure": 5}
CLASS_RULES = 8
CLASS_RULE = struct.Struct("<HH")          # 4 bytes


def auto_class(ext):
    """Class of an untagged, non-tree BIN from its world extent (metres x, y,
    z): ground = both horizontal sides >= 2 m and either height under a
    quarter of the shorter one or a room-scale surround (radius >= 30 m);
    clutter = bounding radius under 1.5 m; else structure. Landmarks are
    never guessed: they are tagged per room (--class)."""
    narrow = min(ext[0], ext[2])
    radius = 0.5 * math.sqrt(sum(e * e for e in ext))
    if narrow >= 2.0 and (ext[1] < 0.25 * narrow or radius >= 30.0):
        return MESH_CLASSES["ground"]
    if radius < 1.5:
        return MESH_CLASSES["clutter"]
    return MESH_CLASSES["structure"]


# Pixels per unit of error at unit depth for the source's 60 degree fovy on
# 480 lines (cam_ctrl.cpp m_behind_fovy); only used to place card-thinning
# levels, the runtime uses the live projection.
NOMINAL_PX = 240.0 / math.tan(math.radians(30.0))
DEFAULT_EPS = (16.0, 32.0, 64.0, 128.0, 256.0, 512.0)   # world units (source mm)
DEFAULT_CARDS = ((0.5, 12000.0), (0.25, 20000.0), (0.125, 30000.0))  # (kept fraction, switch distance)


# ---- LOD substitution / export (--lod-substitute, --lod-export) -------------
#
# Other level sources (e.g. PS2-derived or Blender-decimated meshes) plug in per
# BIN part without touching the runtime. A manifest lists, per (owner, bin,
# part index in the BIN's source part order), OBJ meshes in that BIN's model
# space (the space --lod-export writes: v = source positions after the BIN's
# position shift, vt = source UVs, front faces in exported/GX winding) and the
# world error (source mm) at which each may be drawn:
#   {"parts": [{"owner": "0x01", "bin": 17, "part": 0, "offset": 0,   # offset optional, checked
#               "levels": [{"error": 0, "obj": "a.obj"},             # error 0 replaces the source
#                          {"error": 150, "obj": "b.obj"}]}]}
# A substituted part keeps its identity (texture, alpha, flags, source part
# offset: the game still decides when it draws) and becomes one cluster whose
# levels are exactly the manifest's (plus the source as level 0 when no entry
# has error 0). Corner colours (CLR0 palette) come from the nearest source
# vertex of that part, normals from vn or the nearest source vertex, so the
# runtime lighting and 16-colour palette are unchanged. Relative OBJ paths are
# relative to the manifest.
def parse_obj(path):
    """-> dict(v, vt, vn, groups, faces=[(usemtl name, ((v, vt or None, vn or None) 0-based indices) * 3)],
    face_groups=[index into groups per face]); polygons fan-triangulated. Every g/o line opens a
    group (faces before the first one belong to "default")."""
    v, vt, vn, faces, groups, face_groups = [], [], [], [], [], []
    material = ""
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if not f or f[0].startswith("#"):
            continue
        if f[0] == "v":
            v.append(tuple(float(x) for x in f[1:4]))
        elif f[0] == "vt":
            vt.append(tuple(float(x) for x in f[1:3]))
        elif f[0] == "vn":
            vn.append(tuple(float(x) for x in f[1:4]))
        elif f[0] == "usemtl":
            material = f[1] if len(f) > 1 else ""
        elif f[0] in ("g", "o"):
            groups.append(f[1] if len(f) > 1 else "g%d" % len(groups))
        elif f[0] == "f":
            corners = []
            for c in f[1:]:
                idx = (c.split("/") + ["", ""])[:3]

                def pick(table, i):
                    if not i:
                        return None
                    i = int(i)
                    return i - 1 if i > 0 else len(table) + i
                corners.append((pick(v, idx[0]), pick(vt, idx[1]), pick(vn, idx[2])))
            if not groups:
                groups.append("default")
            for k in range(1, len(corners) - 1):
                faces.append((material, (corners[0], corners[k], corners[k + 1])))
                face_groups.append(len(groups) - 1)
    return dict(v=v, vt=vt, vn=vn, groups=groups, faces=faces, face_groups=face_groups)


def read_obj(path):
    """-> [((xyz, uv or None, normal or None) * 3)] fan-triangulated faces."""
    obj = parse_obj(path)

    def value(table, i):
        return None if i is None else table[i]
    return [tuple((obj["v"][c[0]], value(obj["vt"], c[1]), value(obj["vn"], c[2])) for c in f)
            for _, f in obj["faces"]]


def load_substitutes(manifest):
    """-> {(owner, bin, part_index): dict(offset, levels=[(error_world, faces)])}"""
    if Path(manifest).is_dir():
        return {}
    data = json.loads(Path(manifest).read_text())
    base = Path(manifest).parent
    out = {}
    for entry in data.get("parts", []):
        owner = entry["owner"]
        owner = int(owner, 0) if isinstance(owner, str) else int(owner)
        levels = sorted(((float(l["error"]), read_obj(base / l["obj"])) for l in entry["levels"]), key=lambda l: l[0])
        out[(owner, int(entry["bin"]), int(entry["part"]))] = dict(offset=entry.get("offset"), levels=levels)
    return out


def write_obj(path, tris, positions, comment):
    """tris as convert_lod: (ids, ((uv, normal, colour) * 3))."""
    vs, vts, vns, lines = {}, {}, {}, []

    def index(table, key):
        if key not in table:
            table[key] = len(table) + 1
        return table[key]
    for ids, attrs in tris:
        lines.append("f " + " ".join("%d/%d/%d" % (index(vs, positions[i]), index(vts, a[0]), index(vns, a[1]))
                                     for i, a in zip(ids, attrs)))
    out = ["# " + c for c in comment]
    out += ["v %.9g %.9g %.9g" % p for p in vs]
    out += ["vt %.9g %.9g" % t for t in vts]
    out += ["vn %.6g %.6g %.6g" % n for n in vns]
    Path(path).write_text("\n".join(out + lines) + "\n")


def substitute_levels(sub, tris, welded, factor_scale=1.0):
    """Manifest levels of one part -> [(error_model, tris)] in convert_lod's
    triangle form, new vertices appended to welded (exact positions reuse ids)."""
    where = {p: i for i, p in welded.items()}
    source = {}
    for ids, attrs in tris:
        for i, a in zip(ids, attrs):
            source.setdefault(welded[i], a)
    points = list(source)

    def nearest(p):
        best = min(points, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2)
        return source[best]
    out = [] if any(e == 0.0 for e, _ in sub["levels"]) else [(0.0, tris)]
    for error, faces in sub["levels"]:
        lt = []
        for f in faces:
            ids, attrs = [], []
            for p, uv, n in f:
                p = tuple(float(f32(x)) for x in p)
                if p not in where:
                    where[p] = len(welded)
                    welded[where[p]] = p
                ids.append(where[p])
                near = nearest(p)
                if n is not None:
                    length = math.sqrt(sum(x * x for x in n)) or 1.0
                    n = tuple(x / length for x in n)
                attrs.append((tuple(uv) if uv is not None else near[0], n if n is not None else near[1], near[2]))
            if len(set(ids)) == 3:
                lt.append((tuple(ids), tuple(attrs)))
        out.append((error / factor_scale, lt))
    return out


# ---- Whole-BIN replacement (--lod-substitute DIR, or a manifest's "replace") --
#
# Unlike per-part levels above, a replacement swaps a BIN's render geometry
# before level generation: the BIN's QEM / card levels are then built from the
# replacement exactly as from source geometry. The OBJ is in the BIN's model
# space; faces are assigned to source parts by material name "p<part>_..."
# (e.g. "p0_bark"), and a source part with no faces draws nothing. Part
# identity (source offset/size), texture, alpha and flags stay the source's,
# so the game still decides when and where every part draws; collision,
# placement and sequencing never read this geometry. Each part takes the
# CLR0 colour of its first source corner; normals come from vn, else from the
# replacement's face normals merged across faces meeting within
# REPLACE_SMOOTH_ANGLE at one position. Levels that simplify to no triangles
# are dropped for replaced BINs only (a replacement must not vanish at
# distance; source BINs keep their authored empty levels). Directory form:
# DIR/<OWNER>_<bin>.obj with OWNER MAINSCENARIO (0xff), COMMON (0xfe) or
# FILE_<nn>; manifest form: {"replace": [{"owner": "0xfe", "bin": 3,
# "obj": "COMMON_3.obj"}]} (relative to the manifest).
REPLACE_SMOOTH_ANGLE = 45.0
# --lod-cluster-trees: a connected component taller than this (world mm) is a trunk
TREE_TRUNK_MM = 3000.0
OWNER_NAMES = {0xFF: "MAINSCENARIO", 0xFE: "COMMON"}


def owner_name(owner):
    return OWNER_NAMES.get(owner, "FILE_%02d" % owner)


def load_replacements(path):
    """-> {(owner, bin): OBJ path} from a directory or a manifest's "replace" list."""
    path = Path(path)
    out = {}
    if path.is_dir():
        names = {v: k for k, v in OWNER_NAMES.items()}
        for p in sorted(path.glob("*.obj")):
            m = re.fullmatch(r"(MAINSCENARIO|COMMON|FILE_(\d+))_(\d+)", p.stem)
            if not m:
                raise ValueError("%s: expected <OWNER>_<bin>.obj" % p)
            owner = names[m.group(1)] if m.group(2) is None else int(m.group(2))
            out[(owner, int(m.group(3)))] = p
        return out
    data = json.loads(path.read_text())
    for entry in data.get("replace", []):
        owner = entry["owner"]
        owner = int(owner, 0) if isinstance(owner, str) else int(owner)
        out[(owner, int(entry["bin"]))] = path.parent / entry["obj"]
    return out


def _mesh_lod():
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mesh_lod
    return mesh_lod


def _unit(v):
    s = math.sqrt(sum(x * x for x in v))
    return tuple(x / s for x in v) if s > 1e-12 else (0.0, 1.0, 0.0)


def merge_normals(items, angle):
    """items [(key, unit normal, weight)] at one position -> {key: merged normal};
    greedy by weight, a normal joins the first group within angle."""
    c = math.cos(math.radians(angle))
    groups = []  # [weighted sum, unit direction, keys]
    for key, n, w in sorted(items, key=lambda t: -t[2]):
        for g in groups:
            if sum(a * b for a, b in zip(g[1], n)) >= c:
                g[0] = [a + w * b for a, b in zip(g[0], n)]
                g[1] = _unit(g[0])
                g[2].append(key)
                break
        else:
            groups.append([[w * b for b in n], n, [key]])
    return {key: g[1] for g in groups for key in g[2]}


def replace_source(src, path, angle=REPLACE_SMOOTH_ANGLE):
    """parse_bin() result -> the same BIN with every part's triangles taken from
    the replacement OBJ (loose triangles; corners carry uv/normal/colour values)."""
    mesh_lod = _mesh_lod()
    obj = parse_obj(path)
    positions = obj["v"]
    part_faces = [[] for _ in src["parts"]]
    for material, f in obj["faces"]:
        m = re.match(r"p(\d+)(?:_|$)", material)
        if not m or int(m.group(1)) >= len(part_faces):
            raise ValueError("%s: material %r names no source part (0..%d)" % (path, material, len(part_faces) - 1))
        part_faces[int(m.group(1))].append(f)
    ids, _ = mesh_lod.weld(positions)
    items = {}
    for pi, faces in enumerate(part_faces):
        for fi, f in enumerate(faces):
            if all(c[2] is not None for c in f):
                continue
            a, b, c = (positions[k[0]] for k in f)
            cross = mesh_lod._cross(mesh_lod._sub(b, a), mesh_lod._sub(c, a))
            area = math.sqrt(sum(x * x for x in cross))
            if area <= 0:
                continue
            for j, k in enumerate(f):
                items.setdefault(ids[k[0]], []).append(((pi, fi, j), tuple(x / area for x in cross), area))
    face_normal = {}
    for group in items.values():
        for key, n in merge_normals(group, angle).items():
            face_normal[key] = tuple(round(x, 6) for x in n)
    parts = []
    for pi, (part, faces) in enumerate(zip(src["parts"], part_faces)):
        first = next(iter([k for s in part["strips"] for k in s] + [k for t in part["loose"] for k in t]), None)
        color = src["color"](first[1]) if first else (255, 255, 255, 255)
        loose = []
        for fi, f in enumerate(faces):
            loose.append(tuple((k[0], color,
                                tuple(round(x, 6) for x in obj["vt"][k[1]]) if k[1] is not None else (0.0, 0.0),
                                _unit(obj["vn"][k[2]]) if k[2] is not None else
                                face_normal.get((pi, fi, j), (0.0, 1.0, 0.0)))
                               for j, k in enumerate(f)))
        parts.append(dict(part, strips=[], loose=loose))

    def same(x):
        return x
    return dict(src, positions=positions, parts=parts, uv=same, normal=same, color=same)


def surface(tris, positions):
    """Triangle area and summed normal-area vector (model units)."""
    area, normal = 0.0, [0.0, 0.0, 0.0]
    for t in tris:
        a, b, c = (positions[v] for v in t[0])
        u = [b[i] - a[i] for i in range(3)]
        w = [c[i] - a[i] for i in range(3)]
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        area += math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) / 2
        normal = [normal[i] + n[i] / 2 for i in range(3)]
    return area, normal


def convert_lod(entries, color_scale, scales=None, px=2.0, eps_world=DEFAULT_EPS, cluster_world=20000.0,
                cluster_tris_max=768, cards=DEFAULT_CARDS, min_gain=0.5, max_levels=5, bias=None,
                substitutes=None, export_dir=None, replacements=None, floor=None, share=False,
                classes=None, class_auto=False, class_rules=None, cluster_trees=None, cluster_bins=None,
                source=None, color_mode="oct", decimate=None):
    """entries as convert(); scales: {(owner, bin): world scale} (largest
    placement scale, default 1) so that errors are chosen in world units.
    bias: {(owner, bin): factor}; stored level errors are multiplied by it, so
    a factor of 3/8 lets that BIN reach 8 px where the runtime allows 3 px.
    substitutes: load_substitutes(); export_dir: write each part's levels as
    OBJ (<owner>-<bin>-p<part>-L<k>.obj) plus parts.json there.
    replacements: load_replacements(); whole-BIN render geometry swapped in
    before level generation (see replace_source).
    floor: {(owner, bin) or None: world error}; level 0 of those BINs (None:
    every BIN) is the source simplified to that error before clustering, so
    near-coplanar detail the eye cannot see at the nearest view is not drawn.
    Substituted and card-field parts keep their source level 0.
    share: coarse meshlets reuse the part's existing vertices through a u16
    index table (R4IM v3, INDEXED_MESHLET; room/instanced_mesh.hpp).
    classes: {(owner, bin): MESH_CLASSES code}; class_auto: untagged BINs get
    tree (card field or replaced BIN) or auto_class(); class_rules: {code:
    (full_dm, cull_dm)}. Without any of the three the package is unchanged.
    source: callable(path) -> parse_bin()-shaped dict, in place of parse_bin(path.read_bytes()) (a
    non-BIN source such as the PS2 world, tools/ps2_world_r4im.py).
    decimate: callable(owner, bin, [model-space xyz of the cluster's corners]) -> triangle ratio or None (roomscan
    dec, default none): that cluster's level 0 is simplified in place to at most ratio of its triangles, its
    boundary vertices locked (no cracks), before its levels are built; no level records are added. Kept only
    when the piece's surface area stays within 25% (a lost piece keeps the source).
    color_mode: "oct" (default: palette index + octahedral normal, lit at runtime) or "prelit": the
    colour slot is the corner's final ARGB1555 (source color() 8-bit RGBA, color_scale ignored), header
    reserved[0] = COLOR_ARGB1555 and a one-word palette; the runtime lights nothing. "oct-vertex": the colour
    slot is palette index 0 + the octahedral normal, each vertex's CLR0 x color_scale (as an oct palette entry) is
    an ARGB8888 table at header reserved[1], reserved[0] = COLOR_OCT_VERTEX: lit at runtime exactly as oct, with
    any number of colours (the runtime's adopt_by_encoding, game SCENERY_ENCODING=1)."""
    mesh_lod = _mesh_lod()
    # cluster_trees: {(owner, bin)} grove BINs whose clusters are formed per tree (tree_groups)
    cluster_trees = set(cluster_trees or ())
    # cluster_bins: {(owner, bin): world mm} per-BIN cluster size in place of cluster_world (a compact
    # object the default size keeps whole, e.g. a large tree the camera can stand inside, is split so
    # each region picks its own level)
    cluster_bins = cluster_bins or {}
    groves = 0
    floor = floor or {}
    decimated = [0, 0, 0]  # triangles before, after; parts refused
    scales = scales or {}
    bias = bias or {}
    substitutes = substitutes or {}
    replacements = replacements or {}
    both = {(o, b) for o, b, _ in substitutes} & set(replacements)
    if both:
        raise ValueError("BINs both replaced and given per-part levels: %s" % sorted(both))
    used_substitutes = set()
    used_replacements = set()
    floored = [0, 0, 0]  # triangles before, after; parts refused
    shared_vertices = [0, 0]  # indexed meshlets: reused vertices, table entries
    classes = classes or {}
    class_rules = class_rules or {}
    mesh_classes = []
    exported = []
    meshes, parts, meshlets, vertices, index_bytes = [], [], [], [], bytearray()
    part_lods, clusters, levels = [], [], []
    palette, palette_index = [], {}
    report = []

    def slot_of(color, normal):
        r, g, b, a = color
        if color_mode == "oct-vertex":
            # The stored key carries the vertex colour too (corners that differ only in colour stay apart);
            # the vertex slot keeps the low 12 bits (palette index 0 + oct normal), the table the colour.
            if not palette:
                palette.append(0xFFFFFFFF)
            argb = (a << 24) | (min(255, round(r * color_scale)) << 16) |                    (min(255, round(g * color_scale)) << 8) | min(255, round(b * color_scale))
            return (argb << 12) | oct12(normal)
        if color_mode == "prelit":
            if not palette:
                palette.append(0xFFFFFFFF)
            q = lambda v: min(31, max(0, round(v * 31 / 255)))
            return (0x8000 if a >= 128 else 0) | (q(r) << 10) | (q(g) << 5) | q(b)
        argb = (a << 24) | (min(255, round(r * color_scale)) << 16) | \
               (min(255, round(g * color_scale)) << 8) | min(255, round(b * color_scale))
        if argb not in palette_index:
            palette_index[argb] = len(palette)
            palette.append(argb)
        if palette_index[argb] > 15:
            raise ValueError("more than 16 CLR0 values in one package")
        return (palette_index[argb] << 12) | oct12(normal)

    for owner, common, bin_no, path in entries:
        src = source(path) if source else parse_bin(path.read_bytes())
        replaced = (owner, bin_no) in replacements
        if replaced:
            src = replace_source(src, replacements[(owner, bin_no)])
            used_replacements.add((owner, bin_no))
        pos = src["positions"]
        used = sorted({k[0] for p in src["parts"] for s in p["strips"] for k in s} |
                      {k[0] for p in src["parts"] for t in p["loose"] for k in t})
        if not used:
            continue
        scale = float(scales.get((owner, bin_no), 1.0)) or 1.0
        factor = float(bias.get((owner, bin_no), 1.0))
        extra = [c[0] for (o, b, _), sub in substitutes.items() if (o, b) == (owner, bin_no)
                 for _, faces in sub["levels"] for f in faces for c in f]
        lo = [f32(min([pos[i][a] for i in used] + [p[a] for p in extra])) for a in range(3)]
        hi = [f32(max([pos[i][a] for i in used] + [p[a] for p in extra])) for a in range(3)]
        step = [f32(max((hi[a] - lo[a]) / 65535.0, 1e-6)) for a in range(3)]
        weld_ids, welded = mesh_lod.weld(pos)

        def grid(p):
            return tuple(min(65535, max(0, round((p[a] - lo[a]) / step[a]))) for a in range(3))
        first_part = len(parts)
        mesh_report = []
        for part_index, part in enumerate(src["parts"]):
            raw = [t for s in part["strips"] for t in strip_triangles(s)] + [tuple(t) for t in part["loose"]]
            tris = []
            for t in raw:
                ids = tuple(weld_ids[k[0]] for k in t)
                if len(set(ids)) < 3:
                    continue
                tris.append((ids, tuple((src["uv"](k[2]), src["normal"](k[3]), src["color"](k[1])) for k in t)))
            # Clusters: large parts split by triangle centroid into world cells;
            # vertices shared between cells are locked in every level.
            # Clusters: large parts are split (k-d, by triangle centroid) so each
            # region picks its own level; vertices shared between clusters are
            # locked in every level. Card fields split finer: they have no
            # shared vertices and thin best close to the camera.
            sub = substitutes.get((owner, bin_no, part_index))
            if sub is not None:
                if sub["offset"] is not None and int(sub["offset"]) != part["offset"]:
                    raise ValueError("substitute %s:%d part %d: offset %d != source %d" % (
                        hex(owner), bin_no, part_index, int(sub["offset"]), part["offset"]))
                used_substitutes.add((owner, bin_no, part_index))
            card = sub is None and mesh_lod.is_card_field(tris, bool(part["flags"] & 4))
            floor_world = floor.get((owner, bin_no), floor.get(None, 0.0))
            if floor_world > 0 and sub is None and not card and tris:
                floor_tris = mesh_lod.simplify_levels(welded, tris, [floor_world / scale], (), 1.0)[-1][1]
                # Kept only when it covers the same surface: area and summed
                # normal-area within 0.2%, so a fold or a lost piece (the
                # simplifier has no flip test on unlocked flat parts) keeps the source.
                a0, n0 = surface(tris, welded)
                a1, n1 = surface(floor_tris, welded)
                if floor_tris and abs(a1 - a0) <= 0.002 * a0 and math.dist(n0, n1) <= 0.002 * a0:
                    floored[0] += len(tris)
                    floored[1] += len(floor_tris)
                    tris = floor_tris
                else:
                    floored[2] += 1
            trees = None
            cw = cluster_bins.get((owner, bin_no), cluster_world)
            if (owner, bin_no) in cluster_trees and sub is None and tris and not card:
                trees = mesh_lod.tree_groups(tris, welded, TREE_TRUNK_MM / scale)
            if sub is not None:
                cluster_tris = [tris]
            elif not tris:
                cluster_tris = []   # a replacement may leave a source part empty: it draws nothing
            elif card:
                cluster_tris = mesh_lod.kd_clusters(tris, welded, 256, 0.4 * cw / scale,
                                                    0.2 * cw / scale)
            elif trees:
                # --lod-cluster-trees: no cluster spans two trees and each tree's clusters are
                # contiguous, so the runtime can draw a tree as its own impostor (s16 impt records)
                cluster_tris, tree_rows = [], []
                for g in trees:
                    cs = mesh_lod.kd_clusters([tris[i] for i in g], welded, cluster_tris_max, cw / scale,
                                              0.4 * cw / scale)
                    tree_rows.append(dict(first=len(cluster_tris), clusters=len(cs), triangles=len(g)))
                    cluster_tris += cs
            else:
                cluster_tris = mesh_lod.kd_clusters(tris, welded, cluster_tris_max, cw / scale,
                                                    0.4 * cw / scale)
            locked = set()
            if len(cluster_tris) > 1 and not card and sub is None:
                owners = {}
                for n, ct in enumerate(cluster_tris):
                    for t in ct:
                        for v in t[0]:
                            owners.setdefault(v, set()).add(n)
                locked = {v for v, s in owners.items() if len(s) > 1}
            if decimate and sub is None and not card:
                # 4 m pieces of each cluster decide on their own (a 20 m cluster often reaches the play area at one end
                # only); vertices shared between pieces or clusters are locked, so no cracks open
                for n, ct in enumerate(cluster_tris):
                    if len(ct) < 8:
                        continue
                    pieces = mesh_lod.kd_clusters(ct, welded, 256, 4000.0 / scale, 1600.0 / scale)
                    cnt = {}
                    for pc in pieces:
                        for v in {v for t in pc for v in t[0]}:
                            cnt[v] = cnt.get(v, 0) + 1
                    lock = set(locked) | {v for v, k in cnt.items() if k > 1}
                    out, changed = [], False
                    for pc in pieces:
                        r = decimate(owner, bin_no, [welded[v] for t in pc for v in t[0]]) if len(pc) >= 8 else None
                        pick = None
                        if r:
                            # far / prop decimation is an approved approximation: the UV seam guard is relaxed to the
                            # scan1 value (0.2) for these pieces only
                            g0 = mesh_lod.UV_GUARD
                            mesh_lod.UV_GUARD = max(g0 or 0.0, 0.2)
                            try:
                                lv = mesh_lod.simplify_levels(welded, pc, [e / scale for e in (5, 10, 20, 40, 80, 160, 320, 640,
                                                                                              1280, 2560, 5120)], lock, 1.0)
                            finally:
                                mesh_lod.UV_GUARD = g0
                            pick = next((t for _, t in lv[1:] if t and len(t) <= r * len(pc)), None)
                            if pick is not None and abs(surface(pick, welded)[0] - surface(pc, welded)[0]) > 0.25 * surface(pc, welded)[0]:
                                pick = None
                            if pick is None:
                                decimated[2] += 1
                        if pick is not None:
                            decimated[0] += len(pc); decimated[1] += len(pick); out += pick; changed = True
                        else:
                            out += pc
                    if changed:
                        cluster_tris[n] = out
            built = []  # per cluster: [(error_model, tris)]
            for ct in cluster_tris:
                if sub is not None:
                    built.append(substitute_levels(sub, tris, welded, factor_scale=scale))
                    continue
                if not ct:
                    continue
                if card:
                    lv = mesh_lod.card_levels(ct, welded, [1.0] + [k for k, _ in cards])
                    errs = [0.0] + [d * px / NOMINAL_PX / scale for _, d in cards]
                    ls = [(errs[0], lv[0])]
                    for e, t in zip(errs[1:], lv[1:]):
                        if len(t) <= min_gain * len(ls[-1][1]) or not t:
                            ls.append((e, t))
                else:
                    ls = mesh_lod.simplify_levels(welded, ct, [e / scale for e in eps_world], locked, min_gain)
                    if replaced:
                        ls = [lv for lv in ls if lv[1]] or ls[:1]
                built.append(ls[:max_levels])
            corners = [a for ls in built for _, lt in ls for t in lt for a in t[1]]
            if corners:
                ulo = [f32(min(c[0][a] for c in corners)) for a in range(2)]
                uhi = [f32(max(c[0][a] for c in corners)) for a in range(2)]
            else:
                ulo, uhi = [0.0, 0.0], [0.0, 0.0]
            uscale = [f32(max((uhi[a] - ulo[a]) / 65535.0, 1e-9)) for a in range(2)]

            def stored_corner(v, attrs, ulo=ulo, uscale=uscale):
                uv, normal, color = attrs
                return (v, (min(65535, max(0, round((uv[0] - ulo[0]) / uscale[0]))),
                            min(65535, max(0, round((uv[1] - ulo[1]) / uscale[1]))), slot_of(color, normal)))
            first_meshlet = len(meshlets)
            first_cluster = len(clusters)
            part_levels = []
            pool, pool_base = {}, len(vertices)  # this part's stored vertices by key
            for ls in built:
                cgrid = [grid(welded[v]) for _, lt in ls for t in lt for v in t[0]]
                first_level = len(levels)
                for li, (err, lt) in enumerate(ls):
                    # Corners are keyed by what is stored (grid position, 16-bit
                    # UV, palette slot + 12-bit normal): source attributes that
                    # quantise alike are one vertex, so strips run through them.
                    keyed = [tuple(stored_corner(v, c) for v, c in zip(t[0], t[1])) for t in lt]
                    strips = [c for s in mesh_lod.stripify(keyed) for c in split_strip(s) if len(c) >= 3]
                    level_first = len(meshlets)
                    for chunk in mesh_lod.pack_meshlets(strips, MAX_MESHLET_VERTICES, lambda k: welded[k[0]]):
                        keys = list(dict.fromkeys(c for s in chunk for c in s))
                        local = {c: i for i, c in enumerate(keys)}
                        # --lod-share: a coarse meshlet whose vertices mostly
                        # exist already in this part references them through a
                        # u16 table (part pool relative) instead of storing them.
                        fresh = [c for c in keys if c not in pool]
                        indexed = (share and li > 0 and 12 * (len(keys) - len(fresh)) > 2 * len(keys) + 2 and
                                   len(vertices) + len(fresh) - pool_base <= 65536)
                        if indexed:
                            for c in fresh:
                                pool[c] = len(vertices)
                                v, (qu, qv, slot) = c
                                vertices.append((*grid(welded[v]), qu, qv, slot))
                            if len(index_bytes) & 1:
                                index_bytes.append(0)
                            first_vertex, first_index = pool_base, len(index_bytes)
                            index_bytes.extend(struct.pack("<%dH" % len(keys), *(pool[c] - pool_base for c in keys)))
                            strip_start = len(index_bytes)
                            shared_vertices[0] += len(keys) - len(fresh)
                            shared_vertices[1] += len(keys)
                        else:
                            first_vertex, first_index = len(vertices), len(index_bytes)
                            strip_start = first_index
                            for c in keys:
                                pool.setdefault(c, len(vertices))
                                v, (qu, qv, slot) = c
                                vertices.append((*grid(welded[v]), qu, qv, slot))
                        for s in chunk:
                            index_bytes.append(len(s))
                            index_bytes.extend(local[c] for c in s)
                        g = [grid(welded[c[0]]) for c in keys]
                        meshlets.append((first_vertex, first_index, len(index_bytes) - strip_start, len(keys),
                                         len(chunk) | (INDEXED_MESHLET if indexed else 0),
                                         *[min(q[a] for q in g) for a in range(3)],
                                         *[max(q[a] for q in g) for a in range(3)]))
                    levels.append((level_first, len(meshlets) - level_first, f32(err * factor)))
                    part_levels.append(dict(level=li, error_world=round(err * scale, 1), triangles=len(lt),
                                            corners=sum(len(s) for s in strips), strips=len(strips),
                                            vertices=sum(m[3] for m in meshlets[level_first:])))
                clusters.append((*[min(q[a] for q in cgrid) for a in range(3)],
                                 *[max(q[a] for q in cgrid) for a in range(3)], first_level, len(levels) - first_level))
            parts.append((part["offset"], part["size"], part["texture"], part["alpha"], part["flags"], 0,
                          first_meshlet, len(meshlets) - first_meshlet, ulo[0], ulo[1], uscale[0], uscale[1]))
            part_lods.append((first_cluster, len(clusters) - first_cluster))
            if export_dir is not None:
                depth = max((len(ls) for ls in built), default=0)
                for k in range(depth):
                    lt = [t for ls in built for t in ls[min(k, len(ls) - 1)][1]]
                    err = max(ls[min(k, len(ls) - 1)][0] for ls in built) * scale
                    name = "%02x-%d-p%d-L%d.obj" % (owner, bin_no, part_index, k)
                    write_obj(Path(export_dir) / name, lt, welded,
                              ["owner %s bin %d part %d offset %d texture %d alpha %d flags %d" % (
                                  hex(owner), bin_no, part_index, part["offset"], part["texture"], part["alpha"],
                                  part["flags"]),
                               "level %d error_world<=%.1f (source mm) triangles %d" % (k, err, len(lt))])
                    exported.append(dict(owner=hex(owner), bin=bin_no, part=part_index, offset=part["offset"],
                                         texture=part["texture"], alpha=part["alpha"], flags=part["flags"],
                                         common=bool(common), level=k, error_world=round(err, 1),
                                         triangles=len(lt), obj=name))
            if trees and len(clusters) - first_cluster != len(cluster_tris):
                raise ValueError("%s:%d part %d: a tree cluster came out empty" % (hex(owner), bin_no, part_index))
            mesh_report.append(dict(card=card, clusters=len(clusters) - first_cluster, levels=part_levels,
                                    **(dict(trees=tree_rows) if trees else {})))
            groves += bool(trees)
        meshes.append((bin_no, int(common), owner, src["nvtx"], src["nparts"], src["flags"],
                       first_part, len(parts) - first_part, *lo, *step, *lo, *hi))
        code = classes.get((owner, bin_no))
        if code is None and class_auto:
            ext = [(hi[a] - lo[a]) * scale / 1000.0 for a in range(3)]
            code = MESH_CLASSES["tree"] if replaced or any(p["card"] for p in mesh_report) else auto_class(ext)
        mesh_classes.append(code or 0)
        report.append(dict(owner=owner, common=bool(common), bin=bin_no, scale=scale, bias=factor, parts=mesh_report,
                           mesh_class=code or 0))
    missing = set(k for k in substitutes if (k[0], k[1]) in {(e[0], e[2]) for e in entries}) - used_substitutes
    if missing:
        raise ValueError("substitutes for missing parts: %s" % sorted(missing))
    missing = set(k for k in replacements if k[0] in {e[0] for e in entries}) - used_replacements
    if missing:
        raise ValueError("replacements for missing BINs: %s" % sorted(missing))
    if export_dir is not None:
        (Path(export_dir) / "parts.json").write_text(json.dumps(dict(
            space="BIN model space (source positions after the position shift); vt = source UV; GX front-face winding",
            parts=exported), indent=1))
    body = bytearray()
    offsets = {}
    head = HEADER.size + LOD_HEADER.size
    for name, blob in (("mesh", b"".join(MESH.pack(*m) for m in meshes)),
                       ("part", b"".join(PART.pack(*p) for p in parts)),
                       ("meshlet", b"".join(MESHLET.pack(*m) for m in meshlets)),
                       ("vertex", b"".join(VERTEX.pack(*v[:5], v[5] & 0xFFF if color_mode == "oct-vertex" else v[5])
                                           for v in vertices)),
                       ("index", bytes(index_bytes)),
                       ("palette", b"".join(struct.pack("<I", c) for c in palette)),
                       ("vcolor", b"".join(struct.pack("<I", v[5] >> 12) for v in vertices)
                        if color_mode == "oct-vertex" else b""),
                       ("part_lod", b"".join(PART_LOD.pack(*p) for p in part_lods)),
                       ("cluster", b"".join(CLUSTER.pack(*c) for c in clusters)),
                       ("level", b"".join(LEVEL.pack(*l) for l in levels)),
                       ("class", bytes(mesh_classes) if classes or class_auto else b""),
                       ("rule", b"".join(CLASS_RULE.pack(*class_rules.get(c, (0, 0))) for c in range(CLASS_RULES))
                        if class_rules else b"")):
        if not blob and name in ("class", "rule", "vcolor"):
            continue
        start = align(head + len(body)) - head
        body.extend(b"\0" * (start - len(body)))
        offsets[name] = head + len(body)
        body.extend(blob)
    body.extend(b"\0" * (align(head + len(body)) - head - len(body)))
    lod = LOD_HEADER.pack(len(clusters), len(levels), offsets["part_lod"], offsets["cluster"], offsets["level"],
                          offsets.get("class", 0), offsets.get("rule", 0), 0)
    body = lod + bytes(body)
    total = HEADER.size + len(body)
    header = HEADER.pack(MAGIC, VERSION_SHARE if shared_vertices[1] else VERSION_LOD, total, zlib.crc32(body),
                         len(meshes), len(parts), len(meshlets), len(vertices), len(index_bytes), len(palette),
                         offsets["mesh"], offsets["part"], offsets["meshlet"], offsets["vertex"],
                         offsets["index"], offsets["palette"],
                         {"prelit": COLOR_ARGB1555, "oct-vertex": COLOR_OCT_VERTEX}.get(color_mode, COLOR_OCT_NORMAL),
                         offsets.get("vcolor", 0), 0, 0)
    blob = header + body
    summary = dict(package_bytes=total, meshes=len(meshes), parts=len(parts), meshlets=len(meshlets),
                   vertices=len(vertices), strip_bytes=len(index_bytes), palette=len(palette),
                   clusters=len(clusters), levels=len(levels), substituted_parts=len(used_substitutes),
                   replaced_bins=len(used_replacements), floor_triangles=floored, decimated_triangles=decimated, shared_vertices=shared_vertices,
                   version=VERSION_SHARE if shared_vertices[1] else VERSION_LOD,
                   mesh_classes={name: [r["bin"] for r in report if r["mesh_class"] == code]
                                 for name, code in MESH_CLASSES.items()} if classes or class_auto else None,
                   class_rules={name: class_rules[code] for name, code in MESH_CLASSES.items() if code in class_rules}
                   if class_rules else None,
                   level0_triangles=sum(lv["triangles"] for r in report for p in r["parts"] for lv in p["levels"]
                                        if lv["level"] == 0),
                   meshes_detail=report)
    if cluster_trees:
        summary["grove_parts"] = groves
    return blob, summary


# ---- Any room (--smd) --------------------------------------------------------
class _Blob:
    """A BIN held in memory, read like a NNNN.BIN path."""
    def __init__(self, data, name):
        self.data, self.name = data, name

    def read_bytes(self):
        return self.data

    def __str__(self):
        return self.name


def _room_smd():
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    import room_smd
    return room_smd


def smd_entries(source, owner):
    """Room SMD (room_smd.load_smd: .das, decoded tagged archive or SMD) ->
    dict(entries for convert()/convert_lod(), scales {bin: largest placement
    |scale|}, kept {bin: reason}). Only render-qualified BINs (single node,
    rigid, no shape table: the model bridge's static_geometry test) become
    meshes; the others keep the source GX path."""
    room_smd = _room_smd()
    smd, e = room_smd.load_smd(source)
    if e != ">":
        raise ValueError("%s: --smd needs source byte order (.das, decoded archive or source SMD)" % source)
    s = room_smd.Smd(smd, e)
    entries, kept = [], {}
    for b, data in sorted(s.bins().items()):
        why = room_smd.releasable(data, e)
        if why in room_smd.RENDER_UNQUALIFIED:
            kept[b] = why
            continue
        entries.append((owner, False, b, _Blob(data, "%s:BIN%d" % (source, b))))
    scales = {int(k.split(":")[1]): v for k, v in s.scales(owner).items()}
    return dict(entries=entries, scales=scales, kept=kept)


def release_identities(entries, summary):
    """BINs whose every source part is in the package and whose room-archive
    copy may drop its GX render payload (room_smd.py release), with the source
    identity that step checks before it replaces a BIN by its stub."""
    room_smd = _room_smd()
    packaged = {(r["owner"], r["bin"]) for r in summary["meshes_detail"]}
    out = []
    for owner, common, b, path in entries:
        if common or (owner, b) not in packaged:
            continue
        data = path.read_bytes()
        if room_smd.releasable(data, ">"):
            continue
        lay = room_smd.bin_layout(data, ">")
        heads = room_smd.part_headers(data, ">", lay)
        out.append(dict(bin=b, vertices=lay["nv"], parts=lay["nd"], part_offsets=[o for o, _ in heads],
                        part_sizes=[z for _, z in heads], source_bytes=len(data),
                        resident_bytes=len(room_smd.release_bin(data, ">"))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path)
    ap.add_argument("--owner", type=lambda s: int(s, 0), required=True,
                    help="0xff main scenario, 0xfe common, otherwise source block number")
    ap.add_argument("--bins", type=Path, help="directory of NNNN.BIN files")
    ap.add_argument("--smd", type=Path, metavar="ROOM",
                    help="any room: its local BINs from the SMD of a room .das, decoded tagged archive or SMD "
                         "(tools/room_smd.py), placement scales included; the summary's \"release\" lists the "
                         "BINs whose GX payload the room archive may drop (room_smd.py release)")
    ap.add_argument("--common", action="store_true", help="BINs are the room's common (shared) set")
    ap.add_argument("--color-policy", choices=["vertex"], default="vertex")
    ap.add_argument("--color-scale", type=float, default=1.0)
    ap.add_argument("--color", dest="color_mode", choices=["oct", "prelit", "oct-vertex"], default="oct",
                    help="--lod colour slots: oct (palette of at most 16 CLR0 values + normal, lit at runtime), "
                         "prelit (CLR0 as ARGB1555, no palette limit, never lit; the PS2 world's encoding) or "
                         "oct-vertex (oct normal + each vertex's CLR0 in a side table: lit at runtime like oct, any "
                         "number of colours; game SCENERY_ENCODING=1)")
    ap.add_argument("--cell", type=float, default=0.0,
                    help="spatial meshlet cell in model units (source mm); 0 keeps source strip order")
    ap.add_argument("--min-fill", type=int, default=64,
                    help="corners a spatial meshlet holds before the cell extent may close it")
    ap.add_argument("--lod", action="store_true",
                    help="write R4IM v2: spatial clusters with QEM / card-thinning levels of detail")
    ap.add_argument("--lod-px", type=float, default=2.0,
                    help="pixel tolerance the card-thinning distances assume (match MESH_LOD_PX)")
    ap.add_argument("--lod-eps", default=",".join("%g" % e for e in DEFAULT_EPS),
                    help="QEM level error targets in world units (source mm)")
    ap.add_argument("--lod-cluster", type=float, default=20000.0,
                    help="largest world extent of an independently selected cluster (k-d split of large parts)")
    ap.add_argument("--lod-cluster-tris", type=int, default=768, help="largest triangle count of a cluster")
    ap.add_argument("--lod-min-gain", type=float, default=0.5,
                    help="a level is kept only with at most this fraction of the previous level's triangles")
    ap.add_argument("--lod-max-levels", type=int, default=5)
    ap.add_argument("--scales", type=Path,
                    help='JSON {"<owner>:<bin>": world scale}; the largest placement scale of each BIN')
    ap.add_argument("--lod-substitute", type=Path, action="append", metavar="MANIFEST.json|DIR",
                    help="external geometry in BIN model space, repeatable: a manifest's per-part levels "
                         "(load_substitutes) and whole-BIN replacements (load_replacements), or a directory "
                         "of <OWNER>_<bin>.obj replacements")
    ap.add_argument("--lod-export", type=Path, metavar="DIR",
                    help="also write every part's levels as OBJ plus parts.json (templates for --lod-substitute)")
    ap.add_argument("--lod-share", action="store_true",
                    help="coarse levels reuse the part's vertices through u16 tables (R4IM v3; needs a runtime "
                         "that adopts v3)")
    ap.add_argument("--lod-floor", action="append", default=[], metavar="[OWNER:BINS=]MM",
                    help="level 0 is the source simplified to this world error (source units), before "
                         "clustering; bare MM applies to every BIN, OWNER:BINS=MM overrides; repeatable")
    ap.add_argument("--class", dest="mesh_class", action="append", default=[], metavar="OWNER:BINS=CLASS",
                    help="scenery class tag for a runtime distance rule (%s); repeatable" % "|".join(MESH_CLASSES))
    ap.add_argument("--class-auto", action="store_true",
                    help="tag BINs --class leaves untagged: tree (card field / replaced BIN), ground, clutter or "
                         "structure from world extent (auto_class)")
    ap.add_argument("--class-rule", action="append", default=[], metavar="CLASS=FULL_M,CULL_M",
                    help="this room's distances for a class (metres; 0 = runtime default); repeatable")
    ap.add_argument("--lod-cluster-trees", action="append", default=[], metavar="OWNER:BINS",
                    help="grove BINs (e.g. 0xff:17,38): clusters are formed per tree (connected components "
                         "joined to the nearest trunk taller than 3 m), so each tree can draw as its own "
                         "impostor; a BIN with fewer than two trunks is unchanged; repeatable")
    ap.add_argument("--lod-cluster-bins", action="append", default=[], metavar="OWNER:BINS=MM",
                    help="cluster size (world mm, as --lod-cluster) for these BINs only (e.g. 0xff:59=8000: a "
                         "7 m tree splits into ~500-triangle regions that pick their levels separately); "
                         "repeatable")
    ap.add_argument("--lod-bias", action="append", default=[], metavar="OWNER:BINS=FACTOR",
                    help="multiply the stored level errors of these BINs (e.g. 0xfe:0-10=0.375: the common "
                         "trees switch at 8 px when MESH_LOD_PX=3); repeatable")
    a = ap.parse_args()
    if (a.bins is None) == (a.smd is None):
        ap.error("give exactly one of --bins and --smd")
    room = smd_entries(a.smd, a.owner) if a.smd else None
    entries = room["entries"] if room else [(a.owner, a.common, int(p.stem), p) for p in sorted(a.bins.glob("*.BIN"))]
    if a.lod:
        scales = {(a.owner, b): s for b, s in room["scales"].items()} if room else {}
        if a.scales:
            for k, v in json.loads(a.scales.read_text()).items():
                o, b = k.split(":")
                scales[(int(o, 0), int(b))] = float(v)
        bias = {}
        for spec in a.lod_bias:
            key, factor = spec.split("=")
            o, bins = key.split(":")
            for r in bins.split(","):
                lo_bin, _, hi_bin = r.partition("-")
                for b in range(int(lo_bin), int(hi_bin or lo_bin) + 1):
                    bias[(int(o, 0), b)] = float(factor)
        floor = {}
        for spec in a.lod_floor:
            if "=" not in spec:
                floor[None] = float(spec)
                continue
            key, value = spec.split("=")
            o, bins = key.split(":")
            for r in bins.split(","):
                lo_bin, _, hi_bin = r.partition("-")
                for b in range(int(lo_bin), int(hi_bin or lo_bin) + 1):
                    floor[(int(o, 0), b)] = float(value)
        classes = {}
        for spec in a.mesh_class:
            key, name = spec.split("=")
            o, bins = key.split(":")
            for r in bins.split(","):
                lo_bin, _, hi_bin = r.partition("-")
                for b in range(int(lo_bin), int(hi_bin or lo_bin) + 1):
                    classes[(int(o, 0), b)] = MESH_CLASSES[name]
        class_rules = {}
        for spec in a.class_rule:
            name, value = spec.split("=")
            full, cull = (float(x) for x in value.split(","))
            class_rules[MESH_CLASSES[name]] = (round(full * 10), round(cull * 10))
        eps = tuple(float(x) for x in a.lod_eps.split(","))
        cluster_trees = set()
        for spec in a.lod_cluster_trees:
            o, bins = spec.split(":")
            for r in bins.split(","):
                lo_bin, _, hi_bin = r.partition("-")
                cluster_trees.update((int(o, 0), b) for b in range(int(lo_bin), int(hi_bin or lo_bin) + 1))
        cluster_bins = {}
        for spec in a.lod_cluster_bins:
            key, mm = spec.split("=")
            o, bins = key.split(":")
            for r in bins.split(","):
                lo_bin, _, hi_bin = r.partition("-")
                for b in range(int(lo_bin), int(hi_bin or lo_bin) + 1):
                    cluster_bins[(int(o, 0), b)] = float(mm)
        substitutes, replacements = {}, {}
        for source in a.lod_substitute or []:
            for table, new in ((substitutes, load_substitutes(source)), (replacements, load_replacements(source))):
                twice = set(table) & set(new)
                if twice:
                    raise ValueError("%s: given twice: %s" % (source, sorted(twice)))
                table.update(new)
        if a.lod_export:
            a.lod_export.mkdir(parents=True, exist_ok=True)
        blob, summary = convert_lod(entries, a.color_scale, scales, a.lod_px, eps, a.lod_cluster, a.lod_cluster_tris,
                                    min_gain=a.lod_min_gain, max_levels=a.lod_max_levels, bias=bias,
                                    substitutes=substitutes, export_dir=a.lod_export, replacements=replacements,
                                    floor=floor, share=a.lod_share, classes=classes, class_auto=a.class_auto,
                                    class_rules=class_rules, cluster_trees=cluster_trees, cluster_bins=cluster_bins,
                                    color_mode=a.color_mode)
        version = summary["version"]
    else:
        blob, summary = convert(entries, a.color_scale, a.cell, a.min_fill)
        version = VERSION
    a.out.write_bytes(blob)
    summary.update(format="R4IM", version=version, color_policy=a.color_policy, color_scale=a.color_scale,
                   cell=a.cell, min_fill=a.min_fill,
                   sha256=hashlib.sha256(blob).hexdigest(),
                   meaning="instanced native prelit meshes; colour is authored CLR0 times color_scale (placeholder)")
    if room:
        summary.update(smd=str(a.smd), gx_kept=room["kept"], release=release_identities(entries, summary))
    if a.lod:
        summary.update(lod_px=a.lod_px, lod_eps=a.lod_eps, lod_cluster=a.lod_cluster, lod_cluster_tris=a.lod_cluster_tris,
                       lod_min_gain=a.lod_min_gain, lod_max_levels=a.lod_max_levels, lod_bias=a.lod_bias,
                       lod_floor=a.lod_floor, lod_share=a.lod_share, mesh_class=a.mesh_class,
                       class_auto=a.class_auto, class_rule=a.class_rule,
                       lod_substitute=[str(p) for p in a.lod_substitute] if a.lod_substitute else None)
        if a.lod_cluster_trees:
            summary.update(lod_cluster_trees=a.lod_cluster_trees)
        if a.lod_cluster_bins:
            summary.update(lod_cluster_bins=a.lod_cluster_bins)
    Path(str(a.out) + ".json").write_text(json.dumps(summary, indent=1))
    detail = summary.pop("meshes_detail")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

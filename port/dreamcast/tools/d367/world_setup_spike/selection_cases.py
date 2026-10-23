#!/usr/bin/env python3
"""Deterministic, source-free R4IM v2/v3 fixtures for real world selection.

Every generated mesh is adopted by production MeshPackage::adopt before a test
can invoke either selector. Group data describes the same count-prefixed strips
and raw bounds. The fixtures are synthetic controls, not a recorded game view.
"""
import hashlib
import json
from pathlib import Path
import struct

INPUT_FORMAT = "<10I31f"
INPUT_BYTES = struct.calcsize(INPUT_FORMAT)


def triangle(x=100, y=100, z=100):
    return [(x, y, z), (x + 8, y, z), (x, y + 8, z)]


def meshlet(groups=None):
    groups = groups or [triangle()]
    vertices, strips, records = [], bytearray(), []
    for xyz in groups:
        first = len(vertices)
        vertices.extend(xyz)
        strips += bytes([len(xyz), *range(first, len(vertices))])
        lo = [min(v[a] for v in xyz) for a in range(3)]
        hi = [max(v[a] for v in xyz) for a in range(3)]
        records.append((*lo, *hi, len(strips), first | ((len(vertices) - 1) << 8)))
    return dict(vertices=vertices, strips=bytes(strips), groups=records,
                lo=[min(v[a] for v in vertices) for a in range(3)],
                hi=[max(v[a] for v in vertices) for a in range(3)])


def package(parts, groups=4, indexed=False):
    """parts -> clusters -> levels(error, list[meshlet]), a validated v2/v3."""
    meshlets, vertices, strips, group_records = [], [], bytearray(), bytearray()
    part_records, part_lods, clusters, levels = [], [], [], []
    for source_part, part in enumerate(parts):
        part_first, cluster_first = len(meshlets), len(clusters)
        for cluster in part:
            level_first = len(levels)
            xyz = []
            for error, lets in cluster:
                first = len(meshlets)
                for let in lets:
                    xyz.extend(let["vertices"])
                    fv, fs = len(vertices), len(strips)
                    vertices.extend(let["vertices"])
                    if indexed:
                        if len(strips) & 1:
                            strips += b"\0"
                        fs = len(strips)
                        strips += struct.pack("<%dH" % len(let["vertices"]), *range(len(let["vertices"])))
                    strips += let["strips"]
                    meshlets.append((fv, fs, len(let["strips"]), len(let["vertices"]),
                                     len(let["groups"]) | (0x8000 if indexed else 0), *let["lo"], *let["hi"]))
                    assert len(let["groups"]) <= groups
                    for row in let["groups"]:
                        group_records += struct.pack("<8H", *row)
                    end = len(let["strips"])
                    for _ in range(groups - len(let["groups"])):
                        group_records += struct.pack("<8H", 0, 0, 0, 0, 0, 0, end, 0)
                levels.append((first, len(lets), error))
            lo = [min(v[a] for v in xyz) if xyz else 0 for a in range(3)]
            hi = [max(v[a] for v in xyz) if xyz else 0 for a in range(3)]
            clusters.append((*lo, *hi, level_first, len(cluster)))
        part_records.append((source_part * 32, 32, 0, 0, 0, 0, part_first,
                             len(meshlets) - part_first, .125, .25, 1 / 32768, 1 / 16384))
        part_lods.append((cluster_first, len(clusters) - cluster_first))
    body = bytearray(112)

    def section(data):
        body.extend(b"\0" * (-len(body) % 4))
        at = len(body)
        body.extend(data)
        return at

    all_xyz = vertices or [(0, 0, 0)]
    lo = [min(v[a] for v in all_xyz) for a in range(3)]
    hi = [max(v[a] for v in all_xyz) for a in range(3)]
    meshes = section(struct.pack("<HBBHHIII12f", 1, 0, 0, len(vertices), len(parts), 0, 0,
                                 len(parts), 0, 0, 0, 1, 1, 1, *lo, *hi))
    part_at = section(b"".join(struct.pack("<2I4B2I4f", *p) for p in part_records))
    let_at = section(b"".join(struct.pack("<3I8H", *l) for l in meshlets))
    vertex_at = section(b"".join(struct.pack("<6H", *v, 0, 0, 0xffff) for v in vertices))
    strip_at = section(strips)
    palette_at = section(struct.pack("<I", 0xffffffff))
    part_lod_at = section(b"".join(struct.pack("<2I", *p) for p in part_lods))
    cluster_at = section(b"".join(struct.pack("<6H2I", *c) for c in clusters))
    level_at = section(b"".join(struct.pack("<2If", *l) for l in levels))
    struct.pack_into("<4s19I", body, 0, b"R4IM", 3 if indexed else 2, len(body), 0,
                     1, len(parts), len(meshlets), len(vertices), len(strips), 1,
                     meshes, part_at, let_at, vertex_at, strip_at, palette_at, 2, 0, 0, 0)
    struct.pack_into("<8I", body, 80, len(clusters), len(levels), part_lod_at, cluster_at, level_at, 0, 0, 0)
    cones = bytearray()
    for _ in range(len(meshlets) * groups):
        # Deliberately narrow +Z cone. Geometry fixtures all lie on parallel
        # planes. Runtime cone data is optional; selectors must agree either way.
        cones += struct.pack("<3bBf", 0, 0, 127, 1, 32.0)
    return bytes(body), bytes(group_records), bytes(cones)


def defaults():
    return dict(part_index=0, cull=0, inside=0, use_abs=1, groups=4, use_groups=1,
                cone_on=0, marked=0, pass_=0, sky=0,
                near=1., far=1000., cull_far=1000., lod_scale=1.,
                mvq=[.1, 0, 0, -10, 0, .1, 0, -10, 0, 0, -.1, -20],
                projection=[0, 1, 0, 1, 0, -1 / 999, -1000 / 999],
                viewport=[0, 0, 640, 480, 0, 1], uv_offset=[0, 0])


def input_bytes(config):
    fields = ("part_index", "cull", "inside", "use_abs", "groups", "use_groups", "cone_on", "marked", "pass_", "sky")
    values = [config[k] for k in fields]
    values += [config[k] for k in ("near", "far", "cull_far", "lod_scale")]
    for k in ("mvq", "projection", "viewport", "uv_offset"):
        values += config[k]
    return struct.pack(INPUT_FORMAT, *values)


def cases():
    output = []

    def add(name, parts, expected=None, indexed=False, **changes):
        config = defaults()
        config.update(changes)
        pkg, groups, cone = package(parts, config["groups"], indexed)
        output.append(dict(name=name, config=config, package=pkg, groups=groups, cones=cone,
                           expected=expected))

    one = [[[ (0., [meshlet()]) ]]]
    add("empty-part", [[]], expected=[])
    add("zero-meshlet-level", [[[(0., [])]]], expected=[])
    add("whole-inside", one, expected=[[0, 255, 0, 0, 0]], inside=1)
    add("whole-tested", one, expected=[[0, 255, 0, 0, 0]])
    add("no-group-table", one, expected=[[0, 255, 0, 0, 0]], use_groups=0)
    add("scalar-box-fallback", one, expected=[[0, 255, 0, 0, 0]], use_abs=0)
    add("indexed-v3", one, expected=[[0, 255, 0, 0, 0]], indexed=True)
    for label, axis, distance in (("left", 3, -1000), ("right", 3, 1000),
                                  ("bottom", 7, -1000), ("top", 7, 1000),
                                  ("behind-near", 11, 1000), ("beyond-far", 11, -2000)):
        matrix = defaults()["mvq"]
        matrix[axis] = distance
        add("cluster-" + label, one, expected=[], mvq=matrix)
    separated = meshlet([triangle(0, 50, 0), triangle(100, 50, 0), triangle(300, 50, 0), triangle(450, 50, 0)])
    add("partial-groups", [[[(0., [separated])]]])
    all_outside = meshlet([triangle(0, 50, 0), triangle(600, 50, 0)])
    matrix = defaults()["mvq"];matrix[3] = -30;matrix[11] = -10
    add("zero-retained-groups-pick", [[[(0., [all_outside])]]], mvq=matrix)
    near = meshlet([triangle(100, 100, 0), triangle(100, 100, 50)])
    matrix = defaults()["mvq"];matrix[11] = 0
    add("near-group-split", [[[(0., [near])]]], mvq=matrix, near=2)
    mixed = [[[(0., [meshlet([triangle(100, 100, 100)])])],
              [(0., [meshlet([triangle(60000, 100, 100)])])]]]
    add("cluster-mix", mixed)
    levels = [[[(0., [meshlet(), meshlet()]), (1., [meshlet()]), (20., [meshlet()])]]]
    for scale in (0., 2., 100.):
        add("lod-scale-%g" % scale, levels, lod_scale=scale)
    nonempty = [[[(0., [meshlet()]), (1., []), (10., [])]]]
    add("empty-coarse-lod", nonempty)
    add("many-meshlets", [[[(0., [meshlet() for _ in range(320)])]]], inside=1)
    add("repeated-plane-cache", [[[(0., [separated for _ in range(6)])]]])
    add("second-part", [[], *one], part_index=1)
    for cull in (0, 1, 2):
        add("cone-winding-%d" % cull, one, cull=cull, cone_on=1)
        add("marked-uv-cull-%d" % cull, one, cull=cull, marked=1, uv_offset=[.125, -.25], sky=1, pass_=2)
    for sign in (-1, 0, 1):
        matrix = defaults()["mvq"];matrix[0] *= sign
        add("cone-determinant-%d" % sign, one, mvq=matrix, cull=1, cone_on=1)
    for sign in (-1, 1):
        matrix = [.08 * sign, .015, -.025, -9, -.01, .09, .03, -11, .02, -.03, -.1, -25]
        add("sheared-reflection-%d" % sign, one, mvq=matrix, cull=2, cone_on=1)
    # Boundary-adjacent cameras keep numeric decisions authoritative in the
    # production bodies; host and target each compare the two contexts locally.
    for step in range(-8, 9):
        matrix = defaults()["mvq"];matrix[3] = 10 + step / 1024
        add("screen-boundary-%+d" % step, one, mvq=matrix)
    return output


def write_case(case, path):
    chunks = (case["package"], case["groups"], case["cones"])
    data = struct.pack("<5I", 0x31505357, INPUT_BYTES, *(len(x) for x in chunks))
    data += input_bytes(case["config"]) + b"".join(chunks)
    Path(path).write_bytes(data)
    return dict(name=case["name"], file=Path(path).name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                expected=case["expected"], config=case["config"])


def write_cases(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    records = [write_case(c, directory / (c["name"] + ".bin")) for c in cases()]
    (directory / "cases.json").write_text(json.dumps(records, indent=2) + "\n")
    return records

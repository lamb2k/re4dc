#!/usr/bin/env python3
"""Build proof-bearing PCL2 cells from immutable, opaque PS2 world walls.

Disabled unless --barn-portals29=1. Unlike build_cell.py this does no ray
sampling: every unproved part of an axis-aligned house face is an aperture.
The exact rational complement includes small cracks and all unsupported walls.
The runtime must verify the witness parts were submitted in the current view.
"""
import argparse
from collections import Counter
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cell_file

SCHEMA = "re4dc.world-portal29/1"
MARKER = int.from_bytes(b"WP29", "little")
MAX_WITNESSES = 256
MAX_POLYGONS = 20000


def require(ok, message):
    if not ok:
        raise ValueError(message)


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rational(value):
    require(type(value) in (int, float) and math.isfinite(value), "finite numeric coordinate required")
    return Q(value)


def f32(value):
    try:
        result = struct.unpack("<f", struct.pack("<f", float(value)))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError("float32 coordinate overflow") from exc
    require(math.isfinite(result), "finite float32 coordinate required")
    return result


def outward(value, high):
    """One directed rounding to a finite float32, including negative values."""
    value = Q(value)
    result = f32(value)
    if (Q(result) < value if high else Q(result) > value):
        bits = struct.unpack("<I", struct.pack("<f", result))[0]
        if result == 0:
            bits = 1 if high else 0x80000001
        else:
            bits += 1 if ((result > 0) == high) else -1
        result = struct.unpack("<f", struct.pack("<I", bits))[0]
    require(math.isfinite(result), "outward float32 coordinate overflow")
    return result


def cross(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def area(poly):
    return sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1]))


def clean(poly):
    result = []
    for p in poly:
        if not result or p != result[-1]:
            result.append(p)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    if len(result) < 3 or not area(result):
        return []
    return result if area(result) > 0 else list(reversed(result))


def halfplane(poly, a, b, inside=True):
    """Exact Sutherland-Hodgman clipping; retain the boundary on both sides."""
    result = []
    if not poly:
        return result
    for p, q in zip(poly, poly[1:] + poly[:1]):
        sp, sq = cross(a, b, p), cross(a, b, q)
        pin = sp >= 0 if inside else sp <= 0
        qin = sq >= 0 if inside else sq <= 0
        if pin:
            result.append(p)
        if pin != qin:
            t = sp / (sp - sq)
            result.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return clean(result)


def intersection(poly, cover):
    for a, b in zip(cover, cover[1:] + cover[:1]):
        poly = halfplane(poly, a, b)
        if not poly:
            break
    return poly


def subtract(poly, cover):
    """A disjoint convex partition of poly outside the convex CCW cover."""
    outside = []
    for a, b in zip(cover, cover[1:] + cover[:1]):
        fragment = halfplane(poly, a, b, False)
        if fragment:
            outside.append(fragment)
        poly = halfplane(poly, a, b)
        if not poly:
            break
    return outside


def subtract_all(polys, covers):
    for cover in covers:
        polys = [piece for poly in polys for piece in subtract(poly, cover)]
        require(len(polys) <= MAX_POLYGONS, "polygon budget exceeded; split authored house hull")
        if not polys:
            break
    return polys


def disjoint(polys):
    result = []
    for poly in polys:
        result.extend(subtract_all([poly], result))
        require(len(result) <= MAX_POLYGONS, "polygon budget exceeded; split authored house hull")
    return result


def rectangle(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def box(value, label):
    require(isinstance(value, list) and len(value) == 2 and all(isinstance(v, list) and len(v) == 3 for v in value),
            label + " must be [lo_xyz, hi_xyz]")
    lo, hi = [[rational(v) for v in row] for row in value]
    require(all(a < b for a, b in zip(lo, hi)), label + " has empty/reversed extent")
    # Keeping hull planes exactly representable avoids shifting a closed wall to
    # a different plane when PCL2 stores it. Unknown planes must be authored anew.
    require(all(Q(f32(v)) == v for v in lo + hi), label + " coordinates must be exactly float32 representable")
    return lo, hi


def codec():
    path = HERE.parents[1] / "world_blender_roundtrip" / "package.py"
    spec = importlib.util.spec_from_file_location("portal29_world_codec", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_path(root, entry, key):
    require(isinstance(entry.get(key), str) and entry[key], "missing package " + key)
    relative = Path(entry[key])
    require(not relative.is_absolute() and ".." not in relative.parts, "package paths must remain within --package")
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), "package path escapes --package")
    data = path.read_bytes()
    require(sha(data) == entry.get(key + "_sha256"), key + " sha256 mismatch")
    return data


def load_package(config, directory):
    require(config.get("schema") == SCHEMA, "unsupported config schema")
    room = config.get("room")
    room = int(room, 0) if isinstance(room, str) else room
    require(type(room) is int and 0 <= room <= 0xfff, "room must be an explicit 0x000..0xfff identity")
    entry = config.get("package", {})
    root = Path(directory)
    mesh, policy, ids = [checked_path(root, entry, k) for k in ("mesh", "policy", "ids")]
    module = codec()
    doc = module.decode(mesh, policy, preserve_index_layout=True)
    mh = struct.unpack_from("<4s19I", mesh)
    ph = struct.unpack_from("<4s7I", policy)
    require(len(ids) >= 16, "short R4ID")
    magic, version, count, source_crc = struct.unpack_from("<4s3I", ids)
    require(magic == b"R4ID" and version == 1 and count == len(doc["placements"])
            and len(ids) in (16 + count, (16 + count + 31) & ~31)
            and not any(ids[16 + count:]), "R4ID identity/count/size")
    # Remapped policies have a distinct physical CRC. The approved source CRC
    # must be explicitly supplied and verified against the package certificate;
    # do not turn an arbitrary config integer into identity evidence.
    allowed_crc = ph[5]
    if source_crc != allowed_crc:
        import re
        cert_root = HERE.parents[1] / "texture_rect21"
        accepted = False
        for filename in ("provenance_certificates.inc", "provenance_certificates_n256.inc"):
            for raw in re.findall(r"\{([^{}]+)\}", (cert_root / filename).read_text()):
                words = raw.split(",")
                if len(words) != 10:
                    continue
                try:
                    w = [int(x.strip().rstrip("Uu"), 0) for x in words]
                except ValueError:
                    continue
                if w[:6] == [room, len(policy), ph[2], ph[3], ph[4], ph[5]] and w[7:] == [mh[3], len(mesh), source_crc]:
                    accepted = True
        require(accepted, "R4ID source CRC is not the physical policy or an exact approved package remap")
    values = ids[16:16 + count]
    counts = Counter(values)
    # Mirror dyn::slot_of construction and the draw-time pl.placement lookup,
    # not the R4PW array index. Repeated IDs intentionally retain baked drawing;
    # only count==1 IDs below dyn::kIds receive a source-object slot.
    dynamic = {i for i, placement in enumerate(doc["placements"])
               if placement[1] >= count or (values[placement[1]] < 250 and counts[values[placement[1]]] == 1)}
    return doc, module, dict(room=room, mesh_crc=mh[3], policy_crc=ph[5], mesh_bytes=len(mesh),
                            mesh_sha256=sha(mesh), policy_sha256=sha(policy), ids_sha256=sha(ids)), dynamic


def world_vertex(mesh, placement, vertex):
    local = [Q(mesh[8 + a]) + Q(mesh[11 + a]) * vertex[a] for a in range(3)]
    affine = placement[2:]
    result = [Q(affine[4 * r + 3]) + sum(Q(affine[4 * r + c]) * local[c] for c in range(3)) for r in range(3)]
    # A generous analytic allowance for the float32 affine/grid evaluation;
    # portals are expanded by >=64 mm. Refuse huge/ill-conditioned transforms.
    bound = max(abs(Q(affine[4 * r + 3])) + sum(abs(Q(affine[4 * r + c]) * local[c]) for c in range(3))
                for r in range(3))
    require(bound < 2**20, "world affine magnitude exceeds the 64 mm rounding guard")
    return result


def cluster_levels(doc, module, placement_index, part_index, cluster_index):
    placement = doc["placements"][placement_index]
    mesh = doc["meshes"][placement[0]]
    cl = doc["clusters"][cluster_index]
    levels = []
    for level in doc["levels"][cl[6]:cl[6] + cl[7]]:
        triangles = []
        for ji in range(level[0], level[0] + level[1]):
            vertices = [world_vertex(mesh, placement, doc["vertices"][vi]) for vi in module.local_vertices(doc, ji)]
            for tri in module.triangles(doc, ji):
                triangles.append([vertices[k] for k in tri])
        levels.append(triangles)
    return levels


def projected(tri, axis, plane, sign, cull):
    if any(v[axis] != plane for v in tri):
        return []
    u, v = (axis + 1) % 3, (axis + 2) % 3
    poly = [(point[u], point[v]) for point in tri]
    winding = area(poly)
    if not winding or (cull == 2 and winding * sign <= 0):
        return []
    return clean(poly)


def merge_rectangles(rects):
    """Safe overestimate, retaining narrow slits unless rectangles intersect."""
    result = list(dict.fromkeys(rects))
    again = True
    while again:
        again = False
        for i, a in enumerate(result):
            for j in range(i + 1, len(result)):
                b = result[j]
                if a[0] == b[0] and a[1] == b[1] and a[2] <= b[3] and b[2] <= a[3] and a[4] <= b[5] and b[4] <= a[5]:
                    result[i] = (a[0], a[1], min(a[2], b[2]), max(a[3], b[3]), min(a[4], b[4]), max(a[5], b[5]))
                    result.pop(j)
                    again = True
                    break
            if again:
                break
    return result


def make_house(doc, module, dynamic, cfg, near, margin):
    lo, hi = box(cfg.get("hull"), "house hull")
    eye_boxes = cfg.get("eye_boxes")
    require(isinstance(eye_boxes, list) and 0 < len(eye_boxes) <= 4096, "house needs explicit eye boxes")
    eyes = [box(b, "eye box") for b in eye_boxes]
    for a, b in eyes:
        require(all(a[k] >= lo[k] + near + 64 and b[k] <= hi[k] - near - 64 for k in range(3)),
                "eye box must be inset >= near_max + 64 mm on every hull face")
    selected = cfg.get("placements", list(range(len(doc["placements"]))))
    require(isinstance(selected, list) and all(type(i) is int and 0 <= i < len(doc["placements"]) for i in selected),
            "invalid house placement selection")
    selected = sorted(set(selected) - dynamic)
    candidates = []
    skipped = Counter()
    for pi in selected:
        placement = doc["placements"][pi]
        mesh = doc["meshes"][placement[0]]
        for part in range(mesh[6], mesh[6] + mesh[7]):
            material = doc["materials"][part]
            if material[4] != 0 or material[5] not in (0, 2) or material[7]:
                skipped["nonopaque_or_unsupported_material"] += 1
                continue
            first, count = doc["part_lods"][part]
            for cluster in range(first, first + count):
                levels = cluster_levels(doc, module, pi, part, cluster)
                candidates.append((pi, part, material[5], levels))
    portals, witnesses, faces = [], set(), []
    for face in range(6):
        axis, high = face // 2, face & 1
        u, v = (axis + 1) % 3, (axis + 2) % 3
        plane, inward = (hi[axis], -1) if high else (lo[axis], 1)
        hull_face = rectangle(lo[u], hi[u], lo[v], hi[v])
        cover = []
        for pi, part, cull, levels in candidates:
            if not levels:
                continue  # no LOD evidence proves no coverage, never the whole face
            common = [hull_face]
            for triangles in levels:
                polies = [projected(t, axis, plane, inward, cull) for t in triangles]
                polies = [p for p in polies if p]
                common = disjoint([piece for p in common for t in polies if (piece := intersection(p, t))])
                if not common:
                    break
            if common:
                witnesses.add((pi, part))
                cover.extend(common)
        holes = subtract_all([hull_face], cover)
        face_portals = []
        for hole in holes:
            u0 = max(lo[u], min(p[0] for p in hole) - margin)
            u1 = min(hi[u], max(p[0] for p in hole) + margin)
            v0 = max(lo[v], min(p[1] for p in hole) - margin)
            v1 = min(hi[v], max(p[1] for p in hole) + margin)
            face_portals.append((axis, float(plane), outward(u0, False), outward(u1, True), outward(v0, False), outward(v1, True)))
        face_portals = merge_rectangles(face_portals)
        # Coarsening to a larger aperture only draws more. Bound runtime work
        # rather than rejecting a real house because it has many small cracks.
        if len(face_portals) > 4:
            face_portals = [(axis, float(plane), float(lo[u]), float(hi[u]), float(lo[v]), float(hi[v]))]
        portals.extend(face_portals)
        faces.append(dict(face=face, aperture_rectangles=len(face_portals), uncovered_area=float(sum(area(p) for p in holes) / 2),
                          face_area=float(area(hull_face) / 2)))
    require(len(portals) <= 24, "runtime portal budget")
    cells = [(list(map(float, a)), list(map(float, b)), 0, len(portals)) for a, b in eyes]
    return (list(map(float, lo + hi)), cells, portals), witnesses, dict(name=cfg.get("name", "house"), faces=faces,
        candidate_clusters=len(candidates), witnesses=len(witnesses), excluded_dynamic=len(set(cfg.get("placements", range(len(doc["placements"])))) & dynamic),
        skipped=dict(skipped))


def pack_proof(identity, near, houses, witnesses):
    ordered = sorted(witnesses)
    require(0 < len(ordered) <= MAX_WITNESSES, "need 1..256 successfully drawn witness parts")
    data = bytearray(cell_file.pack2(identity["room"], identity["mesh_crc"], identity["policy_crc"],
                                    identity["mesh_bytes"], near, houses))
    proof_offset = len(data)
    proof = b"".join(struct.pack("<II", *row) for row in ordered)
    data.extend(proof)
    struct.pack_into("<I", data, 28, len(data))
    struct.pack_into("<6I", data, 40, MARKER, proof_offset, len(ordered), 1, crc(proof), 0)
    struct.pack_into("<I", data, 60, crc(data))
    return bytes(data)


def verify_cell(data):
    """Tools-side structural/checksum check; runtime still verifies witnesses."""
    require(len(data) >= 64 and data[:4] == b"PCL2", "short/missing PCL2")
    w = struct.unpack_from("<16I", data)
    require(w[7] == len(data) and 0 < w[5] <= 4096 and w[6] <= 16384 and 0 < w[9] <= 64, "PCL2 size/count")
    require(w[10] == MARKER and w[13] == 1 and 0 < w[12] <= MAX_WITNESSES, "WP29 proof identity/count")
    expected = 64 + 32 * w[9] + 28 * w[5] + 24 * w[6]
    require(w[11] == expected and len(data) == expected + 8 * w[12], "WP29 proof extent")
    require(crc(data[expected:]) == w[14], "WP29 witness checksum")
    copy = bytearray(data)
    struct.pack_into("<I", copy, 60, 0)
    require(crc(copy) == w[15], "WP29 file checksum")
    near = struct.unpack_from("<f", data, 32)[0]
    require(math.isfinite(near) and near > 0, "PCL2 near margin")
    seen_cells = set()
    houses = []
    for i in range(w[9]):
        h = struct.unpack_from("<6f2HI", data, 64 + 32 * i)
        require(all(math.isfinite(v) for v in h[:6]) and all(h[a] < h[a + 3] for a in range(3))
                and h[7] and h[6] + h[7] <= w[5] and h[8] == 0, "PCL2 house")
        for ci in range(h[6], h[6] + h[7]):
            require(ci not in seen_cells, "PCL2 overlapping house cells")
            seen_cells.add(ci)
        houses.append(h)
    require(len(seen_cells) == w[5], "PCL2 unowned cells")
    cell_start = 64 + 32 * w[9]
    for h in houses:
        for i in range(h[6], h[6] + h[7]):
            c = struct.unpack_from("<6f2H", data, cell_start + 28 * i)
            require(all(math.isfinite(v) for v in c[:6]) and all(h[a] + near + 64 <= c[a] < c[a + 3] <= h[a + 3] - near - 64 for a in range(3))
                    and c[7] <= 24 and c[6] + c[7] <= w[6], "PCL2 cell")
    portal_start = cell_start + 28 * w[5]
    for i in range(w[6]):
        p = struct.unpack_from("<I5f", data, portal_start + 24 * i)
        require(p[0] <= 2 and all(math.isfinite(v) for v in p[1:]) and p[2] < p[3] and p[4] < p[5], "PCL2 portal")
    witnesses = [struct.unpack_from("<II", data, expected + i * 8) for i in range(w[12])]
    require(witnesses == sorted(set(witnesses)), "WP29 witnesses must be sorted and unique")
    return dict(room=w[1], mesh_crc=w[2], policy_crc=w[3], mesh_bytes=w[4], cells=w[5], portals=w[6],
                houses=w[9], witnesses=witnesses, bytes=len(data))


def build(config, package):
    doc, module, identity, dynamic = load_package(config, package)
    near, margin = rational(config.get("near_max")), rational(config.get("aperture_margin", 64))
    require(near > 0 and Q(f32(near)) == near and margin >= 64, "near_max must be positive float32; aperture_margin >=64 mm")
    house_cfgs = config.get("houses")
    require(isinstance(house_cfgs, list) and 0 < len(house_cfgs) <= 64, "need 1..64 houses")
    houses, witnesses, reports = [], set(), []
    for house in house_cfgs:
        result, proof, report = make_house(doc, module, dynamic, house, near, margin)
        houses.append(result)
        witnesses.update(proof)
        reports.append(report)
    require(sum(len(h[1]) for h in houses) <= 4096, "PCL2 cell budget")
    data = pack_proof(identity, float(near), houses, witnesses)
    summary = verify_cell(data)
    report = dict(schema=SCHEMA, identity=identity, config_sha256=sha(json.dumps(config, sort_keys=True).encode()),
                  cell_sha256=sha(data), summary=summary, near_max=float(near), aperture_margin=float(margin), houses=reports,
                  geometry_method="exact rational polygon complement; per-cluster intersection of all LOD coverages",
                  runtime_gate="every witness part successfully submitted in the same current draw view; otherwise draw all",
                  limitations=["R4IM v3 canonical/index-layout packages only; other layouts refused",
                               "Only exactly coplanar axis-aligned opaque stable walls prove closure; other area stays open",
                               "All walls use the current draw receipts; no sampled camera path is a visibility proof",
                               "Private package build, raster rounding/magenta walk, transitions, s30 and STRICT remain owner gates"])
    return data, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--barn-portals29", type=int, choices=(0, 1), default=0)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if not args.barn_portals29:
        print("barn-portals29=0: disabled; no input read and no candidate output written")
        return 0
    if any(v is None for v in (args.config, args.package, args.out, args.report)):
        parser.error("enabled builder requires --config, --package, --out and --report")
    try:
        config = json.loads(args.config.read_text())
        data, report = build(config, args.package)
        require(args.out.resolve() != args.report.resolve(), "cell and report destinations must differ")
        require(not args.out.exists() and not args.report.exists(), "outputs already exist; use a fresh candidate directory")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(data)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report["summary"], sort_keys=True))
        return 0
    except (ValueError, OSError, struct.error, KeyError, TypeError) as exc:
        print("barn-portals29 refused: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

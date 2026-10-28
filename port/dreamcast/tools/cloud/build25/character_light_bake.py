#!/usr/bin/env python3
"""Bake PS2 character static light/AO into a source-bound RGB palette dataset.

Input is the existing re4dc-approved-render-mesh-1 exchange from ps2_cast.py
or ps2leon/build_arm_a.py. No game data or private packer is needed to run the
synthetic examples. The explicit --bake-static-light flag defaults to zero.
The mesh and rig bytes are preserved, including when the flag is enabled.
See CHARACTER_LIGHT_BAKE.md for the local owner's pack/runtime contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

SCHEMA = "re4dc-character-light-bake-1"
DEFAULT_SETTINGS = {
    "ambient_rgb": [0.45, 0.45, 0.45],
    "directional_lights": [{"toward_light": [0.3, 1.0, 0.5], "rgb": [0.55, 0.55, 0.55]}],
    "ao_samples": 32,
    "ao_distance_mm": 400.0,
    "ao_strength": 0.6,
    "ao_floor": 0.4,
    "ray_bias_mm": 0.5,
    "exclude_occluder_infos": [],
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(data: bytes) -> Any:
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def bad_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(data, object_pairs_hook=unique, parse_constant=bad_constant)


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name}: expected finite number")
    return float(value)


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name}: expected integer >= {minimum}")
    return value


def vector(value, name):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name}: expected three numbers")
    return tuple(number(v, name) for v in value)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(v, name="normal"):
    length = math.sqrt(dot(v, v))
    if not math.isfinite(length) or length < 1.0e-12:
        raise ValueError(f"{name}: zero or invalid length")
    return tuple(x / length for x in v)


def settings_of(raw: bytes | None):
    settings = dict(DEFAULT_SETTINGS)
    supplied = decode(raw) if raw is not None else {}
    if not isinstance(supplied, dict) or set(supplied) - set(settings):
        raise ValueError("unknown light-bake settings")
    settings.update(supplied)
    for key in ("ambient_rgb",):
        rgb = vector(settings[key], key)
        if any(v < 0 or v > 16 for v in rgb):
            raise ValueError(f"{key}: expected components in [0,16]")
    lights = settings["directional_lights"]
    if not isinstance(lights, list) or len(lights) > 32:
        raise ValueError("expected at most 32 offline directional lights")
    for light in lights:
        if not isinstance(light, dict) or set(light) != {"toward_light", "rgb"}:
            raise ValueError("a light requires toward_light and rgb only")
        unit(vector(light["toward_light"], "toward_light"))
        if any(v < 0 or v > 16 for v in vector(light["rgb"], "light rgb")):
            raise ValueError("light rgb: expected components in [0,16]")
    samples = integer(settings["ao_samples"], "ao_samples", 1)
    if samples > 1024:
        raise ValueError("ao_samples must be <= 1024")
    distance = number(settings["ao_distance_mm"], "ao_distance_mm")
    bias = number(settings["ray_bias_mm"], "ray_bias_mm")
    if not 0 < bias < distance:
        raise ValueError("require 0 < ray_bias_mm < ao_distance_mm")
    for key in ("ao_strength", "ao_floor"):
        if not 0 <= number(settings[key], key) <= 1:
            raise ValueError(f"{key}: expected [0,1]")
    excluded = settings["exclude_occluder_infos"]
    if not isinstance(excluded, list) or len(set(excluded)) != len(excluded):
        raise ValueError("exclude_occluder_infos must be unique integers")
    for info in excluded:
        integer(info, "exclude_occluder_infos")
    return settings


def checked_mesh(mesh_raw: bytes, source_raw: bytes):
    mesh, source = decode(mesh_raw), decode(source_raw)
    if not isinstance(mesh, dict) or mesh.get("schema") != "re4dc-approved-render-mesh-1":
        raise ValueError("expected the existing re4dc-approved-render-mesh-1 schema")
    if not isinstance(source, dict) or mesh.get("source_sha256") != digest(source_raw):
        raise ValueError("mesh/source SHA-256 binding mismatch")
    bones = mesh.get("bones")
    if not isinstance(bones, list) or not bones:
        raise ValueError("mesh has no rig")
    ids = [integer(b.get("id"), "bone id") for b in bones]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate bone id")
    parents = {}
    for bone in bones:
        bid = bone["id"]
        parent = integer(bone.get("parent"), "bone parent", -1)
        if parent != -1 and parent not in ids:
            raise ValueError("bone parent outside rig")
        parents[bid] = parent
        for name in ("rest", "capture"):
            matrix = bone.get(name)
            if matrix is None and name == "capture":
                continue
            if not isinstance(matrix, list) or len(matrix) != 4:
                raise ValueError(f"bone {bid}: invalid {name} matrix")
            for row in matrix:
                if not isinstance(row, list) or len(row) != 4:
                    raise ValueError(f"bone {bid}: invalid {name} matrix row")
                for value in row:
                    number(value, "bone matrix")
    for bid in ids:
        seen = set()
        while bid != -1:
            if bid in seen:
                raise ValueError("cyclic rig")
            seen.add(bid)
            bid = parents[bid]
    pos = mesh.get("positions_mm")
    weights = mesh.get("weights")
    if not isinstance(pos, list) or not pos or not isinstance(weights, list) or len(pos) != len(weights):
        raise ValueError("positions/weights extent mismatch")
    positions = [vector(p, "position") for p in pos]
    for row in weights:
        if not isinstance(row, list) or not row:
            raise ValueError("empty skin weights")
        row_bones, total = set(), 0.0
        for pair in row:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("weight must be [bone id, weight]")
            bid, w = integer(pair[0], "weight bone"), number(pair[1], "weight")
            if bid not in parents or bid in row_bones or w <= 0:
                raise ValueError("invalid or duplicated weighted bone")
            row_bones.add(bid)
            total += w
        if abs(total - 1.0) > 1.0e-4:
            raise ValueError("skin weights do not sum to one")
    tris = mesh.get("triangles")
    if not isinstance(tris, list) or not tris:
        raise ValueError("mesh has no triangles")
    for tri in tris:
        integer(tri.get("source_info"), "source_info")
        corners = tri.get("corners")
        if not isinstance(corners, list) or len(corners) != 3:
            raise ValueError("expected exactly three corners")
        for corner in corners:
            vi = integer(corner.get("vertex"), "corner vertex")
            if vi >= len(positions):
                raise ValueError("corner vertex outside position table")
            unit(vector(corner.get("normal"), "corner normal"))
            uv = corner.get("uv")
            if not isinstance(uv, list) or len(uv) != 2:
                raise ValueError("invalid corner UV")
            for val in uv:
                number(val, "UV")
            if "colour_rgba8" in corner:
                rgba = corner["colour_rgba8"]
                if not isinstance(rgba, list) or len(rgba) != 4:
                    raise ValueError("colour_rgba8 must have four channels")
                if any(integer(v, "colour_rgba8") > 255 for v in rgba):
                    raise ValueError("colour channel above 255")
    return mesh, source, positions


def hits_triangle(origin, direction, triangle, max_distance):
    """Double-sided Moller-Trumbore; degenerates do not occlude."""
    a, b, c = triangle
    ab, ac = sub(b, a), sub(c, a)
    h = cross(direction, ac)
    determinant = dot(ab, h)
    if abs(determinant) < 1.0e-12:
        return False
    inv = 1.0 / determinant
    s = sub(origin, a)
    u = dot(s, h) * inv
    if u < -1.0e-10 or u > 1 + 1.0e-10:
        return False
    q = cross(s, ab)
    v = dot(direction, q) * inv
    if v < -1.0e-10 or u + v > 1 + 1.0e-10:
        return False
    t = dot(ac, q) * inv
    return 1.0e-7 < t <= max_distance


def hits_box(origin, direction, lo, hi, max_distance):
    low, high = 0.0, max_distance
    for axis in range(3):
        d = direction[axis]
        if abs(d) < 1.0e-15:
            if origin[axis] < lo[axis] or origin[axis] > hi[axis]:
                return False
            continue
        a, b = (lo[axis] - origin[axis]) / d, (hi[axis] - origin[axis]) / d
        low, high = max(low, min(a, b)), min(high, max(a, b))
        if low > high:
            return False
    return True


class Occluders:
    """Deterministic median BVH: bounded leaf size, no O(corners*rays*tris) scan."""

    def __init__(self, triangles):
        self.triangles = triangles
        self.nodes = []
        self.box_tests = self.triangle_tests = self.rays = 0
        self.root = self._node(list(range(len(triangles)))) if triangles else None

    def _node(self, indices):
        lo = tuple(min(self.triangles[i][v][a] for i in indices for v in range(3)) for a in range(3))
        hi = tuple(max(self.triangles[i][v][a] for i in indices for v in range(3)) for a in range(3))
        node = len(self.nodes)
        self.nodes.append(None)
        if len(indices) <= 8:
            self.nodes[node] = (lo, hi, indices, None, None)
        else:
            axis = max(range(3), key=lambda a: hi[a] - lo[a])
            indices.sort(key=lambda i: (sum(p[axis] for p in self.triangles[i]), i))
            half = len(indices) // 2
            left, right = self._node(indices[:half]), self._node(indices[half:])
            self.nodes[node] = (lo, hi, None, left, right)
        return node

    def hits(self, origin, direction, distance):
        self.rays += 1
        todo = [] if self.root is None else [self.root]
        while todo:
            lo, hi, indices, left, right = self.nodes[todo.pop()]
            self.box_tests += 1
            if not hits_box(origin, direction, lo, hi, distance):
                continue
            if indices is None:
                todo.extend((right, left))
            else:
                for index in indices:
                    self.triangle_tests += 1
                    if hits_triangle(origin, direction, self.triangles[index], distance):
                        return True
        return False


def hemisphere(normal, count):
    """Fixed cosine-weighted Fibonacci samples, in the normal's hemisphere."""
    tangent = unit(cross((0.0, 0.0, 1.0) if abs(normal[2]) < 0.9 else (0.0, 1.0, 0.0), normal))
    bitangent = cross(normal, tangent)
    angle = math.pi * (3.0 - math.sqrt(5.0))
    for index in range(count):
        radius = math.sqrt((index + 0.5) / count)
        x, y, z = radius * math.cos(index * angle), radius * math.sin(index * angle), math.sqrt(1 - radius * radius)
        yield tuple(tangent[a] * x + bitangent[a] * y + normal[a] * z for a in range(3))


def bake(mesh_raw: bytes, source_raw: bytes, settings_raw: bytes | None = None):
    """Return deterministic dataset files, without changing source or rig bytes."""
    mesh, source, positions = checked_mesh(mesh_raw, source_raw)
    settings = settings_of(settings_raw)
    excluded = set(settings["exclude_occluder_infos"])
    present = {tri["source_info"] for tri in mesh["triangles"]}
    if excluded - present:
        raise ValueError("excluded occluder source_info is absent from the mesh")
    triangles = [tuple(positions[c["vertex"]] for c in tri["corners"])
                 for tri in mesh["triangles"] if tri["source_info"] not in excluded]
    occluders = Occluders(triangles)
    lights = [(unit(tuple(light["toward_light"])), light["rgb"]) for light in settings["directional_lights"]]
    ambient = settings["ambient_rgb"]
    palette, palette_map, rows, indices, cache = [], {}, [], [], {}
    min_ao, max_ao = 1.0, 0.0
    for tri_index, tri in enumerate(mesh["triangles"]):
        corners = []
        for corner in tri["corners"]:
            vertex = corner["vertex"]
            normal = unit(tuple(corner["normal"]))
            # Normal seams are independent samples. UV seams with the same
            # position and normal may share light, but keep distinct mappings.
            key = (vertex, normal)
            if key not in cache:
                position = positions[vertex]
                origin = tuple(position[a] + settings["ray_bias_mm"] * normal[a] for a in range(3))
                if settings["ao_strength"]:
                    covered = sum(occluders.hits(origin, ray, settings["ao_distance_mm"])
                                  for ray in hemisphere(normal, settings["ao_samples"]))
                    visibility = 1 - covered / settings["ao_samples"]
                else:
                    visibility = 1.0
                ao = max(settings["ao_floor"], 1 - settings["ao_strength"] * (1 - visibility))
                rgb = [ambient[c] for c in range(3)]
                for direction, colour in lights:
                    amount = max(0.0, dot(normal, direction))
                    for c in range(3):
                        rgb[c] += amount * colour[c]
                cache[key] = (tuple(value * ao for value in rgb), ao)
            shade, ao = cache[key]
            min_ao, max_ao = min(min_ao, ao), max(max_ao, ao)
            authored = corner.get("colour_rgba8", [255, 255, 255, 255])
            rgb = tuple(min(255, max(0, int(math.floor(shade[c] * authored[c] + 0.5)))) for c in range(3))
            if rgb not in palette_map:
                if len(palette) >= 65536:
                    raise ValueError("more than 65536 colours: split the dataset by existing source part before packing")
                palette_map[rgb] = len(palette)
                palette.append(list(rgb))
            index = palette_map[rgb]
            indices.append(index)
            corners.append({"vertex": vertex, "colour_index": index})
        rows.append({"triangle": tri_index, "source_info": tri["source_info"], "corners": corners})
    geometry = {k: mesh[k] for k in ("positions_mm", "weights", "bones", "triangles")}
    table = {
        "schema": SCHEMA,
        "mesh_sha256": digest(mesh_raw),
        "source_sha256": digest(source_raw),
        "rig_sha256": digest(encoded({k: mesh[k] for k in ("bones", "weights")})),
        "geometry_and_rig_sha256": digest(encoded(geometry)),
        "settings_sha256": digest(encoded(settings)),
        "source_policy": mesh.get("policy", ""),
        "source_ps2_archive_sha256": source.get("ps2_archive_sha256"),
        "synthetic_fixture": bool(source.get("synthetic_fixture", False)),
        "palette_rgb8": palette,
        "triangles": rows,
        "alpha_policy": "preserve source per-corner/part alpha; RGB palette does not replace alpha",
        "runtime_contract": {
            "material_vertex": 1, "ambient_vertex": 0,
            "light_inputs": "room tint plus live flash/fire only; exclude baked static lamps",
            "normal_light_evaluations_per_vertex": 0,
        },
    }
    files = {
        "mesh.json": mesh_raw,
        "source.json": source_raw,
        "settings.json": encoded(settings),
        "light-colours.json": encoded(table),
        "palette.rgb8": bytes(v for colour in palette for v in colour),
        "corner-indices.u16le": struct.pack(f"<{len(indices)}H", *indices),
    }
    manifest = {
        "schema": SCHEMA, "enabled": True,
        "files": {name: {"sha256": digest(data), "bytes": len(data)} for name, data in files.items()},
        "vertices": len(positions), "triangles": len(rows), "corners": len(indices),
        "unique_light_samples": len(cache), "palette_colours": len(palette),
        "occluder_triangles": len(triangles), "bvh_nodes": len(occluders.nodes),
        "ao_range": [min_ao, max_ao],
        "offline_ray_counts": {"rays": occluders.rays, "box_tests": occluders.box_tests,
                               "triangle_tests": occluders.triangle_tests},
        "source_mesh_identical": True, "source_rig_identical": True,
        "packed_rgb_bytes": len(files["palette.rgb8"]),
        "corner_index_bytes": len(files["corner-indices.u16le"]),
        "scope": "offline dataset; existing local packer must map colour indices and retain source alpha",
    }
    files["manifest.json"] = encoded(manifest)
    return files


def verify_dataset(directory: Path):
    manifest = decode((directory / "manifest.json").read_bytes())
    if manifest.get("schema") != SCHEMA or not isinstance(manifest.get("enabled"), bool):
        raise ValueError("not a character-light dataset")
    expected = {"mesh.json", "source.json", "settings.json", "light-colours.json", "palette.rgb8", "corner-indices.u16le"}
    if not manifest["enabled"]:
        expected = {"mesh.json"}
    if set(manifest["files"]) != expected:
        raise ValueError("unexpected dataset file set")
    files = {}
    for name, record in manifest["files"].items():
        data = (directory / name).read_bytes()
        if len(data) != record["bytes"] or digest(data) != record["sha256"]:
            raise ValueError(f"dataset file changed: {name}")
        files[name] = data
    if manifest["enabled"]:
        mesh, _, _ = checked_mesh(files["mesh.json"], files["source.json"])
        table = decode(files["light-colours.json"])
        settings = settings_of(files["settings.json"])
        if (table.get("schema") != SCHEMA or table["mesh_sha256"] != digest(files["mesh.json"]) or
                table["source_sha256"] != digest(files["source.json"]) or
                table["rig_sha256"] != digest(encoded({k: mesh[k] for k in ("bones", "weights")})) or
                table["settings_sha256"] != digest(encoded(settings)) or
                table["geometry_and_rig_sha256"] != digest(encoded({k: mesh[k] for k in
                    ("positions_mm", "weights", "bones", "triangles")}))):
            raise ValueError("bake/source binding mismatch")
        palette = table["palette_rgb8"]
        if not isinstance(palette, list) or not 1 <= len(palette) <= 65536:
            raise ValueError("invalid bake palette")
        for colour in palette:
            if not isinstance(colour, list) or len(colour) != 3 or any(integer(v, "RGB") > 255 for v in colour):
                raise ValueError("invalid palette colour")
        if bytes(v for row in palette for v in row) != files["palette.rgb8"]:
            raise ValueError("palette binary differs from JSON")
        if len(table["triangles"]) != len(mesh["triangles"]):
            raise ValueError("bake triangle count changed")
        indices = []
        for ti, (row, tri) in enumerate(zip(table["triangles"], mesh["triangles"])):
            if row["triangle"] != ti or row["source_info"] != tri["source_info"] or len(row["corners"]) != 3:
                raise ValueError("bake triangle mapping changed")
            for entry, corner in zip(row["corners"], tri["corners"]):
                index = integer(entry["colour_index"], "colour_index")
                if entry["vertex"] != corner["vertex"] or index >= len(palette):
                    raise ValueError("bake corner mapping changed")
                indices.append(index)
        if struct.pack(f"<{len(indices)}H", *indices) != files["corner-indices.u16le"]:
            raise ValueError("corner binary differs from JSON")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("bake")
    make.add_argument("mesh", type=Path)
    make.add_argument("output", type=Path)
    make.add_argument("--source", type=Path)
    make.add_argument("--settings", type=Path)
    make.add_argument("--bake-static-light", nargs="?", const=1, default=0, type=int, choices=(0, 1))
    check = commands.add_parser("verify")
    check.add_argument("dataset", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            report = verify_dataset(args.dataset)
        else:
            mesh = args.mesh.read_bytes()
            if args.bake_static_light:
                if args.source is None:
                    raise ValueError("--source is required when baking")
                files = bake(mesh, args.source.read_bytes(), args.settings.read_bytes() if args.settings else None)
            else:
                # Do not parse, normalize, reserialize or inspect source assets
                # in the off arm. This is the explicit byte-identity contract.
                files = {"mesh.json": mesh}
                files["manifest.json"] = encoded({"schema": SCHEMA, "enabled": False,
                    "files": {"mesh.json": {"sha256": digest(mesh), "bytes": len(mesh)}},
                    "source_mesh_identical": True, "scope": "pass-through; no colours baked"})
            args.output.mkdir(parents=True, exist_ok=False)
            for name, data in files.items():
                (args.output / name).write_bytes(data)
            report = verify_dataset(args.output)
        print(json.dumps({"status": "PASS", "enabled": report["enabled"], "files": report["files"]}, sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
        parser.exit(2, f"character_light_bake: {error}\n")


if __name__ == "__main__":
    main()

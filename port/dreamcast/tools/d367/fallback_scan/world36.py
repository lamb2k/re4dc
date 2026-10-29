"""Build36 world inventory: strict policy bundles or explicit legacy geometry.

The ordinary v1/v2/v3 layouts are owned by tools/convert_room_bins.py and
room/instanced_mesh.hpp. Their non-PS2 packages use live source ModelData for
placement and material state; they do not require an R4PW file. This adapter
validates the public writer's layout before returning geometry-only inventory.
It cannot recover room membership, texture keys, render passes or live draws.

A present policy is always passed to the existing strict world adapter. Its
failure is never reinterpreted as a missing optional sidecar. PS2 owner 0x50,
physical variants and unknown extensions still require their owning adapters.
No input bytes are written, normalized or repaired.
"""
import math
import struct

import formats


HEADER = struct.Struct("<4s19I")
LOD_HEADER = struct.Struct("<8I")
MESH = struct.Struct("<HBBHHIII12f")
PART = struct.Struct("<IIBBBBII4f")
MESHLET = struct.Struct("<IIIHH6H")
VERTEX = struct.Struct("<6H")
PART_LOD = struct.Struct("<II")
CLUSTER = struct.Struct("<6HII")
LEVEL = struct.Struct("<IIf")
INDEXED = 0x8000
COLOR_NAMES = {1: "oct-normal-palette", 2: "prelit-argb1555", 3: "oct-vertex"}
LEGACY_KIND = "R4IM-legacy"
LIMITATIONS = [
    "Geometry-only legacy inventory; source ModelData supplies live material and placement state.",
    "R4PW texture keys/dimensions, pass, cull, placements and vertex-alpha policy are unknown.",
    "Owner/common/BIN fields are source identifiers, not room membership or live instance counts.",
    "Stored LODs are alternatives; inventory does not establish selected geometry or runtime admission.",
]


def _aligned(value):
    return (value + 31) & ~31


def _legacy(mesh):
    require = formats.require
    h = formats.unpack(HEADER.format, mesh, label="R4IM header")
    require(h[0] == b"R4IM" and h[1] in (1, 2, 3),
            "missing matching R4PW: not a supported ordinary legacy R4IM v1/v2/v3")
    require(h[2] == len(mesh) and h[3] == formats.crc(mesh[80:]), "R4IM size/CRC")
    require(h[16] in COLOR_NAMES, "unsupported legacy R4IM color encoding")
    require(h[18:] == (0, 0) and (h[16] == 3 or h[17] == 0),
            "missing matching R4PW: physical variant or unknown R4IM extension")
    require(h[1] != 1 or h[16] == 1, "unsupported legacy v1 color extension")
    require(all(h[i] > 0 for i in (4, 5, 6, 7, 8)) and 0 < h[9] <= 16,
            "legacy R4IM empty geometry/palette count")
    require(h[16] != 3 or h[9] == 1, "oct-vertex palette count")
    lod = formats.unpack(LOD_HEADER.format, mesh, 80, "R4IM LOD header") if h[1] >= 2 else None
    if lod:
        require(lod[7] == 0, "unsupported legacy R4IM appended runtime tables")
    specs = [("mesh", h[10], h[4], MESH), ("part", h[11], h[5], PART),
             ("meshlet", h[12], h[6], MESHLET), ("vertex", h[13], h[7], VERTEX),
             ("index", h[14], h[8], struct.Struct("<B")),
             ("palette", h[15], h[9], struct.Struct("<I"))]
    if h[16] == 3:
        specs.append(("vcolor", h[17], h[7], struct.Struct("<I")))
    if lod:
        specs += [("part_lod", lod[2], h[5], PART_LOD),
                  ("cluster", lod[3], lod[0], CLUSTER), ("level", lod[4], lod[1], LEVEL)]
        if lod[5]:
            specs.append(("class", lod[5], h[4], struct.Struct("<B")))
        if lod[6]:
            specs.append(("rule", lod[6], 8, struct.Struct("<HH")))
    tables, raw, end = {}, {}, 112 if lod else 80
    for name, offset, count, fmt in specs:
        require(offset == _aligned(end), "noncanonical legacy R4IM section: " + name)
        require(not any(formats.span(mesh, end, offset - end, name + " padding")),
                "nonzero legacy R4IM section padding: " + name)
        data = formats.span(mesh, offset, count * fmt.size, name, 32)
        raw[name] = data
        if name != "index":
            tables[name] = list(fmt.iter_unpack(data))
        end = offset + len(data)
    require(len(mesh) == _aligned(end) and not any(mesh[end:]),
            "unsupported legacy R4IM trailing data/padding")
    meshes, parts, lets, vertices = (tables[name] for name in ("mesh", "part", "meshlet", "vertex"))
    require(all(m[2] != 0x50 for m in meshes),
            "missing matching R4PW: PS2 world source owner requires its policy/placements")
    require(all(c[0] < 8 for c in tables.get("class", [])), "legacy R4IM class")
    if h[16] != 2:
        require(all(v[5] >> 12 < h[9] for v in vertices), "legacy R4IM palette reference")

    next_part = 0
    for m in meshes:
        require(m[1] in (0, 1) and m[6] == next_part and m[7] <= h[5] - next_part,
                "legacy R4IM mesh part partition/common flag")
        require(all(math.isfinite(v) for v in m[8:]) and all(v > 0 for v in m[11:14]),
                "legacy R4IM mesh grid")
        require(all(m[14 + axis] <= m[17 + axis] for axis in range(3)), "legacy R4IM mesh bounds")
        next_part += m[7]
    require(next_part == h[5], "legacy R4IM unowned parts")

    summaries, vertex_ranges, index_end = [], [], 0
    for ji, row in enumerate(lets):
        first, offset, size, nv, sc = row[:5]
        indexed = bool(sc & INDEXED)
        require(not indexed or h[1] == 3, "legacy R4IM indexed meshlet requires v3")
        require(0 < nv <= 256 and (sc & 0x7fff) > 0, "legacy R4IM meshlet capacity")
        require(not indexed or offset % 2 == 0, "legacy R4IM pool table alignment")
        table_bytes = 2 * nv if indexed else 0
        formats.span(raw["index"], offset, table_bytes + size, "legacy meshlet indices")
        require(offset >= index_end and not any(raw["index"][index_end:offset]),
                "legacy R4IM overlapping indices or unknown index gap")
        index_end = offset + table_bytes + size
        refs = (tuple(first + value for value in struct.unpack_from("<%dH" % nv, raw["index"], offset))
                if indexed else range(first, first + nv))
        require(first <= h[7] and all(value < h[7] for value in refs), "legacy R4IM vertex reference")
        require(all(row[5 + axis] <= row[8 + axis] for axis in range(3)), "legacy R4IM meshlet bounds")
        require(all(row[5 + axis] <= vertices[value][axis] <= row[8 + axis]
                    for value in refs for axis in range(3)), "legacy R4IM meshlet bounds enclosure")
        vertex_ranges.append((first, max(refs) + 1))
        cursor, strips, corners, triangles, maximum = offset + table_bytes, 0, 0, 0, 0
        while cursor < index_end:
            count = raw["index"][cursor]
            require(3 <= count and count + 1 <= index_end - cursor, "legacy R4IM strip length")
            require(all(k < nv for k in raw["index"][cursor + 1:cursor + 1 + count]),
                    "legacy R4IM strip local reference")
            strips += 1
            corners += count
            triangles += count - 2
            maximum = max(maximum, count)
            cursor += count + 1
        require(strips == (sc & 0x7fff), "legacy R4IM strip count")
        summaries.append(dict(index=ji, vertices=nv, corners=corners, triangles=triangles,
                              indexed=indexed, strips=strips, max_strip=maximum))
    require(index_end == h[8], "legacy R4IM unowned index tail")

    next_let, next_cluster, next_level, previous_pool = 0, 0, 0, 0
    for pi, part in enumerate(parts):
        first, count = part[6:8]
        require(part[5] == 0 and all(math.isfinite(v) for v in part[8:])
                and all(v > 0 for v in part[10:]), "legacy R4IM part state/UV")
        require(first == next_let and count <= h[6] - first, "legacy R4IM part meshlet partition")
        next_let += count
        if h[1] == 3 and count:
            lo = min(a for a, _ in vertex_ranges[first:first + count])
            hi = max(b for _, b in vertex_ranges[first:first + count])
            require(lo >= previous_pool, "legacy R4IM part pool overlap")
            previous_pool = hi
        if not lod:
            for ji in range(first, first + count):
                summaries[ji].update(level=0, level_origin="implicit-v1")
            continue
        fc, nc = tables["part_lod"][pi]
        require(fc == next_cluster and nc <= lod[0] - fc, "legacy R4IM part cluster partition")
        next_cluster += nc
        owned_let = first
        for ci in range(fc, fc + nc):
            cluster = tables["cluster"][ci]
            fl, nl = cluster[6:]
            require(nl > 0 and fl == next_level and nl <= lod[1] - fl, "legacy R4IM cluster level partition")
            next_level += nl
            require(all(cluster[a] <= cluster[a + 3] for a in range(3)), "legacy R4IM cluster bounds")
            previous_error = 0.
            for ordinal, li in enumerate(range(fl, fl + nl)):
                lf, ln, error = tables["level"][li]
                require(math.isfinite(error) and previous_error <= error < 3.e38, "legacy R4IM level error")
                previous_error = error
                require(lf == owned_let and ln <= first + count - lf, "legacy R4IM level meshlet partition")
                owned_let += ln
                for ji in range(lf, lf + ln):
                    bounds = lets[ji][5:]
                    require(all(cluster[a] <= bounds[a] and bounds[a + 3] <= cluster[a + 3]
                                for a in range(3)), "legacy R4IM cluster bounds enclosure")
                    summaries[ji].update(level=ordinal, cluster=ci, level_origin="stored-LOD-table")
        require(owned_let == first + count, "legacy R4IM unowned LOD meshlets")
    require(next_let == h[6], "legacy R4IM unowned meshlets")
    if lod:
        require((next_cluster, next_level) == lod[:2], "legacy R4IM unowned clusters/levels")

    layout = "R4IM-v%d-legacy" % h[1]
    models = []
    for mi, record in enumerate(meshes):
        inventory = []
        for pi in range(record[6], record[6] + record[7]):
            part = parts[pi]
            meshlets = summaries[part[6]:part[6] + part[7]]
            level0 = [row for row in meshlets if row["level"] == 0]
            inventory.append(dict(index=pi, meshlets=meshlets,
                vertices=sum(row["vertices"] for row in level0),
                corners=sum(row["corners"] for row in level0), triangles=sum(row["triangles"] for row in level0),
                vertex_basis="stored v1 local vertices" if h[1] == 1 else "stored level-0 local vertices",
                source_offset=part[0], source_size=part[1], source_alpha=part[3], source_part_flags=part[4],
                texture_index=part[2], texture_key=None, texture_width=None, texture_height=None,
                pass_id=None, cull=None, vertex_alpha=None, vertex_colors=None,
                material_flags=None, material_raw=None, model_flags=None, legacy_opcodes=[],
                uv_excess=None, signed_uv=False, cone_status="not-actor-path", colors=[],
                world_layout=layout, color_encoding=COLOR_NAMES[h[16]], metadata_status="incomplete"))
        models.append(dict(key=f"mesh[{mi}]/bin[{record[0]}]", name=f"BIN {record[0]:#x}",
            kind=LEGACY_KIND, model_id=None, parts=inventory, source_sha256=formats.sha(mesh),
            source_bytes=len(mesh), policy_sha256=None, placements=None, lineage=None,
            world_layout=layout, color_encoding=COLOR_NAMES[h[16]],
            source_owner=record[2], source_common=bool(record[1]), source_vertices=record[3],
            source_parts=record[4], source_flags=record[5], metadata_status="incomplete",
            policy_status="not-stored-in-legacy-format"))
    return dict(models=models, meshlets=h[6], parts=h[5], placements=None, layout=layout, lineage=None,
                stored_vertices=h[7], lod=h[1] >= 2, color_encoding=COLOR_NAMES[h[16]],
                metadata_status="incomplete", policy_status="not-stored-in-legacy-format",
                limitations=list(LIMITATIONS))


def parse_world(mesh, policy=None):
    """Return validated inventory; only ``None`` means no policy was supplied.

    The caller owns file selection, containment checks and sidecar provenance.
    In particular, it must not turn unreadable/malformed present files into
    ``None``. Legacy models need inventory-only classification and partial
    coverage; they must not enter the scanner's actor fallback classifier.
    """
    if policy is not None:
        result = formats.parse_world(mesh, policy)
        return dict(result, metadata_status="complete", policy_status="present-validated", limitations=[])
    return _legacy(mesh)

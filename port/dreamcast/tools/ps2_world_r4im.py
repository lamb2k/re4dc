#!/usr/bin/env python3
"""PS2 r101 world (full-wrapper-v5 .r4p + ps2_world_data.inc) -> R4IM v3 + an R4PW placement sidecar.

The committed scenery machinery then draws it (native_static.cpp MeshDraw: cluster LOD, the transform-once
meshlet fast path, direct TA submission) instead of native_ps2_world.cpp's scalar path.

Mesh = one PS2 template in its own model space (template positions x factor, millimetres); the 22
normal-lit placements (79..100) get a mesh each, because their reference light depends on the placement.
Part = one ordered range of the template (one texture, pass and cull). Triangles are the r19 renderer's
(native_ps2_world.cpp draw(): corner flag ends a strip, odd positions reversed); colours are its final
per-corner colours (authored RGBA/128 or the reference normal light, times the texture gain, clamped),
stored prelit as ARGB1555 (convert_lod color_mode="prelit"). Vertex alpha is 1.0 everywhere (checked).

R4PW v1 (little endian): header {'R4PW', version 1, placement_count, part_count, mesh_count, crc32(body),
0, 0}; part_count x {u32 crc, fnv; u16 width, height; u8 pass (0 OP, 1 PT, 2 TR), cull (native part cull:
0 none, 1 CCW, 2 CW; PS2 cull 0 -> 2, 2 -> 0), texture index, 0} in R4IM part order; placement_count x
{u16 mesh, u16 placement; f32 affine[3][4] (model mm -> world mm)} in r19 draw order.
"""
import argparse, collections, hashlib, json, math, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert_room_bins as crb
import mesh_lod
import ps2src

OWNER = 0x50
PS2_TO_PART_CULL = {0: 2, 1: 1, 2: 0}


class Token:
    def __init__(self, mesh):
        self.mesh = mesh

    def __repr__(self):
        return "ps2-mesh-%d" % self.mesh


def build(package, tables):
    pkg, tab = package, tables
    meshes = []          # dict(template, placement_lit or None, ranges=[range index of the first user])
    mesh_of = {}
    placements = []
    for p in pkg.placements:
        t = pkg.templates[p["template"]]
        key = (p["template"], p["placement"] if t["kind"] else None)
        if key not in mesh_of:
            mesh_of[key] = len(meshes)
            meshes.append(dict(template=p["template"], lit=key[1], placement=p,
                               ranges=list(range(p["first_range"], p["first_range"] + p["range_count"]))))
        placements.append((mesh_of[key], p))
    sources, parts_meta = {}, []
    for mi, m in enumerate(meshes):
        t = pkg.templates[m["template"]]
        p = m["placement"]
        positions = [tuple(v * t["factor"] for v in struct.unpack_from("<3h", pkg.payload, t["position"][0] + 6 * i))
                     for i in range(t["position"][1])]
        uvs, uv_index, colors, color_index = [], {}, [], {}
        parts = []
        for k, ri in enumerate(m["ranges"]):
            pol = tab["policy"][ri]
            tex = tab["textures"][pol["texture"]]
            loose = []
            for tri in pkg.range_triangles(ri):
                corners = []
                for ci in tri:
                    c = pkg.corner(t, ci)
                    rgba = ps2src.corner_rgba(tab, p["placement"], p["affine"], t, c, tex["gain"])
                    c8 = tuple(int(ps2src.clamp(x) * 255.0 + 0.5) for x in rgba)
                    if c8 not in color_index:
                        color_index[c8] = len(colors)
                        colors.append(c8)
                    if c["uv"] not in uv_index:
                        uv_index[c["uv"]] = len(uvs)
                        uvs.append(c["uv"])
                    corners.append((c["pos_index"], color_index[c8], uv_index[c["uv"]], 0))
                loose.append(tuple(corners))
            parts.append(dict(offset=32 * k, size=0, flags=0, texture=k & 255, alpha=255, strips=[], loose=loose))
            parts_meta.append((tex["crc"], tex["fnv"], tex["width"], tex["height"], pol["pass_"],
                               PS2_TO_PART_CULL[pol["cull"]], pol["texture"]))
        sources[mi] = dict(flags=0, nvtx=min(65535, len(positions)), nparts=len(parts), positions=positions,
                           parts=parts, uv=uvs.__getitem__, color=colors.__getitem__,
                           normal=lambda n: (0.0, 1.0, 0.0), bytes=0)
    return meshes, placements, sources, parts_meta


def placement_scale(affine):
    return max(math.sqrt(sum(affine[r][c] ** 2 for r in range(3))) for c in range(3))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("r4p", type=Path)
    ap.add_argument("inc", type=Path)
    ap.add_argument("out", type=Path, help="output stem: <out>.re4mesh, <out>.r4pw, <out>.json")
    ap.add_argument("--lod-eps", default="24,48,96,192,384")
    ap.add_argument("--lod-min-gain", type=float, default=0.4)
    ap.add_argument("--lod-max-levels", type=int, default=4)
    ap.add_argument("--lod-floor", type=float, default=2.0)
    ap.add_argument("--lod-cluster", type=float, default=20000.0)
    ap.add_argument("--no-share", action="store_true")
    ap.add_argument("--lod-uv-guard", type=float, default=None,
                    help="refuse LOD collapses that move a corner's UV off its triangle's mapping by more "
                         "than this (UV units, e.g. 0.002; mesh_lod.UV_GUARD); default off")
    ap.add_argument("--strip-swaps", action="store_true",
                    help="stripify with swaps (repeat a corner to turn; same drawn triangles, longer strips)")
    ap.add_argument("--meshlet-vertices", type=int, default=64,
                    help="largest meshlet (runtime bound 256; default 64, user-adopted 2026-09-28: -2.5 hw ms for +53 KB)")
    layouts = ap.add_mutually_exclusive_group()
    layouts.add_argument("--scenery-local-indexed", action="store_true", default=argparse.SUPPRESS,
                         help="also write exact local-vertex alternate ps2-sli1.re4mesh beside the unchanged output")
    layouts.add_argument("--scenery-direct-strips", action="store_true", default=argparse.SUPPRESS,
                         help="also write exact sequential-corner alternate ps2-sds1.re4mesh beside the unchanged output")
    ap.add_argument("--scenery-record-split", "--record-split", type=int, choices=(0, 1),
                    nargs="?", const=1, default=argparse.SUPPRESS,
                    help="experimental v4 emit16/bounds12 alternate <out>-split.re4mesh/.r4sg; default off")
    a = ap.parse_args()
    # Keep even the ordinary JSON receipt identical when the experiment is off.
    record_split = bool(vars(a).pop("scenery_record_split", 0))
    if record_split and (getattr(a, "scenery_local_indexed", False) or getattr(a, "scenery_direct_strips", False)):
        raise SystemExit("SCENERY_RECORD_SPLIT cannot be composed with Build12 local-indexed/direct-strips; a new lineage format is required")
    if not 3 <= a.meshlet_vertices <= 256:
        raise SystemExit("--meshlet-vertices must be 3..256")
    crb.MAX_MESHLET_VERTICES = a.meshlet_vertices
    mesh_lod.STRIP_SWAPS = a.strip_swaps
    mesh_lod.UV_GUARD = a.lod_uv_guard
    pkg = ps2src.Package(a.r4p)
    tab = ps2src.load_tables(a.inc)
    if ps2src.payload_crc(pkg.payload) != tab["payload_crc"]:
        raise SystemExit("payload crc does not match ps2_world_data.inc")
    meshes, placements, sources, parts_meta = build(pkg, tab)
    scales = collections.defaultdict(float)
    for mi, p in placements:
        scales[(OWNER, mi)] = max(scales[(OWNER, mi)], placement_scale(p["affine"]))
    entries = [(OWNER, 0, mi, Token(mi)) for mi in range(len(meshes))]
    eps = tuple(float(x) for x in a.lod_eps.split(","))
    blob, summary = crb.convert_lod(entries, 1.0, scales=dict(scales), eps_world=eps, cluster_world=a.lod_cluster,
                                    min_gain=a.lod_min_gain, max_levels=a.lod_max_levels,
                                    floor={None: a.lod_floor} if a.lod_floor > 0 else None, share=not a.no_share,
                                    source=lambda token: sources[token.mesh], color_mode="prelit")
    if summary["parts"] != len(parts_meta):
        raise SystemExit("part count %d != %d (an empty mesh was skipped)" % (summary["parts"], len(parts_meta)))
    body = b"".join(struct.pack("<IIHHBBBB", *m, 0) for m in parts_meta)
    body += b"".join(struct.pack("<HH12f", mi, p["placement"], *[x for row in p["affine"] for x in row])
                     for mi, p in placements)
    side = struct.pack("<4s7I", b"R4PW", 1, len(placements), len(parts_meta), len(meshes), zlib.crc32(body), 0, 0) + body
    layout_report = None
    if getattr(a, "scenery_local_indexed", False) or getattr(a, "scenery_direct_strips", False):
        import scenery_data_variants as layouts
        variant = "local-indexed" if getattr(a, "scenery_local_indexed", False) else "direct-strips"
        candidate, _, layout_report = layouts.convert(blob, variant, side)
        candidate_path = a.out.parent / (layouts.STEMS[variant] + ".re4mesh")
        if candidate_path.resolve() == a.out.with_suffix(".re4mesh").resolve():
            raise SystemExit("normal output stem must differ from the alternate filename")
        if candidate_path.exists() and a.out.with_suffix(".re4mesh").exists() and candidate_path.samefile(a.out.with_suffix(".re4mesh")):
            raise SystemExit("normal and alternate output paths alias through a hard link")
        layout_report["path"] = str(candidate_path)
    split_outputs = None
    if record_split:
        import scenery_record_split as split
        split.refuse_extra_sidecars(a.out.with_suffix(".re4mesh"))
        split_stem = a.out.with_name(a.out.name + "-split")
        split.refuse_extra_sidecars(split_stem.with_suffix(".re4mesh"))
        ordinary_paths = [a.r4p, a.inc] + [a.out.with_suffix(s) for s in (".re4mesh", ".r4pw", ".r4sg", ".json")]
        candidate_paths = [split_stem.with_suffix(s) for s in (".re4mesh", ".r4sg", ".json")]
        for dst in candidate_paths:
            split.require(all(dst.resolve() != src.resolve() and
                              not (dst.exists() and src.exists() and dst.samefile(src)) for src in ordinary_paths),
                          "split output aliases a source/control path")
        existing_groups = a.out.with_suffix(".r4sg")
        split_outputs = split.convert(blob, side, existing_groups.read_bytes() if existing_groups.exists() else None)
    a.out.with_suffix(".re4mesh").write_bytes(blob)
    a.out.with_suffix(".r4pw").write_bytes(side)
    if layout_report is not None:
        candidate_path.write_bytes(candidate)
    level0 = summary["level0_triangles"]
    summary.pop("meshes_detail")
    report = dict(source=str(a.r4p), source_sha256=hashlib.sha256(pkg.bytes).hexdigest(),
                  inc_sha256=hashlib.sha256(a.inc.read_bytes()).hexdigest(),
                  args=vars(a) | dict(r4p=str(a.r4p), inc=str(a.inc), out=str(a.out)),
                  meshes=len(meshes), placements=len(placements), source_triangles=sum(
                      len(pkg.range_triangles(r)) for r in range(len(pkg.ranges))),
                  re4mesh_bytes=len(blob), re4mesh_sha256=hashlib.sha256(blob).hexdigest(),
                  r4pw_bytes=len(side), r4pw_sha256=hashlib.sha256(side).hexdigest(), level0_triangles=level0,
                  summary=summary)
    if layout_report is not None:
        report["layout_candidate"] = layout_report
    a.out.with_suffix(".json").write_text(json.dumps(report, indent=1, default=str))
    if split_outputs:
        split_blob, split_groups, split_report = split_outputs
        split_stem.with_suffix(".re4mesh").write_bytes(split_blob)
        split_stem.with_suffix(".r4sg").write_bytes(split_groups)
        split_stem.with_suffix(".json").write_text(json.dumps(split_report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("meshes", "placements", "source_triangles", "level0_triangles",
                                             "re4mesh_bytes", "r4pw_bytes")}))


if __name__ == "__main__":
    main()

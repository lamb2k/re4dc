#!/usr/bin/env python3
"""Exact offline SLI1/SDS1 PS2 scenery layouts, with original-package provenance.

SLI1 expands each shared gather to its existing local 12-byte vertex order.
SDS1 stores each original strip corner once, in strip order. It only splits
between whole strips when the existing 256-local-vertex limit requires it.
The source mesh, policy, source identities, LOD decisions and strip order do
not change. This is a data-layout experiment, not a geometry reducer.

The optional original R4SG is validated, then remapped with identical source
group bounds. No source mesh, policy, or original metadata file is overwritten.
Other mesh-CRC-bound metadata must not be borrowed by these alternate files.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

import convert_room_bins as fmt

MARKERS = {"local-indexed": int.from_bytes(b"SLI1", "little"),
           "direct-strips": int.from_bytes(b"SDS1", "little")}
STEMS = {"local-indexed": "ps2-sli1", "direct-strips": "ps2-sds1"}
INDEXED = 0x8000


def require(ok, message):
    if not ok:
        raise ValueError(message)


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Package:
    """Strict subset used by the current prelit PS2 world builder.

    Unknown header/runtime tables, nonzero unclaimed bytes and section aliases
    are refused instead of being silently dropped by repacking.
    """
    def __init__(self, data, variant=None):
        self.data = bytes(data)
        require(len(data) >= 112, "short R4IM")
        self.h = h = fmt.HEADER.unpack_from(data)
        require(h[0] == b"R4IM" and h[1] in (2, 3) and h[2] == len(data), "R4IM identity/extent")
        require(h[6] <= 65536, "meshlet id capacity exceeds uint16 Pick.let")
        require(h[3] == crc(data[80:]), "R4IM body CRC")
        require(h[16] == fmt.COLOR_ARGB1555, "only prelit PS2 colour encoding is supported")
        if variant is None:
            require(h[17:20] == (0, 0, 0), "source provenance/marker must be empty (SDO3 unsupported)")
        else:
            require(variant in MARKERS and h[1] == 3 and h[19] == MARKERS[variant]
                    and h[17] >= 112, "variant marker/provenance")
        self.lod = lod = fmt.LOD_HEADER.unpack_from(data, 80)
        require(not lod[7], "appended runtime/impostor/texture tables are unsupported")
        self.sections = {}
        spans = [(0, 112, "headers")]

        def section(name, offset, count, stride):
            require(112 <= offset <= len(data) and count <= (len(data)-offset)//stride,
                    "section extent: " + name)
            require(not (offset & 3), "section alignment: " + name)
            self.sections[name] = bytes(data[offset:offset+count*stride])
            if count:
                spans.append((offset, offset+count*stride, name))

        for name, offset, count, stride in (
                ("mesh", h[10], h[4], 68), ("part", h[11], h[5], 36),
                ("meshlet", h[12], h[6], 28), ("vertex", h[13], h[7], 12),
                ("index", h[14], h[8], 1), ("palette", h[15], h[9], 4),
                ("part_lod", lod[2], h[5], 8), ("cluster", lod[3], lod[0], 20),
                ("level", lod[4], lod[1], 12)):
            section(name, offset, count, stride)
        require(0 < h[9] <= 16, "palette extent")
        if lod[5]:
            section("class", lod[5], h[4], 1)
            require(all(c < fmt.CLASS_RULES for c in self.sections["class"]), "mesh class")
        if lod[6]:
            section("rule", lod[6], fmt.CLASS_RULES, fmt.CLASS_RULE.size)
        previous = 0
        for start, end, name in sorted(spans):
            require(start >= previous, "overlapping sections: " + name)
            require(not any(data[previous:start]), "unrecognized nonzero data before " + name)
            previous = end
        require(not any(data[previous:]), "unrecognized trailing data")
        self.meshes = list(fmt.MESH.iter_unpack(self.sections["mesh"]))
        self.parts = list(fmt.PART.iter_unpack(self.sections["part"]))
        self.part_lods = list(fmt.PART_LOD.iter_unpack(self.sections["part_lod"]))
        self.clusters = list(fmt.CLUSTER.iter_unpack(self.sections["cluster"]))
        self.levels = list(fmt.LEVEL.iter_unpack(self.sections["level"]))
        self.lets = []
        vertices, indices = self.sections["vertex"], self.sections["index"]
        next_local = 0
        for row in fmt.MESHLET.iter_unpack(self.sections["meshlet"]):
            fv, fs, sb, vc, sc = row[:5]
            ix = bool(sc & INDEXED)
            require(0 < vc <= 256 and fv < h[7], "meshlet vertex range")
            require(not ix or h[1] == 3, "indexed v2 meshlet")
            table = 2*vc if ix else 0
            require(fs <= h[8] and table+sb <= h[8]-fs and (not ix or fs % 2 == 0),
                    "meshlet strip extent/alignment")
            offsets = struct.unpack_from("<%dH" % vc, indices, fs) if ix else range(vc)
            require(all(fv+k < h[7] for k in offsets), "meshlet pool index")
            local = [vertices[12*(fv+k):12*(fv+k+1)] for k in offsets]
            strips, cursor = [], fs+table
            while cursor < fs+table+sb:
                n = indices[cursor]
                require(3 <= n <= 255 and cursor+1+n <= fs+table+sb, "strip length")
                strip = bytes(indices[cursor+1:cursor+1+n])
                require(all(k < vc for k in strip), "strip local index")
                strips.append(strip)
                cursor += 1+n
            require(strips and len(strips) == (sc & 0x7fff), "strip count")
            for raw in local:
                xyz = struct.unpack_from("<3H", raw)
                require(all(row[5+a] <= xyz[a] <= row[8+a] for a in range(3)), "meshlet bounds")
            if variant:
                require(not ix and fv == next_local, "variant must contain dense disjoint local meshlets")
                next_local += vc
            if variant == "direct-strips":
                require(bytes(k for strip in strips for k in strip) == bytes(range(vc)),
                        "SDS1 must consume each sequential local vertex exactly once")
            self.lets.append(dict(row=row, vertices=local, strips=strips, indexed=ix,
                                  references=[fv+k for k in offsets]))
        if variant:
            require(next_local == h[7], "variant vertex extent")
        covered, previous_vertex = 0, 0
        for p, pl in zip(self.parts, self.part_lods):
            require(not p[5] and p[6] == covered and p[7] <= h[6]-covered, "part partition/state")
            covered += p[7]
            if h[1] == 3:
                refs = [k for m in self.lets[p[6]:covered] for k in m["references"]]
                if refs:
                    require(min(refs) >= previous_vertex, "overlapping part vertex pools")
                    previous_vertex = max(refs)+1
            require(pl[0] <= len(self.clusters) and pl[1] <= len(self.clusters)-pl[0], "part clusters")
            # chunk_select reserves p.meshlet_count Picks before selecting one
            # level per cluster. Check the worst simultaneous selection, even
            # when individually valid cluster ranges overlap.
            remaining_picks = p[7]
            for cl in self.clusters[pl[0]:pl[0]+pl[1]]:
                fl, nl = cl[6:8]
                require(nl > 0 and fl <= len(self.levels) and nl <= len(self.levels)-fl, "cluster levels")
                prev_error = 0.0
                for first, count, error in self.levels[fl:fl+nl]:
                    require(math.isfinite(error) and prev_error <= error < 3.0e38, "LOD error")
                    require(p[6] <= first <= p[6]+p[7] and count <= p[6]+p[7]-first, "LOD meshlet range")
                    prev_error = error
                largest_level = max(level[1] for level in self.levels[fl:fl+nl])
                require(largest_level <= remaining_picks, "part pick capacity exceeded by cluster levels")
                remaining_picks -= largest_level
        require(covered == h[6], "part meshlet coverage")
        covered = 0
        for m in self.meshes:
            require(m[6] == covered and m[7] <= h[5]-covered, "mesh part partition")
            require(all(math.isfinite(f) for f in m[8:]) and all(f > 0 for f in m[11:14]), "mesh grid")
            covered += m[7]
        require(covered == h[5], "mesh part coverage")


def _identity_checks(message, checks, diagnostics):
    """Keep legacy errors by default; diagnostics never change admission."""
    failed = [row for row in checks if not row[0]]
    if failed and diagnostics:
        message += ": " + "; ".join(
            f"{field} actual={actual!r} expected={expected!r}"
            for _, field, actual, expected in failed)
    require(not failed, message)


def policy_header(side, package, *, policy_diagnostics=False):
    require(len(side) >= 32, "short R4PW")
    p = struct.unpack_from("<4s7I", side)
    _identity_checks("R4PW identity/counts/reserved", (
        (p[0] == b"R4PW", "magic@0", p[0], b"R4PW"),
        (p[1] == 1, "version@4", p[1], 1),
        (p[3] == package.h[5], "part_count@12", p[3], package.h[5]),
        (p[4] == package.h[4], "mesh_count@16", p[4], package.h[4]),
        (p[6] == 0, "reserved@24", p[6], 0),
        (p[7] == 0, "reserved@28", p[7], 0)), policy_diagnostics)
    actual_crc = crc(side[32:])
    _identity_checks("R4PW size/CRC", (
        (len(side) == 32+16*p[3]+52*p[2], "file_bytes", len(side), 32+16*p[3]+52*p[2]),
        (p[5] == actual_crc, "body_crc@20", f"{p[5]:08x}", f"{actual_crc:08x}")),
        policy_diagnostics)
    for row in struct.iter_unpack("<IIHHBBBB", side[32:32+16*p[3]]):
        require(0 < row[2] <= 1024 and 0 < row[3] <= 1024 and row[4] <= 2 and row[5] <= 2,
                "R4PW material")
    for row in struct.iter_unpack("<HH12f", side[32+16*p[3]:]):
        require(row[0] < p[4] and all(math.isfinite(x) for x in row[2:]), "R4PW placement")
    return p


def parse_groups(data, package, side, *, policy_diagnostics=False):
    policy = policy_header(side, package, policy_diagnostics=policy_diagnostics)
    require(len(data) >= 32, "short R4SG")
    w = struct.unpack_from("<4s7I", data)
    actual_crc = crc(data[32:])
    _identity_checks("R4SG identity/CRC", (
        (w[0] == b"R4SG", "magic@0", w[0], b"R4SG"),
        (w[1] == 1, "version@4", w[1], 1),
        (w[2] == package.h[6], "meshlet_count@8", w[2], package.h[6]),
        (1 <= w[3] <= 8, "groups_per_meshlet@12", w[3], "1..8"),
        (w[4] == package.h[3], "mesh_body_crc@16", f"{w[4]:08x}", f"{package.h[3]:08x}"),
        (w[5] == package.h[2], "mesh_file_bytes@20", w[5], package.h[2]),
        (w[6] == policy[5], "physical_policy_crc@24", f"{w[6]:08x}", f"{policy[5]:08x}"),
        (len(data) == 32+16*w[2]*w[3], "file_bytes", len(data), 32+16*w[2]*w[3]),
        (w[7] == actual_crc, "record_crc@28", f"{w[7]:08x}", f"{actual_crc:08x}")),
        policy_diagnostics)
    result = []
    for li, meshlet in enumerate(package.lets):
        cursor, strip_first, groups = 0, 0, []
        for gi in range(w[3]):
            rec = struct.unpack_from("<6HHBB", data, 32+16*(li*w[3]+gi))
            end, lo, hi = rec[6:9]
            require(cursor <= end <= meshlet["row"][2], "R4SG byte end")
            first = strip_first
            used = []
            while cursor < end and strip_first < len(meshlet["strips"]):
                st = meshlet["strips"][strip_first]
                used.extend(st); cursor += 1+len(st); strip_first += 1
            require(cursor == end, "R4SG strip boundary")
            if used:
                require(lo <= min(used) <= max(used) <= hi < len(meshlet["vertices"]), "R4SG local range")
                for k in used:
                    xyz = struct.unpack_from("<3H", meshlet["vertices"][k])
                    require(all(rec[a] <= xyz[a] <= rec[3+a] for a in range(3)), "R4SG bounds")
            else:
                require(lo > hi, "R4SG empty range")
            groups.append((first, strip_first, rec))
        require(strip_first == len(meshlet["strips"]), "R4SG coverage")
        result.append(groups)
    return w[3], result


def pack(source, sections, counts):
    body, offsets = bytearray(32), {}
    for name in ("mesh", "part", "meshlet", "vertex", "index", "palette", "part_lod", "cluster", "level", "class", "rule"):
        if name not in sections:
            continue
        body.extend(bytes(fmt.align(80+len(body))-80-len(body)))
        offsets[name] = 80+len(body)
        body.extend(sections[name])
    body.extend(bytes(fmt.align(80+len(body))-80-len(body)))
    lod = list(source.lod)
    lod[2:7] = [offsets["part_lod"], offsets["cluster"], offsets["level"], offsets.get("class", 0), offsets.get("rule", 0)]
    body[:32] = fmt.LOD_HEADER.pack(*lod)
    h = list(source.h)
    h[1:4] = [3, 80+len(body), crc(body)]
    h[6:9] = counts
    h[10:16] = [offsets[n] for n in ("mesh", "part", "meshlet", "vertex", "index", "palette")]
    return h, body


def convert(mesh, variant, side=None, groups=None, *, policy_diagnostics=False):
    require(variant in MARKERS, "unknown variant")
    source = Package(mesh)
    if side is not None:
        policy_header(side, source, policy_diagnostics=policy_diagnostics)
    require(groups is None or side is not None, "R4SG conversion needs its exact R4PW")
    old_groups = parse_groups(groups, source, side, policy_diagnostics=policy_diagnostics) if groups is not None else None
    vertices, strips, meshlets, children, prefix = bytearray(), bytearray(), [], [], [0]
    for li, old in enumerate(source.lets):
        chunks, first, used = [], 0, 0
        for i, strip in enumerate(old["strips"]):
            if variant == "direct-strips" and used+len(strip) > 256:
                chunks.append((first, i)); first, used = i, 0
            used += len(strip)
        chunks.append((first, len(old["strips"])))
        for first, end in chunks:
            fv, fs = len(vertices)//12, len(strips)
            local = old["vertices"] if variant == "local-indexed" else [old["vertices"][k]
                for strip in old["strips"][first:end] for k in strip]
            vertices.extend(b"".join(local))
            next_local = 0
            for strip in old["strips"][first:end]:
                strips.append(len(strip))
                strips.extend(strip if variant == "local-indexed" else range(next_local, next_local+len(strip)))
                next_local += len(strip)
            row = (fv, fs, len(strips)-fs, len(local), end-first, *old["row"][5:])
            meshlets.append(row); children.append((li, first, end))
            require(len(meshlets) <= 65536, "expanded meshlet id capacity exceeds uint16 Pick.let")
        prefix.append(len(meshlets))
    sections = dict(source.sections)
    sections.update(vertex=bytes(vertices), index=bytes(strips),
                    meshlet=b"".join(fmt.MESHLET.pack(*row) for row in meshlets))
    parts = bytearray(source.sections["part"])
    for i, p in enumerate(source.parts):
        struct.pack_into("<II", parts, 36*i+12, prefix[p[6]], prefix[p[6]+p[7]]-prefix[p[6]])
    sections["part"] = bytes(parts)
    levels = bytearray(source.sections["level"])
    for i, (first, count, _) in enumerate(source.levels):
        struct.pack_into("<II", levels, 12*i, prefix[first], prefix[first+count]-prefix[first])
    sections["level"] = bytes(levels)
    h, body = pack(source, sections, [len(meshlets), len(vertices)//12, len(strips)])
    h[17:20] = [len(mesh), source.h[3], MARKERS[variant]]
    result = fmt.HEADER.pack(*h)+body
    new_groups = None
    if old_groups:
        count, records = old_groups
        out = bytearray()
        for new_li, (old_li, first, end) in enumerate(children):
            cursor, local = 0, 0
            for group_first, group_end, rec in records[old_li]:
                a, b = max(first, group_first), min(end, group_end)
                if a < b:
                    selected = source.lets[old_li]["strips"][a:b]
                    n = sum(map(len, selected))
                    used = [k for s in selected for k in s]
                    lo, hi = (min(used), max(used)) if variant == "local-indexed" else (local, local+n-1)
                    cursor += n+len(selected); local += n
                    out.extend(struct.pack("<6HHBB", *rec[:6], cursor, lo, hi))
                else:
                    out.extend(struct.pack("<6HHBB", 0, 0, 0, 0, 0, 0, cursor, 1, 0))
            require(cursor == meshlets[new_li][2], "internal group remap coverage")
        p = policy_header(side, source)
        new_groups = struct.pack("<4s7I", b"R4SG", 1, len(meshlets), count, h[3], len(result), p[5], crc(out))+out
        require(len(new_groups) <= 262144, "candidate R4SG exceeds runtime size limit")
    validate_pair(mesh, result, variant, side, groups, new_groups, policy_diagnostics=policy_diagnostics)
    stats = dict(variant=variant, marker=struct.pack("<I", MARKERS[variant]).decode(),
        source_bytes=len(mesh), source_crc=source.h[3], source_sha256=sha(mesh),
        candidate_bytes=len(result), candidate_crc=h[3], candidate_sha256=sha(result),
        source_meshlets=source.h[6], candidate_meshlets=len(meshlets), split_children=len(meshlets)-source.h[6],
        source_vertices=source.h[7], candidate_vertices=len(vertices)//12,
        source_index_bytes=source.h[8], candidate_index_bytes=len(strips),
        original_indexed_meshlets=sum(m["indexed"] for m in source.lets),
        ordered_strip_corners=sum(len(s) for m in source.lets for s in m["strips"]),
        resident_package_delta=len(result)-len(mesh), retained_gather_scratch_bytes=3072,
        source_groups_bytes=len(groups) if groups is not None else 0,
        candidate_groups_bytes=len(new_groups) if new_groups is not None else 0,
        meshlet_remap=[[prefix[i], prefix[i+1]-prefix[i]] for i in range(source.h[6])],
        metadata_policy="R4PW unchanged; supplied R4SG mapped with original selection bounds; no other CRC metadata rebound")
    return bytes(result), new_groups, stats


def validate_pair(before, after, variant, side=None, before_groups=None, after_groups=None, *, policy_diagnostics=False):
    a, b = Package(before), Package(after, variant)
    require((b.h[17], b.h[18]) == (len(before), a.h[3]), "source provenance mismatch")
    if side is not None:
        policy_header(side, a, policy_diagnostics=policy_diagnostics)
        policy_header(side, b, policy_diagnostics=policy_diagnostics)
    for name in ("mesh", "palette", "part_lod", "cluster", "class", "rule"):
        require(a.sections.get(name) == b.sections.get(name), "identity table changed: "+name)
    require(len(a.parts) == len(b.parts) and len(a.levels) == len(b.levels), "part/level identity")
    for x, y in zip(a.parts, b.parts):
        require(x[:6]+x[8:] == y[:6]+y[8:], "source part/UV/material identity")
    for i, (x, y) in enumerate(zip(a.levels, b.levels)):
        require(a.sections["level"][12*i+8:12*i+12] == b.sections["level"][12*i+8:12*i+12], "LOD error changed")
        old = [[m["vertices"][k] for k in s] for m in a.lets[x[0]:x[0]+x[1]] for s in m["strips"]]
        new = [[m["vertices"][k] for k in s] for m in b.lets[y[0]:y[0]+y[1]] for s in m["strips"]]
        require(old == new, "ordered LOD strip corners changed")
    # Parts also cover geometry of packages with no LOD clusters.
    for x, y in zip(a.parts, b.parts):
        old = [[m["vertices"][k] for k in s] for m in a.lets[x[6]:x[6]+x[7]] for s in m["strips"]]
        new = [[m["vertices"][k] for k in s] for m in b.lets[y[6]:y[6]+y[7]] for s in m["strips"]]
        require(old == new, "ordered part strip corners changed")
    if before_groups is not None:
        require(after_groups is not None, "missing mapped R4SG")
        parse_groups(before_groups, a, side, policy_diagnostics=policy_diagnostics)
        parse_groups(after_groups, b, side, policy_diagnostics=policy_diagnostics)
    else:
        require(after_groups is None, "unexpected R4SG")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mesh", type=Path); ap.add_argument("policy", type=Path)
    choice = ap.add_mutually_exclusive_group(required=True)
    choice.add_argument("--scenery-local-indexed", action="store_true")
    choice.add_argument("--scenery-direct-strips", action="store_true")
    ap.add_argument("--source-groups", type=Path)
    ap.add_argument("--policy-diagnostics", type=int, choices=(0, 1), nargs="?", const=1, default=0,
                    help="include exact policy/group header fields in refusals; admission is unchanged")
    ap.add_argument("--out", type=Path, required=True, help="new output directory; source files stay unchanged")
    args = ap.parse_args()
    variant = "local-indexed" if args.scenery_local_indexed else "direct-strips"
    m, g, report = convert(args.mesh.read_bytes(), variant, args.policy.read_bytes(),
                           args.source_groups.read_bytes() if args.source_groups else None,
                           policy_diagnostics=bool(args.policy_diagnostics))
    args.out.mkdir(parents=True, exist_ok=False)
    files = {STEMS[variant]+".re4mesh": m}
    if g is not None:
        files[STEMS[variant]+".r4sg"] = g
    for name, data in files.items():
        (args.out/name).write_bytes(data)
    report.update(source_mesh=str(args.mesh), source_policy=str(args.policy),
                  source_policy_sha256=sha(args.policy.read_bytes()),
                  source_groups=str(args.source_groups) if args.source_groups else None)
    (args.out/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    (args.out/"SHA256SUMS").write_text("".join(sha(data)+"  "+name+"\n" for name, data in files.items()))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

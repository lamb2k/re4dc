"""Read-only adapters for Build 29; no private files or optional dependencies.

Layouts remain owned by le_mirror/model_registry/pl08_pack/convert_room_bins/
texpack. These readers check extents and checksums before returning inventory;
they do not certify all of the runtime's source-identity/admission contracts.
"""
import hashlib
import math
import struct
import zlib


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def span(data, offset, size, label="span", alignment=1):
    require(isinstance(offset, int) and isinstance(size, int) and offset >= 0 and size >= 0
            and offset % alignment == 0 and offset <= len(data) and size <= len(data) - offset,
            f"{label}: range/alignment {offset}+{size}/{len(data)}")
    return data[offset:offset + size]


def unpack(fmt, data, offset=0, label="record"):
    return struct.unpack(fmt, span(data, offset, struct.calcsize(fmt), label))


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def fnv(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def sha(data):
    return hashlib.sha256(data).hexdigest()


def key_text(key):
    return "%08x-%08x" % tuple(key)


def excess_bits(values):
    """native_actor_fast.cpp Converter::track_uv, including trailing zeros."""
    result = 0
    for value in values:
        n = abs(value)
        if n:
            n //= n & -n
            result = max(result, n.bit_length() - 8)
    return result


def parse_actor_blob(data, positions, normals, uv_count, allow_extensions=False):
    """FE/v3 level-zero cast stream, from coarse_actor_preflight.h."""
    h = unpack("<4B6H4f", data, label="actor header")
    require(h[0:2] == (0xfe, 3), "unsupported actor blob")
    flags, levels, count, color, rec4, idx4, lod4, bake4 = h[2:10]
    require(not flags & 0x80 and not levels and not lod4,
            "cast FE/v3 pending/LOD stream needs its own adapter")
    require(allow_extensions or not flags & 3 and not bake4,
            "cast FE/v3 CI/bake extension outside preflight contract")
    require(bool(flags & 2) == bool(bake4), "actor bake flag/offset")
    require(all(math.isfinite(v) for v in h[10:]) and h[-1] >= 0, "actor bounds")
    require(0 < count <= (len(data) - 32) // 8, "actor meshlet count")
    rec, idx = rec4 * 4, idx4 * 4
    require(rec >= 32 + 8 * count and rec <= idx <= len(data), "actor record/index order")
    stride = 3 + bool(flags & 1) + bool(flags & 2)
    lets, expected_first, last_index, all_records = [], 0, 0, []
    for i in range(count):
        counts, first, offset = unpack("<IHH", data, 32 + 8 * i, "actor meshlet")
        nv, ni, nt = counts & 255, counts >> 8 & 4095, counts >> 20
        require(0 < nv <= 128 and 0 < ni <= (2048 if allow_extensions else 1024) and first == expected_first,
                "actor meshlet counts/record partition")
        require(rec + (first + nv) * stride * 2 <= idx, "actor records overlap index table")
        records = [unpack("<" + "H" * stride, data, rec + stride * 2 * (first + j), "actor corner") for j in range(nv)]
        require(all(r[0] < positions and r[1] < normals and r[2] < uv_count for r in records),
                "actor corner outside arrays")
        indices = span(data, idx + offset, ni, "actor strip indices")
        run = triangles = 0
        for b in indices:
            require((b & 127) < nv, "actor local index")
            run += 1
            require(allow_extensions or run <= 64, "cast actor strip exceeds preflight capacity")
            if b & 128:
                require(run >= 3, "actor strip shorter than triangle")
                triangles += run - 2
                run = 0
        require(not run and triangles == nt, "actor strip termination/triangle count")
        require(offset >= last_index and (allow_extensions or offset == last_index),
                "actor overlapping/out-of-order/noncontiguous index spans")
        lets.append(dict(index=i, vertices=nv, corners=ni, triangles=nt, records=records,
                         cone_stored=False, record_offset=rec + first * stride * 2,
                         chunk_unique=all(a[0] != b[0] for a, b in zip(records, records[1:])),
                         chunk_normal_unique=len({r[1] for r in records}) == nv))
        all_records.extend(records)
        expected_first += nv
        last_index = offset + ni
    bake = None
    if bake4:
        require(bake4 * 4 >= idx + last_index, "bake block overlaps indices")
        b = unpack("<2I28f", data, bake4 * 4, "BakeBlock")
        require(all(math.isfinite(v) for v in b[2:]), "BakeBlock nonfinite")
        bake = dict(state=b[0], clamped=b[1], dir=list(b[2:14]), color=list(b[14:]),
                    fallback29=b[0] == 0x46423290 and b[1] & ~3 == 0xf0290000 and bool(b[1] & 3) and b[-1] == 291.0)
    return dict(meshlets=lets, vertices=expected_first, corners=sum(x["corners"] for x in lets),
                triangles=sum(x["triangles"] for x in lets), uv_excess=(flags >> 2) & 31,
                vertex_colors=bool(flags & 1), blob_flags=flags, cone_status="runtime-generated",
                stored_records=all_records, constant_color=color, bake=bake)


def parse_model_bin(data, source="BIN"):
    """Little-endian ModelData arrays, original big-endian GX command words.

    PS2 objects retain this layout after ps2_objects.py and le_mirror.py.
    Material RGB, TEV scale, light count and normal basis are runtime state.
    """
    require(len(data) >= 64, "short ModelData")
    word = lambda at: unpack("<I", data, at)[0]
    half = lambda at: unpack("<H", data, at)[0]
    version, flags = word(60), word(32)
    require(version in (0x20010801, 0x20030818), "unsupported/non-native ModelData version")
    if version == 0x20030818:
        span(data, 0, 72, "ModelData v2 header")
    pos_at, nrm_at, uv_at, color_at = word(48), word(52), word(16), word(12)
    nv, nn, nparts, joints = half(56), half(58), half(26), data[25]
    require(data[40] <= 31, "position shift")
    span(data, pos_at, nv * 8, "positions", 2)
    nstride = 4 if flags & 0x20000000 else 8
    span(data, nrm_at, nn * nstride, "normals", 2)
    span(data, word(0), joints * 16, "joint heads", 4)
    weights = half(42) if half(42) > 255 else data[24]
    wstride = 12 if half(42) > 255 else 8
    wb = span(data, word(20), weights * wstride, "weights", 2)
    for i in range(weights):
        n = unpack("<H", wb, i * wstride + 6)[0] if wstride == 12 else wb[i * wstride + 3]
        require(1 <= n <= 3, "weight influence count")
    cursor, parts = word(28), []
    require(cursor >= (72 if version == 0x20030818 else 64), "part table overlaps header")
    boundaries = [v for v in (word(0),color_at,uv_at,word(20),cursor,word(44),pos_at,nrm_at,len(data)) if v > 0]
    def array_end(at):
        return min((v for v in boundaries if v > at), default=len(data))
    stride = 8 if flags & 0x80000000 else 6
    for pi in range(nparts):
        header = span(data, cursor, 32, "ModelPart", 4)
        length, declared_tris = unpack("<II", header, 24)
        stream = span(data, cursor + 32, length, "GX stream")
        q, records, triangles, primitives, unsupported, primitive_records = 0, [], 0, 0, [], []
        actor_blob = None
        if stream[:2] == b"\xfe\x03":
            # UV extent is checked on every referenced index below; unlike the
            # cast preflight the source model does not store a UV array count.
            actor_blob = parse_actor_blob(stream,nv,nn,max(0,(array_end(uv_at)-uv_at)//4),allow_extensions=True)
            for r in actor_blob["stored_records"]:
                records.append((r[0],r[1],r[3] if actor_blob["blob_flags"] & 1 else actor_blob["constant_color"],r[2])
                               if stride == 8 else (r[0],r[1],r[2]))
            triangles = actor_blob["triangles"]
            q = len(stream)
        while q < len(stream):
            opcode = stream[q]
            q += 1
            if opcode == 0:
                continue
            require(opcode in (0x80, 0x90, 0x98, 0xa0, 0xa8, 0xb0, 0xb8),
                    f"unknown GX opcode {opcode:#x}")
            n = unpack(">H", stream, q, "GX count")[0]
            q += 2
            span(stream, q, n * stride, "GX primitive")
            corners = [unpack(">" + "H" * (stride // 2), stream, q + j * stride) for j in range(n)]
            require(all(r[0] < nv and r[1] < nn for r in corners), "GX vertex/normal reference")
            require(opcode != 0x80 or n % 4 == 0, "quad count")
            require(opcode != 0x90 or n % 3 == 0, "triangle count")
            if opcode == 0x80:
                triangles += n // 2
            elif opcode == 0x90:
                triangles += n // 3
            elif opcode in (0x98, 0xa0):
                require(n >= 3, "triangle strip/fan count")
                triangles += n - 2
            else:
                unsupported.append(opcode)
            records.extend(corners)
            primitive_records.append(dict(opcode=opcode, records=corners))
            primitives += 1
            q += n * stride
        tids = sorted({r[-1] for r in records})
        require(not tids or uv_at >= 64 and uv_at + (max(tids)+1)*4 <= array_end(uv_at), "UV reference crosses declared array boundary")
        uvs = [unpack("<2h" if stride == 8 else "<2H", data, uv_at + 4 * t, "UV") for t in tids]
        cids = sorted({r[2] for r in records}) if stride == 8 else []
        require(not cids or color_at >= 64 and color_at + (max(cids)+1)*4 <= array_end(color_at), "colour reference crosses declared array boundary")
        colors = [list(span(data, color_at + 4 * c, 4, "colour")) for c in cids]
        parts.append(dict(index=pi, offset=cursor, stream_offset=cursor + 32, stream_bytes=length,
                          material_raw=header[11:24].hex(), material_flags=header[11], texture_index=header[12],
                          alpha_texture_index=header[14], alpha_ref=header[20], records=records,
                          source_key_texture_bytes=[header[12],header[14] if header[11] & 4 else 255],
                          vertices=len(set(records)), positions=len({r[0] for r in records}),
                          vertex_basis="stored FE records" if actor_blob else "unique source corner tuples; runtime meshlet duplication unknown",
                          corners=len(records), triangles=triangles, declared_triangles=declared_tris,
                          primitives=primitives, meshlets=actor_blob["meshlets"] if actor_blob else [],
                          uv_excess=excess_bits(v for uv in uvs for v in uv), bake=actor_blob["bake"] if actor_blob else None,
                          primitive_records=primitive_records,
                          vertex_colors=bool(stride == 8), colors=colors, model_flags=flags,
                          color_indices=cids, uv_indices=tids, legacy_opcodes=sorted(set(unsupported)),
                          cone_status="runtime-generated", signed_uv=bool(stride == 8)))
        if actor_blob:
            parts[-1].update(vertices=actor_blob["vertices"],corners=actor_blob["corners"])
        cursor += 32 + length
    return dict(key=source, name=source, kind="ModelData", flags=flags, version=version,
                position_count=nv, normal_count=nn, joints=joints, weights=weights,
                morph=bool(word(44)), position_shift=data[40], model_id=None, parts=parts,
                source_sha256=sha(data), source_bytes=len(data), source_offset=0, source_length=len(data), part_table=word(28),
                positions_offset=pos_at, normals_offset=nrm_at, colors_offset=color_at, uv_offset=uv_at)


CONTAINER_MAGIC = b"\xca\xb6\xbe\x20" * 8
DRS_MAGIC = bytes.fromhex("836e834a835a82cc8341837a815b815b815b815b815b815b815b814981498149")


def parse_esl(data, source="ESL"):
    """Native EmListData (include/em_set.h, le_mirror.py fmt_esl).

    A list can be a story-dependent alternative. Presence establishes a spawn
    candidate, never a current actor, source model or active room membership.
    """
    require(0 < len(data) <= 0x2000 and len(data) % 0x20 == 0, "ESL record extent")
    rows = []
    for at in range(0, len(data), 32):
        row = data[at:at + 32]
        if row[1] == 0:
            continue
        flags, hp = unpack("<IH", row, 4)
        pos = unpack("<3h", row, 12)
        rot = unpack("<3h", row, 18)
        room, guard = unpack("<Hh", row, 24)
        rows.append(dict(location=source, index=at // 32, room=room, enemy_id=row[1],
            type=row[2], set=row[3], be_flag=row[0], flags=flags, hp=hp,
            emset_no=row[10], character=row[11], position=[v * 10 for v in pos],
            rotation_raw=list(rot), guard_radius=guard * 1000,
            status="inventory", active="unknown; story-selected list and live game state required"))
    return rows


def tagged_entries(data):
    n = unpack("<I", data)[0]
    require(0 < n <= 8192 and 16 + 8 * n <= len(data), "tagged archive header/count")
    offsets = unpack("<" + "I" * n, data, 16)
    start = 16 + 8 * n
    require(all(start <= o < len(data) for o in offsets), "tagged archive offset")
    cuts = sorted(set(offsets) | {len(data)})
    ends = dict(zip(cuts, cuts[1:]))
    return [(span(data, 16 + 4 * n + 4 * i, 4, "tag"), o, ends[o]) for i, o in enumerate(offsets)]


def parse_room_archive(data, source="archive"):
    """Native DAR/DRS or tagged archive; BIN, SMD and named ETM members.

    Never decode arbitrary bytes or a source-endian compressed room as native.
    Returns model identities with absolute byte offsets for owner attribution.
    """
    models, references, notes, spawns = [], [], [], []

    def add_bin(payload, at, end, label, base, placements=None):
        m = parse_model_bin(span(payload, at, end - at), label)
        m.update(source_offset=base + at, source_length=end - at)
        if placements is not None:
            m["placements"] = placements
        models.append(m)

    def etc(payload, label, base):
        n = unpack("<I", payload)[0]
        require(n <= (len(payload) - 32) // 64, "ETM count")
        at = 32
        for i in range(n):
            length = unpack("<I", payload, at)[0]
            require(length >= 64, "ETM member length")
            member = span(payload, at, length, "ETM member")
            raw_name = member[32:64]
            require(b"\0" in raw_name, "ETM unterminated name")
            name = raw_name.split(b"\0", 1)[0].decode("ascii")
            if name.lower().endswith(".bin"):
                add_bin(member, 64, len(member), label + "/" + name, base + at)
            at += length

    def smd(payload, label, base):
        span(payload, 0, 16, "SMD header")
        count = unpack("<H", payload, 2)[0]
        table, tpl_table, mot_table = unpack("<3I", payload, 4)
        work = 16
        if payload[1] & 1:
            groups = unpack("<I", payload, 16)[0]
            span(payload, 20, groups * 4, "SMD groups")
            work = 20 + groups * 4
        span(payload, work, 72 * count, "SMD placements")
        placements = {}
        for i in range(count):
            at = work + 72 * i
            bin_id, tpl_id, motion, ident = payload[at + 36:at + 40]
            flags = unpack("<I", payload, at + 68)[0]
            floats = unpack("<9f", payload, at)
            require(all(math.isfinite(v) for v in floats), "nonfinite SMD placement")
            if ident != 255 and not flags & 16:
                placements.setdefault(bin_id, []).append(dict(index=i, object_id=ident, texture=tpl_id,
                    motion=motion, position=list(floats[:3]), scale=list(floats[6:]), flags=flags))
        if not placements:
            return
        n = max(placements) + 1
        offsets = [table + x for x in unpack("<" + "I" * n, payload, table, "SMD BIN offsets")]
        end = min([x for x in (tpl_table, mot_table, len(payload)) if x > table])
        require(all(table + n * 4 <= x < end for x in offsets), "SMD BIN range")
        cuts = sorted(set(offsets) | {end})
        ends = dict(zip(cuts, cuts[1:]))
        for i in sorted(placements):
            add_bin(payload, offsets[i], ends[offsets[i]], label + f"/BIN[{i}]", base, placements[i])

    def archive(payload, label, base):
        entries = tagged_entries(payload)
        for i, (tag, start, end) in enumerate(entries):
            tag = tag.rstrip(b"\0")
            part = span(payload, start, end - start)
            entry = label + f"/ARC[{i + 4:#x}]"
            if tag == b"BIN":
                add_bin(payload, start, end, entry, base)
            elif tag == b"ETM":
                etc(part, entry, base + start)
            elif tag == b"SMD":
                smd(part, entry, base + start)
            elif tag == b"ESL":
                spawns.extend(parse_esl(part, entry))
        # Native texture references can also occur in TPL/ETM/SMD tables.
        for magic in (b"R4NREF\0\0", b"R4PREF\0\0"):
            at = payload.find(magic)
            while at >= 0:
                rec = unpack("<8s6I", payload, at, "native texture reference")
                references.append(dict(key=key_text(rec[1:3]), width=rec[3], height=rec[4],
                    format=rec[5], palette=magic.startswith(b"R4P"), location=label + f"@{at:#x}"))
                at = payload.find(magic, at + 8)

    if data[:32] in (CONTAINER_MAGIC, DRS_MAGIC):
        span(data, 0, 0x400, "DVD container header")
        payloads, terminated = 0, False
        for at in range(32, 0x400, 32):
            kind, size, dest, offset = unpack("<4I", data, at)
            if kind == 0xffffffff:
                terminated = True
                break
            if kind == 0:
                require(offset >= 0x400 and not dest, "native type-0 destination/offset")
                archive(span(data, offset, size, "DVD payload"), source + f"/DVD[{at // 32 - 1}]", offset)
                payloads += 1
        require(terminated and payloads, "DVD native type-0 payload/terminator absent")
    else:
        archive(data, source, 0)
    return dict(models=models, texture_references=references, notes=notes, spawn_records=spawns)


PACK_KINDS = ("desc", "ref", "geom", "blob", "tex", "parents", "bind", "fmodel", "fpart", "ftex", "role", "sblob")
PACK_SIZES = (48, 16, 64, 1, 16, 1, 48, 96, 32, 68, 32, 32)


def parse_registry(data):
    h = unpack("<8s14I", data, label="RE4NMR header")
    require(h[0] == b"RE4NMR1\0" and h[1] in (1, 2) and h[2] == 64 and h[3] == len(data)
            and h[4:6] == (12, 64), "RE4NMR header/version/size")
    head = bytearray(data[:64]); struct.pack_into("<I", head, 44, 0)
    require(crc(head) == h[10] and crc(data[64:]) == h[8] and fnv(data[64:]) == h[9], "RE4NMR checksum")
    require((h[1], h[13]) in ((1, 0), (2, 1)) and not h[14], "RE4NMR flags/reserved")
    sections, spans = {}, []
    for i, (name, stride) in enumerate(zip(PACK_KINDS, PACK_SIZES)):
        kind, at, size, n = unpack("<4I", data, 64 + i * 16, "RE4NMR section")
        require(kind == i + 1 and size == stride * n and at >= 256, "RE4NMR section kind/size")
        sections[name] = (span(data, at, size, name, 32), n)
        if size:
            spans.append((at, at + size))
    require(all(a[1] <= b[0] for a, b in zip(sorted(spans), sorted(spans)[1:])), "RE4NMR overlapping sections")
    blob = sections["blob"][0]
    geoms = []
    for i in range(sections["geom"][1]):
        g = unpack("<16I", sections["geom"][0], i * 64)
        nv, nn, npal, tris, size, uv_size, skin, bones = g[:8]
        require(0 < nv <= 65535 and 0 < nn <= 65535 and 0 < npal <= 256 and 0 < bones <= 256
                and uv_size > 0 and uv_size % 4 == 0 and not g[15], "RE4NMR geometry counts")
        arrays = [span(blob, at, sz, "RE4NMR geometry array", 32) for at, sz in zip(g[8:13],
            (nv * 8, nn * 8, uv_size, size, npal * 16))]
        require(crc(b"".join(arrays)) == g[13] and fnv(b"".join(arrays)) == g[14], "RE4NMR geometry digest")
        for j in range(npal):
            w = unpack("<4B3f", arrays[4], j * 16)
            require(1 <= w[3] <= 3 and all(b < bones for b in w[:w[3]])
                    and all(math.isfinite(f) and 0 <= f <= 1 for f in w[4:4+w[3]])
                    and abs(sum(w[4:4+w[3]]) - 1) <= 0.0001, "RE4NMR weights")
        require(all(unpack("<H", arrays[0], j * 8 + 6)[0] < npal for j in range(nv))
                and all(unpack("<H", arrays[1], j * 8 + 6)[0] < npal for j in range(nn)), "RE4NMR palette reference")
        geom = parse_actor_blob(arrays[3], nv, nn, uv_size // 4)
        require(geom["triangles"] == tris, "RE4NMR triangle count")
        geom.update(geometry_index=i, source_bytes=sum(map(len, arrays)), position_count=nv,
                    normal_count=nn, palette_count=npal, skin_bytes=skin, bones=bones, signed_uv=False,
                    material_flags=None, model_flags=None, colors=[], legacy_opcodes=[])
        geoms.append(geom)
    tex = [unpack("<4I", sections["tex"][0], i * 16) for i in range(sections["tex"][1])]
    refs = [unpack("<4I", sections["ref"][0], i * 16) for i in range(sections["ref"][1])]
    models = []
    for i in range(sections["desc"][1]):
        desc = span(sections["desc"][0], i * 48, 48)
        require(b"\0" in desc[:16], "RE4NMR descriptor name")
        name = desc[:16].split(b"\0", 1)[0].decode("ascii")
        appearance, model_id, bones, count, first, parent, bind, flags = unpack("<8I", desc, 16)
        require(count and first <= len(refs) and count <= len(refs) - first, "RE4NMR descriptor refs")
        parts = []
        for j, r in enumerate(refs[first:first + count]):
            require(r[0] < len(geoms) and r[1] < len(tex), "RE4NMR ref")
            part = dict(geoms[r[0]])
            require(part["bones"] == bones, "RE4NMR descriptor bones")
            t = tex[r[1]]
            part.update(index=j, source_info=r[2], texture_key=key_text(t[:2]), texture_width=t[2],
                        texture_height=t[3], mask_runs=r[3], material_raw=None)
            parts.append(part)
        models.append(dict(key=f"descriptor[{i}]/{name}", name=name, kind="RE4NMR", model_id=model_id,
                           appearance=appearance, descriptor_flags=flags, parts=parts, room=h[7],
                           source_sha256=sha(data), source_bytes=len(data)))
    # Identity facts describe source materials, not the replacement geometry or its SourceLighting.
    facts = [sections["fpart"][0][i*32:i*32+13].hex() for i in range(sections["fpart"][1])]
    return dict(models=models, source_material_facts=facts, room=h[7], sections={k: v[1] for k, v in sections.items()})


def parse_pl08(data):
    h = unpack("<8s7I", data)
    require(h[:3] == (b"RE4PL08\0", 1, 256) and h[3] == len(data) and h[4] == 3, "RE4PL08 header")
    head = bytearray(span(data, 0, 256)); struct.pack_into("<I", head, 32, 0)
    require(crc(head) == h[7] and crc(data[256:]) == h[5] and fnv(data[256:]) == h[6], "RE4PL08 checksum")
    require(not any(head[36:64]), "RE4PL08 reserved")
    parts = []
    for i in range(3):
        r = unpack("<16I", data, 64 + 64 * i)
        role, info, nv, nn, npal, tris, size, po, pb, no, nb, uo, ub, go, wo, reserved = r
        require(role == (0, 1, 8)[i] and not reserved and pb == nv*8 and nb == nn*8 and ub and ub % 4 == 0,
                "RE4PL08 chunk fields")
        for off, sz in ((po,pb), (no,nb), (uo,ub), (go,size), (wo,npal*16)):
            require(off >= 256, "RE4PL08 payload offset")
            span(data, off, sz, "RE4PL08 array", 32)
        part = parse_actor_blob(span(data, go, size), nv, nn, ub // 4)
        require(part["triangles"] == tris, "RE4PL08 triangles")
        part.update(index=role, source_info=info, texture_key=None, material_flags=None, material_raw=None,
                    model_flags=None, colors=[], legacy_opcodes=[], signed_uv=False)
        parts.append(part)
    return dict(key="pl08", name="pl08", kind="RE4PL08", model_id=0, parts=parts,
                source_sha256=sha(data), source_bytes=len(data))


def parse_world(mesh, policy):
    # Reuse the owning strict adapters. Physical layouts/lineage remain visible
    # in inventory; decoding for analysis never writes or changes source data.
    from pathlib import Path
    import importlib.util
    p = Path(__file__).resolve().parent.parent / "world_blender_roundtrip" / "package.py"
    spec = importlib.util.spec_from_file_location("fallback29_world_codec", p)
    codec = importlib.util.module_from_spec(spec); spec.loader.exec_module(codec)
    tools = p.parents[2]

    def reader(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
        return obj

    header = unpack("<4s19I", mesh, label="R4IM header")
    layout, lineage, repeats = "R4IM-v3", None, {}
    try:
        marker = header[19]
        if header[1] == 4 or header[1] == 2 or marker in (int.from_bytes(b"SLI1","little"),int.from_bytes(b"SDS1","little")):
            if header[1] in (2,4):
                adapter = reader("fallback29_split_codec", tools / "scenery_record_split.py")
                package = adapter.Package(mesh, allow_split=True)
                adapter.policy(policy, package)
                meshlets, tables = package.meshlets, package.tables
                commands = [dict(strips=[list(s[1:]) for s in package.strips(i)]) for i in range(len(meshlets))]
                layout = "R4IM-v4-split" if header[1] == 4 else "R4IM-v2"
                lineage = dict(source_bytes=header[19],source_crc=header[18]) if header[1] == 4 else None
            else:
                adapter = reader("fallback29_variant_codec", tools / "scenery_data_variants.py")
                variant = "local-indexed" if marker == int.from_bytes(b"SLI1","little") else "direct-strips"
                package = adapter.Package(mesh, variant=variant)
                adapter.policy_header(policy, package)
                meshlets = [m["row"] for m in package.lets]
                commands = [dict(strips=[list(s) for s in m["strips"]]) for m in package.lets]
                tables = dict(part_lod=package.part_lods,cluster=package.clusters,level=package.levels)
                layout = "SLI1" if variant == "local-indexed" else "SDS1"
                lineage = dict(source_bytes=header[17],source_crc=header[18])
            ph = codec.PW_HEAD.unpack_from(policy)
            doc = dict(meshes=package.meshes,parts=package.parts,meshlets=meshlets,commands=commands,
                part_lods=tables["part_lod"],clusters=tables["cluster"],levels=tables["level"],
                materials=codec.rows(policy,32,ph[3],codec.PW_PART,"materials"),
                placements=codec.rows(policy,32+16*ph[3],ph[2],codec.PW_PLACE,"placements"))
            require(all(m[7] <= 1 for m in doc["materials"]), "R4PW material reserved bits")
        elif marker == int.from_bytes(b"SDO3","little"):
            adapter = reader("fallback29_dedup_codec", p.parent.parent / "dedup_offline23" / "offline_dedup.py")
            package = adapter.Package(mesh, encoded=True)
            require(header[17] == 0, "SDO3 unknown reserved extension")
            # Decode repeats before applying ordinary geometry bounds/ownership
            # checks. Physical header CRC and all repeat tags were checked above.
            plain = bytearray(mesh)
            for i, let in enumerate(package.lets):
                if let["rep"]:
                    repeats[i] = let["rep"]
                    for j, vertex in enumerate(package.decoded(let)):
                        struct.pack_into("<6H",plain,header[13]+12*(let["fv"]+j),*vertex)
                    struct.pack_into("<H",plain,let["offset"]+14,let["sc"] & 127)
            struct.pack_into("<2I",plain,72,0,0)
            struct.pack_into("<I",plain,12,crc(plain[80:]))
            doc = codec.decode(bytes(plain), policy, preserve_index_layout=True)
            layout, lineage = "SDO3", dict(source_bytes=len(mesh),source_crc=header[18])
        else:
            doc = codec.decode(mesh, policy, preserve_index_layout=True)
    except (ValueError,struct.error) as exc:
        raise Invalid(str(exc)) from exc
    ownership = codec.owners(doc)
    models = []
    for mi, m in enumerate(doc["meshes"]):
        parts = []
        for pi in range(m[6], m[6] + m[7]):
            mat, part = doc["materials"][pi], doc["parts"][pi]
            lets = []
            for ji in range(part[6], part[6] + part[7]):
                record, command = doc["meshlets"][ji], doc["commands"][ji]
                lets.append(dict(index=ji, vertices=record[3], corners=sum(map(len, command["strips"])),
                    triangles=sum(len(s)-2 for s in command["strips"]), indexed=bool(record[4]&0x8000),
                    level=ownership[ji][4], strips=len(command["strips"]), max_strip=max(map(len,command["strips"]),default=0),
                    stored_position_repeats=repeats.get(ji,0)))
            level0 = [x for x in lets if x["level"] == 0]
            parts.append(dict(index=pi, meshlets=lets, vertices=sum(x["vertices"] for x in level0),
                corners=sum(x["corners"] for x in level0), triangles=sum(x["triangles"] for x in level0),
                texture_key=key_text(mat[:2]), texture_width=mat[2], texture_height=mat[3], pass_id=mat[4],
                vertex_basis="stored level-0 local vertices",
                cull=mat[5], texture_index=mat[6], vertex_alpha=bool(mat[7]&1), vertex_colors=True,
                material_flags=None, material_raw=None, model_flags=None, legacy_opcodes=[],
                uv_excess=None, signed_uv=False, cone_status="not-actor-path", colors=[],world_layout=layout))
        models.append(dict(key=f"mesh[{mi}]/bin[{m[0]}]", name=f"BIN {m[0]:#x}", kind="R4IM/R4PW",
            model_id=None, parts=parts, source_sha256=sha(mesh), policy_sha256=sha(policy),
            world_layout=layout,lineage=lineage,
            source_bytes=len(mesh)+len(policy), placements=[dict(index=i, source_group=p[1],
            affine=list(p[2:])) for i,p in enumerate(doc["placements"]) if p[0] == mi]))
    return dict(models=models, meshlets=len(doc["meshlets"]), parts=len(doc["parts"]), placements=len(doc["placements"]),
                layout=layout,lineage=lineage)


def parse_glod(data):
    """GLP1: glod_pack.py's streamed body/head rungs; hands remain in image."""
    h = unpack("<16I", data)
    magic, version, count, biggest, directory, file_bytes, checksum, apps = h[:8]
    require(magic == 0x31504c47 and version == 1 and 1 <= count <= 8 and 1 <= apps <= 64
            and file_bytes == len(data) and not any(h[8:]), "GLP1 header")
    record_size = 24 + 128 * apps
    require(directory == 64 + count * record_size and fnv(data[64:]) == checksum, "GLP1 directory/checksum")
    span(data, 64, count * record_size, "GLP1 directory")
    models, level_spans = [], []
    for level in range(count):
        at = 64 + level * record_size
        name = span(data, at, 8).rstrip(b"\0").decode("ascii")
        off32, size, skin, reserved = unpack("<4I", data, at + 8)
        require(not reserved and size <= biggest and off32 * 32 >= directory, "GLP1 level fields")
        blob = span(data, off32 * 32, size, "GLP1 level data", 32)
        level_spans.append((off32*32, off32*32+size))
        for app in range(apps):
            parts = []
            for role in range(2):
                r = unpack("<16I", data, at + 24 + (app*2+role)*64)
                rid, nv, nn, npal, tri, sb = r[:6]
                require(rid == role and 0 < npal <= 256 and r[11] == nv*8 and r[12] == nn*8
                        and r[13] > 0 and r[13] % 4 == 0 and r[14] == sb and r[15] == npal*16,
                        "GLP1 role/counts")
                arrays = [span(blob, off, sz, "GLP1 array", 32) for off,sz in zip(r[6:11],r[11:])]
                part = parse_actor_blob(arrays[3], nv, nn, r[13]//4)
                require(part["triangles"] == tri, "GLP1 triangle count")
                part.update(index=role, source_info=role, texture_key=None, material_flags=None,
                    material_raw=None, model_flags=None, colors=[], legacy_opcodes=[], signed_uv=False)
                parts.append(part)
            models.append(dict(key=f"level[{level}]/appearance[{app}]", name=f"Ganado appearance {app} {name}",
                kind="GLP1", model_id=None, actor_class="ganado", parts=parts, level=level,
                appearance=app, source_sha256=sha(data), source_bytes=len(data), hands_in_image=True))
    require(all(a[1] <= b[0] for a,b in zip(sorted(level_spans),sorted(level_spans)[1:])), "GLP1 level overlap")
    return dict(models=models, levels=count, appearances=apps)


def parse_compiled_header(data, source):
    """Read generated byte-array headers without executing C/C++ or Python."""
    import re
    text = data.decode("ascii")
    array_re = re.compile(r"alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};", re.S)
    arrays = {}
    for match in array_re.finditer(text):
        fields = [x.strip() for x in match[2].replace("\n", "").split(",") if x.strip()]
        require(all(re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|[0-9]+)",x) for x in fields), "generated header byte literal")
        try:
            arrays[match[1]] = bytes(int(x,0) for x in fields)
        except ValueError as exc:
            raise Invalid("generated header byte range") from exc
    prefixes = sorted(k[:-4] for k in arrays if k.endswith("_pos"))
    require(prefixes, "no generated cast byte arrays")
    parts = []
    for index, prefix in enumerate(prefixes):
        require(all(prefix+"_"+k in arrays for k in ("pos","nrm","uv","gx")), "generated cast array set")
        p,n,u,g = (arrays[prefix+"_"+k] for k in ("pos","nrm","uv","gx"))
        require(len(p)%8 == len(n)%8 == len(u)%4 == 0, "generated cast array alignment")
        part = parse_actor_blob(g,len(p)//8,len(n)//8,len(u)//4)
        part.update(index=index, source_info=prefix, texture_key=None, material_flags=None,
                    material_raw=None, model_flags=None, colors=[], legacy_opcodes=[], signed_uv=False)
        parts.append(part)
    return dict(key=source, name=source, kind="compiled-cast-header", model_id=None, parts=parts,
                source_sha256=sha(data), source_bytes=len(data))


def parse_texture(data):
    h = unpack("<8s10I", data)
    require(h[:3] == (b"RE4DCTX\0", 2, 48) and h[3] == 96 and h[4] and h[5] == 48, "texture metadata header")
    require(h[4] <= (len(data)-48)//96 and h[6] >= 48+96*h[4], "texture descriptor/data layout")
    span(data, h[6], h[7], "texture payload")
    if crc(data[48:]) == h[8]:
        crc_rule = "header"
    elif h[6]+h[7] == len(data) and crc(data[h[6]:]) == h[8]:
        crc_rule = "legacy-data"
    else:
        raise Invalid("texture payload checksum")
    entries = []
    for i in range(h[4]):
        w, ht, fmt, off, size, flags, payload, reserved = unpack("<8I", data, 48 + 96*i + 64)
        require(0 < w <= 4096 and 0 < ht <= 4096 and not reserved and off >= h[6]
                and off+size <= h[6]+h[7], "texture descriptor extent/dimensions")
        span(data,off,size,"texture descriptor bytes")
        entries.append(dict(index=i, width=w, height=ht, format=fmt, flags=flags, payload_type=payload,
                            bytes=size, palette=fmt in (3,4,5), mipmap=bool(flags&4)))
    return dict(entries=entries, crc_rule=crc_rule, sha256=sha(data), bytes=len(data))


def parse_texpak(data):
    # Existing writer's runtime-index validation, plus package checks and no aliases.
    from pathlib import Path
    import importlib.util
    p = Path(__file__).resolve().parent.parent / "texpack.py"
    spec = importlib.util.spec_from_file_location("fallback29_texpack", p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    try:
        count, _ = mod.verify(data)
    except SystemExit as exc:
        raise Invalid(str(exc)) from exc
    out, extents = {}, []
    for i in range(count):
        c, f, off, size = unpack("<4I", data, 2048 + 16*i)
        out[key_text((c,f))] = parse_texture(span(data,off,size))
        extents.append((off,off+size))
    require(all(a[1] <= b[0] for a,b in zip(sorted(extents),sorted(extents)[1:])), "tex.pak payload aliases/overlaps")
    return out


def parse_resident(data):
    require(len(data) % 512 == 0, "resident.bin size must be a whole 512-byte piece")
    out, seen, padded = [], set(), False
    for at in range(0,len(data),16):
        r,w,h,f,c,v = unpack("<4H2I",data,at)
        if not any((r,w,h,f,c,v)):
            padded = True
            continue
        require(not padded and w > 0 and h > 0, "resident.bin interior padding/size")
        require((r,c,v) not in seen, "resident.bin duplicate room/key")
        seen.add((r,c,v))
        out.append(dict(room=r,key=key_text((c,v)),width=w,height=h,format=f))
    require(out == sorted(out,key=lambda x:(x["room"],x["key"])), "resident.bin order")
    return out

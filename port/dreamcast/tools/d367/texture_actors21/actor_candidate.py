#!/usr/bin/env python3
"""Create explicit, source-bound actor mip replacements without changing a disc.

Game data, copied evidence and previews are private outputs. The input contract
pins each package and consumer proof; a label or a matching material name alone
never selects a texture. Existing VQ codebooks and full-resolution indices are
immutable. Mips are filtered/quantized candidates, not lossless lower levels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
import mipmap_vq as mip
import texpack
from vram.vq_pak import read_pak

SCHEMA = "re4dc-actor-mip-contract-1"
PROTECTED_GANADO = {
    "ebed7ba6-2ca7490f", "65c6fe5a-2593694e", "b4f70c44-1e5fd331",
    "df13f362-0ed8fbdd", "bbde9497-188ca895",
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def rounded(n, alignment):
    return (n + alignment - 1) // alignment * alignment


def parse_key(name):
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{8}", name):
        raise ValueError("invalid texture key: " + name)
    return tuple(int(s, 16) for s in name.split("-"))


def registry_sections(blob):
    if len(blob) < 64 or blob[:8] != b"RE4NMR1\0":
        raise ValueError("consumer proof is not a native model registry")
    h = struct.unpack_from("<14I", blob, 8)
    if h[0] not in (1, 2) or h[1] != 64 or h[2] != len(blob) or h[3:5] != (12, 64):
        raise ValueError("unsupported or truncated native model registry")
    sections = {}
    for i in range(h[3]):
        ident, offset, length, count = struct.unpack_from("<4I", blob, h[4] + 16 * i)
        if offset < 256 or offset + length > len(blob) or ident in sections:
            raise ValueError("invalid native model registry section")
        sections[ident] = (blob[offset:offset + length], count)
    return sections


def registry_binding(blob, key, dimensions):
    """Prove the key is used by a descriptor's primary geometry references."""
    sections = registry_sections(blob)
    tex, nt = sections[5]
    if len(tex) != 16 * nt:
        raise ValueError("bad registry texture table")
    selected = [i for i in range(nt) if struct.unpack_from("<4I", tex, i * 16)
                == (*parse_key(key), *dimensions)]
    if len(selected) != 1:
        raise ValueError("registry lacks a unique exact texture binding: " + key)
    refs, nr = sections[2]
    desc, nd = sections[1]
    geom, ng = sections[3]
    data, _ = sections[4]
    if len(refs) != nr * 16 or len(desc) != nd * 48 or len(geom) != ng * 64:
        raise ValueError("bad registry descriptor/reference/geometry table")
    owners, geometry = [], set()
    for i in range(nd):
        name = desc[i * 48:i * 48 + 16].split(b"\0", 1)[0].decode("ascii")
        words = struct.unpack_from("<8I", desc, i * 48 + 16)
        if words[4] + words[3] > nr:
            raise ValueError("registry descriptor reference range is truncated")
        hits = []
        for r in range(words[4], words[4] + words[3]):
            g, t, source, mask = struct.unpack_from("<4I", refs, r * 16)
            if t == selected[0]:
                if g >= ng:
                    raise ValueError("registry geometry index is invalid")
                geometry.add(g)
                hits.append(dict(reference=r, geometry=g, source=source, mask_word=mask))
        if hits:
            owners.append(dict(name=name, appearance=words[0], model_id=words[1], references=hits))
    if not owners:
        raise ValueError("registry declares the texture but no primary geometry uses it")
    uv = []
    for g in sorted(geometry):
        words = struct.unpack_from("<16I", geom, g * 64)
        # put_arrays writes pos/nrm/uv/gx/weights offsets relative to blob.
        at, length = words[10], words[5]
        if length % 4 or at + length > len(data):
            raise ValueError("registry UV array is truncated")
        uv.extend(struct.iter_unpack("<2H", data[at:at + length]))
    return dict(texture_index=selected[0], descriptors=owners,
                uv_entries=len(uv), uv_word_range=[min(min(p) for p in uv), max(max(p) for p in uv)] if uv else None,
                normalized_uv_bounds=[[min(p[c] for p in uv) / 32768,
                                       max(p[c] for p in uv) / 32768] for c in range(2)] if uv else None,
                uv_arrays_and_geometry_unchanged=True)


def leon_binding(proofs):
    needed = ("leon_draw", "leon_variants", "leon_recipe", "leon_default", "leon_mk")
    if any(p not in proofs for p in needed):
        raise ValueError("standard Leon binding lacks selected draw/variant/recipe proof")
    draw, variants, recipe, default, mk = (proofs[p].decode() for p in needed)
    if ("constexpr unsigned crc=0xec255e66U, fnv=0x76812316U;" not in draw
            or not re.search(r'\{"CUR",0xec255e66U,0x76812316U,', variants)
            or "PS2_LEON=1" not in recipe or "CHARBAKE_TOGGLE=1" not in recipe
            or not re.search(r"CHARBAKE_VARIANT\s*\?=\s*0", default)
            or "atlas ec255e66-76812316" not in mk):
        raise ValueError("selected standard Leon key/variant/recipe no longer matches")
    return dict(kind="standard-leon", appearance=256, boot_variant=0,
                boot_variant_label="CUR", key="ec255e66-76812316",
                conditional_variants_not_selected=True,
                hair_separate=True, runtime_selection_not_measured=True)


def leon_runtime_uv(header, mesh):
    """Bind source-mesh footprint evidence to the selected recipe's UV arrays."""
    rows = []
    for role in range(8):
        found = re.search(r"unsigned char i%d_uv\[\] = \{(.*?)\};" % role, header.decode(), re.S)
        if not found:
            raise ValueError("selected Leon runtime UV array is absent")
        values = [int(v) for v in re.findall(r"\d+", found.group(1))]
        if any(v > 255 for v in values) or len(values) % 4:
            raise ValueError("selected Leon UV array is not packed u16 pairs")
        actual = set(struct.iter_unpack("<2H", bytes(values)))
        expected = {tuple(round(x * 32768) for x in c["uv"])
                    for t in mesh["triangles"] if t["source_info"] == role for c in t["corners"]}
        if actual != expected or not actual:
            raise ValueError("source mesh UVs differ from selected Leon runtime role " + str(role))
        rows.append(dict(role=role, unique_uvs=len(actual), exact_quantized_uv_set=True))
    return dict(selected_runtime_sha256=sha(header), roles=rows,
                source_mesh_uvs_match_selected_runtime=True,
                convention="u16 little endian, normalized value / 32768; tile x=u*512, y=(1-v)*512")


def atlas_boundaries(tiles, mesh, side):
    """Conservative box-filter + bilinear footprint audit of actual mesh corners.

    Tile x/y follow the converter's source_uv_tiles layout. pack_arm.py uses
    x=u*512, y=(1-v)*512. A triangle within one rectangular tile is convex, so
    its extreme coordinates occur at corners. This is a source bound, not a
    measured screen derivative or a claim that every mip is selected at runtime.
    """
    rectangles = []
    for name, t in sorted(tiles.items()):
        x, y, w, h = (t[k] for k in ("x", "y", "width", "height"))
        if min(w, h) <= 0 or min(x, y) < 0 or x + w > side or y + h > side:
            raise ValueError("atlas tile is out of bounds")
        if w - t["inner_width"] != 4 or h - t["inner_height"] != 4:
            raise ValueError("expected the proven two-texel Leon gutter")
        for _, a, b, c, d in rectangles:
            if x < c and a < x + w and y < d and b < y + h:
                raise ValueError("atlas tiles overlap")
        rectangles.append((name, x, y, x + w, y + h))
    corners, unknown, crossing, triangles = [], [], 0, 0
    by_tile = {name: 0 for name, *_ in rectangles}
    for triangle in mesh["triangles"]:
        # PS2_LEON's role7 uses its separately owned hair colour/mask runs.
        if triangle["source_info"] == 7:
            continue
        triangles += 1
        owners = set()
        for c in triangle["corners"]:
            u, v = c["uv"]
            x, y = u * side, (1 - v) * side
            match = [r for r in rectangles if r[1] <= x < r[3] and r[2] <= y < r[4]]
            if len(match) != 1:
                unknown.append([x, y])
                continue
            rect = match[0]
            owners.add(rect[0])
            by_tile[rect[0]] += 1
            corners.append((x, y, rect))
        crossing += len(owners) > 1
    if unknown or crossing:
        raise ValueError(f"atlas mesh ownership failed: {len(unknown)} corners, {crossing} crossing triangles")
    levels = []
    for power in range(side.bit_length()):
        out_side = 1 << power
        scale = side // out_side
        bad = 0
        for x, y, (_, x0, y0, x1, y1) in corners:
            lo = [math.floor(x / scale - 0.5), math.floor(y / scale - 0.5)]
            # Both bilinear taps plus their source box footprints are contained
            # only when this rectangle stays within the owned tile, including
            # its existing gutters. No repeat across atlas tile edges is added.
            if (lo[0] * scale < x0 or (lo[0] + 2) * scale > x1 or
                    lo[1] * scale < y0 or (lo[1] + 2) * scale > y1):
                bad += 1
        mixed = 0
        for yy in range(out_side):
            for xx in range(out_side):
                x0, y0, x1, y1 = xx * scale, yy * scale, (xx + 1) * scale, (yy + 1) * scale
                hits, area = 0, 0
                for _, a, b, c, d in rectangles:
                    overlap = max(0, min(x1, c) - max(x0, a)) * max(0, min(y1, d) - max(y0, b))
                    hits += overlap > 0
                    area += overlap
                mixed += hits > 1 or (hits > 0 and area != scale * scale)
        levels.append(dict(side=out_side, source_box_side=scale,
                           corner_footprints_crossing_tile=bad, corners=len(corners),
                           box_cells_mixing_tile_owners=mixed,
                           sampler_acceptance="needs look and derivative evidence" if bad or mixed else "source footprint contained"))
    return dict(kind="atlas", tile_count=len(rectangles), gutter_texels=2,
                triangles=triangles, sampled_corners=len(corners), corner_counts=by_tile,
                hair_role7_excluded=True, all_body_triangles_within_one_tile=True,
                levels=levels, runtime_mip_adoption_accepted=False,
                limitation="Finite atlas gutters do not isolate every coarse mip. Full-chain candidate is for review; no sampler or default is changed.")


def build_candidate(pack, contract, proofs, *, enabled=False, engine="auto"):
    if contract.get("schema") != SCHEMA or contract.get("source_pack_sha256") != sha(pack):
        raise ValueError("actor contract schema or exact source pack mismatch")
    texpack.verify(pack)
    packages = read_pak(pack)
    if texpack.build(packages)[0] != pack:
        raise ValueError("source pack is not canonical or has duplicate keys")
    declarations = contract.get("proofs", [])
    if len({p["id"] for p in declarations}) != len(declarations):
        raise ValueError("duplicate proof identity")
    for proof in declarations:
        if proof["id"] not in proofs or sha(proofs[proof["id"]]) != proof["sha256"]:
            raise ValueError("pinned consumer proof mismatch: " + proof["id"])
    rows, replacements, selected = [], {}, set()
    for item in contract.get("textures", []):
        name = item["key"]
        key = parse_key(name)
        if key in selected or name in PROTECTED_GANADO:
            raise ValueError("duplicate or protected existing Ganado mip key: " + name)
        selected.add(key)
        if key not in packages or sha(packages[key]) != item["source_package_sha256"]:
            raise ValueError("selected normal-pack winner is absent or differs: " + name)
        before = mip.read_native_vq(packages[key])
        if before.mipmapped:
            raise ValueError("actor candidates require an existing base-only VQ package")
        if (before.texture[1], before.texture[2]) != tuple(item["dimensions"]):
            raise ValueError("selected actor dimensions differ")
        if item["binding"]["kind"] == "standard-leon" and name == "ec255e66-76812316":
            if item["dimensions"] != [512, 512]:
                raise ValueError("the selected standard Leon consumer requires its 512-square atlas")
            owner = leon_binding(proofs)
        elif item["binding"]["kind"] == "native-registry":
            owner = registry_binding(proofs[item["binding"]["proof"]], name, item["dimensions"])
        else:
            raise ValueError("unsupported actor consumer binding")
        if before.texture[3] != mip.tpl.FORMAT_RGB565:
            raise ValueError("alpha-bearing actor mips require a separate reviewed coverage policy")
        sampling = item.get("sampling", {})
        if sampling.get("kind") == "leon-atlas":
            tiles = json.loads(proofs[sampling["tiles_proof"]])["source_uv_tiles"]
            mesh = json.loads(proofs[sampling["mesh_proof"]])
            sampling = atlas_boundaries(tiles, mesh, before.size)
            sampling["runtime_uv_identity"] = leon_runtime_uv(proofs[item["sampling"]["runtime_proof"]], mesh)
        elif sampling.get("kind") == "owned-native-atlas":
            sampling = dict(sampling, runtime_mip_adoption_accepted=False,
                            limitation="Native UV words and atlas layout stay exact; coarse-level seam and derivative checks remain pending.")
        else:
            raise ValueError("actor sampler ownership policy is absent")
        result, row = mip.add_mipmaps(packages[key], enabled=enabled, engine=engine)
        after = mip.read_native_vq(result)
        if before.codebook != after.codebook or before.base_indices != after.base_indices:
            raise ValueError("actor full-resolution codebook or indices changed")
        row.update(key=name, owner=owner, sampling=sampling,
                   material=before.texture[0].split(b"\0", 1)[0].decode("ascii"),
                   alpha_policy="RGB565 opaque base and all mips; separate hair/mask packages unchanged",
                   source_flags=before.texture[6], candidate_flags=after.texture[6],
                   before_allocation_request=len(before.payload), after_allocation_request=len(after.payload),
                   before_alloc32=rounded(len(before.payload), 32), after_alloc32=rounded(len(after.payload), 32),
                   before_archive_slot=rounded(len(packages[key]), 2048), after_archive_slot=rounded(len(result), 2048))
        rows.append(row)
        replacements[key] = result
    if not rows:
        raise ValueError("actor candidate has no source-bound textures")
    unchanged = {k: sha(v) for k, v in packages.items() if k not in replacements}
    report = dict(schema="re4dc-actor-mip-candidate-1", candidate_only=True, enabled=enabled,
                  source_pack_sha256=sha(pack), source_pack_bytes=len(pack), packages=len(packages),
                  changed_keys=sum(r["changed"] for r in rows), textures=rows,
                  unselected_packages=len(unchanged),
                  unselected_identity_sha256=sha("\n".join("%08x-%08x %s" % (*k, v) for k, v in sorted(unchanged.items())).encode()),
                  protected_existing_ganado={name: sha(packages[parse_key(name)]) for name in sorted(PROTECTED_GANADO) if parse_key(name) in packages},
                  extra_allocation_request_bytes=sum(r["after_allocation_request"] - r["before_allocation_request"] for r in rows),
                  extra_alloc32_bytes=sum(r["after_alloc32"] - r["before_alloc32"] for r in rows),
                  lower_levels="box filtered premultiplied colour, nearest existing codebook; intentionally quantized",
                  required_build_knobs=["CAST_MIPMAP=1"] if enabled else [],
                  acceptance=dict(source_data=True, independent_decode=False, runtime_vram=False,
                                  runtime_look=False, gameplay=False, hardware_timing=False),
                  limitations=["Sparse replacements only; normal packed lookup wins over duplicate loose files.",
                               "Allocation totals are exact requests and 32-byte rounding, not measured peak/residency.",
                               "Atlas coarse levels require sampling/look review before adoption.",
                               "No new VQ encoding, runtime/build/default, SH4ZAM or SKIN_SH4ZAM change."])
    return replacements, report


def write_previews(before_blob, after_blob, directory):
    from PIL import Image, ImageDraw
    before, after = mip.read_native_vq(before_blob), mip.read_native_vq(after_blob)
    directory.mkdir()
    levels = []
    for power in reversed(range(after.size.bit_length())):
        side = 1 << power
        pixels = mip.decode_level(after, side)
        image = Image.frombytes("RGBA", (side, side), bytes(c for p in pixels for c in p))
        image.save(directory / f"mip-{side:04d}.png")
        levels.append((side, image))
    base = Image.frombytes("RGBA", (before.size, before.size), bytes(c for p in mip.decode_level(before, before.size) for c in p))
    base.save(directory / "source-base.png")
    ideal, old_side, quality = mip.decode_level(before, before.size), before.size, []
    for side, image in levels:
        while old_side > side:
            ideal = mip._halve(ideal, old_side)
            old_side //= 2
        actual = list(image.getdata())
        squared = sum((a[c] - b[c]) ** 2 for a, b in zip(actual, ideal) for c in range(3))
        mse = squared / (side * side * 3)
        quality.append(dict(side=side, rgb_rmse=math.sqrt(mse),
                            rgb_psnr_db=10 * math.log10(255 * 255 / mse) if mse else None,
                            maximum_rgb_error=max(abs(a[c] - b[c]) for a, b in zip(actual, ideal) for c in range(3)),
                            opaque_pixels=sum(p[3] == 255 for p in actual), pixels=side * side))
        if side != before.size:
            Image.frombytes("RGBA", (side, side), bytes(c for p in ideal for c in p)).save(directory / f"box-reference-{side:04d}.png")
    (directory / "quality.json").write_text(json.dumps(dict(reference="recursive rounded box-filtered original decoded base; no new VQ codebook",
                                                            lower_levels_intentionally_quantized=True, visual_acceptance=False,
                                                            levels=quality), indent=2) + "\n")
    cell, columns = 260, 5
    sheet = Image.new("RGB", (cell * columns, (math.ceil(len(levels) / columns) + 1) * 284), "#202429")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), "Private actor atlas mip candidate. Base/codebook/indices exact; filtered lower levels need look review.", fill="white")
    for i, (side, image) in enumerate(levels):
        x, y = i % columns * cell, 36 + i // columns * 284
        sheet.paste(image.resize((256, 256), Image.Resampling.NEAREST).convert("RGB"), (x, y))
        draw.text((x + 4, y + 260), f"{side} x {side}", fill="white")
    sheet = sheet.crop((0, 0, cell * columns, 36 + math.ceil(len(levels) / columns) * 284))
    sheet.save(directory / "contact-sheet.png")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-pack", type=Path, required=True)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--enable-mipmaps", action="store_true")
    ap.add_argument("--engine", choices=("auto", "python", "numpy"), default="auto")
    ap.add_argument("--previews", action="store_true")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("candidate output exists; use a new directory")
    contract = json.loads(a.contract.read_text())
    proofs = {p["id"]: Path(p["path"]).read_bytes() for p in contract["proofs"]}
    pack = a.source_pack.read_bytes()
    replacements, report = build_candidate(pack, contract, proofs, enabled=a.enable_mipmaps, engine=a.engine)
    a.out.mkdir(parents=True)
    (a.out / "inputs").mkdir()
    for p in contract["proofs"]:
        suffix = Path(p["path"]).suffix
        relative = "inputs/" + p["id"] + suffix
        (a.out / relative).write_bytes(proofs[p["id"]])
        p["original_path"], p["path"] = p["path"], relative
    (a.out / "contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    (a.out / "replacements").mkdir()
    (a.out / "originals").mkdir()
    originals = read_pak(pack)
    for key, blob in replacements.items():
        name = "%08x-%08x" % key
        (a.out / "replacements" / (name + ".re4tex")).write_bytes(blob)
        (a.out / "originals" / (name + ".re4tex")).write_bytes(originals[key])
        if a.previews and a.enable_mipmaps:
            write_previews(originals[key], blob, a.out / (name + "-previews"))
    (a.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(changed_keys=report["changed_keys"],
                          extra_alloc32_bytes=report["extra_alloc32_bytes"], out=str(a.out))))


if __name__ == "__main__":
    main()

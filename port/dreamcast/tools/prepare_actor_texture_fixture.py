#!/usr/bin/env python3
"""Prepare audited actor TPLs while retaining every other staged archive byte.

Uses the existing native texture converter, R4NREF records and NTR table. Source
big-endian data must normalize to the complete staged little-endian body before
any edit. Embedded REL, every FCV/SEQ/EFF/BIN and nested audio remain exact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile

import le_mirror as mirror
from convert_tpl import parse_tpl, build_package, MaterialBinding
from prepare_native_ui import image_identity, select_upload_only, compact_spans, native_identity_index

# Exact ARC numbers, not an automatic whole-file upload-only qualification.
# em18.cpp:250-262,558-620 passes these only to modelInit / ModInfoMgr.create.
# em3b.cpp:424,432 passes these only to modelInit. EFF textures stay resident.
# em35.cpp:895-913 body/limbs use ARC5; 5184 weak-point cObj00 uses ARC0x9C.
# em14 links the same em10.cpp/em10_tmpl.cpp model consumers as qualified
# em11/em12/em13/em15/em17 (config/G4BE08/modules.py). Only its top-level model
# TPLs are selected here; its EFF family is deliberately retained in full.
MODEL_TPL_ARCS = {
    # em3c.cpp em3cModelInit:1867-1914 body, chainmail and attached weapons.
    # Parasite TPL0x4C/0x57 and EFF stay resident and byte exact.
    "em3c.drs": (6, 8, 0xA, 0xD, 0xF),
    "em18.drs": (6, 8, 0xF), "em3b.drs": (5, 0xC),
    "em35.drs": (5, 0x9C),
    # pl14.cpp modelSet:203-215 and equipWeapon:1465 (body/head/gun).
    "pl14.drs": (5, 7, 15),
    "em14.drs": (163,356,488,490,497,509,513,526,528,530,532,534,536,
                 537,538,540,542,544,594,623,625,627,629,631,645),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def payload(data):
    slot = mirror.native_payload_slot(data)
    size, base = struct.unpack_from("<I4xI", data, slot + 4)
    return slot, base, bytearray(data[base:base + size])


def prepare(source, staged, destination):
    source, staged, destination = map(Path, (source, staged, destination))
    name = source.name.lower()
    if name not in MODEL_TPL_ARCS or staged.name.lower() != name:
        raise ValueError("actor has no audited texture-only contract")
    if destination.exists():
        raise FileExistsError(destination)
    file = "em/" + name
    original, baseline = source.read_bytes(), staged.read_bytes()
    converted = bytearray(original)
    references, palettes = [], []
    old_offset, old_tpl = mirror.OFFSET_OBSERVER, mirror.TPL_OBSERVER
    start = len(mirror.REPORT)
    mirror.OFFSET_OBSERVER = lambda f, field, base, value: references.append((field, base, value))
    mirror.TPL_OBSERVER = lambda f, off, data, context: palettes.append((off, data, context))
    try:
        mirror.convert_file(file, converted)
    finally:
        mirror.OFFSET_OBSERVER, mirror.TPL_OBSERVER = old_offset, old_tpl
    coverage = mirror.REPORT[start:]
    with tempfile.TemporaryDirectory() as tmp:
        required = Path(tmp) / "required.txt"
        required.write_text(file + "\n")
        bad = mirror.check_required(coverage, str(required))
    _, source_base, body = payload(converted)
    staged_slot, _, staged_body = payload(baseline)
    normalization_policy = "existing le_mirror whole-body conversion"
    if name == "pl14.drs":
        # The authoritative CH22 fixture predates the stricter FCV decoder. Its
        # unused 32-byte ARC0xC has only a header and 0xCD padding; preserve the
        # exact historical header bytes, without claiming its invalid key data
        # became qualified. Its already stripped REL remains a 64-byte static
        # descriptor. Both complete source/staged identities are pinned here.
        if sha(original) != "2b5b554d45a67f12612474a9ed0a1bbeb7cf5882d16a7c67ce7ff25018676f27" or \
           sha(baseline) != "50c5c8cbdd589b4a8bb3154dcd46af78a52d30fc90185e82366376e805af6a95":
            raise ValueError("pl14 historical fixture identity differs")
        expected_error = "em/pl14.drs:0#8: error: joint 0 (kind 0x0004, parts 1) key block at 0x10 lies in the 0xCD padding"
        if bad != [expected_error]:
            raise ValueError("pl14 source qualification changed")
        count, rel = struct.unpack_from("<2I", body)
        dummy = struct.unpack_from("<I", body, 16+8*4)[0]
        if sha(body[dummy:dummy+32]) != "df94c556b1beb0bd7ac4449f9d597d81f53840a50b4c34f9a2dc7d5b8452449f":
            raise ValueError("pl14 retained dummy FCV changed")
        body[dummy:dummy+32] = bytes.fromhex("a0150104000100002000000010000000cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd")
        if len(body)-rel != 30624 or struct.unpack_from("<I",body,rel)[0] != 66 or \
           struct.unpack_from("<2I",body,rel+28) != (3,16):
            raise ValueError("pl14 source static REL changed")
        descriptor = bytearray(64)
        struct.pack_into("<I", descriptor, 0, 66)
        struct.pack_into("<2I", descriptor, 28, mirror.STATIC_REL_VERSION, 16)
        body = body[:rel] + descriptor
        normalization_policy = "pinned CH22 pl14 baseline: retained legacy dummy FCV header and existing static REL descriptor"
    elif bad:
        raise ValueError("unqualified actor archive: " + ", ".join(bad))
    if body != staged_body:
        raise ValueError("normalized source body differs from staged body")
    count, rel = struct.unpack_from("<2I", body)
    boundary = rel or len(body)
    offsets = struct.unpack_from("<%dI" % count, body, 16)
    tags = [bytes(body[16 + count*4 + i*4:20 + count*4 + i*4]) for i in range(count)]
    if b"NTR\0" in tags:
        raise ValueError("archive is already texture prepared")
    indices = MODEL_TPL_ARCS[name]
    if any(i < 4 or i >= count+4 or tags[i-4] != b"TPL\0" for i in indices):
        raise ValueError("audited model TPL ordinal changed")
    contexts = {file + ":0#" + str(i-4) for i in indices}
    local_palettes = [(o-source_base, d, c) for o, d, c in palettes
                      if source_base <= o < source_base+boundary]
    if {c for _, _, c in local_palettes if c in contexts} != contexts:
        raise ValueError("audited model TPL was not observed")
    # Fresh destination only; no accepted package or staged archive is overwritten.
    destination.mkdir(parents=True)
    textures = destination / "textures"
    textures.mkdir()
    source_images, known = [], {}
    for off, raw, context in local_palettes:
        if context not in contexts:
            continue
        for image_index, image in enumerate(parse_tpl(raw)):
            key, identity = image_identity(image)
            blob, _ = build_package([image], [MaterialBinding("source", 0, None)],
                twiddle=True, pad_to_power_of_two=True, source_intensity_alpha=True)
            if key in known and known[key] != (sha(identity), sha(blob)):
                raise ValueError("source texture identity collision")
            known[key] = (sha(identity), sha(blob))
            (textures / (key + ".re4tex")).write_bytes(blob)
            source_images.append(dict(context=context, image=image_index, key=key,
                source_sha256=sha(identity), native_sha256=sha(blob), native_bytes=len(blob)))
    ranges, selected, retained = select_upload_only(body, local_palettes, textures, lambda c: c in contexts)
    if not ranges:
        raise ValueError("no eligible model texture payloads")
    first = min(o for o in offsets if o)
    growth = (max(0, 16+8*(count+1)-first)+31) & ~31
    local_refs = [(f-source_base, b-source_base, v) for f,b,v in references
                  if source_base <= f < source_base+boundary]
    if rel:
        local_refs.append((4, 0, rel))
    out, mapped = compact_spans(body, local_refs,
        ([(first, first, bytes(growth))] if growth else []) + ranges)
    if any(struct.unpack_from("<I",out,16+4*i)[0] != (mapped(o) if o else 0) for i,o in enumerate(offsets)):
        raise ValueError("archive ordinal rebasing failed")
    preserved = []
    for off in sorted(set(offsets)-{0}):
        end = min([o for o in offsets if o>off] + [boundary])
        slots = [i for i,o in enumerate(offsets) if o==off]
        if any(off <= a < end for a,b,record in ranges):
            if any(i+4 not in indices for i in slots):
                raise ValueError("texture edit entered unaudited ordinal")
            continue
        if out[mapped(off):mapped(end)] != body[off:end]:
            raise ValueError("non-texture ordinal changed")
        preserved.append(dict(arc_indices=[i+4 for i in slots], tags=[tags[i].rstrip(b"\0").decode() for i in slots],
                              bytes=end-off, sha256=sha(body[off:end])))
    new_rel = mapped(boundary)
    table_bytes = (32+12*len(selected)+31)&~31
    final_bytes = len(out)+table_bytes
    table = native_identity_index(selected, mapped, len(body), final_bytes)
    out = out[:new_rel] + table + out[new_rel:]
    struct.pack_into("<2I", out, 0, count+1, new_rel+len(table) if rel else 0)
    struct.pack_into("<I", out, 16+4*count, new_rel)
    out[16+4*(count+1):16+8*(count+1)] = b"".join(tags + [b"NTR\0"])
    if rel and out[new_rel+table_bytes:] != body[rel:]:
        raise ValueError("embedded REL changed")
    packaged = mirror.replace_native_payload(baseline, out)
    if packaged[:staged_slot] != baseline[:staged_slot] or packaged[staged_slot+16:len(baseline)] != baseline[staged_slot+16:]:
        raise ValueError("staged container/audio bytes changed")
    (destination/name).write_bytes(packaged)
    (destination/(source.stem+".arc")).write_bytes(out)
    manifest = {"contract":"audited-actor-texture-fixture-v1", "actor":source.stem,
        "source_sha256":sha(original), "staged_sha256":sha(baseline),
        "output_sha256":sha(packaged), "output_bytes":len(packaged),
        "original_body_bytes":len(body), "resident_body_bytes":len(out),
        "header_growth_bytes":growth, "audited_tpl_arcs":list(indices),
        "source_normalized_body_matches_staged":True, "normalization_policy":normalization_policy,
        "preserved_ordinals":preserved,
        "embedded_rel_bytes":len(body)-rel if rel else 0,
        "embedded_rel_sha256":sha(body[rel:]) if rel else None,
        "container_audio_unchanged_except_payload_entry":True,
        "motions":"all source FCV and SEQ remain resident and byte identical",
        "source_images":source_images, "selected_textures":selected, "retained_textures":retained,
        "qualification":coverage, "runtime_qualified":False,
        "limits":"offline source and transport checks; runtime admission and visible output need a fresh run"}
    (destination/"fixture-report.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",required=True,type=Path)
    parser.add_argument("--staged",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    result=prepare(args.source,args.staged,args.output)
    print(json.dumps({k:result[k] for k in ("actor","original_body_bytes","resident_body_bytes","output_sha256")}))

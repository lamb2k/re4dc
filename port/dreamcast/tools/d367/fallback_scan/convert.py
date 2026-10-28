#!/usr/bin/env python3
"""Build 29: source-bound ModelData GX -> FE/v3 RGB565 bake, default OFF.

Every byte outside selected existing stream allocations is preserved. This is
an adapter for source-path converted PS2 ModelData, not a registry certificate
rewriter. See CONVERSIONS.md before using it on private data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from formats import Invalid, parse_model_bin, sha, excess_bits

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from convert_character import triangulate  # existing GX winding rule

SCHEMA = "re4dc.fallback29.bake/1"
STATE, FLAGS = 0x46423290, 0xf0290000
IDENTITY = [1., 0., 0., 0., 1., 0., 0., 0., 1.]


def require(value, message):
    if not value:
        raise Invalid(message)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def bad(value):
        raise Invalid("nonfinite JSON number: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def number(value, key, low, high):
    require(not isinstance(value, bool) and isinstance(value, (int, float)) and
            math.isfinite(value) and low <= value <= high, key + ": invalid finite range")
    return float(value)


def integer(value, key, low, high):
    require(type(value) is int and low <= value <= high, key + ": invalid integer range")
    return value


def boolean(value, key):
    require(type(value) is bool, key + ": expected boolean")
    return value


def rgb(value, key):
    require(isinstance(value, list) and len(value) == 3, key + ": expected RGB")
    return [number(x, key, 0, 255) for x in value]


def unit(value):
    require(isinstance(value, (list, tuple)) and len(value) == 3, "expected three-vector")
    values = [number(x, "direction", -1e20, 1e20) for x in value]
    length = math.sqrt(sum(x*x for x in values))
    require(length > 1e-12, "zero normal/direction")
    return tuple(x/length for x in values)


def align4(value):
    return (value + 3) & ~3


def source_triangles(data, part, signed):
    stream = data[part["stream_offset"]:part["stream_offset"] + part["stream_bytes"]]
    require(not stream.startswith(b"\xfe\x03"), "already encoded input: convert the original source stream")
    cursor, triangles = 0, []
    stride = 8 if signed else 6
    while cursor < len(stream):
        opcode = stream[cursor]
        cursor += 1
        if opcode == 0:
            continue
        require(opcode in (0x80, 0x90, 0x98), "unsupported primitive for reversible bake")
        n = struct.unpack_from(">H", stream, cursor)[0]
        cursor += 2
        raw = [struct.unpack_from(">4H" if signed else ">3H", stream, cursor+i*stride) for i in range(n)]
        cursor += n*stride
        # Runtime FE records use vi,ni,ti,ci; GX uses vi,ni,ci,ti.
        rows = [(r[0], r[1], r[-1], r[2] if signed else 0) for r in raw]
        triangles.extend(tuple(t) for t in triangulate(opcode, rows))
    return triangles


def checked_context(raw, data, model):
    context = decode(raw)
    require(isinstance(context, dict) and context.get("schema") == SCHEMA, "expected " + SCHEMA)
    require(context.get("source_sha256") == sha(data), "converted source SHA-256 mismatch")
    require(context.get("source_kind") == "PS2-converted-ModelData", "requires declared PS2 converted ModelData")
    require(context.get("ownership") == "source-model", "NMR/certificate-owned models require their own packer; refused")
    require(isinstance(context.get("provenance"), str) and context["provenance"].strip(), "missing owner provenance note")
    require(context.get("pose_space") == "source-normal-space", "explicit source-normal-space pose required")
    require(not model["morph"], "morph model requires a dynamic bake adapter; refused")
    require(data[40] <= 30, "position shift exceeds native actor qualification")
    parts = context.get("parts")
    require(isinstance(parts, list), "context.parts must be a list")
    seen = set()
    for entry in parts:
        require(isinstance(entry, dict), "part context must be object")
        index = integer(entry.get("index"), "part index", 0, len(model["parts"])-1)
        require(index not in seen, "duplicate part context")
        seen.add(index)
        require(entry.get("static_vertex_colors") is True, "static_vertex_colors must be explicitly true")
        render = entry.get("render", {})
        require(isinstance(render, dict), "part render context must be object")
        require(render.get("blend") == 0 and type(render.get("blend")) is int, "opaque blend=0 required")
        integer(render.get("alpha_state"), "constant alpha_state", 0, 255)
        require(render.get("material_animation") is False, "animated source material policy refused")
        light = entry.get("lighting", {})
        require(isinstance(light, dict), "part lighting context must be object")
        require(light.get("enabled") is True, "lighting-disabled parts already have a cheap constant path")
        boolean(light.get("ambient_vertex"), "ambient_vertex")
        boolean(light.get("material_vertex"), "material_vertex")
        rgb(light.get("ambient_rgb"), "ambient_rgb")
        rgb(light.get("material_rgb"), "material_rgb")
        number(light.get("tev_scale"), "tev_scale", 0.001, 4)
        integer(light.get("diffuse"), "diffuse", 0, 2)
        integer(light.get("actor_probe_mode"), "actor_probe_mode", 0, 2)
        integer(light.get("model_id"), "model_id", -1, 255)
        boolean(light.get("leon_marker"), "leon_marker")
        boolean(light.get("headroom_half"), "headroom_half")
        require(not light["leon_marker"] and not light["headroom_half"],
                "special Leon/headroom lighting policy requires its owner packer; refused")
        boolean(light.get("ganado_lit_toggle"), "ganado_lit_toggle")
        integer(light.get("ganado_mode"), "ganado_mode", 0, 9)
        boolean(light.get("basis_valid"), "basis_valid")
        boolean(light.get("probe_valid"), "probe_valid")
        lights = light.get("directional_lights")
        require(isinstance(lights, list) and len(lights) <= 8, "at most eight explicit captured directional lights")
        for lamp in lights:
            require(isinstance(lamp, dict) and set(lamp) == {"direction", "color_rgb"}, "unsupported directional light")
            unit(lamp["direction"])
            rgb(lamp["color_rgb"], "light color")
        matrices = entry.get("normal_matrices")
        require(isinstance(matrices, list) and len(matrices) >= max(1, model["weights"]), "captured normal matrices missing")
        for matrix in matrices:
            require(isinstance(matrix, list) and len(matrix) == 9, "normal matrix must have nine row-major entries")
            for x in matrix:
                number(x, "normal matrix", -1e6, 1e6)
        require(not model["parts"][index]["material_flags"], "bump/specular/mask material refused")
    return context


def triggers(light):
    scale = any(c*light["tev_scale"] < 255 for c in light["material_rgb"])
    fold = scale and light["diffuse"] == 2 and not light["ambient_vertex"] and not light["material_vertex"]
    eligible_model = light["leon_marker"] or (light["actor_probe_mode"] >= 2 and 0x10 <= light["model_id"] <= 0x20
        and (not light["ganado_lit_toggle"] or light["ganado_mode"] != 0))
    probe = light["actor_probe_mode"] > 0 and (not eligible_model or scale or light["diffuse"] != 2 or
        light["ambient_vertex"] or light["material_vertex"] or
        light["leon_marker"] and not light["basis_valid"] or not light["probe_valid"])
    return fold, probe


def vertex_color(data, model, record):
    if not model["flags"] & 0x80000000:
        return (255, 255, 255, 255)
    at = model["colors_offset"] + record[3]*4
    return tuple(data[at:at+4])


def vertex_normal(data, model, record, matrices):
    small = bool(model["flags"] & 0x20000000)
    stride = 4 if small else 8
    at = model["normals_offset"] + record[1]*stride
    raw = struct.unpack_from("<3bB" if small else "<3hH", data, at)
    require(raw[3] < len(matrices), "normal palette index outside captured pose")
    m = matrices[raw[3]]
    return unit([sum(m[a*3+b]*raw[b] for b in range(3)) for a in range(3)])


def shade(data, model, record, context):
    light = context["lighting"]
    col = vertex_color(data, model, record)
    normal = vertex_normal(data, model, record, context["normal_matrices"])
    value = [c/255. for c in (col[:3] if light["ambient_vertex"] else light["ambient_rgb"])]
    for lamp in light["directional_lights"]:
        d = unit(lamp["direction"])
        f = 1. if light["diffuse"] == 0 else sum(x*y for x,y in zip(normal,d))
        if light["diffuse"] == 2:
            f = max(0., f)
        for c in range(3):
            value[c] += lamp["color_rgb"][c]*f/255.
    material = col[:3] if light["material_vertex"] else light["material_rgb"]
    # native_actor_fast::channel truncates after final clamp. The additional
    # RGB565 quantization is explicit and tested separately from exact source RGB.
    rgb8 = [int(min(255., max(0., material[c]*light["tev_scale"]*min(1., max(0., value[c]))))) for c in range(3)]
    word = ((rgb8[0] >> 3) << 11) | ((rgb8[1] >> 2) << 5) | (rgb8[2] >> 3)
    return word


def bake_reference(data, model, records, context, flags):
    light = context["lighting"]
    colors = [vertex_color(data, model, r) for r in records]
    average = [sum(v[c] for v in colors)/len(colors) for c in range(3)]
    ambient = average if light["ambient_vertex"] else light["ambient_rgb"]
    material = average if light["material_vertex"] else light["material_rgb"]
    mean = 1. if light["diffuse"] == 0 else .25 if light["diffuse"] == 2 else 0.
    response = [(ambient[c] + mean*sum(l["color_rgb"][c] for l in light["directional_lights"])) *
                material[c]*light["tev_scale"]/255. for c in range(3)]
    require(all(0 < x <= 16384 for x in response), "zero/invalid reference channel cannot track future brightening")
    mode = int(light["ambient_vertex"]) | (int(light["material_vertex"]) << 1) | (light["diffuse"] << 2)
    ref = response + list(ambient) + list(material) + [light["tev_scale"], 1., float(mode)]
    reserved = [0.]*15 + [291.]
    return struct.pack("<II28f", STATE, FLAGS | flags, *(ref + reserved))


def encode_blob(data, model, part, context, flags):
    triangles = source_triangles(data, part, bool(model["flags"] & 0x80000000))
    require(triangles, "empty part does not need a light bake")
    meshlets, records, indices, lookup, local = [], [], bytearray(), {}, []
    corners = bytearray()
    def flush():
        nonlocal lookup, local, corners
        if not local:
            return
        meshlets.append((len(local) | (len(corners) << 8) | ((len(corners)//3) << 20), len(records), len(indices)))
        records.extend(local)
        indices.extend(corners)
        lookup, local, corners = {}, [], bytearray()
    for tri in triangles:
        if len(lookup) + len(set(tri)-lookup.keys()) > 128 or len(corners)+3 > 1024:
            flush()
        for j, record in enumerate(tri):
            if record not in lookup:
                lookup[record] = len(local)
                local.append(record)
            corners.append(lookup[record] | (128 if j == 2 else 0))
    flush()
    require(len(records) <= 65535 and len(indices) <= 65535, "16-bit FE record/index extent")
    all_colors = {r[3] for r in records}
    has_ci = len(all_colors) > 1
    stride = 4 + int(has_ci)
    rec_at = 32 + 8*len(meshlets)
    idx_at = rec_at + align4(len(records)*stride*2)
    bake_at = idx_at + align4(len(indices))
    used = bake_at + 120
    require(used <= part["stream_bytes"] and used//4 < 65536, "baked native stream does not fit existing part capacity")
    result = bytearray(part["stream_bytes"])
    raw_uv = []
    positions = []
    for r in records:
        raw_uv.extend(struct.unpack_from("<2h" if model["flags"] & 0x80000000 else "<2H", data, model["uv_offset"] + 4*r[2]))
        positions.append(struct.unpack_from("<3h", data, model["positions_offset"] + 8*r[0]))
    # Same bind-space sphere convention as Converter::bounds (unscaled source
    # positions divided by 2^shift); never tighten to a camera/captured pose.
    factor = 1. / (1 << data[40])
    lo = [min(p[c] for p in positions)*factor for c in range(3)]
    hi = [max(p[c] for p in positions)*factor for c in range(3)]
    center = [(a+b)*.5 for a,b in zip(lo,hi)]
    radius = math.sqrt(sum(((hi[c]-lo[c])*.5)**2 for c in range(3)))
    # Round outwards so float32 serialization cannot accidentally shrink bounds.
    radius = max(radius * (1. + 2e-6), 1e-5)
    blob_flags = 2 | int(has_ci) | (min(excess_bits(raw_uv),31) << 2)
    struct.pack_into("<4B6H4f", result, 0, 0xfe,3,blob_flags,0,len(meshlets),min(all_colors),rec_at//4,idx_at//4,0,bake_at//4,*center,radius)
    for i, row in enumerate(meshlets):
        struct.pack_into("<IHH", result, 32+8*i, *row)
    for i, r in enumerate(records):
        packed = list(r[:3]) + ([r[3]] if has_ci else []) + [shade(data,model,r,context)]
        struct.pack_into("<"+"H"*stride, result, rec_at+i*stride*2, *packed)
    result[idx_at:idx_at+len(indices)] = indices
    result[bake_at:used] = bake_reference(data,model,records,context,flags)
    return bytes(result), dict(meshlets=len(meshlets), records=len(records), triangles=len(triangles),
        old_stream_bytes=part["stream_bytes"], used_stream_bytes=used, resident_delta_bytes=0,
        baked_record_bytes=2*len(records), flags=flags,
        old_probe_decline=triggers(context["lighting"])[1], old_light_scale=triggers(context["lighting"])[0])


def convert(data, context_raw=None, fold_light_scale=False, bake_probe_decline=False):
    require(type(fold_light_scale) is bool and type(bake_probe_decline) is bool, "flags must be booleans")
    report = dict(schema="re4dc.fallback29.convert/1", input_sha256=sha(data), bytes=len(data),
                  fold_light_scale=fold_light_scale, bake_probe_decline=bake_probe_decline, parts=[])
    if not fold_light_scale and not bake_probe_decline:
        report.update(output_sha256=sha(data), changed=False, mode="byte-identical-copy")
        return data, report
    require(context_raw is not None, "enabled conversion requires source-bound context")
    model = parse_model_bin(data)
    context = checked_context(context_raw, data, model)
    result = bytearray(data)
    # Arrays, joint tables and part headers may not alias a stream being edited.
    protected = [(0,72 if model["version"] == 0x20030818 else 64),
        (model["positions_offset"],model["position_count"]*8),
        (model["normals_offset"],model["normal_count"]*(4 if model["flags"]&0x20000000 else 8))]
    protected.extend((p["offset"],32) for p in model["parts"])
    head, weights_at = struct.unpack_from("<I", data, 0)[0], struct.unpack_from("<I", data, 20)[0]
    protected.extend([(head, model["joints"]*16), (weights_at, model["weights"]*(12 if struct.unpack_from("<H",data,42)[0] > 255 else 8))])
    if model["version"] == 0x20030818:
        for field, stride in ((64,8),(68,2)):
            at=struct.unpack_from("<I",data,field)[0]
            if at:
                require(at+4<=len(data), "joint table outside source")
                count=struct.unpack_from("<I",data,at)[0]
                protected.append((at,4+count*stride))
    for p in model["parts"]:
        protected.extend((model["uv_offset"]+4*i,4) for i in p["uv_indices"])
        protected.extend((model["colors_offset"]+4*i,4) for i in p["color_indices"])
    for at,size in protected:
        require(0 <= at <= len(data) and size <= len(data)-at, "protected range outside source")
    for entry in context["parts"]:
        part = model["parts"][entry["index"]]
        scale, probe = triggers(entry["lighting"])
        mode = int(fold_light_scale and scale) | (int(bake_probe_decline and probe) << 1)
        if not mode:
            report["parts"].append(dict(index=part["index"], changed=False, reason="selected trigger absent"))
            continue
        start, end = part["stream_offset"], part["stream_offset"]+part["stream_bytes"]
        require(all(end <= at or at+size <= start for at,size in protected), "stream aliases protected source data")
        blob, stats = encode_blob(data,model,part,entry,mode)
        result[start:end] = blob
        report["parts"].append(dict(index=part["index"],changed=True,stream_sha256=sha(blob),**stats))
    output = bytes(result)
    report.update(output_sha256=sha(output), changed=output != data, context_sha256=sha(context_raw),
        source_kind=context["source_kind"], provenance=context["provenance"], ownership=context["ownership"],
        approximation="captured-pose directional RGB565 bake; live quarter-Lambert color-energy gain per part",
        runtime_requires="FALLBACK_SCAN29=1 NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 MODEL_STREAM_FIX=1 NATIVE_ACTOR_PRELIT=1; FAST_ONLY not required")
    return output,report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path)
    ap.add_argument("output",type=Path)
    ap.add_argument("--context",type=Path)
    ap.add_argument("--receipt",type=Path)
    ap.add_argument("--fold-light-scale",nargs="?",const=1,default=0,type=int,choices=(0,1))
    ap.add_argument("--bake-probe-decline",nargs="?",const=1,default=0,type=int,choices=(0,1))
    args=ap.parse_args(argv)
    try:
        require(not args.output.exists(), "output already exists; choose a new path")
        require(args.receipt is None or not args.receipt.exists(), "receipt already exists")
        require(args.receipt is None or args.receipt.resolve()!=args.output.resolve(), "receipt/output must differ")
        enabled=args.fold_light_scale or args.bake_probe_decline
        source=args.input.read_bytes()
        context=args.context.read_bytes() if enabled and args.context else None
        output,report=convert(source,context,bool(args.fold_light_scale),bool(args.bake_probe_decline))
        with args.output.open("xb") as handle:
            handle.write(output)
        if args.receipt:
            with args.receipt.open("x") as handle:
                handle.write(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
        print(json.dumps(report,sort_keys=True,allow_nan=False))
    except (Invalid,ValueError,OSError,KeyError,TypeError,struct.error) as exc:
        ap.exit(2,"conversion refused: "+str(exc)+"\n")


if __name__=="__main__":
    main()

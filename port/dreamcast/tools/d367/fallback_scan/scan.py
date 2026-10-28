#!/usr/bin/env python3
"""Build 29: inventory converted disc data and predict fallback predicates.

Read-only inputs. Predictions describe potential draws, never a console census.
Runtime lighting/view/residency facts stay unknown unless explicitly bound to
the input SHA256 and exact scanner model key in --context.
"""
import argparse
import collections
import csv
import io
import json
import math
from pathlib import Path
import re
import sys

import formats

SCHEMA = "re4dc.fallback29.scan/1"
CONTEXT_SCHEMA = "re4dc.fallback29.context/1"
ROOM_LIST_SCHEMA = "re4dc.fallback29.rooms/1"
ROW_FIELDS = ("room", "source", "source_sha256", "model", "label", "kind", "model_id", "scope", "part", "meshlet",
              "level", "material", "reason", "status", "parts", "vertices", "vertex_basis", "corners", "meshlets", "instances",
              "knob", "recipe_value", "trigger", "evidence")
ACTIVE = ("predicted", "candidate", "static")


def room_name(value):
    if isinstance(value, str):
        value = int(value.lower().removeprefix("r").removeprefix("0x"), 16)
    formats.require(type(value) is int and 0 <= value <= 0xffff, "room number")
    return f"r{value:03x}"


def read_knobs(path):
    if path is None:
        return {}, None
    data = path.read_bytes()
    knobs = {}
    for line in data.decode().splitlines():
        if line.lstrip().startswith("#"):
            continue
        # Resolved files have one KEY=value per line; do not execute shell text.
        m = re.fullmatch(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*", line)
        if m:
            knobs[m[1]] = m[2]
    formats.require(knobs, "knob file has no KEY=value rows")
    return knobs, dict(path=path.name, sha256=formats.sha(data))


def knob_int(knobs, key):
    try:
        return int(knobs[key], 0)
    except (KeyError, ValueError):
        return None


def dynamic_state(context, key):
    value = context.get(key)
    return value if type(value) is bool else None


def predicate(value, evidence, candidate=False):
    if value is None:
        return "candidate" if candidate else "unknown", evidence
    return ("predicted" if value else "clear"), evidence


def validate_context(document):
    formats.require(isinstance(document, dict) and document.get("schema") == CONTEXT_SCHEMA,
                    "context schema must be " + CONTEXT_SCHEMA)
    formats.require(isinstance(document.get("sources", []), list), "context sources array")
    out = {}
    for source in document.get("sources", []):
        formats.require(isinstance(source, dict), "context source object")
        path = source.get("path")
        formats.require(isinstance(path,str) and path not in out and not Path(path).is_absolute()
                        and ".." not in Path(path).parts, "context source path/duplicate")
        formats.require(isinstance(source.get("sha256"), str) and
                        re.fullmatch(r"[0-9a-f]{64}",source["sha256"]), "context source SHA256")
        formats.require(isinstance(source.get("models", []), list), "context models array")
        models = {}
        for model in source.get("models", []):
            formats.require(isinstance(model, dict), "context model object")
            key = model.get("key")
            formats.require(isinstance(key,str) and key not in models, "context model key/duplicate")
            formats.require(isinstance(model.get("parts", []), list), "context parts array")
            formats.require(isinstance(model.get("rooms", []), list), "context rooms array")
            formats.require("model_id" not in model or model["model_id"] is None or
                            type(model["model_id"]) is int and -1 <= model["model_id"] <= 255,
                            "context model ID")
            formats.require("model_kind" not in model or model["model_kind"] is None or
                            type(model["model_kind"]) is int and 0 <= model["model_kind"] <= 255,
                            "context model kind")
            parts = {}
            for part in model.get("parts", []):
                formats.require(isinstance(part,dict), "context part object")
                index = part.get("index")
                formats.require(type(index) is int and index >= 0 and index not in parts, "context part index/duplicate")
                light, render = part.get("lighting",{}), part.get("render",{})
                formats.require(isinstance(light,dict) and isinstance(render,dict), "context lighting/render object")
                for k in ("enabled","ambient_vertex","material_vertex","leon_marker","headroom_half","basis_valid","probe_valid"):
                    formats.require(k not in light or type(light[k]) is bool, "context lighting boolean " + k)
                for k in ("diffuse","ganado_mode","leon_mode","significant_lights","keep_lights"):
                    formats.require(k not in light or type(light[k]) is int and light[k] >= 0,
                                    "context lighting integer " + k)
                if "diffuse" in light:
                    formats.require(light["diffuse"] in (0,1,2), "context diffuse mode")
                if "leon_mode" in light:
                    formats.require(light["leon_mode"] in (0,1,2,3), "context Leon light mode")
                if "significant_lights" in light:
                    formats.require(light["significant_lights"] <= 8, "context significant light count")
                for k in ("material_rgb","ambient_rgb"):
                    if k in light:
                        formats.require(isinstance(light[k],list) and len(light[k]) == 3
                            and all(type(v) is int and 0 <= v <= 255 for v in light[k]), "context " + k)
                if "tev_scale" in light:
                    formats.require(type(light["tev_scale"]) in (int,float) and math.isfinite(light["tev_scale"])
                                    and light["tev_scale"] >= 0, "context TEV scale")
                for k in ("flat","cone_available","static_class","chunk_unique","chunk_normal_unique"):
                    formats.require(k not in render or type(render[k]) is bool, "context render boolean " + k)
                if "uv_offset" in render:
                    formats.require(isinstance(render["uv_offset"],list) and len(render["uv_offset"]) == 2
                                    and all(type(v) in (int,float) and math.isfinite(v) for v in render["uv_offset"]),
                                    "context UV offset")
                for k in ("blend","alpha_state"):
                    formats.require(k not in render or type(render[k]) is int and render[k] >= 0, "context " + k)
                parts[index] = part
            models[key] = dict(model, parts=parts)
        out[path] = dict(source, models=models)
    return out


def classify_part(model, part, context, knobs, textures):
    """Rows have exact predicate semantics; several rows can describe one part."""
    light, render = context.get("lighting",{}), context.get("render",{})
    rows = []

    def add(reason, value, trigger, knob="", candidate=False, evidence="", status=None):
        s, e = predicate(value, evidence, candidate)
        rows.append(dict(reason=reason, status=status or s, knob=knob, recipe_value=knobs.get(knob,"unknown") if knob else "n/a",
                         trigger=trigger, evidence=e))

    if model["kind"] == "R4IM/R4PW":
        lod = knob_int(knobs,"MESH_LOD")
        add("w_mesh_no_lod",lod == 0 if lod is not None else None,
            "MESH_LOD disabled selects all part meshlets instead of cluster LOD selection","MESH_LOD",
            evidence="supported world layouts contain cluster/LOD tables")
        direct = knob_int(knobs,"SCENERY_DIRECT_STRIPS")
        add("w_direct_kind",part.get("world_layout") != "SDS1",
            "direct-strip helper requires an SDS1 physical package plus PS2/SQ owner","SCENERY_DIRECT_STRIPS",
            evidence="static layout only; owner/SQ/diagnostic guards remain runtime",
            status="inert" if direct == 0 else "candidate" if part.get("world_layout") != "SDS1" else "unknown")
        add("w_strip_general",True if knob_int(knobs,"MESH_STRIP_LEAN") in (0,2) else None,
            "ordinary strip walker unless lean mode and selected SQ/check state admit it","MESH_STRIP_LEAN",
            evidence="strips and maximum strip sizes are listed per stored meshlet")
        add("w_clip_rebuild", None, "selected meshlet crosses view/depth clip plane; requires camera/outcodes",
            "SCENERY_CLIP_INDEXED26", evidence="offline mesh bounds do not determine current camera clipping")
        add("w_translucent", part.get("pass_id") == 2, "R4PW part pass is 2", "PS2_WORLD_MESH",
            evidence=f"pass={part.get('pass_id')}")
        add("w_vertex_alpha", bool(part.get("vertex_alpha")), "R4PW reserved bit 0 carries ARGB4444 corner alpha",
            "PS2_VERTEX_ALPHA", evidence=f"vertex_alpha={part.get('vertex_alpha')}")
    else:
        fast_only = knob_int(knobs,"ACTOR_LIGHT_FAST_ONLY")
        light_cap = knob_int(knobs,"ACTOR_LIGHT_CAP")
        baked29 = bool(part.get("bake") and part["bake"].get("fallback29"))
        data29 = baked29 and knob_int(knobs,"FALLBACK_SCAN29") != 0
        if baked29:
            add("offline_light29", True, "FE/v3 BakeBlock has source-bound Build29 marker", "FALLBACK_SCAN29",
                evidence="marker does not prove live admission: channel modes, material, blend, mask, alpha, TEV and gain limits can decline",
                status="inert" if knob_int(knobs,"FALLBACK_SCAN29") == 0 else "candidate")
        enabled = dynamic_state(light,"enabled")
        av, mv = dynamic_state(light,"ambient_vertex"), dynamic_state(light,"material_vertex")
        vertex = av or mv if av is not None and mv is not None else True if av is True or mv is True else None
        diffuse = light.get("diffuse")
        caps = None
        if "material_rgb" in light and "tev_scale" in light:
            caps = all(c * light["tev_scale"] >= 255 for c in light["material_rgb"])
        generic_caps = caps
        if caps is False and light.get("headroom_half") is True:
            if knob_int(knobs,"LEON_LIGHT_HEADROOM") is None:
                generic_caps = None
            elif knob_int(knobs,"LEON_LIGHT_HEADROOM"):
                generic_caps = all(2 * c * light["tev_scale"] >= 255 for c in light["material_rgb"])
        elif caps is False and "headroom_half" not in light and knob_int(knobs,"LEON_LIGHT_HEADROOM") != 0:
            generic_caps = None
        scale_bad = (diffuse != 2 or not generic_caps) if diffuse is not None and generic_caps is not None else (
            True if diffuse is not None and diffuse != 2 or generic_caps is False else None)
        material_bad = scale_bad if enabled is True and vertex is False else False if enabled is False or vertex is True else None
        if fast_only or light_cap:
            add("a_lit_scale",False,"S.enable && !vertex && (diffuse != 2 || material*TEV < 255)",
                "ACTOR_LIGHT_FAST_ONLY",evidence="runtime cap/fast-only suppresses old exact dispatch",status="inert")
            add("a_lit_colour",False,"ambient_vertex || material_vertex","ACTOR_LIGHT_FAST_ONLY",status="inert")
        else:
            add("a_lit_scale",material_bad,"S.enable && !vertex && (diffuse != 2 || material*TEV < 255)",
                "ACTOR_LIGHT_CAP",evidence="bound SourceLighting" if light else "RGB/diffuse/TEV are runtime, absent from ModelPart")
            add("a_lit_colour",vertex,"ambient_vertex || material_vertex","ACTOR_LIGHT_CAP",
                evidence="ModelData CLR presence alone does not establish channel source")
        probe = knob_int(knobs,"ACTOR_PROBE_LIGHT")
        model_id = context.get("model_id",model.get("model_id"))
        if context.get("model_kind") is not None and context["model_kind"] != 0:
            model_id = -1  # re4dc_actor_model_id only exposes kind-0 enemy IDs.
        eligible_class = True if light.get("leon_marker") is True else None
        ganado = model.get("actor_class") == "ganado" or type(model_id) is int and 0x10 <= model_id <= 0x20
        if eligible_class is not True:
            if probe is not None and probe >= 2 and ganado:
                toggle, mode = knob_int(knobs,"GANADO_LIT_TOGGLE"), light.get("ganado_mode")
                eligible_class = True if toggle == 0 or mode is not None and mode != 0 else (
                    False if toggle and mode == 0 else None)
            elif light.get("leon_marker") is False and ((model_id is not None and not ganado) or probe is not None and probe < 2):
                eligible_class = False
        probe_bad = None
        if probe == 0 or fast_only:
            add("a_probe_miss",False,"probe eligibility/scale/basis/probe-cache failure","ACTOR_PROBE_LIGHT",status="inert")
        else:
            if enabled is False or vertex is True or diffuse is not None and diffuse != 2 or caps is False or eligible_class is False:
                probe_bad = True
            elif all(x is not None for x in (enabled,vertex,diffuse,caps,eligible_class)):
                basis = light.get("basis_valid") if light.get("leon_marker") is True else True if light.get("leon_marker") is False else None
                valid = light.get("probe_valid")
                probe_bad = False if probe is not None and probe > 0 and basis is True and valid is True else (
                    True if basis is False or valid is False else None)
            add("a_probe_miss",probe_bad,"probe_eligible then material*TEV >= 255 and valid basis/cache",
                "ACTOR_PROBE_LIGHT",evidence="probe decline alone can still use generic fast build_lights")
        lights = light.get("significant_lights")
        fourth = lights > 3 if lights is not None else None
        keep = light.get("keep_lights")
        if keep is None:
            if knob_int(knobs,"GIGANTE_LIGHTS") == 0: keep = 0
            elif light_cap: keep = 3
            elif knob_int(knobs,"GIGANTE_LIGHTS") and model_id == 0x2b: keep = 3
            elif knob_int(knobs,"GIGANTE_LIGHTS") and model_id == 0x49 and knob_int(knobs,"GIGANTE_LIGHTS_TREES"): keep = 3
            elif knob_int(knobs,"GIGANTE_LIGHTS") and knob_int(knobs,"GANADO_LIGHT_FOLD") and type(model_id) is int and 0x10 <= model_id <= 0x20:
                keep = 3
        generic_enter = probe == 0 or probe_bad is True
        early_return = enabled is False or vertex is True and not light_cap or material_bad is True and not light_cap
        fourth_bad = False if early_return or keep else (fourth if fourth is False or keep == 0 else None)
        add("a_lit_fourth",fourth_bad,"fourth significant retained light after prior guards; class keep rules may cap",
            "GIGANTE_LIGHTS",evidence="raw room light count is not significant retained count")
        basis = light.get("basis_valid")
        source_light = knob_int(knobs,"LEON_SOURCE_LIGHT")
        basis_bad = False if early_return or source_light == 0 or light.get("leon_marker") is False else (
            not basis if basis is not None and light.get("leon_marker") is True and source_light else None)
        add("a_lit_basis",basis_bad,"Leon-marker part requires an inverse normal basis and that inversion fails",
            "LEON_SOURCE_LIGHT",evidence="bind-pose geometry cannot establish current modelview inverse")
        if basis_bad is True:
            fourth_bad = False
            next(r for r in rows if r["reason"] == "a_lit_fourth")["status"] = "clear"
        exact = None
        if fast_only or light_cap or probe_bad is False:
            exact = False
        elif generic_enter and (material_bad is True or vertex is True or basis_bad is True or fourth_bad is True):
            exact = True
        elif generic_enter and all(x is False for x in (material_bad,vertex,basis_bad,fourth_bad)):
            # STATUE_LIGHTS>=2 also deliberately selects an exact evaluator.
            exact = False if knob_int(knobs,"STATUE_LIGHTS") == 0 else None
        add("a_lit_exact",exact,"probe decline AND generic build_lights refusal AND lit draw selects exact pass",
            "ACTOR_LIGHT_FAST_ONLY",evidence="potential vertices; no visibility/LOD/draw-frequency multiplication")
        for row in rows:
            if row["reason"] in ("a_lit_scale","a_lit_colour","a_lit_fourth","a_lit_basis"):
                if fast_only or probe_bad is False:
                    row["status"] = "inert" if fast_only else "clear"
                elif row["status"] == "predicted" and (not generic_enter or data29 or fast_only is None or
                        row["reason"] in ("a_lit_scale","a_lit_colour") and light_cap is None or
                        row["reason"] in ("a_lit_fourth","a_lit_basis") and
                        (enabled is None or vertex is None or material_bad is None)):
                    row["status"] = "candidate"
                    row["evidence"] += "; dispatch/recipe admission remains conditional"
            elif row["reason"] in ("a_lit_exact","a_probe_miss") and row["status"] == "predicted" and (
                    data29 or fast_only is None or row["reason"] == "a_probe_miss" and probe is None or
                    row["reason"] == "a_lit_exact" and light_cap is None):
                row["status"] = "candidate"
                row["evidence"] += "; dispatch/recipe admission remains conditional"
        leon_toggle, leon_mode = knob_int(knobs,"LEON_LIGHT_TOGGLE"), light.get("leon_mode")
        if light.get("leon_marker") is True and leon_toggle != 0 and probe != 0 and leon_mode not in (1,2):
            constant_override = bool(leon_toggle) and probe is not None and probe > 0 and leon_mode in (0,3)
            for row in rows:
                if row["reason"] in ("a_lit_scale","a_lit_colour","a_probe_miss","a_lit_fourth","a_lit_basis","a_lit_exact"):
                    if constant_override:
                        row["status"] = "inert"
                        row["evidence"] += "; captured Leon toggle mode returns constant before probe/generic dispatch"
                    elif row["status"] == "predicted":
                        row["status"] = "candidate"
                        row["evidence"] += "; Leon light toggle recipe/mode may select an earlier constant pass"
        add("a_vertex_colors",bool(part.get("vertex_colors")),"geometry supplies per-corner CLR index",
            evidence="static field, not proof SourceLighting uses vertex ambient/material",status="static" if part.get("vertex_colors") else "clear")
        uv_bad = None
        uv16 = knob_int(knobs,"NATIVE_ACTOR_UV16")
        if uv16 == 0:
            uv_bad = True
        elif uv16 is not None and "uv_offset" in render and all(k in part for k in ("texture_width","texture_height")):
            excess = part.get("uv_excess")
            if excess is not None:
                scale = 1/256 if part.get("signed_uv") else 1/32768
                dims = (part["texture_width"],part["texture_height"])
                uv_bad = any(render["uv_offset"]) or any(n < 8 or n > 1024 or n&(n-1) for n in dims) or (
                    excess > 0 and any(math.ldexp(scale*n,excess-1) > .5 for n in dims))
        add("a_uv32",uv_bad,"UV16 disabled, scroll/non-power-of-two texture, or bf16 error exceeds half texel",
            "NATIVE_ACTOR_UV16",evidence=f"stored significant-bit excess={part.get('uv_excess')}; resolved UV16 recipe and texture/scroll context required")
        cone = render.get("cone_available")
        add("a_cone_absent",True if knob_int(knobs,"ACTOR_BACKFACE_CONE") == 0 else not cone if cone is not None else None,
            "cone feature disabled or runtime converted meshlet has no valid rigid normal cone",
            "ACTOR_BACKFACE_CONE",evidence="disc FE/GX bytes do not carry the cone later built into runtime stream tail")
        flat = render.get("flat")
        lean, movca = knob_int(knobs,"ACTOR_BYTES_LEAN"), knob_int(knobs,"ACTOR_MOVCA")
        rewrite = flat
        if flat and lean and movca == 0:
            rewrite = bool(render["alpha_state"] & 256) if "alpha_state" in render else None
        elif flat and (lean is None or lean and movca is None): rewrite = None
        add("a_flat_rewrite",rewrite,"constant-light pass rewrites cached vertex colours unless lean constant fill applies",
            "ACTOR_BYTES_LEAN",evidence="constant/flat choice, vertex alpha and MOVCA determine this counter")
        if fast_only: rows[-1]["status"] = "inert"
        static = render.get("static_class")
        split = True if len(model["parts"]) <= 1 or len(model["parts"]) > 16 or render.get("blend",0) != 0 else None
        if static is False:
            split = True
        add("m_obj_split",split,"STATIC_OBJ_BATCH eligibility rejects class/blend/part count/lighting/state",
            "STATIC_OBJ_BATCH",evidence=f"part_count={len(model['parts'])}; live batch/state equality remains runtime")
        if knob_int(knobs,"STATIC_OBJ_BATCH") == 0: rows[-1]["status"] = "inert"
        elif split: rows[-1]["status"] = "candidate"
        alpha = render.get("alpha_state")
        chunk = knob_int(knobs,"CHAR_CHUNK")
        add("a_chunk_alpha",bool(alpha & 256) if alpha is not None else None,"chunk lighting uses ordinary pass when source vertex alpha is selected",
            "CHAR_CHUNK",evidence="texture alpha is separate from channel-alpha source")
        unique = render.get("chunk_unique")
        add("a_chunk_unique",unique,"every adjacent stored position ID differs; position chunk has no repeated run",
            "CHAR_CHUNK",evidence="source GX runtime packing order is unknown; stored FE meshlets can resolve this")
        add("a_chunk_nuniq",render.get("chunk_normal_unique"),"all stored normal IDs distinct; lighting chunk cannot share work",
            "CHAR_CHUNK",evidence="applies only when fast lighting chunk is selected and vertex alpha is absent")
        add("a_chunk_scratch",None,"lighting chunk side-cache allocation fails","CHAR_CHUNK",
            evidence="runtime workspace pressure is not a static geometry fact")
        for row in rows:
            if row["reason"].startswith("a_chunk_"):
                field = {"a_chunk_unique":"chunk_unique","a_chunk_nuniq":"chunk_normal_unique"}.get(row["reason"])
                if field and part["meshlets"] and all(field in let for let in part["meshlets"]):
                    affected = [let for let in part["meshlets"] if let[field]]
                    row.update(status="candidate" if affected else "clear",vertices=sum(x["vertices"] for x in affected),
                               corners=sum(x["corners"] for x in affected),meshlets=len(affected))
                    row["evidence"] = "derived from stored FE record order/normal IDs; runtime selection and light dispatch remain conditional"
                if chunk == 0 or fast_only and row["reason"] != "a_chunk_unique": row["status"] = "inert"
                elif row["reason"] == "a_chunk_nuniq" and alpha is not None and alpha & 256: row["status"] = "inert"
                elif row["status"] == "predicted": row["status"] = "candidate"
        add("legacy_primitive",bool(part.get("legacy_opcodes")),"line/point GX primitive outside native triangle packing",
            "NATIVE_ACTOR_FAST",evidence=str(part.get("legacy_opcodes",[])),status="static" if part.get("legacy_opcodes") else "clear")
        add("source_vertex_ambient",bool((part.get("model_flags") or 0)&0x40000000),
            "ModelData bit 30 selects vertex ambient in commonLightSet",evidence="call-site and owner lighting policy still required")
        add("source_morph",bool(model.get("morph")),"ModelData shape pointer may require source deformation",
            evidence="render data only; scanner never changes shape/gameplay",status="static" if model.get("morph") else "clear")
        if model["kind"] == "ModelData":
            bad_contract = model["position_shift"] > 30 or not model["position_count"] or not model["normal_count"] or not 32 <= part["stream_bytes"] <= 1024*1024
            add("a_contract",bad_contract,"native actor rejects source shift/counts/stream-size contract","NATIVE_ACTOR_FAST",
                evidence="only static subset; projection, palette, source identity and current frame contracts remain runtime",
                status="candidate" if bad_contract else "unknown")
    key = part.get("texture_key")
    if key:
        tex = textures.get(key)
        add("tex_missing",tex is None,"referenced texture key absent from supplied tex.pak and loose packages",
            "TEX_PACK",evidence=key,status="static" if tex is None else "clear")
        pal = any(t["palette"] for t in tex["entries"]) if tex else None
        add("tex_palette",pal,"texture package requires a palette","NATIVE_PALETTE",evidence=key,
            status="static" if pal else None)
        add("tex_handle",None,"runtime texture handle lookup misses current residency/generation",
            "TEX_PACK",evidence="presence in tex.pak does not imply a resident live handle")
    else:
        add("tex_handle",None,"runtime source TPL/key lookup and residency","TEX_PACK",evidence="no package texture key for this part")
    return rows


def infer_rooms(path, model):
    if "room" in model:
        return [room_name(model["room"])]
    matches = re.findall(r"(?:^|[/_.-])(r[0-9a-f]{3})(?=[/_.-]|$)",path.lower())
    return sorted(set(matches))


def scan_tree(tree, rooms, knobs=None, context=None, room_list=None, extra_inputs=()):
    knobs = knobs or {}
    contexts = validate_context(context) if context else {}
    formats.require(tree.is_dir(), "disc tree does not exist")
    root = tree.resolve()
    models, coverage, sources, textures, resident, refs, spawns = [], [], {}, {}, [], [], []
    context_used = set()
    room_map = collections.defaultdict(list)
    if room_list:
        formats.require(isinstance(room_list,dict) and room_list.get("schema") == ROOM_LIST_SCHEMA, "room-list schema")
        formats.require(isinstance(room_list.get("rooms",{}),dict), "room-list rooms object")
        for r, rows in room_list.get("rooms",{}).items():
            formats.require(isinstance(rows,list), "room-list entries array")
            for row in rows:
                formats.require(isinstance(row,dict) and isinstance(row.get("path"),str), "room-list row")
                room_map[row["path"]].append(dict(row,room=room_name(r)))
    paths = [(p,p.relative_to(tree).as_posix()) for p in sorted(tree.rglob("*")) if p.is_file() and
        (p.suffix.lower() in (".dar",".drs",".arc",".bin",".esl",".re4nmr",".re4cp",".re4gl",".re4mesh",".re4tex")
         or p.name.lower() == "tex.pak")]
    for p in extra_inputs:
        paths.append((p,"@input/"+p.name))
    seen_paths = set()
    for path, rel in paths:
        formats.require(rel not in seen_paths, "duplicate input identity " + rel)
        seen_paths.add(rel)
        formats.require(path.is_file(), "missing input " + str(path))
        if not rel.startswith("@input/"):
            formats.require(path.resolve().is_relative_to(root), "disc input symlink escapes supplied root: " + rel)
        with path.open("rb") as stream:
            head = stream.read(80)
        typ = None
        if head.startswith(b"RE4PAK1\0"): typ="tex.pak"
        elif head.startswith(b"RE4DCTX\0"): typ="texture"
        elif head.startswith(b"RE4NMR1\0"): typ="RE4NMR"
        elif head.startswith(b"RE4PL08\0"): typ="RE4PL08"
        elif head.startswith(b"GLP1"): typ="GLP1"
        elif head.startswith(b"R4IM"): typ="R4IM/R4PW"
        elif rel == "dc/resident.bin": typ="resident"
        elif path.suffix.lower() == ".esl": typ="ESL"
        elif head[:32] in (formats.CONTAINER_MAGIC,formats.DRS_MAGIC) or path.suffix.lower() in (".dar",".drs",".arc"):
            typ="archive"
        elif len(head)>=64 and formats.unpack("<I",head,60)[0] in (0x20010801,0x20030818): typ="ModelData"
        elif path.suffix.lower() == ".h": typ="compiled-cast-header"
        elif path.suffix.lower() in (".re4nmr",".re4cp",".re4gl",".re4mesh",".re4tex"):
            typ="unsupported"
        if typ is None:
            continue
        data = path.read_bytes()
        sources[rel] = dict(path=rel,sha256=formats.sha(data),bytes=len(data),format=typ)
        file_models=[]
        try:
            if typ == "tex.pak":
                new = formats.parse_texpak(data)
                for key,value in new.items():
                    if key in textures:
                        formats.require(textures[key]["sha256"] == value["sha256"], "duplicate texture key with different payload")
                textures.update(new)
            elif typ == "texture":
                m = re.fullmatch(r"([0-9a-f]{8}-[0-9a-f]{8})\.re4tex",path.name.lower())
                formats.require(m is not None,"loose texture key filename")
                value = formats.parse_texture(data)
                if m[1] in textures:
                    formats.require(textures[m[1]]["sha256"] == value["sha256"],"duplicate texture key with different payload")
                textures[m[1]]=value
            elif typ == "resident": resident = formats.parse_resident(data)
            elif typ == "ESL":
                spawns.extend(dict(s,source=rel,source_sha256=sources[rel]["sha256"]) for s in formats.parse_esl(data,rel))
            elif typ == "RE4NMR": file_models=formats.parse_registry(data)["models"]
            elif typ == "RE4PL08": file_models=[formats.parse_pl08(data)]
            elif typ == "GLP1": file_models=formats.parse_glod(data)["models"]
            elif typ == "R4IM/R4PW":
                side = path.with_suffix(".r4pw")
                if not side.is_file() and (path.name in ("ps2-sli1.re4mesh","ps2-sds1.re4mesh",
                        "ps2-world-split.re4mesh","ps2-dd3.re4mesh") or re.fullmatch(r"ps2-wv[0-9]+\.re4mesh",path.name)):
                    side = path.parent/"ps2-world.r4pw"
                if not side.is_file() and path.name == "ps2-world.re4mesh" and path.parent.name == "sc21":
                    side = path.parent.parent/"ps2-world.r4pw"
                formats.require(side.is_file(),"missing matching R4PW sidecar")
                formats.require(side.resolve().is_relative_to(path.parent.resolve() if rel.startswith("@input/") else root),
                                "R4PW symlink escapes supplied root")
                side_data=side.read_bytes()
                side_rel="@input/"+side.name if rel.startswith("@input/") else side.relative_to(tree).as_posix()
                sources[side_rel]=dict(path=side_rel,sha256=formats.sha(side_data),bytes=len(side_data),format="R4PW")
                parsed=formats.parse_world(data,side_data)
                file_models=parsed["models"]
                lineage=parsed["lineage"]
                if lineage:
                    source=path.parent/"ps2-world.re4mesh"
                    if source == path or not source.is_file():
                        coverage.append(dict(source=rel,format="world-lineage",status="missing",models=0,
                            message="physical variant parsed; canonical ps2-world.re4mesh needed for source CRC/extent binding"))
                    else:
                        formats.require(source.resolve().is_relative_to(path.parent.resolve()),"world lineage symlink escapes directory")
                        original=source.read_bytes();h=formats.unpack("<4s19I",original)
                        formats.require(h[0] == b"R4IM" and h[1] in (2,3) and h[2] == len(original)
                            and h[3] == formats.crc(original[80:]) and h[16:] == (2,0,0,0),"world lineage source header/CRC")
                        formats.require(lineage["source_bytes"] == len(original) and lineage["source_crc"] == h[3],
                                        "world variant source CRC/extent mismatch")
                        for m in file_models:
                            m["lineage_source_sha256"]=formats.sha(original)
            elif typ == "archive":
                result=formats.parse_room_archive(data,rel)
                file_models=result["models"]
                refs.extend(dict(r,source=rel,rooms=infer_rooms(rel,{})) for r in result["texture_references"])
                spawns.extend(dict(s,source=rel,source_sha256=sources[rel]["sha256"]) for s in result["spawn_records"])
            elif typ == "ModelData": file_models=[formats.parse_model_bin(data,rel)]
            elif typ == "compiled-cast-header": file_models=[formats.parse_compiled_header(data,rel)]
            else: raise formats.Invalid("unrecognised package magic/adapter")
            coverage.append(dict(source=rel,format=typ,status="scanned",models=len(file_models),message=""))
        except (ValueError,UnicodeError,IndexError,OSError) as exc:
            coverage.append(dict(source=rel,format=typ,status="rejected",models=0,message=str(exc)))
            continue
        ctx_source=contexts.get(rel)
        if ctx_source:
            formats.require(ctx_source["sha256"] == sources[rel]["sha256"],"stale context SHA256 for " + rel)
            context_used.add(rel)
        found=set()
        for model in file_models:
            mctx=(ctx_source or {}).get("models",{}).get(model["key"],{})
            found.add(model["key"])
            formats.require(set(mctx.get("parts",{})).issubset({p["index"] for p in model["parts"]}),"context part not in " + rel)
            model.update(source=rel,file_sha256=sources[rel]["sha256"],label=mctx.get("label",model["name"]),context=mctx)
            memberships=[dict(room=r,instances=None,origin="package/path") for r in infer_rooms(rel,model)]
            memberships.extend(dict(room=room_name(r),instances=None,origin="bound context") for r in mctx.get("rooms",[]))
            for entry in room_map.get(rel,[]):
                if entry.get("model",model["key"]) == model["key"]:
                    if "sha256" in entry:
                        formats.require(entry["sha256"] == model["file_sha256"],"room-list stale SHA256")
                    n=entry.get("instances")
                    formats.require(n is None or type(n) is int and n > 0,"room-list instances")
                    memberships.append(dict(room=entry["room"],instances=n,origin="explicit room list"))
                    model["label"]=entry.get("label",model["label"])
            by_room={m["room"]:m for m in memberships}
            model["memberships"]=[by_room[r] for r in sorted(by_room)] or [dict(room="unassigned",instances=None,origin="unknown")]
            models.append(model)
        if ctx_source:
            formats.require(set(ctx_source["models"]).issubset(found),"context model key not in " + rel)
    formats.require(set(contexts).issubset(context_used),"context sources missing/rejected: " + ", ".join(sorted(set(contexts)-context_used)))
    for path in sorted(set(room_map)-set(sources)):
        coverage.append(dict(source=path,format="room-list",status="missing",models=0,message="explicitly listed file not scanned"))
    rows=[]
    for model in models:
        ctx=model["context"]
        for part in model["parts"]:
            pctx=dict(ctx.get("parts",{}).get(part["index"],{}))
            if "model_id" in ctx: pctx["model_id"]=ctx["model_id"]
            if "model_kind" in ctx: pctx["model_kind"]=ctx["model_kind"]
            reasons=classify_part(model,part,pctx,knobs,textures)
            for member in model["memberships"]:
                if member["room"] != "unassigned" and member["room"] not in rooms:
                    continue
                base=dict(room=member["room"],source=model["source"],source_sha256=model["file_sha256"],model=model["key"],
                    label=model["label"],kind=model["kind"],model_id=ctx.get("model_id",model.get("model_id")),scope="part",part=part["index"],meshlet="",
                    level=model.get("level",""),material=part.get("material_raw") or part.get("texture_key") or "unknown",
                    parts=1,vertices=part["vertices"],vertex_basis=part.get("vertex_basis","stored FE records"),
                    corners=part["corners"],meshlets=len(part["meshlets"]),
                    instances=member["instances"])
                rows.extend(dict(base,**reason) for reason in reasons)
                for let in part["meshlets"]:
                    mesh_base=dict(base,scope="meshlet",meshlet=let["index"],level=let.get("level",model.get("level","")),parts=0,
                        vertices=let["vertices"],vertex_basis="stored meshlet local vertices",corners=let["corners"],meshlets=1)
                    rows.append(dict(mesh_base,reason="meshlet_inventory",status="inventory",knob="",recipe_value="n/a",
                        trigger="stored meshlet; LODs are alternatives; inherits parent part predicates",evidence=f"triangles={let['triangles']}"))
                    for reason,field,trigger in (("a_chunk_unique","chunk_unique","all adjacent stored position IDs differ"),
                                                 ("a_chunk_nuniq","chunk_normal_unique","all stored normal IDs distinct")):
                        if field not in let: continue
                        status="candidate" if let[field] else "clear"
                        if knob_int(knobs,"CHAR_CHUNK") == 0: status="inert"
                        if reason == "a_chunk_nuniq" and (knob_int(knobs,"ACTOR_LIGHT_FAST_ONLY") or
                                pctx.get("render",{}).get("alpha_state",0) & 256): status="inert"
                        rows.append(dict(mesh_base,reason=reason,status=status,knob="CHAR_CHUNK",recipe_value=knobs.get("CHAR_CHUNK","unknown"),
                            trigger=trigger,evidence="exact FE record identity; meshlet selection and chunk dispatch remain runtime"))
    for rec in resident:
        room=room_name(rec["room"])
        if room not in rooms: continue
        missing=rec["key"] not in textures
        rows.append(dict(room=room,source="dc/resident.bin",source_sha256=sources.get("dc/resident.bin",{}).get("sha256",""),
            model="resident",label="room preload list",kind="resident",model_id=None,scope="resident",part="",meshlet="",level="",
            material=rec["key"],reason="resident_key_missing",status="static" if missing else "clear",parts=0,vertices=0,
            corners=0,meshlets=0,instances=None,knob="ROOM_RESIDENT",recipe_value=knobs.get("ROOM_RESIDENT","unknown"),
            trigger="listed resident key absent from supplied texture packages",evidence=rec["key"]))
    for ref in refs:
        for room in ref["rooms"] or ["unassigned"]:
            if room not in rooms and room != "unassigned": continue
            missing=ref["key"] not in textures
            for reason,status in (("archive_texture_missing","static" if missing else "clear"),
                                  ("archive_palette_reference","static" if ref["palette"] else "clear")):
                rows.append(dict(room=room,source=ref["source"],source_sha256=sources[ref["source"]]["sha256"],
                    model=ref["location"],label="native archive texture reference",kind="texture-reference",model_id=None,scope="texture-reference",
                    part="",meshlet="",level="",material=ref["key"],reason=reason,status=status,parts=0,vertices=0,
                    corners=0,meshlets=0,instances=None,knob="TEX_PACK",recipe_value=knobs.get("TEX_PACK","unknown"),
                    trigger="R4NREF/R4PREF names texture key",evidence=ref["key"]))
    rows.sort(key=lambda r:(r["room"],r["source"],r["model"],str(r["part"]),str(r["meshlet"]),r["reason"]))
    spawn_rows=[dict(s,room=room_name(s["room"])) for s in spawns if room_name(s["room"]) in rooms]
    spawn_rows.sort(key=lambda s:(s["room"],s["source"],s["location"],s["index"]))
    present={r["room"] for r in rows}
    for room in rooms:
        if room not in present:
            coverage.append(dict(source=room,format="route-room",status="missing",models=0,message="no model/texture inventory bound to this room"))
    template=dict(schema=CONTEXT_SCHEMA,notes=["Unbound template: empty lighting/render means unknown.",
        "Bind a console capture by source hash + exact model/part; model ID alone is insufficient.",
        "Geometry can coexist with native replacement and source fallback: listed bytes do not prove a draw.",
        "Add evidence and runtime draw frequency separately; scanner counts one part, not instances or frames."],sources=[])
    for source in sorted({m["source"] for m in models}):
        template["sources"].append(dict(path=source,sha256=sources[source]["sha256"],models=[dict(key=m["key"],
            label=m["label"],model_id=m.get("model_id"),model_kind=None,rooms=[x["room"] for x in m["memberships"] if x["room"]!="unassigned"],
            source_offset=m.get("source_offset"),source_length=m.get("source_length"),
            position_count=m.get("position_count"),normal_count=m.get("normal_count"),
            parts=[dict(index=p["index"],source_info=p.get("source_info"),part_offset=p.get("offset"),
                position_count=p.get("position_count",m.get("position_count")),normal_count=p.get("normal_count",m.get("normal_count")),
                stream_bytes=p.get("stream_bytes"),material_raw=p.get("material_raw"),
                source_key_texture_bytes=p.get("source_key_texture_bytes"),vertices=p["vertices"],lighting={},render={}) for p in m["parts"]])
            for m in models if m["source"]==source]))
    inventory=[]
    for m in models:
        item={k:v for k,v in m.items() if k not in ("parts","context")}
        item["parts"]=[{k:v for k,v in p.items() if k not in
            ("records","primitive_records","stored_records","colors","color_indices","uv_indices","meshlets")}
            for p in m["parts"]]
        for p,out in zip(m["parts"],item["parts"]):
            out["meshlets"]=[{k:v for k,v in q.items() if k != "records"} for q in p["meshlets"]]
        inventory.append(item)
    return dict(schema=SCHEMA,status="INCOMPLETE" if any(c["status"] != "scanned" for c in coverage) else "SCANNED",
        scope="static inventory + explicitly hash-bound context; no console measurements",rooms=rooms,rows=rows,
        coverage=sorted(coverage,key=lambda x:(x["source"],x["format"])),sources=[sources[k] for k in sorted(sources)],
        textures=len(textures),models=len(models),model_inventory=inventory,spawn_inventory=spawn_rows,context_template=template)


def aggregate(rows, fields):
    groups={}
    for row in rows:
        if row["status"] not in ACTIVE or row.get("scope") == "meshlet" or row["reason"] == "meshlet_inventory": continue
        key=tuple(row[k] for k in fields)+(row["reason"],row["status"])
        if key not in groups:
            groups[key]={**{k:row[k] for k in fields},"reason":row["reason"],"status":row["status"],
                         "parts":0,"vertices":0,"corners":0,"meshlets":0}
        for k in ("parts","vertices","corners","meshlets"): groups[key][k]+=row[k]
    return sorted(groups.values(),key=lambda x:(x.get("room",""),-x["vertices"],-x["parts"],
        tuple(str(x[k]) for k in fields),x["reason"],x["status"]))


def tsv(rows, fields):
    out=io.StringIO(newline="")
    writer=csv.DictWriter(out,fieldnames=fields,delimiter="\t",lineterminator="\n",extrasaction="ignore")
    writer.writeheader()
    writer.writerows({k:json.dumps(v,sort_keys=True,separators=(",",":")) if isinstance(v,(dict,list)) else v
                     for k,v in row.items()} for row in rows)
    return out.getvalue()


def render_report(result):
    lines=["# Build 29 fallback asset scan", "",f"Status: **{result['status']}**. Models: {result['models']}; texture keys: {result['textures']}.",
        "", "Counts are static potential work per part (world vertices use level 0). They are not observed draws, frame cost, or additive reason totals.",
        "Raw ModelData vertices are unique source corner tuples: runtime conversion may duplicate them across meshlets. Stored FE/world records retain their own counts; see vertex_basis.",
        "Several LODs/appearances and source fallback/replacement models may coexist. Visibility, instance multiplicity and active selection remain runtime facts.",
        "An absent reason is not proof of a fast frame. Unknown lighting, view and residency fields stay in details.tsv.","", "## Ranked by room and model", "",
        "| Room | Model | Reason | Status | Parts | Vertices |", "|---|---|---|---|---:|---:|"]
    ranked=aggregate(result["rows"],("room","source","model","label"))
    for r in ranked:
        label=(r["source"]+" :: "+r["label"]).replace("|","\\|")
        lines.append(f"| {r['room']} | {label} | {r['reason']} | {r['status']} | {r['parts']} | {r['vertices']} |")
    if not ranked: lines.append("| — | No statically resolved trigger | — | — | 0 | 0 |")
    lines += ["", "## Barn attribution", "", "r103 potential light-scale/probe cases are in barn.tsv, including unknown predicates.",
        "Use the source path, exact model key, part index/offset and SHA256 in context-template.json to bind the Ganado, pitchfork, hay and barn props to console capture rows.",
        "The scanner does not invent those labels from filenames or use a model ID alone as proof. Source assets do not store runtime material RGB/TEV/light selection.",
        "Model byte ranges, source material fields, placements and per-meshlet metadata are in report.json/model_inventory; native ESL spawn candidates are in spawns.tsv.",
        "ESL lists are story-dependent alternatives. Their enemy IDs and positions help locate candidates but do not authenticate an asset binding or prove the actor is present.",
        "After binding context, rerun and compare a_probe_miss, a_lit_scale and a_lit_exact separately: probe decline can still use the generic fast fold.",
        "A Build 29 baked tag is only a candidate: live adapter guards can still select the previous renderer.","", "## Coverage and refusals", ""]
    gaps=[x for x in result["coverage"] if x["status"]!="scanned"]
    if not gaps: lines.append("All recognised supplied formats and requested room inventories were scanned; runtime admission and private-data/visual gates remain separate.")
    for c in gaps: lines.append(f"- `{c['source']}` ({c['format']}): {c['status']} — {c['message']}")
    lines += ["", "## Cost interpretation", "", "This tool adds zero runtime cycles/loads/stores/code/stack; MODELLED whole-frame delta is 0 ms for the scanner itself.",
        "Potential transformed vertices and meshlet/part counts are ranking inputs. No guessed light/cache timing is multiplied into an FPS claim.",
        "Use the Build 29 sweep cost table and actual drawn-tick populations; cache-line footprints are not hardware cache misses.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tree",type=Path,help="extracted/composed disc root containing dc/ and st*/em/")
    ap.add_argument("--out",type=Path,required=True,help="new output directory outside the input tree")
    ap.add_argument("--rooms",default=",".join(f"r{x:03x}" for x in range(0x100,0x120)),help="comma-separated chapter 1-2 room ids")
    ap.add_argument("--knobs",type=Path,help="exact image resolved-knobs.txt; omitted means unknown recipe values")
    ap.add_argument("--context",type=Path,help="hash-bound runtime lighting/owner context JSON")
    ap.add_argument("--room-list",type=Path,help="explicit room-to-source/model membership JSON")
    ap.add_argument("--input",type=Path,action="append",default=[],help="additional compiled PS2 header/standalone package (repeatable)")
    ap.add_argument("--strict",action="store_true",help="exit 1 for rejected/missing coverage as well as malformed context")
    args=ap.parse_args(argv)
    try:
        formats.require(not args.out.exists(),"output directory already exists; use a new destination")
        formats.require(not args.out.resolve().is_relative_to(args.tree.resolve()),"output must be outside the input tree")
        rooms=sorted(set(room_name(x) for x in args.rooms.split(",") if x.strip()))
        formats.require(rooms,"empty room selection")
        knobs,knob_source=read_knobs(args.knobs)
        result=scan_tree(args.tree,rooms,knobs,json.loads(args.context.read_text()) if args.context else None,
            json.loads(args.room_list.read_text()) if args.room_list else None,args.input)
        result["knob_source"]=knob_source
        result["knobs"]=knobs
        template=result.pop("context_template")
        reports={"details.tsv":tsv(result["rows"],ROW_FIELDS),
                 "by-model.tsv":tsv(aggregate(result["rows"],("room","source","model","label")),
                     ("room","source","model","label","reason","status","parts","vertices","corners","meshlets")),
                 "by-room.tsv":tsv(aggregate(result["rows"],("room",)),
                     ("room","reason","status","parts","vertices","corners","meshlets")),
                 "barn.tsv":tsv([r for r in result["rows"] if r["room"]=="r103" and r["reason"] in
                     ("a_probe_miss","a_lit_scale","a_lit_exact","a_lit_colour","a_lit_fourth","a_lit_basis")],ROW_FIELDS),
                 "spawns.tsv":tsv(result["spawn_inventory"],("room","source","source_sha256","location","index","enemy_id",
                     "type","character","set","be_flag","flags","hp","position","rotation_raw","guard_radius","status","active")),
                 "coverage.tsv":tsv(result["coverage"],("source","format","status","models","message")),
                 "report.json":json.dumps(result,indent=2,sort_keys=True)+"\n",
                 "context-template.json":json.dumps(template,indent=2,sort_keys=True)+"\n",
                 "REPORT.md":render_report(result)}
        args.out.mkdir(parents=True)
        for name,text in reports.items(): (args.out/name).write_text(text)
        print(f"{result['status']}: {result['models']} models, {result['textures']} texture keys; {args.out}/REPORT.md")
        return 1 if args.strict and result["status"]!="SCANNED" else 0
    except (ValueError,OSError,UnicodeError) as exc:
        print("fallback_scan: "+str(exc),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

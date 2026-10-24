#!/usr/bin/env python3
"""Exact host UI checks over extracted production bodies and synthetic inputs.

The bridge, enqueue, both quad drains, glyph run and message camera are the real
source. KOS vertex/header/context declarations and header compilation are real.
Only the cache-allocation edge is modeled: packed-color header words 4..7 are
unspecified on a fresh compile and excluded from that comparison. Preseeded
cache-hit headers and all vertex words are compared in full. No game data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
NATIVE = ROOT / "port/dreamcast/game/platform/native_ui.cpp"
BRIDGE = ROOT / "port/dreamcast/game/ui_bridge.cpp"
MES = ROOT / "src/game/mes.cpp"
GX = ROOT / "port/dreamcast/game/platform/gx_stub.cpp"
MTX = ROOT / "src/lib/mtx.c"
MTX44 = ROOT / "src/lib/mtx44.c"
GEOMETRY = ROOT / "port/dreamcast/room/pvr_geometry.cpp"
PACKAGE = ROOT / "port/dreamcast/room/texture_package.cpp"
PACKAGE_HEADER = ROOT / "port/dreamcast/room/texture_package.hpp"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def block(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth, cursor = 1, brace + 1
    while depth:
        depth += (source[cursor] == "{") - (source[cursor] == "}")
        cursor += 1
    return source[start:cursor]


def declarations(text):
    return "\n".join(line for line in text.splitlines() if not line.startswith("#include"))


def defines(text, names=None):
    result = []
    lines = iter(re.sub(r"/\*.*?\*/", "", text, flags=re.S).splitlines())
    for line in lines:
        m = re.match(r"#define\s+(\w+)(?:\([^)]*\))?", line)
        if not m or (names is not None and not names(m.group(1))):
            continue
        full = line
        while full.rstrip().endswith("\\"):
            full += "\n" + next(lines)
        result.append(full)
    return "\n".join(result)


def kos_sources(profile):
    pvr = Path(profile["pvr_header_overlay"]["source"])
    assert sha(pvr) == profile["pvr_header_overlay"]["source_sha256"]
    kos = pvr.parents[5]
    return {"pvr": pvr, "header": pvr.parent / "pvr/pvr_header.h",
            "regs": pvr.parent / "pvr/pvr_regs.h", "legacy": pvr.parent / "pvr/pvr_legacy.h",
            "fields": kos / "include/kos/regfield.h",
            "prim": kos / "kernel/arch/dreamcast/hardware/pvr/pvr_prim.c"}


def kos_blocks(paths):
    pvr, header, prim = (paths[n].read_text() for n in ("pvr", "header", "prim"))
    types = header[header.index("typedef enum pvr_color_fmts"):header.index("static inline pvr_txr_ptr_t")]
    types += header[header.index("typedef struct pvr_poly_hdr_cmd"):header.index("_Static_assert")]
    types += pvr[pvr.index("typedef enum pvr_mip_bias"):pvr.index("} pvr_poly_cxt_t;") + len("} pvr_poly_cxt_t;")]
    types += block(pvr, "typedef struct pvr_vertex {") + " pvr_vertex_t;\n"
    types += "static_assert(sizeof(pvr_vertex_t)==32 && alignof(pvr_vertex_t)==32);\n"
    types += "static_assert(sizeof(pvr_poly_hdr_t)==32 && alignof(pvr_poly_hdr_t)==32);\n"
    types += "static_assert(offsetof(pvr_vertex_t,oargb)==28 && offsetof(pvr_vertex_t,u)==16);\n"
    constants = defines(pvr, lambda n: n.startswith(("PVR_CMD_", "PVR_TXRFMT_", "PVR_TA_")))
    constants += "\n" + defines(paths["regs"].read_text(), lambda n: n.startswith("PVR_TA_"))
    constants += "\n" + defines(paths["legacy"].read_text(), lambda n: n in (
        "PVR_DEPTHWRITE_ENABLE", "PVR_DEPTHWRITE_DISABLE", "PVR_BLEND_DISABLE"))
    constants += "\n" + defines(paths["fields"].read_text(), lambda n: n in ("BIT", "GENMASK", "FIELD_PREP"))
    pointer = block(header, "static inline pvr_txr_ptr_t to_pvr_txr_ptr(")
    pointer = pointer.replace("(uint32_t)addr", "(uint32_t)(uintptr_t)addr")
    return {"KOS_TYPES": types, "KOS_CONSTANTS": constants,
            "KOS_COMPILER": pointer + "\n" + block(prim, "void pvr_poly_compile(").replace("void pvr_poly_compile(", "void fixture_real_pvr_poly_compile(", 1) + "\n" + block(prim, "void pvr_poly_cxt_txr(")}


def native_blocks(source):
    start = source.index("// One run: a header when the palette bank changes")
    glyph_run = source[start:source.index("short glyph_quarter(", start)]
    ui = block(source, "static void ui_draw_quad(unsigned i)")
    # Conditional initializer variants contain two alternative opening braces.
    # The drain is delimited by its next actual source declaration instead.
    start = source.index("static void ui_draw_quad(unsigned i)")
    ui = source[start:source.index("static void ui_order_flush()", start)]
    order = block(source, "static void ui_order_flush()")
    start = source.index("    for(unsigned i=0;i<nquad && !movie_override && !re4dc_vi_black();++i){")
    end = source.index("\n#endif\n#if RE4DC_DOOR_FREEZE", start)
    legacy = source[start:end]
    return {
        "ENTRY": source[source.index("struct Key {"):source.index("#ifndef RE4DC_TEX_PAYLOAD_RETRY")]
            + source[source.index("struct Entry {"):source.index("struct Source {")],
        "COVER_MACROS": source[source.index("#if defined(RE4DC_FX_PS2_PACK)"):source.index("#if defined(RE4DC_FX_TEX_POOL)")],
        "GLYPH_TYPES": source[source.index("#ifndef RE4DC_NATIVE_MES_CELLS"):source.index("pvr_ptr_t glyph_atlas;")],
        "GLYPH_HEADER": block(source, "const pvr_poly_hdr_t& glyph_header(unsigned bank)"),
        "GLYPH_RUN": glyph_run,
        "NATIVE_ENQUEUE": block(source, 'extern "C" void re4dc_ui_submit(const Re4dcUiQuad* q)').replace(
            "{\n    RE4DC_PROFILE_SCOPE", "{\n    fixture_native_enqueue_note(q);\n    RE4DC_PROFILE_SCOPE", 1),
        "NATIVE_DRAW": ui,
        "NATIVE_ORDER": order,
        "NATIVE_LEGACY": legacy,
        "OVERLAY_DEPTH": "#if RE4DC_WORLD_AUTOSORT\n" + block(source, "float overlay_depth(){") +
            "\n#else\n" + block(source, "constexpr float overlay_depth(){") + "\n#endif\n",
        "BEGIN_PACKET": block(GEOMETRY.read_text(), "void begin_pvr_packet("),
        "HEADER_WRAPPER": "#if RE4DC_TEX_MIP_DADJ\n" + block(source, 'extern "C" void __wrap_pvr_poly_compile(').replace("__wrap_pvr_poly_compile", "pvr_poly_compile").replace("__real_pvr_poly_compile", "fixture_real_pvr_poly_compile") +
            "\n#else\nstatic void pvr_poly_compile(pvr_poly_hdr_t* dst,const pvr_poly_cxt_t* src){fixture_real_pvr_poly_compile(dst,src);}\n#endif"}


def bridge_blocks(source):
    start = source.index("#ifndef RE4DC_UI_QUAD_LEAN")
    helpers = source[start:source.index('extern "C" void re4dc_draw_id_quad')]
    helpers = declarations(helpers)
    idunit = block((ROOT / "include/id_sys.h").read_text(), "struct IdUnit {") + ";"
    tpl = declarations((ROOT / "include/tpl.h").read_text()).replace("CLUTHeader* CLUTHeader;", "struct CLUTHeader* CLUTHeader;")
    texture = (ROOT / "include/texture.h").read_text()
    gxstruct = (ROOT / "include/dolphin/gx/GXStruct.h").read_text()
    textures = block(gxstruct, "typedef struct _GXTexObj {") + " GXTexObj;\n"
    textures += block(gxstruct, "typedef struct _GXTlutObj {") + " GXTlutObj;\n"
    textures += block(texture, "struct TexAnm {") + ";\n" + block(texture, "struct TexWk {") + ";\n"
    return {"ID_UNIT": idunit, "TPL": tpl, "TEXTURE_TYPES": textures, "BRIDGE_HELPERS": helpers,
            "BRIDGE_DRAW": block(source, 'extern "C" void re4dc_draw_id_quad(const IdUnit* u)')}


def math_blocks(mes):
    gx, mtx = GX.read_text(), MTX.read_text()
    getter_start = gx.index("#if defined(RE4DC_RES_ALTERNATE)", gx.index("void GXSetViewport("))
    getter_end = gx.index("void GXSetScissor(", getter_start)
    camera = (ROOT / "src/game/camera.cpp").read_text()
    return {
        "GX_VIEWPORT": block(gx, "void GXSetViewport(") + "\n" + gx[getter_start:getter_end],
        "GX_PROJECTION": block(gx, "void GXSetProjection(").replace("{\n", "{\n    fixture_projection_note(mtx,type);\n", 1) + "\n" + block(gx, "void GXGetProjectionv(") + "\n" + block(gx, "void GXProject("),
        "GX_EMPTY": block(gx, "void GXLoadPosMtxImm(").replace("{", "{ ++empty_load_calls;", 1) + "\n" + block(gx, "void GXSetCurrentMtx(").replace("{", "{ ++empty_current_calls;", 1),
        "GXF_HEADER": (ROOT / "port/dreamcast/game/gx_fast.h").read_text().replace('"+f"(t)', '"+x"(t)'),
        "CAMERA_CURRENT": block(camera, "void CameraSetProjection(int type)") + "\n" + block(camera, "void CameraCurrentProjection()"),
        "MATRIX_BODIES": "\n".join(block(mtx, sig) for sig in ("void C_MTXIdentity(", "void C_MTXCopy(", "void C_MTXConcat(")) + "\n__attribute__((noinline,noclone)) " + block(MTX44.read_text(), "void C_MTXOrtho("),
        "MESSAGE_CAMERA": block(mes, "void messageCamera()\n")}


def fixture(profile, texts):
    ks = kos_sources(profile)
    replacements = kos_blocks(ks) | native_blocks(texts["native"]) | bridge_blocks(texts["bridge"]) | math_blocks(texts["mes"])
    package_header = declarations(PACKAGE_HEADER.read_text()).replace("private:", "public: // fixture population only; actual layout retained")
    package_body = PACKAGE.read_text()
    replacements["PACKAGE_HEADER"] = package_header
    replacements["PACKAGE_GETTERS"] = "\n".join(block(package_body, sig) for sig in (
        "const Texture* Package::textures() const", "pvr_ptr_t Package::pvr_texture(", "std::uint32_t pvr_format("))
    replacements["ROOT"] = str(ROOT)
    content = "\n".join((HERE / name).read_text() for name in ("fixture_common.cpp.in", "fixture_native.cpp.in", "fixture_bridge.cpp.in", "fixture_cases.cpp.in"))
    for name, value in replacements.items():
        content = content.replace("@" + name + "@", value)
    assert not re.search(r"@[A-Z_]+@", content), re.findall(r"@[A-Z_]+@", content)
    return content, ks


MACROS = set("RE4DC_UI_HEADERS RE4DC_UI_HANDLES RE4DC_UI_QUAD_LEAN RE4DC_UI_HUD_MASK RE4DC_NATIVE_MES RE4DC_NATIVE_MES_CELLS RE4DC_SS_UI_ORDER RE4DC_D349_RENDERER_STACK RE4DC_PVR_STREAM RE4DC_WORLD_AUTOSORT RE4DC_RES_MODES RE4DC_RES_ALTERNATE RE4DC_GC_CENSUS_TRIM RE4DC_GXF_JITTER RE4DC_COPY_LEAN RE4DC_FX_PS2_PACK RE4DC_GANADO_ATLAS_DROP RE4DC_CAST_MIPMAP RE4DC_TEX_PAL4_ALPHA RE4DC_TEX_PAL8_ALPHA RE4DC_TEX_PAL4_MIPMAP RE4DC_TEX_PAL8_MIPMAP RE4DC_TREE_IMPOSTOR RE4DC_PAD_PROMPTS RE4DC_OPTION_ROW_STYLE RE4DC_RENDER_OPTION RE4DC_LETTERBOX_CLIP RE4DC_DOOR_FREEZE RE4DC_TEX_PACK RE4DC_TEX_PACK_WINDOW RE4DC_TEX_MIP_DADJ".split())


def profile_macros(row):
    values = {}
    for path, digest in row["generated_headers"].items():
        assert sha(path) == digest, (path, "generated header changed")
        for name, value in re.findall(r"^#define\s+(\w+)\s+([^\n]+)", Path(path).read_text(), re.M):
            if name in MACROS:
                values[name] = value.split("//")[0].strip()
    for flag in row["flags"]:
        m = re.fullmatch(r"-D(\w+)(?:=(.*))?", flag)
        if m and m[1] in MACROS:
            values[m[1]] = m[2] or "1"
    return values


VARIANTS = {
    "public": {},
    "legacy_order": {"RE4DC_SS_UI_ORDER": "0", "RE4DC_WORLD_AUTOSORT": "0"},
    "uncached": {"RE4DC_UI_HEADERS": "0", "RE4DC_UI_HANDLES": "0"},
    "old_quad": {"RE4DC_UI_QUAD_LEAN": "0", "RE4DC_GC_CENSUS_TRIM": "0"},
    "quad_diag": {"RE4DC_UI_QUAD_LEAN": "2"},
    "glyph128": {"RE4DC_NATIVE_MES_CELLS": "128"},
    "no_glyph": {"RE4DC_NATIVE_MES": "0"},
    "hooks": {"RE4DC_PAD_PROMPTS": "1", "RE4DC_OPTION_ROW_STYLE": "1", "RE4DC_RENDER_OPTION": "1", "RE4DC_LETTERBOX_CLIP": "1"},
}


def mutate(texts, name):
    texts = dict(texts)
    if name == "palette-default":
        source, old, new = "bridge", "q.image.palette_bytes = 0;", "q.image.palette_bytes = 2;"
    elif name == "offset-color":
        source, old, new = "native", "v[n].oargb=0;", "v[n].oargb=0x12345678;"
    elif name == "camera-constant":
        source, old, new = "mes", "2.0f * (1.0f / 512.0f)", "4.0f * (1.0f / 512.0f)"
    elif name == "glyph-corner":
        source, old, new = "native", "vertex(x1,y1,u1,v1,PVR_CMD_VERTEX_EOL);", "vertex(x0,y1,u1,v1,PVR_CMD_VERTEX_EOL);"
    else:
        raise AssertionError(name)
    assert texts[source].count(old) == (2 if name == "offset-color" else 1), name
    texts[source] = texts[source].replace(old, new)
    return texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=("smoke", "all", "sanitizer", "negative"), default="all")
    parser.add_argument("--variants", nargs="+", choices=tuple(VARIANTS))
    parser.add_argument("--profiles", nargs="+")
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    profile = json.loads(args.profile.read_text())
    texts = {name: path.read_text() for name, path in (("native", NATIVE), ("bridge", BRIDGE), ("mes", MES))}
    profiles = args.profiles or (list(profile["profiles"]) if args.mode == "all" else ["public"])
    assert set(profiles) <= set(profile["profiles"]), "unknown profile"
    variants = args.variants or ["public"]
    controls = [None] if args.mode != "negative" else ["palette-default", "offset-color", "camera-constant", "glyph-corner"]
    rows = []
    for control in controls:
        for profile_name, variant in ((p,v) for p in profiles for v in variants):
            base = profile_macros(profile["profiles"][profile_name]["native_ui"])
            for name, value in profile_macros(profile["profiles"][profile_name]["ui_bridge"]).items():
                base.setdefault(name, value)
            outputs = []
            scalar_outputs = []
            for lean in (0, 1):
                content, ks = fixture(profile, mutate(texts, control) if control and lean else texts)
                label = f"{profile_name}-{variant}-{control or 'normal'}-{lean}"
                cpp, exe, output = (args.output / (label + ext) for ext in (".cpp", "", ".bin"))
                cpp.write_text(content)
                macros = base | VARIANTS[variant] | {"RE4DC_GAME": "1", "RE4DC_UI_DRAW_LEAN": str(lean)}
                command = [args.cxx, "-std=gnu++17", "-O2", "-fno-strict-aliasing", "-fno-fast-math", "-ffp-contract=off", "-Wno-attributes"]
                if args.mode == "sanitizer":
                    command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g"]
                command += [f"-D{k}={v}" for k, v in sorted(macros.items())] + [str(cpp), "-o", str(exe)]
                compile_result = subprocess.run(command, capture_output=True)
                (args.output / (label + ".compile.log")).write_bytes(compile_result.stdout + compile_result.stderr)
                assert compile_result.returncode == 0, (label, compile_result.stderr.decode()[-9000:])
                run = subprocess.run([str(exe), str(output)], capture_output=True, env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
                (args.output / (label + ".stdout")).write_bytes(run.stdout)
                (args.output / (label + ".stderr")).write_bytes(run.stderr)
                if control and lean and run.returncode != 0:
                    assert control=="camera-constant" and b"Assertion" in run.stderr and b"projection_matrix,reference" in run.stderr, (label,"unrelated failure",run.stderr.decode())
                    outputs.append(None)
                    rows.append(dict(profile=profile_name,variant=variant,lean=lean,negative_control=control,
                        detected="independent full-matrix assertion",stderr=run.stderr.decode(),fixture_sha256=sha(cpp),macros=macros,command=command))
                    continue
                assert run.returncode == 0, (label, run.returncode, run.stderr.decode()[-9000:])
                assert not run.stderr, (label, run.stderr.decode()[-9000:])
                data = output.read_bytes(); outputs.append(data)
                scalar_path=Path(str(output)+".ta"); scalar=scalar_path.read_bytes();scalar_outputs.append(scalar)
                rows.append(dict(profile=profile_name,variant=variant, lean=lean, negative_control=control, output_bytes=len(data), output_sha256=sha(output),
                    scalar_ta_bytes=len(scalar),scalar_ta_sha256=sha(scalar_path),stats=json.loads(run.stdout), fixture_sha256=sha(cpp), macros=macros, command=command))
            assert (outputs[0] == outputs[1]) != bool(control), (variant, control, "differential result")
            if not control:assert scalar_outputs[0]==scalar_outputs[1], (profile_name,variant,"scalar TA mismatch")
            print("PASS", profile_name,variant, control or "normal", len(outputs[0]), flush=True)
    assert texts == {name: path.read_text() for name, path in (("native", NATIVE), ("bridge", BRIDGE), ("mes", MES))}, "runtime changed"
    dependencies = [NATIVE, BRIDGE, MES, GX, MTX, MTX44, GEOMETRY, PACKAGE, PACKAGE_HEADER,
        ROOT / "include/id_sys.h", ROOT / "include/tpl.h", ROOT / "include/texture.h", ROOT / "include/dolphin/gx/GXStruct.h", ROOT / "src/game/camera.cpp",
        ROOT / "port/dreamcast/game/gx_fast.h", ROOT / "port/dreamcast/game/platform/include/native_ui.h",
        ROOT / "port/dreamcast/game/platform/include/re4dc_screen.h", Path(__file__), *HERE.glob("fixture_*.cpp.in")]
    receipt = dict(status="PASS", scope=__doc__, mode=args.mode, profile_sha256=sha(args.profile),
        source_and_tool_sha256={str(p.relative_to(ROOT)): sha(p) for p in dependencies},
        kos_sha256={name: {"path": str(p), "sha256": sha(p)} for name, p in ks.items()}, configurations=rows)
    (args.output / "runtime_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build18 production-extracted queue/packet gate; no game data or console.

Reuses esp_setup_lean/check_runtime.py extraction and runtime_queue.cpp.in.
Real effect/model/UI enqueue, packet and FIFO drain code runs with fake texture,
PVR compiler, room lifecycle and heap-4 provider boundaries. Four ASan/UBSan
variants compare the base, option absent, explicit zero and enabled candidate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PLATFORM = ROOT / "port/dreamcast/game/platform"
INCLUDE = PLATFORM / "include"
EXISTING = ROOT / "port/dreamcast/tools/d367/esp_setup_lean"
TEST = Path(__file__).with_name("fx_r200_entry_cap_test.cpp")
NATIVE = "port/dreamcast/game/platform/native_ui.cpp"
INCLUDES = "port/dreamcast/game/platform/include/"
SOURCE_NAMES = [
    NATIVE, INCLUDES + "fx_r200_entry_cap.h", INCLUDES + "native_effect_haze_batch.inc",
    INCLUDES + "native_effect_stage1_batch.inc", INCLUDES + "native_effect_strip21.inc",
    INCLUDES + "fx_sprite_trim.inc", INCLUDES + "fx_sprite_trim_table.inc",
    INCLUDES + "native_ui.h", INCLUDES + "native_model.h", INCLUDES + "effect_strip_geometry21.hpp",
    INCLUDES + "re4dc_screen.h", INCLUDES + "native_render_profile.hpp",
    "port/dreamcast/room/pvr_geometry.cpp", "port/dreamcast/room/pvr_geometry.hpp",
    "port/dreamcast/room/native_draw_plan.hpp", "port/dreamcast/room/source_lighting.hpp",
    "port/dreamcast/tools/d367/esp_setup_lean/check_runtime.py",
    "port/dreamcast/tools/d367/esp_setup_lean/runtime_queue.cpp.in",
    "port/dreamcast/tests/fx_r200_entry_cap_test.cpp", "port/dreamcast/tests/test_fx_r200_entry_cap.py",
]

spec = importlib.util.spec_from_file_location("build6_runtime_extract", EXISTING / "check_runtime.py")
extract = importlib.util.module_from_spec(spec)
assert spec.loader
sys.dont_write_bytecode = True
spec.loader.exec_module(extract)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha((ROOT / name).read_bytes()) for name in SOURCE_NAMES}


def replace_once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise RuntimeError(f"Extraction scaffold changed: expected one occurrence of {before[:90]!r}")
    return text.replace(before, after, 1)


def marked(source: str, begin: str, end: str) -> str:
    start = source.index("\n", source.index(begin)) + 1
    stop = source.rfind("//", start, source.index(end))
    return source[start:stop]


def definition(source: str, signature: str) -> str:
    """Select a definition, skipping an earlier forward declaration."""
    offset = 0
    while True:
        start = source.index(signature, offset)
        brace, semicolon = source.find("{", start), source.find(";", start)
        if brace >= 0 and (semicolon < 0 or brace < semicolon):
            return extract.function(source[start:], signature)
        offset = start + len(signature)


def production(name: str, base: str | None = None) -> str:
    if base is None:
        return (ROOT / name).read_text()
    result = subprocess.run(["git", "show", f"{base}:{name}"], cwd=ROOT, text=True, capture_output=True, check=True)
    return result.stdout


PVR_STUB = r'''#pragma once
#include <cstddef>
#include <cstdint>
struct alignas(32) pvr_poly_hdr_t {unsigned cmd,mode1,mode2,mode3,argb,oargb,d1,d2;};
using pvr_sprite_hdr_t=pvr_poly_hdr_t;
struct alignas(32) pvr_sprite_txr_t {unsigned flags;float ax,ay,az,bx,by,bz,cx,cy,cz,dx,dy;unsigned dummy,auv,buv,cuv;};
struct alignas(32) pvr_vertex_t {unsigned flags;float x,y,z,u,v;unsigned argb,oargb;};
static_assert(sizeof(pvr_poly_hdr_t)==32 && sizeof(pvr_sprite_txr_t)==64 && sizeof(pvr_vertex_t)==32);
enum pvr_blend_mode_t {PVR_BLEND_ZERO=0,PVR_BLEND_ONE=1,PVR_BLEND_SRCALPHA=4,PVR_BLEND_INVSRCALPHA=5};
using pvr_list_t=unsigned;
using pvr_uv_clamp_t=unsigned;
enum {PVR_LIST_OP_POLY=0,PVR_LIST_TR_POLY=2,PVR_CULLING_NONE=0,PVR_DEPTHCMP_GEQUAL=3,PVR_DEPTHCMP_ALWAYS=7,
    PVR_DEPTHWRITE_DISABLE=1,PVR_DEPTHWRITE_ENABLE=0,PVR_TXRENV_MODULATEALPHA=1,
    PVR_UVCLAMP_U=1,PVR_UVCLAMP_V=2,PVR_UVCLAMP_UV=3,PVR_TXRALPHA_ENABLE=1,PVR_SHADE_GOURAUD=1,
    PVR_FOG_DISABLE=0,PVR_FOG_TABLE=1,PVR_FILTER_BILINEAR=1};
constexpr unsigned PVR_CMD_VERTEX=0xe0000000U,PVR_CMD_VERTEX_EOL=0xf0000000U;
inline int pvr_prim(const void*,std::size_t){return 0;}
'''

CONFIG = {
    "RE4DC_NATIVE_STATIC": 1, "RE4DC_D349_RENDERER_STACK": 1, "RE4DC_PVR_STREAM": 1,
    "RE4DC_MODEL_DRAW_PLANS": 1, "RE4DC_EFFECT_SPRITES": 1, "RE4DC_EFFECT_SPRITE_MAX": 64,
    "RE4DC_FX_ROOM_SPILL_KB": 24, "RE4DC_FX_QUEUE_MARGIN": "8192U",
    "RE4DC_ESP_SPRITE_FAST": 1, "RE4DC_ESP_SETUP_LEAN": 1, "RE4DC_EFFECT_ROOM": 1,
    "RE4DC_FX_SPRITE_TRIM": 2, "RE4DC_EFFECT_HAZE_LEAN": 4, "RE4DC_NATIVE_LASER": 1,
    "RE4DC_FX_STRIP21": 1, "RE4DC_CLOTH_NATIVE": 1,
    "RE4DC_PS2_FX_COMMON_HAZE": 1, "RE4DC_PS2_FX_ADDITIONS": 1,
    "RE4DC_COPY_LEAN": 1, "RE4DC_BRIDGE_LEAN": 1, "RE4DC_UI_HANDLES": 1,
    "RE4DC_RES_MODES": 0, "RE4DC_NATIVE_FOG": 0, "RE4DC_WORLD_AUTOSORT": 1,
    "RE4DC_WORLD_HOLE_FIX": 1,
}


def scaffold(base: str | None = None) -> str:
    source = production(NATIVE, base)
    template = (EXISTING / "runtime_queue.cpp.in").read_text().split("int main(int argc,char** argv){", 1)[0]
    template = replace_once(template, '#include "native_ui.h"', '#include "native_model.h"\n#include "native_render_profile.hpp"\n#include "pvr_geometry.hpp"')
    start = template.index("struct alignas(32) pvr_poly_hdr_t")
    stop = template.index("struct pvr_sprite_cxt_t", start)
    template = template[:start] + '#include <dc/pvr.h>\n' + template[stop:]
    template = replace_once(template, "struct{unsigned culling,fog_type;}gen;", "struct{unsigned culling,fog_type,shading;}gen;")
    template = replace_once(template, "struct{unsigned env,uv_clamp;}txr;", "struct{unsigned env,uv_clamp,alpha;}txr;")
    template = replace_once(template, "using pvr_poly_cxt_t=pvr_sprite_cxt_t;", "using pvr_poly_cxt_t=pvr_sprite_cxt_t;\nvoid pvr_poly_cxt_col(pvr_poly_cxt_t* c,unsigned list){*c={};c->list=list;}")
    support = source[source.index("using SourceLighting=re4dc::render::SourceLighting;") : source.index("DeferredPart* deferred_first=nullptr;")]
    template = replace_once(template, "struct DeferredLighting {};\nstruct DeferredPart {DeferredPart* next;DeferredLighting* lighting;unsigned changed[2];};\n@BATCH_ENABLE@", support)
    template = replace_once(template, "void* deferred_light_sets=nullptr;void* deferred_basis=nullptr;void* deferred_lights=nullptr;\n", "")
    template = replace_once(template, "alignas(32) unsigned char frame_storage[32768],spill[4096];", "constexpr unsigned kQuadCount=256;\nalignas(32) unsigned char frame_storage[kQuadCount*sizeof(Re4dcUiQuad)];\nauto& spill=gate::room_cell;")
    template = replace_once(template, "namespace re4dc::render { bool is_finite(float v){return std::isfinite(v);} }", "")
    template = replace_once(template, "#define RE4DC_SCREEN_WF (640.0f*re4dc_ui_sx)\n#define RE4DC_SCREEN_HF (480.0f*re4dc_ui_sy)", '#include "re4dc_screen.h"')
    template = replace_once(template, "Entry entries[4];", "Entry entries[4];\nEntry* handles[kQuadCount]{};\nRe4dcUiQuad* const quads=reinterpret_cast<Re4dcUiQuad*>(frame_storage);\nunsigned dropped,culled,unsupported,missing,drawn,frame_queue_drops,deferred_drops,deferred_peak;")
    template = replace_once(template, "#define AVD_EVENT(...) ((void)0)", "#define AVD_EVENT(...) ((void)0)\n#define RE4DC_WHD_ABORT(...) ((void)0)\nvoid whfix_drop(unsigned){}\nextern \"C\" void re4dc_model_result(unsigned,unsigned,unsigned){}")
    old_log = extract.function(template, "void re4dc_log(")
    template = replace_once(template, old_log, r'''void re4dc_log(const char* fmt,...){
    char b[512];va_list ap;va_start(ap,fmt);int n=vsnprintf(b,sizeof b,fmt,ap);va_end(ap);
    CHECK(n>=0 && n<int(sizeof b));gate::logs.emplace_back(b);
}''')

    constants_begin = source.index("#if defined(RE4DC_FRAME_QUEUE_SPILL_KB)")
    constants_end = source.index("pvr_vertex_t* model_packets;", constants_begin)
    constants = source[constants_begin:constants_end] + "pvr_vertex_t* model_packets=nullptr;\n"
    provider = extract.conditional(source, "#if defined(RE4DC_FX_ROOM_SPILL_KB)") + "\n" + definition(source, 'extern "C" void* re4dc_model_deferred_storage(')
    state = adapter = ""
    if "FX_R200_TAIL_STATE_BEGIN" in source:
        state = '#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP\n#include "fx_r200_entry_cap.h"\nnamespace {\n' + marked(source, "FX_R200_TAIL_STATE_BEGIN", "FX_R200_TAIL_STATE_END") + "}\n#endif\n"
        adapter = '#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP\n' + marked(source, "FX_R200_TAIL_ADAPTER_BEGIN", "FX_R200_TAIL_ADAPTER_END") + "\n#endif\n"
    old_provider = extract.function(template, "void* re4dc_model_deferred_storage(")
    template = replace_once(template, old_provider, constants + state + provider + "\n" + adapter)
    old_stream = extract.function(template, "void stream_send(")
    template = replace_once(template, old_stream, r'''void stream_send(const void* data,unsigned count){
    sent_bytes+=count;gate::Packet packet{1,{}};
    auto append=[&](const void* p,unsigned n){const auto* b=static_cast<const unsigned char*>(p);packet.bytes.insert(packet.bytes.end(),b,b+n);};
    if(count==64){CHECK(header_valid);append(&active_header,32);append(data,count);++sent_sprites;++body_packets;}
    else {CHECK(count>=32);memcpy(&active_header,data,32);header_valid=true;append(data,count);if(count==96)++sent_sprites;}
    gate::packets.push_back(std::move(packet));
    if(abort_after&&sent_sprites>=abort_after)stream_aborted=true;
}''')
    template = replace_once(template, extract.function(template, "void stream_select("), "void stream_select(unsigned list){CHECK(list==PVR_LIST_TR_POLY);}")

    packet_begin = source.index("DeferredLighting* const kSpriteTag=")
    packet_end = source.index("\n}\n}\n#if defined(RE4DC_EFFECT_ROOM)", packet_begin) + 2
    packet = source[packet_begin:packet_end].replace('#include "include/fx_sprite_trim.inc"', '#include "fx_sprite_trim.inc"')
    # Complete actual packet helpers include both kinds of octagon. Strip/cloth
    # additionally link the real pvr_geometry.cpp clipping implementation.
    models = extract.function(source, "pvr_list_t select_model_pass(") + "\n" + extract.function(source, "int defer_part(") + "\n" + extract.function(source, 'extern "C" int re4dc_model_defer_part(')
    models += "\n" + extract.function(source, 'extern "C" void re4dc_ui_submit(')
    models += '\nextern "C" void re4dc_model_invalidate_static_lighting(){++gate::invalidations;}\n'
    models += extract.function(source, 'extern "C" void re4dc_model_invalidate_pending(')
    models += r'''
extern "C" void re4dc_model_submit(const Re4dcModelPart* view){
    const unsigned values[]={view->serial,view->blend,view->alpha_state,view->material_flags,view->depth_mode};
    gate::Packet packet{2,{}};const auto* bytes=reinterpret_cast<const unsigned char*>(values);
    packet.bytes.assign(bytes,bytes+sizeof(values));gate::packets.push_back(std::move(packet));
}
'''
    batches = "\n".join(production(INCLUDES + name, base) for name in
                        ("native_effect_haze_batch.inc", "native_effect_stage1_batch.inc", "native_effect_strip21.inc"))
    batches += "\n" + extract.function(source, 'extern "C" int re4dc_effect_line(')
    drain_begin = source.index("#if RE4DC_EFFECT_SPRITES\n#if defined(RE4DC_FX_STRIP21)", source.index('extern "C" void re4dc_model_finish_source_draws'))
    drain_end = source.index("\n    }\n    AVD_EVENT(FinishEnd", drain_begin)
    drain = source[drain_begin:drain_end]
    replacements = {
        "PACKET": packet, "RESET_FUNCTION": extract.function(source, "void reset_deferred()") + "\n" + models,
        "SUBMIT": extract.function(source, 'extern "C" int re4dc_effect_sprite('), "BATCHES": batches, "DRAIN": drain,
    }
    # The full packet slice already contains the trim include, unlike the older
    # Build6 scaffold's deliberately reduced packet slice.
    template = replace_once(template, '\n#include "fx_sprite_trim.inc"\n', "\n")
    for key, value in replacements.items():
        template = replace_once(template, "@" + key + "@", value)
    opaque = "        // Unchanged model/strip/octagon owners are represented by their actual queue tag and opaque bytes.\n        auto* packet=reinterpret_cast<unsigned char*>(deferred_first)+kSpriteNode;\n        const unsigned count=deferred_first->changed[1];\n        deferred_first=deferred_first->next;stream_send(packet,count);\n"
    template = replace_once(template, opaque, "")
    template = replace_once(template, "    draining_parts=false;source_draws_finished=true;\n}", "    draining_parts=false;source_draws_finished=true;reset_deferred();\n}")
    if re.search(r"@[A-Z_]+@", template):
        raise RuntimeError("Unresolved scaffold placeholder")
    return template


def run_step(label: str, command: list[str], steps: list[dict], *, env=None) -> subprocess.CompletedProcess:
    start = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120, env=env)
    stdout = {"stdout_sha256": sha(result.stdout.encode()), "stdout_bytes": len(result.stdout.encode())} if label.startswith("preprocess ") else {"stdout": result.stdout}
    steps.append({"label": label, "argv": command, "returncode": result.returncode,
                  "host_wall_seconds": round(time.monotonic() - start, 6), **stdout, "stderr": result.stderr})
    if result.stdout and label.startswith("run "):
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}")
    return result


def cases(output: str) -> dict:
    rows = []
    for line in output.splitlines():
        if line.startswith("CASE\t"):
            parts = line.split("\t", 3)
            rows.append({"name": parts[1], "status": parts[2], **({"error": parts[3]} if len(parts) > 3 else {})})
    total = re.search(r"^TOTAL\tpassed=(\d+)\tfailed=(\d+)\tassertions=(\d+)$", output, re.M)
    if not total or len(rows) != int(total[1]) + int(total[2]):
        raise RuntimeError("Missing/inconsistent actual case totals")
    return {"passed": int(total[1]), "failed": int(total[2]), "assertions": int(total[3]), "cases": rows}


def observations(path: Path) -> dict[str, bytes]:
    data = path.read_bytes(); offset = 0; records = {}
    def word():
        nonlocal offset
        value = struct.unpack_from("=I", data, offset)[0]; offset += 4; return value
    while offset < len(data):
        length = word(); name = data[offset:offset + length].decode(); offset += length
        count = word(); start = offset
        for _ in range(count):
            word(); size = word(); offset += size
        if offset > len(data):
            raise RuntimeError("Truncated observation")
        records[name] = data[start:offset]
    return records


SEAM_SIGNATURES = [
    "void reset_deferred(", "bool fx_packet(", 'extern "C" int re4dc_effect_sprite(',
    'extern "C" int re4dc_effect_line(', 'extern "C" int re4dc_effect_quad(',
    'extern "C" int re4dc_effect_mesh21(', 'extern "C" int re4dc_effect_haze_batch(',
    'extern "C" int re4dc_effect_stage1_batch(', "int defer_part(",
    'extern "C" void re4dc_ui_submit(', 'extern "C" void re4dc_model_invalidate_pending(',
    'extern "C" void* re4dc_model_deferred_storage(',
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--base", default="74154cae", help="read-only git base for absent/zero identity comparisons")
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    compiler = shlex.split(args.compiler)
    if not compiler or not shutil.which(compiler[0]):
        parser.error("Host C++ compiler is unavailable")
    receipt = {
        "schema": "re4dc-build18-host-gate-v1", "result": "FAIL",
        "generated_utc": datetime.now(timezone.utc).isoformat(), "base": args.base,
        "fixture_definitions": CONFIG, "steps": [], "variants": {},
        "limits": [
            "No private room data, console or emulator; this does not establish which allocation refused the owner's reported 803-827 sprites.",
            "Actual production enqueue/packet/drain/reset/provider code is executed; texture lookup, heap-4 provider and PVR header compilation are controlled host shims.",
            "The real strip/cloth projection and clipping code executes on host floating point, not SH4 floating point.",
            "Native model enqueue and view restoration execute; final model rendering is captured at the re4dc_model_submit boundary.",
            "Host pointers/structure ABI differ from SH4. Runtime seam and packet equivalence here do not replace complete target option-off object identity.",
            "ASan and UBSan are enabled; LeakSanitizer is disabled because this sandbox cannot inspect /proc tasks.",
            "No hardware cycles, frame-time saving, heap floor or observed r200 drop reduction is claimed.",
        ],
    }
    try:
        before = source_hashes(); receipt["source_sha256"] = before
        version = run_step("compiler version", compiler + ["--version"], receipt["steps"])
        receipt["compiler"] = version.stdout.splitlines()[0]
        base_commit = run_step("resolve base", ["git", "rev-parse", args.base + "^{commit}"], receipt["steps"])
        receipt["base_commit"] = base_commit.stdout.strip()
        current_scaffold, base_scaffold = scaffold(), scaffold(args.base)
        receipt["extracted_sha256"] = {"candidate": sha(current_scaffold.encode()), "base": sha(base_scaffold.encode())}
        with tempfile.TemporaryDirectory(prefix="re4dc-r200-gate-") as directory:
            tmp = Path(directory); (tmp / "dc").mkdir(); (tmp / "dc/pvr.h").write_text(PVR_STUB)
            config = tmp / "config.h"
            config.write_text("\n".join(f"#define {name} {value}" for name, value in CONFIG.items()) + "\n")
            common = compiler + ["-std=c++20", "-O2", "-ffp-contract=off", "-fno-pie", "-no-pie",
                "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-I" + str(tmp), "-I" + str(INCLUDE),
                "-I" + str(ROOT / "port/dreamcast/room"), "-include", str(config)]
            env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
            traces, seams = {}, {}
            for name, content, knob in (("base", base_scaffold, None), ("absent", current_scaffold, None),
                                        ("zero", current_scaffold, 0), ("enabled", current_scaffold, 1)):
                (tmp / "fx_r200_test_scaffold.inc").write_text(content)
                options = [] if knob is None else [f"-DRE4DC_FX_R200_ENTRY_CAP={knob}"]
                exe, trace = tmp / name, tmp / (name + ".trace")
                command = common + options + [str(TEST), str(ROOT / "port/dreamcast/room/pvr_geometry.cpp"), "-o", str(exe)]
                run_step("compile " + name, command, receipt["steps"])
                result = run_step("run " + name, [str(exe), str(trace)], receipt["steps"], env=env)
                receipt["variants"][name] = cases(result.stdout)
                receipt["variants"][name]["trace_sha256"] = sha(trace.read_bytes())
                traces[name] = observations(trace)
                if name != "enabled":
                    pp = run_step("preprocess seams " + name, common + options + ["-E", "-P", str(TEST)], receipt["steps"])
                    # Fixture assertion line numbers are not a runtime change.
                    # Compare actual preprocessed production functions only.
                    seams[name] = {signature: re.sub(r"\s+", " ", definition(pp.stdout, signature)).strip()
                                   for signature in SEAM_SIGNATURES}
            if not (traces["base"] == traces["absent"] == traces["zero"]):
                raise RuntimeError("Option-absent/zero observations differ from base")
            if not (seams["base"] == seams["absent"] == seams["zero"]):
                changed = [name for name in SEAM_SIGNATURES if len({seams[v][name] for v in seams}) != 1]
                raise RuntimeError("Option-absent/zero production seam mismatch: " + ", ".join(changed))
            shared = [name for name in traces["enabled"] if name.startswith("no_overflow_") or name.startswith("other_room_") or name == "global_cap"]
            for name in shared:
                if traces["enabled"][name] != traces["base"][name]:
                    raise RuntimeError("Enabled behavior changed outside overflow scope: " + name)
            receipt["identity"] = {
                "base_absent_zero_observations_equal": True,
                "preprocessed_production_functions_equal": len(SEAM_SIGNATURES),
                "enabled_no_overflow_other_room_cap_observations_equal": len(shared),
                "seam_sha256": {name: sha(value.encode()) for name, value in seams["base"].items()},
            }
        after = source_hashes()
        if before != after:
            receipt["source_sha256_after"] = after
            raise RuntimeError("Source changed during gate; rerun after freeze")
        receipt["result"] = "PASS"
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        receipt["error"] = str(error)
        print("Build18 gate FAILED:", error)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print("Receipt:", args.report)
    if receipt["result"] == "PASS":
        print("Build18 PASS:", {name: result["passed"] for name, result in receipt["variants"].items()})
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

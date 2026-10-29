#!/usr/bin/env python3
"""Public host gates for the opt-in streamed world portal completion class."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
BASE = "6e1e5a0638d10bd7a59670a61e2f4b1f9a536e02"
NATIVE = ROOT / "port/dreamcast/game/platform/native_static.cpp"
TEMPLATE = ROOT / "port/dreamcast/tests/world_portal_stream31/producer_fixture.cpp.in"
PROFILE = ROOT / "port/dreamcast/tools/cloud/build31/portal_completion_profiles.json"
GAME = ROOT / "port/dreamcast/game"


def run(args, **kw):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    if result.returncode:
        raise AssertionError(f"{result.returncode}: {' '.join(map(str, args))}\n{result.stdout}")
    return result.stdout


def source_methods():
    path = ROOT / "port/dreamcast/tools/d367/world_submit_spike/check_runtime.py"
    spec = importlib.util.spec_from_file_location("world_stream_extract", path)
    extract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract)
    source = NATIVE.read_text()
    names = {
        "PVS_FINISH": "void pvs_finish(bool success){",
        "PVS_OBSERVED": "void pvs_observed(const RE4DC_SCENERY_RECORD& l){",
        "CORNERS": "const re4dc::room::CompactVertex12* corners(const RE4DC_SCENERY_RECORD& l){",
        "STREAM_GATHER": "__attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(){",
        "LEAN_FLUSH": "void lean_flush(",
        "STRIPS_LEAN": "const std::uint8_t* strips_lean(",
        "EMIT_PICK": "int emit_pick(const Pick& pk){",
        "CHUNK_EMIT": "__attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){",
    }
    bodies = {name: extract.function(source, signature) for name, signature in names.items()}
    for name in ("CORNERS", "CHUNK_EMIT"):
        assert "{\n#endif" in bodies[name]
        bodies[name] = bodies[name].replace("{\n#endif", "{", 1)
    bodies["RECEIPT"] = source.split("// PORTAL_COMPLETION_FLUSH_BEGIN", 1)[1].split(
        "// PORTAL_COMPLETION_FLUSH_END", 1)[0]
    return bodies


def producer(tmp):
    kos = tmp / "stubs/kos"
    kos.mkdir(parents=True)
    (kos / "fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    source = TEMPLATE.read_text().replace("@ROOT@", str(ROOT))
    for key, body in source_methods().items():
        source = source.replace("@" + key + "@", body)
    assert "@" not in source, "unresolved producer fixture placeholder"
    cpp = tmp / "producer.cpp"
    cpp.write_text(source)
    for sanitize in (False, True):
        exe = tmp / ("producer-san" if sanitize else "producer")
        flags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined", "-no-pie"] if sanitize else ["-O2", "-g0"]
        run(["g++", "-std=gnu++17", "-Wall", "-Wextra", "-Wno-unused-parameter",
             *flags, "-I", tmp / "stubs", "-I", ROOT / "port/dreamcast/game/platform/include",
             "-I", ROOT / "port/dreamcast/tools/d367/world_scratch23/stubs",
             cpp, "-o", exe])
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
        run([exe], env=env)
    print("source-extracted stream transform/strip/PVS/receipt normal+ASan/UBSan pass")


def paged_producer(tmp):
    # Compose the actual streamed emitter with the actual post-emission page
    # validation and whole-part receipt. Selector cursor parity is exercised
    # separately by test_world_pages31.py; these picks are synthetic pages.
    bodies = source_methods()
    source = TEMPLATE.read_text().replace("@ROOT@", str(ROOT)).split("int run_case(", 1)[0]
    for key, body in bodies.items():
        source = source.replace("@" + key + "@", body)
    source = source.replace("#define RE4DC_WORLD_PAGES31 0", "#define RE4DC_WORLD_PAGES31 1")
    source = source.replace("meshlet==0 && count==4", "meshlet<1024 && count==4")
    source = source.replace("Record record{};re4dc::room::MeshPart part{};",
                            "Record record{};std::vector<Record> records;re4dc::room::MeshPart part{};")
    source = source.replace("const Record* meshlets()const{return &record;}",
                            "const Record* meshlets()const{return records.empty()?&record:records.data();}")
    source = source.replace("std::array<std::uint32_t,256*8> sq_storage{};",
                            "std::array<std::uint32_t,1280*8> sq_storage{};")
    inputs = NATIVE.read_text().split("// PAGE31_INPUTS_BEGIN", 1)[1].split("// PAGE31_INPUTS_END", 1)[0]
    support = r'''
#include "world_page31.hpp"
struct Ps2Part {std::uint32_t crc=0,fnv=0;std::uint16_t width=0,height=0;
                std::uint8_t pass=0,cull=0,texture=0,reserved=0;} material;
struct World {float view[12]{},projection[7]{},viewport[6]{};Ps2Part* parts=&material;
    const void* lut=nullptr;const void* gather=nullptr;const void* sg=nullptr;unsigned sg_groups=0;} ps2w;
unsigned frame=1,re4dc_sg_lean_on=0,aborts=0,close_mutation=0;
bool plan_valid=true;
unsigned re4dc_ui_frame(){return frame;}
namespace wplan29 {bool current(unsigned){return plan_valid;}}
void re4dc_model_packet_abort(){++aborts;}
struct {unsigned aborts=0;} c;
''' + inputs + r'''
struct Batch {bool held=true;};
void re4dc_ps2_world_batch_close(Batch* b){
    if(!b->held)return;
    b->held=false;sq_held=false;++closes;events.push_back(2);
    if(close_mutation==1)ps2w.view[0]=1;
    if(close_mutation==2)++material.fnv;
    if(close_mutation==3)plan_valid=false;
}
'''
    first = source.index("struct Batch {bool held=true;};")
    last = source.index("namespace wp29 {", first)
    source = source[:first] + support + source[last:]
    source += r'''
int flush_stream_page(unsigned total,unsigned first,unsigned count,bool last,
                      re4dc::page31::Part& proof,const ChunkPageInputs& inputs,
                      const float* affine,bool refuse,bool clip,bool reorder){
    StreamEmitter e;
    e.limit=clip?3U:64U;e.bind_ok=!refuse;
    e.package.record.vertex_count=4;e.package.record.strip_bytes=5;
    e.package.record.strip_count=1|re4dc::room::kIndexedMeshlet;
    e.package.records.assign(total,e.package.record);
    e.package.part.first_meshlet=0;e.package.part.meshlet_count=total;
    e.part.uv_scale[0]=e.part.uv_scale[1]=1;
    for(unsigned i=0;i<4;++i)e.package.pool[i]={std::uint16_t(i+1),std::uint16_t(i+2),0,
        std::uint16_t(i*8),std::uint16_t(i*4),0xffff};
    re4dc::vp::build_lut(e.lut_storage.data());e.k.lut=e.lut_storage.data();
    e.k.su=e.k.sv=e.k.scale_u=e.k.scale_v=1;
    e.k.near_distance=.5f;e.k.far_distance=2.f;e.k.and_mask=~0U;e.k.finish();
    PickRecord picks[320]{};
    for(unsigned i=0;i<count;++i){picks[i].let=first+i;picks[i].nr=255;}
    if(reorder && count>1)std::swap(picks[0],picks[1]);
    proof.selected(picks,count);
    const unsigned wp29_clipped=stats.strips_clipped,wp29_culled=stats.strips_culled;
    const bool wp29_whole=re4dc::portal29::whole_source(picks,count,0,total);
    const int result=e.chunk_emit(picks,count);
    const auto& cpkg=e.package;const auto& wp29_source=cpkg.parts()[0];
    struct X {unsigned index=0,count=0,key[6]{};
        re4dc::portal29::Ticket wp29_ticket{1,0,7,0};} x;
    x.count=count;
    struct {Batch batch;} submit_scope;
    auto* active_page=&proof;const auto* active_page_inputs=&inputs;
    const float* active_page_affine=affine;
    const unsigned active_page_index=0,active_page_plan=1;
    const bool active_page_last=last;unsigned nctx=1,npk=count;
''' + bodies["RECEIPT"] + r'''
    (void)nctx;(void)npk;
    e.pvs_finish(result>0);
    assert(!sq_held);
    return result;
}
void paged_case(unsigned total,unsigned fail_page=~0U,unsigned mutate=0,
                bool clip=false,bool reorder=false,bool final_empty=false){
    stats={};observed=committed=receipts=closes=model_results=aborts=0;
    close_mutation=0;frame=1;plan_valid=true;sq_held=false;events.clear();c={};
    material={};ps2w={};vp_host_xmtrx[3][0]=0;
    float affine[12]{};ChunkPageInputs inputs;inputs.capture(material,affine);
    re4dc::page31::Part proof(0,total);unsigned page=0;
    for(unsigned first=0;first<total;){
        const unsigned count=std::min(320U,total-first);
        const bool last=first+count==total && !final_empty;
        close_mutation=page==1?mutate:0;
        const int result=flush_stream_page(total,first,count,last,proof,inputs,affine,
            page==fail_page,clip && page==0,reorder && page==0);
        if(page==fail_page || close_mutation){
            assert(result==-1 && receipts==0 && aborts==1 && c.aborts==1 && !sq_held);
            assert(closes==page+1);return; // no next page after a gap or stale source
        }
        assert(result==1 && aborts==0);
        if(!last)assert(receipts==0);
        first+=count;++page;
    }
    if(final_empty){
        close_mutation=0;
        assert(flush_stream_page(total,total,0,true,proof,inputs,affine,false,false,false)==1);
        ++page;
    }
    assert(closes==page && proof.input==2*total && proof.output==2*total);
    assert(observed==total && receipts==unsigned(!clip && !reorder));
    assert(!sq_held && aborts==0);
}
int main(){
    paged_case(321);paged_case(641);paged_case(640,~0U,0,false,false,true);
    paged_case(641,0);paged_case(641,1);paged_case(641,2);
    for(unsigned mutation=1;mutation<=3;++mutation)paged_case(641,~0U,mutation);
    paged_case(641,~0U,0,true);paged_case(641,~0U,0,false,true);
}
'''
    assert "@" not in source
    cpp = tmp / "paged-producer.cpp"
    cpp.write_text(source)
    for sanitize in (False, True):
        exe = tmp / ("paged-producer-san" if sanitize else "paged-producer")
        flags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined", "-no-pie"] if sanitize else ["-O2", "-g0"]
        run(["g++", "-std=gnu++17", "-Wall", "-Wextra", "-Wno-unused-parameter", *flags,
             "-I", tmp / "stubs", "-I", ROOT / "port/dreamcast/game/platform/include",
             "-I", ROOT / "port/dreamcast/tools/d367/world_scratch23/stubs", cpp, "-o", exe])
        run([exe], env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                           UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1"))
    print("actual stream + ordered page aggregation/refusal/mutation normal+ASan/UBSan pass")


def source_guards(tmp):
    current = NATIVE.read_text()
    guard = current.split("#ifndef RE4DC_WORLD_PORTAL_COMPLETION", 1)[1].split(
        "#ifndef RE4DC_SCENERY_SUBMIT_BATCH", 1)[0]
    guard = "#ifndef RE4DC_WORLD_PORTAL_COMPLETION\n" + guard + "int admitted=1;\n"
    definitions = {"WORLD_PORTAL_COMPLETION": 1, "WORLD_PORTAL29": 1,
                   "PS2_PVS_BATCH_COMPOSE": 1, "SCENERY_SUBMIT_BATCH": 1,
                   "SCENERY_STREAM": 1, "PS2_PVS": 1, "WORLD_PORTAL_STREAM31": 1}
    def check(values, expect):
        defs = ["-DRE4DC_" + k + "=" + str(v) for k, v in values.items()]
        result = subprocess.run(["g++", "-E", "-P", "-x", "c++", *defs, "-"],
                                input=guard, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        assert (result.returncode == 0) == expect, (values, result.stderr)
        return result.stdout
    check(definitions, True)
    check({"SCENERY_STREAM": 1, "PS2_PVS": 0, "WORLD_PORTAL_STREAM31": 0}, True)
    for key, value in (("WORLD_PORTAL_STREAM31", 0), ("WORLD_PORTAL_STREAM31", 2),
                       ("WORLD_PORTAL_COMPLETION", 0), ("SCENERY_STREAM", 0),
                       ("PS2_PVS", 0), ("PS2_PVS_BATCH_COMPOSE", 0),
                       ("SCENERY_EMIT_PREFETCH", 1), ("SCENERY_CLIP_GATHER", 1),
                       ("SCENERY_CLIP_INDEXED26", 1), ("SCENERY_RECORD_SPLIT", 1),
                       ("SCENERY_DIRECT_STRIPS", 1), ("TA_HASH", 1)):
        check({**definitions, key: value}, False)
    # A default/explicit-zero portal build still has exact source output in
    # this changed early guard, including every newline after preprocessing.
    old = run(["git", "show", f"{BASE}:port/dreamcast/game/platform/native_static.cpp"])
    old_guard = "#ifndef RE4DC_WORLD_PORTAL_COMPLETION\n" + old.split(
        "#ifndef RE4DC_WORLD_PORTAL_COMPLETION", 1)[1].split(
        "#ifndef RE4DC_SCENERY_SUBMIT_BATCH", 1)[0] + "int admitted=1;\n"
    def pp(text):
        return subprocess.run(["g++", "-E", "-P", "-x", "c++", "-"], input=text,
                              text=True, check=True, capture_output=True).stdout
    off = pp(old_guard)
    assert off == pp(guard)
    assert check({"WORLD_PORTAL_STREAM31": 0}, True) == off
    objects = []
    for label, body in (("base", old_guard), ("current", guard)):
        obj = tmp / f"guard-{label}.o"
        run(["g++", "-std=gnu++17", "-O2", "-g0", "-x", "c++", "-c", "-", "-o", obj], input=body)
        objects.append(obj.read_bytes())
    assert objects[0] == objects[1]
    print("source guard admission/refusal and OFF preprocessor/object identity pass")


def make_commands(tmp):
    kos = tmp / "kos-stub"
    kos.mkdir()
    (kos / "Makefile.rules").write_text("")
    options = json.loads(PROFILE.read_text())["on_options"]
    extras = ["PS2_WORLD_DRAW=1", "COARSE=1", "PACE_CATCHUP=2", "PACE_TRANS_SKIP=1",
              "TREE_IMPOSTOR=1", "NATIVE_MESH=1", "PS2_WORLD_PARTS=1",
              "COARSE_SOURCE_OBJECTS=1", "COARSE_SCENERY_FALLBACK=1", "GAME_ATCHK=1",
              "GAME_ATCHK_LIST=1", "PS2_WORLD_LEAN=2", "NATIVE_STATIC=1",
              "ROUTE_MOVIES=1", "ROUTE_MOVIE_YUV=1", "IO_ALIGNED=1",
              "MOVIE_HEAP_EVICT=1", "MOTION_OOM_EVICT=1", "PVR_PIPELINE=1"]
    base = ["make", "-f", "Makefile", "-n", f"KOS_BASE={kos}", *options, *extras]
    def command(overrides, accepted):
        process = subprocess.run([*base, *overrides, "obj/platform/native_static.o"],
                                 cwd=GAME, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        assert (process.returncode == 0) == accepted, (overrides, process.stdout[-3000:])
        if not accepted:
            return ""
        lines = [line for line in process.stdout.splitlines() if line.startswith("kos-c++")
                 and "platform/native_static.cpp" in line]
        assert len(lines) == 1
        return lines[0]
    old = command([], True)
    zero = command(["WORLD_PORTAL_STREAM31=0"], True)
    assert old == zero and "RE4DC_WORLD_PORTAL_STREAM31" not in old
    stream = ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1"]
    on = command(stream, True)
    assert on.count("-DRE4DC_WORLD_PORTAL_STREAM31=1") == 1
    assert on.count("-DRE4DC_SCENERY_STREAM=1") == 1
    paged = command([*stream, "WORLD_PAGES31=1", "WORLD_PREPARED09=1",
                     "WORLD_PART_PLAN29=1", "MOVIE_WORLD_ARENA=1", "STATIC_OBJ_LIFETIME05=1"], True)
    assert paged.count("-DRE4DC_WORLD_PAGES31=1") == 1
    assert paged.count("-DRE4DC_WORLD_PORTAL_STREAM31=1") == 1
    for values in (["SCENERY_STREAM=1"], ["WORLD_PORTAL_STREAM31=1"],
                   [*stream, "SCENERY_CLIP_GATHER=1"],
                   [*stream, "SCENERY_CLIP_INDEXED26=1"],
                   [*stream, "SCENERY_EMIT_PREFETCH=1"],
                   [*stream, "PS2_PVS_BATCH_COMPOSE=0"],
                   [*stream, "WORLD_PORTAL_COMPLETION=0"],
                   [*stream, "WORLD_PORTAL_STREAM31="],
                   [*stream, "WORLD_PORTAL_STREAM31=%"],
                   [*stream, "WORLD_PORTAL_STREAM31=0 1"],
                   [*stream, "WORLD_PORTAL_STREAM31=2"]):
        command(values, False)
    # The previously admitted standalone streaming profile (without PVS or
    # portal completion) is still admitted with the new control at zero.
    solo = dict(option.split("=", 1) for option in options)
    solo.update(PS2_PVS="0", PS2_PVS_BATCH_COMPOSE="0", WORLD_PORTAL29="0",
                WORLD_PORTAL_COMPLETION="0", SCENERY_STREAM="1")
    process = subprocess.run(["make", "-f", "Makefile", "-n", f"KOS_BASE={kos}",
                              *[f"{key}={value}" for key, value in solo.items()], *extras,
                              "WORLD_PORTAL_STREAM31=0", "obj/platform/native_static.o"],
                             cwd=GAME, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    assert process.returncode == 0, process.stdout[-3000:]
    assert "-DRE4DC_SCENERY_STREAM=1" in process.stdout
    assert "RE4DC_WORLD_PORTAL_STREAM31" not in process.stdout
    print("actual primary Make absent/zero/stream ON and invalid composition pass")


def main():
    with tempfile.TemporaryDirectory(prefix="world-portal-stream31-") as td:
        tmp = Path(td)
        producer(tmp)
        paged_producer(tmp)
        source_guards(tmp)
        make_commands(tmp)


if __name__ == "__main__":
    main()

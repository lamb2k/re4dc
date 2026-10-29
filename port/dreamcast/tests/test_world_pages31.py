"""Host parity for the actual shared world selector and its bounded page proof."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
BASE = "39ed524a3b0a4727148aaa5a45eaaea4d211cede"
FIXTURE = ROOT / "port/dreamcast/tests/world_pages31/selector_fixture.cpp"
SELECTOR = "port/dreamcast/game/platform/include/scenery_chunk_select.inc"
MAKE = ROOT / "port/dreamcast/game/world_plan29.mk"
FLAGS = ["-std=gnu++17", "-DRE4DC_SG_SELECT_LEAN=1",
         "-DRE4DC_SCENERY_RECORD_SPLIT=0", "-DRE4DC_SCENERY_CONE=0",
         "-DRE4DC_PS2_WORLD_NONEMPTY_LOD=0", "-DRE4DC_WORLD_PORTAL29=0",
         "-DRE4DC_PS2_PVS=0", "-DRE4DC_PS2_INTERIOR_CULL=0",
         "-DRE4DC_QUALITY_ASSETS=0", "-DRE4DC_DRAW_FALLBACK_AUDIT=0"]


def run(args, **kw):
    p = subprocess.run([str(x) for x in args], cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    if p.returncode:
        raise AssertionError(f"{p.returncode}: {' '.join(map(str, args))}\n{p.stdout}")
    return p.stdout


def fixture(tmp, stream, sanitize, census=0):
    exe = tmp / f"page-{stream}-{census}-{'san' if sanitize else 'normal'}"
    flags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined"] if sanitize else ["-O2", "-g0"]
    run(["g++", *FLAGS, f"-DRE4DC_SCENERY_STREAM={stream}",
         f"-DRE4DC_WORLD_CENSUS24={census}", *flags, FIXTURE, "-o", exe])
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    return run([exe], env=env).strip()


def off_identity(tmp, stream):
    source = FIXTURE.read_text()
    prefix = source[:source.index("struct PageSelector")]
    prefix = prefix.replace('#include "../../game/platform/include/world_page31.hpp"', "")
    prefix = prefix.replace('#include "../../game/platform/include/world_portal29.hpp"', "")
    prefix = prefix.replace('#include "../../game/platform/include/scenery_chunk_select.inc"',
                            '#include "scenery_chunk_select.inc"')
    prefix += "\nunsigned off_call(SourceSelector* s,Pick* p){return s->chunk_select(p);}\n"
    outputs = []
    for baseline in (True, False):
        branch = tmp / f"off-{stream}-{'base' if baseline else 'new'}"
        branch.mkdir()
        selector = run(["git", "show", f"{BASE}:{SELECTOR}"]) if baseline else (ROOT / SELECTOR).read_text()
        (branch / "scenery_chunk_select.inc").write_text(selector)
        (branch / "off.cpp").write_text(prefix)
        flags = [*FLAGS, f"-DRE4DC_SCENERY_STREAM={stream}", "-O2", "-g0"]
        pp = run(["g++", *flags, "-E", "-P", branch / "off.cpp"])
        (branch / "off.ii").write_text(pp)
        obj = branch / "off.o"
        run(["g++", *flags, "-c", branch / "off.ii", "-o", obj])
        outputs.append((pp.encode(), obj.read_bytes()))
    assert outputs[0] == outputs[1], f"WORLD_PAGES31 OFF changed selector preprocessing/object for stream={stream}"
    return hashlib.sha256(outputs[0][0]).hexdigest()[:16], hashlib.sha256(outputs[0][1]).hexdigest()[:16]


def make_flags(tmp):
    mf = tmp / "Makefile"
    mf.write_text(f"""OBJDIR := obj
PLATFORM_CPPFLAGS :=
WORLD_PART_PLAN29 := 1
NATIVE_PKG_HIGH := 1
PS2_WORLD_MESH := 1
WORLD_PREPARED09 := 1
MOVIE_WORLD_ARENA := 1
STATIC_OBJ_LIFETIME05 := 1
SCENERY_CHUNK := 1
include {MAKE}
obj/platform/native_static.o: ; @echo $(PLATFORM_CPPFLAGS)
""")
    def check(value):
        p = subprocess.run(["make", "-s", "-f", str(mf), "obj/platform/native_static.o",
                            *([] if value is None else [f"WORLD_PAGES31={value}"])],
                           cwd=tmp, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode, p.stdout
    absent, zero, on, empty, bad = (check(v) for v in (None, "0", "1", "", "2"))
    assert absent == zero and absent[0] == on[0] == 0
    assert "RE4DC_WORLD_PAGES31" not in absent[1] and "-DRE4DC_WORLD_PAGES31=1" in on[1]
    assert empty[0] != 0 and bad[0] != 0


def actual_make(tmp):
    kos = tmp / "kos-stub"
    kos.mkdir()
    (kos / "Makefile.rules").write_text("")
    game = ROOT / "port/dreamcast/game"
    options = json.loads((ROOT / "port/dreamcast/tools/cloud/build31/world_prepared09_profiles.json").read_text())["profiles"]["portal"]
    extras = ["PS2_WORLD_DRAW=1", "COARSE=1", "PACE_CATCHUP=2", "PACE_TRANS_SKIP=1",
              "TREE_IMPOSTOR=1", "NATIVE_MESH=1", "PS2_WORLD_PARTS=1",
              "COARSE_SOURCE_OBJECTS=1", "COARSE_SCENERY_FALLBACK=1", "GAME_ATCHK=1",
              "GAME_ATCHK_LIST=1", "PS2_WORLD_LEAN=2", "NATIVE_STATIC=1",
              "ROUTE_MOVIES=1", "ROUTE_MOVIE_YUV=1", "IO_ALIGNED=1",
              "MOVIE_HEAP_EVICT=1", "MOTION_OOM_EVICT=1", "PVR_PIPELINE=1"]
    base = ["make", "-f", "Makefile", "-n", f"KOS_BASE={kos}", *options, *extras]
    def command(value):
        args = [*base, *([] if value is None else [f"WORLD_PAGES31={value}"]),
                "obj/platform/native_static.o"]
        p = subprocess.run(args, cwd=game, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        assert p.returncode == 0, p.stdout[-3000:]
        lines = [line for line in p.stdout.splitlines() if line.startswith("kos-c++") and
                 "platform/native_static.cpp" in line]
        assert len(lines) == 1
        return lines[0]
    absent, zero, on = command(None), command(0), command(1)
    assert absent == zero and "RE4DC_WORLD_PAGES31" not in absent
    assert on.count("-DRE4DC_WORLD_PAGES31=1") == 1
    assert on.replace(" -DRE4DC_WORLD_PAGES31=1", "") == absent


def production_inputs(tmp):
    native = (ROOT / "port/dreamcast/game/platform/native_static.cpp").read_text()
    body = native.split("// PAGE31_INPUTS_BEGIN", 1)[1].split("// PAGE31_INPUTS_END", 1)[0]
    src = r'''#include <cassert>
#include <cstdint>
#include <cstring>
#define RE4DC_PS2_STRIP_GROUPS 1
#define RE4DC_SG_SELECT_LEAN 1
struct Ps2Part { std::uint32_t crc,fnv; std::uint16_t width,height; std::uint8_t pass,cull,texture,reserved; };
struct World { float view[12]{},projection[7]{},viewport[6]{}; const void* lut=nullptr;const void* gather=nullptr;
               const void* sg=nullptr;unsigned sg_groups=0; } ps2w;
unsigned frame=1,re4dc_sg_lean_on=0;
unsigned re4dc_ui_frame(){return frame;}
int main(){
''' + body + r'''
    Ps2Part p{};float affine[12]{};ChunkPageInputs guard;guard.capture(p,affine);
    assert(guard.current(p,affine));
    ++p.crc;assert(!guard.current(p,affine));--p.crc;
    ps2w.view[0]=1;assert(!guard.current(p,affine));ps2w.view[0]=0;
    ps2w.projection[0]=1;assert(!guard.current(p,affine));ps2w.projection[0]=0;
    ps2w.viewport[0]=1;assert(!guard.current(p,affine));ps2w.viewport[0]=0;
    affine[0]=1;assert(!guard.current(p,affine));affine[0]=0;
    ps2w.lut=&p;assert(!guard.current(p,affine));ps2w.lut=nullptr;
    ps2w.gather=&p;assert(!guard.current(p,affine));ps2w.gather=nullptr;
    ps2w.sg=&p;assert(!guard.current(p,affine));ps2w.sg=nullptr;
    ps2w.sg_groups=1;assert(!guard.current(p,affine));ps2w.sg_groups=0;
    re4dc_sg_lean_on=1;assert(!guard.current(p,affine));re4dc_sg_lean_on=0;
    ++frame;assert(!guard.current(p,affine));
}
'''
    cpp = tmp / "production_inputs.cpp"
    cpp.write_text(src)
    exe = tmp / "production_inputs"
    run(["g++", "-std=gnu++17", "-O2", "-g0", cpp, "-o", exe])
    run([exe])


def production_callsites(tmp):
    native = (ROOT / "port/dreamcast/game/platform/native_static.cpp").read_text()
    inputs = native.split("// PAGE31_INPUTS_BEGIN", 1)[1].split("// PAGE31_INPUTS_END", 1)[0]
    post = native.split("// PORTAL_COMPLETION_FLUSH_BEGIN", 1)[1].split("// PAGE31_POST_EMIT_END", 1)[0] + "\n#endif\n"
    a = native.index("// Preserve the original capacity flush and queue snapshot.")
    b = native.index("                    continue;\n                }\n#undef WP29_MESHLET_COUNT", a)
    select_only = native[a:b + len("                    continue;")]
    a = native.index("#if RE4DC_WORLD_PAGES31\n                const bool paged=d.part.meshlet_count")
    b = native.index("                continue;\n            }\n#endif", a)
    ordinary = native[a:b + len("                continue;")]
    prefix = r'''#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
#include "world_page31.hpp"
#define RE4DC_WORLD_PAGES31 1
#define RE4DC_WORLD_PREPARED09 1
#define RE4DC_SCENERY_SUBMIT_BATCH 0
#define RE4DC_PS2_WORLD_TRANSITION_OWNER 0
#define RE4DC_SCENERY_UV_SNAPSHOT 0
#define RE4DC_PS2_PVS 0
#define RE4DC_SKY_ANY 0
#define RE4DC_WORLD_PORTAL29 0
#define RE4DC_WORLD_PORTAL_COMPLETION 0
#define RE4DC_PS2_STRIP_GROUPS 1
#define RE4DC_SG_SELECT_LEAN 1
#define RE4DC_PS2_AFFINE pl.affine
#define WP29_MESHLET_COUNT selected_meshlets
struct Ps2Part { std::uint32_t crc,fnv; std::uint16_t width,height; std::uint8_t pass,cull,texture,reserved; };
struct SourcePart { unsigned first_meshlet=0,meshlet_count=321; };
struct Package { SourcePart source;const SourcePart* parts()const{return &source;} } pk;
struct World { float view[12]{},projection[7]{},viewport[6]{}; Ps2Part* parts=nullptr;
               const void* lut=nullptr;const void* gather=nullptr;const void* sg=nullptr;unsigned sg_groups=0; } ps2w;
unsigned re4dc_sg_lean_on=0,abort_calls=0;bool plan_valid=true;
unsigned re4dc_ui_frame(){return 1;}
void re4dc_model_packet_abort(){++abort_calls;}
namespace wplan29 { bool current(unsigned){return plan_valid;} }
''' + inputs + r'''
struct Pick {std::uint16_t let=0;std::uint8_t nr=0;};
struct ChunkPart { float mvq[12];unsigned key[6];float cull_far,lod_scale;unsigned index,first,count;
                   std::uint8_t cull;bool marked; };
struct FakeD {SourcePart part;float cull_far=100;bool vertex_alpha=false;unsigned next=0;
    re4dc::page31::Page chunk_select(Pick* out,unsigned capacity,re4dc::page31::Cursor& cursor){
        const unsigned remain=part.meshlet_count-next;
        const unsigned n=remain<capacity?remain:capacity;
        for(unsigned i=0;i<n;++i){out[i].let=next+i;out[i].nr=255;}
        next+=n;cursor.started=true;
        return {n,next==part.meshlet_count};
    }
};
struct Counts {unsigned aborts=0;} c;
std::vector<unsigned> emitted;unsigned receipts=0;
int go(unsigned mode){
    Ps2Part meta_data{};ps2w={};ps2w.parts=&meta_data;pk.source={0,321};
    plan_valid=true;abort_calls=receipts=0;emitted.clear();c={};
    constexpr unsigned kChunkParts=48,kChunkPicks=320;
    ChunkPart cctx[kChunkParts]{};Pick cpk[kChunkPicks]{};unsigned nctx=0,npk=0;
    re4dc::page31::Part* active_page=nullptr;bool active_page_last=false;
    const ChunkPageInputs* active_page_inputs=nullptr;const float* active_page_affine=nullptr;
    unsigned active_page_index=0,active_page_plan=0;
    auto chunk_flush=[&]()->int{
        if(!nctx)return 1;
        const ChunkPart x=cctx[0];
        if(active_page){
            emitted.push_back(x.count);
            if(mode==1 && emitted.size()==1)return -1;
            if(emitted.size()==2){
                if(mode==2)ps2w.view[0]=1;
                if(mode==3)plan_valid=false;
                if(mode==4)++ps2w.parts[0].fnv;
            }
        }
        struct E {void end_direct(){}} e;
        const int result=((mode==5 && emitted.size()==1) ||
                          (mode==6 && emitted.size()==2))?0:1;
''' + post + r'''
        if(active_page){
            active_page->selected(cpk+x.first,x.count);
            active_page->emitted(result,result>0,x.count,result>0?x.count:0);
            if(active_page_last && active_page->complete(0))++receipts;
        }
        nctx=npk=0;return 1;
    };
    FakeD d;d.part=pk.source;
    struct {float affine[12]{};} pl;
    struct {unsigned cull=0;} part;
    const Ps2Part& meta=ps2w.parts[0];
    unsigned key[6]{},index=0,plan_incarnation=1,selected_meshlets=321;
    const int* plan=reinterpret_cast<const int*>(1);
    float mvq[12]{};float lod_scale=1;bool marked=false;
    for(unsigned once=0;once<1;++once){
@SITE@
    }
    return 0;
}
int main(){
    assert(go(0)==0 && receipts==1 && (emitted==std::vector<unsigned>{320,1}));
    assert(go(1)==-1 && receipts==0 && emitted.size()==1 && dummytag());
    for(unsigned mode=2;mode<=4;++mode)assert(go(mode)==-1 && receipts==0 && emitted.size()==2 && abort_calls==1);
    assert(go(5)==-1 && receipts==0 && emitted.size()==1 && abort_calls==1);
    assert(go(6)==-1 && receipts==0 && emitted.size()==2 && abort_calls==1);
}
'''
    # Keep the return-value assertion simple while still checking that a failed
    # first page cannot enter the next iteration or publish a receipt.
    prefix = prefix.replace(" && dummytag()", "")
    for name, site in (("select", select_only), ("ordinary", ordinary)):
        cpp = tmp / f"production_{name}.cpp"
        cpp.write_text(prefix.replace("@SITE@", site))
        for sanitize in (False, True):
            exe = tmp / f"production_{name}_{'san' if sanitize else 'normal'}"
            flags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined"] if sanitize else ["-O2", "-g0"]
            run(["g++", "-std=gnu++17", *flags, "-I",
                 ROOT / "port/dreamcast/game/platform/include", cpp, "-o", exe])
            env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
            run([exe], env=env)


def production_receipt(tmp):
    native = (ROOT / "port/dreamcast/game/platform/native_static.cpp").read_text()
    inputs = native.split("// PAGE31_INPUTS_BEGIN", 1)[1].split("// PAGE31_INPUTS_END", 1)[0]
    flush = native.split("// PORTAL_COMPLETION_FLUSH_BEGIN", 1)[1].split("// PORTAL_COMPLETION_FLUSH_END", 1)[0]
    src = r'''#include <cassert>
#include <cstdint>
#include <cstring>
#define RE4DC_WORLD_PAGES31 1
#define RE4DC_WORLD_PREPARED09 1
#define RE4DC_SCENERY_SUBMIT_BATCH 1
#define RE4DC_PS2_WORLD_TRANSITION_OWNER 0
#define RE4DC_PS2_STRIP_GROUPS 1
#define RE4DC_SG_SELECT_LEAN 1
#define RE4DC_WORLD_PORTAL29 1
#define RE4DC_WORLD_PORTAL_COMPLETION 1
#include "world_page31.hpp"
#include "world_portal29.hpp"
struct Ps2Part { std::uint32_t crc,fnv; std::uint16_t width,height; std::uint8_t pass,cull,texture,reserved; };
struct World {float view[12]{},projection[7]{},viewport[6]{}; Ps2Part* parts=nullptr;
              const void* lut=nullptr;const void* gather=nullptr;const void* sg=nullptr;unsigned sg_groups=0;} ps2w;
unsigned frame=1,re4dc_sg_lean_on=0,aborts=0,receipts=0,closes=0,close_mutation=0;
bool plan_valid=true,batch_open=false;
unsigned re4dc_ui_frame(){return frame;}
namespace wplan29 {bool current(unsigned){return plan_valid;}}
void re4dc_model_packet_abort(){++aborts;}
struct Batch {};
void re4dc_ps2_world_batch_close(Batch*){
    if(batch_open && close_mutation==6)ps2w.view[0]=1;
    batch_open=false;++closes;
}
namespace wp29 {
void finish(const re4dc::portal29::Ticket& t,const re4dc::portal29::Completion& c,const unsigned*){
    assert(!batch_open);if(t.serial && c.witnessed())++receipts;
}
}
''' + inputs + r'''
struct SourcePart {unsigned first_meshlet=0,meshlet_count=321;};
struct Package {SourcePart source;const SourcePart* parts()const{return &source;}} cpkg;
struct Pick {std::uint16_t let=0;std::uint8_t nr=255;};
Pick cpk[321]{};
struct X {unsigned index=0,first=0,count=0,wp29_placement=0,key[6]{};
          re4dc::portal29::Ticket wp29_ticket{1,0,0,0};};
struct Stats {unsigned strips_clipped=0,strips_culled=0;} stats;
struct Counts {unsigned aborts=0;} c;
struct E {bool submitted=true;unsigned input=0,output=0;void end_direct(){}};
int flush_page(const X& x,re4dc::page31::Part& proof,const ChunkPageInputs& inputs,
               const float* affine,bool last,unsigned mutation,int emit_result=1){
    re4dc::page31::Part* active_page=&proof;
    const ChunkPageInputs* active_page_inputs=&inputs;
    const float* active_page_affine=affine;
    unsigned active_page_index=0,active_page_plan=1,nctx=1,npk=x.count;
    bool active_page_last=last;
    struct {Batch batch;} submit_scope;
    E e;e.input=e.output=x.count;e.submitted=x.count!=0;
    const int result=emit_result;
    active_page->selected(cpk+x.first,x.count);
    const unsigned wp29_clipped=stats.strips_clipped,wp29_culled=stats.strips_culled;
    const auto& wp29_source=cpkg.parts()[x.index];
    const bool wp29_whole=re4dc::portal29::whole_source(cpk+x.first,x.count,
        wp29_source.first_meshlet,wp29_source.meshlet_count);
    batch_open=true;close_mutation=mutation;
    if(mutation==1)ps2w.view[0]=1;
    if(mutation==2)++ps2w.parts[0].fnv;
    if(mutation==3)plan_valid=false;
    if(mutation==4)re4dc_sg_lean_on=1;
    if(mutation==5)const_cast<float*>(affine)[0]=1;
''' + flush + r'''
    return 1;
}
int main(){
    for(unsigned i=0;i<321;++i){cpk[i].let=i;cpk[i].nr=255;}
    Ps2Part material{};ps2w.parts=&material;float affine[12]{};
    for(unsigned mutation=0;mutation<=6;++mutation){
        ps2w.view[0]=0;material.fnv=0;plan_valid=true;re4dc_sg_lean_on=0;affine[0]=0;
        aborts=receipts=closes=0;stats={};c={};
        ChunkPageInputs inputs;inputs.capture(material,affine);
        re4dc::page31::Part proof(0,321);
        X first;first.count=320;assert(flush_page(first,proof,inputs,affine,false,0)==1);
        assert(receipts==0 && proof.input==320 && closes==2);
        X last;last.first=320;last.count=1;
        const int result=flush_page(last,proof,inputs,affine,true,mutation);
        if(!mutation)assert(result==1 && receipts==1 && aborts==0 && closes==4);
        else assert(result==-1 && receipts==0 && aborts==1 && closes==3);
    }
    for(unsigned refuse_page=0;refuse_page<2;++refuse_page){
        ps2w.view[0]=0;material.fnv=0;plan_valid=true;re4dc_sg_lean_on=0;affine[0]=0;
        aborts=receipts=closes=0;stats={};c={};
        ChunkPageInputs inputs;inputs.capture(material,affine);
        re4dc::page31::Part proof(0,321);
        X first;first.count=320;
        const int first_result=flush_page(first,proof,inputs,affine,false,0,refuse_page?1:0);
        if(!refuse_page){
            assert(first_result==-1 && proof.input==0 && receipts==0 && aborts==1 && closes==1);
            continue; // same callsite contract: no second page after refusal
        }
        assert(first_result==1 && proof.input==320 && receipts==0 && closes==2);
        X last;last.first=320;last.count=1;
        assert(flush_page(last,proof,inputs,affine,true,0,0)==-1);
        assert(proof.input==320 && receipts==0 && aborts==1 && closes==3);
    }
}
'''
    cpp = tmp / "production_receipt.cpp"
    cpp.write_text(src)
    for sanitize in (False, True):
        exe = tmp / f"production_receipt_{'san' if sanitize else 'normal'}"
        flags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined"] if sanitize else ["-O2", "-g0"]
        run(["g++", "-std=gnu++17", *flags, "-I", ROOT / "port/dreamcast/game/platform/include",
             cpp, "-o", exe])
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
        run([exe], env=env)


def main():
    with tempfile.TemporaryDirectory(prefix="world-pages31-") as td:
        tmp = Path(td)
        for stream in (0, 1):
            print(f"selector stream={stream}:", fixture(tmp, stream, False))
            print(f"selector stream={stream} ASan/UBSan:", fixture(tmp, stream, True))
            print(f"selector stream={stream} OFF pp/object SHA16:", *off_identity(tmp, stream))
        print("selector census=1:", fixture(tmp, 1, False, 1))
        print("selector census=1 ASan/UBSan:", fixture(tmp, 1, True, 1))
        make_flags(tmp)
        actual_make(tmp)
        production_inputs(tmp)
        production_callsites(tmp)
        production_receipt(tmp)
        native = (ROOT / "port/dreamcast/game/platform/native_static.cpp").read_text()
        assert native.count("const auto page=d.chunk_select(cpk+npk,kChunkPicks-npk,page_cursor);") == 2
        assert native.count("if(chunk_flush()<0)return -1; //") == 2
        assert native.count("plan && re4dc::page31::indexable(") == 4
        print("WORLD_PAGES31 fragment and actual native_static Make commands absent/zero/ON pass")


if __name__ == "__main__":
    main()

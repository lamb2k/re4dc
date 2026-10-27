#!/usr/bin/env python3
"""Actual-source host checks for house-only arithmetic/emission receipts.

No SDK/guest/timing. Stubs exercise actual receipt, writer accounting and
streamed emit_pick control flow; they do not reproduce the renderer's pixels.
"""
import argparse, hashlib, importlib.util, json, re, resource, subprocess
from pathlib import Path

BASE='b6a5a3d34'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract(s,anchor):
    start=s.index(anchor)
    clean=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m[0]),s)
    first=clean.index('{',start);depth=0
    for end in range(first,len(clean)):
        depth+=(clean[end]=='{')-(clean[end]=='}')
        if not depth:return s[start:end+1]
    raise ValueError(anchor)
def cmd(c):
    p=subprocess.run(c,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(p.stdout)
    return p.stdout

PREFIX=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <array>
#include <vector>
#define RE4DC_HOUSE_ARENA27 1
#define RE4DC_HOUSE_ARENA27_COUNTS 1
#define RE4DC_SCENERY_STREAM 1
#define RE4DC_SCENERY_CHUNK 1
#define RE4DC_SCENERY_REPLAY_LEAN 1
#define RE4DC_SCENERY_SUBMIT_BATCH 1
#define RE4DC_MESH_FASTPATH 1
#define RE4DC_MESH_DIRECT 1
#define RE4DC_HW_LEAN 1
#define RE4DC_MESH_VP_SCHED 1
#define RE4DC_BFC_SCOPE(a,b)
#include "house_arena27_counts.h"
struct Head{unsigned crc=0x12345678,bytes=4096;};
struct PackageIdentity{Head h;const Head& header()const{return h;}};
struct Counter{unsigned fallback=0,aborts=0;};
struct{void* storage=(void*)1;bool camera=true;unsigned room=0x101;float view[12]{},projection[7]{},viewport[6]{};PackageIdentity package;Counter count[3];}ps2w;
unsigned ui_frame=300,room_frame=120;bool open_ok=true;
unsigned re4dc_ui_frame(){return ui_frame;}
unsigned re4dc_house_arena27_room_frame(){return room_frame;}
bool ps2_open(){return open_ok;}
std::vector<Re4dcHouseArena27Geometry> received;
extern "C" void re4dc_house_arena27_geometry(const Re4dcHouseArena27Geometry* p){received.push_back(*p);}
@@HELPERS@@
@@SCOPE@@
int pass_result=1;bool fallback=false,aborted=false;
int ps2_pass(unsigned pass,float){
 auto& c=ps2w.count[pass];c={};
 @@ENTERED@@
 arena27_counts_transform(7,false);arena27_counts_transform(3,true);arena27_counts_emit(9,3);
 c.fallback=fallback;c.aborts=aborted;return pass_result;
}
@@WRAPPER@@
struct Re4dcWorldSubmitBatch{};
unsigned closed_slots,closed_calls;
void re4dc_model_direct_end(unsigned n){closed_slots+=n;++closed_calls;}
void re4dc_ps2_world_direct_end_batch(unsigned n,Re4dcWorldSubmitBatch*){closed_slots+=n;++closed_calls;}
struct Owner{const unsigned* ps2=(unsigned*)1;uint32_t* sq=(uint32_t*)1;unsigned slots=0,output=0;Re4dcWorldSubmitBatch* submit_batch=nullptr;
@@END_DIRECT@@
};
@@TESTS@@
'''

TESTS=r'''
int main(){
 for(unsigned pass=0;pass<3;++pass){assert(re4dc_ps2_mesh_draw(pass,25000)==1);auto r=received.back();assert(r.schema==1&&r.sequence==pass+1&&r.pass==pass&&r.ui_frame==300&&r.room_frame==120&&r.valid&&r.result==1);assert(r.transformed_positions==10&&r.transformed_cache==7&&r.transformed_clip==3&&r.emitted_corners==9&&r.emitted_triangles==3);}
 const auto camera=received.back().camera_hash;ps2w.view[0]=1;re4dc_ps2_mesh_draw(0,25000);assert(received.back().camera_hash!=camera);ps2w.view[0]=0;
 for(int result:{-1,0}){pass_result=result;re4dc_ps2_mesh_draw(0,25000);assert(!received.back().valid&&received.back().result==result);}pass_result=1;
 fallback=true;re4dc_ps2_mesh_draw(0,25000);assert(!received.back().valid&&received.back().fallback==1);fallback=false;
 aborted=true;re4dc_ps2_mesh_draw(0,25000);assert(!received.back().valid&&received.back().aborts==1);aborted=false;
 // Early entry refusal must not consume an old pass's counters/result.
 ps2w.count[0]={13,17};open_ok=false;re4dc_ps2_mesh_draw(0,25000);assert(!received.back().valid&&received.back().result==-2&&received.back().fallback==0&&received.back().aborts==0);open_ok=true;
 re4dc_ps2_mesh_draw(3,25000);assert(!received.back().valid);ps2w.camera=false;re4dc_ps2_mesh_draw(0,25000);assert(!received.back().valid);ps2w.camera=true;
 assert(!arena27_counts_active);arena27_counts_transform(99,false);arena27_counts_emit(99,99);
 Re4dcHouseArena27Geometry r{};arena27_counts_active=&r;
 Owner e;e.slots=12;e.output=6;e.end_direct();e.end_direct();assert(r.emitted_corners==12&&r.emitted_triangles==6&&closed_calls==1);
 // A restart uses a fresh owner count, even with batch ownership retained.
 e.sq=(uint32_t*)1;e.slots=3;e.output=1;Re4dcWorldSubmitBatch batch;e.submit_batch=&batch;e.end_direct();assert(r.emitted_corners==15&&r.emitted_triangles==7&&closed_calls==2);
 e.ps2=nullptr;e.sq=(uint32_t*)1;e.slots=30;e.output=10;e.end_direct();assert(r.emitted_corners==15&&r.emitted_triangles==7);arena27_counts_active=nullptr;
 puts("actual scope/wrapper/end_direct PASS: three passes, exact count sums, camera identity, monotonic IDs, refusals, no stale state, no duplicate owner close, nonworld excluded");}
'''

def pick_check(s,build,helper_state,helpers):
    # Reuse the proven zero-prime consumer's dependency stubs. Actual method
    # text below is freshly extracted from this tree, not copied from that test.
    prefix=PICK_PREFIX
    for name,value in [('RE4DC_WORLD_ZERO_PRIME27',0),('RE4DC_SCENERY_STREAM',1),('RE4DC_SCENERY_EMIT_PREFETCH',0),('RE4DC_SCENERY_DIRECT_STRIPS',0),('RE4DC_WORLD_METER',0),('RE4DC_WORLD_CENSUS24',0),('RE4DC_SCN_CENSUS',0)]:
        prefix=re.sub(r'(#define '+name+r') \w+',r'\g<1> '+str(value),prefix)
    prefix=prefix.replace('prime_calls=0;','prime_calls=0,transformed=0;')
    prefix=prefix.replace('void transform_one(const Vertex12& in,pvr_vertex_t& out,unsigned char& oc){','void transform_one(const Vertex12& in,pvr_vertex_t& out,unsigned char& oc){++trace.transformed;')
    prefix='#define RE4DC_HOUSE_ARENA27_COUNTS 1\n#include "house_arena27_counts.h"\nstatic Re4dcHouseArena27Geometry* arena27_counts_active=nullptr;\n'+extract(helpers,'static void arena27_counts_transform(')+'\n'+prefix
    methods=extract(s,'    int emit_pick(')+'\n'+extract(s,'    [[gnu::always_inline]] void chunk_restart(')
    prefix=prefix.replace('// ACTUAL_METHODS',methods)
    tests=r'''
int main(){
 for(bool world:{false,true})for(unsigned let=0;let<6;++let)for(unsigned mode=0;mode<4;++mode){
  trace={};lean::prime_at=nullptr;lean::primed=0;Emitter e(world);Re4dcHouseArena27Geometry r{};arena27_counts_active=&r;
  auto pick=Emitter::Pick{static_cast<unsigned short>(let),static_cast<unsigned char>(mode==0?255:mode==1?0:1),static_cast<unsigned char>(mode==3?2:1),static_cast<unsigned char>(mode==3?2:0),static_cast<unsigned char>(mode==3?3:1)};
  assert(e.emit_pick(pick)==1);unsigned expected=trace.transformed;
  assert(r.transformed_cache==(world?expected:0)&&r.transformed_positions==r.transformed_cache&&r.transformed_clip==0);
  assert(expected==(mode==0?e.package.lets[let].vertex_count:mode==1?0:2));
  e.chunk_restart();assert(e.emit_pick(pick)==1);assert(r.transformed_cache==(world?2*expected:0));
 }
 for(unsigned failure=0;failure<3;++failure){trace={};Emitter e;e.fail_bind=failure==0;e.fail_gather=failure==1;e.fail_borrow=failure==2;Re4dcHouseArena27Geometry r{};arena27_counts_active=&r;Emitter::Pick p{0,255,0,0,0};assert(e.emit_pick(p)==0);assert(!r.transformed_positions&&!trace.transformed);}
 arena27_counts_active=nullptr;puts("actual emit_pick/restart PASS: plain/indexed, full/partial/empty, all6meshlet sizes, world-only, exact transform-call entries, admission refusals");}
'''
    return build('actual_emit_pick',prefix+tests)

def clip_check(s,build,helper_state,helpers):
    vertex=extract(s,'    void clip_vertex(')
    clip=extract(s,'    int clip_strip(')
    probe=extract(clip,'        {\n            const float* pp=p.projection;')
    prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#define RE4DC_HOUSE_ARENA27_COUNTS 1
#define RE4DC_COPY_LEAN 1
#define RE4DC_SCREEN_WF 640.0f
#define RE4DC_SCREEN_HF 480.0f
#define RE4DC_SCREEN_HALF_WF 320.0f
#define RE4DC_SCREEN_HALF_HF 240.0f
#define RE4DC_INV255 /255.0f
#include "house_arena27_counts.h"
static Re4dcHouseArena27Geometry* arena27_counts_active=nullptr;
@@HELPER@@
namespace re4dc::render{
struct StaticCorner{float x,y,z;short u=0,v=0;unsigned argb=0xFFFFFFFF;};
struct Position{float world_x,world_y,world_z,depth,x,y,z;};
struct RenderVertex{unsigned offset_color;Position position;float u,v,light_red,light_green,light_blue;};}
namespace re4dc::room{struct CompactBatch{float uv_bias[2]{},uv_scale[2]{1,1};};}
struct{unsigned strips_culled=0;}stats;
struct Clip {
 const unsigned* ps2=(unsigned*)1;float mvq[12]={1,0,0,0,0,1,0,0,0,0,1,0};
 struct{float projection[7]={0,1,0,1,0,1,1};}p;
 float proj_bx=320,proj_by=240,near=1,far=100;
 static void project(float&,float&,float&,const void*){}
 float u(float f)const{return f;}float v(float f)const{return f;}
 re4dc::render::StaticCorner corner(const re4dc::render::StaticCorner& c)const{return c;}
 @@VERTEX@@
 int probe(const re4dc::render::StaticCorner* base,const unsigned* index,unsigned count){@@PROBE@@ return 0;}
};
int main(){
 Re4dcHouseArena27Geometry r{};arena27_counts_active=&r;Clip c;re4dc::room::CompactBatch b;
 re4dc::render::StaticCorner in[4]={{0,0,-10},{1,1,-10},{-1,1,-10},{0,0,-10}};unsigned index[]={0,1,2,3};
 re4dc::render::RenderVertex out{};for(const auto& p:in)c.clip_vertex(p,b,out);assert(r.transformed_positions==4&&r.transformed_clip==4&&r.transformed_cache==0);
 r={};assert(c.probe(in,index,4)==0);assert(r.transformed_positions==1); // probe stops after first inside point
 for(auto& p:in){p.z=5;}r={};assert(c.probe(in,index,4)==1);assert(r.transformed_positions==4&&stats.strips_culled==1);
 c.ps2=nullptr;r={};c.clip_vertex(in[0],b,out);c.probe(in,index,4);assert(r.transformed_positions==0);
 puts("actual scalar clip transform/probe PASS: repeated position work, early-inside break, whole-strip reject, world-only");}
'''
    prefix=prefix.replace('@@HELPER@@',extract(helpers,'static void arena27_counts_transform(')).replace('@@VERTEX@@',vertex).replace('@@PROBE@@',probe)
    return build('actual_clip_positions',prefix)

def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--tree',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();tree=a.tree.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    source=tree/'port/dreamcast/game/platform/native_static.cpp';s=source.read_text();header=tree/'port/dreamcast/game/platform/include/house_arena27_counts.h'
    ca_path=tree/'port/dreamcast/tools/d367/world_rebuild27/check_arena.py'
    spec=importlib.util.spec_from_file_location('ca',ca_path);ca=importlib.util.module_from_spec(spec);spec.loader.exec_module(ca)
    def project(text,macro):
        # Reuse reviewed conditional projection with a renamed exact token.
        return ca.off_projection(re.sub(r'\b'+macro+r'\b','RE4DC_HOUSE_ARENA27',text))
    baseline=cmd(['git','-C',str(tree),'show',BASE+':port/dreamcast/game/platform/native_static.cpp'])
    projected=project(s,'RE4DC_HOUSE_ARENA27_COUNTS')
    # The preexisting HOUSE guard must remain unresolved for COUNTS-only OFF.
    # Mask it while evaluating COUNTS conditionals.
    masked=s.replace('RE4DC_HOUSE_ARENA27','RE4DC_EXISTING_HOUSE_GUARD',)
    masked=masked.replace('RE4DC_EXISTING_HOUSE_GUARD_COUNTS','RE4DC_HOUSE_ARENA27')
    masked=masked.replace('include/house_arena27.h','include/existing_house_header.h')
    projected=ca.off_projection(masked).replace('RE4DC_EXISTING_HOUSE_GUARD','RE4DC_HOUSE_ARENA27').replace('include/existing_house_header.h','include/house_arena27.h')
    projected=re.sub(r'^#include "include/house_arena27_counts.h"\n','',projected,flags=re.M)
    identity='''    if(ps2w.room==0x101U)re4dc_log("arena27: identity schema=2 variant=%u mesh_crc=%08x mesh_bytes=%u\\n",
        unsigned(re4dc_house_arena27_variant()),ps2w.package.header().crc,ps2w.package.header().bytes);
'''
    assert projected.count(identity)==1
    off_equal=ca.tokens(projected.replace(identity,''))==ca.tokens(baseline)
    # HOUSE=0 removes both the approved identity line and the new counters.
    house_off=ca.off_projection(projected)
    house_zero=ca.tokens(house_off)==ca.tokens(ca.off_projection(baseline))
    helpers='\n'.join(extract(s,'static '+sig) for sig in ('void arena27_counts_transform(', 'void arena27_counts_emit('))
    helper_state='static Re4dcHouseArena27Geometry* arena27_counts_active=nullptr;static uint32_t arena27_counts_sequence;static bool arena27_counts_entered;\n'
    scope=extract(s,'struct Arena27CountsScope')+';'
    wrapper=extract(s,'extern "C" int re4dc_ps2_mesh_draw(')
    enter=re.search(r'if\(arena27_counts_active\)arena27_counts_entered=true;',s).group()
    end=extract(s,'    void end_direct()')
    program=PREFIX.replace('@@HELPERS@@',helper_state+helpers).replace('@@SCOPE@@',scope).replace('@@ENTERED@@',enter).replace('@@WRAPPER@@',wrapper).replace('@@END_DIRECT@@',end).replace('@@TESTS@@',TESTS)
    def build(name,text,extra=()):
        p=out/(name+'.cpp');p.write_text(text);exe=out/name
        cmd(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I'+str(header.parent),*extra,str(p),'-o',str(exe)])
        return cmd([str(exe)]).strip()
    result={'scope':'SOURCE/HOST arithmetic receipts only; no SDK/guest/timing','head':cmd(['git','-C',str(tree),'rev-parse','HEAD']).strip(),'native_sha256':sha(source),'header_sha256':sha(header),'counts0_renderer_tokens_identical_except_approved_identity_log':off_equal,'house0_tokens_identical':house_zero,'host':{},'refusals':{}}
    result['host']['scope_wrapper_owner']=build('scope_wrapper_owner',program)
    result['host']['actual_emit_pick']=pick_check(s,build,helper_state,helpers)
    result['host']['actual_clip_positions']=clip_check(s,build,helper_state,helpers)
    # Build actual compile-refusal block in isolation, with supported flags.
    start=s.index('#if !RE4DC_HOUSE_ARENA27 || !RE4DC_MESH_FASTPATH')
    finish=s.index('static Re4dcHouseArena27Geometry*',start)
    contract=s[start:finish]
    supported=PREFIX[:PREFIX.index('struct Head')]+contract+'int main(){}\n'
    result['host']['supported_contract']=build('supported_contract',supported)
    for macro,value in [('RE4DC_CPU_BACKFACE',1),('RE4DC_CPU_BACKFACE',2),('RE4DC_SCENERY_DEDUP',1),('RE4DC_SCENERY_DIRECT_STRIPS',1),('RE4DC_SCENERY_EMIT_PREFETCH',1),('RE4DC_SCENERY_RECORD_SPLIT',1),('RE4DC_MESH_VP_SCHED',2),('RE4DC_SCENERY_STREAM',0),('RE4DC_PS2_WORLD_R11F_OWNER',1),('RE4DC_PS2_WORLD_TRANSITION_OWNER',1)]:
        altered=re.sub(r'^#define '+macro+r' \d+\n','',supported,flags=re.M)
        altered='#define '+macro+' '+str(value)+'\n'+altered
        name=macro+'_'+str(value);p=out/(name+'.cpp');p.write_text(altered)
        check=subprocess.run(['g++','-std=c++17','-fsyntax-only','-I'+str(header.parent),str(p)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        result['refusals'][name]=check.returncode!=0 and 'HOUSE_ARENA27_COUNTS' in check.stdout
        (out/(name+'.log')).write_text(check.stdout)
    result['mutations']={}
    for name,before,after in [('transform','transformed_positions+=n','transformed_positions+=0'),('emission','if(ps2)arena27_counts_emit(slots,output);',''),('stale_entry','if(arena27_counts_active)arena27_counts_entered=true;','')]:
        assert before in program
        try:
            build('mutation_'+name,program.replace(before,after))
            result['mutations'][name]=False
        except RuntimeError as e:
            result['mutations'][name]=(out/('mutation_'+name)).exists() and 'Assertion' in str(e)
            (out/('mutation_'+name+'.log')).write_text(str(e))
    result['source_readback_identical']=sha(source)==result['native_sha256']
    result['helper_sha256']=sha(Path(__file__))
    result['pass']=off_equal and house_zero and result['source_readback_identical'] and all(result['refusals'].values()) and all(result['mutations'].values())
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['pass'] else 1
PICK_PREFIX='\n#include <algorithm>\n#include <array>\n#include <cassert>\n#include <cstdint>\n#include <cstring>\n#include <iostream>\n#include <sstream>\n#include <string>\n#include <vector>\n#define RE4DC_WORLD_ZERO_PRIME27 ZP\n#define RE4DC_SCENERY_STREAM STREAM\n#define RE4DC_SCENERY_EMIT_PREFETCH PREFETCH\n#define RE4DC_SCENERY_DIRECT_STRIPS DIRECT\n#define RE4DC_WORLD_METER OBSERVE\n#define RE4DC_WORLD_CENSUS24 OBSERVE\n#define RE4DC_SCN_CENSUS OBSERVE\n#define RE4DC_SCENERY_REPLAY_LEAN 1\n#define RE4DC_SCENERY_RECORD_SPLIT 0\n#define RE4DC_SCENERY_DEDUP 0\n#define RE4DC_PS2_PVS 0\nconstexpr unsigned PVR_CMD_VERTEX=0xe0000000U;\nstruct pvr_vertex_t { unsigned flags; float x,y,z,u,v; unsigned argb,oargb; };\nstruct Trace { std::string semantic; unsigned prime_entries=0,prime_calls=0; } trace;\nvoid note(const std::string& s){trace.semantic+=s+\';\';}\nstruct Stats { unsigned groups_visible=0,bind_rejects=0,batches=0,reserve_rejects=0,strips=0,strips_culled=0; } stats;\nunsigned scn_cen[7]{};\nnamespace lean { const pvr_vertex_t* prime_at=nullptr; unsigned primed=0; }\nnamespace re4dc::room {\nstruct CompactVertex12 { unsigned short q[6]; };\nstruct CompactBatch { float uv_bias[2]{},uv_scale[2]{}; };\n}\nnamespace re4dc::wc24 {\nenum Phase {Other,Transform,Submit,Transformed};\nstruct Scope { explicit Scope(Phase p){note("scope"+std::to_string(p));} ~Scope(){note("scope-end");} void phase(Phase p){note("phase"+std::to_string(p));} };\nvoid count(Phase p,unsigned n){note("census"+std::to_string(p)+":"+std::to_string(n));}\n}\nnamespace re4dc::vp {\nusing Vertex12=re4dc::room::CompactVertex12;\nstruct Constants{};\nconstexpr unsigned kChecksAll=3;\nvoid prime(pvr_vertex_t* p,unsigned count){++trace.prime_calls;trace.prime_entries+=count;for(unsigned i=0;i<count;++i){p[i].flags=PVR_CMD_VERTEX;p[i].oargb=0;}}\nvoid transform_one(const Vertex12& in,pvr_vertex_t& out,unsigned char& oc){\n    assert(out.flags==PVR_CMD_VERTEX && out.oargb==0); // Every actual consumer requires demand priming.\n    out.x=in.q[0];out.y=in.q[1];out.z=in.q[2];out.u=in.q[3];out.v=in.q[4];out.argb=in.q[5];oc=0;\n}\ntemplate<unsigned Checks> void transform_sched(const Vertex12* in,unsigned count,pvr_vertex_t* cache,unsigned char* oc,const Constants&){\n    note("plain-transform:"+std::to_string(count));for(unsigned i=0;i<count;++i)transform_one(in[i],cache[i],oc[i]);\n}\nvoid transform_sched_ix(const Vertex12* in,const unsigned short* ix,unsigned count,pvr_vertex_t* cache,unsigned char* oc,const Constants&){\n    note("index-transform:"+std::to_string(count));for(unsigned i=0;i<count;++i)transform_one(in[ix[i]],cache[i],oc[i]);\n}\n}\nvoid re4dc_wm_corners(const unsigned char*,unsigned n,unsigned mask){note("meter:"+std::to_string(n)+":"+std::to_string(mask));}\nvoid re4dc_model_packet_commit(unsigned n){note("commit:"+std::to_string(n));}\nvoid re4dc_model_result(unsigned a,unsigned b,unsigned c){note("result:"+std::to_string(a)+":"+std::to_string(b)+":"+std::to_string(c));}\nint re4dc_model_packet_streaming(){note("streaming");return 1;}\nstruct Meshlet { unsigned first_vertex=0,strip_bytes=4;unsigned short vertex_count=4;bool indexed=false; };\nstruct Package {\n    std::array<Meshlet,6> lets{};std::array<re4dc::room::CompactVertex12,256> verts{};std::array<unsigned short,256> offsets{};unsigned char strips_[4]{0,1,2,3};\n    Package(){unsigned counts[6]={4,8,32,128,256,16};for(unsigned j=0;j<6;++j){lets[j].vertex_count=counts[j];lets[j].indexed=(j&1)!=0;}for(unsigned i=0;i<256;++i){offsets[i]=255-i;for(unsigned j=0;j<6;++j)verts[i].q[j]=i*6+j;}}\n    const Meshlet* meshlets()const{return lets.data();} const auto* vertices()const{return verts.data();}\n    bool indexed(const Meshlet& l)const{return l.indexed;}const unsigned short* pool_offsets(const Meshlet&)const{return offsets.data();}\n    const unsigned char* strip_begin(const Meshlet&)const{return strips_;}\n};\nstd::array<pvr_vertex_t,256> shared_cache;\nstruct Emitter {\n    struct Pick { unsigned short let;unsigned char nr,gmask,lo,hi; };\n    Package package;\n    const unsigned* ps2=nullptr;\n    bool lean_part=true,bound=false,submitted=false,streaming=false;\n    bool fail_bind=false,fail_gather=false,fail_borrow=false,direct_return=false;\n    unsigned used=0,input=0,output=0,slots=0,primed=0;\n    pvr_vertex_t* cache=nullptr;unsigned char codes_[256]{};unsigned char* outcodes=codes_;\n    const Meshlet* stream_l=nullptr;\n    re4dc::room::CompactBatch batch,part;\n    re4dc::vp::Constants k;\n    unsigned short sg_records[6*16]{};const unsigned char* sg=reinterpret_cast<const unsigned char*>(sg_records);unsigned sg_groups=2;\n    explicit Emitter(bool world=true){static unsigned key=1;ps2=world?&key:nullptr;for(unsigned i=0;i<6;++i){sg_records[i*16+6]=2;sg_records[i*16+14]=4;}}\n    bool bind(){note("bind");if(fail_bind)return false;if(!bound){note("header");bound=true;}return true;}\n    bool borrow_gather(){note("gather-admit");return !fail_gather;}\n    bool borrow(){note("borrow");if(fail_borrow)return false;if(!cache){cache=shared_cache.data();primed=lean_part && lean::prime_at==cache?lean::primed:0;}return true;}\n    const re4dc::room::CompactVertex12* corners(const Meshlet&){note("corners");return package.verts.data();}\n    const re4dc::room::CompactVertex12* emit_corners(const Meshlet& l,const Pick&){note("decoder");return corners(l);}\n    bool sequential_direct(const Meshlet&){note("direct-check");return direct_return;}\n    void prefetch_emit_header(const Pick&){note("prefetch-header");}\n    void prefetch_emit_payload(const Pick&){note("prefetch-payload");}\n    void set_clip(){note("set-clip");}void* palette=nullptr;\n    void strips_lean(const unsigned char* begin,const unsigned char* end,const re4dc::room::CompactVertex12*,re4dc::room::CompactBatch&,int& result){\n        note("strip:"+std::to_string(begin-package.strips_)+":"+std::to_string(end-package.strips_));\n        for(auto* p=begin;p<end;++p){const auto& v=cache[*p];assert(v.flags==PVR_CMD_VERTEX && v.oargb==0);unsigned words[8];std::memcpy(words,&v,sizeof words);for(unsigned w:words)note("word:"+std::to_string(w));}\n        ++stats.strips;input+=unsigned(end-begin);output+=unsigned(end-begin);used+=unsigned(end-begin);result=strip_result;\n    }\n    int strip_result=1;\n    // ACTUAL_METHODS\n};\n'
if __name__=='__main__':raise SystemExit(main())

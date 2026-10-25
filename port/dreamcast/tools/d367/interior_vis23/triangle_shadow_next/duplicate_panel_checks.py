#!/usr/bin/env python3
"""Execute actual Panel matcher/table/observe/commit/cut source on host fixtures.

Synthetic geometry/package/material/scene state exercise unchanged source logic.
The real host frame guard remains false. Explicit controlled validity enables
isolated receipt checks; these controls do not qualify SH4, assets or rendering.
"""
import argparse
import hashlib
import json
import resource
import subprocess
import tempfile
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-tree',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    if a.out.exists():raise ValueError('Preserve old receipt')
    inc=a.source_tree/'port/dreamcast/game/platform/include'
    header=inc/'pvs23_proof.hpp';runtime=inc/'pvs23_runtime.inc'
    expected={'pvs23_proof.hpp':'1881d1d814fdc7bb787991a2cd6f67ebab293d5c2a7efa42cdd515fb07821ba4','pvs23_runtime.inc':'09a05d430e31216570bcce9e7ef6a8c5fde929bd32f4c2b6979a25df967609a0'}
    pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (header,runtime)}
    if pins!=expected:raise ValueError('Unreviewed production proof source')
    fixture=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <utility>
#include "pvs23_proof.hpp"
struct pvr_vertex_t {float x,y,z;};
namespace re4dc::vp {constexpr unsigned kCacheSlots=264;}
unsigned frame=10,scene=20;bool material=true,intact=true,scene_live=true;
unsigned re4dc_ui_frame(){return frame;}
extern "C" int re4dc_pvs23_scene(unsigned out[2]){out[0]=frame;out[1]=scene;return scene_live;}
extern "C" int re4dc_pvs23_opaque_ready(const unsigned*,unsigned){return material;}
int re4dc_ps2_placements_intact(unsigned,const unsigned char*,unsigned){return intact;}
std::uint32_t ps2_crc32(const unsigned char* p,unsigned n){unsigned c=~0U;for(unsigned i=0;i<n;++i){c^=p[i];for(unsigned b=0;b<8;++b)c=(c>>1)^(0xedb88320U&(0U-(c&1U)));}return ~c;}
struct FakePackage {
 struct Header{unsigned part_count=1,meshlet_count=1;} h;
 struct Mesh{unsigned first_part=0,part_count=1;} m;
 struct Lod{unsigned first_cluster=0,cluster_count=1;} d;
 struct Cluster{unsigned first_level=0,level_count=1;} c;
 struct Level{unsigned first_meshlet=0,meshlet_count=1;} l;
 struct Meshlet{unsigned vertex_count=3;} v;
 bool lod()const{return true;}const auto& header()const{return h;}
 const Mesh* meshes()const{return &m;}const Lod* part_lods()const{return &d;}
 const Cluster* clusters()const{return &c;}const Level* levels()const{return &l;}
 const Meshlet* meshlets()const{return &v;}
};
struct Part{unsigned pass=0,cull=2,reserved=0;};struct Placement{unsigned mesh=0,placement=0;};
Part parts[1];Placement placements[2]={{0,0},{0,1}};
struct World{unsigned room=0x10d,nplacements=2;void* storage=(void*)1;FakePackage package;Part* parts=::parts;Placement* placements=::placements;}ps2w;
volatile unsigned re4dc_ps2_pvs_on=1;
namespace pvs{unsigned generation=1,pl_skipped=0,cl_skipped=0;unsigned char b=0;const std::uint8_t* cur=&b;bool can_cut(unsigned);}
#include "pvs23_runtime.inc"
unsigned checks=0;
#define CHECK(x) do{++checks;assert(x);}while(0)
int main(){
 using namespace re4dc::pvsproof;
 Panel p{0,0,0,0,0,{0,1,2,0,1,2}};
 pvr_vertex_t v[4]={{10,10,.001f},{10,100,.001f},{100,10,.001f},{100,100,.001f}};
 std::uint8_t codes[4]={0,0x40,0x80,0xc0},strip[4]={3,0,1,2};
 auto sent=[&](){return panel_sent(p,v,codes,3,strip,4,2,64);};
 CHECK(sent()); // ONE unchanged actual oriented triple satisfies both bits.
 std::swap(p.corners[1],p.corners[2]);std::swap(p.corners[4],p.corners[5]);CHECK(!sent());p={0,0,0,0,0,{0,1,2,0,1,2}};
 std::uint8_t absent[4]={3,0,2,1};CHECK(!panel_sent(p,v,codes,3,absent,4,2,64));
 CHECK(!panel_sent(p,v,codes,3,strip,3,2,64));CHECK(!panel_sent(p,v,codes,3,strip,4,2,2));
 for(unsigned bit:{16U,32U}){codes[1]=bit;CHECK(!sent());}codes[1]=0x40;
 for(auto& c:codes)c=1;CHECK(!sent());codes[0]=0;codes[1]=0x40;codes[2]=0x80;codes[3]=0xc0;
 auto saved=v[2];v[2]=v[1];CHECK(!sent());v[2]=saved;
 v[0].z=0;CHECK(!sent());v[0].z=.001f;
 v[0].x=std::numeric_limits<float>::quiet_NaN();CHECK(!sent());v[0].x=10;
 p.corners[5]=3;CHECK(!sent());p.corners[5]=2;
 // Odd strip parity uses (t+2,t+1,t), never naive consecutive ordering.
 std::uint8_t odd[5]={4,3,2,1,0};CHECK(panel_sent(p,v,codes,4,odd,5,2,64));
 // Exercise unchanged actual table_guard, including one-LOD and all material gates.
 unsigned char table=0;auto guard=[&](){return re4dc_pvs23_table_guard(0x10d,&table,1,1,1,1);};
 CHECK(guard());ps2w.package.c.level_count=2;CHECK(!guard());ps2w.package.c.level_count=1;CHECK(guard());
 parts[0].reserved=1;CHECK(!guard());parts[0].reserved=0;
 parts[0].pass=1;CHECK(!guard());parts[0].pass=0;
 parts[0].cull=1;CHECK(!guard());parts[0].cull=2;
 placements[0].placement=1;CHECK(!guard());placements[0].placement=0;
 ps2w.package.v.vertex_count=2;CHECK(!guard());ps2w.package.v.vertex_count=3;CHECK(guard());
 // Real host frame_guard remains closed; it is not replaced or stubbed.
 float view[12]{},proj[7]{},port[6]{};CHECK(!re4dc_pvs23_frame_guard(0x10d,view,proj,port,10,100000));
 auto arm=[&](){CHECK(guard());proof23::valid=true;proof23::checked_frame=frame;proof23::checked_generation=pvs::generation;};
 auto observe=[&](unsigned pending[3]){re4dc_pvs23_observe(0,0,0,v,codes,3,strip,4,2,64,pending);};
 auto commit=[&](const unsigned pending[3]){unsigned key[6]{};re4dc_pvs23_commit(0,0,pending,key);};
 unsigned pending[3]{};arm();observe(pending);CHECK(pending[2]==1);CHECK(!pvs::can_cut(1));commit(pending);CHECK(pvs::can_cut(1));CHECK(!pvs::can_cut(0));
 arm();pending[0]=pending[1]=pending[2]=0;observe(pending);material=false;commit(pending);CHECK(!pvs::can_cut(1));material=true;
 arm();observe(pending);++scene;commit(pending);CHECK(!pvs::can_cut(1));
 arm();observe(pending);++frame;commit(pending);CHECK(!pvs::can_cut(1));
 arm();observe(pending);++pvs::generation;commit(pending);CHECK(!pvs::can_cut(1));
 arm();pending[0]=pending[1]=pending[2]=0;codes[0]=16;observe(pending);CHECK(!pending[2]);commit(pending);CHECK(!pvs::can_cut(1));codes[0]=0;
 arm();observe(pending);re4dc_pvs23_commit(1,0,pending,nullptr);CHECK(!pvs::can_cut(1));
 arm();observe(pending);intact=false;commit(pending);CHECK(!pvs::can_cut(1));intact=true;
 arm();observe(pending);commit(pending);CHECK(pvs::can_cut(1));proof23::key[0]=1;CHECK(!pvs::can_cut(1));
 arm();observe(pending);commit(pending);CHECK(pvs::can_cut(1));re4dc_ps2_pvs_on=0;CHECK(!pvs::can_cut(1));
 std::printf("checks=%u\n",checks);
}
'''
    # Synthetic certificate binds the exact one-byte table and synthetic package.
    cert='const Panel panels[]={{0,0,0,0,0,{0,1,2,0,1,2}}};\nconst Certificate certificates[]={{0x10d,1,1,1,1,0xd202ef8dU,0,1,32,panels,{1000,1000,1000}}};\n'
    records=[]
    with tempfile.TemporaryDirectory(prefix='iv23-duplicate-panel-',dir='/dev/shm') as tmp:
        tmp=Path(tmp);(tmp/'fixture.cpp').write_text('#include <cstdio>\n'+fixture);(tmp/'cert.inc').write_text(cert)
        for label,mutation in [('baseline',None),('matcher-mutant',('found|=1U<<q','found|=1U')),('commit-mutant',('!re4dc_pvs23_opaque_ready(key,re4dc::vp::kCacheSlots+64U)','false')),('epoch-mutant',('pending[0]!=epoch[0] || pending[1]!=epoch[1] ||','false ||'))]:
            h=header.read_text();r=runtime.read_text()
            if mutation:
                old,new=mutation
                if h.count(old)+r.count(old)!=1:raise ValueError('Mutation anchor changed')
                h=h.replace(old,new);r=r.replace(old,new)
            (tmp/'pvs23_proof.hpp').write_text(h);(tmp/'pvs23_runtime.inc').write_text(r)
            exe=tmp/(label+'.exe')
            cmd=['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_PVS23_CERTIFICATES="cert.inc"','-I'+str(tmp),str(tmp/'fixture.cpp'),'-o',str(exe)]
            subprocess.run(cmd,check=True,capture_output=True,text=True)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            if (run.returncode==0)!=(mutation is None):raise ValueError('Control/mutant outcome '+label+' '+run.stdout+run.stderr)
            records.append(dict(label=label,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected='pass' if mutation is None else 'assertion failure'))
    out=dict(kind='Actual-source duplicate-index Panel and isolated receipts host controls',sources=pins,tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),variants=records,scope='Synthetic transcript only; actual host frame guard refuses as expected. No SH4/numeric/raster/asset/admission claim.',peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(out,f,indent=1);f.write('\n')
    print(json.dumps(out))

if __name__=='__main__':main()

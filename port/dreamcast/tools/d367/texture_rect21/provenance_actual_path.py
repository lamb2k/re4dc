#!/usr/bin/env python3
"""Compile actual native_static open/consumer predicates into a bounded host probe.

Source extraction is intentional: no Python reimplementation grants consumer
acceptance. Filesystem/allocator and MeshPackage header are test seams. The
caller independently verifies the full frozen geometry bytes before supplying
that header. This is source/host evidence, never a full target build or guest.
"""
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'game/platform/native_static.cpp'

def between(s,a,b):
    if s.count(a)!=1:raise ValueError('ambiguous source anchor '+a)
    return s.split(a,1)[1].split(b,1)[0]

def function(s,signature):
    at=s.index(signature); begin=s.index('{',at);depth=1;i=begin+1
    while depth:
        if s[i]=='{':depth+=1
        if s[i]=='}':depth-=1
        i+=1
    return s[at:i]

def generate():
    s=SOURCE.read_text(); o=function(s,'bool ps2_open(){')
    structs=between(s,'namespace {\nstruct Ps2Part','static_assert(sizeof(Ps2Part)')
    structs='struct Ps2Part'+structs
    physical='Ps2Head h{};if(ok){'+between(s,'    Ps2Head h{};\n    if(ok){','\n#if RE4DC_PS2_OPEN_TRACE\n    re4dc_log("PS2OPEN sidecar')
    anchor='const std::uint32_t policySourceCrc='+between(s,'    const std::uint32_t policySourceCrc=','\n#if RE4DC_PS2_AREA_HIDE')
    ids='if('+between(s,'            if(!std::memcmp(ih.magic,"R4ID",4)','                auto* sb=') 
    ids='if(!std::memcmp(ih.magic,"R4ID",4)'+ids[3:]
    # Retain the real unique source-ID census; substitute allocation result only.
    ids += ' unique=n; ids_ok=true; }\n'
    trans_head='struct Head'+between(s,'namespace trans{\nenum : unsigned { kUnknown=0,kOp=1,kPtBin=2,kOpaqueInTr=3,kFlat=4,kFlatMid=5,kCardNear=6,kCardSoftA=7,kSoft=8,kVa=9,kDrop=10 };\nenum : unsigned { kTpFlat=1U,kTpCard=2U,kTpSofta=4U,kTpFar=8U,kTpDrop=128U };\nstruct Head','\nstatic_assert(sizeof(Head)==24);')
    movie_fnv=function((SOURCE.parent/'include/movie_world_arena_lifecycle.inc').read_text(),'inline unsigned fnv(')
    trans_open=function(s,'static void open(unsigned r,std::uint32_t r4pw_crc,unsigned parts)')
    crc=function(s,'std::uint32_t ps2_crc32(const unsigned char* p,unsigned n)')
    intact=function(s,'extern "C" int re4dc_ps2_world_intact(')
    placements=function(s,'extern "C" int re4dc_ps2_placements_intact(')
    pc_pkg='pc::st.ok='+between(o,'    pc::st.ok=','\n    re4dc_log("PCCULL cell room=')
    pc_bad='if(std::memcmp(b,"PCL1",4)'+between(s,'        if(std::memcmp(b,"PCL1",4)','why="header";')
    movie_capture='ps2_movie_files='+between(s,'        ps2_movie_files=',';\n    }\n#endif\n#if RE4DC_PS2_STRIP_GROUPS')+';'
    movie_guard='if(ps2_crc32(data,files.mesh)'+between(s,'    if(ps2_crc32(data,files.mesh)','return false;')+'return false;'
    profile='sourceWorldSidecarCrc='+between(o,'    sourceWorldSidecarCrc=',';\n#endif\n#if defined(RE4DC_ENEMY_VIS_CULL)')+';'
    enemy='enemyVisSidecarCrc='+between(o,'    enemyVisSidecarCrc=',';\n#endif\n#if RE4DC_PS2_WORLD_DYNAMIC')+';'
    trans_call='trans::open('+between(s,'    trans::open(',');\n#if RE4DC_PS2_PASS_MASK')+');'
    # Ensure movie reload's policy close and raw integrity expression stay literal.
    reload_body=function(s,'bool ps2_movie_reload()')
    if 'trans::close(); // no I/O here' not in reload_body or 'policySourceCrc' in reload_body:
        raise ValueError('movie reload identity/policy semantics changed')
    prefix=r'''
#include <cstdint>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <iostream>
#include <algorithm>
#include "world_rect_provenance.h"
#define RE4DC_PS2_WORLD_ROOMS 1
#define RE4DC_PS2_WORLD_DYNAMIC 1
#define RE4DC_PS2_WORLD_PARTS 1
#define RE4DC_PS2_PLACE_GATE 1
#define RE4DC_PS2_AREA_HIDE 1
namespace re4dc::render { bool is_finite(float f){return std::isfinite(f);} }
struct MH { unsigned crc,bytes,part_count,mesh_count; };
struct Package { MH h; const MH& header()const{return h;} };
'''
    seams=r'''
struct World { Package package; unsigned room=0,nplacements=0; unsigned char* storage=nullptr; const Ps2Part* parts=nullptr; const Ps2Placement* placements=nullptr; } ps2w;
namespace dyn {
constexpr unsigned kIds=250,kNone=255,off_flag=0,off_serial=4,off_mat=8;
struct Head {char magic[4];std::uint32_t version,count,crc;};
struct PartPose {const unsigned char* part;float pose[9];};
struct Slot {const unsigned char* obj;std::uint32_t serial;float rest[12];PartPose* parts;unsigned nparts,pose_offset;bool source;};
const unsigned char* ids=nullptr;Slot* slots=nullptr;unsigned nids=0;std::uint8_t slot_of[250]{};
}
namespace gate {unsigned room=0,kMax=64,owned[2]{},cur[2]{},want[2]{};}
namespace area {bool cur=false,hidden=false;bool hide(unsigned){return hidden;}}
std::uint32_t enemyVisSidecarCrc=0,sourceWorldSidecarCrc=0;
namespace pc {
constexpr unsigned kPcRoom=0x100,kPcSidecarUse=0x14118acd,kPcMeshUse=0xfb35ea9c,kPcMeshBytesUse=1537920,kPcCellCount=170,kPcPortalCount=1186;
struct {bool ok=false;}st;
}
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
std::vector<unsigned char> class_file;
int fs_open(const char*,int){return class_file.empty()?-1:1;}
long fs_total(int){return class_file.size();}
long fs_read(int,void*p,unsigned n){auto count=std::min<std::size_t>(n,class_file.size());std::memcpy(p,class_file.data(),count);return count;}
void fs_close(int){}
void* re4dc_static_alloc(unsigned n){return std::malloc(n);}
void re4dc_static_free(void*p){std::free(p);}
int re4dc_static_heap_free(){return 123456;}
void re4dc_log(const char*,...){}
unsigned re4dc_trans_policy=3;
namespace movie_world {ACTUAL_MOVIE_FNV}
struct MovieWorldFiles {unsigned mesh=0,side=0,mesh_crc=0,mesh_fnv=0,side_crc=0,side_fnv=0;}ps2_movie_files;
'''
    seams=seams.replace('ACTUAL_MOVIE_FNV',movie_fnv)
    trans=r'''
namespace trans {
HEAD
static std::uint8_t* block=nullptr;static const std::uint8_t* cls=nullptr;
static unsigned room=~0U,nparts=0;
static void close(){if(block)re4dc_static_free(block);block=nullptr;cls=nullptr;room=~0U;nparts=0;}
static bool listed(unsigned r){return r==0x100 || r==0x103;}
OPEN
}
'''.replace('HEAD',trans_head).replace('OPEN',trans_open)
    main=r'''
std::vector<unsigned char> read_blob(){
    std::uint32_t n=0;std::cin.read(reinterpret_cast<char*>(&n),4);
    std::vector<unsigned char>b(n);std::cin.read(reinterpret_cast<char*>(b.data()),n);return b;
}
bool movie_same(const std::vector<unsigned char>& mesh,const std::vector<unsigned char>& side){
    auto buffer=mesh;buffer.insert(buffer.end(),side.begin(),side.end());const unsigned char*data=buffer.data();
    const auto& files=ps2_movie_files;const unsigned mb=files.mesh;
    MOVIE_GUARD
    return true;
}
int main(int argc,char**argv){
    if(argc!=7)return 2;
    unsigned room=std::stoul(argv[1],nullptr,0);
    MH mh{unsigned(std::stoul(argv[2],nullptr,0)),unsigned(std::stoul(argv[3],nullptr,0)),unsigned(std::stoul(argv[4],nullptr,0)),unsigned(std::stoul(argv[5],nullptr,0))};
    unsigned mutation=std::stoul(argv[6],nullptr,0);
    auto world=read_blob(),ids_file=read_blob(),tc_file=read_blob(),pcl=read_blob(),mesh=read_blob(),occl_file=read_blob();
    class_file=tc_file;ps2w.package.h=mh;ps2w.room=room;
    if(mutation==1 && world.size()>32)world[world.size()-1]^=1;
    if(mutation==2 && world.size()>=32)world[24]^=1;
    if(mutation==10 && world.size()>=32)world[28]^=1;
    if(mutation==11 && world.size()>=32)world[4]^=1;
    if(mutation==3 && ids_file.size()>=16)ids_file[12]^=1;
    if(mutation==4 && class_file.size()>24)class_file[24]^=1;
    if(mutation==5 && !pcl.empty())pcl[12]^=1;
    if(mutation==6)world.resize(31);
    if(mutation==9 && occl_file.size()>=16)occl_file[12]^=1;
    if(mutation==7 && world.size()>32){world[32+8]^=1;auto crc=ps2_crc32(world.data()+32,world.size()-32);std::memcpy(world.data()+20,&crc,4);}
    if(mutation==8 && world.size()>32){world[world.size()-1]^=1;auto crc=ps2_crc32(world.data()+32,world.size()-32);std::memcpy(world.data()+20,&crc,4);}
    if(world.size()<32){std::cout<<"{\"physical\":false}\n";return 0;}
    unsigned char*s=world.data();const unsigned mbytes=0,psize=world.size();
    bool ok=true;const char*why=nullptr;
    PHYSICAL
    (void)why;
    if(!ok){std::cout<<"{\"physical\":false}\n";return 0;}
    ps2w.storage=s;ps2w.nplacements=h.placements;
    ANCHOR
    PROFILE
    ENEMY
    dyn::Head ih{};unsigned isize=ids_file.size(),unique=0;bool ids_ok=false;
    if(isize>=sizeof(ih)){
        auto*ib=ids_file.data();std::memcpy(&ih,ib,sizeof(ih));
        IDS
    }
    TRANS_CALL
    bool trans_ok=trans::cls!=nullptr;unsigned class6=0,class9=0;
    const auto class_crc=trans_ok?ps2_crc32(trans::cls,trans::nparts):0;
    for(unsigned i=0;trans_ok && i<trans::nparts;++i){class6+=trans::cls[i]==6;class9+=trans::cls[i]==9;}
    PC_PACKAGE
    bool pc_file=false;
    if(pcl.size()>=32){using namespace pc;auto*b=pcl.data();std::uint32_t w[8];std::memcpy(w,b,32);bool bad=false;
        PC_BAD bad=true;
        pc_file=!bad;
    }
    std::uint32_t occl_crc=0;if(occl_file.size()>=16)std::memcpy(&occl_crc,occl_file.data()+12,4);
    bool occl=re4dc_ps2_world_intact(room,occl_crc);
    bool wrong_room=!re4dc_ps2_world_intact(room+1,ih.crc),wrong_crc=!re4dc_ps2_world_intact(room,ih.crc^1),zero_crc=!re4dc_ps2_world_intact(room,0);
    unsigned char fields[2]{};
    bool rest=re4dc_ps2_placements_intact(room,fields,1);
    area::cur=true;area::hidden=true;bool area_hidden=!re4dc_ps2_placements_intact(room,fields,1);area::cur=false;
    gate::room=room;gate::owned[0]=1;bool gate_hidden=!re4dc_ps2_placements_intact(room,fields,1);gate::owned[0]=0;
    unsigned char id=0,obj[56]{};std::uint32_t flag=1,serial=7;
    std::memcpy(obj,&flag,4);std::memcpy(obj+4,&serial,4);
    dyn::Slot slot{};slot.obj=obj;slot.serial=serial;dyn::ids=&id;dyn::slots=&slot;dyn::nids=1;dyn::slot_of[0]=0;
    bool object_hidden=!re4dc_ps2_placements_intact(room,fields,1);
    flag=3;std::memcpy(obj,&flag,4);bool visible_rest=re4dc_ps2_placements_intact(room,fields,1);
    obj[8]^=1;bool moved=!re4dc_ps2_placements_intact(room,fields,1);obj[8]^=1;
    slot.source=true;bool hierarchy=!re4dc_ps2_placements_intact(room,fields,1);slot.source=false;
    unsigned char part[36]{};dyn::PartPose pose{part,{}};slot.parts=&pose;slot.nparts=1;part[0]=1;
    bool part_moved=!re4dc_ps2_placements_intact(room,fields,1);slot.nparts=0;
    const unsigned msize=mesh.size();s=mesh.data();
    auto whole=mesh;whole.insert(whole.end(),world.begin(),world.end());s=whole.data();
    const unsigned movie_mbytes=msize;
    {const unsigned mbytes=movie_mbytes;MOVIE_CAPTURE}
    bool movie_current=movie_same(mesh,world);
    auto movie_bad=world;movie_bad.back()^=1;bool movie_bad_refused=!movie_same(mesh,movie_bad);
    auto movie_mesh_bad=mesh;movie_mesh_bad.back()^=1;bool movie_mesh_refused=!movie_same(movie_mesh_bad,world);
    trans::close(); // actual reload retains this idle policy behavior.
    std::cout<<"{\"physical\":true,\"actual_crc\":"<<h.crc<<",\"source_crc\":"<<policySourceCrc
             <<",\"profile_crc\":"<<sourceWorldSidecarCrc<<",\"ids\":"<<ids_ok<<",\"unique\":"<<unique
             <<",\"trans\":"<<trans_ok<<",\"class_crc\":"<<class_crc<<",\"class6\":"<<class6<<",\"class9\":"<<class9
             <<",\"pc_package\":"<<pc::st.ok<<",\"pc_file\":"<<pc_file<<",\"occl\":"<<occl
             <<",\"occl_guards\":"<<(wrong_room&&wrong_crc&&zero_crc&&rest&&area_hidden&&gate_hidden&&object_hidden&&visible_rest&&moved&&hierarchy&&part_moved)
             <<",\"movie_current\":"<<movie_current<<",\"movie_bad_refused\":"<<(movie_bad_refused&&movie_mesh_refused)
             <<",\"movie_raw_crc\":"<<ps2_movie_files.side_crc<<",\"movie_raw_fnv\":"<<ps2_movie_files.side_fnv
             <<",\"movie_policy_idle\":"<<(trans::cls==nullptr)<<"}\n";
}
'''
    for token,value in [('MOVIE_GUARD',movie_guard),('PHYSICAL',physical),('ANCHOR',anchor),('PROFILE',profile),('ENEMY',enemy),('IDS',ids),('TRANS_CALL',trans_call),('PC_PACKAGE',pc_pkg),('PC_BAD',pc_bad),('MOVIE_CAPTURE',movie_capture)]:
        main=main.replace(token,value)
    return prefix+structs+seams+crc+'\n'+intact+'\n'+placements+'\n'+trans+main
#!/usr/bin/env python3
"""Execute actual PVS admission/selection, meter helper and tick-log windows on host.

Only file I/O, package metadata and clocks are substituted. No target build.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

TREE = Path(__file__).resolve().parents[5]
GAME = TREE/'port/dreamcast/game'
NATIVE = GAME/'platform/native_static.cpp'


def compile_run(scratch, name, code, extra=()):
    cpp, exe = scratch/(name+'.cpp'), scratch/name
    cpp.write_text(code)
    subprocess.run(['g++','-std=c++17','-O1','-g','-fsanitize=undefined,address',
                    '-fno-omit-frame-pointer','-I'+str(GAME/'platform/include'),'-I'+str(GAME),
                    '-I'+str(scratch),*extra,str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)


def main():
    source = NATIVE.read_text()
    begin = source.index('namespace pvs {\nstruct Head')
    end = source.index('\n#endif',source.index('extern "C" void re4dc_ps2_pvs_state',begin))
    pvs = source[begin:end].replace('#include "include/pvs23_runtime.inc"','')
    # Loader tests substitute the independently exercised prefix contract.
    pvs += '\nnamespace pvs {bool can_cut(unsigned){return true;}}\n'
    prefix = r'''
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <limits>
#include <sys/types.h>
#include "pvs23_format.hpp"
namespace re4dc::render {bool is_finite(float x){return std::isfinite(x);}}
extern "C" void re4dc_log(const char*,...){}
unsigned frame_id=1;
unsigned re4dc_ui_frame(){return frame_id;}
void* re4dc_static_alloc(unsigned n){return std::malloc(n);}
void re4dc_static_free(void* p){std::free(p);}
int re4dc_static_heap_free(){return 1000000;}
using file_t=int;
constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
bool present=true,allow_table=true,allow_frame=true;
std::vector<unsigned char> file;
int fs_open(const char*,int){return present?0:-1;}
unsigned fs_total(int){return file.size();}
ssize_t fs_read(int,void* p,unsigned n){std::memcpy(p,file.data(),n);return n;}
void fs_close(int){}
struct Header {unsigned part_count=1,mesh_count=1;};
struct Mesh {unsigned first_part=0,part_count=1;};
struct Lod {unsigned cluster_count=1;};
struct FakePackage {
    Header h;Mesh m;Lod l;
    const Header& header()const{return h;}
    const Mesh* meshes()const{return &m;}
    const Lod* part_lods()const{return &l;}
};
struct Placement {unsigned mesh=0;};
struct {unsigned nplacements=1;FakePackage package;Placement placements[1];} ps2w;
extern "C" {volatile unsigned re4dc_ps2_pvs_on=0;}
extern "C" int re4dc_pvs23_table_guard(unsigned,const void*,unsigned,unsigned,unsigned,unsigned) __attribute__((weak));
extern "C" int re4dc_pvs23_frame_guard(unsigned,const float*,const float*,const float*,float,float) __attribute__((weak));
#ifndef NO_GUARDS
extern "C" int re4dc_pvs23_table_guard(unsigned,const void*,unsigned,unsigned,unsigned,unsigned){return allow_table;}
extern "C" int re4dc_pvs23_frame_guard(unsigned,const float*,const float*,const float*,float,float){return allow_frame;}
#endif
'''
    tests = r'''
void good(){
    pvs::Head h{{'R','4','P','V'},1,11,22,42,1,1,1,0,0,1000,1,1,1,{0,0}};
    pvs::Cell c{0,-100,100,0};
    file.assign(96,0);std::memcpy(file.data(),&h,sizeof(h));std::memcpy(file.data()+64,&c,8);
}
void load(){pvs::open(0x101,11,22,42);}
int main(){
    good();load();
#ifdef NO_GUARDS
    assert(!pvs::block && !std::strcmp(pvs::why,"uncertified"));return 0;
#else
    assert(pvs::block);
    float v[12]={1,0,0,-500,0,1,0,0,0,0,1,-500},p[7]={},vp[6]={};
    re4dc_ps2_pvs_set(1);pvs::frame(v,p,vp,10,20000);assert(pvs::cur && pvs::hidden(0));
    re4dc_ps2_pvs_set(0);assert(!pvs::cur && !pvs::hidden(0));
    pvs::frame(v,p,vp,10,20000);assert(!pvs::cur);
    re4dc_ps2_pvs_set(1);pvs::frame(v,p,vp,10,20000);assert(pvs::cur);
    v[3]=-2000;pvs::frame(v,p,vp,10,20000);assert(!pvs::cur); // same frame, other eye
    v[3]=-500;pvs::frame(v,p,vp,10,20000);assert(pvs::cur);
    allow_frame=false;pvs::frame(v,p,vp,10,20000);assert(!pvs::cur);allow_frame=true;
    pvs::close();assert(!pvs::cur && !pvs::hidden(0));
    present=false;load();assert(!pvs::block);present=true;
    allow_table=false;good();load();assert(!pvs::block);allow_table=true;
    for(unsigned word: {1U,2U,3U,4U,6U,7U,11U,12U,13U,14U,15U}){
        good();reinterpret_cast<std::uint32_t*>(file.data())[word]=0xffffffffU;
        load();assert(!pvs::block && !pvs::cur && !pvs::hidden(0));
    }
    good();reinterpret_cast<pvs::Head*>(file.data())->nx=0x40000000U;
    reinterpret_cast<pvs::Head*>(file.data())->nz=4;load();assert(!pvs::block); // u32 product overflow
    good();reinterpret_cast<pvs::Head*>(file.data())->cell=std::numeric_limits<float>::infinity();load();assert(!pvs::block);
    good();reinterpret_cast<pvs::Cell*>(file.data()+64)->ylo=101;load();assert(!pvs::block);
    good();file[95]=1;load();assert(!pvs::block);
    good();ps2w.package.l.cluster_count=65536;load();assert(!pvs::block);ps2w.package.l.cluster_count=1;
    good();load();assert(pvs::block);pvs::close();
    return 0;
#endif
}
'''
    geometry = r'''
#include <cassert>
#include <limits>
#include "pvs23_meter.hpp"
struct V {float x,y,z;};
int main(){
    using namespace re4dc::pvs23;
    Geometry g;std::uint8_t codes[]={0,0,4,2,1,32};
    g.add(0,codes,6,0x3f);assert(g.transformed[0]==6 && g.input_inside[0]==2);
    // Strip reuse adds no call. A repeated actual transform adds work.
    g.add(1,codes,2,0x3f);g.add(1,codes,2,0x3f);
    assert(g.transformed[1]==4 && g.input_inside[1]==4);
    g.add(2,nullptr,7,0);assert(g.transformed[2]==7 && g.input_inside[2]==7);
    g.add(3,codes,6,0x3f);assert(g.transformed[2]==7);
    unsigned a[7]={1,2,3,4,5,6,7},b[7]={1,2,3,4,5,6,7};assert(same(a,b));
    for(unsigned i=0;i<7;++i){++b[i];assert(!same(a,b));--b[i];}
    g.clear();assert(!g.transformed[0] && !g.input_inside[1]);
}
'''
    tick_driver = r'''
#include <cassert>
#include <cstring>
#include <cstdint>
unsigned key[7]={0x101,0,0,0,0,0,1};
unsigned long long host_clock=1000;
extern "C" void re4dc_log(const char*,...){}
extern "C" void re4dc_world_meter_identity(unsigned out[7]){std::memcpy(out,key,sizeof(key));}
extern "C" void re4dc_world_meter_take(unsigned* u,unsigned* v,unsigned* g,unsigned* identity){
    re4dc_world_meter_identity(identity);for(unsigned i=0;i<3;++i){u[i]=100+i;v[i]=200+i;g[i]=10+i;g[i+3]=5+i;}
}
extern "C" void re4dc_vram_fail_drain(unsigned){}
extern "C" unsigned re4dc_wm_room(){return key[0];}
#include "tick_log.cpp"
unsigned long ticks[5]={4050,4050,4050,4050,4050};const char* names[5]={};
void tick(unsigned f){host_clock+=1000;re4dc_tick_log_frame(ticks,names,5,f);}
int main(){
    unsigned out[11],avg[48];const char* nm[48];
    assert(!re4dc_world_meter_window(out));tick(10);assert(!re4dc_world_meter_window(out));
    tick(11);assert(!re4dc_world_meter_window(out));
    tick(12);assert(re4dc_world_meter_window(out) && out[7]==11 && out[8]==12 && out[9]==2);
    int n=re4dc_tick_log_snapshot(nm,avg,nullptr,48,nullptr);bool found=false;
    for(int i=0;i<n;++i)if(!strcmp(nm[i],"topq")){assert(avg[i]==10);found=true;}assert(found);
    for(unsigned k=0;k<7;++k){
        ++key[k];assert(!re4dc_world_meter_window(out));assert(!re4dc_tick_log_snapshot(nullptr,nullptr,nullptr,48,nullptr));
        tick(20+3*k);assert(!re4dc_world_meter_window(out));tick(21+3*k);assert(!re4dc_world_meter_window(out));
        tick(22+3*k);assert(re4dc_world_meter_window(out));
        assert(out[k]==key[k] && out[9]==2);
    }
}
'''
    wm_start=source.index('extern "C" { volatile unsigned re4dc_qa_wopq_mm,re4dc_qa_wxlu_mm,re4dc_qa_wshell; }')
    wm_end=source.index('// The far a world pass draws with under the QA rows:',wm_start)
    # Match the real FAR_SHELL include's anonymous-namespace declaration. A
    # second global weak getter makes address lookup ambiguous in the full TU.
    view_decl=re.search(r'extern "C" int re4dc_view_dist_get\(void\);', (GAME/'platform/far_shell.inc').read_text())[0]
    wm_driver=r'''
#include <cassert>
#include <cstring>
#include "pvs23_meter.hpp"
struct pvr_vertex_t {float x,y,z;};
unsigned current_room=0x101;int current_view=0;
extern "C" unsigned re4dc_wm_room(){return current_room;}
'''+ '\nnamespace {\n'+view_decl+r'''
extern "C" int re4dc_view_dist_get(){return current_view;}
}
volatile unsigned re4dc_ps2_pvs_on;
unsigned long long timer_us_gettime64(){static unsigned long long t;return ++t;}
'''+source[wm_start:wm_end]+r'''
int main(){
    unsigned u[3],v[3],g[6],key[7],strip=0;
    std::uint8_t codes[2]={0,4};
    {wmeter::Scope scope(0,&strip,0);re4dc_wm_corners(codes,2,0x3f);strip=9;}
    re4dc_world_meter_take(u,v,g,key);assert(u[0]==1 && v[0]==9 && g[0]==2 && g[3]==1 && key[0]==0x101);
    re4dc_world_meter_take(u,v,g,key);assert(!u[0] && !v[0] && !g[0]);
    {wmeter::Scope scope(1,&strip,2);re4dc_wm_corners(codes,2,0x3f);}
    current_view=1;re4dc_world_meter_take(u,v,g,key);assert(!u[1] && !g[2] && key[1]==1);
    {wmeter::Scope scope(0,&strip,0);re4dc_wm_corners(codes,2,0x3f);}
    ++wm_generation;re4dc_world_meter_take(u,v,g,key);assert(!g[0] && key[6]==1);
}
'''
    with tempfile.TemporaryDirectory(prefix='pvs23-host-') as td:
        scratch=Path(td)
        compile_run(scratch,'pvs',prefix+pvs+tests)
        compile_run(scratch,'pvs-no-guards',prefix+pvs+tests,('-DNO_GUARDS',))
        compile_run(scratch,'geometry',geometry)
        compile_run(scratch,'native-meter',wm_driver,('-DRE4DC_PS2_PVS=1','-DRE4DC_MESH_FASTPATH=1',
            '-DRE4DC_MESH_VP_SCHED=1','-DRE4DC_SCREEN_W=640','-DRE4DC_SCREEN_H=480',
            '-DRE4DC_VIEW_DIST_OPTION=1','-DRE4DC_FAR_SHELL=1','-DRE4DC_WORLD_METER=1'))
        (scratch/'re4dc_platform.h').write_text('extern "C" void re4dc_log(const char*,...);\n')
        (scratch/'arch').mkdir()
        (scratch/'arch/timer.h').write_text('extern unsigned long long host_clock; inline unsigned long long timer_us_gettime64(){return host_clock;}\n')
        compile_run(scratch,'window',tick_driver,('-DRE4DC_WORLD_METER=1','-DRE4DC_TICK_LOG=2'))
        # Parse the entire QA translation unit with KOS/QR declarations only.
        # This catches UI branches and type/signature errors without a target
        # object or full-program build.
        qa=(GAME/'qa_menu.cpp').read_text()
        auto_start=qa.index('int re4dc_qa_menu_auto(')
        auto_end=qa.index('\n}\n\n// In-game menu',auto_start)+2
        auto_driver=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
enum {A_RESUME,A_TELEPORT_MENU,A_DIAG,A_HEALTH,A_LEON,A_PARTNER,A_ENEMY,A_SPEED,A_SHORE,A_WOPQ,A_WXLU,A_WSHELL,A_TITLE};
enum {M_MAIN,M_DIAG,M_QR};
struct Menu {int items[16],nitems,screen,qr_page;};
unsigned resumes=0,captures=0;int g_diag_len=10;char g_path[48];
void re4dc_world_meter_resume(){++resumes;}
void load_presets(){}int fb_displayed(){return 0;}
void draw(int,const Menu&){}void spin_us(unsigned){}
void snap_diag(){assert(resumes==0);++captures;}
int qr_pages(){return 1;}void re4dc_log(const char*,...){}
'''+qa[auto_start:auto_end]+r'''
int main(){
    const char* path=nullptr;
    assert(re4dc_qa_menu_auto(nullptr,&path,16)==0 && resumes==1 && captures==1);
    resumes=0;captures=0;
    assert(re4dc_qa_menu_auto("",&path,0)==0 && resumes==1 && captures==0);
    resumes=0;captures=0;
    assert(re4dc_qa_menu_auto("fixture.txt",&path,16)==1 && resumes==1 && captures==1);
    assert(!strcmp(path,"/cd/dc/qa/fixture.txt"));
}
'''
        compile_run(scratch,'auto-resume',auto_driver,('-DRE4DC_WORLD_METER=1',))
        (scratch/'dc/maple').mkdir(parents=True)
        (scratch/'kos.h').write_text('''#pragma once
#include <cstdint>
extern void* vram_s;
struct video_mode {int width,height;};extern video_mode* vid_mode;
void vid_set_mode(int,int);
constexpr int DM_640x480=0,PM_RGB565=0;
''')
        (scratch/'dc/video.h').write_text('#pragma once\n')
        (scratch/'dc/maple.h').write_text('''#pragma once
struct maple_device_t{};
constexpr int MAPLE_FUNC_CONTROLLER=1;
maple_device_t* maple_enum_type(int,int);void* maple_dev_status(maple_device_t*);
''')
        constants=sorted(set(re.findall(r'\bCONT_[A-Z_]+\b',qa)))
        (scratch/'dc/maple/controller.h').write_text('#pragma once\nstruct cont_state_t {unsigned buttons;int ltrig,rtrig;};\n'+
            '\n'.join('constexpr unsigned '+c+'=1U<<'+str(i)+';' for i,c in enumerate(constants)))
        (scratch/'third_party/qrcodegen').mkdir(parents=True)
        (scratch/'third_party/qrcodegen/qrcodegen.h').write_text('''#pragma once
#include <cstdint>
constexpr int qrcodegen_Ecc_HIGH=0,qrcodegen_Mask_AUTO=0;
#define qrcodegen_BUFFER_LEN_FOR_VERSION(v) (4096)
bool qrcodegen_encodeText(const char*,uint8_t*,uint8_t*,int,int,int,int,bool);
int qrcodegen_getSize(const uint8_t*);bool qrcodegen_getModule(const uint8_t*,int,int);
''')
        subprocess.run(['g++','-std=c++17','-fsyntax-only','-I'+str(scratch),
            '-DRE4DC_WORLD_METER=1','-DRE4DC_QA_NAME="host"',str(GAME/'qa_menu.cpp')],check=True)
        # This is source-token off identity, not a linked-program gate. Headers
        # are removed identically so no target runtime/toolchain is invoked.
        common=['-DRE4DC_WORLD_METER=0','-DRE4DC_PS2_PVS=0','-DRE4DC_NATIVE_MESH=1',
                '-DRE4DC_PS2_WORLD_MESH=1','-DRE4DC_PS2_WORLD_DRAW=1','-DRE4DC_PS2_WORLD_ROOMS=2','-DRE4DC_SS_UI_ORDER=1',
                '-DRE4DC_D349_RENDERER_STACK=1','-DRE4DC_PVR_STREAM=1']
        # The current production control retains ENEMY_VIS_CULL=1. PVS-only
        # liveness strengthening must not alter that existing helper when off.
        current=['-D__sh__=1','-DRE4DC_ENEMY_VIS_CULL=1','-DRE4DC_MESH_FASTPATH=1','-DRE4DC_MESH_DIRECT=1',
                 '-DRE4DC_MESH_VP_SCHED=1','-DRE4DC_HW_LEAN=1','-DRE4DC_SCENERY_CHUNK=1',
                 '-DRE4DC_PS2_WORLD_LEAN=23','-DRE4DC_MESH_PRIME_LAZY=1','-DRE4DC_MESH_STRIP_LEAN=1',
                 '-DRE4DC_MESH_LOD=1','-DRE4DC_MESH_CLASSIFY=0','-DRE4DC_PS2_STRIP_GROUPS=1','-DRE4DC_PS2_WORLD_DYNAMIC=1',
                 '-DRE4DC_PS2_WORLD_ROOT_POSE=1','-DRE4DC_PS2_WORLD_PARTS=1','-DRE4DC_PS2_PLACE_GATE=1',
                 '-DRE4DC_PS2_AREA_HIDE=1']
        for name in ('platform/native_static.cpp','tick_log.cpp','qa_menu.cpp','platform/native_ui.cpp',
                     'platform/native_ps2_world.cpp','platform/vram_pages.cpp','dbgwarp_bridge.cpp'):
            before=subprocess.check_output(['git','-C',str(TREE),'show','272e2892f:port/dreamcast/game/'+name]).decode()
            after=(GAME/name).read_text()
            for mode,flags in (('minimal',common),('current',common+current)):
                tokens=[]
                for revision,text in (('before',before),('after',after)):
                    path=scratch/(revision+'.cc')
                    path.write_text(re.sub(r'^\s*#\s*include[^\n]*','',text,flags=re.M))
                    pp=subprocess.check_output(['g++','-E','-P','-x','c++',*flags,str(path)]).decode()
                    tokens.append(re.sub(r'\s+','',pp))
                assert tokens[0]==tokens[1], 'off preprocessed tokens differ: '+name+' '+mode
    files=[NATIVE,GAME/'tick_log.cpp',GAME/'qa_menu.cpp',GAME/'platform/include/pvs23_meter.hpp',GAME/'platform/include/pvs23_format.hpp']
    print(json.dumps(dict(result='PASS',scope='ASan/UBSan host source execution only',
        files={str(p.relative_to(TREE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),sort_keys=True))


if __name__=='__main__':
    main()

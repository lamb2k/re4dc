"""EF14: the bounded XM point batch consumed by the prepared cloth draw."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
INC = ROOT / 'game/platform/include'
PIN = 'a0166e96b09cb419b46f02c6cddd6cdfb46f254f'
spec = importlib.util.spec_from_file_location('cloth11', ROOT / 'tests/test_native_cloth_sheet11.py')
cloth11 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloth11)
old = cloth11.old


def extract_adapter(source):
    start = source.index('#if defined(RE4DC_NATIVE_DRAW_OUTCOMES)', source.index('static int re4dc_cloth_visible'))
    end = source.index('\n#endif\n\n// clothTrans builds', start)
    return source[start:end]


def production():
    source = (REPO / 'src/game/cloth.cpp').read_text()
    adapter = extract_adapter(source)
    epoch_start = source.index('#if defined(RE4DC_CLOTH_SHEET11)', source.index('Cloth ClothWk[8]'))
    epoch_end = source.index('\n#endif', epoch_start) + len('\n#endif')
    epochs = source[epoch_start:epoch_end]
    direct = (ROOT / 'game/platform/sh4zam_direct.c').read_text()
    batch = direct[direct.index('#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14'):]
    return adapter, epochs, old.function(source, 'void Cloth::Destroy()'), batch


def fixture():
    adapter, epochs, destroy, batch = production()
    stub, code = cloth11.packet_harness()
    code = code.replace('Entry* resolve(', 'void source_hook();\nEntry* resolve(').replace(
        '++opens;return missing?', '++opens;source_hook();return missing?')
    code = code.replace('void stream_send(', 'void send_hook();\nvoid stream_send(').replace(
        'sent_bytes=bytes;', 'sent_bytes=bytes;send_hook();')
    code += r'''
#include <cstdint>
#include <limits>
#include "re4dc_xm.h"
#include "native_cloth_sheet11.hpp"
using u32=unsigned;using f32=float;using Mtx=float[3][4];
struct Vec{float x,y,z;};using zvec_t=Vec;
struct shz_vec3_t{float x,y,z;};struct alignas(16) shz_vec4_t{float x,y,z,w;};
unsigned xm_loads=0,ftrvs=0,scalar_calls=0;
float xm[3][4]{};
shz_vec3_t shz_vec3_init(float x,float y,float z){return{x,y,z};}
shz_vec4_t shz_vec4_init(float x,float y,float z,float w){return{x,y,z,w};}
void shz_xmtrx_load_rows_3x4(const shz_vec4_t* a,const shz_vec4_t* b,const shz_vec4_t* c){
 assert(!((uintptr_t(a)|uintptr_t(b)|uintptr_t(c))&15));
 ++xm_loads;std::memcpy(xm[0],a,16);std::memcpy(xm[1],b,16);std::memcpy(xm[2],c,16);}
shz_vec3_t shz_xmtrx_transform_point3(shz_vec3_t v){++ftrvs;
 return {xm[0][0]*v.x+xm[0][1]*v.y+xm[0][2]*v.z+xm[0][3],
         xm[1][0]*v.x+xm[1][1]*v.y+xm[1][2]*v.z+xm[1][3],
         xm[2][0]*v.x+xm[2][1]*v.y+xm[2][2]*v.z+xm[2][3]};}
void PSMTXMultVec(const Mtx m,const Vec* p,Vec* out){++scalar_calls;const float x=p->x,y=p->y,z=p->z;
 *out={m[0][0]*x+m[0][1]*y+m[0][2]*z+m[0][3],
       m[1][0]*x+m[1][1]*y+m[1][2]*z+m[1][3],
       m[2][0]*x+m[2][1]*y+m[2][2]*z+m[2][3]};}
'''+batch+r'''
struct Color{unsigned char r,g,b,a;};struct cLight{Color DispCol;unsigned xD;float Radius;Vec World;};
struct Env{Color AmbientScr{255,255,255,255};};struct LightManager{Env e;Env* getEnvPtr(){return &e;}} LightMgr;
struct Global{struct{Mtx v_mat;}Cam;unsigned Frame_cnt;}global_value,*pG=&global_value;
struct Cloth{void* tex;void* pTobjA;unsigned divH,divV;void* tlut;unsigned x74;Color color;float Scale;
 Mtx mat;Vec* pVer;Vec* pNor;void* m_pMem;unsigned be_flag;void Destroy();};
Cloth ClothWk[8];
'''+epochs+r'''
std::vector<std::vector<pvr_vertex_t>> packet_log;
void Mem_free(void*){}
'''+destroy+r'''
bool retire_on_load=false,retire_on_send=false;
void source_hook(){if(retire_on_load)ClothWk[0].Destroy();}
void send_hook(){auto* v=reinterpret_cast<const pvr_vertex_t*>(sent);
 packet_log.emplace_back(v,v+sent_bytes/sizeof(pvr_vertex_t));
 if(retire_on_send){retire_on_send=false;ClothWk[0].Destroy();}}
void PSMTXScale(Mtx m,float,float,float){std::memset(m,0,sizeof(Mtx));m[0][0]=m[1][1]=m[2][2]=1;}
void PSMTXConcat(const Mtx,const Mtx,Mtx out){PSMTXScale(out,1,1,1);}
float GetDistance3(Vec*,Vec*){return 0;}
void projection(float* out){auto q=quad();std::memcpy(out,q.projection,sizeof q.projection);}
void viewport(float* out){auto q=quad();std::memcpy(out,q.viewport,sizeof q.viewport);}
#define RE4DC_GXF_GET_PROJECTION(p) projection(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport(p)
'''+adapter+r'''
void fresh(){reset();packet_log.clear();source_draws_finished=true;stream_aborted=false;frame_ready=true;draining_parts=false;
 direct_open=false;missing=false;spill_available=true;entry.valid=true;entry.upload_incarnation=1;
 compiles=opens=xm_loads=ftrvs=scalar_calls=0;retire_on_load=retire_on_send=false;pG->Frame_cnt=frame;}
void setup(Cloth& c,Vec* grid,unsigned width,unsigned rows,unsigned* tex){c={};c.tex=tex;c.divH=width;
 c.divV=rows;c.pVer=grid;c.be_flag=0x31;c.Scale=1;c.color={128,64,32,192};}
int main(){using Outcome=re4dc::NativeDrawOutcome;unsigned tex[]={1,(64U<<16)|64U,14,0};
 cLight* lights[8]{};Vec pos{};
 // The real source adapter consumes each bounded row/tile batch and the
 // existing prepared packet renderer in source row/column order.
 for(unsigned width:{2U,99U,100U,101U,255U}){fresh();std::vector<Vec> grid(width*4);
  for(unsigned row=0;row<4;++row)for(unsigned col=0;col<width;++col)
   grid[row*width+col]={float(col)*.001f,float(row),-10};
  const auto before=grid;auto& c=ClothWk[0];setup(c,grid.data(),width,4,tex);
  auto result=re4dc_cloth_native(&c,lights,&pos,1);
  if(width>100&&!RE4DC_CLOTH_TILES11){assert(result.outcome==Outcome::UnsupportedBeforePublication);
   assert(!result.published()&&!xm_loads&&!ftrvs&&!scalar_calls&&!opens);continue;}
  const unsigned tiles=width<=100?1:1+(width-2)/99;
  assert(result.outcome==Outcome::Submitted&&result.submitted==3*tiles);
  const unsigned expected_loads=width<=100?(width<4?0:4):
   6*(tiles-(width-(tiles-1)*99<4));
  const unsigned expected_points=width<=100?(width<4?0:width*4):
   6*(width+tiles-1-(width-(tiles-1)*99<4?width-(tiles-1)*99:0));
  const unsigned expected_scalars=width<=100?(width<4?width*4:0):
   (width-(tiles-1)*99<4?6*(width-(tiles-1)*99):0);
  assert(xm_loads==expected_loads&&ftrvs==expected_points&&scalar_calls==expected_scalars);
  assert(opens==1&&compiles==1&&packet_log.size()==3*tiles);
  assert(!std::memcmp(before.data(),grid.data(),grid.size()*sizeof(Vec)));
  for(unsigned row=0;row<3;++row)for(unsigned tile=0;tile<tiles;++tile){
   const unsigned first=width<=100?0:tile*99;
   const unsigned columns=width<=100?width:std::min(100U,width-first);
   const auto& packet=packet_log[row*tiles+tile];
   assert(packet.size()==2*columns+1&&packet[2*columns].flags==PVR_CMD_VERTEX_EOL);
   const float du=1.f/float(width-1),dv=1.f/3.f;
   assert(packet[1].u==float(first)*du&&packet[2*columns].u==float(first+columns-1)*du);
   assert(packet[1].v==float(row)*dv&&packet[2].v==float(row)*dv+dv);
   if(tile+1<tiles){const auto& next=packet_log[row*tiles+tile+1];
    assert(packet[2*columns-1].u==next[1].u&&packet[2*columns].u==next[2].u);
    assert(packet[2*columns-1].x==next[1].x&&packet[2*columns-1].y==next[1].y&&
           packet[2*columns].x==next[2].x&&packet[2*columns].y==next[2].y);}
  }
 }
 if(RE4DC_CLOTH_TILES11){
  fresh();std::vector<Vec> wide(101*4,Vec{0,0,-10});auto& c=ClothWk[0];setup(c,wide.data(),101,4,tex);
  retire_on_load=true;auto result=re4dc_cloth_native(&c,lights,&pos,1);
  assert(result.outcome==Outcome::PartialAbort&&!result.published()&&packet_log.empty());
  fresh();setup(c,wide.data(),101,4,tex);retire_on_send=true;
  result=re4dc_cloth_native(&c,lights,&pos,1);
  assert(result.outcome==Outcome::PartialAbort&&result.submitted==1&&!result.fallback_allowed());
  assert(packet_log.size()==1&&xm_loads==2&&ftrvs==200);
  fresh();setup(c,wide.data(),101,4,tex);missing=true;
  result=re4dc_cloth_native(&c,lights,&pos,1);
  assert(result.outcome==Outcome::Refused&&packet_log.empty()&&!xm_loads);
  fresh();for(unsigned row=0;row<2;++row)for(unsigned col=0;col<101;++col)
   wide[row*101+col]={float(col)*.001f,float(row),-10};
  setup(c,wide.data(),101,2,tex);wide[99].z=-.5f;
  result=re4dc_cloth_native(&c,lights,&pos,1);
  assert(result.outcome==Outcome::Submitted&&packet_log.size()==100);
  for(unsigned col=0;col<100;++col){
   const auto& packet=packet_log[col];assert(packet.size()>1&&packet.size()<=13);
   float lo=2,hi=-1;for(unsigned i=1;i<packet.size();++i){lo=std::min(lo,packet[i].u);hi=std::max(hi,packet[i].u);}
   assert(lo>=float(col)/100.f-1e-6f&&hi<=float(col+1)/100.f+1e-6f);
  }
 }
 fresh();Vec near_grid[]={{0,0,-.5f},{1,0,-10},{0,1,-10},{1,1,-10}};
 auto& c=ClothWk[0];setup(c,near_grid,2,2,tex);
 auto result=re4dc_cloth_native(&c,lights,&pos,1);
 assert(result.published()&&!xm_loads&&!ftrvs&&scalar_calls==4&&opens==1&&compiles==1);
 fresh();setup(c,near_grid,2,2,tex);retire_on_load=true;
 result=re4dc_cloth_native(&c,lights,&pos,1);
 assert(result.outcome==Outcome::PartialAbort&&!result.published()&&!xm_loads);
 fresh();setup(c,near_grid,2,2,tex);retire_on_send=true;
 result=re4dc_cloth_native(&c,lights,&pos,1);
 assert(result.outcome==Outcome::PartialAbort&&result.published()&&!result.fallback_allowed());
 assert(!xm_loads&&!ftrvs&&scalar_calls==4);
 // Compare both production routes over nontrivial affine input and strides.
 alignas(4) Mtx m={{1.5f,.25f,-.5f,4},{-.5f,2,.125f,-3},{.75f,-1,1.25f,2}};
 struct S{Vec v;float guard;};S input[5]{};struct D{Vec v;float guard[2];};D scalar[5]{},fast[5]{};
 for(unsigned i=0;i<5;++i){input[i].v={float(i)-2,float(i*i)*.25f,-float(i)-3};input[i].guard=19;
  scalar[i].guard[0]=fast[i].guard[0]=13;scalar[i].guard[1]=fast[i].guard[1]=17;}
 scalar_calls=xm_loads=ftrvs=0;
 assert(re4dc_zam_xm_points14_scalar(m,input,sizeof input,sizeof(S),scalar,sizeof scalar,sizeof(D),5));
 assert(scalar_calls==5&&!xm_loads&&!ftrvs);
 assert(re4dc_zam_xm_points14(m,input,sizeof input,sizeof(S),fast,sizeof fast,sizeof(D),5));
 assert(xm_loads==1&&ftrvs==5&&scalar_calls==5);
 for(unsigned i=0;i<5;++i){assert(!std::memcmp(&scalar[i].v,&fast[i].v,sizeof(Vec)));
  assert(scalar[i].guard[0]==13&&scalar[i].guard[1]==17&&fast[i].guard[0]==13&&fast[i].guard[1]==17);}
 // Game Mtx guarantees four-byte alignment; SH4ZAM's vec4 type needs 16.
 alignas(16) unsigned char matrix_storage[64]{};
 auto m4=reinterpret_cast<float(*)[4]>(matrix_storage+4);
 assert((uintptr_t(m4)&15)==4);std::memcpy(m4,m,sizeof m);
 D four_aligned[5]{};
 assert(re4dc_zam_xm_points14(m4,input,sizeof input,sizeof(S),
                             four_aligned,sizeof four_aligned,sizeof(D),5));
 for(unsigned i=0;i<5;++i)assert(!std::memcmp(&scalar[i].v,&four_aligned[i].v,sizeof(Vec)));
 Vec inplace[3]={{1,2,3},{4,5,6},{7,8,9}};Vec reference[3];
 for(unsigned i=0;i<3;++i)PSMTXMultVec(m,&inplace[i],&reference[i]);
 assert(re4dc_zam_xm_points14(m,inplace,sizeof inplace,sizeof(Vec),inplace,sizeof inplace,sizeof(Vec),3));
 assert(!std::memcmp(inplace,reference,sizeof inplace));
 // Every malformed envelope fails before an output store or XMTRX load.
 alignas(4) unsigned char bytes[128];std::memset(bytes,0x5a,sizeof bytes);
 auto unchanged=[&](){for(auto byte:bytes)assert(byte==0x5a);};
 auto reject=[&](const Mtx matrix,const void* src,unsigned sb,unsigned ss,void* dst,unsigned db,unsigned ds,unsigned n){
  const unsigned loads=xm_loads,points=ftrvs,calls=scalar_calls;
  assert(!re4dc_zam_xm_points14(matrix,src,sb,ss,dst,db,ds,n));
  assert(!re4dc_zam_xm_points14_scalar(matrix,src,sb,ss,dst,db,ds,n));
  assert(loads==xm_loads&&points==ftrvs&&calls==scalar_calls);unchanged();};
 reject(m,input,sizeof input,sizeof(S),bytes,12,12,2); // short output
 reject(m,input,11,12,bytes,sizeof bytes,12,1);       // short input
 reject(m,input,sizeof input,8,bytes,sizeof bytes,12,2);
 reject(m,input,sizeof input,13,bytes,sizeof bytes,12,2);
 reject(m,input,sizeof input,sizeof(S),bytes+1,sizeof bytes-1,12,2);
 reject(m,input,sizeof input,sizeof(S),bytes,sizeof bytes,12,0);
 reject(m,input,sizeof input,sizeof(S),bytes,sizeof bytes,12,101);
 reject(m,bytes,sizeof bytes,12,bytes+4,sizeof bytes-4,12,3); // shifted alias
 reject(m,m,sizeof m,12,bytes,sizeof bytes,12,2);               // matrix/source alias
 reject(m,input,sizeof input,sizeof(S),m,sizeof m,12,2);        // matrix/output alias
 reject(reinterpret_cast<const float(*)[4]>(matrix_storage+1),input,sizeof input,
        sizeof(S),bytes,sizeof bytes,12,2);                     // misaligned matrix
 reject(m,reinterpret_cast<void*>(UINTPTR_MAX-3),~0U,12,bytes,sizeof bytes,12,2);
 assert(!re4dc_zam_xm_points14(m,input,~0U,~0U,bytes,sizeof bytes,12,2));unchanged();
}
'''
    return stub, code


class ClothXmBatch14(unittest.TestCase):
    def test_production_consumer_and_bounds(self):
        stub, code = fixture()
        for tiles in (0, 1):
            with self.subTest(tiles=tiles), tempfile.TemporaryDirectory(prefix='re4dc-cloth-xm14-') as td:
                tmp = Path(td)
                (tmp / 'dc').mkdir()
                (tmp / 'dc/pvr.h').write_text(stub)
                (tmp / 're4dc_xm.h').write_text((REPO / 'include/re4dc_xm.h').read_text())
                cpp = tmp / 'fixture.cpp'
                cpp.write_text(code)
                exe = tmp / 'check'
                flags = ['-fsanitize=address,undefined', '-fno-pie', '-no-pie'] if os.getenv('CLOTH_XM_BATCH14_SANITIZE') == '1' else []
                args = ['g++', '-std=c++20', '-O2', '-ffp-contract=off', '-DRE4DC_FX_STRIP21=1',
                        '-DRE4DC_CLOTH_NATIVE=1', '-DRE4DC_NATIVE_DRAW_OUTCOMES=1',
                        '-DRE4DC_CLOTH_SHEET11=1', '-DRE4DC_CLOTH_XM_BATCH14=1',
                        f'-DRE4DC_CLOTH_TILES11={tiles}',
                        '-DRE4DC_PS2_UPLOAD_INCARNATION=1', '-DRE4DC_UI_HANDLES=1',
                        '-DRE4DC_TA_DIRECT=1', '-DRE4DC_EFFECT_SPRITE_MAX=256', *flags,
                        '-I'+str(tmp), '-I'+str(INC), '-I'+str(ROOT/'room'),
                        str(cpp), str(ROOT/'room/pvr_geometry.cpp'), '-o', str(exe)]
                build = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(build.returncode, 0, build.stderr)
                run = subprocess.run([str(exe)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_scalar_and_batch_production_packets_identical(self):
        stub, code = fixture()
        prefix = code.split('int main(){', 1)[0]
        comparison = prefix + r'''
#include <cstdio>
int main(){unsigned tex[]={1,(64U<<16)|64U,14,0};cLight* lights[8]{};Vec pos{};
 auto emit=[](){std::uint32_t n=packet_log.size();std::fwrite(&n,4,1,stdout);
  for(const auto& packet:packet_log){n=packet.size();std::fwrite(&n,4,1,stdout);
   std::fwrite(packet.data(),sizeof(pvr_vertex_t),packet.size(),stdout);}};
 for(unsigned width:{2U,99U,100U,101U,255U}){fresh();std::vector<Vec> grid(width*4);
  for(unsigned row=0;row<4;++row)for(unsigned col=0;col<width;++col)
   grid[row*width+col]={float(col)*.001f,float(row),-10};
  setup(ClothWk[0],grid.data(),width,4,tex);
  auto result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
  assert(result.outcome==re4dc::NativeDrawOutcome::Submitted);emit();}
 fresh();std::vector<Vec> clipped(101*2);
 for(unsigned row=0;row<2;++row)for(unsigned col=0;col<101;++col)
  clipped[row*101+col]={float(col)*.001f,float(row),-10};
 clipped[99].z=-.5f;setup(ClothWk[0],clipped.data(),101,2,tex);
 auto result=re4dc_cloth_native(&ClothWk[0],lights,&pos,1);
 assert(result.outcome==re4dc::NativeDrawOutcome::Submitted&&packet_log.size()==100);emit();
}
'''
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth-xm14-compare-') as td:
            tmp=Path(td);(tmp/'dc').mkdir();(tmp/'dc/pvr.h').write_text(stub)
            (tmp/'re4dc_xm.h').write_text((REPO/'include/re4dc_xm.h').read_text())
            cpp=tmp/'fixture.cpp';cpp.write_text(comparison)
            flags=['-fsanitize=address,undefined','-fno-pie','-no-pie'] if os.getenv('CLOTH_XM_BATCH14_SANITIZE')=='1' else []
            outputs=[]
            for batch in (0,1):
                exe=tmp/('scalar' if batch==0 else 'batch')
                args=['g++','-std=c++20','-O2','-ffp-contract=off',
                      '-DRE4DC_FX_STRIP21=1','-DRE4DC_CLOTH_NATIVE=1',
                      '-DRE4DC_NATIVE_DRAW_OUTCOMES=1','-DRE4DC_CLOTH_SHEET11=1',
                      '-DRE4DC_CLOTH_TILES11=1',f'-DRE4DC_CLOTH_XM_BATCH14={batch}',
                      '-DRE4DC_PS2_UPLOAD_INCARNATION=1','-DRE4DC_UI_HANDLES=1',
                      '-DRE4DC_TA_DIRECT=1','-DRE4DC_EFFECT_SPRITE_MAX=256',*flags,
                      '-I'+str(tmp),'-I'+str(INC),'-I'+str(ROOT/'room'),
                      str(cpp),str(ROOT/'room/pvr_geometry.cpp'),'-o',str(exe)]
                build=subprocess.run(args,capture_output=True,text=True)
                self.assertEqual(build.returncode,0,build.stderr)
                run=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(run.returncode,0,run.stderr.decode())
                outputs.append(run.stdout)
            self.assertGreater(len(outputs[0]),0)
            self.assertEqual(outputs[0],outputs[1])

    def test_make_scope_and_dependencies(self):
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth-xm14-mk-') as td:
            tmp=Path(td);mk=tmp/'fixture.mk';targets=['obj/src/game/cloth.o','obj/platform/sh4zam_direct.o','obj/platform/native_ui.o']
            mk.write_text('OBJDIR := obj\ninclude '+str(ROOT/'game/cloth_xm_batch14.mk')+'\n'+
                          '\n'.join(t+':\n\t@echo GAME $(GAME_CPPFLAGS) PLATFORM $(PLATFORM_CPPFLAGS) KOS $(KOS_CFLAGS)' for t in targets)+'\n')
            deps=['CLOTH_SHEET11=1','GAME_SH4ZAM=1','GAME_SH4ZAM_RENDER_ONLY=1','GAME_SH4ZAM_LOGIC=0']
            for value in (None,'0','1','','2','-1','0 1','%'):
                args=['make','--no-print-directory','-f',str(mk),*targets,*deps]
                if value is not None:args+=['CLOTH_XM_BATCH14='+value]
                run=subprocess.run(args,capture_output=True,text=True,cwd=tmp)
                if value in ('','2','-1','0 1','%'):
                    self.assertNotEqual(run.returncode,0)
                else:
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(run.stdout.count('-DRE4DC_CLOTH_XM_BATCH14=1'),2 if value=='1' else 0)
                    self.assertNotIn('-DRE4DC_CLOTH_XM_BATCH14=1',run.stdout.splitlines()[2])
            for dep in ('CLOTH_SHEET11','GAME_SH4ZAM','GAME_SH4ZAM_RENDER_ONLY'):
                args=['make','--no-print-directory','-f',str(mk),targets[0],*deps,'CLOTH_XM_BATCH14=1',dep+'=0']
                run=subprocess.run(args,capture_output=True,text=True,cwd=tmp)
                self.assertNotEqual(run.returncode,0)
            run=subprocess.run(['make','--no-print-directory','-f',str(mk),targets[0],*deps,
                                'CLOTH_XM_BATCH14=1','GAME_SH4ZAM_LOGIC=1'],capture_output=True,text=True,cwd=tmp)
            self.assertNotEqual(run.returncode,0)
            # Parse the actual game Makefile through its production include.
            # Temporary dependency placeholders prove command scope
            # without claiming an SH target compile or changing the submodule.
            (tmp/'Makefile.rules').write_text('')
            shz=tmp/'sh4zam/include/sh4zam';shz.mkdir(parents=True)
            (shz/'shz_xmtrx.h').write_text('')
            actual=['make','--no-print-directory','-f','Makefile','-n',
                    'KOS_BASE='+str(tmp),'SH4ZAM_DIR='+str(tmp/'sh4zam'),
                    'EFFECT_SPRITES=1','FX_STRIP21=1','CLOTH_NATIVE=1',
                    'NATIVE_DRAW_OUTCOMES=1','PS2_UPLOAD_INCARNATION=1','CLOTH_SHEET11=1',
                    'GAME_SH4ZAM=1','GAME_SH4ZAM_RENDER_ONLY=1',
                    'obj/src/game/cloth.o','obj/platform/sh4zam_direct.o',
                    'obj/platform/native_ui.o','obj/src/game/esp_sub.o']
            commands=[]
            for value in (None,'0','1'):
                args=[*actual]
                if value is not None:args+=['CLOTH_XM_BATCH14='+value]
                run=subprocess.run(args,capture_output=True,text=True,cwd=ROOT/'game')
                self.assertEqual(run.returncode,0,run.stderr)
                commands.append([s for s in run.stdout.splitlines() if s.startswith(('kos-c++','kos-cc'))])
            self.assertEqual(commands[0],commands[1])
            self.assertEqual(len(commands[2]),4)
            for i,line in enumerate(commands[2]):
                self.assertEqual(line.count('-DRE4DC_CLOTH_XM_BATCH14=1'),int(i<2))

    def test_off_source_identity(self):
        # These are wholly additive, protected definitions. The source adapter
        # has conditional lines inserted inside it; compile its actual excerpt
        # beside the real native packet consumer to compare emitted objects.
        for name in ('include/re4dc_xm.h','port/dreamcast/game/platform/sh4zam_direct.c'):
            before=subprocess.check_output(['git','show',PIN+':'+name],cwd=REPO,text=True)
            after=(REPO/name).read_text()
            self.assertTrue(after.startswith(before))
        source_path='src/game/cloth.cpp'
        before=subprocess.check_output(['git','show',PIN+':'+source_path],cwd=REPO,text=True)
        baseline=extract_adapter(before)
        current=extract_adapter((REPO/source_path).read_text())
        stub,code=fixture()
        code=code.split('int main(){',1)[0]+'int main(){return 0;}\n'
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth-xm14-off-') as td:
            tmp=Path(td);(tmp/'dc').mkdir();(tmp/'dc/pvr.h').write_text(stub)
            (tmp/'re4dc_xm.h').write_text((REPO/'include/re4dc_xm.h').read_text())
            for tiles in (0,1):
                variants=[]
                for name,adapter,flags in (('baseline',baseline,[]),('absent',current,[]),
                                           ('zero',current,['-DRE4DC_CLOTH_XM_BATCH14=0'])):
                    cpp=tmp/'fixture.cpp';cpp.write_text(code.replace(extract_adapter((REPO/source_path).read_text()),adapter))
                    args=['g++','-std=c++20','-O2','-g0','-w','-ffp-contract=off',
                          '-DRE4DC_FX_STRIP21=1','-DRE4DC_CLOTH_NATIVE=1',
                          '-DRE4DC_NATIVE_DRAW_OUTCOMES=1','-DRE4DC_CLOTH_SHEET11=1',
                          f'-DRE4DC_CLOTH_TILES11={tiles}',
                          '-DRE4DC_PS2_UPLOAD_INCARNATION=1','-DRE4DC_UI_HANDLES=1',
                          '-DRE4DC_TA_DIRECT=1','-DRE4DC_EFFECT_SPRITE_MAX=64',*flags,
                          '-I'+str(tmp),'-I'+str(INC),'-I'+str(ROOT/'room')]
                    pre=subprocess.run([*args,'-E','-P',str(cpp)],capture_output=True,text=True)
                    self.assertEqual(pre.returncode,0,pre.stderr)
                    obj=tmp/(name+'.o')
                    build=subprocess.run([*args,'-c',str(cpp),'-o',str(obj)],capture_output=True,text=True)
                    self.assertEqual(build.returncode,0,build.stderr)
                    variants.append((pre.stdout,obj.read_bytes()))
                self.assertEqual(variants[0],variants[1],f'tiles={tiles}')
                self.assertEqual(variants[1],variants[2],f'tiles={tiles}')


if __name__ == '__main__':
    unittest.main()

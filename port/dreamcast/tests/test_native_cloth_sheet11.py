"""Consumed EF11 source/packet/clip fixtures; public synthetic inputs only."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1];INC=ROOT/'game/platform/include'
spec=importlib.util.spec_from_file_location('ef11_previous',ROOT/'tests/test_native_draw_outcomes.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def packet_harness():
    stub,code=old.harness()
    code=code.replace('sent[2048]','sent[8192]')
    code=code.replace('struct Entry{Package package;unsigned frame=0;} entry;',
                      'constexpr unsigned kTextureCount=1;struct Entry{Package package;unsigned frame=0,upload_incarnation=1;bool valid=true;} entries[1];Entry& entry=entries[0];')
    code=code.replace('#include "native_effect_strip21.inc"','extern "C" void re4dc_log(const char*,...){}\nbool fx_r200_tail_select(unsigned,unsigned char*&,unsigned*&){return false;}\n#include "native_effect_strip21.inc"')
    code=code.replace('void pvr_poly_compile(pvr_poly_hdr_t* p,','unsigned compiles=0;\nvoid pvr_poly_compile(pvr_poly_hdr_t* p,').replace('*p={};p->words[0]', '++compiles;*p={};p->words[0]')
    return stub,code

class ClothSheet11(unittest.TestCase):
    def run_code(self,stub,code,extra=()):
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth11-') as td:
            tmp=Path(td);(tmp/'dc').mkdir();(tmp/'dc/pvr.h').write_text(stub);cpp=tmp/'fixture.cpp';cpp.write_text(code);exe=tmp/'check'
            args=['g++','-std=c++20','-O2','-DRE4DC_FX_STRIP21=1','-DRE4DC_CLOTH_NATIVE=1','-DRE4DC_NATIVE_DRAW_OUTCOMES=1',
                  '-DRE4DC_CLOTH_SHEET11=1','-DRE4DC_PS2_UPLOAD_INCARNATION=1','-DRE4DC_UI_HANDLES=1','-DRE4DC_TA_DIRECT=1','-DRE4DC_EFFECT_SPRITE_MAX=64',
                  '-fsanitize=address,undefined','-fno-pie','-no-pie','-I'+str(tmp),'-I'+str(INC),'-I'+str(ROOT/'room'),*extra,
                  str(cpp),str(ROOT/'room/pvr_geometry.cpp'),'-o',str(exe)]
            build=subprocess.run(args,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_actual_prepared_packets_lifetime_and_partial_refusal(self):
        stub,code=packet_harness()
        code+=r'''
using Outcome=re4dc::NativeDrawOutcome;
void fresh(){reset();source_draws_finished=false;stream_aborted=false;frame_ready=true;draining_parts=false;direct_open=false;
 missing=false;spill_available=true;entry.valid=true;entry.upload_incarnation=1;entry.package.value.width=64;compiles=opens=0;}
Re4dcEffectMesh21 sheet(unsigned cols,unsigned rows){auto q=quad();Re4dcEffectMesh21 m{};
 m.image=q.image;m.cols=cols;m.rows=rows;m.color=q.color;m.src=q.src;m.dst=q.dst;m.wrap_s=q.wrap_s;m.wrap_t=q.wrap_t;
 std::memcpy(m.projection,q.projection,sizeof m.projection);std::memcpy(m.viewport,q.viewport,sizeof m.viewport);return m;}
int main(){
 for(unsigned cols:{2U,99U,100U}){fresh();auto m=sheet(cols,4);Re4dcClothMaterial11 material;re4dc::NativeDrawResult stop{Outcome::Refused};
  assert(re4dc_cloth_prepare11(&m,&material,&stop));assert(opens==1&&compiles==1&&entry.frame==frame);
  float top[300],bottom[300];for(unsigned i=0;i<cols;++i){top[3*i]=bottom[3*i]=float(i)*.01f;top[3*i+1]=1;bottom[3*i+1]=0;top[3*i+2]=bottom[3*i+2]=-10;}
  source_draws_finished=true;
  for(unsigned row=0;row<3;++row){Re4dcClothBand11 b{top,bottom,cols,0,row};auto result=re4dc_cloth_band11(&material,&b);
   assert(result.outcome==Outcome::Submitted&&result.submitted==1&&!result.fallback_allowed());
   const auto* v=reinterpret_cast<const pvr_vertex_t*>(sent);assert(sent_bytes==(2*cols+1)*32&&v[2*cols].flags==PVR_CMD_VERTEX_EOL);
   assert(v[1].u==0&&v[2*cols].u==1&&v[1].v==row*(1.f/3));}
  assert(opens==1&&compiles==1);
  entry.upload_incarnation=2;Re4dcClothBand11 b{top,bottom,cols,0,0};auto result=re4dc_cloth_band11(&material,&b);assert(result.outcome==Outcome::Refused&&!result.published());
 }
 float top[]={-1,1,-10,1,1,-10},bottom[]={-1,-1,-10,1,-1,-10};
 fresh();auto m=sheet(2,3);Re4dcClothMaterial11 material;re4dc::NativeDrawResult stop{Outcome::Refused};assert(re4dc_cloth_prepare11(&m,&material,&stop));
 deferred_top=16384+kEffectQuad21Node+5*32;spill_available=false;re4dc::NativeDrawProgress progress;
 Re4dcClothBand11 b{top,bottom,2,0,0};assert(progress.add(re4dc_cloth_band11(&material,&b)));b.row=1;
 assert(!progress.add(re4dc_cloth_band11(&material,&b)));assert(progress.result.outcome==Outcome::PartialAbort&&progress.result.queued==1&&!progress.result.fallback_allowed()&&deferred_count==1);
 for(unsigned cols:{101U,255U}){m=sheet(cols,3);assert(!re4dc_cloth_prepare11(&m,&material,&stop)&&stop.outcome==Outcome::UnsupportedBeforePublication);
  b.row=0;assert(re4dc_cloth_band11(&material,&b).outcome==Outcome::Refused);}
 fresh();m=sheet(2,3);missing=true;assert(!re4dc_cloth_prepare11(&m,&material,&stop)&&stop.outcome==Outcome::Refused&&!deferred_count);
 missing=false;entry.upload_incarnation=0;assert(!re4dc_cloth_prepare11(&m,&material,&stop)&&stop.outcome==Outcome::Refused&&!deferred_count);
 entry.upload_incarnation=1;m.color=0;assert(!re4dc_cloth_prepare11(&m,&material,&stop)&&stop.outcome==Outcome::PolicySkip);
 m.color=0xffffffff;assert(re4dc_cloth_prepare11(&m,&material,&stop));++frame;assert(re4dc_cloth_band11(&material,&b).outcome==Outcome::Refused);--frame;
 fresh();m=sheet(2,2);assert(re4dc_cloth_prepare11(&m,&material,&stop));entry.valid=false;assert(re4dc_cloth_band11(&material,&b).outcome==Outcome::Refused);
 // One prepared material serves near-clipped cells and source-correct topology.
 fresh();m=sheet(2,2);assert(re4dc_cloth_prepare11(&m,&material,&stop));top[2]=-.5f;
 source_draws_finished=true;auto result=re4dc_cloth_band11(&material,&b);assert(result.published()&&opens==1&&compiles==1);
}
'''
        self.run_code(stub,code)
        self.run_code(stub,code,('-DRE4DC_FX_R200_ENTRY_CAP=1',))

    def test_actual_source_rolling_rows_preflight_and_pool_retirement(self):
        source=(REPO/'src/game/cloth.cpp').read_text();start=source.index('#if defined(RE4DC_NATIVE_DRAW_OUTCOMES)',source.index('static int re4dc_cloth_visible'))
        end=source.index('\n#endif\n\n// clothTrans builds',start);adapter=source[start:end]
        epoch_start=source.index('#if defined(RE4DC_CLOTH_SHEET11)',source.index('Cloth ClothWk[8]'))
        epoch_end=source.index('\n#endif',epoch_start)+len('\n#endif');epochs=source[epoch_start:epoch_end]
        destroy=old.function(source,'void Cloth::Destroy()');init=old.function(source,'void ClothInit()')
        routing_start=source.index('\n#if defined(RE4DC_CLOTH_NATIVE)',source.index('    GXSetChanMatColor(4, pCL->color);'))
        routing_end=source.index('\n#if defined(RE4DC_FALLBACK_AUDIT29)',routing_start)
        routing=source[routing_start:routing_end]
        fallback=old.function(source,'    for (i = 0; i < pCL->divV - 1; i++)')
        stub,code=packet_harness()
        code=code.replace('Entry* resolve(', 'void source_hook();\nEntry* resolve(').replace('++opens;return missing?', '++opens;source_hook();return missing?')
        code+=r'''
#include "native_cloth_sheet11.hpp"
using u32=unsigned;using f32=float;using Mtx=float[3][4];struct Vec{float x,y,z;};
struct Color{unsigned char r,g,b,a;};struct cLight{Color DispCol;unsigned xD;float Radius;Vec World;};
struct Env{Color AmbientScr{255,255,255,255};};struct LightManager{Env e;Env* getEnvPtr(){return &e;}} LightMgr;
struct Global{struct{Mtx v_mat;}Cam;unsigned Frame_cnt;}global_value,*pG=&global_value;
struct Cloth{void* tex;void* pTobjA;unsigned divH,divV;void* tlut;unsigned x74;Color color;float Scale;Mtx mat;Vec* pVer;Vec* pNor;void* m_pMem;unsigned be_flag;void Destroy();};
Cloth ClothWk[8];
'''+epochs+r'''
unsigned retirement_before=0;
void Mem_free(void*){assert(cloth11_epoch(&ClothWk[0])!=retirement_before);}
'''+destroy+'\n'+init+r'''
unsigned transforms=0;bool retire_on_load=false,fail_after_retire=false,frame_on_load=false,retire_transform=false,row_retired=false;
void source_hook(){if(retire_on_load){retirement_before=cloth11_epoch(&ClothWk[0]);ClothWk[0].Destroy();if(fail_after_retire)missing=true;}if(frame_on_load)++pG->Frame_cnt;}
void PSMTXScale(Mtx m,float,float,float){std::memset(m,0,sizeof(Mtx));m[0][0]=m[1][1]=m[2][2]=1;}
void PSMTXConcat(const Mtx,const Mtx,Mtx out){PSMTXScale(out,1,1,1);}
void PSMTXMultVec(const Mtx,const Vec* p,Vec* out){assert(!row_retired);++transforms;*out=*p;
 if(retire_transform&&transforms==4){retirement_before=cloth11_epoch(&ClothWk[0]);ClothWk[0].Destroy();++entry.upload_incarnation;row_retired=true;}}
float GetDistance3(Vec*,Vec*){return 0;}
void projection(float* out){auto q=quad();std::memcpy(out,q.projection,sizeof q.projection);}
void viewport(float* out){auto q=quad();std::memcpy(out,q.viewport,sizeof q.viewport);}
#define RE4DC_GXF_GET_PROJECTION(p) projection(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport(p)
'''+adapter+r'''
unsigned fallback_reads=0,fallback_draws=0;
void GXBegin(unsigned primitive,unsigned,unsigned){assert(primitive==0x98);++fallback_draws;}
void GXPosition3f32(float,float,float){++fallback_reads;}
void GXNormal3f32(float,float,float){}void GXTexCoord2f32(float,float){}
void actual_cloth_caller(Cloth* pCL,cLight** lights,Vec* pos,float size){
 struct{struct{cLight* pLight[8];}LightInfo;Vec pos;}model{};
 std::memcpy(model.LightInfo.pLight,lights,sizeof model.LightInfo.pLight);model.pos=*pos;float r=size;int i,j,k,t;
'''+routing+'\n'+fallback+r'''
}
void fresh_source(){reset();source_draws_finished=true;stream_aborted=false;frame_ready=true;draining_parts=false;direct_open=false;
 missing=false;spill_available=true;entry.valid=true;entry.upload_incarnation=1;compiles=opens=transforms=0;retire_on_load=fail_after_retire=frame_on_load=retire_transform=row_retired=false;fallback_reads=fallback_draws=0;pG->Frame_cnt=frame;ClothWk[0].be_flag=0x31;}
int main(){using Outcome=re4dc::NativeDrawOutcome;cLight* lights[8]{};Vec pos{};unsigned tex[]={1,(64<<16)|64,14,0};
 for(unsigned width:{2U,99U,100U,101U,255U}){fresh_source();std::vector<Vec> grid(width*4);
  for(unsigned r=0;r<4;++r)for(unsigned col=0;col<width;++col)grid[r*width+col]={float(col)*.001f,float(r),-10};
  auto original=grid;auto& c=ClothWk[0];c={};c.tex=tex;c.divH=width;c.divV=4;c.pVer=grid.data();c.be_flag=0x31;c.Scale=1;c.color={128,64,32,192};
  auto result=re4dc_cloth_native(&c,lights,&pos,1);
  if(width<=100){assert(result.outcome==Outcome::Submitted&&result.submitted==3&&transforms==width*4&&opens==1&&compiles==1);}
  else assert(result.outcome==Outcome::UnsupportedBeforePublication&&!transforms&&!opens);
  assert(!std::memcmp(original.data(),grid.data(),grid.size()*sizeof(Vec)));
 }
 fresh_source();Vec grid[8];for(unsigned i=0;i<8;++i)grid[i]={float(i%2),float(i/2),-10};auto& c=ClothWk[0];c={};c.tex=tex;c.divH=2;c.divV=4;c.pVer=grid;c.be_flag=0x31;c.Scale=1;c.color={255,255,255,255};
 missing=true;auto result=re4dc_cloth_native(&c,lights,&pos,1);assert(result.outcome==Outcome::Refused&&!transforms&&!deferred_count);
 fresh_source();retire_on_load=true;result=re4dc_cloth_native(&c,lights,&pos,1);assert(result.outcome==Outcome::PartialAbort&&!result.fallback_allowed()&&!transforms&&!deferred_count);
 Vec normals[8]{};c.pNor=normals;
 for(unsigned failing_load:{0U,1U}){fresh_source();retire_on_load=true;fail_after_retire=failing_load;actual_cloth_caller(&c,lights,&pos,1);
  assert(!fallback_reads&&!fallback_draws&&!transforms&&!deferred_count);}
 fresh_source();frame_on_load=true;actual_cloth_caller(&c,lights,&pos,1);assert(!fallback_reads&&!fallback_draws&&!transforms&&!deferred_count);
 fresh_source();retire_transform=true;actual_cloth_caller(&c,lights,&pos,1);assert(!fallback_reads&&!fallback_draws&&transforms==4&&!deferred_count);
 fresh_source();retirement_before=cloth11_epoch(&c);c.Destroy();actual_cloth_caller(&c,lights,&pos,1);assert(!fallback_reads&&!fallback_draws&&!transforms&&!opens);
 fresh_source();c.be_flag=1;actual_cloth_caller(&c,lights,&pos,1);assert(!fallback_reads&&!fallback_draws&&!transforms&&!opens);
 // Ordinary resource refusal retains a valid source and its previous routing.
 fresh_source();missing=true;actual_cloth_caller(&c,lights,&pos,1);assert(fallback_reads==12&&fallback_draws==3&&!transforms);
 fresh_source();grid[7].x=std::numeric_limits<float>::quiet_NaN();result=re4dc_cloth_native(&c,lights,&pos,1);assert(result.outcome==Outcome::UnsupportedBeforePublication&&!transforms&&!opens);grid[7].x=1;
 fresh_source();source_draws_finished=false;deferred_top=16384+kEffectQuad21Node+5*32;spill_available=false;
 result=re4dc_cloth_native(&c,lights,&pos,1);assert(result.outcome==Outcome::PartialAbort&&result.queued==1&&!result.fallback_allowed()&&transforms==6&&deferred_count==1&&opens==1&&compiles==1);
 fresh_source();c.pTobjA=&c;result=re4dc_cloth_native(&c,lights,&pos,1);assert(result.outcome==Outcome::UnsupportedBeforePublication&&!transforms&&!opens);c.pTobjA=nullptr;
 fresh_source();Cloth foreign=c;result=re4dc_cloth_native(&foreign,lights,&pos,1);assert(result.outcome==Outcome::UnsupportedBeforePublication&&!opens&&!transforms);
 assert(!cloth11_epoch(reinterpret_cast<Cloth*>(reinterpret_cast<unsigned char*>(ClothWk)+1)));
 auto slot=cloth11_slot(&c);cloth11_incarnation[slot]=~0U;cloth11_replace(&c);assert(!cloth11_epoch(&c));cloth11_replace(&c);assert(!cloth11_epoch(&c));ClothInit();assert(!cloth11_epoch(&c));c.be_flag=0x31;
 result=re4dc_cloth_native(&c,lights,&pos,1);assert(result.outcome==Outcome::UnsupportedBeforePublication);
}
'''
        self.run_code(stub,code)

    def test_non_coplanar_clipped_cells_match_actual_source_strip_triangle_order(self):
        source=(REPO/'src/game/cloth.cpp').read_text();start=source.index('    for (i = 0; i < pCL->divV - 1; i++)')
        loop=old.function(source,'    for (i = 0; i < pCL->divV - 1; i++)')
        stub,code=packet_harness()
        code+=r'''
struct Vec{float x,y,z;};struct Cloth{unsigned divH,divV;Vec* pVer;Vec* pNor;};using f32=float;
struct Captured{Vec position;float u,v;};Captured captured[4];unsigned cursor;
void GXBegin(unsigned primitive,unsigned,unsigned n){assert(primitive==0x98&&n==4);cursor=0;}
void GXPosition3f32(float x,float y,float z){captured[cursor].position={x,y,z};}
void GXNormal3f32(float,float,float){}
void GXTexCoord2f32(float u,float v){captured[cursor].u=u;captured[cursor].v=v;++cursor;}
void actual_source(Cloth* pCL){int i,j,k,t;
'''+loop+r'''
}
int main(){Vec grid[]={{-1,1,-.5f},{1,1,-6},{-1,-1,-3},{1,-1,-17}},normal[4]{};Cloth c{2,2,grid,normal};actual_source(&c);assert(cursor==4);
 auto q=quad();for(unsigned i=0;i<4;++i){q.positions[i][0]=captured[i].position.x;q.positions[i][1]=captured[i].position.y;q.positions[i][2]=captured[i].position.z;q.u[i]=captured[i].u;q.v[i]=captured[i].v;}
 pvr_vertex_t actual[12]{},expected[12]{};unsigned n=re4dc::cloth11::cell(q,actual),used=0;
 const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
 re4dc::render::ClipParameters clip{near,far,RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,re4dc::effect_strip21::project,&q};
 // Derive parity and corner order from the captured source strip, rather than
 // use the new helper's hand-written triangles as an oracle.
 for(unsigned tri=0;tri+2<cursor;++tri){re4dc::render::RenderVertex vertices[3]{};
  for(unsigned k=0;k<3;++k){unsigned ix=tri+(tri%2&&k<2?1-k:k);auto& v=vertices[k];const auto& in=captured[ix];
   v.position.world_x=v.position.x=in.position.x;v.position.world_y=v.position.y=in.position.y;v.position.world_z=v.position.z=in.position.z;v.position.depth=-in.position.z;
   if(v.position.depth>=near)re4dc::effect_strip21::project(v.position.x,v.position.y,v.position.z,&q);
   v.u=in.u;v.v=in.v;v.light_red=v.light_green=v.light_blue=1;}
  used+=3*re4dc::render::clip_projected_triangle(vertices,expected+used,0,clip);}
 for(unsigned i=0;i<used;++i)expected[i].argb=q.color;
 assert(n==used&&n>6&&!std::memcmp(actual,expected,n*sizeof(pvr_vertex_t)));
 // The old cloth-through-quad diagonal differs on this noncoplanar cell.
 Re4dcEffectQuad old=q;const unsigned order[]={0,1,3,2};for(unsigned i=0;i<4;++i){std::memcpy(old.positions[i],q.positions[order[i]],sizeof old.positions[i]);old.u[i]=q.u[order[i]];old.v[i]=q.v[order[i]];}
 pvr_vertex_t wrong[12]{};unsigned wrong_n=re4dc::effect_strip21::vertices(old,wrong);assert(wrong_n!=n||std::memcmp(actual,wrong,n*sizeof(pvr_vertex_t)));
}
'''
        self.run_code(stub,code)

    def test_disabled_emitter_objects_match_parent_absent_and_zero(self):
        stub,code=packet_harness()
        parent=subprocess.check_output(['git','show','255964fdc7d22a61acff1ef59734a36ec91ebff0:port/dreamcast/game/platform/include/native_effect_strip21.inc'],cwd=REPO,text=True)
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth11-off-') as td:
            tmp=Path(td);(tmp/'dc').mkdir();(tmp/'dc/pvr.h').write_text(stub);parent_dir=tmp/'parent';parent_dir.mkdir();(parent_dir/'native_effect_strip21.inc').write_text(parent)
            objects=[]
            for name,flags,first in [('parent',[],parent_dir),('absent',[],INC),('zero',['-DRE4DC_CLOTH_SHEET11=0'],INC)]:
                dest=tmp/(name+'.o');args=['g++','-std=c++20','-g0','-O2','-DRE4DC_FX_STRIP21=1','-DRE4DC_CLOTH_NATIVE=1',
                     '-DRE4DC_NATIVE_DRAW_OUTCOMES=1','-DRE4DC_PS2_UPLOAD_INCARNATION=1','-DRE4DC_UI_HANDLES=1','-DRE4DC_TA_DIRECT=1','-DRE4DC_EFFECT_SPRITE_MAX=64',*flags,
                     '-I'+str(tmp),'-I'+str(first),'-I'+str(INC),'-I'+str(ROOT/'room'),'-x','c++','-','-c','-o',str(dest)]
                build=subprocess.run(args,input=code,capture_output=True,text=True,cwd=INC);self.assertEqual(build.returncode,0,build.stderr);objects.append(dest.read_bytes())
            self.assertEqual(objects[0],objects[1]);self.assertEqual(objects[0],objects[2])

    def test_make_control_default_off_strict_dependencies_and_two_consumers(self):
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth11-make-') as td:
            tmp=Path(td);mk=tmp/'fixture.mk';targets=['obj/src/game/cloth.o','obj/platform/native_ui.o']
            mk.write_text('OBJDIR := obj\ninclude '+str(ROOT/'game/effects30.mk')+'\n'+
                          '\n'.join(t+':\n\t@echo FLAGS $(GAME_CPPFLAGS) $(PLATFORM_CPPFLAGS)' for t in targets)+'\n')
            deps=['EFFECT_SPRITES=1','FX_STRIP21=1','CLOTH_NATIVE=1','NATIVE_DRAW_OUTCOMES=1','PS2_UPLOAD_INCARNATION=1']
            for value in (None,'0','1','2','-1'):
                args=['make','--no-print-directory','-f',str(mk),*targets,*deps]
                if value is not None:args+=['CLOTH_SHEET11='+value]
                run=subprocess.run(args,capture_output=True,text=True,cwd=tmp)
                if value in ('2','-1'):
                    self.assertNotEqual(run.returncode,0);self.assertIn('CLOTH_SHEET11 must be 0 or 1',run.stderr)
                else:
                    self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(run.stdout.count('-DRE4DC_CLOTH_SHEET11=1'),2 if value=='1' else 0)
            for dep in ('CLOTH_NATIVE','NATIVE_DRAW_OUTCOMES','PS2_UPLOAD_INCARNATION'):
                run=subprocess.run(['make','--no-print-directory','-f',str(mk),targets[0],*deps,'CLOTH_SHEET11=1',dep+'=0'],capture_output=True,text=True,cwd=tmp)
                self.assertNotEqual(run.returncode,0);self.assertIn('CLOTH_SHEET11 needs',run.stderr)

if __name__=='__main__':unittest.main()

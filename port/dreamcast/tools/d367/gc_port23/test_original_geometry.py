"""Actual source parser/member/bridge controls, synthetic source bytes only."""
from pathlib import Path
import subprocess,tempfile,unittest
from test_runtime_hooks import function
HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]/'game'
class OriginalGeometryTests(unittest.TestCase):
 def compile(self,text,mutant=False,payload=None):
  with tempfile.TemporaryDirectory(prefix='gc-original-bridge-',dir='/dev/shm') as d:
   p=Path(d)/'source.cpp';p.write_text(text);exe=Path(d)/'check'
   helper=GAME/'platform/gc_asset_payloads.cpp'
   if payload is not None:helper=Path(d)/'payload.cpp';helper.write_text(payload)
   subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_GC_ASSET_TEST=1','-I',str(GAME/'platform'),'-I',str(GAME/'platform/include'),str(p),str(GAME/'platform/gc_asset_members.cpp'),str(GAME/'platform/gc_asset_gate.cpp'),str(helper),'-o',str(exe)],check=True,capture_output=True,text=True)
   q=subprocess.run([str(exe)],capture_output=True,text=True)
   self.assertNotEqual(q.returncode,0,q.stderr) if mutant else self.assertEqual(q.returncode,0,q.stderr)
 def test_actual_parser_and_member_lifetime(self):self.compile((HERE/'test_original_geometry.cpp').read_text())
 def fixture(self):
  bridge=(GAME/'model_bridge.cpp').read_text()
  names=['bool gcasset_original_input(','extern "C" unsigned re4dc_gcasset_original_color_member(','extern "C" void re4dc_gcasset_pose_reset(','extern "C" void re4dc_gcasset_pose_publish(','extern "C" void re4dc_gcasset_shape_reset(','extern "C" void re4dc_gcasset_shape_source(','extern "C" unsigned re4dc_gcasset_weapon_consumer(','extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_original_model_select(','extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_original_actor_select(']
  fixture=(HERE/'test_original_bridge.cpp.in').read_text().replace('// ACTOR_SELECTION',(GAME/'platform/include/gc_asset_actor_select.inc').read_text()).replace('// BRIDGE_FUNCTIONS','\n'.join(function(bridge,n) for n in names))
  ui=(GAME/'platform/native_ui.cpp').read_text()
  fixture=fixture.replace('// UI_ACCEPT_FUNCTIONS',function(ui,'void gcasset_model_prepare(')+'\n'+function(ui,'void gcasset_model_accept('))
  model=(GAME/'platform/native_model.cpp').read_text();start=model.index('extern "C" void re4dc_model_submit(')
  gateway=model[start:model.index('#if RE4DC_NATIVE_ACTOR\n',start)]+'observe_selected(p);\n}\n'
  return fixture.replace('// MODEL_GATEWAY',gateway)
 def test_actual_raw_rigid_prepared_lazy_and_foreign_sources(self):self.compile(self.fixture())
 def test_semantic_mutants(self):
  source=self.fixture()
  for old,new in [('part->uv!=input.uv','false'),('!member_pose_current(info,member.serial,part->positions,part->normals,pG->Frame_cnt)','false'),('source->positions!=d->vtxOrig','false')]:
   with self.subTest(mutant=old):self.assertIn(old,source);self.compile(source.replace(old,new),True)

 def test_compound_acceptance_mutants(self):
  source=self.fixture();payload=(GAME/'platform/gc_asset_payloads.cpp').read_text()
  for old,new in [('member_accept(c->member_serial,mask);','/* lost original member */'),('c.parent->serial==c.parent_serial','true'),('!member_serial_current(member_serial)','false')]:
   with self.subTest(mutant=old):self.assertIn(old,payload);self.compile(source,True,payload.replace(old,new))

 def test_fe_reader_layout_contract(self):
  native=(GAME/'platform/native_actor_fast.cpp').read_text()
  header=native[native.index('struct BlobHeader {'):native.index('// flags bits 2..6')]
  records=native[native.index('struct Records {'):native.index('inline const BlobHeader* blob_of(')]
  self.compile('#include <cstddef>\n#include <cstdint>\nusing u8=unsigned char;using u16=unsigned short;using u32=unsigned;\n'+header+records+'\nextern "C" void re4dc_log(const char*,...){}\nint main(){static_assert(offsetof(BlobHeader,meshlets)==4 && offsetof(BlobHeader,color_index)==6 && offsetof(BlobHeader,rec4)==8 && offsetof(BlobHeader,idx4)==10 && offsetof(BlobHeader,lod4)==12);u16 data[8]={0,0,0,7,0,0,0,9};Records variable{data,4,2,true},constant{data,4,2,false};return variable.ci(0)!=7 || variable.ci(1)!=9 || constant.ci(1)!=2;}\n')

 def test_actual_source_output_publication_boundaries(self):
  trans=(GAME.parents[2]/'src/game/trans.cpp').read_text()
  bodies=function(trans,'extern "C" void re4dc_face_lazy_resolve(')+'\n'+function(trans,'extern "C" int re4dc_skin_materialize(')
  fixture=r'''
#include "gc_asset_members.h"
#include <cassert>
#include <cstdint>
using u32=std::uintptr_t;using u8=unsigned char;
extern "C" void re4dc_log(const char*,...){}
struct Weight{};struct WeightExt{};struct cModel{};
struct ModelData{unsigned weight_ext_num=0,weight_palette_num=2,shift=0,flags=0,nVtx=3,nNrm=3;void*pWeight=nullptr,*vtxOrig=nullptr,*nrmOrig=nullptr;};
struct cModelInfo{ModelData*pData;void*pPosBuf[2]{},*pNrmBuf[2]{};};
struct Global{unsigned vtx_buf_no=0,Frame_cnt=1;}global;Global*pG=&global;
struct Face{cModelInfo*info=nullptr;void*pos=nullptr;cModel*m=nullptr;}g_faceLazy;
cModel*g_skinLazyMtx=nullptr;unsigned g_skinLazyMtxFrame=0;u32 g_gqr6=111,g_skin_palette=0;
unsigned phase=0,resets=0,published=0,writes=0;bool allocation=true;alignas(32) char output[128];
extern "C" void re4dc_gcasset_pose_reset(const void*){assert(!re4dc_gcasset::geometry_producers_idle());phase=1;++resets;}
extern "C" void re4dc_gcasset_pose_publish(const void*,unsigned frame,unsigned lazy){assert(!re4dc_gcasset::geometry_producers_idle());assert(phase==3 && g_gqr6==111 && !g_skin_palette && frame==1 && !lazy);++published;}
void setupGQR6(u32 n){g_gqr6=n;}void calcWeightMat(cModel*){}void MakeWeightPalette(Weight*,unsigned){}void MakeWeightPaletteExt(WeightExt*,unsigned){}
void DCStoreRangeNoSync(void*,unsigned){}
void CalcSk1_x(void* dst,const void*src,unsigned n){assert(dst && src && n==3 && (phase==1 || phase==2));++phase;++writes;}
void CalcSk1_x2(void*d,const void*s,unsigned n){CalcSk1_x(d,s,n);}
void*re4dc_prim_tail(unsigned,unsigned){assert(phase==1);return allocation?output:nullptr;}
''' + bodies + r'''
int main(){ModelData data;data.vtxOrig=output+80;data.nrmOrig=output+100;cModelInfo info{&data};cModel model;float palette[16]{};
 allocation=false;assert(!re4dc_skin_materialize(&info,palette));assert(resets==1 && !writes && !published && re4dc_gcasset::geometry_producers_idle());
 allocation=true;assert(re4dc_skin_materialize(&info,palette));assert(resets==2 && writes==2 && published==1 && re4dc_gcasset::geometry_producers_idle());
 data.flags=0x20000000;assert(re4dc_skin_materialize(&info,palette));assert(resets==3 && writes==4 && published==2);
 re4dc_face_lazy_resolve(nullptr);assert(resets==3 && published==2);
 g_faceLazy={&info,output+1,&model};re4dc_face_lazy_resolve(&info);assert(resets==3 && published==2);
 for(unsigned flags:{0U,0x20000000U}){data.flags=flags;g_faceLazy={&info,info.pPosBuf[0],&model};re4dc_face_lazy_resolve(&info);assert(!g_faceLazy.info && re4dc_gcasset::geometry_producers_idle());}
 assert(resets==5 && writes==8 && published==4);}
'''
  fixture='#include <initializer_list>\n#define RE4DC_GAME 1\n#define RE4DC_NATIVE_ACTOR_SKIN_LAZY 1\n'+fixture
  self.compile(fixture)
  for old,new in [('re4dc_gcasset_pose_reset(info);','/* omitted reset */'),('re4dc_gcasset_pose_publish(info,pG->Frame_cnt,0);','/* omitted completion publication */')]:
   with self.subTest(mutant=old):self.compile(fixture.replace(old,new),True)

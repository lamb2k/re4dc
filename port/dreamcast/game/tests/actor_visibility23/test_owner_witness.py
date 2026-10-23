"""Bounded host-only witness controls. No SDK copies, target build or guest."""
from pathlib import Path
import hashlib,json,os,re,struct,subprocess,tempfile,unittest
HERE=Path(__file__).resolve().parent
GAME=HERE.parent.parent
ROOT=GAME.parents[2]
BASE='bea2d402ba06d41fb7b39946b5a9431a72f5b52a'
OUT=Path(os.environ.get('AV23_WITNESS_TEST_OUT','/tmp'))
HEADER=GAME/'platform/include/actor_visibility23_witness.h'

def extract(text,name):
 match=re.search(r'[^\n]*\b'+re.escape(name)+r'\([^;]*?\)\s*\{',text,re.S)
 if not match:raise AssertionError(name)
 start=text.rfind('\n',0,match.start())+1;at=text.index('{',match.start());depth=1;i=at+1
 while depth:
  if text[i]=='{':depth+=1
  if text[i]=='}':depth-=1
  i+=1
 return text[start:i]

def compile_run(source,defines=()):
 with tempfile.TemporaryDirectory(dir=OUT)as temp:
  p=Path(temp);cpp=p/'control.cpp';cpp.write_text(source);exe=p/'control'
  compile=subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off',*defines,'-I'+str(HEADER.parent),str(cpp),'-o',str(exe)],capture_output=True,text=True)
  if compile.returncode:raise AssertionError(compile.stderr)
  run=subprocess.run([str(exe)],capture_output=True,text=True)
  if run.returncode:raise AssertionError(run.stderr)

COMMON=r'''
#include "actor_visibility23_witness.h"
#include <cassert>
#include <cstring>
using namespace actor_visibility23::witness;
'''

class OwnerWitnessTests(unittest.TestCase):
 def sdk(self):
  path=os.environ.get('AV23_WITNESS_SDK')
  if not path:self.skipTest('Set AV23_WITNESS_SDK to the retained SDK; no SDK copies are made')
  return Path(path)
 def actual_cc(self,p,enabled,source=None):
  # Only the old small tracked warp header is materialized, never an SDK.
  inc=p/'include';inc.mkdir(exist_ok=True)
  (inc/'warp_late.h').write_bytes(subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':port/dreamcast/game/platform/include/warp_late.h']))
  obj=p/('actor-'+str(enabled)+'.o')
  command=['g++','-std=c++17','-O2','-ffunction-sections','-fdata-sections','-fno-fast-math','-ffp-contract=off','-DRE4DC_ACTOR_VISIBILITY23=1','-DRE4DC_DBG_WARP=1','-DRE4DC_ACTOR_VISIBILITY23_WITNESS='+str(enabled),'-I'+str(self.sdk()/'include'),'-I'+str(p),'-c',str(source or GAME/'platform/actor_visibility23.cc'),'-o',str(obj)]
  result=subprocess.run(command,capture_output=True,text=True)
  if result.returncode:self.fail(result.stderr)
  return obj
 def test_bounded_state_lifetime_receipt_and_both_actual_skip_commits(self):
  compile_run((HERE/'test_owner_witness.cpp').read_text().replace('#include "../../platform/include/actor_visibility23_witness.h"','#include "actor_visibility23_witness.h"').replace('#include "../../platform/include/actor_visibility23_window.h"','#include "actor_visibility23_window.h"'))

 def test_actual_owner_bridge_copies_live_fields_and_refuses_unknown_lifetime(self):
  bridge=extract((GAME/'coarse_actor_owner_ganado.inc').read_text(),'re4dc_actor_visibility23_witness_owner')
  prefix=COMMON+r'''
struct Info{Info* pList;};struct cModel{unsigned id,serial,be_flag;Info* pModelInfo;};
struct Global{unsigned room_id,Frame_cnt;} global{0x119,99};Global* pG=&global;
namespace re4dc_material{namespace life{unsigned serial=30;}}
unsigned current_epoch=2;
extern "C" unsigned re4dc_actor_visibility23_epoch(){return current_epoch;}
extern "C" unsigned re4dc_ui_frame(){return 200;}
'''
  suffix=r'''
int main(){Info head{},body{&head},foreign{};cModel m{0x2b,10,7,&body};Owner o{};
 assert(re4dc_actor_visibility23_witness_owner(&m,&body,2,&o)==1&&o.id==0x2b&&o.serial==10&&o.role==0&&o.life==30&&o.game==99&&o.ui==200);
 assert(re4dc_actor_visibility23_witness_owner(&m,&head,2,&o)==1&&o.role==1&&o.info==reinterpret_cast<std::uintptr_t>(&head));
 assert(re4dc_actor_visibility23_witness_owner(&m,&foreign,2,&o)==-1);
 assert(re4dc_actor_visibility23_witness_owner(&m,&body,3,&o)==-1);
 current_epoch=0;assert(re4dc_actor_visibility23_witness_owner(&m,&body,2,&o)==-1);current_epoch=2;
 m.serial=11;assert(re4dc_actor_visibility23_witness_owner(&m,&body,2,&o)==1&&o.serial==11);
 m.id=0x10;assert(re4dc_actor_visibility23_witness_owner(&m,&body,2,&o)==0);
 assert(re4dc_actor_visibility23_witness_owner(nullptr,&body,2,&o)==-1);
 assert(re4dc_actor_visibility23_witness_owner(&m,&body,2,nullptr)==-1);
}
'''
  compile_run(prefix+bridge+suffix)

 def test_actual_ready_getter_snapshot_uses_consumed_field_receipt_and_outcome(self):
  getter=extract((GAME/'platform/native_static.cpp').read_text(),'re4dc_actor_world23_ready')
  prefix=COMMON+r'''
namespace actor_visibility23{namespace r119{unsigned full[2]={3,5};}}
struct ReceiptStub{
 const void* storage=reinterpret_cast<void*>(0x6000);const void* metadata=reinterpret_cast<void*>(0x7000);
 unsigned owner=1,active=0,complete=1,epoch=2,stamp=2,frame=200,scene=300,mode=0,coverage[2]={3,5};float near=100,far[2]={20000,21000};
 bool allow=true;unsigned calls=0,k=9,f=0,fp=9;
 bool ready(unsigned frame,const void*,const float*,const float*,const float*,unsigned field,float,float,unsigned,unsigned mode){++calls;k=field;f=frame;fp=mode;return allow;}
}actor_world23;
struct PS{unsigned room=0x119;const void* storage=reinterpret_cast<void*>(0x6000);}ps2w;
unsigned enemyVisSidecarCrc=0xfb5072f8U,scene=300,ui_calls=0,mode_calls=0;int intact=1;unsigned checked_field=0;
struct re4dc_room_header{};
const void* current_metadata=reinterpret_cast<void*>(0x7000);
extern "C" unsigned re4dc_actor_world23_scene(){return scene;}
unsigned re4dc_ui_frame(){++ui_calls;return 200;}
unsigned actor_world23_mode(){++mode_calls;return 0;}
const void* re4dc_room_section(const char*,unsigned* b,unsigned* v,unsigned*,const re4dc_room_header**){*b=1376;*v=2;return current_metadata;}
int re4dc_ps2_placements_intact(unsigned,const unsigned char* field,unsigned n){assert(n==1);checked_field=field[0];return intact;}
World captured{};unsigned captures=0;
extern "C" void re4dc_actor_visibility23_witness_world(const World* w){captured=*w;++captures;}
'''
  suffix=r'''
int main(){float v[12]={1,0,0,-112950,0,1,0,-4000,0,0,1,-20000},P[7]{},V[6]{};
 assert(re4dc_actor_world23_ready(v,P,V,100,19000)==1);
 assert(captures==1&&captured.field==5&&captured.required==3&&captured.coverage==3&&captured.stage==Placement&&captured.result==1&&checked_field==5);
 assert(captured.frame==200&&captured.current_frame==200&&captured.current_storage==0x6000&&captured.current_metadata==0x7000&&captured.current_near==100&&captured.far==20000);
 assert(ui_calls==1&&mode_calls==1&&actor_world23.calls==1&&actor_world23.k==0);
 v[3]=-117050;assert(re4dc_actor_world23_ready(v,P,V,100,19000)==1&&captured.field==7&&captured.required==5&&checked_field==7&&actor_world23.k==1);
 intact=0;assert(!re4dc_actor_world23_ready(v,P,V,100,19000)&&captured.stage==Placement&&!captured.result);intact=1;
 actor_world23.allow=false;assert(!re4dc_actor_world23_ready(v,P,V,100,19000)&&captured.stage==Receipt&&!captured.result);actor_world23.allow=true;
 current_metadata=reinterpret_cast<void*>(0x7010);assert(!re4dc_actor_world23_ready(v,P,V,100,19000)&&captured.stage==Metadata);current_metadata=reinterpret_cast<void*>(0x7000);
 v[3]=0;assert(!re4dc_actor_world23_ready(v,P,V,100,19000)&&captured.stage==Cell&&!captured.field);
 scene=0;assert(!re4dc_actor_world23_ready(v,P,V,100,19000)&&captured.stage==Scene&&!captured.field);
}
'''
  compile_run(prefix+getter+suffix,['-DRE4DC_ACTOR_VISIBILITY23_WITNESS=1'])

 def test_actual_diagnostic_api_and_both_native_caller_branches(self):
  with tempfile.TemporaryDirectory(dir=OUT)as temp:
   p=Path(temp);obj=self.actual_cc(p,1);native=(GAME/'platform/native_actor_fast.cpp').read_text()
   wrapper=extract(native,'observed_section_wall23')
   branches=[]
   for match in re.finditer(r'if\(AV23_SECTION23\(',native):
    start=match.start();i=native.index('{',start)+1;depth=1
    while depth:
     depth+=(native[i]=='{')-(native[i]=='}');i+=1
    branches.append(native[start:i])
   self.assertEqual(len(branches),2)
   prefix=COMMON+r'''
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>
extern "C" unsigned re4dc_actor_visibility23_mode;
extern "C" void re4dc_actor_visibility23_frame(unsigned,unsigned,unsigned,unsigned);
std::vector<std::string> logs;
extern "C" void re4dc_log(const char* format,...){char row[256];va_list a;va_start(a,format);const int n=vsnprintf(row,sizeof(row),format,a);va_end(a);assert(n>0&&n<int(sizeof(row)));if(std::string(row).find("AV23OWNER")==0)logs.emplace_back(row);}
extern "C" int re4dc_actor_visibility23_witness_owner(const void* model,const void* info,unsigned epoch,Owner* out){*out={reinterpret_cast<std::uintptr_t>(model),reinterpret_cast<std::uintptr_t>(info),0x2b,10,epoch,30,unsigned(reinterpret_cast<std::uintptr_t>(info)==0x2010),7,0x119,100,200};return 1;}
struct Re4dcModelPart{const void* model=reinterpret_cast<void*>(0x1000);const void* info=reinterpret_cast<void*>(0x2000);};
struct Frame{const void* positions=reinterpret_cast<void*>(0x3000);};struct BlobHeader{};struct MeshletInfo{};
struct Records{const unsigned short* r=reinterpret_cast<const unsigned short*>(0x5000);};
unsigned frame_serial=1;bool hide=false;
static bool section_wall23(const Re4dcModelPart& p,Frame&,const BlobHeader*,const MeshletInfo&,const Records&,unsigned,unsigned,unsigned){
 Owner o{};re4dc_actor_visibility23_witness_owner(p.model,p.info,2,&o);re4dc_actor_visibility23_witness_identity(1,&o);
 float lo[3]={1,2,3},hi[3]={4,5,6},v[12]{},P[7]{},V[6]{};re4dc_actor_visibility23_witness_bounds(lo,hi,v,P,V);
 World w{};w.storage=w.current_storage=0x6000;w.metadata=w.current_metadata=0x7000;w.stage=Placement;w.field=5;w.result=w.owner=w.complete=1;w.epoch=w.stamp=2;w.frame=w.current_frame=200;w.scene=w.current_scene=300;w.coverage=w.required=3;w.room=0x119;w.metadata_bytes=1376;w.metadata_version=2;re4dc_actor_visibility23_witness_world(&w);
 if(hide)re4dc_actor_visibility23_witness_potential();return hide;
}
'''
   middle=wrapper+r'''
#define AV23_SECTION23 observed_section_wall23
#define AV23_WITNESS_ARGS(level,path) ,level,path
struct{unsigned meshlets_culled=0;}stats;struct{unsigned input=0;}e;
int main(){re4dc_actor_visibility23_frame(1,1,0x40,0);Re4dcModelPart p;Frame f;BlobHeader b;const BlobHeader* blob=&b;MeshletInfo m;Records r;
 unsigned level=2,mi=3,nv=12,nt=8,positions_started=0;
 for(unsigned run=0;run<2;++run){hide=run;
'''+branches[0]+r'''
 ++positions_started;}
 p.info=reinterpret_cast<void*>(0x2010);nv=20;nt=10;
 for(unsigned run=0;run<2;++run){hide=run;
'''+branches[1]+r'''
 ++positions_started;}
 assert(positions_started==2&&stats.meshlets_culled==2&&e.input==18);
 for(unsigned serial=2;serial<=601;++serial)re4dc_actor_visibility23_frame(serial,1,0x40,0);
 assert(logs.size()==39&&logs[0].find("complete=1 qualified=1 fail=0 mode=2 binds=600")!=std::string::npos);
 assert(logs[1].find("query=2 bound=2 potential=1 would=12 skip=1 positions=12 triangles=8")!=std::string::npos);
 assert(logs[2].find("query=2 bound=2 potential=1 would=20 skip=1 positions=20 triangles=10")!=std::string::npos);
 unsigned committed=0;for(const auto& line:logs)if(line.find("AV23OWNER_SOURCE")==0&&line.find("potential=1 committed=1")!=std::string::npos)++committed;
 assert(committed==2);
}
'''
   cpp=p/'api.cpp';cpp.write_text(prefix+middle);exe=p/'api'
   command=['g++','-std=c++17','-O2','-DRE4DC_ACTOR_VISIBILITY23_WITNESS=1','-I'+str(HEADER.parent),str(cpp),str(obj),'-Wl,--gc-sections','-o',str(exe)]
   result=subprocess.run(command,capture_output=True,text=True)
   if result.returncode:self.fail(result.stderr)
   result=subprocess.run([str(exe)],capture_output=True,text=True)
   if result.returncode:self.fail(result.stderr)

 def test_actual_host_helper_object_identity_with_witness_off(self):
  def allocated(path):
   blob=path.read_bytes();self.assertEqual(blob[:5],b'\x7fELF\x02');offset=struct.unpack_from('<Q',blob,40)[0];size,count,strings=struct.unpack_from('<HHH',blob,58)
   rows=[struct.unpack_from('<IIQQQQIIQQ',blob,offset+i*size)for i in range(count)];names=blob[rows[strings][4]:rows[strings][4]+rows[strings][5]]
   return {names[r[0]:].split(b'\0',1)[0].decode():(r[1],r[2],r[5],None if r[1]==8 else blob[r[4]:r[4]+r[5]])for r in rows if r[2]&2}
  with tempfile.TemporaryDirectory(dir=OUT)as temp:
   p=Path(temp);new=self.actual_cc(p,0);old=p/'baseline';(old/'platform/include').mkdir(parents=True)
   for name in('actor_visibility23.cc','include/actor_visibility23.h','include/actor_visibility23_window.h','include/warp_late.h'):
    (old/'platform'/name).write_bytes(subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':port/dreamcast/game/platform/'+name]))
   before=self.actual_cc(old,0,old/'platform/actor_visibility23.cc')
   self.assertEqual(allocated(before),allocated(new))
   symbols=subprocess.check_output(['nm',str(new)],text=True);self.assertNotIn('witness',symbols)

 def test_witness_off_preprocessed_tokens_preserve_all_existing_runtime_files(self):
  paths=('platform/native_actor_fast.cpp','platform/native_static.cpp','coarse_actor_owner_ganado.inc','platform/actor_visibility23.cc','platform/include/actor_visibility23.h')
  for relative in paths:
   new=(GAME/relative).read_text();tracked='port/dreamcast/game/'+relative
   old=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+tracked],text=True)
   def preprocess(text):
    text=re.sub(r'^\s*#\s*include[^\n]*(?:\n|$)','\n',text,flags=re.M)
    p=subprocess.run(['g++','-std=c++17','-E','-P','-x','c++','-DRE4DC_ACTOR_VISIBILITY23=1','-DRE4DC_ACTOR_VISIBILITY23_WITNESS=0','-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_ENEMY_VIS_CULL=1','-'],input=text,text=True,capture_output=True)
    if p.returncode:raise AssertionError(p.stderr)
    return re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\w+|[^\s]',p.stdout)
   with self.subTest(path=relative):self.assertEqual(preprocess(old),preprocess(new))

 def test_fixed_logs_and_real_both_callers_only_commit_inside_skip_branch(self):
  cc=(GAME/'platform/actor_visibility23.cc').read_text();native=(GAME/'platform/native_actor_fast.cpp').read_text()
  self.assertIn('for(unsigned i=0;i<4;++i)',cc);self.assertEqual(cc.count('AV23OWNER_SAMPLE slot='),1)
  self.assertEqual(cc.count('AV23OWNER_WORLD slot='),1);self.assertNotIn('re4dc_log',extract(native,'section_wall23'))
  for path in(0,1):
   pattern=r'if\(AV23_SECTION23\(p,f,blob,m,r,mi,nv,nt AV23_WITNESS_ARGS\(level,'+str(path)+r'\)\)\)\{\s*#if RE4DC_ACTOR_VISIBILITY23_WITNESS\s*re4dc_actor_visibility23_witness_skip\('+str(path)+r',level,mi,nv,nt\);\s*#endif\s*\+\+stats.meshlets_culled;e.input\+=nt;continue;\}'
   self.assertRegex(native,pattern)
  self.assertEqual(native.count('re4dc_actor_visibility23_witness_skip('),2)
  self.assertEqual(len(re.findall(r'AV23_SECTION23\(',native)),2)

 def test_actual_report_fits_native256_byte_formatter_even_at_counter_limits(self):
  text=(GAME/'platform/actor_visibility23.cc').read_text();word=extract(text,'witness_word23');report=extract(text,'witness_report23')
  prefix=COMMON+r'''
#include <cstdio>
#include <cstdarg>
State owner_witness23;unsigned lines=0,bytes=0;
extern "C" void re4dc_log(const char* format,...){char line[256];va_list a;va_start(a,format);int n=vsnprintf(line,sizeof(line),format,a);va_end(a);assert(n>0&&n<int(sizeof(line)));++lines;bytes+=n;}
'''
  suffix=r'''
int main(){auto& w=owner_witness23;w.complete=w.sealed=w.owner_seen=true;w.mode=2;w.binds=600;w.failures=~0U;w.unattributed=~0U;
 w.owner={0xffffffffU,0xffffffffU,0x2b,~0U,~0U,~0U,1,~0U,0x119,~0U,~0U};
 for(auto& c:w.parts)c={~0U,~0U,~0U,~0U,~0U,~0U,~0U};w.infos[0]=w.infos[1]=0xffffffffU;
 for(unsigned i=0;i<4;++i){auto& sample=w.samples[i];sample.present=true;auto& q=sample.query;q.token=~0U;q.owner=w.owner;q.owner.role=i/2;
 q.source={0xffffffffU,0xffffffffU,0xffffffffU,0xffffffffU,0xffffffffU,~0U,2,~0U,~0U,~0U,~0U,1};q.potential=q.committed=true;
 q.world.storage=q.world.current_storage=q.world.metadata=q.world.current_metadata=0xffffffffU;
 q.world.stage=Placement;q.world.field=7;q.world.result=q.world.owner=q.world.complete=1;q.world.active=0;
 q.world.epoch=q.world.stamp=q.world.frame=q.world.current_frame=q.world.scene=q.world.current_scene=~0U;
 q.world.fpscr=q.world.current_fpscr=q.world.coverage=q.world.required=~0U;q.world.room=0x119;q.world.metadata_bytes=1376;q.world.metadata_version=2;
 }
 witness_report23();assert(lines==39&&bytes<=39*255);
}
'''
  compile_run(prefix+word+'\n'+report+suffix)

 def test_make_toggle_is_default_off_validated_and_only_owned_diagnostics_flagged(self):
  with tempfile.TemporaryDirectory(dir=OUT)as temp:
   p=Path(temp);mk=p/'check.mk'
   mk.write_text('OBJDIR:=obj\nACTOR_TRANSACTION:=1\nENEMY_VIS_CULL:=1\nPS2_INTERIOR_CULL:=1\nPS2_INTERIOR_ACTORS:=2\nCROWD_INVIS_SKIP:=1\nCOARSE_GANADO_CAST:=1\nPS2_WORLD_DYNAMIC:=1\nPS2_WORLD_PARTS:=1\nMIST_CUT:=0\nTRANS_POLICY_DEBUG:=0\nDBG_WARP:=1\nWORLD_SCRATCH:=0\nMESH_FASTPATH:=1\nHW_LEAN:=1\nMESH_VP_SCHED:=1\nWORLD_RECT21:=1\nCPU_BACKFACE:=0\nACTOR_VISIBILITY23_CERT:=private-certificate-not-used-by-this-control\ninclude '+str(GAME/'actor_visibility23.mk')+'\nobj/platform/native_actor_fast.o:\n\t@echo $(PLATFORM_CPPFLAGS)\n')
   def flags(*values):return subprocess.run(['make','--no-print-directory','-n','-f',str(mk),'obj/platform/native_actor_fast.o',*values],cwd=GAME,capture_output=True,text=True)
   default=flags();self.assertEqual(default.returncode,0,default.stderr);self.assertNotIn('WITNESS=1',default.stdout)
   off=flags('ACTOR_VISIBILITY23=1');self.assertEqual(off.returncode,0,off.stderr);self.assertNotIn('WITNESS=1',off.stdout)
   on=flags('ACTOR_VISIBILITY23=1','ACTOR_VISIBILITY23_WITNESS=1');self.assertEqual(on.returncode,0,on.stderr);self.assertIn('-DRE4DC_ACTOR_VISIBILITY23_WITNESS=1',on.stdout)
   for value in('2','-1','0 1',''):
    result=flags('ACTOR_VISIBILITY23=1','ACTOR_VISIBILITY23_WITNESS='+value);self.assertNotEqual(result.returncode,0)
   self.assertNotEqual(flags('ACTOR_VISIBILITY23_WITNESS=1').returncode,0)

if __name__=='__main__':unittest.main()

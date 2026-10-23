from pathlib import Path
import hashlib,importlib.util,io,json,os,re,subprocess,tempfile,time,unittest
HERE=Path(__file__).resolve().parent
G=Path(os.environ.get('AV23_MATERIAL_GAME',str(HERE.parent.parent)))
R=Path(os.environ['AV23_MATERIAL_REPO']) if 'AV23_MATERIAL_REPO' in os.environ else Path(subprocess.check_output(['git','-C',str(G),'rev-parse','--show-toplevel'],text=True).strip())
_base_temp=tempfile.TemporaryDirectory(prefix='material-route23-host-') if 'AV23_MATERIAL_EVIDENCE' not in os.environ else None
E=Path(os.environ['AV23_MATERIAL_EVIDENCE']) if 'AV23_MATERIAL_EVIDENCE' in os.environ else Path(_base_temp.name)
BASE='18a9db3b400721c00ab5aa3a912cbd5681547919';TMP=E/'host-scratch';TMP.mkdir(exist_ok=True)
for name in ('actor_visibility23_window.h','warp_late.h'):
 p=G/'platform/include'/name
 if not p.exists():p.write_bytes(subprocess.check_output(['git','-C',str(R),'show',BASE+':port/dreamcast/game/platform/include/'+name]))
spec=importlib.util.spec_from_file_location('prior_witness',R/'port/dreamcast/game/tests/actor_visibility23/test_owner_witness.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old.GAME=G;old.HEADER=G/'platform/include/actor_visibility23_witness.h';old.OUT=TMP
os.environ.setdefault('AV23_WITNESS_SDK','/root/probe/codex-actor-visibility23/port/dreamcast/game/.actor-visibility23-sdk-final')
def extract(s,n):return old.extract(s,n)
def compile_run(s):return old.compile_run(s)
class MaterialControls(unittest.TestCase):
 def test_actual_readonly_source_bridge_modes_debug_owner_lifetime_and_run(self):
  source=(G/'coarse_actor_owner_ganado.inc').read_text();bridge=extract(source,'re4dc_actor_visibility23_source_cull')
  original=subprocess.check_output(['git','-C',str(R),'show',BASE+':port/dreamcast/game/platform/include/native_model.h'],text=True);mapping=extract(original,'re4dc_model_cull')
  pre='''#include "actor_visibility23_material.h"
#include <cassert>
struct cModelInfo{cModelInfo* pList;unsigned blend_mode;};
struct cModel{unsigned id,be_flag,CullMode,z_mode; cModelInfo* pModelInfo;};
struct Global{unsigned Debug_flg[1];} global{};Global* pG=&global;
unsigned current_epoch=2;extern "C" unsigned re4dc_actor_visibility23_epoch(){return current_epoch;}
'''
  post='''int main(){cModelInfo head{},body{&head,0},other{};cModel m{0x2b,1,0,0,&body};
assert(re4dc_actor_visibility23_source_cull(&m,&body,2)==2);
assert(re4dc_actor_visibility23_source_cull(&m,&head,2)==2);
m.CullMode=1;assert(re4dc_actor_visibility23_source_cull(&m,&body,2)==1);
global.Debug_flg[0]=0x20000000;assert(re4dc_actor_visibility23_source_cull(&m,&body,2)==2);
for(unsigned mode: {2U,3U,255U}){m.CullMode=mode;assert(!re4dc_actor_visibility23_source_cull(&m,&body,2));}
m.CullMode=0;assert(!re4dc_actor_visibility23_source_cull(&m,&other,2));assert(!re4dc_actor_visibility23_source_cull(&m,&body,1));
current_epoch=0;assert(!re4dc_actor_visibility23_source_cull(&m,&body,2));current_epoch=2;
m.id=0x10;assert(!re4dc_actor_visibility23_source_cull(&m,&body,2));m.id=0x2b;
m.be_flag=0;assert(!re4dc_actor_visibility23_source_cull(&m,&body,2));m.be_flag=0x4001;assert(!re4dc_actor_visibility23_source_cull(&m,&body,2));m.be_flag=1;
m.z_mode=1;assert(!re4dc_actor_visibility23_source_cull(&m,&body,2));m.z_mode=0;
head.blend_mode=1;assert(!re4dc_actor_visibility23_source_cull(&m,&head,2));assert(re4dc_actor_visibility23_source_cull(&m,&body,2)==2);
assert(!re4dc_actor_visibility23_source_cull(nullptr,&body,2));assert(!re4dc_actor_visibility23_source_cull(&m,nullptr,2));}
'''
  compile_run(pre+'#include <initializer_list>\n'+mapping+'\n'+bridge+'\n'+post)
 def test_actual_material_helper_all_negative_run_overrides(self):
  compile_run('''#include "actor_visibility23_material.h"
#include <cassert>
#include <initializer_list>
using namespace actor_visibility23::material23;
int main(){Inputs b{0,0,255,256,0,0,8,false,true,true,true,true};assert(!refusal(b));
for(unsigned c=0;c<3;++c){auto a=b;a.cull=c;assert(!refusal(a));}
#define CASE(member,value,bit) {auto a=b;a.member=value;assert(refusal(a)==bit);}
CASE(blend,1,Blend) CASE(flags,4,Masked) CASE(alpha,254,Alpha) CASE(alpha,511,Alpha)
CASE(mask,true,MaskImage) CASE(mask_ref,0,MaskRef) CASE(cull,3,BackendCull)
CASE(depth,1,Depth) CASE(stride,6,Stride) CASE(same_stream,false,Stream)
CASE(skin,false,Skin) CASE(owned,false,Owned) CASE(palette,false,Palette)
for(unsigned bit: {Stream,Skin,Owned,Stride,Palette})assert(!diagnostic_provenance(bit,true,true));
assert(!diagnostic_provenance(Alpha,false,true));assert(!diagnostic_provenance(Alpha,true,false));assert(diagnostic_provenance(Alpha|Depth,true,true));
auto a=b;a.alpha=0;a.depth=1;a.mask=true;assert(refusal(a)==(Alpha|Depth|MaskImage));
}
''')
 def test_actual_refusal_api_never_views_unsafe_provenance(self):
  function=extract((G/'platform/actor_visibility23.cc').read_text(),'re4dc_actor_visibility23_witness_material')
  compile_run('#include "actor_visibility23_material.h"\n#include "actor_visibility23_witness.h"\n#include <cassert>\n#include <initializer_list>\nusing namespace actor_visibility23::witness;\nState owner_witness23;unsigned views=0;\nextern "C" unsigned re4dc_actor_visibility23_view(float*,const void*,const void*){++views;return 0;}\nextern "C" int re4dc_actor_visibility23_witness_owner(const void*,const void*,unsigned,Owner*){assert(false);return -1;}\n'+function+'\nint main(){using namespace actor_visibility23::material23;owner_witness23.pending.live=true;\nauto& s=owner_witness23.pending.source;s.owner=s.info=1;\nfor(unsigned bit: {Stream,Skin,Owned,Stride,Palette})re4dc_actor_visibility23_witness_material(bit);\nassert(views==0);s.owner=0;re4dc_actor_visibility23_witness_material(Alpha);assert(views==0);\ns.owner=1;s.info=0;re4dc_actor_visibility23_witness_material(Alpha);assert(views==0);\ns.info=1;re4dc_actor_visibility23_witness_material(Alpha|Depth);assert(views==1);}\n')
 def test_fixed_attributed_refusal_count_and_overflow(self):
  compile_run('''#include "actor_visibility23_witness.h"
#include <cassert>
using namespace actor_visibility23::witness;
int main(){State s;s.material(4);assert(!s.refused[0]);s.pending.live=true;s.material(4);assert(!s.refused[0]);
s.pending.tracked=true;s.pending.owner.role=1;s.material(4);s.material(2048);assert(s.refused[1]==2&&s.refuse[1]==2052&&s.refused[0]==0);
s.refused[1]=~0U;s.material(1);assert(s.failures&Overflow);assert(sizeof(State)<=4096);}
''')
 def test_exact_report_worst_width_still39_lines_below256B(self):
  text=(G/'platform/actor_visibility23.cc').read_text();word=extract(text,'witness_word23');report=extract(text,'witness_report23')
  # Reuse the real prior formatting control, adding maximum values for BOTH new fields.
  original=old.compile_run
  def capture(s,defines=()):
   s=s.replace('for(auto& c:w.parts)c=', 'w.refused[0]=w.refused[1]=~0U;w.refuse[0]=w.refuse[1]=~0U;for(auto& c:w.parts)c=')
   return original(s,defines)
  old.compile_run=capture
  try:old.OwnerWitnessTests().test_actual_report_fits_native256_byte_formatter_even_at_counter_limits()
  finally:old.compile_run=original
 def test_actual_full_helper_on_compiles_with_new_api(self):
  with tempfile.TemporaryDirectory(dir=TMP) as temp:
   obj=old.OwnerWitnessTests().actual_cc(Path(temp),1)
   symbols=subprocess.check_output(['nm','-S',str(obj)],text=True)
   self.assertIn('re4dc_actor_visibility23_witness_material',symbols)
   state=next(line for line in symbols.splitlines() if 'owner_witness23' in line)
   self.assertLessEqual(int(state.split()[1],16),4096)
 def test_actual_host_helper_off_allocated_identity(self):
  old.OwnerWitnessTests().test_actual_host_helper_object_identity_with_witness_off()
 def test_existing_bounded_state_controls(self):
  old.OwnerWitnessTests().test_bounded_state_lifetime_receipt_and_both_actual_skip_commits()
 def test_default_experiment_off_tokens_and_backend_untouched(self):
  for rel in ('platform/native_actor_fast.cpp','platform/actor_visibility23.cc','platform/include/actor_visibility23.h','coarse_actor_owner_ganado.inc'):
   before=subprocess.check_output(['git','-C',str(R),'show',BASE+':port/dreamcast/game/'+rel],text=True);after=(G/rel).read_text()
   def pp(text):
    text=re.sub(r'^\s*#\s*include[^\n]*(?:\n|$)','\n',text,flags=re.M)
    out=subprocess.run(['g++','-E','-P','-x','c++','-DRE4DC_ACTOR_VISIBILITY23=0','-DRE4DC_ACTOR_VISIBILITY23_WITNESS=0','-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_ENEMY_VIS_CULL=1','-'],input=text,text=True,capture_output=True);self.assertEqual(out.returncode,0,out.stderr)
    return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',out.stdout)
   self.assertEqual(pp(before),pp(after),rel)
  bridge=extract((G/'coarse_actor_owner_ganado.inc').read_text(),'re4dc_actor_visibility23_source_cull')
  self.assertNotRegex(bridge,r'(?:p|part|b)[.>]cull\s*=')
  native=(G/'platform/native_actor_fast.cpp').read_text();section=extract(native,'section_wall23')
  self.assertLess(section.index('re4dc_actor_visibility23_view'),section.index('re4dc_actor_visibility23_source_cull'))
  self.assertNotRegex(section,r'p\.cull\s*=')
  self.assertEqual(native.count('re4dc_actor_visibility23_witness_skip('),2)

if __name__=='__main__':
 log=io.StringIO();start=time.monotonic();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MaterialControls));elapsed=time.monotonic()-start
 (E/'host-material.log').write_text(log.getvalue());print(log.getvalue());print('SECONDS',elapsed)
 record={'status':'PASS' if result.wasSuccessful() else 'FAIL','methods':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'seconds':elapsed,'source_parent':BASE,'files':[{'path':str(p.relative_to(G)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in G.rglob('*') if p.is_file()]};(E/'HOST-MATERIAL-RESULTS.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)

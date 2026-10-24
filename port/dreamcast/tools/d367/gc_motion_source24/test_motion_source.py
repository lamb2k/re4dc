"""Production source/helper tests. Synthetic original inputs; no SDK or guest.

The real gate's hash, catalog binding and token validation are linked unchanged.
Only accepted-use/fault sinks are replaced to inspect the new helper in isolation:
production gate Motion remains unwired until root's whole-unit review.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
import re
ROOT=Path(__file__).resolve().parents[5]
PLATFORM=ROOT/'port/dreamcast/game/platform'
FLAGS=['-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1','-DRE4DC_GC_ASSET_MOTION_SOURCE=1','-DRE4DC_GC_ASSET_TEST=1','-I'+str(PLATFORM/'include')]
FIXTURE=r"""
#include "gc_asset_motion_source.h"
#include "gc_asset_motion_unknown.h"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdarg>
#include <vector>
using namespace re4dc_gcasset;
NATIVE_FIXTURE
namespace re4dc_gcasset {Digest gate_fingerprint(const void*,unsigned);CheckedAsset gate_bind_checked(const char*,const char*,const Digest&);}
bool protected_context=false,motion_mutex=false;unsigned hashes=0,accepts=0,faults=0;CheckedAsset accepted[128]{};
extern "C" void re4dc_log(const char*,...){assert(!protected_context);}
namespace re4dc_gcasset {
Digest fingerprint(const void* p,unsigned n){assert(!protected_context);++hashes;return gate_fingerprint(p,n);}
CheckedAsset bind_checked(const char* k,const char* id,const Digest& d){assert(!protected_context && !motion_mutex);return gate_bind_checked(k,id,d);}
void emitted_checked(Consumer c,CheckedAsset a){assert(!protected_context && c==Motion);assert(checked_current(a));accepted[accepts++]=a;}
void unresolved(Consumer c,const char*){assert(!protected_context && c==Motion);++faults;}
}
void ident(const Digest& d,char* id){const char* h="0123456789abcdef";for(unsigned i=0;i<20;++i){id[2*i]=h[d.bytes[i]>>4];id[2*i+1]=h[d.bytes[i]&15];}id[40]=0;}
void word(unsigned char* p,unsigned v){std::memcpy(p,&v,4);}
void actual_read_archive(const void* m,void* pArc,unsigned len){
LOADER_CAPTURE
}
void actual_retire_archive(const void* m){
LOADER_RETIRE
}
int main(){
 alignas(32) unsigned char source_storage[16448]{};std::memset(source_storage,0x5a,sizeof source_storage);
 assert(motion_source_test_storage_bytes()<=16384);
 assert(!motion_source_storage_bind(source_storage+1,16384));
 assert(!motion_source_storage_bind(source_storage+32,1));
 assert(motion_source_storage_bind(source_storage+32,16384));
 assert(motion_source_storage_bind(source_storage+32,16384));
 assert(!motion_source_storage_bind(source_storage+64,16384));
 unsigned owner=0,model=0,camera=0,shape=0;unsigned char fcv[64]{1,2,1},evd[96]{4,5},bind[80]{9,10};word(fcv+12,16);fcv[16]=fcv[32]=fcv[48]=1;
 const auto original=gate_fingerprint(fcv,sizeof fcv);char id0[41],id1[41],id2[41];ident(original,id0);ident(gate_fingerprint(evd,sizeof evd),id1);ident(gate_fingerprint(bind,sizeof bind),id2);
 CatalogRow rows[]={{"motion",id0,original,PS2},{"motion",id1,gate_fingerprint(evd,sizeof evd),GameCube},{"motion",id2,gate_fingerprint(bind,sizeof bind),Authored}};
 assert(install(rows,3));begin(0x100,1,0x1f6);
 assert(motion_source_adopt(&owner,fcv,sizeof fcv,MotionFcv));
 assert(motion_source_adopt(&owner,evd,sizeof evd,MotionEvd));
 assert(motion_source_adopt(&owner,bind,sizeof bind,MotionBind));
 assert(accepts==0);const unsigned original_hashes=hashes;
 // Relocation/pose preparation after capture never changes source identities.
 std::memset(fcv,0xaa,sizeof fcv);
 assert(motion_source_adopt(&owner,fcv,sizeof fcv,MotionFcv));assert(hashes==original_hashes);
 assert(!motion_source_adopt(&owner,fcv,sizeof fcv-1,MotionFcv));
 assert(!motion_source_adopt(&shape,fcv+1,10,MotionFcv));
 faults=0;
 std::memset(fcv+16,0,48);fcv[16]=fcv[32]=fcv[48]=1;
 protected_context=true;
 motion_source_note_key(&model,fcv,fcv+16,0);motion_source_note(&model,evd+8,MotionEvd);
 motion_source_note(&shape,bind,MotionBind);motion_source_note_key(&camera,fcv,fcv+16,0);
 motion_source_view(&camera);
 const auto receipt=motion_source_snapshot(&model,&shape);assert(receipt.count==3 && !receipt.fault);
 motion_source_accept(receipt,0);protected_context=false;motion_source_flush();assert(!accepts && !faults);
 // Nested scopes in frozen deferred replay must retain the saved contributor
 // set rather than resnapshot a later subject with an additional live source.
 unsigned snapshot_owner=0,snapshot_other=0;unsigned char snapshot_extra[80]{};
 assert(motion_source_adopt(&snapshot_owner,snapshot_extra,sizeof snapshot_extra,MotionBind));
 motion_source_note(&model,snapshot_extra,MotionBind);
 assert(motion_source_snapshot(&model,&shape).count==4);
 {MotionSourceScope saved(receipt);assert(!motion_source_idle());
  {MotionSourceScope nested(&model,&shape);assert(motion_source_replay_active());assert(motion_source_current().count==3);}
  {MotionSourceScope mismatch(&snapshot_other,&shape);assert(motion_source_current().fault && !motion_source_current().count);}
 }
 assert(!motion_source_replay_active() && motion_source_idle());
 // Actual accepted record latches; all hashing/catalog/logging waits for flush.
 {MotionUnknownScope unknown(motion_model_reason());MotionSourceScope scope(receipt);motion_prepare();protected_context=true;motion_accept_pending(7);protected_context=false;}
 assert(!accepts);motion_unknown_flush();assert(accepts==3 && faults==1);faults=0;
 AssetDescription description{};assert(describe_checked(accepted[0],&description));assert(!std::memcmp(description.digest.bytes,original.bytes,32));assert(description.provenance==PS2);
 assert(describe_checked(accepted[1],&description));assert(description.provenance==GameCube);
 // Deferred snapshot cannot follow a new generation at the same address.
 motion_source_retire(&owner);const unsigned before=accepts;
 assert(!motion_source_adopt(&owner,fcv,sizeof fcv,MotionFcv));std::memset(fcv,0,sizeof fcv);fcv[2]=1;word(fcv+12,16);fcv[16]=fcv[32]=fcv[48]=1;assert(motion_source_adopt(&owner,fcv,sizeof fcv,MotionFcv));faults=0;
 protected_context=true;motion_source_accept(receipt,1);protected_context=false;motion_source_flush();assert(accepts==before && faults==1);
 motion_source_reset(&model);auto stale=motion_source_snapshot(&model);assert(stale.fault);
 // Evaluation without any accepted records is never emission.
 const unsigned evaluated=accepts;motion_source_note_key(&model,fcv,fcv+16,0);motion_source_flush();assert(accepts==evaluated);
 // Unbound pointers, malformed roles and stale catalog tokens fail closed.
 protected_context=true;motion_source_note(&shape,reinterpret_cast<void*>(1),MotionFcv);motion_source_accept(motion_source_snapshot(&shape),1);protected_context=false;motion_source_flush();assert(faults>=2);
 retire_catalog();protected_context=true;motion_source_accept(motion_source_snapshot(&model),1);protected_context=false;motion_source_flush();assert(accepts==evaluated);
 motion_source_retire(&owner);motion_source_reset(&model);motion_source_reset(&camera);motion_source_reset(&shape);
 // Complete original archive FCV capture, never only an MTC shell prefix.
 unsigned char arc[160]{};word(arc,2);word(arc+16,32);word(arc+20,96);std::memcpy(arc+24,"FCV",3);std::memcpy(arc+28,"BIN",3);arc[34]=1;word(arc+44,16);arc[48]=arc[64]=arc[80]=1;
 end(1);assert(install(rows,3));begin(0x100,2,0x1f6);
 const unsigned prior_hashes=hashes;actual_read_archive(&owner,arc,sizeof arc);assert(hashes==prior_hashes+2);assert(accepts==evaluated);
 motion_source_reset(&model);motion_source_note_key(&model,arc+32,arc+48,0);
 const auto archive_receipt=motion_source_snapshot(&model);const unsigned original_archive_hashes=hashes;
 std::memset(arc+32,0xcc,64);actual_read_archive(&owner,arc,sizeof arc);assert(hashes==original_archive_hashes);
 protected_context=true;motion_source_accept(archive_receipt,1);protected_context=false;motion_source_flush();assert(accepts==evaluated+1);
 assert(describe_checked(accepted[accepts-1],&description));assert(description.provenance==Unknown);
 actual_retire_archive(&owner);const unsigned original_accepts=accepts;
 protected_context=true;motion_source_accept(archive_receipt,1);protected_context=false;motion_source_flush();assert(accepts==original_accepts);
 motion_source_retire(&owner);std::memset(arc+32,0,64);arc[34]=1;word(arc+44,16);arc[48]=arc[64]=arc[80]=1;std::memcpy(arc+28,"MTC",3);const unsigned prefix_hashes=hashes;assert(motion_source_archive(&owner,arc,sizeof arc));assert(hashes==prefix_hashes);
 word(arc+20,32);std::memcpy(arc+28,"FCV",3);assert(!motion_source_archive(&owner,arc,sizeof arc));
 // Cold external source: exact production capture block before table writes,
 // actual Re4dcMotionLease publishes only after its acquire mutex is released.
 unsigned char clip[64]{};clip[2]=1;word(clip+12,16);clip[16]=clip[32]=clip[48]=1;
 unsigned char proxy[16];std::memcpy(proxy,clip,16);
 const auto cold_original=gate_fingerprint(clip,sizeof clip);native_begin(proxy,clip);unsigned* destination=nullptr;
 const unsigned before_external=accepts;unsigned ticket=0;
 {Re4dcMotionLease lease(proxy,&destination,nullptr);assert(lease.external());assert(destination);
  ticket=motion_source_external_serial(native_owner(),clip,proxy);assert(ticket);
  assert(!re4dc_motion_gcasset_idle());
  motion_source_reset(&model);motion_source_note_key(&model,proxy,clip+16,0);
  const auto external=motion_source_snapshot(&model);
  assert(external.count==1);
  {MotionSourceScope frozen(external);MotionSourceScope nested(&model);assert(motion_source_current().count==1);}
  motion_source_reset(&model);motion_source_note_key(&model,proxy,clip+16,0);
  {MotionSourceScope stale(external);assert(motion_source_current().fault && !motion_source_current().count);}
  const auto current_external=motion_source_snapshot(&model);
  motion_source_reset(&shape);motion_source_note_key(&shape,proxy,clip+60,0);assert(motion_source_snapshot(&shape).fault);
  protected_context=true;motion_source_accept(current_external,1);protected_context=false;
 }
 assert(re4dc_motion_gcasset_idle());
 motion_mutex=true;assert(!re4dc_motion_gcasset_idle());motion_source_external_invalidate(native_owner());motion_mutex=false;
 motion_source_flush();assert(accepts==before_external+1); // accepted identity survives cold-slot eviction
 assert(describe_checked(accepted[accepts-1],&description));assert(!std::memcmp(description.digest.bytes,cold_original.bytes,32));
 assert(!motion_source_external_publish(native_owner(),ticket));
 // Foreign keys cannot be blessed by an authentic proxy/header or source name.
 motion_source_reset(&model);motion_source_note_key(&model,proxy,clip+16,0);assert(motion_source_snapshot(&model).fault);
 native_stop();
 // Invalid directory sizes/ranges and serial exhaustion do not read a span.
 word(arc,4097);assert(!motion_source_archive(&owner,arc,sizeof arc));
 assert(!motion_source_adopt(&owner,reinterpret_cast<void*>(~std::uintptr_t(0)-3),8,MotionFcv));
 motion_source_test_serial(0xfffffffeU);assert(!motion_source_adopt(&owner,arc,sizeof arc,MotionEvd));
 for(unsigned i=0;i<32;++i){assert(source_storage[i]==0x5a);assert(source_storage[16416+i]==0x5a);}
 std::puts("source capture, original digest, accepted replay, negative, mutation and lifetime controls PASS");
}
"""
class MotionSourceTests(unittest.TestCase):
 def compile_run(self,mutant=None,reject=False):
  with tempfile.TemporaryDirectory(prefix='gc-motion-source24-',dir='/dev/shm') as t:
   p=Path(t)
   read=(ROOT/'src/game/read.cpp').read_text()
   def production_block(call):
    at=read.index(call);start=read.rfind('#if',0,at);finish=read.index('#endif',at)+len('#endif')
    return read[start:finish]
   fixture=FIXTURE.replace('NATIVE_FIXTURE',self.native_fixture())
   fixture=fixture.replace('LOADER_CAPTURE',production_block('re4dc_gcasset::motion_source_archive(m,pArc,len);'))
   fixture=fixture.replace('LOADER_RETIRE',production_block('re4dc_gcasset::motion_source_retire(m);'))
   (p/'fixture.cpp').write_text(fixture)
   # Compile gate independently so only the diagnostic observation sink differs.
   subprocess.run(['g++',*FLAGS,'-Dfingerprint=gate_fingerprint','-Dbind_checked=gate_bind_checked','-Demitted_checked=gate_emitted_checked','-Dunresolved=gate_unresolved','-c',str(PLATFORM/'gc_asset_gate.cpp'),'-o',str(p/'gate.o')],check=True,timeout=60,capture_output=True,text=True)
   source=(PLATFORM/'gc_asset_motion_source.cpp').read_text()
   if mutant:
    old,new=mutant;assert old in source;source=source.replace(old,new,1)
   source=source.replace('#include "include/gc_asset_motion_source.h"','#include "gc_asset_motion_source.h"')
   (p/'source.cpp').write_text(source)
   compile=subprocess.run(['g++',*FLAGS,str(p/'fixture.cpp'),str(p/'source.cpp'),str(PLATFORM/'gc_asset_motion_unknown.cpp'),str(p/'gate.o'),'-o',str(p/'run')],capture_output=True,text=True,timeout=60)
   self.assertEqual(compile.returncode,0,compile.stderr)
   run=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(p/'run')],capture_output=True,text=True,timeout=10)
   self.assertNotEqual(run.returncode,0,run.stdout) if reject else self.assertEqual(run.returncode,0,run.stderr)
 def native_fixture(self):
  import sys
  sys.path.insert(0,str(ROOT/'port/dreamcast/tools/d367/gc_port23'))
  from test_runtime_hooks import function
  source=(PLATFORM/'native_motion.cpp').read_text()
  cold=source.index('        re4dc_gcasset::motion_source_external_capture(&s,proxy,head,data,size);')
  start=source.rfind('#if RE4DC_GC_ASSET_MOTION_SOURCE',0,cold);finish=source.index('#endif',cold)+len('#endif')
  capture=source[start:finish]
  publish=function(source,'extern "C" void re4dc_motion_gcasset_publish(')
  idle=function(source,'extern "C" int re4dc_motion_gcasset_idle(')
  return r'''
#include "native_motion.h"
#include <cstdint>
extern bool motion_mutex;
constexpr unsigned kArchives=4;
struct Slot {unsigned char* data=nullptr;unsigned pins=0;std::uint64_t used=0;};
struct Binding {unsigned char* archive=nullptr;unsigned count=0;Slot* slots=nullptr;};
struct Owner {const void* thread=nullptr;unsigned leases=0;};
Binding bindings[4]{};Owner owners[32]{};int lock=0;Slot native_slot{};unsigned char* native_clip;const void* native_proxy;
unsigned native_record[5]{};
const unsigned char* record(const Binding&,unsigned){return reinterpret_cast<const unsigned char*>(native_record);}
unsigned word(const unsigned char* p){unsigned v;std::memcpy(&v,p,4);return v;}
int irq_disable(){return 0;}void irq_restore(int){}
int mutex_trylock(int*){if(motion_mutex)return -1;motion_mutex=true;return 0;}
void mutex_unlock(int*){assert(motion_mutex);motion_mutex=false;}
struct Locked {Locked(){assert(!motion_mutex);motion_mutex=true;}~Locked(){mutex_unlock(&lock);}};
void native_begin(unsigned char* proxy,unsigned char* data){native_proxy=proxy;native_clip=data;bindings[0]={proxy,1,&native_slot};native_record[0]=0;}
void* native_owner(){return &native_slot;}
void native_stop(){bindings[0]={};native_slot={};owners[0]={};}
extern "C" int re4dc_motion_acquire(const void* header,unsigned** table){
 assert(header==native_proxy);{Locked guard;auto& s=native_slot;const auto* proxy=static_cast<const unsigned char*>(header);const unsigned head=16,size=64;auto* data=native_clip;
 COLD_CAPTURE
 // The original source is captured above; mimic only the following pointer-table mutation.
 unsigned value=0xfedcba98U;std::memcpy(data+12,&value,4);s.data=data;++s.pins;owners[0]={header,1};static unsigned accepted_table;*table=&accepted_table;
 }return 1;
}
extern "C" void re4dc_motion_release(int token){assert(token==1 && native_slot.pins);--native_slot.pins;owners[0]={};}
'''.replace('COLD_CAPTURE',capture)+publish+idle
 def test_production_helper_with_real_hash_catalog_and_tokens(self):self.compile_run()
 def test_retirement_and_stale_mutations(self):
  for mutant in [('for(auto& s:state->sources)if(s.owner==owner)s={};',''),('if(found && checked_current(found->asset))','if(found)'),('if(external)continue;','if(external){}'),('if(s.bytes==bytes && s.role==unsigned(role))return true;','if(s.bytes==bytes && s.role==unsigned(role)){capture(base,bytes);return true;}'),('if((role==MotionFcv || role==MotionShape) && !original_fcv(base,bytes))','if(false && (role==MotionFcv || role==MotionShape) && !original_fcv(base,bytes))'),('if(state->frozen_context){if(!receipt_current(state->context,model,info))','if(false){if(!receipt_current(state->context,model,info))'),('const CheckedAsset asset=capture_digest(s.digest);','const CheckedAsset asset=capture(s.base,s.bytes);')]:
   with self.subTest(mutant=mutant[0]):self.compile_run(mutant,reject=True)
 def test_default_header_evaluates_no_arguments_and_object_empty(self):
  with tempfile.TemporaryDirectory(prefix='gc-motion-off24-',dir='/dev/shm') as t:
   p=Path(t)
   for flags in [[],['-DRE4DC_GC_ASSET_MOTION_SOURCE=0']]:
    subprocess.run(['g++','-std=c++17','-O2',*flags,'-c',str(PLATFORM/'gc_asset_motion_source.cpp'),'-o',str(p/'source.o')],check=True,timeout=60)
    symbols=subprocess.run(['nm',str(p/'source.o')],check=True,capture_output=True,text=True).stdout
    self.assertFalse(symbols.strip(),symbols)
 def test_exact_loader_capture_and_retire_order(self):
  s=(ROOT/'src/game/read.cpp').read_text()
  self.assertLess(s.index('motion_source_archive(m,pArc,len)'),s.index('if (!re4dc_motion_bind(pArc, len))'))
  self.assertLess(s.index('motion_source_retire(m)'),s.index('re4dc_motion_unbind(m->pArc)'))
  self.assertIn('motion_source_archive(&PlReadModule,data,info.size[0][0])',s)
  self.assertIn('motion_source_archive(&WepReadModule,data,info.size[0][0])',s)
  self.assertNotIn('motion_source_archive(&PlReadModule,data,total)',s)
  self.assertNotIn('motion_source_archive(&WepReadModule,data,total)',s)
 def test_loader_source_off_projection_is_exact(self):
  include='#if defined(RE4DC_GAME) && !defined(__PPC__)\n#include "gc_asset_motion_source.h"\n#endif\n'
  for name in ['read.cpp','motion.cpp','shape.cpp','cam_motion.cpp']:
   path='src/game/'+name
   source=(ROOT/path).read_text();self.assertTrue(source.startswith(include));source=source[len(include):]
   if name=='shape.cpp':
    for block in ['#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE\nextern "C" void re4dc_gcasset_shape_reset(const void* info,const void* dst);\nextern "C" void re4dc_gcasset_shape_source(const void* info,unsigned index,const void* delta,unsigned count);\n#endif\n\n','#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE\n    re4dc_gcasset_shape_reset(info,dst);\n#endif\n','#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE\n                    re4dc_gcasset_shape_source(info,w->idx[i],src,(unsigned)num);\n#endif\n']:
     self.assertEqual(source.count(block),1);source=source.replace(block,'')
   lines=source.splitlines(True);out=[];skip=0
   for line in lines:
    if not skip and line.lstrip().startswith('#if') and 'RE4DC_GC_ASSET_MOTION_SOURCE' in line:skip=1;continue
    if skip:
     if re.match(r'\s*#\s*(if|ifdef|ifndef)\b',line):skip+=1
     elif re.match(r'\s*#\s*endif\b',line):skip-=1
     continue
    out.append(line)
   baseline=subprocess.run(['git','show','140a699f8ead7b406e76581de7075191acf77a96:'+path],cwd=ROOT,check=True,capture_output=True,text=True).stdout
   self.assertEqual(''.join(out),baseline,path)
 def test_unknown_helper_source_off_host_object_identity(self):
  path='port/dreamcast/game/platform/gc_asset_motion_unknown.cpp'
  baseline=subprocess.run(['git','show','140a699f8ead7b406e76581de7075191acf77a96:'+path],cwd=ROOT,check=True,capture_output=True,text=True).stdout
  current=(ROOT/path).read_text()
  with tempfile.TemporaryDirectory(prefix='gc-motion-off-identity-',dir='/dev/shm') as t:
   p=Path(t);src=p/'gc_asset_motion_unknown.cpp';objects=[]
   for i,source in enumerate([baseline,current]):
    src.write_text(source)
    obj=p/('arm'+str(i)+'.o')
    subprocess.run(['g++','-std=c++17','-O2','-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1','-I'+str(PLATFORM),'-c',str(src),'-o',str(obj)],check=True,timeout=60)
    objects.append(obj.read_bytes())
   self.assertEqual(*objects)
 def test_native_source_off_projection_is_exact(self):
  for path in ['port/dreamcast/game/platform/native_motion.cpp','port/dreamcast/game/platform/include/native_motion.h']:
   source=(ROOT/path).read_text()
   include='#include "include/gc_asset_motion_source.h"\n' if path.endswith('.cpp') else '#include "gc_asset_motion_source.h"\n'
   self.assertEqual(source.count(include),1);source=source.replace(include,'')
   out=[];skip=0
   for line in source.splitlines(True):
    if not skip and line.lstrip().startswith('#if') and 'RE4DC_GC_ASSET_MOTION_SOURCE' in line:skip=1;continue
    if skip:
     if re.match(r'\s*#\s*(if|ifdef|ifndef)\b',line):skip+=1
     elif re.match(r'\s*#\s*endif\b',line):skip-=1
     continue
    out.append(line)
   baseline=subprocess.run(['git','show','140a699f8ead7b406e76581de7075191acf77a96:'+path],cwd=ROOT,check=True,capture_output=True,text=True).stdout
   projected=''.join(out).replace('            re4dc_motion_free(data);\n            fail("motion key offset"); }','            re4dc_motion_free(data);fail("motion key offset"); }')
   self.assertEqual(projected,baseline,path)
 def test_host_32bit_storage_layout_control(self):
  # Host IA32 layout check only. Minimal standard declarations avoid requiring
  # target SDK/multilib C++ headers; this is not SH4/KOS object qualification.
  with tempfile.TemporaryDirectory(prefix='gc-motion-layout32-',dir='/dev/shm') as t:
   p=Path(t)
   (p/'cstdint').write_text('namespace std { using uintptr_t=unsigned; }\n')
   (p/'cstring').write_text('namespace std { extern "C" void* memcpy(void*,const void*,unsigned); extern "C" int memcmp(const void*,const void*,unsigned); }\n')
   (p/'new').write_text('inline void* operator new(unsigned,void* p) noexcept { return p; }\n')
   (p/'type_traits').write_text('namespace std { template<class T> struct is_trivially_destructible { static constexpr bool value=__has_trivial_destructor(T); }; }\n')
   obj=p/'helper.o'
   run=subprocess.run(['g++',*FLAGS,'-m32','-nostdinc++','-fno-exceptions','-fno-rtti','-fno-pie','-I'+str(p),'-c',str(PLATFORM/'gc_asset_motion_source.cpp'),'-o',str(obj)],capture_output=True,text=True,timeout=60)
   self.assertEqual(run.returncode,0,run.stderr)
   dis=subprocess.run(['objdump','-d','-C',str(obj)],check=True,capture_output=True,text=True).stdout
   block=dis[dis.index('<re4dc_gcasset::motion_source_test_storage_bytes()>'):]
   self.assertRegex(block.split('\n\n')[0],r'\$0x2e98,%eax') #11928 bytes under IA32 ABI
   symbols=subprocess.run(['nm','-S','-C',str(obj)],check=True,capture_output=True,text=True).stdout
   state=[line for line in symbols.splitlines() if ' b ' in line or ' B ' in line]
   self.assertEqual(sum(int(line.split()[1],16) for line in state),8,state)
 def test_actual_malformed_external_key_preserves_backing_ownership(self):
  source=(PLATFORM/'native_motion.cpp').read_text()
  at=source.index('            if(offset<head || offset>=size) {')
  finish=source.index('fail("motion key offset"); }',at)+len('fail("motion key offset"); }')
  actual=source[at:finish]
  fixture=r'''#include <cassert>
struct Binding {bool bounded;};bool reserved;unsigned freed,invalidated;bool stopped;
bool reserved_data(const Binding&,void*){return reserved;}
void re4dc_motion_free(void*){++freed;}
void fail(const char*){stopped=true;}
namespace re4dc_gcasset {void motion_source_external_invalidate(const void*){++invalidated;}}
void invalid(Binding& b,void* data,unsigned offset,unsigned head,unsigned size){int s=0;
BODY
(void)b;(void)data;(void)s;
}
int main(){int data=0;for(bool held:{false,true}){Binding b{held};reserved=held;freed=invalidated=0;stopped=false;
 invalid(b,&data,4,16,64);assert(stopped);
#if RE4DC_MOTION_RESERVE_PACK || RE4DC_MOTION_BOUNDED_R11F
 assert(freed==unsigned(!held));
#else
 assert(freed==1);
#endif
 assert(invalidated==RE4DC_GC_ASSET_MOTION_SOURCE);
 }
}
'''.replace('BODY',actual).replace('for(bool held:{false,true})','for(unsigned value=0;value<2;++value)').replace('Binding b{held};','const bool held=value!=0;Binding b{held};')
  with tempfile.TemporaryDirectory(prefix='gc-motion-bad-key-',dir='/dev/shm') as t:
   p=Path(t);(p/'fixture.cpp').write_text(fixture)
   for enabled in [0,1]:
    for pack,bounded in [(0,0),(1,0),(0,1)]:
     run=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_MOTION_SOURCE='+str(enabled),'-DRE4DC_MOTION_RESERVE_PACK='+str(pack),'-DRE4DC_MOTION_BOUNDED_R11F='+str(bounded),str(p/'fixture.cpp'),'-o',str(p/'run')],capture_output=True,text=True,timeout=60)
     self.assertEqual(run.returncode,0,run.stderr)
     result=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(p/'run')],capture_output=True,text=True,timeout=10)
     self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()

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
namespace re4dc_gcasset {Digest gate_fingerprint(const void*,unsigned);CheckedAsset gate_bind_checked(const char*,const char*,const Digest&);}
bool protected_context=false;unsigned hashes=0,accepts=0,faults=0;CheckedAsset accepted[128]{};
extern "C" void re4dc_log(const char*,...){assert(!protected_context);}
namespace re4dc_gcasset {
Digest fingerprint(const void* p,unsigned n){assert(!protected_context);++hashes;return gate_fingerprint(p,n);}
CheckedAsset bind_checked(const char* k,const char* id,const Digest& d){assert(!protected_context);return gate_bind_checked(k,id,d);}
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
 unsigned owner=0,model=0,camera=0,shape=0;unsigned char fcv[64]{1,2,3},evd[96]{4,5},bind[80]{9,10};
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
 protected_context=true;
 motion_source_note(&model,fcv,MotionFcv);motion_source_note(&model,evd+8,MotionFcv);
 motion_source_note(&shape,bind,MotionBind);motion_source_note(&camera,fcv,MotionFcv);
 motion_source_view(&camera);
 const auto receipt=motion_source_snapshot(&model,&shape);assert(receipt.count==3 && !receipt.fault);
 motion_source_accept(receipt,0);protected_context=false;motion_source_flush();assert(!accepts && !faults);
 // Actual accepted record latches; all hashing/catalog/logging waits for flush.
 {MotionUnknownScope unknown(motion_model_reason());MotionSourceScope scope(receipt);motion_prepare();protected_context=true;motion_accept_pending(7);protected_context=false;}
 assert(!accepts);motion_unknown_flush();assert(accepts==3 && faults==1);faults=0;
 AssetDescription description{};assert(describe_checked(accepted[0],&description));assert(!std::memcmp(description.digest.bytes,original.bytes,32));assert(description.provenance==PS2);
 assert(describe_checked(accepted[1],&description));assert(description.provenance==GameCube);
 // Deferred snapshot cannot follow a new generation at the same address.
 motion_source_retire(&owner);const unsigned before=accepts;
 assert(motion_source_adopt(&owner,fcv,sizeof fcv,MotionFcv));
 protected_context=true;motion_source_accept(receipt,1);protected_context=false;motion_source_flush();assert(accepts==before && faults==1);
 motion_source_reset(&model);auto stale=motion_source_snapshot(&model);assert(stale.fault);
 // Evaluation without any accepted records is never emission.
 const unsigned evaluated=accepts;motion_source_note(&model,fcv,MotionFcv);motion_source_flush();assert(accepts==evaluated);
 // Unbound pointers, malformed roles and stale catalog tokens fail closed.
 protected_context=true;motion_source_note(&shape,reinterpret_cast<void*>(1),MotionFcv);motion_source_accept(motion_source_snapshot(&shape),1);protected_context=false;motion_source_flush();assert(faults>=2);
 retire_catalog();protected_context=true;motion_source_accept(motion_source_snapshot(&model),1);protected_context=false;motion_source_flush();assert(accepts==evaluated);
 motion_source_retire(&owner);motion_source_reset(&model);motion_source_reset(&camera);motion_source_reset(&shape);
 // Complete original archive FCV capture, never only an MTC shell prefix.
 unsigned char arc[160]{};word(arc,2);word(arc+16,32);word(arc+20,96);std::memcpy(arc+24,"FCV",3);std::memcpy(arc+28,"BIN",3);
 end(1);assert(install(rows,3));begin(0x100,2,0x1f6);
 const unsigned prior_hashes=hashes;actual_read_archive(&owner,arc,sizeof arc);assert(hashes==prior_hashes+2);assert(accepts==evaluated);
 motion_source_reset(&model);motion_source_note(&model,arc+32,MotionFcv);
 const auto archive_receipt=motion_source_snapshot(&model);const unsigned original_archive_hashes=hashes;
 std::memset(arc+32,0xcc,64);actual_read_archive(&owner,arc,sizeof arc);assert(hashes==original_archive_hashes);
 protected_context=true;motion_source_accept(archive_receipt,1);protected_context=false;motion_source_flush();assert(accepts==evaluated+1);
 assert(describe_checked(accepted[accepts-1],&description));assert(description.provenance==Unknown);
 actual_retire_archive(&owner);const unsigned original_accepts=accepts;
 protected_context=true;motion_source_accept(archive_receipt,1);protected_context=false;motion_source_flush();assert(accepts==original_accepts);
 motion_source_retire(&owner);std::memcpy(arc+28,"MTC",3);const unsigned prefix_hashes=hashes;assert(!motion_source_archive(&owner,arc,sizeof arc));assert(hashes==prefix_hashes);
 word(arc+20,32);std::memcpy(arc+28,"FCV",3);assert(!motion_source_archive(&owner,arc,sizeof arc));
 // Invalid directory sizes/ranges and serial exhaustion do not read a span.
 word(arc,4097);assert(!motion_source_archive(&owner,arc,sizeof arc));
 assert(!motion_source_adopt(&owner,reinterpret_cast<void*>(~std::uintptr_t(0)-3),8,MotionFcv));
 motion_source_test_serial(0xfffffffeU);assert(!motion_source_adopt(&owner,arc,sizeof arc,MotionEvd));
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
   fixture=FIXTURE.replace('LOADER_CAPTURE',production_block('re4dc_gcasset::motion_source_archive(m,pArc,len);'))
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
 def test_production_helper_with_real_hash_catalog_and_tokens(self):self.compile_run()
 def test_retirement_and_stale_mutations(self):
  for mutant in [('for(auto& s:sources)if(s.owner==owner)s={};',''),('if(found && checked_current(found->asset))','if(found)'),('if(external){good=false;continue;}',''),('if(s.bytes==bytes && s.role==unsigned(role))return true;','if(s.bytes==bytes && s.role==unsigned(role)){capture(base,bytes);return true;}')]:
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
if __name__=='__main__':unittest.main()

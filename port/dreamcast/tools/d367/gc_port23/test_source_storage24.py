#!/usr/bin/env python3
"""Host controls for the actual diagnostic profile, not target qualification."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
PLATFORM=ROOT/'port/dreamcast/game/platform'
def function(text,signature):
    start=text.index(signature);i=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
class SourceStorage(unittest.TestCase):
    def test_actual_make_profile(self):
        mk=ROOT/'port/dreamcast/game/gc_asset_gate.mk'
        source=f"OBJDIR := fixture\nPLATFORM_OBJS := fixture/platform/a.o fixture/platform/gc_asset_motion_source.o\ninclude {mk}\nall:\n\t@printf '%s\\n' 'FLAGS=$(PLATFORM_CPPFLAGS)' 'GAME=$(GAME_CPPFLAGS)' 'OBJECTS=$(PLATFORM_OBJS)'\n"
        def run(*variables):
            return subprocess.run(['/usr/bin/make','--no-print-directory','-f','-',*variables],input=source,text=True,capture_output=True,timeout=10)
        off=run();self.assertEqual(off.returncode,0,off.stderr)
        self.assertNotIn('gc_asset_motion_source.o',off.stdout);self.assertNotIn('-D',off.stdout)
        good=['GC_ASSET_GATE=1','PVR_STREAM=1','AICA_AUDIO=1','GC_ASSET_MOTION_UNKNOWN=1','NATIVE_ACTOR=1','NATIVE_ACTOR_FAST=1','GC_ASSET_MOTION_SOURCE=1','GC_ASSET_SOURCE_PROOFS=1','MODEL_DRAW_PLANS=1','D349_RENDERER_STACK=1']
        on=run(*good);self.assertEqual(on.returncode,0,on.stderr)
        self.assertIn('-DRE4DC_GC_ASSET_SOURCE_PROOFS=1',on.stdout)
        self.assertIn('fixture/platform/gc_asset_motion_source.o',on.stdout)
        for bad in ['GC_ASSET_MOTION_SOURCE=2','GC_ASSET_SOURCE_PROOFS=2','GC_ASSET_MOTION_SOURCE=0 1','GC_ASSET_SOURCE_PROOFS=','MODEL_DRAW_PLANS=0','D349_RENDERER_STACK=0','GC_ASSET_MOTION_UNKNOWN=0','GC_ASSET_GATE=0']:
            with self.subTest(bad=bad):self.assertNotEqual(run(*good,bad).returncode,0)
    def test_actual_cold_binding_and_cache_isolation(self):
        ui=(PLATFORM/'native_ui.cpp').read_text();startup=function(ui,'void gcasset_startup()')
        start=startup.index('    bool source_storage=false;');end=startup.index('\n#endif',start);binding=startup[start:end]
        cache=function(ui,'extern "C" void* re4dc_model_metadata_storage(')
        self.assertLess(startup.index(binding),startup.index('ensure_disc_catalog()'))
        self.assertLess(startup.index(binding),startup.index('re4dc_gcasset_actor_startup()'))
        code=r"""
#include <cassert>
#include <cstddef>
alignas(32) unsigned char slab[65536];
unsigned char* model_packets=slab;
constexpr unsigned kModelMetadataBytes=32768,kModelPacketBytes=12288,kModelPreparationBytes=12288,kModelStaticLightBytes=0,kModelDeferredSpillBytes=8192;
constexpr unsigned kGcGeometryBytes=12288,kGcMotionBytes=12288;
bool ensure=true,geometry_ok=true,motion_ok=true;unsigned expected_bytes=12288,calls=0;
bool ensure_model_storage(){return ensure;}
namespace re4dc_gcasset {
unsigned member_original_storage_bytes(){return expected_bytes;}
bool member_original_storage(void* p,unsigned n){++calls;assert(p==slab+32768 && n==12288);return geometry_ok;}
bool motion_source_storage_bind(void* p,unsigned n){++calls;assert(p==slab+45056 && n==12288);return motion_ok;}
}
bool bind_actual(){
"""+binding+r"""
 return source_storage;
}
"""+cache+r"""
int main(){
 assert(bind_actual() && calls==2);unsigned bytes=999;
 assert(re4dc_model_metadata_storage(&bytes)==nullptr && bytes==0);
 ensure=false;calls=0;assert(!bind_actual() && calls==0);
 ensure=true;expected_bytes=12289;assert(!bind_actual() && calls==0);
 expected_bytes=12288;geometry_ok=false;assert(!bind_actual() && calls==1);
 geometry_ok=true;motion_ok=false;calls=0;assert(!bind_actual() && calls==2);
}
"""
        with tempfile.TemporaryDirectory(prefix='gc-source-storage24-') as tmp:
            d=Path(tmp);p=d/'actual.cpp';p.write_text(code)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_SOURCE_PROOFS=1',str(p),'-o',str(d/'actual')],check=True,timeout=30)
            subprocess.run([str(d/'actual')],check=True,timeout=10)
    def test_off_cache_function_tokens_unchanged(self):
        rel='port/dreamcast/game/platform/native_ui.cpp'
        old=subprocess.check_output(['git','show','140a699f:'+rel],cwd=ROOT,text=True);current=(ROOT/rel).read_text()
        def project(text):
            f=function(text,'extern "C" void* re4dc_model_metadata_storage(')
            p=subprocess.run(['g++','-E','-P','-x','c++','-DRE4DC_GC_ASSET_SOURCE_PROOFS=0','-'],input=f,text=True,capture_output=True,check=True,timeout=10)
            return p.stdout.split()
        self.assertEqual(project(old),project(current))
if __name__=='__main__':unittest.main()

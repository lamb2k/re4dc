#!/usr/bin/env python3
"""Actual-source rect21 material admission controls; RAM host checks only."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
TREE=HERE.parents[4]
GAME=TREE/'port/dreamcast/game'
sys.path.insert(0,str(HERE.parent/'pvs23'))
from host_checks import compile_run
from check_queued_affine import function

def assigned(text,name):
    body=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='main').body
    return next(ast.literal_eval(n.value) for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))

def real_kos(kos,ui):
    files={n:(kos/p).read_text() for n,p in {
      'pvr.h':'kernel/arch/dreamcast/include/dc/pvr.h',
      'pvr_header.h':'kernel/arch/dreamcast/include/dc/pvr/pvr_header.h',
      'pvr_legacy.h':'kernel/arch/dreamcast/include/dc/pvr/pvr_legacy.h',
      'regfield.h':'include/kos/regfield.h',
      'pvr_prim.c':'kernel/arch/dreamcast/hardware/pvr/pvr_prim.c'}.items()}
    ph,hh,legacy,reg,prim=(files[n] for n in ('pvr.h','pvr_header.h','pvr_legacy.h','regfield.h','pvr_prim.c'))
    enums='\n'.join(re.findall(r'typedef enum\s+\w+\s*\{.*?\}\s*\w+;',hh+'\n'+ph,re.S))
    macros='\n'.join(line.split('/**')[0] for s in (ph,legacy) for line in s.splitlines() if re.match(r'#define PVR_',line))
    reg=reg.replace('#include <kos/cdefs.h>','').replace('__BEGIN_DECLS','').replace('__END_DECLS','')
    cxt=ph[ph.index('typedef struct {\n    pvr_list_t'):ph.index('} pvr_poly_cxt_t;')+len('} pvr_poly_cxt_t;')]
    hdr=hh[hh.index('typedef struct pvr_poly_hdr_cmd'):hh.index('_Static_assert(sizeof(pvr_poly_hdr_t)')]
    code='''#include <cassert>\n#include <cstdint>\n#include <cstring>\n#include <cstdio>\nusing pvr_ptr_t=uint32_t;using pvr_txr_ptr_t=uint32_t;
#define assert_msg(c,m) assert(c)
#define dcache_alloc_line_with_value(dst,v) ((dst)->cmd=(v))
'''+reg+'\n'+enums+'\n'+macros+'\n'+cxt+'\n'+hdr+'''
static pvr_txr_ptr_t to_pvr_txr_ptr(pvr_ptr_t addr){return (addr&0x7fffffU)>>3;}
'''+function(prim,'void pvr_poly_compile(').replace('void pvr_poly_compile(', 'void __real_pvr_poly_compile(')+'\n'+function(prim,'void pvr_poly_cxt_txr(')+'''
#define RE4DC_HDR_PROBE(d,k) ((void)0)
'''+function(ui,'extern "C" void __wrap_pvr_poly_compile(')+'''
pvr_poly_hdr_t observed;
void pvr_poly_compile(pvr_poly_hdr_t* h,const pvr_poly_cxt_t* c){
#if RE4DC_TEX_MIP_DADJ
 __wrap_pvr_poly_compile(h,c);
#else
 __real_pvr_poly_compile(h,c);
#endif
 observed=*h;
}
'''
    return code,{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}

def preprocess_ui(ui,base):
    def pp(text,knobs):
        text=re.sub(r'^\s*#\s*include[^\n]*','',text,flags=re.M)
        names=sorted(set(re.findall(r'\bRE4DC_[A-Z0-9_]+\b',text)))
        definitions=''.join(f'#define {n} {knobs.get(n,0)}\n' for n in names)
        process=subprocess.run(['g++','-E','-P','-x','c++','-'],input=definitions+text,text=True,capture_output=True)
        if process.returncode:raise AssertionError('\n'.join(l for l in process.stderr.splitlines() if 'error:' in l))
        return process.stdout
    result=[]
    for rect in (0,1):
      for cache in (0,1):
       for shadows in (0,1):
        knobs=dict(RE4DC_PS2_PVS=0,RE4DC_D349_RENDERER_STACK=1,RE4DC_PVR_STREAM=1,RE4DC_TA_DIRECT=1,RE4DC_TA_HEADROOM=1,RE4DC_PS2_WORLD_DRAW=1,RE4DC_PS2_WORLD_MESH=1,RE4DC_MESH_DIRECT=1,
                   RE4DC_WORLD_RECT21=rect,RE4DC_PS2_WORLD_HDR_CACHE=cache,RE4DC_MV_SHADOWS=shadows)
        before,after=pp(base,knobs),pp(ui,knobs)
        assert before==after,'PVS0 source differs'
        result.append(dict(world_rect21=rect,header_cache=cache,mv_shadows=shadows,sha256=hashlib.sha256(after.encode()).hexdigest()))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kos',type=Path,default=Path('/root/work/kos-re4dc-d367'))
    ap.add_argument('--base',default='4835ff70e')
    ap.add_argument('--evidence',type=Path)
    args=ap.parse_args()
    ui_path=GAME/'platform/native_ui.cpp';ui=ui_path.read_text()
    body=function(ui,'extern "C" int re4dc_pvs23_opaque_ready(')
    legacy=(HERE.parent/'pvs23/opaque_checks.py').read_text()
    stub=assigned(legacy,'prefix');tests=assigned(legacy,'tests');flags=assigned(legacy,'flags')
    real,hashes=real_kos(args.kos,ui)
    # Existing state controls use actual KOS context/compile bodies and enums.
    stub=stub[stub.index('struct Key '):]
    first=stub.index('struct pvr_poly_cxt_t {');last=stub.index('#define RE4DC_TSP_W(t)',first)
    stub=stub[:first]+stub[last:]
    stub=stub.replace('unsigned width=64,height=64,format=0,flags=0;','unsigned width=64,height=64,format=0,flags=0,payload=0,data_size=0;')
    th=(GAME.parent/'room/texture_package.hpp').read_text()
    constants='\n'.join(re.findall(r'inline constexpr std::uint32_t\s+\w+\s*=.*?;',th))
    stub=stub.replace('@TEXTURE_CONSTANTS@',constants)
    tex=(GAME.parent/'room/texture_package.cpp').read_text()
    stub=stub.replace('unsigned pvr_format(const Texture& t){return t.format;}',function(tex,'std::uint32_t pvr_format('))
    stub=stub.replace('unsigned texture_count=1;','unsigned texture_count=1,payload_crc32=0;')
    stub=stub.replace('pvr_ptr_t address=reinterpret_cast<void*>(32);','pvr_ptr_t address=0xa4000020U;')
    stub=stub.replace('void* texture=nullptr;','pvr_ptr_t texture=0;')
    tests=tests.replace('int main(){','void baseline(){').replace('package.address=nullptr','package.address=0')
    tests=tests.replace('slot.words[1]^=16','slot.words[1]^=PVR_TA_PM1_DEPTHWRITE')
    rect=HERE.parent/'texture_rect21'
    extra=r'''
void adapted(){
 reset();key[0]=0x33ea067e;key[1]=0x3e26baf5;key[2]=512;key[3]=256;
 entries[0].key={key[0],key[1]};auto& t=entries[0].package.t;
 t={256,256,0,4,2,23894};entries[0].package.h.payload_crc32=0xd165446f;
}
int main(){
 baseline();adapted();
#if RE4DC_WORLD_RECT21
 assert(ready());
 Entry before=entries[0];assert(ready());assert(!std::memcmp(&before,&entries[0],sizeof(before)));
 for(unsigned field=0;field<7;++field){
  adapted();auto& p=entries[0].package;
  unsigned* fields[]={&p.t.width,&p.t.height,&p.t.format,&p.t.flags,&p.t.payload,&p.t.data_size,&p.h.payload_crc32};
  *fields[field]^=1;assert(!ready());
 }
 for(unsigned field=0;field<4;++field){adapted();key[field]^=1;entries[0].key={key[0],key[1]};assert(!ready());}
 for(unsigned flag:{re4dc::texture::kAlpha,re4dc::texture::kBinaryAlpha,re4dc::texture::kTopDrop}){
  adapted();entries[0].package.t.flags|=flag;assert(!ready());
 }
 adapted();entries[0].frame=9;assert(!ready());
 adapted();entries[0].package.uploaded=false;assert(!ready());
 adapted();source_binding=false;assert(!ready());
 adapted();r11f_binding=false;assert(!ready());
 adapted();re4dc_ps2_check_header=1;assert(!ready());
 adapted();re4dc_ps2_sky_header=1;assert(!ready());
#if RE4DC_PS2_WORLD_HDR_CACHE
 adapted();assert(ready());
 unsigned set=(key[0]^(key[1]>>7)^(key[1]<<3)^(2U*0x3c1U))&(kPs2HdrSets-1U);
 auto& slot=ps2_hdr[set][0];slot.mode=(2U<<2)|(1U<<4)|0x100U;
 slot.crc=key[0];slot.fnv=key[1];slot.size=512U|(256U<<16);slot.entry=&entries[0];slot.texture=entries[0].package.address;
 std::memcpy(slot.words,&observed,16);auto before_slot=slot;assert(ready());assert(!std::memcmp(&before_slot,&slot,sizeof(slot)));
 for(unsigned word=0;word<4;++word){slot.words[word]^=0x100;assert(!ready());slot.words[word]^=0x100;}
#endif
#else
 assert(!ready());
#endif
 puts("PASS actual-source material eligibility with actual KOS context/compiler");
}
'''
    source=real+'\n#include <initializer_list>\n#include "world_rect_bind.h"\n'+stub+'\n'+body+'\n'+tests+extra
    base=subprocess.check_output(['git','show',args.base+':port/dreamcast/game/platform/native_ui.cpp'],cwd=TREE,text=True)
    result=dict(host_only=True,base=args.base,native_ui_sha256=hashlib.sha256(ui.encode()).hexdigest(),
                real_kos=hashes,inputs={str(p.relative_to(TREE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ui_path,GAME.parent/'room/texture_package.hpp',GAME.parent/'room/texture_package.cpp',rect/'world_rect_bind.h',rect/'scoped_representations.inc')},tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(source.encode()).hexdigest(),runs=[])
    with tempfile.TemporaryDirectory(prefix='iv23-material-',dir='/dev/shm') as td:
      work=Path(td)
      result['pvs0_source_preprocess']=preprocess_ui(ui,base)
      for rect_on in (0,1):
       for cache in (0,1):
        for shadows in (0,1):
         compile_run(work,f'material-{rect_on}-{cache}-{shadows}',source,(*flags,
          '-I'+str(rect),'-DRE4DC_CAST_MIPMAP=1','-DRE4DC_TEX_MIP_DADJ=3',
          '-DRE4DC_WORLD_RECT21='+str(rect_on),'-DRE4DC_PS2_WORLD_HDR_CACHE='+str(cache),'-DRE4DC_MV_SHADOWS='+str(shadows)))
         result['runs'].append(dict(world_rect21=rect_on,header_cache=cache,mv_shadows=shadows))
    if args.evidence:
      args.evidence.mkdir(parents=True,exist_ok=True)
      (args.evidence/'material-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

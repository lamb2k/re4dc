#!/usr/bin/env python3
"""EF11 single: full recovered OFF preprocessing and scoped host objects; no SDK."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('single',HERE/'test_cloth_single_material11.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
ROOT,DC,INC=S.ROOT,S.M.ROOT,S.M.INC
BASE=S.BASE
FILES=['src/game/cloth.cpp','src/game/esp.cpp','src/game/esp4e.cpp','port/dreamcast/game/platform/native_effect.cpp']
DEFS=['RE4DC_GAME=1','RE4DC_CLOTH_NATIVE=1','RE4DC_CLOTH_SHEET11=1','RE4DC_CLOTH_TILES11=1','RE4DC_NATIVE_DRAW_OUTCOMES=1','RE4DC_FX_STRIP21=1','RE4DC_PLAN_OWNER_SCOPED=1','RE4DC_PS2_UPLOAD_INCARNATION=1','RE4DC_UI_HANDLES=1','RE4DC_TA_DIRECT=1','RE4DC_EFFECT_SPRITE_MAX=256','RE4DC_CLOTH_LIGHT_ABI_FIX=1','RE4DC_ESP_POOL_RECYCLE=1']

def old(path):return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
def digest(b):return hashlib.sha256(b).hexdigest()
def run(cmd,code,out,label):
 r=subprocess.run(cmd,input=code,text=True,capture_output=True)
 (out/(label+'.log')).write_text(r.stderr)
 record=out/'commands.json';commands=json.loads(record.read_text()) if record.exists() else []
 commands.append(dict(command=cmd,input_sha256=digest(code.encode()),returncode=r.returncode))
 record.write_text(json.dumps(commands,indent=2)+'\n')
 assert not r.returncode,r.stderr
 return r.stdout

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 stub,generated=S.fixture();prefix=generated[:generated.index('struct Esp4eWork')]
 # Host boundary declarations/layout only. Actual source bodies are untouched.
 header=(ROOT/'include/cloth.h').read_text();prefix+='\n'+S.function(header,'extern "C" {')+'\n'
 (out/'dc/pvr').mkdir(parents=True);(out/'kos').mkdir()
 (out/'dc/pvr.h').write_text(stub)
 (out/'dc/sq.h').write_text('#pragma once\n#include <cstdint>\nstd::uint32_t* sq_lock(void*);void sq_wait();void sq_unlock();\n')
 (out/'dc/pvr/pvr_mem.h').write_text('#include <cstddef>\nvoid* pvr_mem_malloc(std::size_t);void pvr_mem_free(void*);\n')
 (out/'dc/pvr/pvr_txr.h').write_text('#include <cstddef>\n#define PVR_TXRLOAD_16BPP 0\nvoid pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned);void pvr_txr_load(const void*,void*,std::size_t);\n')
 (out/'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\n#include <cstddef>\n#include <fcntl.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\nint fs_open(const char*,int);ssize_t fs_read(int,void*,size_t);ssize_t fs_total(int);int fs_close(int);void* fs_mmap(int);off_t fs_seek(int,off_t,int);\n')
 (out/'kos.h').write_text('#include <kos/fs.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n')
 (out/'kos/net.h').write_text('extern "C" unsigned net_crc32le(const unsigned char*,unsigned);\n')
 flags=['g++','-std=c++20','-O2','-g0','-fpermissive','-fno-pie',*['-D'+x for x in DEFS],'-I'+str(out),'-I'+str(INC),'-I'+str(DC/'room')]
 full=[*flags,'-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),'-I'+str(DC/'game/platform'),'-include',str(INC/'re4dc_prelude.h')]
 rows=[]
 for file in FILES:
  texts=[old(file),(ROOT/file).read_text(),(ROOT/file).read_text()];pps=[]
  for arm,text,extra in zip(('base','absent','zero'),texts,([],[],['-DRE4DC_CLOTH_MATERIAL11=0'])):
   pp=run(full+extra+['-E','-P','-x','c++','-'],text,out,Path(file).stem+'-'+arm+'-full-pp')
   (out/(Path(file).stem+'-'+arm+'.pp')).write_text(pp);pps.append(pp)
  assert pps[0]==pps[1]==pps[2],file
  rows.append(dict(scope='full_actual_preprocessing',source=file,bytes=len(pps[0]),sha256=digest(pps[0].encode())))
 refused=subprocess.run(full+['-DRE4DC_CLOTH_MATERIAL11=1','-URE4DC_CLOTH_LIGHT_ABI_FIX','-DRE4DC_CLOTH_LIGHT_ABI_FIX=0','-E','-P','-x','c++','-'],input=(ROOT/'src/game/cloth.cpp').read_text(),text=True,capture_output=True)
 (out/'actual-cloth-FIX0-refusal.log').write_text(refused.stderr)
 assert refused.returncode and 'CLOTH_MATERIAL11 requires CLOTH_LIGHT_ABI_FIX=1' in refused.stderr
 rows.append(dict(actual_cloth_FIX0_refused=True))
 # This independent full-TU comparison must see an unrelated producer change,
 # not substitute the current body wholesale to make source drift disappear.
 current=(ROOT/'src/game/esp4e.cpp').read_text();changed=current.replace('    return 1;\n}', '    return 2;\n}',1);assert changed!=current
 perturbed=run(full+['-E','-P','-x','c++','-'],changed,out,'outside-helper-negative-pp')
 assert perturbed!=(out/'esp4e-absent.pp').read_text()
 rows.append(dict(outside_helper_change_detected=True))
 for scope,file in [('esp4e_full_includes_elided','src/game/esp4e.cpp'),('esp_actual_allocation_functions','src/game/esp.cpp'),('native_effect_full','port/dreamcast/game/platform/native_effect.cpp')]:
  objects=[]
  for arm,text,extra in [('base',old(file),[]),('absent',(ROOT/file).read_text(),[]),('zero',(ROOT/file).read_text(),['-DRE4DC_CLOTH_MATERIAL11=0']),('on',(ROOT/file).read_text(),['-DRE4DC_CLOTH_MATERIAL11=1'])]:
   if scope.startswith('esp4e'):
    code=prefix+'\n'+'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))
   elif scope.startswith('esp_actual'):
    start=text.find('#if defined(RE4DC_CLOTH_MATERIAL11)')
    macros=text[start:text.index('#line 1',start)] if start>=0 else ''
    funcs=[]
    for sig in ('void* cEsp::operator new(', 'int PullEsp(', 'void PushEsp(', 'int EspArrayAlloc(', 'int EspArrayFree(', 'int EspArrayPush(', 'int EspArrayPop('):
     funcs.append(S.function(text[text.rfind(sig):],sig).replace('unsigned int size','std::size_t size',1))
    code=prefix+'\n'+macros+'\n'+'\n'.join(funcs)
   else:code=text
   obj=out/(scope+'-'+arm+'.o');run(flags+extra+['-c','-x','c++','-','-o',str(obj)],code,out,scope+'-'+arm+'-object');objects.append(obj.read_bytes())
  assert objects[0]==objects[1]==objects[2],scope
  assert objects[3]!=objects[0],scope
  rows.append(dict(scope=scope,absent_zero_baseline_objects_equal=True,on_differs=True,bytes=len(objects[0]),sha256=digest(objects[0])))
 result=dict(status='PASS_SCOPED_OFF_IDENTITY',base=BASE,rows=rows,limits=['includes-elided Esp4e object uses host source model; allocator signatures adapted to host size_t','complete recovered source preprocessing retains real project headers','not full SH4 objects/ELF/program identity; no SDK'])
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()

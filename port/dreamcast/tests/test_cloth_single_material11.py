#!/usr/bin/env python3
"""Real Esp4e -> Cloth -> prepared native bands, synthetic archives/devices."""
from pathlib import Path
import argparse, contextlib, hashlib, importlib.util, json, os, subprocess, traceback
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('material',HERE/'test_cloth_material11.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
spec=importlib.util.spec_from_file_location('publication',HERE/'test_cloth_publication11.py')
PUB=importlib.util.module_from_spec(spec);spec.loader.exec_module(PUB)
ROOT=M.REPO
BASE='36b0ab8c737d0e3452fea44af1d5390b4b9f55ee'

def function(text,signature):return M.OWNER.function(text,signature)
def replace_function(text,signature,replacement):
 old=function(text,signature);assert old in text;return text.replace(old,replacement,1)

def fixture(slot_hook_revision=None,oom_source_revision=None):
 raw=bytes([255])*128
 image=M.TPL.TplImage(8,8,M.TPL.GX_TF_RGB565,raw)
 package=M.TPL.build_package([image],[M.TPL.MaterialBinding('cloth-white',0,None)],twiddle=True)[0]
 stub,code=M.producer_fixture((package,package),(raw,raw));code=code[:code.rindex('int main(){')]
 code=code.replace('extern "C" void re4dc_log(const char*,...){}','extern "C" void re4dc_log(const char*,...);')
 code=code.replace('extern "C" int re4dc_cloth_esp4e_words11(const Cloth*,unsigned*){return 0;}','')
 cloth=(ROOT/'src/game/cloth.cpp').read_text();esp=(ROOT/'src/game/esp.cpp').read_text();producer=(ROOT/'src/game/esp4e.cpp').read_text()
 if slot_hook_revision:esp=subprocess.check_output(['git','show',slot_hook_revision+':src/game/esp.cpp'],cwd=ROOT,text=True)
 header=(ROOT/'include/cloth.h').read_text();definition=function(header,'class Cloth')+';'
 start=code.index('struct Cloth{');end=code.index('};',start)+2
 code=code[:start]+'''using u8=unsigned char;using u16=unsigned short;using s8=signed char;using s32=int;
using GXColor=Color;struct GXTlutObj{unsigned w[3];};
'''+definition+code[end:]
 code=code.replace('struct LightManager{Env e;Env* getEnvPtr(){return &e;}} LightMgr;',
                   'struct cModel;struct LightManager{Env e;Env* getEnvPtr(){return &e;}void setClothN(cModel*,int);} LightMgr;')
 code=code.replace('struct Global{struct{Mtx v_mat;}Cam;unsigned Frame_cnt;}',
                   'struct Global{struct{Mtx v_mat;}Cam;unsigned Frame_cnt,room_id=0x101;}')
 code=replace_function(code,'void PSMTXScale(','''void PSMTXScale(Mtx m,float x,float y,float z){std::memset(m,0,sizeof(Mtx));m[0][0]=x;m[1][1]=y;m[2][2]=z;}''')
 code=replace_function(code,'void PSMTXConcat(','''void PSMTXConcat(const Mtx a,const Mtx b,Mtx out){Mtx t{};
 for(unsigned r=0;r<3;++r){for(unsigned c=0;c<3;++c)for(unsigned k=0;k<3;++k)t[r][c]+=a[r][k]*b[k][c];
 t[r][3]=a[r][3];for(unsigned k=0;k<3;++k)t[r][3]+=a[r][k]*b[k][3];}std::memcpy(out,t,sizeof t);}''')
 code=replace_function(code,'void PSMTXMultVec(','''void PSMTXMultVec(const Mtx m,const Vec* p,Vec* out){assert(!retired);++transforms;Vec t{};
 t.x=m[0][0]*p->x+m[0][1]*p->y+m[0][2]*p->z+m[0][3];
 t.y=m[1][0]*p->x+m[1][1]*p->y+m[1][2]*p->z+m[1][3];
 t.z=m[2][0]*p->x+m[2][1]*p->y+m[2][2]*p->z+m[2][3];*out=t;}''')
 prelude=(HERE/'cloth_single_material11_fixture.cpp.in').read_text(encoding='utf-8-sig')
 before,after=prelude.split('@ACTUAL_SOURCE@')
 code+='\n'+before+'\n'
 macro_start=esp.index('#if defined(RE4DC_CLOTH_MATERIAL11)')
 code+=esp[macro_start:esp.index('#line 1',macro_start)]+'\n'
 # Actual source bodies, with only host operator-new parameter type adapted.
 code+=function(producer,'struct Esp4eWork')+';\n'+function(producer,'class cEsp4e')+';\n'
 names=[('void ClothInit(',cloth),('void Cloth::Set(',cloth),('void Cloth::SetPosAng(',cloth),
        ('void Cloth::Destroy(',cloth),('void ClothCalcTplAddr(',cloth),('int ClothTexSetUp(',cloth),
        ('void Cloth::calcSpeed(',cloth),('void Cloth::move(',cloth),('void Cloth::calcNormal(',cloth),
        ('void Cloth::disturbance(',cloth),('int PullCloth(',cloth),
        ('extern "C" void re4dc_cloth_material_retire11(',cloth),
        ('extern "C" void re4dc_cloth_material_retire_one11(',cloth),
        ('void* cEsp::operator new(',esp),('int PullEsp(',esp),('void PushEsp(',esp),
        ('int EspArrayAlloc(',esp),('int EspArrayFree(',esp),('int EspArrayPush(',esp),('int EspArrayPop(',esp),
        ('cEsp* EspGetDmyPtr(',esp),
        ('cEsp* Esp4e_Create(',producer),('void cEsp4e::move(',producer),('void cEsp4e::Destruct(',producer),
        ('int cEsp4e::SetFreeWork(',producer),('extern "C" int re4dc_cloth_esp4e_words11(',producer),
        ('extern "C" void re4dc_cloth_esp4e_retire11(',producer),
        ('static int re4dc_cloth_visible(',cloth),('static void ClothDraw_log_room(',cloth),
        ('void clothTrans(',cloth),('void ClothDraw(',cloth),('void ClothDrawNow(',cloth)]
 for sig,source in names:
  if sig=='void Cloth::Set(' and oom_source_revision:
   source=subprocess.check_output(['git','show',oom_source_revision+':src/game/cloth.cpp'],cwd=ROOT,text=True)
  # Declarations near the source top are not the implementation.
  if sig.startswith(('int EspArray','int PullCloth','void PushEsp','cEsp* Esp4e_Create')):
   pos=source.rfind(sig);body=function(source[pos:],sig)
  elif sig=='void clothTrans(':body=source[source.index('void clothTrans(Cloth* pCL)\n{'):]
  else:
   try:body=function(source,sig)
   except Exception as error:raise RuntimeError(sig) from error
  if sig=='void* cEsp::operator new(':
   # The recovered allocator inspects raw, not-yet-constructed pool slots.
   # Disable only that host vptr check; the new typed helper keeps vptr/ASan.
   body='__attribute__((no_sanitize("vptr")))\n'+body.replace('unsigned int size','std::size_t size',1)
  code+='\n'+body+'\n'
 native=(ROOT/'port/dreamcast/game/platform/native_effect.cpp').read_text()
 macro_start=native.index('#if defined(RE4DC_CLOTH_MATERIAL11)')
 code+=native[macro_start:native.index('#line 15',macro_start)]+'\n'
 code+='\n'+function(native,'extern "C" void re4dc_effect_retire_room(')+'\n'
 code+=PUB.native_hooks((ROOT/'port/dreamcast/game/platform/native_ui.cpp').read_text())+'\n'+after
 caller=(ROOT/'src/game/esp_sub.cpp').read_text()
 failure=function(caller[caller.index('        ret = e.p->SetFreeWork(rec, seed);'):],'    if (ret == 0) {')
 call='        ret = e.p->SetFreeWork(rec, seed);'
 boundary='''\nint actual_creation_failure_boundary11(cEsp* effect,EspGenWork* rec,u32* seed,cEsp** out){
 struct{cEsp* p;}e{effect};int ret;\n'''+call+'\n'+failure+'\nreturn ret;\n}\n'
 code=code.replace('unsigned cases11=0;',boundary+'\nunsigned cases11=0;')
 return stub,code

def run_host(out,sanitize,pool_recycle,slot_hook_revision,oom_source_revision,oom_only):
 out.mkdir(parents=True,exist_ok=False);stub,code=fixture(slot_hook_revision,oom_source_revision)
 assert code.count('no_sanitize("vptr")')==1
 assert '__attribute__((no_sanitize("vptr")))\nvoid* cEsp::operator new(' in code
 @contextlib.contextmanager
 def persistent(prefix):yield str(out)
 M.tempfile.TemporaryDirectory=persistent
 (out/'generated.cpp').write_text(code)
 original_run=subprocess.run;commands=[]
 def recorded_run(command,*args,**kwargs):
  if command[0]!='g++':kwargs['env']=dict(kwargs.get('env',os.environ),UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  result=original_run(command,*args,**kwargs)
  label='compile' if command[0]=='g++' else 'execute'
  (out/(label+'.log')).write_text((result.stdout or '')+(result.stderr or ''))
  commands.append(dict(command=list(map(str,command)),returncode=result.returncode))
  (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  return result
 M.subprocess.run=recorded_run
 try:stdout=M.ClothMaterial11().build_run(stub,code,sanitize=sanitize,full_package=True,extra=('-DRE4DC_GAME=1',f'-DRE4DC_ESP_POOL_RECYCLE={pool_recycle}',f'-DRE4DC_CLOTH_SINGLE_OOM_ONLY11={int(oom_only)}','-ffp-contract=off','-fstack-usage'))
 except BaseException:(out/'failure.log').write_text(traceback.format_exc());raise
 (out/'run.log').write_text(stdout)
 if sanitize:
  assert 'runtime error:' not in (out/'execute.log').read_text()
  assert 'ERROR: AddressSanitizer' not in (out/'execute.log').read_text()
 return dict(status='PASS',sanitize=sanitize,pool_recycle=pool_recycle,slot_hook_revision=slot_hook_revision,oom_source_revision=oom_source_revision,oom_only=oom_only,stdout=stdout,
             sanitizer_scope='ASan/UBSan halt_on_error; only legacy raw-pool operator new has host vptr instrumentation excluded; new typed helper vptr checks remain enabled' if sanitize else 'not sanitized')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--sanitize',action='store_true');p.add_argument('--pool-recycle',type=int,choices=(0,1),default=1);p.add_argument('--slot-hook-revision');p.add_argument('--oom-source-revision');p.add_argument('--oom-only',action='store_true');a=p.parse_args()
 row=run_host(a.output.resolve(),a.sanitize,a.pool_recycle,a.slot_hook_revision,a.oom_source_revision,a.oom_only)
 row['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'src/game/cloth.cpp',ROOT/'src/game/esp4e.cpp',ROOT/'src/game/esp.cpp',ROOT/'src/game/esp_sub.cpp',ROOT/'include/cloth.h',ROOT/'port/dreamcast/game/platform/gx_stub.cpp',ROOT/'port/dreamcast/game/platform/native_draw_plan_owner.cpp',ROOT/'port/dreamcast/game/platform/native_effect.cpp',ROOT/'port/dreamcast/game/effects30.mk',ROOT/'port/dreamcast/game/platform/include/cloth_material11_source.hpp',ROOT/'port/dreamcast/game/platform/include/cloth_material11_sampler.hpp',ROOT/'port/dreamcast/game/platform/include/cloth_publication11.hpp',ROOT/'port/dreamcast/game/platform/include/native_cloth_sheet11.hpp',ROOT/'port/dreamcast/game/platform/include/native_cloth_sheet11.inc',Path(__file__),HERE/'cloth_single_material11_fixture.cpp.in',HERE/'test_cloth_material11.py',ROOT/'port/dreamcast/room/texture_package.cpp',ROOT/'port/dreamcast/tools/convert_tpl.py')}
 (a.output/'receipt.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
if __name__=='__main__':main()

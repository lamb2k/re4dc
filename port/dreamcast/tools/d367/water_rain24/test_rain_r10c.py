#!/usr/bin/env python3
"""Bounded actual-source host controls for the private default-off r10c rain experiment.
No SDK, guest, source data or evidence writer. Generated compilation/runs stay in /dev/shm.
"""
import hashlib,json,pathlib,re,resource,subprocess,tempfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[4]
BASE='d291f814b5a873718c3f32b686eef5f1a8707f1d'
FILTER='src/game/filter06.cpp';MK='port/dreamcast/game/effects30.mk'
def call(args,**kw):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,**kw)
def old(path):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path],timeout=10).decode()
def extract(text,sig,last=False):
 start=text.rindex(sig) if last else text.index(sig);a=text.index('{',start);depth=1;b=a+1
 while depth:depth+=(text[b]=='{')-(text[b]=='}');b+=1
 return text[start:b]
def h(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
new=(ROOT/FILTER).read_text();baseline=old(FILTER);fixture=(HERE/'fixture_rain_r10c.cpp.in').read_text()
# Queue words are actual source declarations; mocks carry no independent ticket design.
fixture=fixture.replace('u32 s_raindc_queued_room=0,s_raindc_queued_frame=0;', 'static u32 s_raindc_queued_room, s_raindc_queued_frame;')
assert 'static u32 s_raindc_queued_room, s_raindc_queued_frame;' in new
sigs=['static int Filter06Ps2Rain()','static f32 RainDcUnit()','static void RainDcSpawn(','static void RainDcFlush()','void Filter06RoomInit()','void Filter06Trans()','void Filter06SetParam(','void Filter06Render()']
shared=[('src/game/filter.cpp',['void FilterTrans()']),('src/game/main_sub.cpp',['int Render_checkBlurPermission()']),('src/game/espgen44.cpp',['void Espgen44_Destruct(','int Espgen44_SetFreeWork(']),('port/dreamcast/game/platform/gx_stub.cpp',['void GXSetDrawSync(u16 token)'])]
def unit(text):
 parts=[]
 if 'static int Filter06R10cRain()' in text:
  parts=['#if RE4DC_RAIN_R10C_DC',extract(text,'static int Filter06R10cRain()'),extract(text,'static void RainDcR10cCancel()'),'#endif']
 for sig in sigs:
  body=extract(text,sig,last=sig=='void Filter06Render()')
  if sig=='void Filter06Render()':body=body[:body.index('    GXSetBlendMode(')]+'}\n'
  parts.append(body)
 for path,items in shared:
  source=(ROOT/path).read_text()
  parts.extend(extract(source,sig) for sig in items)
 return fixture.replace('/* EXTRACTED_SOURCE */','\n'.join(parts))
# Actual callback runs in Render before the synchronous ADEB hook and the next frame increment.
main=(ROOT/'src/game/main.cpp').read_text();render=extract((ROOT/'src/game/trans.cpp').read_text(),'void Render()',last=True)
loop=main[main.index('            Render();'):main.index('            TaskScheduler();')]
assert loop.index('Render();')<loop.index('SetPrimBuffPtr();')<loop.index('ClearOt();')<loop.index('pG->Frame_cnt++;')
assert render.index('ExecOt(OT_TYPE_MAX);')<render.index('GXSetDrawSync(0xADEB);')
assert not re.search(r'Frame_cnt\s*(?:\+\+|--|=(?!=)|\+=|-=)',render)
assert 'OT_TYPE_MAX = 18' in (ROOT/'include/trans_ot.h').read_text()
hook=extract((ROOT/'port/dreamcast/game/platform/gx_stub.cpp').read_text(),'void GXSetDrawSync(u16 token)')
assert '#if RE4DC_D349_RENDERER_STACK' in hook and hook.index('re4dc_model_finish_source_draws()')<hook.index('re4dc_rain_flush()')
# Retain the original historical baseline. The later independently qualified DIAG
# adds only guarded observation statements to Filter06Trans; compare its ACTUAL
# preprocessed DIAG0 simulation in every PS2/native combination, not raw text.
simulation={}
for sig in ['void cParticle06::init(', 'void cParticle06::move()', 'static int Filter06Ps2Rain()']:
 a=extract(baseline,sig);b=extract(new,sig);assert a==b,sig+' changed';simulation[sig]=h(a)
def simulation_projection(source,flags):
 body=extract(source,'void Filter06Trans()')
 x=call(['g++','-x','c++','-E','-P',*['-D'+f for f in flags],'-'],input=body.encode())
 assert x.returncode==0,x.stderr.decode()
 return x.stdout
def check_trans_simulation(source):
 comparisons=[]
 for ps2 in [0,1]:
  for native in [0,1]:
   flags=['RE4DC_RAIN_PS2='+str(ps2),'RE4DC_RAIN_R10C_DC='+str(native)]
   original=simulation_projection(baseline,flags)
   for diag in [[],['RE4DC_RAIN_R10C_DIAG=0']]:
    actual=simulation_projection(source,flags+diag)
    assert actual==original,'Filter06Trans simulation changed with DIAG0'
    comparisons.append({'ps2':ps2,'native':native,'diag':'absent' if not diag else '0','sha256':h(actual)})
 return comparisons
trans_simulation=check_trans_simulation(new)
# A genuine simulation change or leaking diagnostic guard must remain detectable.
trans_negatives=[]
for name,a,b in [('alpha-update','flt06.alphaF +=','flt06.alphaF -='),('diagnostic-guard-leak','#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG','#if !defined(RE4DC_RAIN_R10C_DIAG) || !RE4DC_RAIN_R10C_DIAG')]:
 body=extract(new,'void Filter06Trans()');assert a in body
 mutant=new.replace(body,body.replace(a,b,1),1)
 try:check_trans_simulation(mutant)
 except AssertionError:trans_negatives.append(name)
 else:raise AssertionError(name+' simulation guard mutant survived')
receipt={'scope':'host source excerpts, source-order checks, preprocessing and GNU Make flags; no SH4 ABI/target/image/current-loaded proof','base':BASE,'source_sha256':h(new),'unchanged_simulation_function_sha256':simulation,'diagnostic_guarded_Trans':{'historical_raw_sha256':h(extract(baseline,'void Filter06Trans()')),'current_raw_sha256':h(extract(new,'void Filter06Trans()')),'actual_DIAG0_preprocessed_comparisons':trans_simulation,'projection_negatives_defeated':trans_negatives,'DIAG1_scope':'separate actual rain_diag24 controls; no DIAG1 simulation identity claim'},'frame_lifecycle_sha256':{'main_loop_excerpt':h(loop),'Render':h(render),'GXSetDrawSync':h(hook)},'passed':[]}
with tempfile.TemporaryDirectory(prefix='water-rain24-r10c-controls-',dir='/dev/shm') as temp:
 ram=pathlib.Path(temp);cpp=ram/'host.cpp';exe=ram/'host'
 def host(text,enabled,night=False):
  cpp.write_text(unit(text));result=call(['g++','-std=c++17','-O2','-DRE4DC_RAIN_R10C_DC='+str(enabled),str(cpp),'-o',str(exe)])
  assert result.returncode==0,result.stderr.decode()
  return call([str(exe)]+(['night'] if night else []))
 for text,on in [(baseline,0),(new,0),(new,1)]:
  result=host(text,on);assert result.returncode==0,result.stderr.decode();receipt['passed'].append(result.stdout.decode().strip())
 nights=[host(text,on,True) for text,on in [(baseline,0),(new,0),(new,1)]]
 assert all(x.returncode==0 for x in nights)
 assert nights[0].stdout==nights[1].stdout==nights[2].stdout
 receipt['old_night_parity']={'bytes':len(nights[0].stdout),'sha256':h(nights[0].stdout),'arms':['baseline','new OFF','new ON']}
 mutants={
 'room-only-signature':('pG->room_id == 0x10C && flt06.p != 0 && flt06.num == 1100 &&','pG->room_id == 0x10C || flt06.p != 0 && flt06.num == 1100 &&'),
 'stale-frame':('if (r10c && (s_raindc_queued_frame != pG->Frame_cnt ||','if (r10c && (false ||'),
 'prior-registration-frame':('s_raindc_queued_frame = pG->Frame_cnt;','s_raindc_queued_frame = pG->Frame_cnt - 1;'),
 'stop-keeps-moving':('if (r10c && (pG->Stop_flg & 0x08000000))','if (false)'),
 'wrong-alpha-normalizer':('s_raindc_alpha) * (1.0f / 80.0f)','s_raindc_alpha) * (1.0f / 60.0f)'),
 'night-color-for-r10c':('r10c ? 0xD2D2D2U','r10c ? 0xB4B4B4U'),
 'repeat-pending':('    s_raindc_pending = 0;\n#if defined(RE4DC_RAIN_R10C_DIAG)','    s_raindc_pending = 1;\n#if defined(RE4DC_RAIN_R10C_DIAG)'),
 'no-setter-cancel':('    RainDcR10cCancel();\n#endif\n    flt06.num = level;','    /* omitted */\n#endif\n    flt06.num = level;'),
 'no-room-init-cancel':('    RainDcR10cCancel();\n#endif\n    memclr_asm(&flt06','    /* omitted */\n#endif\n    memclr_asm(&flt06'),
 'ignore-indoor-flush':('(pG->Status_flg[1] & 0x02000000) || !Render_checkBlurPermission()','false || !Render_checkBlurPermission()'),
 'ignore-height-flush':('Screen.height != 448.0f || Filter09GetbUse()','false || Filter09GetbUse()')}
 for name,(a,b) in mutants.items():
  assert new.count(a)==1,(name,new.count(a));result=host(new.replace(a,b),1)
  assert result.returncode==-6 and b'Assertion' in result.stderr,name+' did not fail a compiled behavioral assertion'
 receipt['source_mutants_defeated']=list(mutants)
 # Preprocess every token of the actual file with empty include stubs; no target ABI/codegen claim.
 stubs=ram/'stubs';stubs.mkdir()
 for inc in set(re.findall(r'^#include "([^"]+)"',baseline+'\n'+new,re.M)):(stubs/inc).touch()
 def preprocess(text,defs):
  cpp.write_text(text);x=call(['g++','-E','-P','-nostdinc','-I'+str(stubs),'-x','c++',str(cpp)]+['-D'+d for d in defs]);assert x.returncode==0,x.stderr.decode();return x.stdout
 configs=[[],['RE4DC_RAIN_PS2=1'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1','RE4DC_RAIN_DC_N=320'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1','RE4DC_LAKE_FIX_TOGGLE=1'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1','RE4DC_RAIN_DC_N=320','RE4DC_LAKE_FIX_TOGGLE=1']]
 for flags in configs:
  original=preprocess(baseline,flags)
  for disable in [[],['RE4DC_RAIN_R10C_DC=0']]:assert preprocess(new,flags+disable)==original
 receipt['gate0_full_preprocessed_file_comparisons']=len(configs)*2
 # Actual Make include: no SDK/recipes/build. Inspect target-specific flags with a RAM makefile.
 prereqs=['RAIN_DC','RAIN_PS2','D349_RENDERER_STACK','PVR_STREAM','NATIVE_LASER','EFFECT_SPRITES']
 mk=ram/'effects30.mk';mf=ram/'test.mk';obj=ram/'obj';target=str(obj/'src/game/filter06.o')
 def make(text,vals):
  mk.write_text(text);mf.write_text('OBJDIR := '+str(obj)+'\ninclude '+str(mk)+'\n'+target+':\n\t@echo $(GAME_CPPFLAGS)\n')
  defaults={x:'1' for x in prereqs};defaults.update(vals)
  return call(['make','-s','--no-print-directory','-f',str(mf),target]+[k+'='+v for k,v in defaults.items()])
 mknew=(ROOT/MK).read_text();mkold=old(MK)
 a=make(mkold,{});assert a.returncode==0,a.stderr.decode()
 for vals in [{},{'RAIN_R10C_DC':'0'}]:
  b=make(mknew,vals);assert b.returncode==0 and a.stdout==b.stdout,b.stderr.decode()
 b=make(mknew,{'RAIN_R10C_DC':'1'});assert b.returncode==0 and b'-DRE4DC_RAIN_R10C_DC=1' in b.stdout,b.stderr.decode()
 negatives=[]
 for v in ['', '2','-1','01','0 1','1 1','%','*']:
  assert make(mknew,{'RAIN_R10C_DC':v}).returncode!=0;negatives.append('flag='+repr(v))
 for key in prereqs:
  assert make(mknew,{'RAIN_R10C_DC':'1',key:'0'}).returncode!=0;negatives.append(key+'=0')
 # Explicit flush-owner guard mutation must fail the prerequisite test.
 bad=mknew.replace('ifneq ($(D349_RENDERER_STACK),1)\n$(error RAIN_R10C_DC needs D349_RENDERER_STACK=1 for the actual ADEB flush)\nendif\n','')
 assert bad!=mknew and make(bad,{'RAIN_R10C_DC':'1','D349_RENDERER_STACK':'0'}).returncode==0
 receipt['make_negative_cases']=negatives;receipt['make_flush_owner_mutation_detected']=True
print(json.dumps(receipt,indent=2))
#!/usr/bin/env python3
"""Bounded actual C++ excerpt, preprocessing, Make and compiling-mutant controls. No SDK/guest."""
import hashlib,json,pathlib,re,resource,subprocess,tempfile
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];BASE='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
FILTER='src/game/filter06.cpp';ESP='src/game/espgen44.cpp';MK='port/dreamcast/game/effects30.mk'
def old(p):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+p],timeout=15).decode()
def run(args,**kw):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,**kw)
def extract(s,sig,last=False):
 a=s.rindex(sig) if last else s.index(sig);b=s.index('{',a);n=1;c=b+1
 while n:n+=(s[c]=='{')-(s[c]=='}');c+=1
 return s[a:c]
new=(ROOT/FILTER).read_text();esp=(ROOT/ESP).read_text();fixture=(HERE/'fixture_rain_diag.cpp.in').read_text()
sigs=['static f32 RainDcUnit()','static void RainDcSpawn(','static void RainDcFlush()','void Filter06Init()','void Filter06RoomInit()','void Filter06Trans()','void Filter06SetParam(','void Filter06Render()']
def unit(s,e):
 parts=['static int Filter06Ps2Rain()'+extract(s,'static int Filter06Ps2Rain()').split('static int Filter06Ps2Rain()',1)[1], '#if RE4DC_RAIN_R10C_DC || RE4DC_RAIN_R10C_DIAG',extract(s,'static int Filter06R10cRain()'),'#endif','#if RE4DC_RAIN_R10C_DC',extract(s,'static void RainDcR10cCancel()'),'#endif']
 if '// Private observation only.' in s:
  a=s.index('#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG\n// Private observation only.');b=s.index('static f32 RainDcUnit()',a)
  parts.append(re.sub(r'^#include.*\n','',s[a:b],flags=re.M))
 for sig in sigs:
  body=extract(s,sig,last=sig=='void Filter06Render()')
  if sig=='void Filter06Render()':body=body[:body.index('    GXSetBlendMode(')]+'}\n'
  parts.append(body)
 for p,ss in [('src/game/filter.cpp',['void FilterTrans()']),('src/game/main_sub.cpp',['int Render_checkBlurPermission()']),('port/dreamcast/game/platform/gx_stub.cpp',['void GXSetDrawSync(u16 token)'])]:
  source=(ROOT/p).read_text();parts.extend(extract(source,x) for x in ss)
 parts.extend(extract(e,x) for x in ['void Espgen44_Destruct(','int Espgen44_SetFreeWork('])
 return fixture.replace('/* EXTRACTED_SOURCE */','\n'.join(parts))
receipt={'source_base':BASE,'scope':'actual extracted C++ host functions; no target ABI/opcode/cache/programme/guest proof','passed':[]}
with tempfile.TemporaryDirectory(prefix='rain-diag24-host-',dir='/dev/shm') as temp:
 ram=pathlib.Path(temp);cpp=ram/'host.cpp';exe=ram/'host'
 def host(s,e,feature,diag,night=False):
  cpp.write_text(unit(s,e));c=run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Wno-unused-parameter','-DRE4DC_GAME=1','-DRE4DC_RAIN_DIAG_HOST_TEST=1','-DRE4DC_RAIN_R10C_DC='+str(feature),'-DRE4DC_RAIN_R10C_DIAG='+str(diag),str(cpp),'-o',str(exe)])
  assert c.returncode==0,c.stderr.decode()
  return run([str(exe)]+(['night'] if night else []))
 for feature in [0,1]:
  for s,e,diag,label in [(old(FILTER),old(ESP),0,'baseline'),(new,esp,0,'new-DIAG0'),(new,esp,1,'new-DIAG1')]:
   x=host(s,e,feature,diag);assert x.returncode==0,(feature,label,x.stderr.decode());receipt['passed'].append({'feature':feature,'arm':label,'result':x.stdout.decode().strip()})
  nights=[host(s,e,feature,d,True) for s,e,d in [(old(FILTER),old(ESP),0),(new,esp,0),(new,esp,1)]]
  assert all(x.returncode==0 for x in nights)
  assert nights[0].stdout==nights[1].stdout==nights[2].stdout
  receipt.setdefault('night_parity',[]).append({'feature':feature,'bytes':len(nights[0].stdout),'sha256':hashlib.sha256(nights[0].stdout).hexdigest()})

 # Full actual source preprocessing identity, with absent/0 DIAG in both feature arms.
 stub=ram/'stubs';stub.mkdir()
 for inc in set(re.findall(r'^#include "([^"]+)"',old(FILTER)+new+old(ESP)+esp,re.M)):
  q=stub/inc;q.parent.mkdir(parents=True,exist_ok=True);q.touch()
 def pp(text,defs):
  cpp.write_text(text);x=run(['g++','-E','-P','-nostdinc','-I'+str(stub),'-x','c++',str(cpp)]+['-D'+d for d in defs]);assert x.returncode==0,x.stderr.decode();return x.stdout
 configs=[[],['RE4DC_RAIN_PS2=1'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1','RE4DC_RAIN_DC_N=320'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1','RE4DC_LAKE_FIX_TOGGLE=1'],['RE4DC_RAIN_PS2=1','RE4DC_RAIN_DC=1','RE4DC_RAIN_DC_N=320','RE4DC_LAKE_FIX_TOGGLE=1']]
 comparisons=0
 for config in configs:
  for feature in [0,1]:
   flags=config+['RE4DC_RAIN_R10C_DC='+str(feature)]
   for path,source in [(FILTER,new),(ESP,esp)]:
    baseline=pp(old(path),flags)
    for diag in [[],['RE4DC_RAIN_R10C_DIAG=0']]:
     actual=pp(source,flags+diag);assert actual==baseline,(path,flags,diag)
     comparisons+=1
 receipt['full_file_gate0_preprocess_comparisons']=comparisons
 # Exact Make include and target-specific flag checks; no SDK/compile recipe invoked.
 mk=ram/'effects30.mk';mf=ram/'test.mk';obj=ram/'obj';prereqs=['RAIN_DC','RAIN_PS2','D349_RENDERER_STACK','PVR_STREAM','NATIVE_LASER','EFFECT_SPRITES']
 def make(text,vals):
  mk.write_text(text);mf.write_text('OBJDIR := '+str(obj)+'\ninclude '+str(mk)+'\nall: '+str(obj/'src/game/filter06.o')+' '+str(obj/'src/game/espgen44.o')+' '+str(obj/'platform/native_ui.o')+'\n'+str(obj/'src/game/filter06.o')+' '+str(obj/'src/game/espgen44.o')+':\n\t@echo $@ $(GAME_CPPFLAGS)\n'+str(obj/'platform/native_ui.o')+':\n\t@echo $@ $(PLATFORM_CPPFLAGS)\n')
  defaults={x:'1' for x in prereqs};defaults.update(vals)
  return run(['make','-s','--no-print-directory','-f',str(mf),'all']+[k+'='+v for k,v in defaults.items()])
 mnew=(ROOT/MK).read_text();mold=old(MK)
 for feature in [0,1]:
  baseline=make(mold,{'RAIN_R10C_DC':str(feature)});assert baseline.returncode==0,baseline.stderr.decode()
  for d in [None,'0']:
   vals={'RAIN_R10C_DC':str(feature)}
   if d is not None:vals['RAIN_R10C_DIAG']=d
   x=make(mnew,vals);assert x.returncode==0 and x.stdout==baseline.stdout,x.stderr.decode()
  x=make(mnew,{'RAIN_R10C_DC':str(feature),'RAIN_R10C_DIAG':'1'});assert x.returncode==0,x.stderr.decode()
  assert x.stdout.count(b'-DRE4DC_RAIN_R10C_DIAG=1')==2
  assert x.stdout.replace(b' -DRE4DC_RAIN_R10C_DIAG=1',b'')==baseline.stdout
 negatives=[]
 for value in ['', '2','-1','01','1 0','0 1','%','1%','yes']:
  x=make(mnew,{'RAIN_R10C_DIAG':value});assert x.returncode!=0;negatives.append('flag='+repr(value))
 for key in prereqs:
  for value in ['0','1 0']:
   x=make(mnew,{'RAIN_R10C_DIAG':'1',key:value});assert x.returncode!=0;negatives.append(key+'='+value)
 receipt['make_rejections']=negatives
 # Every mutant must still compile, then fail an actual C++ control.
 mutants={
  'no-cold-writeback':('dcache_wback_range((uintptr_t) &re4dc_rain_r10c_diag, sizeof(re4dc_rain_r10c_diag));','(void) 0;'),
  'warm-ABI0-thaw':('if (any) return;','if (d->abi_flags != 0) return;'),
  'no-open-ABI-freeze':('if (d->abi_flags != 1 || (d->seq & 1) || d->seq >= RD_LAST) return 0;','if ((d->seq & 1) || d->seq >= RD_LAST) return 0;'),
  'no-terminal-final-publication':('if (d->seq == RD_LAST - 2)', 'if (false)'),
  'u16-wrap':('if (d->counts[counter] >= 0xfffe)','if (false)'),
  'generation-wrap':('if (d->setter_generation >= 0xfffffffeU)','if (false)'),
  'aggregate-wrap':('if (key->reported >= 0xffffffffU - d->accepted_total)','if (false)'),
  'retain-native-valid-on-events':('    d->state_flags &= ~(RD_SAMPLE | RD_BLUR_KNOWN | RD_BLUR_OK);','    /* omitted sample invalidation */'),
  'requested-as-return':('    diag_key.reported = re4dc_rain_dc_streaks(s_raindc_out, n);','    diag_key.reported = re4dc_rain_dc_streaks(s_raindc_out, n); diag_key.reported = n;'),
  'return-ABA-ignore-sequence':('d->seq == key->seq && key->generation != 0','key->generation != 0'),
  'return-ignore-callback-generation':('d->callback_generation == key->generation &&','true &&'),
  'return-ignore-actual-frame':('pG->Frame_cnt == key->frame &&','true &&'),
  'return-ignore-actual-room':('pG->room_id == key->room &&','true &&'),
  'return-ignore-queue-frame':('d->queue_frame == key->queue_frame &&','true &&'),
  'bind-ignore-signature':('if (valid && controller && record && head &&','if (controller && record && head &&'),
  'bind-ignore-generation':('d->setter_generation == before + 1 && flt06.p','true && flt06.p'),
  'bind-retain-nested-cause':('RainDiagClearCause(); RainDiagCount(RDC_BIND_REJECT);','RainDiagCount(RDC_BIND_REJECT);'),
  'setter-no-invalidation':('RainDiagInvalidate(RD_SET, RDC_SET, RDC_CANCEL_SET, level == 0 ? RD_ZERO : 0);','(void) 0;'),
  'room-no-invalidation':('RainDiagInvalidate(RD_ROOM, RDC_ROOM, RDC_CANCEL_ROOM, 0);','(void) 0;'),
  'callback-no-observation':('    RainDiagCallback();','    (void) 0;'),
  'queue-no-observation':('        RainDiagQueue();','        (void) 0;'),
  'discard-consumed-queue-context':('key->seq = RainDiag()->seq; key->generation = RainDiag()->setter_generation;','RainDiag()->state_flags &= ~RD_QUEUE_KEY; key->seq = RainDiag()->seq; key->generation = RainDiag()->setter_generation;')}
 defeated=[]
 for name,(a,b) in mutants.items():
  assert new.count(a)==1,(name,new.count(a))
  x=host(new.replace(a,b),esp,1,1);assert x.returncode!=0,name+' survived';defeated.append(name)
 receipt['compiling_source_mutants_defeated']=defeated
 # Frozen source ordering and ownership boundaries; no extra helper/runtime edit assumed.
 main=(ROOT/'src/game/main.cpp').read_text();render=(ROOT/'src/game/trans.cpp').read_text();boot=main[main.index('void systemRestartInit()'):]
 assert boot.index('EspgenInit();')<boot.index('FilterInit();')<boot.index('TaskScheduler();') if 'TaskScheduler();' in boot else boot.index('EspgenInit();')<boot.index('FilterInit();')
 loop=main[main.index('            Render();'):main.index('            TaskScheduler();')]
 assert loop.index('Render();')<loop.index('pG->Frame_cnt++;')
 assert 'if (!(pG->Disp_flg & 0x00100000) && !PTS(32))' in render
 assert 'if (PTSK(1024))' in render
 receipt['source_pins']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [FILTER,ESP,MK,'src/game/filter.cpp','src/game/main.cpp','src/game/trans.cpp','src/game/espgen.cpp','src/game/espgen10.cpp','port/dreamcast/game/platform/gx_stub.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/room/pvr_geometry.cpp']}
 receipt['storage']={'record_bytes':128,'alignment':32,'possible_alignment_padding_max':31,'planned_native_key_bytes':32,'heap_bytes':0,'target_stack_codegen_proven':False}
 print(json.dumps(receipt,indent=2))

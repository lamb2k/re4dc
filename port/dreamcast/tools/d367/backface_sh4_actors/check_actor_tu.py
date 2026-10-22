"""Actor caller TU qualification, never a guest or full-program gate."""
from pathlib import Path
import hashlib,json,os,subprocess,shutil
T=Path(__file__).resolve().parents[5];G=T/'port/dreamcast/game';O=Path('/root/probe/codex-backface-sh4zam-actors-objects02')
assert os.environ.get('D367_SLOT_HELD')=='1','Shared build lease required'
O.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=G/'platform/native_actor_fast.cpp';baseline=subprocess.check_output(['git','show','20752045a856121ef97cef92662e31bd661b4988:port/dreamcast/game/platform/native_actor_fast.cpp'],cwd=T)
for label,data in [('base',baseline),('candidate',src.read_bytes())]:
 d=O/label;d.mkdir(exist_ok=True);p=d/'native_actor_fast.cpp'
 if p.exists():assert p.read_bytes()==data,'Preserve qualification source identity'
 else:p.write_bytes(data)
cc=shutil.which('kos-c++');assert cc
common=['-std=gnu++20','-O2','-fpermissive','-fno-exceptions','-fno-rtti','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-threadsafe-statics','-I'+str(G/'platform'),'-I'+str(G/'platform/include'),'-I'+str(T/'include'),'-DRE4DC_GAME=1','-DRE4DC_ACTOR_DIRECT=1','-DRE4DC_ACTOR_ASM=1','-DRE4DC_ACTOR_VTX_KERNEL=1','-DRE4DC_NATIVE_ACTOR_SKIN=1','-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_COARSE_ONE_SUBMIT=1','-DRE4DC_ACTOR_UV16=0','-DRE4DC_TA_GUARD=0','-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_ACTOR_BACKFACE=1']
rows=[]
for movca,skin in [(0,0),(1,1)]:
 for mode in [0,1,2]:
  arms=['candidate']if mode==2 else ['base','candidate']
  flags=common+[f'-DRE4DC_ACTOR_MOVCA={movca}',f'-DRE4DC_SKIN_SH4ZAM={skin}',f'-DRE4DC_CPU_BACKFACE={mode}','-DRE4DC_TA_HASH=0']
  for arm in arms:
   source=O/arm/'native_actor_fast.cpp';name=f'{arm}-cpu{mode}-movca{movca}-skin{skin}';obj=O/(name+'.o');pre=O/(name+'.ii')
   commands=[[cc,*flags,'-E','-P',str(source),'-o',str(pre)],[cc,*flags,'-c',str(source),'-o',str(obj)]]
   if not(obj.exists()and pre.exists()):
    for command in commands:
     r=subprocess.run(command,cwd=G,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
     (O/(name+('-pre.log'if'-E'in command else'-compile.log'))).write_text(r.stdout)
     assert r.returncode==0,(name,r.returncode,r.stdout[-3000:])
   stripped=O/(name+'.nodebug.o');subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','--strip-debug',str(obj),str(stripped)],check=True)
   rows.append(dict(arm=arm,cpu=mode,movca=movca,skin=skin,object_sha256=sha(obj),compiled_nodebug_sha256=sha(stripped),preprocessed_sha256=sha(pre),object_bytes=obj.stat().st_size,command=commands[1]))
  if mode in [0,1]:
   a,b=rows[-2:];assert a['preprocessed_sha256']==b['preprocessed_sha256'],('Preprocess identity',a,b)
   assert a['compiled_nodebug_sha256']==b['compiled_nodebug_sha256'],('Compiled object identity excluding path/line debug',a,b)
# Compile the census/trace arm too; its trace-only MOVCA correction is intentional.
traceflags=common+['-DRE4DC_ACTOR_MOVCA=1','-DRE4DC_SKIN_SH4ZAM=1','-DRE4DC_CPU_BACKFACE=2','-DRE4DC_TA_HASH=1','-DRE4DC_BACKFACE_CENSUS=1']
r=subprocess.run([cc,*traceflags,'-c',str(O/'candidate/native_actor_fast.cpp'),'-o',str(O/'candidate-cpu2-trace.o')],cwd=G,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'trace-compile.log').write_text(r.stdout);assert r.returncode==0,r.stdout[-3000:]
receipt=dict(scope=__doc__,source=sha(src),baseline='20752045a856121ef97cef92662e31bd661b4988',compiler=cc,kos_base=os.environ.get('KOS_BASE'),rows=rows,CPU0_CPU1_actual_preprocess_and_compiled_object_identity=True,CPU2_trace_object=sha(O/'candidate-cpu2-trace.o'),limits='Standalone actual SH-4 TU with explicit direct/ASM/AVK/transaction flags; not canonical full recipe, linked image, pixel diff, KOS squeeze, s30 or timing acceptance.',output_bytes=sum(p.stat().st_size for p in O.rglob('*')if p.is_file()))
assert receipt['output_bytes']<32*1024**2
(O/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(receipt_sha256=sha(O/'RECEIPT.json'),objects=len(rows)+1,bytes=receipt['output_bytes'],CPU0_CPU1_identity=True)))

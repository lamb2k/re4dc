#!/usr/bin/env python3
"""Pin production recipe/commands; dry-run Make flag routing; build only two target TUs.
Run under the shared slot and a private tree lock. Never launches a programme or guest.
"""
import argparse, hashlib, json, os, pathlib, re, shlex, subprocess
BASE='a2477bd2b4d2dc5354fe1bbcc5b5c6b45312928f'
TREE=pathlib.Path(__file__).resolve().parents[5];GAME=TREE/'port/dreamcast/game';KOS=pathlib.Path('/root/work/kos-re4dc-d367')
RECIPE=pathlib.Path('/root/probe/lanes/route/out-rra2477bdrP/candidate.txt');LOG=RECIPE.parent/'build.log'
H=lambda b:hashlib.sha256(b).hexdigest()
def extract(text,sig):
 a=text.index(sig);i=text.index('{',a);d=1;j=i+1
 while d:d+=(text[j]=='{')-(text[j]=='}');j+=1
 return text[a:j]
def run(out,reuse=False):
 if not reuse:assert os.environ.get('D367_SLOT_HELD')=='1','Use qualify_target.sh for both leases'
 if not reuse:out.mkdir(parents=True,exist_ok=False)
 assert H(RECIPE.read_bytes())=='f1b86f54a1c6fdf2ccf496c5fb504f5c20047727d9488b3872cba2bfb0646a22'
 archive=KOS/'lib/dreamcast/libkallisti.a';assert H(archive.read_bytes())=='5e2d867fb5825e7825e1843f2542446288e18c383341a58426e452a0b620daaf'
 (out/'candidate.txt').write_bytes(RECIPE.read_bytes())
 mk=GAME/'backface.mk';header=TREE/'port/dreamcast/room/backface_emit.hpp'
 original_mk=subprocess.check_output(['git','-C',str(TREE),'show',BASE+':port/dreamcast/game/backface.mk'])
 original_header=subprocess.check_output(['git','-C',str(TREE),'show',BASE+':port/dreamcast/room/backface_emit.hpp'])
 (out/'original.mk').write_bytes(original_mk)
 harness=out/'flags.mk'
 def flags(cpu,actor,probe,old=False,ok=True):
  include=str(out/'original.mk') if old else str(mk)
  harness.write_text('OBJDIR := obj\nTA_HASH := 0\ninclude '+include+'\n.PHONY: all\nall: obj/platform/native_static.o obj/platform/native_actor_fast.o\nobj/platform/native_static.o obj/platform/native_actor_fast.o:\n\t@echo $@ $(PLATFORM_CPPFLAGS)\n')
  args=['make','--no-print-directory','-n','-f',str(harness),'all',f'CPU_BACKFACE={cpu}',f'ACTOR_BACKFACE={actor}']
  if probe is not None:args += [f'BACKFACE_WALK_PROBE={probe}']
  r=subprocess.run(args,capture_output=True,text=True)
  assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
  return dict(command=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 controls=[]
 for cpu in (0,1):
  for actor in ((0,) if cpu==0 else (0,1)):
   a=flags(cpu,actor,None,old=True);b=flags(cpu,actor,0);assert a['stdout']==b['stdout'];controls += [a,b]
 for cpu,actor,probe in [(0,0,1),(0,0,2),(1,1,1),(1,1,2),(1,0,3),(1,0,''),(1,0,'1 2')]:controls.append(flags(cpu,actor,probe,ok=False))
 units=['native_static','native_actor_fast'];recorded={}
 for unit in units:
  lines=[line for line in LOG.read_text().splitlines() if f' -c platform/{unit}.cpp ' in line and line.startswith('kos-c++ ')]
  assert len(lines)==1,(unit,len(lines));recorded[unit]=shlex.split(lines[0]);assert not any(x.startswith('-DRE4DC_CPU_BACKFACE') or x.startswith('-DRE4DC_ACTOR_BACKFACE') for x in recorded[unit])
  (out/(unit+'-recorded-command.txt')).write_text(lines[0]+'\n')
 generated={}
 for argv in recorded.values():
  for i,arg in enumerate(argv):
   if arg=='-include':
    p=pathlib.Path(argv[i+1]);p=p if p.is_absolute() else GAME/p
    generated[str(p)]=H(p.read_bytes())
 env=os.environ.copy();env.update(KOS_BASE=str(KOS),KOS_CCPLUS='/opt/toolchains/dc/sh-elf/bin/sh-elf-g++',KOS_CFLAGS='',KOS_CPPFLAGS='',KOS_LIBS='')
 wrapper=str(KOS/'utils/build_wrappers/kos-c++');rows=[];saved_header=header.read_bytes()
 variants=[('original-off',0,0,0,True),('A-off',0,0,0,False),('original-C1',1,0,0,True),('probe0-C1',1,0,0,False),('B-keepall',1,0,1,False),('C-world-drop',1,0,2,False)]
 try:
  for name,cpu,actor,probe,old in variants:
   directory=out/name;directory.mkdir(exist_ok=reuse)
   if not reuse:header.write_bytes(original_header if old else saved_header)
   routed=flags(cpu,actor,probe,old=old);controls.append(routed)
   adds={line.split()[1].split('/')[-1][:-2]:line.split()[2:] for line in routed['stdout'].splitlines()}
   for unit in units:
    args=recorded[unit].copy();args[0]=wrapper;args[args.index('-o')+1]=str(directory/(unit+'.o'));args+=adds[unit]
    (directory/(unit+'-command.json')).write_text(json.dumps(dict(cwd=str(GAME),argv=args,wrapper_env={k:env[k] for k in ['KOS_BASE','KOS_CCPLUS','KOS_CFLAGS','KOS_CPPFLAGS','KOS_LIBS']}),indent=2)+'\n')
    if not reuse:
     with (directory/(unit+'.log')).open('w') as log:subprocess.run(args,cwd=GAME,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
     pp=args.copy();pp[pp.index('-c')]='-E';pp[pp.index('-o')+1]=str(directory/(unit+'.ii'));pp+=['-P']
     subprocess.run(pp,cwd=GAME,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
     macros=pp.copy();macros[macros.index('-o')+1]=str(directory/(unit+'.macros'));macros+=['-dM']
     subprocess.run(macros,cwd=GAME,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
    subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','--strip-debug',str(directory/(unit+'.o')),str(directory/(unit+'.no-debug.o'))],check=True)
    dis=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-dr',str(directory/(unit+'.o'))]);(directory/(unit+'.dis')).write_bytes(dis)
    rows.append(dict(variant=name,unit=unit,object_sha256=H((directory/(unit+'.o')).read_bytes()),no_debug_object_sha256=H((directory/(unit+'.no-debug.o')).read_bytes()),preprocessed_sha256=H((directory/(unit+'.ii')).read_bytes()),macros_sha256=H((directory/(unit+'.macros')).read_bytes()),flags=adds[unit]))
 finally:
  if not reuse:header.write_bytes(saved_header)
 def data(name,unit,suffix):return (out/name/(unit+suffix)).read_bytes()
 for unit in units:
  for a,b in [('original-off','A-off'),('original-C1','probe0-C1')]:
   assert data(a,unit,'.no-debug.o')==data(b,unit,'.no-debug.o'),(a,b,unit,'object code/data/relocations')
   if a=='original-off':assert data(a,unit,'.o')==data(b,unit,'.o')
   assert data(a,unit,'.ii')==data(b,unit,'.ii'),(a,b,unit,'preprocessing')
 for name in ('B-keepall','C-world-drop'):
  assert data('A-off','native_actor_fast','.o')==data(name,'native_actor_fast','.o')
  assert data('A-off','native_actor_fast','.ii')==data(name,'native_actor_fast','.ii')
  assert b'#define RE4DC_CPU_BACKFACE ' not in data(name,'native_actor_fast','.macros')
 assert b'#define RE4DC_CPU_BACKFACE 1' in data('B-keepall','native_static','.macros')
 assert b'#define RE4DC_BACKFACE_KEEP_ALL 1' in data('B-keepall','native_static','.macros')
 keep_body=extract(data('B-keepall','native_static','.ii').decode(),'inline unsigned strip(const pvr_vertex_t*')
 c_body=extract(data('C-world-drop','native_static','.ii').decode(),'inline unsigned strip(const pvr_vertex_t*')
 assert 'emit(plain, n);' in keep_body and 'return n;' in keep_body
 assert 'area' not in keep_body and 'keep[' not in keep_body
 assert 'float area' in c_body and 'keep[' in c_body
 (out/'B-keepall-header.ii').write_text(keep_body+'\n');(out/'C-world-drop-header.ii').write_text(c_body+'\n')
 assert data('C-world-drop','native_static','.o')==data('probe0-C1','native_static','.o')
 opcodes={}
 for name in ('B-keepall','C-world-drop'):
  text=data(name,'native_static','.dis').decode()
  blocks=re.split(r'(?m)^([0-9a-f]+ <[^>]+>:)\n',text)
  bodies=[blocks[i]+'\n'+blocks[i+1] for i in range(1,len(blocks)-1,2) if 'ZN5re4dc2bf5strip' in blocks[i]]
  assert len(bodies)==1,(name,len(bodies))
  opcodes[name]={op:len(re.findall(r'\b'+op+r'\s',bodies[0])) for op in ('fsub','fmul','fmac','fcmp/gt')}
  (out/(name+'-actual-strip.dis')).write_text('\n'.join(line.rstrip() for line in bodies[0].splitlines()).rstrip()+'\n')
 assert all(v==0 for v in opcodes['B-keepall'].values())
 assert opcodes['C-world-drop']['fsub']>=4 and opcodes['C-world-drop']['fmul']>=1
 production_objects={}
 for unit in units:
  production=RECIPE.parent/'obj/platform'/(unit+'.o')
  normalized=out/('recorded-'+unit+'.no-debug.o')
  subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','--strip-debug',str(production),str(normalized)],check=True)
  assert normalized.read_bytes()==data('A-off',unit,'.no-debug.o')
  production_objects[unit]=dict(path=str(production),sha256=H(production.read_bytes()),no_debug_sha256=H(normalized.read_bytes()))
 for p,d in generated.items():assert H(pathlib.Path(p).read_bytes())==d,'Inherited generated header changed'
 assert header.read_bytes()==saved_header
 receipt=dict(base=BASE,recipe_sha256=H(RECIPE.read_bytes()),build_log_sha256=H(LOG.read_bytes()),kos_archive_sha256=H(archive.read_bytes()),generated_headers=generated,source_files={p:H((TREE/p).read_bytes()) for p in ['port/dreamcast/game/backface.mk','port/dreamcast/room/backface_emit.hpp','port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/platform/native_actor_fast.cpp']},objects=rows,production_objects=production_objects,make_controls=controls,strip_opcodes=opcodes,proof=['Probe0 original OFF full target objects byte-identical; normal C1 preprocessed source and code/data/relocations match after stripping debug-line records.','Actor objects/preprocessing byte-identical to OFF in B/C; CPU_BACKFACE define absent.','World C/drop target object byte-identical to normal C1 probe0.','World B preprocessed strip contains only copy+emit and no area/run array; original facing body remains in C.'],limits=['Only two production translation units compiled, not a linked programme, pixels, memory, guest or console test.','Production compiler argument list replayed from pinned integrated build log; original generated headers read-only and SHA-bound.','Normal C1 raw object debug records differ with inserted header line numbers; --strip-debug identity includes code, data, symbols and relocations.','No hardware timing gain or target-opcode execution claim.'])
 (out/'target-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(objects=len(rows),proof=receipt['proof']),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--verify-existing',action='store_true');a=p.parse_args();run(a.output.resolve(),a.verify_existing)

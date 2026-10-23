import json,hashlib,subprocess,shlex,gzip,fcntl,os,sys
from pathlib import Path
import os
BASIS=Path('/root/probe/lanes/actor-visibility23-coverage-integration')
R=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration');T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration');G=T/'port/dreamcast/game';arm=sys.argv[1] if len(sys.argv)>1 else 'on';assert arm in ('on','off');O=R/os.environ.get('ACTOR23_ARM_OUTPUT',arm);E=O/'source-compile';E.mkdir(exist_ok=True)
assert not (E/'compile.json').exists(),'Immutable compile receipt exists; use fresh output/version'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def info(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
head=subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip();raw_status=subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True)
assert head=='f2405bb06ebaff6e2a7681479d5308ec5d3b988a' and raw_status=='?? port/dreamcast/game/obj\n'
assert (G/'obj').is_symlink() and (G/'obj').resolve()==O/'link-scratch'
exclude=R/'generated-build-exclude';exclude.write_text('/port/dreamcast/game/obj\n')
status=subprocess.check_output(['git','-c','core.excludesFile='+str(exclude),'-C',str(T),'status','--porcelain'],text=True);assert not status

remote=subprocess.check_output(['git','-C',str(T),'ls-remote','origin','refs/heads/codex/actor-material-route23'],text=True).strip();assert remote.split()[0]==head
(E/'git-clean-remote.txt').write_text('HEAD '+head+'\nSTATUS_PORCELAIN_RAW '+repr(raw_status)+'\nSTATUS_SOURCE_SCOPED '+repr(status)+'\nREMOTE '+remote+'\n')
source={'source':head,'integration':'0b4beb704902a1dc6b2aace056be344863b4a0c1','clean':True,'clean_scope':'Tracked and untracked source, excluding ONLY exact main-approved generated game/obj symlink','raw_git_status':raw_status,'approved_generated_marker':{'path':str(G/'obj'),'target':str((G/'obj').resolve()),'command_scoped_exclude':str(exclude),'exclude_sha256':sha(exclude)},'import_lineage':{'WORLD_METER':['14afb24fe','272e2892f'],'integration_instances':['9c6c57005','73a13949b'],'actor_source':'7997bc3312e02e4c6c6849a8b7c7f8a5fd928ac5','actor_bounds_source':'7662a04038231e1d8718be077f3d0cb56aa7c977'},'original_link_receipt':info(O/'LINK-RECEIPT.json'),'clean_remote_proof':info(E/'git-clean-remote.txt'),'source_manifest':info(O/'SOURCE.json'),'private_inputs_receipt':info(BASIS/'ALLOCATION-INPUTS.json'),'private_inputs_readback':info(BASIS/'PRIVATE-INPUTS-READBACK.json')}
(E/'source-seal.json').write_text(json.dumps(source,indent=2)+'\n')
files=set()
for p in (O/'obj').rglob('*.d'):
 for tok in shlex.split(p.read_text().replace('\\\n',' ')):
  if tok.endswith(':'):continue
  q=Path(tok);q=q if q.is_absolute() else G/q
  if q.is_file():files.add(q.resolve())
(E/'DEPENDENCY-INPUTS.json').write_text(json.dumps([info(p) for p in sorted(files)],indent=2)+'\n')
required=[O/'obj/platform/native_actor_fast.o',O/'obj/platform/native_static.o',O/'obj/platform/native_ui.o',O/'obj/platform/actor_visibility23.o',O/'obj/coarse_ganado.o',O/'obj/shz_bounds23.o',O/'obj/qa_menu.o',O/'obj/tick_log.o',O/'obj/dbgwarp_bridge.o']
if arm=='off':required=[p for p in required if p.name not in ('actor_visibility23.o','shz_bounds23.o')]
assert all(p.is_file() for p in required)
lines=(R/(os.environ.get('ACTOR23_ARM_OUTPUT',arm)+'-build.log')).read_text().splitlines();commands=[]
for p in required:
 found=[line for line in lines if line.startswith(('kos-c++ ','kos-cc ')) and line.endswith(' -o '+str(p))]
 assert len(found)==1,(str(p),len(found));commands.append({'object':info(p),'command':found[0]})
(E/'TOUCHED-COMPILE-COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n')
# Target preprocessor runs share the normal slots/tree lease; no object mutation.
assert os.environ.get('D367_SLOT_HELD')=='1', 'whole build/preprocess must retain shared slot and tree lease'
pre=[]
for item in commands:
 args=shlex.split(item['command']);args=[a for a in args if a not in ('-MMD','-MP')];args[args.index('-c')]='-E';args[args.index('-o')+1]='-';args.insert(1,'-dD')
 p=E/(Path(item['object']['path']).stem+'.preprocessed.cpp.gz')
 proc=subprocess.Popen(args,cwd=G,stdout=subprocess.PIPE,stderr=subprocess.PIPE);h=hashlib.sha256();count=0
 with gzip.open(p,'wb') as out:
  while True:
   chunk=proc.stdout.read(65536)
   if not chunk:break
   h.update(chunk);count+=len(chunk);out.write(chunk)
 err=proc.stderr.read();assert proc.wait()==0,err.decode()
 with gzip.open(p,'rt',errors='strict') as check:
  definitions={}
  for line in check:
   if line.startswith('#define RE4DC_'):
    parts=line.split(maxsplit=2)
    if len(parts)==3:definitions[parts[1]]=parts[2].strip()
 name=Path(item['object']['path']).name
 for key in ('RE4DC_CPU_BACKFACE','RE4DC_WORLD_SCRATCH'):assert definitions.get(key,'0')=='0',(str(p),key,definitions.get(key))
 if name in ('native_actor_fast.o','native_static.o','native_ui.o','actor_visibility23.o','coarse_ganado.o'):
  assert definitions.get('RE4DC_ACTOR_VISIBILITY23','0')==('1' if arm=='on' else '0'),(str(p),'actor define')
 if name in ('native_actor_fast.o','native_static.o','actor_visibility23.o','coarse_ganado.o'):
  assert definitions.get('RE4DC_ACTOR_VISIBILITY23_WITNESS','0')==('1' if arm=='on' else '0'),(str(p),'witness define')
 # Absent toggles are recorded as absent, with source preprocessor default0; do not fabricate -D flags.

 pre.append({'object':item['object']['path'],'command':args,'preprocessed_sha256':h.hexdigest(),'preprocessed_bytes':count,'artifact':info(p),'actual_control_macros':{key:definitions.get(key) for key in ('RE4DC_CPU_BACKFACE','RE4DC_WORLD_SCRATCH','RE4DC_ACTOR_VISIBILITY23','RE4DC_ACTOR_VISIBILITY23_WITNESS')}})
(E/'PREPROCESS.json').write_text(json.dumps(pre,indent=2)+'\n')

reloc=[line for line in lines if line.startswith('gen_overlay: ')];assert len(reloc)==14
(E/'RELOCATION-VALIDATION.txt').write_text('\n'.join(reloc)+'\n')
link=[line for line in lines if line.startswith('RE4DC_LINK_OVL_HELPERS=') and 'bash tools/link.sh' in line];assert len(link)==1
(E/'LINK-COMMAND.txt').write_text(link[0]+'\n')
j=json.loads((O/'LINK-RECEIPT.json').read_text());compile={'source':head,'integration':source['integration'],'elf_sha256':j['main']['sha256'],'raw_sha256':j['raw']['sha256'],'scrambled_sha256':j['scrambled']['sha256'],'image_format':'unscrambled-gdrom','resolved_sha256':j['resolved']['sha256'],'source_seal_sha256':sha(E/'source-seal.json'),'overlays':{'dc/'+p.name:sha(p) for p in sorted(O.glob('*.ovl'))},'required_objects':[info(p) for p in required],'objects_manifest':info(O/'OBJECTS.json'),'dependency_inputs':info(E/'DEPENDENCY-INPUTS.json'),'commands':info(E/'TOUCHED-COMPILE-COMMANDS.json'),'preprocessing':info(E/'PREPROCESS.json'),'build_log':info(R/(os.environ.get('ACTOR23_ARM_OUTPUT',arm)+'-build.log')),'link_command':info(E/'LINK-COMMAND.txt'),'relocation_validation':info(E/'RELOCATION-VALIDATION.txt'),'module_derivation_script':info(Path('/root/probe/lanes/world-scratch23-integration/toolchain/bin/sh-elf-objcopy')),'module_roster':info(O/'modules/roster.json'),'link_input_mapping':info(O/'LINK-INPUT-MAPPING.json'),'private_inputs_receipt':info(BASIS/'ALLOCATION-INPUTS.json'),'private_inputs_readback':info(BASIS/'PRIVATE-INPUTS-READBACK.json'),'runtime_admitted':False}
(E/'compile.json').write_text(json.dumps(compile,indent=2)+'\n');print('SOURCE_COMPILE_READY',info(E/'source-seal.json'),info(E/'compile.json'))

import hashlib,json,subprocess,sys,gzip,shutil,os
from pathlib import Path
import os
BASIS=Path('/root/probe/lanes/actor-visibility23-coverage-integration')
R=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration');T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration');G=T/'port/dreamcast/game';P='/opt/toolchains/dc/sh-elf/bin/sh-elf-'
arm=sys.argv[1];assert arm in ('off','on');O=R/os.environ.get('ACTOR23_ARM_OUTPUT',arm);assert not (O/'LINK-RECEIPT.json').exists(),'Immutable receipt exists; use fresh output/version';assert O.is_dir() and (O/'re4dc-game.elf').is_file()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def info(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def dump(args,path,compress=False):
 if compress:
  proc=subprocess.Popen(args,stdout=subprocess.PIPE)
  with gzip.open(path,'wb') as f:shutil.copyfileobj(proc.stdout,f)
  assert proc.wait()==0
 else:
  with open(path,'wb') as f:subprocess.run(args,stdout=f,check=True)
elf=O/'re4dc-game.elf';dump([P+'objcopy','-R','.stack','-O','binary',str(elf),str(O/'prog.bin')],O/'objcopy.log')
subprocess.run(['/root/work/kos-re4dc-d367/utils/scramble/scramble',str(O/'prog.bin'),str(O/'1ST_READ.BIN')],check=True)
dump([P+'nm','-S','-C',str(elf)],O/'main.symbols.txt');dump([P+'objdump','-h',str(elf)],O/'main.sections.txt')
for m in (O/'modules').glob('*.elf'):
 dump([P+'nm','-S','-C',str(m)],m.with_suffix('.symbols.txt'));dump([P+'objdump','-h',str(m)],m.with_suffix('.sections.txt'));dump([P+'objdump','-d',str(m)],m.with_suffix('.disassembly.gz'),True)
objects=[]
for base in [O/'obj',G/'obj']:
 for p in sorted(base.rglob('*')):
  if p.is_file():objects.append(info(p))
(O/'OBJECTS.json').write_text(json.dumps(objects,indent=2)+'\n')
linked=O/'link-inputs';linked.mkdir(exist_ok=True)
for p in (G/'obj').glob('*'):
 if p.is_file() and p.suffix not in ('.elf',):shutil.copy2(p,linked/p.name)
source=[]
for name in subprocess.check_output(['git','-C',str(T),'ls-files'],text=True).splitlines():
 p=T/name
 if p.is_file():source.append(info(p))
(O/'SOURCE.json').write_text(json.dumps(source,indent=2)+'\n');(O/'source.diff').write_text(subprocess.check_output(['git','-C',str(T),'diff','--binary'],text=True))
kos=Path('/root/work/kos-re4dc-d367')
inputs=[kos/'lib/dreamcast/libkallisti.a',kos/'kernel/arch/dreamcast/kernel/cache.s',kos/'kernel/arch/dreamcast/include/dc/cache.h',kos/'utils/ldscripts/shlelf.xc']
assert len(list(O.glob('*.ovl')))==14 and len(list((O/'modules').glob('*.elf')))==14
receipt={'kind':'ACTOR23_LINKED_PROGRAMME_PENDING_REVIEW','arm':arm,'source_head':subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip(),'base':'0b4beb704902a1dc6b2aace056be344863b4a0c1','import_lineage':{'WORLD_METER':['14afb24fe','272e2892f'],'integration_instances':['9c6c57005','73a13949b'],'actor_source':'7997bc3312e02e4c6c6849a8b7c7f8a5fd928ac5','actor_bounds_source':'7662a04038231e1d8718be077f3d0cb56aa7c977'},'main':info(elf),'raw':info(O/'prog.bin'),'scrambled':info(O/'1ST_READ.BIN'),'resolved':info(O/'resolved-knobs.txt'),'objects_manifest':info(O/'OBJECTS.json'),'source_manifest':info(O/'SOURCE.json'),'modules_roster':info(O/'modules/roster.json'),'overlays':[info(p) for p in sorted(O.glob('*.ovl'))],'kos':[info(p) for p in inputs],'runtime_admitted':False,'ownership_review':'PENDING_MAIN_EXACT_IMAGE_ALL_MODULE_KOS_REVIEW','private_inputs_receipt':info(BASIS/'ALLOCATION-INPUTS.json')}
(O/'LINK-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'arm':arm,'elf':info(elf),'raw':info(O/'prog.bin'),'overlays':len(receipt['overlays']),'receipt':info(O/'LINK-RECEIPT.json')}))

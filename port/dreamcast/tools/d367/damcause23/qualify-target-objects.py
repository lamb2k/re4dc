"""Validate retained real SH4 objects. No link, image, guest or hardware run."""
from pathlib import Path
import hashlib,json,subprocess,struct,shlex
ROOT=Path('/root/probe/codex-damcause23')
OUT=Path('/mnt/c/Game Dev/Emulators/codex-lanes/damcause23')
OBJ=Path('/root/probe/damcause23-sh4-objects01')
BIN='/opt/toolchains/dc/sh-elf/bin/sh-elf-'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a): return subprocess.check_output(a,text=True)
rels=['src/game/em_set.o','src/game/em.o','src/game/read.o','platform/crash_screen.o','platform/modules.o','mod/st1_2/src/st1/r10c.o']
rows=[]
for rel in rels:
 row={'path':rel,'variants':{}}
 for v in ['baseline','default','zero','on03']:
  p=OBJ/v/rel; data=p.read_bytes(); assert data[:7]==b'\x7fELF\x01\x01\x01' and struct.unpack_from('<H',data,18)[0]==42
  nd=Path(str(p)+'.nodebug'); assert nd.exists()
  nm=run(BIN+'nm','-u',str(p)); dis=run(BIN+'objdump','-dr',str(p))
  (OUT/('target-'+v+'-'+rel.replace('/','_')+'.dis')).write_text(dis)
  row['variants'][v]={'sha256':sha(p),'size':p.stat().st_size,'strip_debug_sha256':sha(nd),'undefined_symbols':nm.splitlines()}
 assert len({row['variants'][v]['strip_debug_sha256'] for v in ['baseline','default','zero']})==1
 assert row['variants']['on03']['strip_debug_sha256']!=row['variants']['default']['strip_debug_sha256']
 rows.append(row)
# Use actual production game compile argv, KOS wrappers/environment from caller.
line=next(l for l in (OUT/'target-on03.log').read_text().splitlines() if l.startswith('kos-c++ ') and ' -c ../../../src/game/em_set.cpp ' in l)
cmd=shlex.split(line); c=cmd.index('-c');o=cmd.index('-o'); cmd[c+1]=str(OBJ/'abi-probe.cpp');cmd[o+1]=str(OBJ/'abi-probe.o')
cmd=[x for x in cmd if x not in ['-MMD','-MP']]
probe='''#include "types.h"
#include "scheduler.h"
#include "issue52_actor_diag.h"
static_assert(sizeof(void*)==4 && sizeof(unsigned long)==4 && sizeof(u32)==4);
static_assert(sizeof(int)==4 && sizeof(unsigned)==4 && sizeof(void(*)())==4);
static_assert(sizeof(Issue52Attempt)==88);
static_assert(TASK_NUM==18);
extern "C" const unsigned issue52_abi[] = {sizeof(void*),sizeof(unsigned long),sizeof(u32),sizeof(Issue52Attempt),sizeof(TASK),__builtin_offsetof(TASK,Thread),sizeof(OSThread),TASK_NUM};
'''
(OBJ/'abi-probe.cpp').write_text(probe)
subprocess.run(cmd,cwd=ROOT/'port/dreamcast/game',check=True)
subprocess.run([BIN+'objcopy','-O','binary','--only-section=.rodata.issue52_abi',str(OBJ/'abi-probe.o'),str(OBJ/'abi-probe.bin')],check=True)
abi=list(struct.unpack('<8I',(OBJ/'abi-probe.bin').read_bytes())); assert abi[:4]==[4,4,4,88] and abi[-1]==18
receipt={'source_sha':run('git','-C',str(ROOT),'rev-parse','HEAD').strip(),'base_sha':run('git','-C',str(ROOT),'rev-parse','origin/t15/int').strip(),'scope':'actual six translation-unit object compilation; no full link/image/runtime acceptance','compiler_version':run(BIN+'g++','--version').splitlines()[0],'compiler_sha256':sha(Path(BIN+'g++')),'runner_sha256':sha(Path(__file__)),'abi_values':dict(zip(['pointer','unsigned_long','u32','attempt','TASK','TASK_Thread_offset','OSThread','TASK_NUM'],abi)),'abi_compile_argv':cmd,'abi_object_sha256':sha(OBJ/'abi-probe.o'),'objects':rows,'build_logs':{p.name:sha(p) for p in OUT.glob('target-*-01.log')},'on_first_log_sha256':sha(OUT/'target-on03.log'),'claims':{'strip_debug_objects_default_zero_equal_integration':True,'actual_on_objects_all_different':True,'full_programme_identity':False,'target_execution':False,'hardware_cause':False}}
(OUT/'target-objects01.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'abi':receipt['abi_values'],'objects':len(rows),'off_identity':True,'receipt_sha256':sha(OUT/'target-objects01.json')}))

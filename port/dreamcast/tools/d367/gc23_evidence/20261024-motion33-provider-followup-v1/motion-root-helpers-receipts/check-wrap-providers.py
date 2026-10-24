from pathlib import Path
import hashlib,json,os,resource,shlex,subprocess,tempfile
OWN=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24')
OUT=Path(tempfile.mkdtemp(prefix='gc-motion24-wrap-check-',dir='/dev/shm'))
BINS=Path('/opt/toolchains/dc/sh-elf/bin');RUN=Path('/dev/shm/gc-motion24-target-run-0mftarg0')
PLAN=json.loads((OWN/'target-prep/PREPARATION.json').read_text());REPORT=json.loads((RUN/'report.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
assert os.environ.get('GC_MOTION24_ALLOCATED')==PLAN['head']
log=Path('/root/work/lanes/gc-port23-full-target2-scratch/on/build.log');assert sha(log)==PLAN['input_pins'][str(log)]['sha256']
links=[x for x in log.read_text().splitlines() if 'GAME_LDFLAGS=' in x and 'bash tools/link.sh ' in x];assert len(links)==1
args=shlex.split(links[0]);flag=next(x.split('=',1)[1] for x in args if x.startswith('GAME_LDFLAGS='));wraps=[x.split('=',1)[1] for x in shlex.split(flag) if x.startswith('-Wl,--wrap=')]
names=[x.removeprefix('___real_') for x in REPORT['provider_closure']['missing']]
assert names and all(x in wraps for x in names)
# These tiny synthetic relocations prove installed SH linker --wrap semantics.
# They never become runtime providers or game objects; actual providers below
# are the pinned SDK archive, not the synthetic definitions.
(OUT/'refs.s').write_text('.text\n'+''.join('.long ___real_'+n+'\n' for n in names))
(OUT/'defs.s').write_text('.text\n'+''.join('.globl _'+n+'\n_'+n+':\n.long 0\n' for n in names))
commands=[]
def call(a):
 commands.append(a);r=subprocess.run(a,capture_output=True,text=True);assert r.returncode==0,(a,r.stdout,r.stderr);return r.stdout
for f in ['refs','defs']:call([str(BINS/'sh-elf-as'),'-little','-o',str(OUT/(f+'.o')),str(OUT/(f+'.s'))])
call([str(BINS/'sh-elf-ld'),'-m','shlelf','-r','-o',str(OUT/'unwrapped.o'),str(OUT/'refs.o'),str(OUT/'defs.o')])
base=call([str(BINS/'sh-elf-nm'),'-u',str(OUT/'unwrapped.o')]);assert all('___real_'+n in base for n in names)
call([str(BINS/'sh-elf-ld'),'-m','shlelf','-r',*('--wrap='+n for n in names),'-o',str(OUT/'wrapped.o'),str(OUT/'refs.o'),str(OUT/'defs.o')])
wrapped=call([str(BINS/'sh-elf-nm'),'-u',str(OUT/'wrapped.o')]);assert not wrapped.strip()
call([str(BINS/'sh-elf-ld'),'-m','shlelf','-r',*('--wrap='+n for n in names[1:]),'-o',str(OUT/'missing-one-wrap.o'),str(OUT/'refs.o'),str(OUT/'defs.o')])
bad=call([str(BINS/'sh-elf-nm'),'-u',str(OUT/'missing-one-wrap.o')]);assert bad.split()[-1]=='___real_'+names[0] and len(bad.splitlines())==1
sdk=Path('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a');assert sha(sdk)==PLAN['input_pins'][str(sdk)]['sha256']
defs=call([str(BINS/'sh-elf-nm'),'--defined-only',str(sdk)])
provided={v[-1] for line in defs.splitlines() if len(v:=line.split())>=3 and v[-2].upper() in ['T','D','B','R','W','V','A','S','C']}
assert all('_'+n in provided for n in names)
# Baseline imports already require these exact wrappers. They are not new
# dependencies from Motion and must never be patched with alias/stub code.
parent=call([str(BINS/'sh-elf-nm'),'-u',str(RUN/'parent-native_ui-gate1-motionabsent.o')])
current=call([str(BINS/'sh-elf-nm'),'-u',str(RUN/'current-native_ui-gate1-motionon.o')])
assert all('___real_'+n in parent and '___real_'+n in current for n in names)
for f in ['unwrapped','wrapped','missing-one-wrap']:
 (OUT/(f+'-undefined.txt')).write_text({'unwrapped':base,'wrapped':wrapped,'missing-one-wrap':bad}[f])
result={'status':'EXACT_EXISTING_LINK_WRAP_AND_REAL_PROVIDER_REWRITE_VERIFIED','failed_run_report_sha256':sha(RUN/'report.json'),'existing_link_log_sha256':sha(log),'SDK_archive_sha256':sha(sdk),'rewrites':[{'reference':'___real_'+n,'existing_link_wrap':n,'real_SDK_definition':'_'+n} for n in names],'synthetic_controls':{'unwrapped_has_all_six':True,'exact_wraps_resolve_all':True,'omitted_one_keeps_one_unresolved':True},'baseline_references_unchanged':True,'actual_game_aliases_or_stubs_added':False,'recompiled_game_objects':0,'tools':{str(BINS/n):sha(BINS/n) for n in ['sh-elf-as','sh-elf-ld','sh-elf-nm']},'commands':commands,'scope':'Read-only existing provider query and isolated synthetic SH linker semantic control only. Not a new complete programme/map, heap or runtime check. Initial incomplete provider report remains immutable.'}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');(OWN/'ROOT-WRAP-PROVIDER-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'out':str(OUT),'status':result['status'],'result_sha256':sha(OUT/'result.json')}))
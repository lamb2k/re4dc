from pathlib import Path
import subprocess,json,resource,hashlib,time
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
root=Path('/root/work/lanes/codex-composition-int24');game=root/'port/dreamcast/game';test=root/'port/dreamcast/tools/d367/composition_int24/test_compose_integrated.py';out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/composition-int24')
block='''#if (defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE != 0) || (defined(RE4DC_GC_ASSET_MOTION_UNKNOWN) && RE4DC_GC_ASSET_MOTION_UNKNOWN != 0)
#error PS2_PVS_BATCH_COMPOSE does not yet qualify GC asset diagnostics
#endif
'''
mutants=[('Make-GC-admission',game/'scenery19.mk',' $(GC_ASSET_GATE) $(GC_ASSET_MOTION_UNKNOWN)','', 'Controls.test_make_prerequisites_and_original_guard'),('Static-GC-admission',game/'platform/native_static.cpp',block,'','Controls.test_source_guards'),('UI-GC-admission',game/'platform/native_ui.cpp',block,'','Controls.test_source_guards')]
rows=[]
for name,path,before,after,method in mutants:
 original=path.read_bytes();s=original.decode();assert s.count(before)==1
 try:
  path.write_text(s.replace(before,after));r=subprocess.run(['python3','-B',str(test),method],capture_output=True,text=True)
 finally:path.write_bytes(original)
 (out/(name+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==1 and 'AssertionError: 0 == 0' in r.stderr,(name,r.returncode,r.stderr)
 rows.append({'name':name,'method':method,'exit_code':r.returncode,'intended_failure':'unsupported GC diagnostic configuration erroneously accepted','original_restored_sha256':hashlib.sha256(original).hexdigest()})
(out/'GUARD-MUTANTS.json').write_text(json.dumps(rows,indent=2)+'\n');print('3 admission guard mutants detected; all source restored')

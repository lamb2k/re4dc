"""Qualify the actual espgen10 unit under the frozen extended OFF recipe."""
from pathlib import Path
import subprocess,hashlib,json,shlex,shutil,os
tree=Path('/root/probe/codex-cache21-integration-next')
out=Path('/root/probe/cache21-effect-controller-sh4-20261021-01')
assert not out.exists();assert shutil.disk_usage('/mnt/c').free>=18*1024**3+64*1024**2
out.mkdir()
log=Path('/root/probe/cache21-extended-build-20261021/off-01/build.log').read_text()
lines=[l for l in log.splitlines()if l.startswith('kos-c++ ')and ' -c ../../../src/game/espgen10.cpp 'in l]
assert len(lines)==1,len(lines)
cmd=shlex.split(lines[0])
original=subprocess.check_output(['git','-C',str(tree),'show','2598b8a56819589644604e32b7c6577d2d1ec532:src/game/espgen10.cpp'],text=True)
candidate=(tree/'src/game/espgen10.cpp').read_text()
source=out/'actual-espgen10.cpp';hashes={};rows=[]
tool='/opt/toolchains/dc/sh-elf/bin/'
env=dict(os.environ);env['PATH']='/root/work/kos-re4dc-d367/utils/build_wrappers:/opt/toolchains/dc/sh-elf/bin:'+env['PATH'];env['RE4DC_KOS_BASE']='/root/work/kos-re4dc-d367'
raw=subprocess.check_output(['bash','-c','set -euo pipefail; source port/dreamcast/kos-env.sh; env -0'],cwd=tree,env=env)
env.update(item.split('=',1) for item in raw.decode().split(chr(0))if '=' in item)
for mode,text in [('baseline',original),('unset',candidate),('zero',candidate),('enabled',candidate)]:
 folder=out/mode;folder.mkdir();source.write_text(text)
 command=cmd.copy();command[command.index('../../../src/game/espgen10.cpp')]=str(source);command[command.index('-o')+1]=str(folder/'espgen10.o');command+=['-fstack-usage']
 if mode in('zero','enabled'):command+=['-DRE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST='+str(int(mode=='enabled'))]
 (folder/'command.json').write_text(json.dumps(command,indent=2)+'\n')
 run=subprocess.run(command,cwd=tree/'port/dreamcast/game',env=env,text=True,capture_output=True);(folder/'compile.log').write_text(run.stdout+run.stderr);assert run.returncode==0,(mode,run.stderr[-1500:])
 subprocess.run([tool+'sh-elf-objcopy','--strip-debug',str(folder/'espgen10.o'),str(folder/'espgen10-stripped.o')],check=True)
 size=subprocess.check_output([tool+'sh-elf-size',str(folder/'espgen10-stripped.o')],text=True)
 hashes[mode]=hashlib.sha256((folder/'espgen10-stripped.o').read_bytes()).hexdigest()
 rows.append({'mode':mode,'stripped_sha256':hashes[mode],'size':size,'update_stack':[l for l in(folder/'espgen10.su').read_text().splitlines()if 'espgen10_Update' in l]})
assert hashes['baseline']==hashes['unset']==hashes['zero']
make_rows=[]
for value in(None,'0','1','','2','0 1','1 0','01','-1','yes'):
 command=['make','--no-print-directory','-n',f'OBJDIR={out}/make-obj',str(out/'make-obj/src/game/espgen10.o')]
 if value is not None:command+=['EFFECT_CONTROLLER_VALIDATE_FIRST='+value]
 run=subprocess.run(command,cwd=tree/'port/dreamcast/game',env=env,text=True,capture_output=True);text=run.stdout+run.stderr;(out/('make-'+str(len(make_rows))+'.log')).write_text(text)
 valid=value in(None,'0','1');assert (run.returncode==0)==valid,(value,run.returncode,text[-1000:])
 if valid:
  lines=[l for l in run.stdout.splitlines()if l.startswith('kos-c++ ')and ' -c ../../../src/game/espgen10.cpp 'in l];assert len(lines)==1,(value,len(lines));assert ('-DRE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST=1' in lines[0])==(value=='1')
 make_rows.append({'value':value,'accepted':valid,'returncode':run.returncode})
receipt={'kind':'whole-SH4-controller-unit-off-identity-on-compile','rows':rows,'make_controls':make_rows,'off_identity':True,'source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'recipe':'extended full OFF2598b8a56 exact compile invocation','limits':['Debug stripped equally; source path normalized equally.','New repair qualified only as source/SH4 unit; preceding extended full OFF receipt is not a full program check of this repair.','No full program ON, Flycast, release or physical Dreamcast acceptance.']}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

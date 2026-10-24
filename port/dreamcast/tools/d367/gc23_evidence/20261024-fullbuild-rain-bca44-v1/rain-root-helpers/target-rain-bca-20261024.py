from pathlib import Path
import subprocess,hashlib,json,shlex,tempfile,os
TREE=Path('/root/work/lanes/water-rain24');BASE=Path('/root/work/lanes/gc-port23')
SOURCE='bca44d58a1fa0a51fd87ba94deba8cba925c8998';PRIOR='1d63cffe3a232c402418f2f2d919e7abae476957'
FULL=Path('/root/work/lanes/gc-port23-full-target2-scratch/off')
UNIT='../../../src/game/filter06.cpp'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(tree,*a):return subprocess.check_output(['git','-C',str(tree),*a],text=True).strip()
def main():
 for tree,expected in [(TREE,SOURCE),(BASE,PRIOR)]:
  if git(tree,'rev-parse','HEAD')!=expected or git(tree,'status','--porcelain'):raise RuntimeError('Frozen source mismatch')
 fb=subprocess.check_output(['git','-C',str(BASE),'show','fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2:src/game/filter06.cpp'])
 if fb!=(BASE/'src/game/filter06.cpp').read_bytes():raise RuntimeError('Baseline rain source not fb254')
 if sha(FULL/'program.bin')!='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b':raise RuntimeError('Full baseline identity changed')
 commands=[]
 for line in (FULL/'build.log').read_text().splitlines():
  if not line.startswith('kos-c++ '):continue
  args=shlex.split(line)
  if '-c' in args and args[args.index('-c')+1]==UNIT:commands.append(args)
 if len(commands)!=1:raise RuntimeError('Actual filter06 command not unique')
 pins={str(p):sha(p) for p in [FULL/'build.log',FULL/'out/resolved-knobs.txt',Path('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a')]}
 out=Path(tempfile.mkdtemp(prefix='rain-r10c-bca44-target-',dir='/dev/shm'))
 report=dict(source=SOURCE,baseline_source=PRIOR,baseline_programme_sha256=sha(FULL/'program.bin'),pins=pins,objects=[],scope='One actual current-profile SH4 translation unit, default-off identity and ON compilation only. No full rain programme/link/heap/guest/appearance/PS2 ancestry acceptance.',harness_sha256=sha(__file__))
 tool='/opt/toolchains/dc/sh-elf/bin/'
 print(str(out),flush=True)
 for arm,tree,v in [('baseline',BASE,None),('absent',TREE,None),('zero',TREE,0),('on',TREE,1)]:
  cwd=tree/'port/dreamcast/game';args=commands[0].copy();obj=out/(arm+'.o');args[args.index('-o')+1]=str(obj)
  args=[a for a in args if a not in ('-MMD','-MD','-MP')]
  for flag in ['-MF','-MT','-MQ']:
   while flag in args:
    i=args.index(flag);del args[i:i+2]
  if v is not None:args.append('-DRE4DC_RAIN_R10C_DC='+str(v))
  args.append('-fstack-usage')
  (out/(arm+'-command.json')).write_text(json.dumps(args,indent=2)+'\n')
  dep=out/(arm+'.d')
  with (out/(arm+'.log')).open('w') as log:
   subprocess.run(args+['-M','-MF',str(dep),'-MT',arm],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
   paths=shlex.split(dep.read_text().split(':',1)[1].replace('\\\n',' '))
   before={str((cwd/p).resolve()):sha((cwd/p).resolve()) for p in paths}
   subprocess.run(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
   if any(sha(p)!=h for p,h in before.items()):raise RuntimeError('Compile inputs changed')
  (out/(arm+'-inputs.json')).write_text(json.dumps(before,indent=2)+'\n')
  stripped=out/(arm+'-nodebug.o');subprocess.run([tool+'sh-elf-objcopy','--strip-debug',str(obj),str(stripped)],check=True)
  size=subprocess.check_output([tool+'sh-elf-size',str(obj)],text=True)
  undefined=subprocess.check_output([tool+'sh-elf-nm','-u',str(obj)],text=True);(out/(arm+'-undefined.txt')).write_text(undefined)
  report['objects'].append(dict(arm=arm,sha256=sha(obj),nodebug_sha256=sha(stripped),size=size,inputs=len(before)))
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
  print(arm+' '+size.strip(),flush=True)
  if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>128*1024**2:raise RuntimeError('Owned RAM cap')
 if len({r['nodebug_sha256'] for r in report['objects'][:3]})!=1:raise RuntimeError('OFF target identity mismatch')
 if any(sha(p)!=h for p,h in pins.items()):raise RuntimeError('Profile/SDK drift')
 for tree,expected in [(TREE,SOURCE),(BASE,PRIOR)]:
  if git(tree,'rev-parse','HEAD')!=expected or git(tree,'status','--porcelain'):raise RuntimeError('Post source mismatch')
 report['complete']=True;report['baseline_absent_zero_identical']=True
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('RAIN SH4 UNIT COMPLETE ONLY; OFF identical; no link/guest/appearance acceptance',flush=True)
if __name__=='__main__':main()
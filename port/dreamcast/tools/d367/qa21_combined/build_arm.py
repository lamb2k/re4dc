#!/usr/bin/env python3
"""Build one reserved, frozen combined-regression arm in its isolated tree."""
import argparse, hashlib, json, os, shutil, signal, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('arm', choices=['default-off','qa-control','combined'])
a=p.parse_args()
T=Path(__file__).resolve().parents[6]
assert T == Path('/root/probe/codex-qa21-combined-regression')
B=Path('/root/probe/qa21-combined-build-20261021'); O=B/a.arm
R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/feedback21-boss-qa-20261021/qa-builds')
assert not O.exists(), 'Preserve existing arm'
assert shutil.disk_usage('/mnt/c').free >= 18*1024**3+640*1024**2
source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=T,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=T,text=True).strip()
recipe=R/'qa-on-1/candidate.txt'
knobs=recipe.read_text().split()
assert hashlib.sha256(recipe.read_bytes()).hexdigest()=='54d2e5d56f84d76c5c0071484771ca74957c6649d28b103a5974943728715f70'
knobs=[x for x in knobs if not x.startswith(('QA_MENU=','PAUSE_NATIVE_PRESENTATION=','SS_WINDOW_HOLD_RESTORE='))]
knobs+=['QA_MENU='+str(int(a.arm!='default-off')),'PAUSE_NATIVE_PRESENTATION='+str(int(a.arm=='combined'))]
assert 'GAME_SH4ZAM=1' in knobs and not any(x.startswith('SKIN_SH4ZAM=') for x in knobs)
O.mkdir(parents=True); (O/'candidate.txt').write_text(' '.join(knobs)+'\n')
env=os.environ.copy(); env.update(TREE=str(T),ROUTE_OUT_ROOT=str(B),ROUTE_PROGRAMS_DIR=str(B/'programs'),ROUTE_PROGRAMS_JSON='',SOURCE_DATE_EPOCH='1760000000',ASSETS='/root/probe/lanes/play-actor-bundle',OBJDIR=str(O/'obj'),OUT=str(O),JOBS='4')
cmd=['bash','/root/probe/d367-buildslot.sh','bash','port/dreamcast/tools/d367/build-r21.sh',*knobs]
t=time.monotonic(); guard=None; log=O/'build.log'
with log.open('xb') as stream:
    child=subprocess.Popen(cmd,cwd=T,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    start=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
    (O/'owned-build.json').write_text(json.dumps({'pid':child.pid,'pgid':os.getpgid(child.pid),'proc_start':start,'source':source,'arm':a.arm,'cmd':cmd},indent=2)+'\n')
    while child.poll() is None:
        if shutil.disk_usage('/mnt/c').free < 18*1024**3+64*1024**2: guard='C18GiB+64MiB runtime floor'
        elif log.stat().st_size > 8*1024**2: guard='8MiB owned log limit'
        if guard:
            assert os.getpgid(child.pid)==child.pid and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==start
            os.killpg(child.pid,signal.SIGTERM)
            try: child.wait(timeout=8)
            except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait()
            break
        time.sleep(2)
    rc=child.wait()
if rc or guard:
    (O/'failed.json').write_text(json.dumps({'code':rc,'guard':guard,'source':source,'elapsed_s':time.monotonic()-t},indent=2)+'\n')
    print(log.read_text(errors='replace')[-3500:]); raise SystemExit(rc or 2)
elf=O/'re4dc-game.elf'; raw=O/'program.bin'
subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(raw)],check=True)
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
files={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in [raw,*sorted(O.glob('*.ovl'))]}
assert len(files)==15
control=R/('control-off-1' if a.arm=='default-off' else 'qa-on-1')
if a.arm!='combined':
    for name, row in files.items(): assert row['sha256']==sha(control/name), name+' identity mismatch'
resolved=(O/'resolved-knobs.txt').read_text().split()
assert 'GAME_SH4ZAM=1' in resolved and 'SKIN_SH4ZAM=0' in resolved
assert not any(x=='SS_WINDOW_HOLD_RESTORE=1' for x in resolved)
receipt={'source':source,'arm':a.arm,'seconds':time.monotonic()-t,'elf_sha256':sha(elf),'files':files,'candidate_sha256':sha(O/'candidate.txt'),'resolved_sha256':sha(O/'resolved-knobs.txt'),'control_program_and_14_overlays_exact':a.arm!='combined','submodule':subprocess.check_output(['git','submodule','status'],cwd=T,text=True).strip(),'scope':'Private combined qualification. No target, release or physical hardware acceptance.'}
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
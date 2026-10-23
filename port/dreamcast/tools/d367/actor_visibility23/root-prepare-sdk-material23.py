from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,shutil,subprocess
T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration')
R=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration')
S=Path('/root/probe/codex-actor-visibility23-integration/port/dreamcast/game/third_party/sh4zam')
D=T/'port/dreamcast/game/third_party/sh4zam'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--resources',required=True);a.add_argument('--resources-sha256',required=True);args=a.parse_args()
p=Path(args.resources)
assert sha(p)==args.resources_sha256
r=json.loads(p.read_bytes());age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(r['utc'])).total_seconds()
assert 0<=age<=60 and r['admitted'] and not r['errors'] and r['successor_cap']==736*1024**2
lock=(R/'tree.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip()=='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
assert json.loads((R/'on/RUN-RESULT.json').read_bytes())['exit_code']==2
marker=T/'port/dreamcast/game/obj'
assert marker.is_symlink() and marker.resolve()==R/'on/link-scratch'
assert not (R/'SDK-SOURCE-READBACK.json').exists() and not any(D.rglob('*'))
files=[x for base in ('include','source') for x in (S/base).rglob('*') if x.is_file()]
assert len(files)==54 and sum(x.stat().st_size for x in files)==775416
rows=[]
for src in files:
 assert not src.is_symlink()
 rel=src.relative_to(S);dst=D/rel
 assert not dst.exists() and dst.resolve().is_relative_to(D.resolve())
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 assert sha(src)==sha(dst)
 rows.append(dict(path=str(rel),bytes=dst.stat().st_size,sha256=sha(dst)))
# This is the exact owned marker from the failed, closed precompiler attempt.
# Keep its target, result and log unchanged; only remove the generated link.
assert marker.is_symlink() and marker.resolve()==R/'on/link-scratch'
marker.unlink()
assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True).strip()
(R/'SDK-SOURCE-READBACK.json').write_text(json.dumps(dict(source=str(S),destination=str(D),files=rows,resource_sha256=args.resources_sha256,failed_attempt_preserved=True,only_owned_marker_retired=True,build=False),indent=2)+'\n')
print(json.dumps(dict(copied=len(rows),logical_bytes=sum(x['bytes']for x in rows),source_clean=True,build=False)))
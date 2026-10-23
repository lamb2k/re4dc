from pathlib import Path
import fcntl,hashlib,json,subprocess
T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration');R=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration');O=R/'on2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lock=(R/'tree.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert sha(O/'PROOF-REPAIR-R1.json')=='3cbe35226d9dfcda10102c6bc87555a855602cef202376004ff376af87e85cc8'
marker=T/'port/dreamcast/game/obj';out=O/'FINAL-LITERAL-CLEAN.json'
assert not out.exists() and marker.is_symlink() and marker.resolve()==O/'link-scratch'
assert subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True)=='?? port/dreamcast/game/obj\n'
# Every generated input has an independently rehashable physical owner path.
entries=json.loads((O/'LINK-INPUT-MAPPING.json').read_bytes())['entries'];assert len(entries)==73
for row in entries:
 p=Path(row['retained_path']);assert p.stat().st_size==row['retained_bytes'] and sha(p)==row['retained_sha256']
marker.unlink()
assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True).strip()
head=subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip();assert head=='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
out.write_text(json.dumps(dict(source=head,clean=True,only_owned_generated_marker_retired=True,link_scratch_preserved=str(O/'link-scratch'),mapping_sha256=sha(O/'LINK-INPUT-MAPPING.json'),runtime_admitted=False),indent=2)+'\n')
print(dict(source=head,clean=True,objects_retained=73))
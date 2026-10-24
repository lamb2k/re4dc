from pathlib import Path
import hashlib,json,subprocess,sys
b=Path('/root/probe/rr-safe-boot-fb254e82-v3')
e=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024/bounded-console-boot-v3')
p=b/'ROOT-REVIEWED.json';cfg=json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
admission=json.loads((e/'ROOT-ADMISSION.json').read_text())
assert sha(p)==admission['approved_config_sha256'] and cfg['status']=='ROOT_REVIEWED_CURRENT_HEAD_INPUTS'
assert cfg['execution_authorized'] and cfg['admission']['release_priority_granted']
assert not (e/'ROOT-EXECUTION.json').exists() and not Path(cfg['lease_path']).exists()
helper=b/'capsule/capsule.py'
assert sha(b/'capsule/CAPSULE.json')==cfg['capsule_manifest_sha256']
commands=[('run',[sys.executable,'-B',str(helper),'hold',str(p),'--',*cfg['admission']['command']]),('bounds',[sys.executable,'-B',str(helper),'audit',str(p)]),('title',[sys.executable,'-B',str(helper),'judge-boot',str(p)])]
results={}
for name,command in commands:
    run=subprocess.run(command,capture_output=True,text=True)
    (e/f'root-{name}-stdout.txt').write_text(run.stdout)
    (e/f'root-{name}-stderr.txt').write_text(run.stderr)
    results[name]=dict(rc=run.returncode,stdout_sha256=sha(e/f'root-{name}-stdout.txt'),stderr_sha256=sha(e/f'root-{name}-stderr.txt'))
    print(name,'rc',run.returncode,run.stdout[-2000:],run.stderr[-2000:],flush=True)
    if run.returncode:break
    if name in ('bounds','title'):results[name]['decision']=json.loads(run.stdout)
passed=(set(results)=={'run','bounds','title'} and all(r['rc']==0 for r in results.values()) and results['bounds']['decision']['status']=='PLANNED_PROCESS_BOUNDS_COMPLETE' and results['title']['decision']['status']=='BOOT_TITLE_GOAL_PASS')
receipt=dict(status='PASS_BOUNDED_FINAL_GDI_TITLE_BOOT' if passed else 'FAIL_PRESERVED',config_sha256=sha(p),results=results,scope='One fresh current-candidate console title observation; no fresh full release/QA/route, hardware or performance claim.')
with (e/'ROOT-EXECUTION.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(0 if passed else 1)

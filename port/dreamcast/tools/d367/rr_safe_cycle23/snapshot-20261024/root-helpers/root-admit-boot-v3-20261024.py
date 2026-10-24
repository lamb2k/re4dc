from pathlib import Path
import datetime,hashlib,json,shutil,subprocess
root=Path(r'C:\Game Dev\Emulators\codex-lanes\rr-safe-cycle23')
b=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\rr-safe-boot-fb254e82-v3')
e=Path(r'C:\Flycast-Evidence\re4-dreamcast\rr-candidate-handback\fb254e82-20261024\bounded-console-boot-v3')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
pending=b/'ROOT-REVIEW-PENDING.json'
assert sha(pending)=='981d6f49363e4bb569ebcb6cef36b7c09f39ee9808b003fd6c0e5c9cc4099f0a'
review=root/'reviewd676/REVIEW-CLEAR.json'
assert sha(review)=='6e70bd83bade582ae98f1fc764e30f509759c42a84d6ea2794356a7f0825641c'
v3review=root/'reviewv3/REVIEW-CLEAR.json'
assert sha(v3review)=='a51ec528ad321af1a29453859da1f92032b88719d40657a17855e5c83430852f'
cfg=json.loads(pending.read_text())
assert cfg['status']=='ROOT-REVIEW-PENDING' and not cfg['execution_authorized']
assert cfg['adapter_source_commit']=='34a5c48bfe22c3d9718810166407048a906b8bcc'
assert cfg['source']=='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
assert cfg['profile']=='RR_FINAL_GDI_BOOT45_CHILD55_LIMITED_V2'
assert len(cfg['expected_runs'])==1 and len(cfg['input_pins'])==49
assert cfg['admission']['maximum_new_c_bytes']==3*1024**3
for path,digest in cfg['input_pins'].items():assert sha(path)==digest,path
cap=Path(next(iter(cfg['expected_runs'])))
assert not cap.exists() and not (b/'ROOT-BOOT-LEASE.json').exists()
manifest=json.loads((b/'capsule/CAPSULE.json').read_text())
assert sha(b/'capsule/CAPSULE.json')==cfg['capsule_manifest_sha256']
for rel,digest in manifest['files'].items():assert sha(b/'capsule'/rel)==digest,rel
guest_text=subprocess.check_output(['powershell.exe','-NoProfile','-Command',"@(Get-CimInstance Win32_Process -Filter \"name='flycast.exe' OR name='flycast-console.exe'\" | Select-Object ProcessId,ExecutablePath) | ConvertTo-Json -Compress"],text=True).strip()
guests=json.loads(guest_text) if guest_text else []
assert guests==[],guests
wsl=['wsl.exe','-d','Ubuntu-24.04','-u','root','--']
rr=subprocess.check_output(wsl+['bash','/root/rr/bin/rr.sh','status'],text=True)
assert 'cycle running: no' in rr and 'origin/t15/int: fb254e82' in rr
remote=subprocess.check_output(wsl+['git','-C','/root/work/lanes/dedup-offline23-land','ls-remote','origin','refs/heads/t15/int'],text=True).strip()
assert remote.split()[0]==cfg['source']
free=shutil.disk_usage('C:\\').free
assert free>=24*1024**3 and free>=20*1024**3+cfg['admission']['maximum_new_c_bytes']
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
approved=b/'ROOT-REVIEWED.json'
assert not approved.exists()
cfg['status']='ROOT_REVIEWED_CURRENT_HEAD_INPUTS'
cfg['execution_authorized']=True
cfg['config_windows']='//wsl.localhost/Ubuntu-24.04/root/probe/rr-safe-boot-fb254e82-v3/ROOT-REVIEWED.json'
cfg['lease_path']='/root/probe/rr-safe-boot-fb254e82-v3/ROOT-BOOT-ROOT-LEASE.json'
assert not Path(r'\\wsl.localhost\Ubuntu-24.04'+cfg['lease_path'].replace('/','\\')).exists()
cfg['admission']['release_priority_granted']=True
cfg['admission']['fresh_root_admission']=dict(utc=now,C_free_bytes=free,known_guests=guests,origin_head=remote.split()[0],legacy_rr_terminal=True,scope='One final-GDI boot only; no SDK, full cycle, metadata promotion, media staging or cleanup.')
cfg['root_review']=dict(independent_review_sha256=sha(review),pending_config_sha256=sha(pending),actual_pins_checked=49,capsule_members_checked=len(manifest['files']),programme='Exact retained current ELF/main/all14 and actual four-track hashes; logical1712-file/1697asset closure reuses the pinned full readback.',semantic_predicate='Require separate bounds audit AND title goal/grace/no error check; no full-route, release or physical claim.')
cfg['root_review']['v3_binding_review_sha256']=sha(v3review)
approved.write_text(json.dumps(cfg,indent=2)+'\n',newline='\n')
receipt=dict(status='ROOT_ADMITTED_SINGLE_BOOT_NOT_RUNTIME_ACCEPTANCE',utc=now,approved_config=str(approved),approved_config_sha256=sha(approved),C_free_bytes=free,input_pins_checked=49,capsule_members_checked=len(manifest['files']),review_sha256=sha(review),rr_status=rr)
with (e/'ROOT-ADMISSION.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt,indent=2))

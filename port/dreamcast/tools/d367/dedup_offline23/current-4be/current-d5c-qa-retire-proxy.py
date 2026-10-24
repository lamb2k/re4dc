"""Fresh final GDI readback and narrowly authorized new QA proxy backing retirement."""
from pathlib import Path
import fcntl,hashlib,json,os,shutil,subprocess,sys
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
T=Path('/root/work/lanes/dedup-offline23-qa-4be08e01/port/dreamcast/tools/d367')
arm=sys.argv[1];assert arm in ('off','on')
lock=open('/root/work/lanes/dedup-offline23-current-d5c-scratch/guest.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
m=json.loads((E/'qa-media-r1/pair-media-identity.json').read_text());x=m['arms'][arm]
gates={}
for kind in ('boot','warp','h2'):
 p=E/f'qa-{arm}-{kind}-console-r1/qa-gate.json';r=json.loads(p.read_text());assert r['status']=='PASS' and r['source']==m['source'];gates[kind]=sha(p)
final=Path(x['path'])/'gdemu'
for n,p in x['tracks'].items():assert (final/n).stat().st_size==p['bytes'] and sha(final/n)==p['sha256'],n
man=E/f'qa-media-r1/{arm}-final-post-manifest.json';assert not man.exists()
subprocess.run(['python3',str(T/'fullplay/fp_iso.py'),'manifest',str(final/'track03.bin'),'-o',str(man)],check=True,stdout=subprocess.DEVNULL)
assert json.loads(man.read_text())==json.loads(Path(x['manifest']).read_text())
base=E/f'qa-proxy-{arm}-r1';target=(base/'track03.iso').resolve()
assert target==E.resolve()/f'qa-proxy-{arm}-r1'/'track03.iso' and target.name=='track03.iso'
identity=json.loads((E/f'qa-proxy-{arm}-identity-r1.json').read_text())
assert target.is_file() and sha(target)==identity['track03_sha256'] and target.stat().st_nlink==1
# Only this arm's completed capture paths; do not touch or stop other lanes.
ps="Get-CimInstance Win32_Process -Filter \"Name='flycast.exe' OR Name='flycast-console.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
raw=subprocess.check_output(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',ps],text=True).strip()
procs=json.loads(raw) if raw else [];procs=procs if isinstance(procs,list) else [procs]
prefix=str(E).replace('/mnt/c/','C:/').replace('/','\\')+'\\qa-'+arm+'-'
assert not [p for p in procs if (p.get('ExecutablePath') or '').lower().startswith(prefix.lower())]
meta={str(p.relative_to(base)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in base.rglob('*') if p.is_file() and p!=target}
receipt=E/f'qa-{arm}-proxy-retirement-r1.json';assert not receipt.exists()
r=dict(status='AUTHORIZED_OWN_NEW_PROXY_BACKING_RETIREMENT',source=m['source'],arm=arm,resolved_target=str(target),bytes=target.stat().st_size,sha256=sha(target),nlink=target.stat().st_nlink,c_free_before=shutil.disk_usage('/mnt/c').free,arm_gates=gates,final_post_manifest_sha256=sha(man),all_final_tracks_full_readback_equal=True,proxy_metadata_retained=meta,owned_windows_guests_active=0,limits='Deletes only newly created exact owned proxy track03.iso after this arm boot/warp/H2 checks and fresh final GDI full readback. Final GDI, source/ELFs/overlays/IP/manifests/logs/caps/screens and all earlier media/evidence retained.')
receipt.write_text(json.dumps(r,indent=2)+'\n')
target.unlink()
assert not target.exists()
for n,p in meta.items():assert sha(base/n)==p['sha256']
r.update(status='REMOVED_ONLY_EXACT_AUTHORIZED_NEW_PROXY_BACKING',c_free_after=shutil.disk_usage('/mnt/c').free,target_absent=True)
receipt.write_text(json.dumps(r,indent=2)+'\n')
print('QA_PROXY_RETIRED_FINAL_READBACK_PASS',arm,r['bytes'],r['c_free_after'],flush=True)


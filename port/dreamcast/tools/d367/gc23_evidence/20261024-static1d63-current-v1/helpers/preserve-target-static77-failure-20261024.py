from pathlib import Path
import hashlib,json,datetime
own=Path(r'C:\Game Dev\Emulators\codex-lanes\gc-port23')
scratch=Path(r'\\wsl.localhost\Ubuntu-24.04\dev\shm\gc-port23-current-77d8a20b2-jx_x05a2')
dest=Path(r'C:\Flycast-Evidence\re4-dreamcast\gc-port23-20261023\target-static77-current-failure')
dest.mkdir(exist_ok=True)
items=['report.json','platform_native_static-on.log','platform_native_static-on-command.json','platform_native_static-on.d']
for name in items:
 p=scratch/name
 if p.is_file():(dest/name).write_bytes(p.read_bytes())
for name in ['static-target-current-20261024.py','static-target-current-20261024.sh','STATIC-TARGET-PREPARATION.json']:
 (dest/name).write_bytes((own/name).read_bytes())
report=json.loads((dest/'report.json').read_text())
receipt=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='TARGET_COMPILE_FAILED',source=report['source'],baseline=report['baseline'],profile=report['profile'],completed_objects=len(report['objects']),completed_off_comparisons=len(report['off_identity']),failure='native_static.cpp ON: RE4DC_SCENERY_DEDUP undeclared in gcasset_static_profile at line613',scratch=str(scratch),no_link_or_guest=True,preserved={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file() and p.name!='FAILURE.json'})
(dest/'FAILURE.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='preserved'},indent=2))
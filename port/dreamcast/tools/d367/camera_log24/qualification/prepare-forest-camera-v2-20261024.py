from pathlib import Path
import hashlib,json,re

own=Path(r'C:\Game Dev\Emulators\codex-lanes\dedup-offline23')
ev=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023\restrip23-fb254')
old=ev/'root-forest-camera'
new=ev/'root-forest-camera-v2'
new.mkdir(exist_ok=True)
assert not list(new.iterdir()), 'Do not overwrite prepared evidence'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=old/'capture-r1'
log=(run/'run-output.txt').read_text(errors='replace')
examples=[m[0] for m in re.finditer(r'PS2CAM f=79[0-9] cf=.*?vp=.*?(?=PS2CAM|warp:|\n)',log)]
assert examples and any('vp=' in x for x in examples)
pins={str(p.relative_to(old)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in old.rglob('*') if p.is_file() and p.suffix.lower() in ('.json','.png','.txt','.cfg')}
report=dict(status='REFUSED_FULL_CAMERA_V1',source='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',reason='Actual 256-byte logger truncates labelled rows near freeze tick800; viewport tail and newline are incomplete. No nibble completion or full-camera admission.',example=examples[0],bounded_console_observation=True,scope='Owned bounded Flycast capture and held presentation pictures remain evidence; full camera matrix is rejected.',pins=pins)
(old/'FULL-CAMERA-REFUSAL.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ('CAPTURE-HELPER-PINS.json','forest-camera-fixture.txt'):
    (new/name).write_bytes((old/name).read_bytes())
review=Path(r'C:\Game Dev\Emulators\codex-lanes\camera-log24\root-review-c2f0\REVIEW-CLEAR.json')
assert sha(review)=='d14e34dcaa45a6742d357fd76073e99a4603ad0317b91e7336c35b13648dc95d'
(new/'CAMERA-REVIEW-PIN.json').write_text(json.dumps(dict(source='c2f0d82e95050a708d0b977f94fad34890cbc279',review=str(review),sha256=sha(review),scope='Source/host review only; target identities and fresh full camera pending.'),indent=2)+'\n')
for kind in ('build','master','run'):
    src=own/f'forest-camera-{kind}-20261024.sh'
    text=src.read_text()
    text=text.replace('/root/work/lanes/dedup-offline23-land-scratch/forest-camera','/root/work/lanes/camera-log24-scratch/forest-camera')
    text=text.replace('/root/work/lanes/dedup-offline23-land','/root/work/lanes/camera-log24')
    text=text.replace('fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2','c2f0d82e95050a708d0b977f94fad34890cbc279')
    text=text.replace('rs24fb254cam','rs24c2f0cam')
    text=text.replace('/root-forest-camera','/root-forest-camera-v2')
    text=text.replace('forest-camera-build-20261024.sh','forest-camera-v2-build-20261024.sh')
    text=text.replace('capture-r1','capture-r2')
    (own/f'forest-camera-v2-{kind}-20261024.sh').write_text(text,newline='\n')
print('V1 full-camera rejected; V2 scripts and source-review pins prepared.')

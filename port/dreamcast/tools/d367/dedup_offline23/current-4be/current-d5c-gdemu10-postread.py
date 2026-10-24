from pathlib import Path
import hashlib,json
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
plan=json.loads((E/'gdemu10-plan-r1.json').read_text());report=json.loads((E/'gdemu10-gates-r1.json').read_text())
assert report['status']=='PASS_TEN_ACTUAL_CURRENT_GDEMU_SEEDS' and report['source']==plan['source']
assert sha(E/'base-standard-current4be-on-r1/track03.iso')==plan['track03_sha256']
fixtures={}
for row in report['runs']:
 p=Path(row['capture'])/'fixture-warp.txt';h=hashlib.sha256(p.read_bytes().replace(b'\r',b'')).hexdigest()
 assert h==plan['fixture_wire_sha256']
 fixtures[str(row['seed'])]=dict(path=str(p),wire_sha256=h)
out=E/'gdemu10-post-readback-r1.json';assert not out.exists()
out.write_text(json.dumps(dict(status='PASS_FINAL_FULL_TRACK_AND_ALL10_INJECTED_FIXTURES_READBACK',source=plan['source'],plan_sha256=sha(E/'gdemu10-plan-r1.json'),gates_sha256=sha(E/'gdemu10-gates-r1.json'),track03_sha256=plan['track03_sha256'],all10_fixtures=fixtures,limits='Final full shared-track and actual injected fixture-byte equality, supplementing captured env/profile/read/landing/endpoint checks; no physical-console claim.'),indent=2)+'\n')
print('GDEMU10_POST_READBACK_PASS')


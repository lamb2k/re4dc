"""Source preparation only: reads JSON/stat metadata; never opens an ISO/payload."""
from pathlib import Path
import hashlib,json,struct
E=Path(__file__).resolve().parent;C=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022');L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23');O=C/'actor23-10395a10-on-q01';N=C/'actor23-bea2d402-on-q01';B=L/'native-runtime10395/bound/on'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,pin):assert sha(p)==pin;return json.loads(p.read_text())
a=load(O/'media-receipt.json','ed7372629a35cf0d427cf2494dc003ddd98c75570dc9d44067614a7ab004d1af');b=load(N/'media-receipt.json','4ae6b825fc955c174c3747bdd17aed44e5d9a78ef3fe5ca6a499dd632232fb9f');prog=load(B/'programme.json','f832120fe836ccb86c30cd03535ba862be2425a64d8bd633b78433749cba97c9');mods=load(B/'modules.json','d2f05fb9eee8009b473f047074f9d6b3ffb2fb5a0bb39b8db3374667b24025cb');ip=Path('/root/probe/pvs23-package-20261022-v1/recovery-inverse-native-base-both/inverse-patches.json');inv=load(ip,'0931bebdffd6776ebb2b1a287a1a78661e2cf8d6ee306998ce708a3d61fb544b')
assert a['new_iso_bytes']==b['new_iso_bytes']==1028911104 and a['appended_payload_bytes']==b['appended_payload_bytes']==4257792
assert a['fixture_record_proof']==b['fixture_record_proof'] and a['original_iso_sha256']==b['original_iso_sha256']
assert a['private_room_proof']['private_room_sha256']==b['private_room_proof']['private_room_sha256']=='9338bd8530b4f45b3c6e891e584f37cc81e93242c4eaec9a0a6bfd7abeb3d22c'
assert len(a['mutations'])==len(b['mutations'])==16 and len(mods['modules'])==14
sources={x['package_path']:dict(path=x['path'],size=x['bytes'],sha256=x['sha256']) for x in mods['modules']};sources['1ST_READ.BIN']=dict(path=prog['raw']['path'],size=prog['raw']['bytes'],sha256=prog['raw']['sha256'])
patches=[];appends=[];payloads=[];inverse={x['offset']:x['before_hex'] for x in inv['patches']};cursor=1024653312
for old,new in zip(a['mutations'],b['mutations']):
 key=old['package_path'];assert key==new['package_path'] and old['new_lba']==new['new_lba'] and old['records_before']==new['records_before']
 size=old['identity']['size'];pad=(size+2047)//2048*2048;assert pad==(new['identity']['size']+2047)//2048*2048
 pos=(old['new_lba']-45000)*2048;assert pos==cursor;cursor+=pad
 appends.append(dict(package_path=key,offset=pos,size=size,padded_size=pad,old_sha256=old['identity']['sha256'],new_size=new['identity']['size'],new_sha256=new['identity']['sha256']))
 if key in sources:
  source=sources[key];assert source['size']==size and source['sha256']==old['identity']['sha256'];p=Path(source['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==size
  payloads.append(dict(package_path=key,offset=pos,padded_size=pad,**source))
 else:assert key=='dc/native/r119/room.r4rc' and old['identity']==new['identity']
 assert len(old['records_before'])==2
 for lba,off,extent,old_size in old['records_before']:
  assert 0<=off<=2048-34
  p=(lba-45000)*2048+off+2
  before=struct.pack('<I',new['new_lba'])+struct.pack('>I',new['new_lba'])+struct.pack('<I',new['identity']['size'])+struct.pack('>I',new['identity']['size'])
  after=struct.pack('<I',old['new_lba'])+struct.pack('>I',old['new_lba'])+struct.pack('<I',size)+struct.pack('>I',size)
  assert inverse[p]==after.hex()
  patches.append(dict(offset=p,before_hex=before.hex(),after_hex=after.hex(),package_path=key))
assert cursor==a['new_iso_bytes'] and len(patches)==32 and len(payloads)==15
for x in inv['patches']:
 if x['kind']=='original-volume-size':assert bytes.fromhex(x['before_hex'])==struct.pack('<I',a['new_iso_bytes']//2048)+struct.pack('>I',a['new_iso_bytes']//2048)
metadata=[O/'media-receipt.json',N/'media-receipt.json',B/'programme.json',B/'modules.json',ip,O/'stage-receipt.json',N/'stage-receipt.json',O/'extraction-receipt.json',N/'extraction-receipt.json']
plan=dict(status='SOURCE_ONLY_EXACT_CE034_RECONSTRUCTION_PENDING_EXECUTION',input=dict(path=str(N/'base/track03.iso'),size=b['new_iso_bytes'],sha256=b['final_iso_sha256']),target=dict(path=str(O/'base/track03.iso'),size=a['new_iso_bytes'],sha256=a['final_iso_sha256']),original_size=1024653312,payloads=payloads,appends=appends,point_patches=patches,metadata=[dict(path=str(p),size=p.stat().st_size,sha256=sha(p)) for p in metadata],private_room=dict(path='/root/probe/codex-actor-visibility23/actor23-r119-final/room.r4rc',size=40080,sha256=a['private_room_proof']['private_room_sha256']),unchanged_fixture_record_proof=a['fixture_record_proof'],descriptor_checks=[dict(offset=x['offset'],hex=x['before_hex']) for x in inv['patches'] if x['kind']=='original-volume-size'],source_input_preserved=True,physical_ce_restored=False)
p=E/'PLAN.json';assert not p.exists();p.write_text(json.dumps(plan,indent=2)+'\n');print('PLAN_SHA',sha(p));print('32pointtuples;15 payloads;same room/fixtures/length;targetpending. No ISO/payload opened.')

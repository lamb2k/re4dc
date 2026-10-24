#!/usr/bin/env python3
"""Prepare only new metadata recipes from current retained exact readback; no asset writes."""
from pathlib import Path
import hashlib,json
import resource,signal
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120)
ROOT=Path('/mnt/c/Game Dev/Emulators')
OUT=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-catalog-proof24-20261024/private-current-v1-inputs')
RR=Path('/root/rr/work/1023-2350-fb254e82/rel/manifest.json')
HAND=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024')
OLD=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-assets23/pkg-rre17af64rP.json')
PROPOSED=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/seed/reviewed-v1/reviewed-seed.json')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def read(path,pin=None):
 b=path.read_bytes()
 if pin:assert sha(b)==pin
 return json.loads(b),{'path':str(path),'bytes':len(b),'sha256':sha(b)}
assert not OUT.exists()
inspection,ip=read(HAND/'INSPECTION.json','d236b9d39f2d618d7c715f6d10c9d83bb10ebbabb7861b4064608a7ad7ecc447')
assert inspection['source']=='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2' and inspection['all1697_nonprogramme_asset_rows_equal_original'] is True
manifest,mp=read(RR);actual,ap=read(HAND/'full-readback-manifest.json');original,op=read(HAND/'original-release-manifest.json')
assert len(manifest)==len(actual)==len(original)==1712 and manifest==actual
assets={k:v for k,v in manifest.items() if k!='1ST_READ.BIN' and not k.endswith('.ovl')};assert len(assets)==1697
assert assets=={k:v for k,v in original.items() if k in assets}
pkg,pp=read(OLD,'c3eaa42015af9f1be44484f340006f03b1ccb7653ddc5ea2a457d6a1e65d0d37')
proposals,hp=read(PROPOSED,'117cb44162e1efa822e06db124cfa78dd5a60f0f5e7de7ec9958fd6c4af9274c')
assert len(proposals['entries'])==5763
assetraw=enc(assets)
providers=[{'provider':'texpak','asset':'dc/tex.pak','path':pkg['replace']['dc/tex.pak']}]
for name in sorted(k for k in assets if k.startswith('dc/tex/') and k.endswith('.re4tex')):
 assert name in pkg['replace'];providers.append({'provider':'file','asset':name,'path':pkg['replace'][name],'kind':'texture','id':Path(name).stem})
assert len(providers)==5
providers.append({'provider':'file','asset':'bgm/aica_str.dat','path':pkg['replace']['bgm/aica_str.dat'],'kind':'sound-stream','id':'aica-str-dat'})
selection={'schema':1,'manifest_sha256':sha(assetraw),'providers':providers}
receipt={'schema':1,'runtime_integration_base':'140a699f8ead7b406e76581de7075191acf77a96','selection_asset_authority':'Retained fb254 independent full1712 readback;1697asset rows exactly original release; no claim of current runtime accepted use.','input_pins':[ip,mp,ap,op,pp,hp],'selected_asset_rows':1697,'providers':providers,'positive_origin_proofs':None,'accepted_allowance_baseline':None,'historical_seed_role':'Unapproved historical load proposals only; never accepted ceiling.','production_pin':0,'asset_bytes_copied':False,'no_new_guest_or_stage':True}
OUT.mkdir(parents=True)
for name,raw in [('manifest-selected1697.json',assetraw),('selection.json',enc(selection)),('INPUT-RECEIPT.json',enc(receipt))]:(OUT/name).write_bytes(raw)
print(json.dumps({'inputs':str(OUT),'manifest_sha256':sha(assetraw),'selection_sha256':sha(enc(selection)),'receipt_sha256':sha(enc(receipt))},indent=2))
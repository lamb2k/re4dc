#!/usr/bin/env python3
"""Prepare a tiny reviewed mipmap23 overlay; never write a whole texture pack.

Reuses unchanged PR53 build_candidate on one-member archives in memory, then
writes only quality-passing .re4tex members. Selection stays pinned to this
source-reviewed item/truck unit. Private evidence and assets remain local.
"""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, struct, sys, zlib
HERE=Path(__file__).resolve().parent
TOOLS=HERE.parent
BASE_SHA='e45f7d6669798715e0edc8f5d88e15eee381d336855aa2a24626f14dcce48f96'
ITEMS={'494053fc-10003b8f','95e685c9-b3d27d88','15eb41ec-439f3753',
       '6596bca3-f2f292f2','83fef658-3fc6836e','ded04d98-82ec70ab',
       'e224e969-04254881','f52df17e-83f5bb15'}
MASKS={'2c9c252a-51c59944','56d70169-8a2e5214','bc5bb46e-c514110b',
       '4166aba4-23610a99','b2c170b7-c75b1acb','628a66ab-711d6b46'}
TRUCK='628a66ab-711d6b46'
MAX_BYTES=32*1024**2
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def fnv(b):
 f=2166136261
 for x in b:f=((f^x)*16777619)&0xffffffff
 return f
def pair(c,m):
 b=b'R4MPv001'+struct.pack('<4I',*c,*m)
 return '%08x-%08x'%(zlib.crc32(b)&0xffffffff,fnv(b))
def parts(b):
 n=struct.unpack_from('<H',b,26)[0];at=struct.unpack_from('<I',b,28)[0];rows=[]
 for i in range(n):
  h=b[at:at+32];size=struct.unpack_from('<I',h,24)[0]
  rows.append(dict(part=i,flags=h[11],tex=h[12],bump=h[13],alpha=h[14],
                   spec=h[15],alpha_ref=h[20],bytes=size))
  at+=32+size
 return rows
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--base-pack',type=Path,required=True)
 p.add_argument('--rr-package',type=Path,required=True)
 p.add_argument('--payload-root',type=Path,required=True)
 p.add_argument('--item-library',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 assert not a.out.exists(),'fresh private output required'
 cv=load(TOOLS/'texsrc22/convert.py','mipmap23_per_key_converter')
 sys.path.insert(0,str(TOOLS.parent));import ps2_items as pi
 blob=a.base_pack.read_bytes();assert sha(blob)==BASE_SHA
 stamp=a.base_pack.stat()
 cv.texpack.verify(blob);packages=cv.read_pak(blob);assert len(packages)==7299
 rrblob=a.rr_package.read_bytes();rr=json.loads(rrblob);files=rr['replace']
 resident=Path(files['dc/resident.bin']);rb=resident.read_bytes()
 preload=collections.defaultdict(list)
 for room,w,h,f,c,fn in struct.iter_unpack('<4H2I',rb):
  key='%08x-%08x'%(c,fn)
  if key in ITEMS|MASKS:
   preload[key].append(dict(room='r%03x'%room,width=w,height=h,flags=f))
 lib=a.item_library;mb=(lib/'manifest.json').read_bytes()
 tb=(lib/'tex/tex.json').read_bytes()
 manifest=json.loads(mb);tex={r['key']:r for r in json.loads(tb)}
 carriers={};carrier_cache={}
 def carrier(logical):
  path=Path(files.get(logical,str(a.payload_root/logical)))
  b=path.read_bytes()
  carriers[logical]=dict(path=str(path),bytes=len(b),sha256=sha(b))
  return b
 def current_asset(asset):
  loc=asset['locator']
  if loc['kind']=='ITM':
   logical='st1/'+asset['room']+'.dar'
   if logical not in carrier_cache:
    pay,_=pi.payload_of(carrier(logical))
    tag,s,e=next(x for x in pi.rs.tagged_entries(bytes(pay),'<') if x[0]==b'ITM\0')
    carrier_cache[logical]=pi.itm_assets(pay[s:e],'<')
   b,t=carrier_cache[logical][loc['id']]
  else:
   assert loc['kind']=='SS'
   logical=loc['file']
   b=carrier(logical+'.bin');t=carrier(logical+'.tpl')
  expected=(lib/asset['room']/asset['bin']).read_bytes()
  assert b[:len(expected)]==expected,('current model differs',logical,asset['name'])
  assert sha(expected)==asset['bin_sha256']
  return b,t,logical
 def ref(t,im,k):
  record=struct.unpack_from('<8s6I',t,im['data'])
  if record[0]==b'R4NREF\0\0':
   assert record[1:3]==cv.key_tuple(k)
   assert record[3:6]==(64,64,14)
   mode='external R4NREF'
  else:
   assert (im['w'],im['h'],im['fmt'])==(64,64,14)
   raw=t[im['data']:im['data']+2048]
   assert len(raw)==2048 and pi.identity_key(64,64,14,raw)==k,('inline current identity differs',k)
   mode='inline CMPR image identity'
  return dict(offset=im['data'],key=k,mode=mode,wrap=struct.unpack_from('<2I',t,im['hdr']+12))
 evidence={}
 for key in sorted(ITEMS):
  original=packages[cv.key_tuple(key)]
  library_package=(lib/'tex'/(key+'.re4tex')).read_bytes()
  assert sha(library_package)==tex[key]['sha256']
  inherited_vq={'6596bca3-f2f292f2','e224e969-04254881','f52df17e-83f5bb15'}
  if original!=library_package:
   # The sealed current pack already carries VQ versions of these historical
   # twiddled pairs. Keep the current base; never silently restore library bytes.
   assert key in inherited_vq
   ck,cn,*_=cv.identify(original);lk,ln,*_=cv.identify(library_package)
   assert ck=='vq' and lk=='twiddled' and cn.size==ln.size==64
   assert cn.texture[0:5]==ln.texture[0:5] and cn.texture[3]==2
  uses=[]
  for asset in manifest['assets']:
   swaps=[s for s in asset.get('swaps',[]) if s.get('key')==key]
   pairs=[s for s in asset.get('pairs',[]) if s.get('key')==key]
   if not swaps and not pairs:continue
   assert asset['status']=='PS2' and asset['geometry']=='ps2'
   b,t,logical=current_asset(asset);ps=parts(b);images=pi.gc_tpl_images(t,'<')
   checks=[]
   for s in swaps:
    matched=[r for r in ps if r['bytes'] and r['tex']==s['j'] and not r['flags']&4]
    assert matched,('no current unmasked base use',key,logical)
    assert all(not r['flags']&1 or r['bump']!=s['j'] for r in matched)
    checks.append(dict(role='base-colour; distinct bump input',parts=matched,
                       reference=ref(t,images[s['j']],key)))
   for s in pairs:
    assert pair(cv.key_tuple(s['color_key']),cv.key_tuple(s['mask_key']))==key
    matched=[r for r in ps if r['bytes'] and r['flags']&4 and
             r['tex']==s['color'] and r['alpha']==s['mask']]
    assert matched and all(r['alpha_ref']==0 for r in matched)
    cr=ref(t,images[s['color']],s['color_key'])
    mr=ref(t,images[s['mask']],s['mask_key'])
    assert cr['wrap']==mr['wrap']
    checks.append(dict(role='same-size same-wrap alpha pair; source alphaRef zero',
                       parts=matched,colour=cr,mask=mr))
   uses.append(dict(room=asset['room'],name=asset['name'],carrier=logical,
       current_model_prefix_exact=True,bin_sha256=asset['bin_sha256'],
       ps2_bin_sha256=asset['ps2_bin_sha256'],ps2_tpl_sha256=asset['ps2_tpl_sha256'],
       checks=checks))
  assert uses and preload[key]
  evidence[key]=dict(kind='ps2-item',uses=uses,preloads=preload[key],
      historical_library_package_sha256=tex[key]['sha256'],
      current_package_sha256=sha(original),
      historical_package_exact=original==library_package,
      lineage_note='Current sealed pack base preserved, including three inherited VQ alpha pairs; historical PS2 library establishes source role, not current byte identity.')
 # Resolve only the six remaining mask candidates in their positive resident rooms.
 mask_bindings=collections.defaultdict(list)
 rooms={r['room'] for key in MASKS for r in preload[key]}
 for logical,path in files.items():
  if not logical.endswith('.re4nmr') or not any('/'+r+'/' in logical for r in rooms):continue
  b=Path(path).read_bytes()
  def sec(i):return struct.unpack_from('<4I',b,64+16*i)[1:]
  ta,_,tn=sec(4);ra,_,rn=sec(1);da,_,dn=sec(0)
  tx=[struct.unpack_from('<4I',b,ta+16*i) for i in range(tn)]
  for d in range(dn):
   at=da+48*d;name=b[at:at+16].split(b'\0')[0].decode()
   app,mid,bones,n,first,*_=struct.unpack_from('<8I',b,at+16)
   for i in range(first,first+n):
    g,t,owner,mw=struct.unpack_from('<4I',b,ra+16*i)
    direct='%08x-%08x'%tx[t][:2]
    if direct in MASKS:
     mask_bindings[direct].append(dict(kind='direct',logical=logical,descriptor=name,ref=i-first))
    if not mw:continue
    tc=(mw>>16)&255;tm=mw>>24
    key=pair(tx[tc][:2],tx[tm][:2])
    if key in MASKS:
     assert tx[tc][2:]==tx[tm][2:]
     mask_bindings[key].append(dict(kind='native-pair-run',logical=logical,path=path,
       package_sha256=sha(b),descriptor=name,appearance=app,model_id=mid,ref=i-first,
       mask_word=mw,colour=tx[tc],mask=tx[tm],
       sampler='material_flags4 blend0 depth_mode1 mask_ref0 same_uv1 wrap1/1; TR alpha enabled; bilinear mip header'))
 assert len(mask_bindings[TRUCK])==1 and mask_bindings[TRUCK][0]['descriptor']=='truck-em3b-00'
 for key in sorted(MASKS):
  if not mask_bindings[key]:continue
  assert all(r['kind']=='native-pair-run' and
      (r['descriptor'].startswith('ashley11') or r['descriptor']=='truck-em3b-00')
      for r in mask_bindings[key]), 'new current mask consumer needs separate review'
  evidence[key]=dict(kind='ps2-mask',bindings=mask_bindings[key],preloads=preload[key])
 assert set(evidence)-ITEMS=={'2c9c252a-51c59944','56d70169-8a2e5214','bc5bb46e-c514110b',TRUCK}
 gate_path=TOOLS/'mipmap21/mip_quality.py';holds=TOOLS/'mipmap22/room-select.tsv'
 gate_bytes=gate_path.read_bytes();hold_bytes=holds.read_bytes()
 assert not set(evidence).intersection(cv.hold_keys(hold_bytes))
 gate=cv.load_gate(gate_path,sha(gate_bytes));gate.HOLD_KEYS.clear()
 gate.HOLD_KEYS.update(cv.hold_keys(hold_bytes))
 source_paths=['game/model_bridge.cpp','game/platform/native_ui.cpp','room/texture_package.cpp',
               'game/coarse_actor_owner_registry.inc','game/coarse_actor_registry_pack_check.inc']
 sources={p:sha((HERE.parents[2]/p).read_bytes()) for p in source_paths}
 repo=HERE.parents[4]
 for p in ['src/game/trans.cpp','include/model.h']:
  sources[p]=sha((repo/p).read_bytes())
 a.out.mkdir(parents=True);outrows=[];reports=[]
 # One serial conversion job, one reviewed member in memory at a time.
 for key in sorted(evidence):
  k=cv.key_tuple(key);original=packages[k]
  mini=cv.texpack.build({k:original})[0]
  selection=dict(schema=cv.SCHEMA,base_pack_sha256=sha(mini),
      quality_gate_sha256=sha(gate_bytes),hold_keys_sha256=sha(hold_bytes),approved_keys=[key])
  generated,report=cv.build_candidate(mini,enabled=True,selection=selection,
      gate_path=gate_path,hold_bytes=hold_bytes)
  result=cv.read_pak(generated)[k]
  kind,bn,decode,generate,base=cv.identify(original)
  _,an,_,_,_=cv.identify(result)
  assert base(bn)==base(an) and decode(bn,bn.size)==decode(an,an.size)
  row=report['rows'][0];levels=[]
  if row['changed']:
   cv.unchanged_base(bn,an,decode,base)
   _,audit,held=gate.audit((k,result))
   assert audit==row['quality'] and audit['verdict']=='pass' and held is None
   for side in [bn.size>>i for i in range(1,bn.size.bit_length())]:
    px=decode(an,side)
    levels.append(dict(side=side,rgba_sha256=sha(bytes(c for p in px for c in p)),
        alpha_histogram=dict(sorted(collections.Counter(p[3] for p in px).items()))))
   assert levels[-1]['side']==1
   target=a.out/'tex'/(key+'.re4tex');target.parent.mkdir(exist_ok=True)
   target.write_bytes(result)
   assert target.read_bytes()==result
  else:
   assert row['verdict']=='held' and result==original
  outrows.append(dict(key=key,verdict=row['verdict'],reasons=row['reasons'],
      source_package_sha256=sha(original),output_package_sha256=sha(result),
      base_payload_exact=True,base_pixels_exact=True,levels=levels,
      extra_payload_bytes=row['extra_payload_bytes'],extra_alloc32_bytes=row['extra_alloc32_bytes'],
      evidence=evidence[key],per_key_archive_sha256=sha(mini)))
  reports.append(dict(key=key,selection=selection,conversion=report))
  assert sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file())<MAX_BYTES//2
 # The original combined archive and current shared tables are read back immutable.
 assert sha(a.base_pack.read_bytes())==BASE_SHA
 assert a.base_pack.stat().st_mtime_ns==stamp.st_mtime_ns
 assert a.rr_package.read_bytes()==rrblob and resident.read_bytes()==rb
 result=dict(schema='re4dc-mipmap23-per-key-qualification-1',scope='source/host/package only',
   base_pack=str(a.base_pack),base_pack_sha256=BASE_SHA,base_pack_bytes=len(blob),
   source_members=len(packages),base_pack_unchanged=True,
   rr_package=str(a.rr_package),rr_package_sha256=sha(rrblob),
   resident=str(resident),resident_sha256=sha(rb),
   item_manifest_sha256=sha(mb),item_tex_manifest_sha256=sha(tb),carriers=carriers,
   selected=len(outrows),accepted=sum(r['verdict']=='pass' for r in outrows),
   held=sum(r['verdict']=='held' for r in outrows),rows=outrows,
   mask_consumer_held={k:dict(reason='positive preload; selected registry and partner packages do not bind key directly or as derived pair; resolve another consumer before conversion',preloads=preload[k]) for k in sorted(MASKS) if not mask_bindings[k]},
   runtime_source_sha256=sources,quality_gate_sha256=sha(gate_bytes),
   hold_manifest_sha256=sha(hold_bytes),full_pack_output='none',
   all_prior_eight_and_shared_and_colour_held='immutable input; no whole-pack mutation or output',
   limits=['Candidate overlay only; main owns any pack assembly/staging.',
           'No guest sampler/minification, visual, VRAM fit/peak, re-entry or physical acceptance.',
           'Bump/specular implementation is not added or certified by mip compatibility.',
           'Dynamic alpha_ref/UV policies still pass existing runtime checks; no broad source-fidelity claim.'])
 for name,data in [('qualification.json',result),('conversion-reports.json',reports)]:
  (a.out/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
 assert sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file())<MAX_BYTES//2
 print(json.dumps(dict(selected=result['selected'],accepted=result['accepted'],held=result['held'],
  results=[{k:r[k] for k in ('key','verdict','reasons','extra_alloc32_bytes')} for r in outrows],
  mask_consumers_held=len(result['mask_consumer_held'])),indent=2))
if __name__=='__main__':main()

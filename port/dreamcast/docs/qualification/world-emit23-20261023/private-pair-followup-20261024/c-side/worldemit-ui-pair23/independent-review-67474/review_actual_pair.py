#!/usr/bin/env python3
"""Read-only actual-member audit; no asset/output generation on disk."""
import pathlib,sys,json,struct,hashlib,zlib,copy
from unittest import mock
ROOT=pathlib.Path('/root/probe/worldemit-ui-pair23')
TOOLS=ROOT/'port/dreamcast/tools'
sys.path.insert(0,str(TOOLS/'d367/worldemit_ui_pair23'))
import prepare_pair as p
ISO=pathlib.Path('/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso')
CAND=pathlib.Path('/mnt/c/Game Dev/Emulators/re4-assets-private/worldemit-ui-pair23-20261023-v2')
OUT=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/worldemit-ui-pair23/independent-review-67474')
index=p.pb.afs_index(ISO);assert index['em35.dat']==(1425610752,3727616)
raw=p.pb.afs_read(ISO,'em35.dat',index)
# Fail immediately if any GX pixel path is invoked, even in actual-member audit.
with mock.patch.object(p.ct,'decode_image',side_effect=AssertionError('no GX pixel decoder allowed')):
 report,blob,decoded,pixels=p.audit(raw)
assert p.sha(blob)=='18978dc1b97247dcd5fda5f5f1744b74e9d1b97c34dc5779977525b0a2dc477e'
# Independent archive/member/material extraction using literal container fields.
n=struct.unpack_from('<I',raw)[0];offsets=struct.unpack_from('<%dI'%n,raw,16)
materials={}
for arc in (4,6,7,8):
 i=arc-4;start=offsets[i];end=min([v for v in offsets if v>start]+[len(raw)])
 tag=raw[16+4*n+4*i:20+4*n+4*i].rstrip(b'\0');assert tag==b'BIN'
 data=raw[start:end];count=struct.unpack_from('<H',data,10)[0];base=struct.unpack_from('<I',data,12)[0]
 rows=[data[base+j*16:base+(j+1)*16] for j in range(count)]
 masked=[(j,row) for j,row in enumerate(rows) if row[0]&4]
 if arc in (4,7):
  assert len(masked)==1 and masked[0][0]==13 and tuple(masked[0][1][k] for k in (0,1,3))==(4,0,1)
 else:assert not masked
 materials[str(arc)]=dict(bin_sha256=p.sha(data),material_count=count,masked_indices=[j for j,_ in masked])
h=p.ct.HEADER.unpack_from(blob);row=p.ct.TEXTURE.unpack_from(blob,h[5]);assert h[4]==1
assert (row[1],row[2],row[3],row[5],row[6],row[7],row[8])==(128,128,2,32768,1,1,0)
assert zlib.crc32(blob[h[2]:])&0xffffffff==h[8]
words=struct.unpack_from('<16384H',blob,row[4]);alphas=set()
for y in range(128):
 for x in range(128):
  flat=y*128+x;off=flat*4;r,g,b=decoded[0][off:off+3];mask=decoded[1][off];assert decoded[1][off:off+3]==bytes([mask])*3 and mask%16==0
  expected=((mask//16)<<12)|((r>>4)<<8)|((g>>4)<<4)|(b>>4)
  morton=sum(((y>>k)&1)<<(2*k) | ((x>>k)&1)<<(2*k+1) for k in range(7))
  assert words[morton]==expected,(x,y);alphas.add(expected>>12)
assert len(alphas)>2
negative=[]
def refuse(name,call,pattern):
 try:call()
 except ValueError as e:assert pattern in str(e);negative.append(dict(name=name,refused=str(e)))
 else:raise AssertionError(name+' admitted')
corrupt=bytearray(raw);corrupt[-1]^=1
refuse('actual member one-byte mutation',lambda:p.audit(corrupt),'identity')
real_decode=p.td.decode
def disagree(tpl,desc,swizzle='gs',**kwargs):
 w,ht,rgba,stats=real_decode(tpl,desc,swizzle=swizzle,**kwargs)
 if swizzle=='jl' and desc['header_off']==64:rgba=bytearray(rgba);rgba[0]^=16
 return w,ht,rgba,stats
with mock.patch.object(p.td,'decode',side_effect=disagree):refuse('actual mask JL disagreement',lambda:p.audit(raw),'disagreement')
with mock.patch.object(p,'KEY','00000000-00000000'):refuse('wrong runtime pair key',lambda:p.audit(raw),'key mismatch')
entries=list(p.pb.dat_entries(raw));altered=[]
for i,tag,data in entries:
 if i==1:data=bytearray(data);data[-1]^=1
 altered.append((i,tag,data))
with mock.patch.object(p.pb,'dat_entries',return_value=altered):refuse('wrong exact TPL bytes',lambda:p.audit(raw),'TPL5 identity')
manifest=json.loads((CAND/'local-pack.json').read_text());assert set(manifest['replace'])=={'dc/tex/7/'+p.KEY+'.re4tex'}
assert manifest['default']==0 and manifest['production_enabled'] is False
actual=(CAND/'files/dc/tex/7'/(p.KEY+'.re4tex')).read_bytes();assert actual==blob
candidate=json.loads((CAND/'candidate.json').read_text());assert candidate['package']==report['package']
assert candidate['production_enabled'] is False and candidate['runtime_qualified'] is False and candidate['look_approved'] is False
receipt=json.loads(pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/worldemit-ui-pair23/RECEIPT.json').read_text())
for rel,pin in receipt['candidate_files'].items():
 data=(CAND/rel).read_bytes();assert len(data)==pin['bytes'] and p.sha(data)==pin['sha256']
result=dict(source='67474ea4b1dd01b0d47e2f80c0e9b58103a7f86d',actual_member=dict(offset=index['em35.dat'][0],bytes=len(raw),sha256=p.sha(raw)),materials=materials,
 package=report['package'],independent_twiddle_argb4444_texels=16384,alpha_nibbles=sorted(alphas),negatives=negative,
 gx_decoder_forbidden_actual_audit=True,exactly_one_manifest_replacement=True,all_candidate_receipt_files_verified=True,
 no_disk_asset_generation=True,private_preview_only=True)
(OUT/'independent-controls.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

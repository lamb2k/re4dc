#!/usr/bin/env python3
"""Verify one pinned r111 conversion-policy migration, never fuzzy equality.

The current policy supplies every affine used by later geometry proofs. This
receipt proves unchanged mesh/material/source-owner identities and quantifies
an older conversion's tiny affine differences with exact rational arithmetic.
It does not admit a table or claim old/new policies are byte-identical.
"""
import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import zlib

EXPECTED={
 'mesh':'bf552dcf8a561e5f94f0d5bebbcc344fdc5bf63e3f5e1c2b617d4f5341bc08d9',
 'report':'bf6f9d74ffd8683a2a29eae048db09e38ac0bdb0eb6b4ef5bad309773ca1dfec',
 'old_policy':'4dc17559e039530db55d6af0f51a85295166052b545dfe36d0e4f054167851d3',
 'original_policy':'e64301ebc3f212a47257b18da246ddbac317f0b82f039943cb9c22f86c74760d',
 'current_policy':'569158227cb2ac9419857c81f476f32587ea668d5f19a234ed320bd3563c025c',
 'old_ids':'6c8415e1abaf7407632bc906144c0b1b21b18a7376ad241afbcf6f4eca00c1d5',
 'ids':'3b2bf77cf5f187c61ce8ab7c57d524cc5ec2526df15c6a0b50b35f8b0109d2e7',
 'iso_receipt':'d5ceded2c6e7b16ed261ac7f51e31468b528506538e3a516089b244f8467fe94'}
ISO='23b02efeb438cd7cc097de7a1ce3924175e7d1aef10efafd9cd7a25715961bc1'

def digest(b):return hashlib.sha256(b).hexdigest()

def policy(b):
 h=struct.unpack_from('<4s7I',b);assert h[:2]==(b'R4PW',1)
 assert h[5]==zlib.crc32(b[32:]);n,parts=h[2:4];base=32+16*parts
 assert len(b)==base+52*n
 rows=[struct.unpack_from('<HH12f',b,base+52*i) for i in range(n)]
 return h,n,parts,base,rows

def normalized_keys(b,parts):
 b=bytearray(b);b[20:24]=bytes(4)
 for part in range(parts):b[32+part*16:40+part*16]=bytes(8)
 return bytes(b)

def verify(old_dir,original_dir,current_dir,iso_receipt):
 sources={
  'report':old_dir/'ps2-world.json','old_policy':old_dir/'ps2-world.r4pw',
  'old_ids':old_dir/'ps2-world.ids','original_policy':original_dir/'ps2-world.r4pw',
  'ids':original_dir/'ps2-world.ids','current_policy':current_dir/'ps2-world.r4pw',
  'mesh':current_dir/'ps2-world.re4mesh','iso_receipt':iso_receipt}
 data={k:p.read_bytes() for k,p in sources.items()}
 for k,b in data.items():assert digest(b)==EXPECTED[k],f'unreviewed {k} bytes'
 for folder in (old_dir,original_dir):assert digest((folder/'ps2-world.re4mesh').read_bytes())==EXPECTED['mesh']
 assert (current_dir/'ps2-world.ids').read_bytes()==data['ids']
 report=json.loads(data['report']);assert report['room']=='r111' and report['placements']==report['groups']==205
 assert report['re4mesh_sha256']==EXPECTED['mesh'] and report['r4pw_sha256']==EXPECTED['old_policy']
 a,b,c=(data[k] for k in ('old_policy','original_policy','current_policy'))
 ah,n,parts,base,ar=policy(a);bh,bn,bp,bb,br=policy(b);ch,cn,cp,cb,cr=policy(c)
 assert (n,parts,base)==(bn,bp,bb)==(cn,cp,cb)==(205,305,4912)
 assert normalized_keys(b,parts)==normalized_keys(c,parts),'current physical policy changed outside texture keys/CRC'
 for ids_blob,crc in ((data['old_ids'],ah[5]),(data['ids'],bh[5])):
  assert struct.unpack_from('<4sIII',ids_blob)==(b'R4ID',1,n,crc)
 assert data['old_ids'][:12]+data['old_ids'][16:]==data['ids'][:12]+data['ids'][16:],'owner ID bytes changed'
 assert a[:20]+a[24:base]==b[:20]+b[24:base],'geometry/material header or part policy changed'
 assert all(x[:2]==y[:2] for x,y in zip(ar,br)),'placement mesh/field owner changed'
 assert br==cr,'current proof must use exact original placement affines'
 # Pin the saved ISO membership receipt; the large raw ISO is not re-read.
 iso=json.loads(data['iso_receipt']);membership={}
 for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):
  key='dc/native/r111/'+name;entry=iso[key]
  assert entry[0].replace('\\','/').endswith('/'+ISO+'/track03.iso')
  assert entry[1]=='DC/NATIVE/R111/'+name.upper().replace('PS2-WORLD','PS2_WORLD')
  membership[key]=entry
 mh=struct.unpack_from('<4s15I4I',data['mesh']);assert mh[:2]==(b'R4IM',3)
 assert mh[2]==len(data['mesh']) and mh[3]==zlib.crc32(data['mesh'][80:])
 changes=[];worst=F(0)
 for i,(old,new) in enumerate(zip(ar,br)):
  if old==new:continue
  mesh=struct.unpack_from('<HBBHHIII12f',data['mesh'],mh[10]+68*new[0])
  # Every decoded vertex at every LOD has uint16 q in [0,65535]. Use the
  # entire quantization cube rather than assuming a tighter header bound.
  bounds=[(F(mesh[8+j]),F(mesh[8+j])+65535*F(mesh[11+j])) for j in range(3)]
  extrema=[]
  for row in range(3):
   delta=[F(new[2+4*row+j])-F(old[2+4*row+j]) for j in range(4)]
   maximum=max(abs(sum(delta[j]*q[j] for j in range(3))+delta[3]) for q in itertools.product(*bounds))
   extrema.append(maximum);worst=max(worst,maximum)
  raw_a=a[base+52*i:base+52*(i+1)];raw_b=b[base+52*i:base+52*(i+1)]
  changes.append(dict(placement=i,mesh=new[0],field=new[1],owner_id=data['ids'][16+new[1]],
   affine_old=list(old[2:]),affine_current=list(new[2:]),
   coefficients=[dict(row=j//4,column=j%4,old_bits=f'{struct.unpack_from("<I",raw_a,4+4*j)[0]:08x}',current_bits=f'{struct.unpack_from("<I",raw_b,4+4*j)[0]:08x}') for j in range(12) if old[j+2]!=new[j+2]],
   max_coordinate_displacement_mm=[dict(numerator=x.numerator,denominator=x.denominator,upper=math.nextafter(float(x),math.inf)) for x in extrema]))
 assert [x['placement'] for x in changes]==[22,24,83]
 upper=math.nextafter(float(worst),math.inf);assert worst<F(32)
 diffs=[dict(offset=i,old=x,current=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
 assert len(diffs)==12
 return dict(kind='exact pinned r111 policy migration; independent review required before preparation',runtime_admitted=False,
  policy_equal=False,mesh_material_owner_identity_equal=True,proof_uses_exact_current_affines=True,
  source_inputs={k:dict(path=str(sources[k]),sha256=digest(v),bytes=len(v)) for k,v in data.items()},
  iso_membership_receipt=membership,raw_iso_reread=False,placements=n,parts=parts,
  byte_differences=diffs,changed_placements=changes,worst_coordinate_displacement_mm_upper=upper,
  uncertainty_budget_mm=32,displacement_fraction_of_budget_upper=math.nextafter(upper/32,math.inf),
  tool_sha256=digest(Path(__file__).read_bytes()),
  limitation='Source identity/geometry provenance only; continuous proofs and all runtime state/material/numeric/receipt guards remain separate.')

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('old','original','current','iso-receipt','out'):ap.add_argument('--'+name,type=Path,required=True)
 args=ap.parse_args();out=verify(args.old,args.original,args.current,args.iso_receipt)
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:out[k] for k in ('kind','runtime_admitted','worst_coordinate_displacement_mm_upper','displacement_fraction_of_budget_upper')}))

if __name__=='__main__':main()

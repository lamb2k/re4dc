#!/usr/bin/env python3
"""Source-only18 TWID append delta on frozen1600. No archive/image/runtime writer."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
import immutable_append1600_writer as parent
from plan_append1596 import layout,scoped,seal,emit,file_sha
from extend_append1600 import shifts

WRITER_SHA='53015865a712cc061cbb29206d316135a3e0d1f609788083b070b06440570b1a'
TWID_SEAL='21b8650a3dfd80d8c6fc2c8e7b0f6fc278a88ce85b7e2db40dd5487dde788b4c'
COVERAGE_SHA='f1c83ea0af2bcbe55a96ac01cd11090c3adbc3058482c0a37dacb3dcc1dea450'
HELPERS={'plan_append1596.py':'10d4d29ba00df46fc93727e0397169059950656429e4da6414a039ae74c8aa29','extend_append1600.py':'0fada7e3c09658f92f9d7344e025e2ce981ebc1e3b342fec27cdea67a953fd91'}
def twid_candidate(blob,r):
 if hashlib.sha256(blob).hexdigest()!=r['candidate_sha256']or len(blob)!=r['package_bytes']:raise ValueError('TWID package SHA/extent')
 h=struct.unpack_from('<8s10I',blob);t=struct.unpack_from('<64s8I',blob,48)
 if h[:7]!=(b'RE4DCTX\0',2,48,96,1,48,144)or h[9:]!=(1,0):raise ValueError('TWID header/source_image_count1/flags0')
 if t[1:]!=(16,16,0,144,688,4,1,0):raise ValueError('opaque16 RGB565 complete TWID mip descriptor')
 if h[7]!=688 or len(blob)!=832 or h[8]!=r['candidate_crc32']or h[8]!=zlib.crc32(blob[48:])&0xffffffff:raise ValueError('TWID canonical descriptor+payload bodyCRC')
 if r['logical']not in([32,16],[64,16])or r['physical']!=[16,16]or r['uv_scale']!=[1.,1.]or(r['format'],r['flags'],r['payload_type'],r['candidate_payload'])!=(0,4,1,688)or r['decoded_levels']!=[1,2,4,8,16]or r['source_codebook_present']is not False:raise ValueError('sealed18 TWID representation contract')
 if scoped(r['original_key'],r['candidate_sha256'])!=r['scoped_key']:raise ValueError('immutable scoped namespace')
 return dict(body_crc32=h[8],descriptor_hex=blob[48:144].hex(),physical=[16,16],payload=688,payload_type=1,format=0,mip_levels=5)

def inputs(frozen_plan,twid,coverage):
 if file_sha(Path(parent.__file__))!=WRITER_SHA:raise ValueError('frozen1600 writer changed')
 for n,h in HELPERS.items():
  if file_sha(Path(__file__).parent/n)!=h:raise ValueError('frozen layout/offset helper changed')
 fp=json.loads(frozen_plan.read_text())
 if set(fp['source_sha256'])!=parent.DEPENDENCIES:raise ValueError('frozen parent dependencies')
 for n,h in fp['source_sha256'].items():
  if file_sha(Path(parent.__file__).parent/n)!=h:raise ValueError('parent source pin changed')
 ph,pi,prior=parent.resolve(fp);seal(twid,TWID_SEAL)
 receipt=json.loads((twid/'conversion-receipt.json').read_text());host=json.loads((twid/'host-gate.json').read_text());summary=json.loads((twid/'summary.json').read_text())
 if file_sha(coverage)!=COVERAGE_SHA or receipt['coverage_sha256']!=COVERAGE_SHA:raise ValueError('exact retained collision coverage')
 if len(receipt['selected'])!=18 or receipt['held']or receipt['canonical1004_preserved']!='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62':raise ValueError('18selected canonical parent')
 if(host['status'],host['positive_cases'],host['strict_adopt_and_stream_CRC1'],host['twiddled_OFF_rejects'],host['corrupt_rejects'],host['PVR_format_bit31'],host['PVR_VQ_bit30'])!=('PASS_TWID_PACKAGE_AND_SOURCE_WORLD_BINDING_HOST_ONLY',18,True,18,3,True,False):raise ValueError('actual Package/source host qualification')
 if summary['producer_commit']!='7eeecd40c5edd1f5b7de20bd780f11cd267a758e'or summary['independent_C_mip_levels']!=90 or summary['material_refs']!=119:raise ValueError('producer identity/counts')
 rows={r['key']:r for r in prior};occupied=set(rows)|{r['key']for r in json.loads(coverage.read_text())['loose_and_quality_rows']}|{'3662c0aa-c9e71c00','fefdf580-f15c1f47'}
 p1596=parent.local(fp['parent1596']);d1600=parent.local(fp['delta1600']);originals={r['original_key']for f in[p1596/'plan/APPENDED-592.json',d1600/'plan/APPENDED-4.json']for r in json.loads(f.read_text())};added=[]
 for r in receipt['selected']:
  key=r['scoped_key'];rel=Path(r['relative_path'])
  if key in occupied or r['original_key']in originals or rel.as_posix()!='textures/'+key+'.re4tex':raise ValueError('collision/source cohort/path')
  occupied.add(key);originals.add(r['original_key']);path=parent.safe_path(twid/rel,twid);blob=path.read_bytes();c=twid_candidate(blob,r)
  row=dict(key=key,bytes=len(blob),sha256=r['candidate_sha256'],source='next18twid',path=path,source_root=twid,source_offset=0,**c)
  rows[key]=row;added.append({k:v for k,v in {**row,'relative_path':rel.as_posix(),'original_key':r['original_key'],'logical':r['logical'],'uv_scale':r['uv_scale'],'base_exact':r['base_exact']}.items()if k not in('path','source_root','source_offset')})
 return fp,ph,pi,prior,rows,added

def virtual(ph,pi,prior,head,index,ordered):
 old=hashlib.sha256(ph+pi);new=hashlib.sha256(head+index);oldkeys={r['key']for r in prior};checked=0
 for r in ordered:
  digest=hashlib.sha256();remaining=r['bytes']
  with Path(r['path']).open('rb')as f:
   f.seek(r['source_offset'])
   while remaining:
    b=f.read(min(1048576,remaining))
    if not b:raise ValueError('source member truncated')
    remaining-=len(b);digest.update(b);new.update(b)
    if r['key']in oldkeys:old.update(b)
  if digest.hexdigest()!=r['sha256']:raise ValueError('inherited/new member changed')
  pad=bytes((-r['bytes'])%2048);new.update(pad)
  if r['key']in oldkeys:old.update(pad);checked+=1
 if checked!=7133 or old.hexdigest()!=parent.PACK_SHA:raise ValueError('all7133 exact parent virtual identity')
 return new.hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in['frozen1600-plan','twid','coverage','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args()
 if a.out.exists():raise FileExistsError('preserve existing1618 namespace')
 fp,ph,pi,prior,rows,added=inputs(a.frozen1600_plan,a.twid,a.coverage);head,index,ordered,size=layout(rows)
 if(len(ordered),len(index),size)!=(7151,56*2048,160159744):raise ValueError('1618 index/layout bound')
 digest=virtual(ph,pi,prior,head,index,ordered);runs=shifts({r['key']:r for r in prior},{r['key']:r for r in ordered})
 four=parent.local(json.loads((parent.local(fp['delta1600'])/'plan/PLAN1600.json').read_text())['four']['path']);before={w['path']:w for w in json.loads((four/'world-proposals.json').read_text())['worlds']};deltas=json.loads((a.twid/'world-proposals.json').read_text())['worlds']
 if len(before)!=29 or len(deltas)!=15 or len({w['path']for w in deltas})!=15:raise ValueError('15delta+14retained world composition')
 for w in deltas:
  if w['path']not in before or w['parent_sha256']!=before[w['path']]['candidate_sha256']:raise ValueError('world parent lineage changed')
 a.out.mkdir();(a.out/'expected-header.bin').write_bytes(head);(a.out/'expected-index.bin').write_bytes(index);emit(a.out/'APPENDED-18-TWID.json',added);emit(a.out/'PARENT-7133-OFFSET-SHIFTS.json',runs)
 minimal=lambda w:{k:w[k]for k in('path','room','parent_sha256','candidate_sha256','physical_body_crc','physical_file_fnv')if k in w}
 emit(a.out/'UNSELECTED-WORLD-DELTA.json',dict(status='ALL29_PRIVATE_UNSELECTED',twid_proposals_path=str(a.twid/'world-proposals.json'),twid_proposals_sha256=file_sha(a.twid/'world-proposals.json'),parent4_proposals_path=str(four/'world-proposals.json'),parent4_proposals_sha256=file_sha(four/'world-proposals.json'),changed15=[minimal(w)for w in deltas],retained14=[minimal(w)for k,w in before.items()if k not in{r['path']for r in deltas}],integration_source='33504b9df is source-only; no programme/data selection inferred',holds=['r11f/r200 physicalmetadata/ownership held','r107AREA baseline identity guard carried','no alpha142 inclusion','all lifecycle/consumer/look/resource/wholefile proof gates carried']))
 plan=dict(status='SOURCE_ONLY_1618_DELTA_NO_MATERIALIZATION_OR_SELECTION',frozen1600=dict(plan_path=str(a.frozen1600_plan),plan_sha256=file_sha(a.frozen1600_plan),writer_sha256=WRITER_SHA,virtual_pack_sha256=parent.PACK_SHA,parent1596seal=parent.PARENT_SEAL,delta1600seal=parent.DELTA_SEAL,members7133_byteexact=True),twid18=dict(path=str(a.twid),producer='7eeecd40c5edd1f5b7de20bd780f11cd267a758e',seal=TWID_SEAL,strictPackage_ON_OFF_corrupt=[18,18,3],actual_decoded_levels=90,format='RGB56516square/TWIDpayload1/mip4/688B/UV1,1',approximation_look_hold=True),expected=dict(pack_sha256=digest,pack_bytes=size,members=7151,mips_if_selected=1618,index_sectors=56,data_offset=116736,index_crc32=zlib.crc32(index)&0xffffffff,index_spare_entries=17,runtime8192_spare_entries=1041,preserved_parent7133=7133,new18=18,old_pack_slot_bytes=156254208,old_slot_overflow_bytes=size-156254208),resolver='Final7151index +frozen1600piecewise7133source/memberSHAresolver +APPENDED18 source/descriptor/SHA/CRC, no duplicate parent fullmap. Frozen1600writer/controller/plan unchanged. A NEW future writer namespace/allocation would be required.',proposed_resources=dict(two_pack_logical_bytes=2*size,metadata_allowance=12582912,aggregate_proposal_only=2*size+12582912,no_allocation=True,accounting='max4KiBlogical/native allocation; allfiles/failed/closed charged; freshC floor18GiB+64MiB+peer64MiB, no automatic compression credit'),worlds='15delta+14retained=29 PRIVATE UNSELECTED/650proposals; no alpha142, r11f/r200 held',source_only=True)
 emit(a.out/'PLAN1618.json',plan)
 with(a.out/'SHA256SUMS').open('x')as f:
  for p in sorted(a.out.iterdir()):
   if p.is_file()and p.name!='SHA256SUMS':f.write(file_sha(p)+'  '+p.name+'\n')
 print(json.dumps(dict(status='PASS_SOURCE_ONLY_1618',expected=plan['expected'],seal=file_sha(a.out/'SHA256SUMS'),large_bytes_written=0)))
if __name__=='__main__':main()

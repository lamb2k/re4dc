#!/usr/bin/env python3
"""Four-key source-only delta on sealed1596 plan; no fullpack/image writer."""
import argparse,hashlib,json,struct
from pathlib import Path
from plan_append1596 import candidate,file_sha,layout,seal,emit

PARENT_SEAL='51d6bf3bc48c7f244fbdf14a3ff813738e117ecc7b7e6c50bbac3e1bed1296c7'
FOUR_SEAL='b42f88622b901d336cb0d32013c6918c8c9fe8bccc98968a9aa1e75f7ce15657'
def verify_parent(root):
 assert file_sha(root/'SHA256SUMS')==PARENT_SEAL
 for line in(root/'SHA256SUMS').read_text().splitlines():
  h,rel=line.split('  ',1);p=Path(rel);assert not p.is_absolute()and'..'not in p.parts;assert file_sha(root/p)==h
def shifts(parent,final):
 result=[]
 for key in sorted(parent):
  delta=final[key]['offset']-parent[key]['offset']
  if result and result[-1]['delta_bytes']==delta:result[-1]['last_parent_key']=key;result[-1]['members']+=1
  else:result.append(dict(first_parent_key=key,last_parent_key=key,delta_bytes=delta,members=1))
 return result
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ['parent','four','coverage','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();assert not a.out.exists();verify_parent(a.parent);seal(a.four,FOUR_SEAL);a.out.mkdir()
 p=json.loads((a.parent/'plan/PLAN.json').read_text());assert p['expected']['members']==7129 and p['expected']['mips_if_selected']==1596
 receipt=json.loads((a.four/'conversion-receipt.json').read_text());host=json.loads((a.four/'host-gate.json').read_text());assert len(receipt['selected'])==4 and host['positive_cases']==4 and host['mip_disabled_rejections']==4 and len(host['negative_cases'])==6 and host['strict_adopt_and_stream_CRC1']
 rows={}
 for line in(a.parent/'plan/MEMBERS-7129.tsv').read_text().splitlines():
  key,n,h,offset,old,source=line.split('\t');rows[key]=dict(bytes=int(n),sha256=h,offset=int(offset),old_offset=None if old=='-'else int(old),source=source)
 assert len(rows)==7129;parent=dict(rows);prior=json.loads((a.parent/'plan/APPENDED-592.json').read_text());by={r['key']:r for r in prior};old_originals={r['original_key']for r in prior}
 coverage=json.loads(a.coverage.read_text());assert file_sha(a.coverage)==receipt['coverage_sha256'];occupied=set(rows)|{r['key']for r in coverage['loose_and_quality_rows']}|{'3662c0aa-c9e71c00','fefdf580-f15c1f47'}
 added=[]
 for r in receipt['selected']:
  key=r['scoped_key'];assert key not in occupied and r['original_key']not in old_originals;occupied.add(key);old_originals.add(r['original_key']);rel=Path(r['relative_path']);assert rel.as_posix()=='textures/'+key+'.re4tex'
  blob=(a.four/rel).read_bytes();c=candidate(blob,r);rows[key]=dict(bytes=len(blob),sha256=r['candidate_sha256'],source='next4',relative_path=rel.as_posix(),old_offset=None);added.append({**c,'key':key,'original_key':r['original_key'],'sha256':r['candidate_sha256'],'bytes':len(blob),'relative_path':rel.as_posix(),'logical':r['logical'],'uv_scale':r['uv_scale'],'base_exact':r['base_exact']})
 head,index,ordered,size=layout(rows);assert len(ordered)==7133 and len(index)==56*2048
 roots={n:Path(path)for n,path in p['append']['roots'].items()};roots['next4']=a.four;digest=hashlib.sha256(head+index);checked=0
 with Path(p['base']['path']).open('rb')as f:
  for r in ordered:
   if r['source']=='canonical1004':f.seek(r['old_offset']);blob=f.read(r['bytes']);checked+=1
   else:
    rel=r.get('relative_path')or by[r['key']]['relative_path'];blob=(roots[r['source']]/rel).read_bytes()
   assert len(blob)==r['bytes']and hashlib.sha256(blob).hexdigest()==r['sha256'];digest.update(blob);digest.update(bytes((-len(blob))%2048))
 assert checked==6537
 final={r['key']:r for r in ordered};ranges=shifts(parent,final);assert sum(r['members']for r in ranges)==7129
 with(a.out/'expected-header.bin').open('xb')as f:f.write(head)
 with(a.out/'expected-index.bin').open('xb')as f:f.write(index)
 emit(a.out/'APPENDED-4.json',added);emit(a.out/'PARENT-7129-OFFSET-SHIFTS.json',ranges)
 before={w['path']:w for w in json.loads((roots['next177']/'world-proposals.json').read_text())['worlds']};after=json.loads((a.four/'world-proposals.json').read_text())['worlds'];changed=[]
 for w in after:
  assert w['parent_sha256']==before[w['path']]['candidate_sha256']
  if w['candidate_sha256']!=w['parent_sha256']:changed.append(w)
 assert len(after)==29 and len(changed)==1 and changed[0]['room']=='r101'and changed[0]['new_key_only_records']==7
 emit(a.out/'UNSELECTED-WORLD-DELTA.json',dict(status='ALL29_UNSELECTED; originalmetadata/source/lifecycle/look/resourceholds carried',parent='sealed1596 plan/UNSELECTED-29-WORLDS.json',changed_world=changed[0],other_worlds_28_byteexact_to177=True,compiled632table_or29cert_selection=False))
 delta=dict(status='SOURCE_ONLY_IMMUTABLE1600_DELTA_NOT_MATERIALIZED_NOT_SELECTED',parent=dict(path=str(a.parent),seal=PARENT_SEAL,members_TSV_sha256=file_sha(a.parent/'plan/MEMBERS-7129.tsv'),candidate592_sha256=file_sha(a.parent/'plan/APPENDED-592.json'),pack_virtual_sha256=p['expected']['sha256']),four=dict(path=str(a.four),seal=FOUR_SEAL,source='51e8d4cc5aaff4f8837a9253b75a930aabf89566',selected=4,bodyCRC_descriptor_namespace_checks=4,material_refs=7,host_ON_OFF_corrupt=[4,4,6]),expected=dict(pack_sha256=digest.hexdigest(),pack_bytes=size,members=7133,mips_if_selected=1600,preserved_current6537_byteexact=6537,preserved_prior592_byteexact=592,index_sectors=56,index_capacity=7168,index_crc32=struct.unpack_from('<I',head,24)[0],data_offset=116736,spare_index_entries=35,remaining_total_runtime_entries=8192-7133,archive_growth_vs_current1004=size-156248064,old_disc_pack_slot=156254208,old_slot_overflow_bytes=size-156254208,old_slot_overflow_sectors=(size-156254208)//2048),membership='Final7133index givesexactkeys/extents; inherited7129TSV giveseachmemberbyteSHA/source/baseoffset, APPENDED4 suppliesfournewhashes/sourcefiles. No duplicatefullmanifest/originalinventoryscan.',independent_virtual_stream_full_member_hashes=True,resource_delta=dict(new_pack_plus_mirror_uncompressed_bytes=2*size,metadata_budget_proposal=12*1024**2,incremental_content_bound_proposal=2*size+12*1024**2,previous1596_sourceplan_and_outputs_remain_charged=True,NTFS_freshfilesystem_peer_guard_and_nooverwrite_spec='Inherited MATERIALIZATION-SPEC.json. Rootfreshallocation/actualC/nativefileID/readback beforecredit; no silentquota/floor change.'),runtime='Current042/733a/69f/1004activefiles unchanged. Existing36world+20actor members remainbyteexact. All29worlds/proposed632table/certificates UNSELECTED; r107/r11f/r200hardholds carried, no metadata or programme selection by this unit.',image_hold='Packdoesnotfitoldextent; freshlayout/integrationallocation required. No pack/image/build/guest/staging/SD/release authorized.')
 emit(a.out/'PLAN1600.json',delta)
 with(a.out/'SHA256SUMS').open('x')as f:
  for path in sorted(a.out.iterdir()):
   if path.is_file()and path.name!='SHA256SUMS':f.write(file_sha(path)+'  '+path.name+'\n')
 print(json.dumps(dict(result='PASS_SOURCE_ONLY1600_DELTA',expected=delta['expected'],seal=file_sha(a.out/'SHA256SUMS'),metadata_bytes=sum(q.stat().st_size for q in a.out.iterdir()if q.is_file()))))
if __name__=='__main__':main()

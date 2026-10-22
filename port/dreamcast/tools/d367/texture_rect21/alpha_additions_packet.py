#!/usr/bin/env python3
"""Metadata-only exact142 additions packet; never creates textures/worlds/pack/programme."""
from pathlib import Path,PureWindowsPath
import argparse,hashlib,json,re,shutil,struct,sys,zlib
T=Path(__file__).resolve().parent;sys.path.insert(0,str(T));import world_bindings as world
H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text())
def pin(p):return dict(path=str(p),sha256=H(p.read_bytes()),bytes=p.stat().st_size)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out;assert not O.exists();assert shutil.disk_usage('/mnt/c').free>=19394461696+1048576+67108864
 A=Path('/root/re4data/private/texture-rect21-next142-alpha-20261022-v1');N=Path('/root/re4data/private/texture-rect21-alpha-repeat16-20261022-v1');P=Path('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021');pol=load(N/'policy-qualified-receipt.json');orig=load(A/'policy-qualified-receipt.json');original119={x['original_key']for x in orig['selected']};new16={x['original_key']for x in load(N/'conversion-receipt.json')['selected']};aliases={x['original_key']:x['refs']for x in load(N/'policy-alias-proof.json')['records']};assert len(original119)==119 and len(new16)==16 and not(original119&new16)
 parentplan=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021/append1618-delta-01/plan/PLAN1618.json');assert H(parentplan.read_bytes())=='38a87ae971e76815aed191bd5553179fefae3cd5e00f05806097d3f4bbb5749d'
 # Exact7151 namespace from immutable6537 index+614 prior additions; no partial writer output is read.
 base=Path('/root/re4data/private/texture-canonical1004-20261021/tex.pak')
 with base.open('rb')as f:
  h=f.read(2048);v,n,off,data,crc=struct.unpack_from('<5I',h,8);assert n==6537;f.seek(off);index=f.read(n*16)
 occupied={tuple(struct.unpack_from('<4I',index,16*i)[:2])for i in range(n)};priorpins={}
 for name,count in [('texture-rect21-next415-20261021-v1',415),('texture-rect21-next177-20261022-v2',177),('texture-rect21-next4-vertical-20261022-v1',4),('texture-rect21-next18-twiddled-20261022-v1',18)]:
  p=Path('/root/re4data/private')/name/'conversion-receipt.json';j=load(p);assert len(j['selected'])==count;priorpins[str(p)]=H(p.read_bytes())
  for x in j['selected']:
   k=tuple(int(z,16)for z in x['scoped_key'].split('-'));assert k not in occupied;occupied.add(k)
 assert len(occupied)==7151
 selected=[];sources={};hostpin=pin(N/'host-gate.json');originalhostpin=pin(A/'host-gate.json')
 for x in pol['selected']:
  rel=Path(x['relative_path']);path=rel if rel.is_absolute()else N/rel;b=path.read_bytes();assert H(b)==x['candidate_sha256']and len(b)==x['package_bytes'];t=struct.unpack_from('<64s8I',b,48);assert len(b[48:144])==96;hd=struct.unpack_from('<4s11I',b,0);checksum=struct.unpack_from('<I',b,36)[0];assert checksum==x['candidate_crc32']==zlib.crc32(b[48:])&0xffffffff
  assert list(t[1:3])==x['physical']and t[3]==x['format']and t[5]==x['candidate_payload']and t[6]==x['flags']and t[7]==x['payload_type']and t[4]==144 and len(b)==144+t[5]
  key=tuple(int(z,16)for z in x['scoped_key'].split('-'));assert key not in occupied;occupied.add(key)
  if x['original_key']in new16:semantic='repeat16';root=N;evidence='alpha-repeat16-batch-01';host=hostpin
  else:semantic='compact119'if x['original_key']in original119 else'missing7';root=A;evidence='next142-alpha-batch-01';host=originalhostpin
  relative=path.relative_to(root).as_posix();win=str(PureWindowsPath('C:/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021')/evidence/relative);mirror=R/evidence/relative;assert mirror.read_bytes()==b
  rows=aliases[x['original_key']];assert len(rows)==len(x['world_refs']);shipped=sum(y['shipped_class']is not None for y in rows);unlisted=len(rows)-shipped
  selected.append(dict(key=x['scoped_key'],scoped_key=x['scoped_key'],original_key=x['original_key'],absolute_path=str(path),windows_path=win,source_root=str(root),relative_path=relative,bytes=len(b),package_bytes=len(b),sha256=H(b),candidate_sha256=H(b),body_crc32=checksum,candidate_crc32=checksum,descriptor_hex=b[48:144].hex(),logical=x['logical'],physical=x['physical'],uv_scale=x['uv_scale'],format=x['format'],flags=x['flags'],payload_type=x['payload_type'],payload_bytes=t[5],mip_levels=x['physical'][0].bit_length(),semantic_source=semantic,eligibility=x['policy_acceptance'],source_contract=dict(base_exact=semantic=='repeat16',lower_mips_filtered=True,source_format=x['format'],source_flags=0,original_VQ_book_retained=x['payload_type']==2,nativeTWID_retained=x['payload_type']==1),host_receipt_sha256=host['sha256'],host_receipt_path=host['path'],aliases=[dict(room=q['world'].split('/')[2],part=q['part'],render_pass=q['render_pass'],cull=q['cull'],texture=q['texture'],flags=q['flags'],policy_acceptance=next(y['acceptance']for y in rows if y['room']==q['world'].split('/')[2]and y['part']==q['part']))for q in x['world_refs']],shipped_class_aliases=shipped,intentional_unlisted_aliases=unlisted))
 assert len(selected)==142 and len(occupied)==7293 and sum(x['shipped_class_aliases']for x in selected)==468 and sum(x['intentional_unlisted_aliases']for x in selected)==40
 def tablekeys(p):return {'%08x-%08x'%(int(a,16),int(b,16))for a,b in re.findall(r'\{0x([0-9a-f]+)U,0x([0-9a-f]+)U,',p.read_text())}
 oldkeys=tablekeys(A/'proposed_scoped_representations_combined769.inc');finalkeys=tablekeys(N/'proposed_scoped_representations_combined792.inc');assert oldkeys<=finalkeys and len(finalkeys-oldkeys)==23;assert (N/'proposed_scoped_representations_combined792.inc').read_bytes().startswith((P/'proposed_scoped_representations_combined650.inc').read_bytes())
 # Resolve prior769 world chain, including allthree unchanged/missing-profile rooms, without generating world copies.
 def resolve(root,name):
  seen=set()
  while root and str(root)not in seen:
   seen.add(str(root));p=root/'proposed-worlds'/name
   if p.exists():return p
   rows=load(root/'world-proposals.json')['worlds'];parent=rows[0].get('parent_lineage','').split('/proposed-worlds/')[0]if rows else'';root=Path(parent)if parent else None
  c=Path('/root/re4data/private/texture-world36-canonical-crc-20261021')/name
  return c if c.exists()else R/'native-bindings-01/inputs'/name
 worlds=[];tot=other=0
 for w in load(N/'world-proposals.json')['worlds']:
  path=N/'proposed-worlds'/w['path'];b=path.read_bytes();source=R/'native-bindings-01/inputs'/w['path'];before=source.read_bytes();assert len(b)==len(before)==w['bytes']and H(b)==w['candidate_sha256'];parts=w['parts'];end=32+16*parts;assert b[:20]==before[:20]and b[24:32]==before[24:32];assert b[end:]==before[end:];assert all(b[32+16*i+8:48+16*i]==before[32+16*i+8:48+16*i]for i in range(parts));prior=resolve(A,w['path']);pb=prior.read_bytes();diff=sum(b[32+16*i:40+16*i]!=pb[32+16*i:40+16*i]for i in range(parts));srcrows=world.inspect_sidecar(before);rows=world.inspect_sidecar(b)
  for a,z in zip(srcrows,rows):
   if z['key']in finalkeys:tot+=1
   else:assert a==z;other+=1
  worlds.append(dict(path=w['path'],absolute_path=str(path),sha256=H(b),bytes=len(b),original_sha256=H(before),parent650_lineage=w['parent_lineage'],parent650_sha256=w['parent_sha256'],intermediate769_path=str(prior),intermediate769_sha256=H(pb),changed_vs769=bool(diff),changed_key_records_vs769=diff,physical_body_crc=w['physical_body_crc'],physical_file_fnv=w['physical_file_fnv'],canonical_source_crc=w['original_source_crc'],mesh_sha256=w['mesh_sha256'],mesh_bytes=w['mesh_bytes'],mesh_crc=w['mesh_crc'],parts=parts,placements=w['placements'],meshes=w['meshes'],all_non_key_material_and_mesh_placement_bytes_original=True,selection_hold='PHYSICAL_DEEP_OWNER_HARDHOLD'if w['room']in('r11f','r200')else'ROOT335_R107_SOURCE_CLOSURE_SEPARATE'if w['room']=='r107'else'EXPANDED792_RUNTIME_SOURCE_AND_TARGET_REVIEW_PENDING'))
 assert len(worlds)==29 and tot==4371 and other==2971
 metrics=Path('/root/re4data/private/texture-rect21-repeat16-metrics-correction-20261022-v1/FINAL142-CORRECTED-METRIC-BINDINGS.json');assert H(metrics.read_bytes())=='31a5789424686776c716321a9d34a5d0b12def3c807774b85bcaf7f384d330f5'
 additions=dict(corrected_metric_bindings=pin(metrics),old_repeat_metrics_historical_only=True,schema='RE4DC_ALPHA142_ADDITIONS_PACKET_V1',status='SOURCE_INPUT_PACKET_NO_PACK_MATERIALIZATION_OR_RUNTIME_ADOPTION',producer_source='6609c87860153ce203d41e49aad933dd8fc90154',producer_seals=[pin(N/'SHA256SUMS.txt'),pin(N/'SHA256SUMS-WSL-ALL.txt'),pin(A/'SHA256SUMS.txt')],source_policy_proof=pin(N/'policy-alias-proof.json'),selected=selected,parent=dict(status='VIRTUAL1618_NOT_COMPLETED_ACTUAL_PACK',manifest=pin(parentplan),expected_pack_sha256='d43d1c81ba2e70ab0177c6c97867fd39c95d68a114b727601b3eadd14e6aaf08',bytes=160159744,members=7151,index_sha256='5a2941719c5936aba53f5f48d4b7d85e1382de2bfbe4a21f904a9c4fe0cf5e87',member_namespace_verified_from6537_plus614=True,prior_receipt_pins=priorpins),index_layout=dict(parent_members=7151,additions=142,final_members=7293,entry_bytes=16,sector_bytes=2048,required_index_sectors=57,index_capacity=7296,spare_entries=3,parent_index_sectors=56,parent_data_start=116736,new_data_start=118784,minimum_existing_member_offset_shift=2048,must_reindex_every_member=True,interleaved_sorted_insertions_add_padding_or_more_offset_shift=True,forbid_silent56sector_reuse=True,final_virtual_pack_sha256=None,virtual_full_SHA_owner='benchmark/root separate source composition allocation'),limits=['No pack/assets/world/programme/image/guest/recipe output; this packet only references sealed inputs.','Semantic_source differentiates119compact/16exactBASErepeat/7missing-onlycompact. Nine keys touch40intentional-unlisted refs, not shipped-class matches.','All original member identities remain unchanged; offsets cannot be copied from7151 parent after index expansion.','All29 world proposals remain unselected pending root integration; physicalr11f/r200 holds and separate rootr107 closure remain.'])
 worldpacket=dict(schema='RE4DC_FINAL792_WORLD_LINEAGE_V1',table=pin(N/'proposed_scoped_representations_combined792.inc'),certificates=pin(N/'proposed_provenance_certificates.inc'),prior650_table=pin(P/'proposed_scoped_representations_combined650.inc'),intermediate769_table=pin(A/'proposed_scoped_representations_combined769.inc'),prior650_prefix_byteexact=True,prior769_keys_retained=True,new_vs769_keys=sorted(finalkeys-oldkeys),new_vs769_semantics='16new repeat versions+7 existing compact missing-only;119 intermediate compact bindings retained',worlds=worlds,rectangle_keys=792,rectangle_material_rows=4371,other_base_material_rows_unchanged=2971,new_mesh_or_placement_bytes=False,worlds_selected=False)
 O.mkdir()
 for name,j in [('ADDITIONS142.json',additions),('WORLD792-LINEAGE.json',worldpacket)]:
  b=(json.dumps(j,separators=(',',':'))+'\n').encode();assert len(b)<400000
  with(O/name).open('xb')as f:f.write(b)
 print(json.dumps(dict(keys=142,classes={s:sum(x['semantic_source']==s for x in selected)for s in('compact119','repeat16','missing7')},worlds=29,changed_worlds_vs769=sum(x['changed_vs769']for x in worlds),metadata_bytes=sum(p.stat().st_size for p in O.iterdir()))))
if __name__=='__main__':main()
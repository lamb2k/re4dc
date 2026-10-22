#!/usr/bin/env python3
"""SOURCE ONLY1760: reindex actual1618+sealed142; stream hash, no pack output."""
import argparse,collections,hashlib,json,mmap,os,struct,zlib
from pathlib import Path
import immutable_append1618_native_c_v3_writer as parent
from mipmap_pair_plan import local
from plan_append1596 import layout,scoped,emit,file_sha,reader
from extend_append1600 import shifts
PACKET_SHA='db5d4d32bfb37c4f256666b3a7eebcd053f868038b5b270068a317fa5b70f406'
WORLD_SHA='62b05566694fd7c5942d83de6220e77008be3b1b7c82e58009e6cbaaeb9c8fe2'
PACKET_SEAL='9b388f786df86266145c3d77c127036281540cd0c4d75ab8c30b26d859ca3ade'
PLAN_SHA='d5b05859fd9fd0d572f765121414cb845c40966f0deb200cc26e8952aaf6d1b6'
COVERAGE_SHA='f1c83ea0af2bcbe55a96ac01cd11090c3adbc3058482c0a37dacb3dcc1dea450'
ROOT792='63644457a2251a398de174f47be650e1b2b4c791'
def require(ok,why):
 if not ok:raise ValueError(why)
def pinned(path,digest):
 path=local(path);require(file_sha(path)==digest,'input SHA drift '+str(path));return path

def alpha_candidate(blob,r):
 require(len(blob)==r['bytes']==r['package_bytes']and hashlib.sha256(blob).hexdigest()==r['sha256']==r['candidate_sha256'],'142package SHA/bytes')
 require(len(blob)>=144,'short descriptor');h=struct.unpack_from('<8s10I',blob);t=struct.unpack_from('<64s8I',blob,48)
 require(h[:7]==(b'RE4DCTX\0',2,48,96,1,48,144)and h[9:]==(1,0),'header/sourcecount/flags')
 side=t[1];levels=side.bit_length();kind=t[7];fmt=t[3]
 require(side in(16,32,64,128,256)and t[2]==side and fmt in(1,2)and t[4]==144 and t[6]==4 and kind in(1,2)and t[8]==0,'alpha complete square mip descriptor')
 payload=(2048 if kind==2 else 6)+sum(max(1,(1<<n)**2//4)if kind==2 else 2*(1<<n)**2 for n in range(levels))
 require(t[5]==payload==h[7]==len(blob)-144==r['payload_bytes'],'complete alpha mip payload')
 require(h[8]==r['body_crc32']==r['candidate_crc32']==zlib.crc32(blob[48:])&0xffffffff,'canonical descriptor+payload CRC')
 require(blob[48:144].hex()==r['descriptor_hex']and r['physical']==[side,side]and r['uv_scale']==([r['logical'][0]/side,r['logical'][1]/side]if r['semantic_source']=='repeat16'else[1.,1.])and(r['format'],r['flags'],r['payload_type'],r['mip_levels'])==(fmt,4,kind,levels),'packet descriptor binding')
 require(r['key']==r['scoped_key']==scoped(r['original_key'],r['sha256']),'scoped immutable key')
 return dict(body_crc32=h[8],descriptor_hex=blob[48:144].hex(),format=fmt,flags=4,payload_type=kind,payload_bytes=payload,physical=[side,side],mip_levels=levels)

def receipt_gate(controller,child):
 require(controller['qualified']and controller['exit_code']==0 and controller['whole_job_empty']and controller['handles_closed_after_empty']and not controller['errors'],'actual root controller not closed PASS')
 require(child['status']=='PASS'and child['byte_exact_mirror']and child['native_C_sources_bound']==615,'actual child PASS/615 source binding')
 for name in('primary','mirror'):
  r=child[name];require(r['known_reader']and r['all_member_SHA']and(r['members'],r['bytes'],r['sha256'])==(7151,parent.PACK_BYTES,parent.PACK_SHA),'actual pack readback identity')

def final_worlds(root):
 w=json.loads(pinned(root/'WORLD792-LINEAGE.json',WORLD_SHA).read_text());require(len(w['worlds'])==29 and w['worlds_selected']is False and w['prior650_prefix_byteexact']and w['prior769_keys_retained']and w['other_base_material_rows_unchanged']and not w['new_mesh_or_placement_bytes'],'all29 private source lineage')
 for name in('table','certificates','prior650_table','intermediate769_table'):
  p=w[name];require(pinned(p['path'],p['sha256']).stat().st_size==p['bytes'],'world table source extent')
 for r in w['worlds']:
  require(pinned(r['absolute_path'],r['sha256']).stat().st_size==r['bytes']and r['all_non_key_material_and_mesh_placement_bytes_original'],'private world key-only source contract')
 return w

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in('actual-pack','writer-plan','actual-metadata','packet','coverage','reader','out'):ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();require(not a.out.exists(),'preserve existing1760 namespace')
 plan=json.loads(pinned(a.writer_plan,PLAN_SHA).read_text());ph,pi,prior=parent.resolve(plan);rows={r['key']:{**r,'source':'actual1618','source_offset':r['offset']}for r in prior};require(len(rows)==7151,'all7151 frozen source identities')
 c=json.loads((a.actual_metadata/'controller.json').read_text());child=json.loads((a.actual_metadata/'child-result.json').read_text());receipt_gate(c,child)
 require(a.actual_pack.stat().st_size==parent.PACK_BYTES and file_sha(a.actual_pack)==parent.PACK_SHA,'actual1618 wholepack hash')
 require(file_sha(a.packet/'SHA256SUMS.txt')==PACKET_SEAL,'frozen142 packet seal')
 for line in(a.packet/'SHA256SUMS.txt').read_text().splitlines():
  h,name=line.split('  ',1);rel=Path(name);require(not rel.is_absolute()and'..'not in rel.parts,'packet path');pinned(a.packet/rel,h)
 packet=json.loads(pinned(a.packet/'ADDITIONS142.json',PACKET_SHA).read_text());require(len(packet['selected'])==142 and packet['parent']['expected_pack_sha256']==parent.PACK_SHA,'142 parent identity')
 require(packet['index_layout']['final_members']==7293 and packet['index_layout']['required_index_sectors']==57 and packet['index_layout']['must_reindex_every_member'],'new57sector contract')
 for p in packet['producer_seals']+[packet['corrected_metric_bindings'],packet['source_policy_proof']]:pinned(p['path'],p['sha256'])
 coverage=json.loads(pinned(a.coverage,COVERAGE_SHA).read_text());occupied=set(rows)|{r['key']for r in coverage['loose_and_quality_rows']}|{'3662c0aa-c9e71c00','fefdf580-f15c1f47'};added=[];blobs={};hostpins={};sem=collections.Counter()
 for r in packet['selected']:
  key=r['key'];require(key not in occupied,'key collision');occupied.add(key);require(r['relative_path']=='textures/'+key+'.re4tex','exact member relative path')
  source=parent.safe_path(local(r['absolute_path']),local(r['source_root']));blob=source.read_bytes();desc=alpha_candidate(blob,r);win=Path('/mnt/c/'+r['windows_path'][3:].replace('\\','/'))if os.name!='nt'else Path(r['windows_path']);require(win.read_bytes()==blob,'explicit C mirror bytes differ')
  hp=pinned(r['host_receipt_path'],r['host_receipt_sha256']);hostpins[str(hp)]=r['host_receipt_sha256'];sem[r['semantic_source']]+=1
  rows[key]=dict(key=key,bytes=len(blob),sha256=r['sha256'],source='final142',source_offset=0);blobs[key]=blob
  added.append(dict(key=key,original_key=r['original_key'],bytes=len(blob),sha256=r['sha256'],absolute_path=r['absolute_path'],windows_path=r['windows_path'],source_root=r['source_root'],relative_path=r['relative_path'],semantic_source=r['semantic_source'],eligibility=r['eligibility'],logical=r['logical'],uv_scale=r['uv_scale'],**desc))
 require(dict(sem)=={'compact119':119,'repeat16':16,'missing7':7},'exact119+16+7 groups')
 for p,h in hostpins.items():
  host=json.loads(Path(p).read_text());outputs=host['outputs'];require(all(x['PASS']for x in outputs.values()),'sealed actual Package host failed')
  require(host.get('corrupt_rejects',host.get('corrupt_rejections',0))>=6,'host corruption controls')
 w=final_worlds(a.packet);head,index,ordered,size=layout(rows);require(len(ordered)==7293 and len(index)==57*2048 and len(head)+len(index)==118784,'final reindex every7293')
 known=reader(a.reader);digest=hashlib.sha256(head+index);members_digest=hashlib.sha256();actual=a.actual_pack.stat();checked=0
 with a.actual_pack.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view:
  require(known.verify(view)[0]==7151 and view[:2048]==ph and view[2048:116736]==pi,'actual knownreader/header/index exact frozen1618')
  for r in ordered:
   blob=bytes(view[r['source_offset']:r['source_offset']+r['bytes']])if r['source']=='actual1618'else blobs[r['key']]
   require(len(blob)==r['bytes']and hashlib.sha256(blob).hexdigest()==r['sha256'],'parent/new member SHA')
   digest.update(blob);digest.update(bytes((-len(blob))%2048))
   if r['source']=='actual1618':checked+=1;members_digest.update((r['key']+' '+str(r['bytes'])+' '+r['sha256']+'\n').encode())
 require(checked==7151 and(a.actual_pack.stat().st_size,a.actual_pack.stat().st_mtime_ns,a.actual_pack.stat().st_ino)==(actual.st_size,actual.st_mtime_ns,actual.st_ino),'all7151 preserved/source identity stable')
 final={r['key']:r for r in ordered};runs=shifts({r['key']:r for r in prior},final);require(sum(r['members']for r in runs)==7151 and min(r['delta_bytes']for r in runs)>=2048,'allparent extents reindexed')
 a.out.mkdir();(a.out/'expected-header.bin').write_bytes(head);(a.out/'expected-index.bin').write_bytes(index);emit(a.out/'APPENDED-142.json',added);emit(a.out/'PARENT-7151-OFFSET-SHIFTS.json',runs)
 expected=dict(pack_sha256=digest.hexdigest(),pack_bytes=size,members=7293,mips_if_selected=1760,parent7151_byteexact=True,new142=True,index_sectors=57,index_capacity=7296,index_spare=3,runtime_spare=899,data_offset=118784,index_crc32=zlib.crc32(index)&0xffffffff,growth_vs_actual1618=size-parent.PACK_BYTES,old_disc_slot_overflow=size-156254208)
 inputs={str(a.writer_plan):PLAN_SHA,str(a.packet/'ADDITIONS142.json'):PACKET_SHA,str(a.packet/'WORLD792-LINEAGE.json'):WORLD_SHA,str(a.packet/'SHA256SUMS.txt'):PACKET_SEAL,str(a.actual_metadata/'controller.json'):file_sha(a.actual_metadata/'controller.json'),str(a.actual_metadata/'child-result.json'):file_sha(a.actual_metadata/'child-result.json'),str(a.coverage):COVERAGE_SHA,**hostpins}
 emit(a.out/'PLAN1760.json',dict(status='SOURCE_ONLY_VIRTUAL1760_NOT_MATERIALIZED_NOT_SELECTED',actual1618=dict(path=str(a.actual_pack),bytes=parent.PACK_BYTES,sha256=parent.PACK_SHA,member_identity_digest=members_digest.hexdigest(),index_sha256=hashlib.sha256(pi).hexdigest(),knownreader=True,all7151memberSHA=True),input_pins=inputs,packet_source='91303e03b3349aac95698acf4912cb6043818c84',root792_source_only=ROOT792,root792_receipt='a8e5a20512639e775e8f31415cbcf72957236204caf11a96045dbc0e13949339',expected=expected,groups=dict(sem),all29worlds_PRIVATE_UNSELECTED=True,source792_not_programme_or_target=True,holds=['27 physical certificates source-only; r11f/r200 held','r107 metadata/lifecycle/look/resource source holds carried','source approximation/repeat/policy semantics distinct; no target look or chosenLOD acceptance','old disc extent too small: no image overwrite'],resolver='Read actual1618 known index+frozen7151 source/memberSHA resolver; final7293index reindexes all offsets; APPENDED142 holds explicit sources+canonical descriptor/bodyCRC; no repeated6501assessment',resources_proposal=dict(pack_plus_mirror_bytes=2*size,metadata_bytes=12582912,total_unallocated=2*size+12582912,old_closed_outputs_preserved=True,guards='Fresh native per-file max4KiBlogical/allocated charge; existing/failed/peers exactlyonce;18GiB+64MiB+sourcepeer64MiB; root new allocation/namespace/deadlines/nooverwrite/readback required'),large_bytes_written=0))
 (a.out/'SHA256SUMS').write_text(''.join(file_sha(p)+'  '+p.name+'\n'for p in sorted(a.out.iterdir())if p.is_file()))
 print(json.dumps(dict(status='PASS_SOURCE_ONLY_VIRTUAL1760',expected=expected,seal=file_sha(a.out/'SHA256SUMS'),metadata_bytes=sum(p.stat().st_size for p in a.out.iterdir()))))
if __name__=='__main__':main()

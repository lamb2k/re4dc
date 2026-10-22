#!/usr/bin/env python3
"""Immutable append composition PLAN only. No fullpack/image/programme writer."""
import argparse,hashlib,importlib.util,json,mmap,os,re,struct,zlib
from pathlib import Path

BASE_SHA='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62'
READER_SHA='199fb53bc3855ba3c831e4f9013c1e8fd4383cf36615803cbc29acacedcf5bbf'
FINAL_SHA='0ebb5316d9253f8045b650b69a98b164d4d2434b26135a915209e7ecd35228e1'
KEY=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{8}$')
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def emit(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def scoped(original,digest):
 pair=struct.unpack('<II',hashlib.sha256(b'RE4DC_WORLD_RECT21_COMPACT_V1\0'+struct.pack('<II',*[int(x,16)for x in original.split('-')])+bytes.fromhex(digest)).digest()[:8])
 return '%08x-%08x'%pair
def seal(root,expected):
 p=root/'SHA256SUMS.txt';assert file_sha(p)==expected,'producer seal drift';count=0
 for line in p.read_text().splitlines():
  h,name=line.split('  ',1);rel=Path(name);assert not rel.is_absolute()and'..'not in rel.parts
  q=root/rel;assert q.is_file()and not q.is_symlink()and file_sha(q)==h,(name,'sealed producer member drift');count+=1
 return count
def layout(rows):
 assert 0<len(rows)<=8192;size=((len(rows)*16+2047)//2048)*2048;offset=2048+size;index=bytearray();out=[]
 for key,row in sorted(rows.items()):
  assert KEY.fullmatch(key)and row['bytes']>0
  index+=struct.pack('<4I',*[int(x,16)for x in key.split('-')],offset,row['bytes']);out.append({**row,'key':key,'offset':offset});offset+=(row['bytes']+2047)//2048*2048
 index+=bytes(size-len(index));head=b'RE4PAK1\0'+struct.pack('<5I',1,len(rows),2048,2048+size,zlib.crc32(index)&0xffffffff);head+=bytes(2048-len(head))
 return head,bytes(index),out,offset
def append(rows,new):
 for key,row in new.items():assert key not in rows,'immutable scoped collision';rows[key]=row
def candidate(blob,r):
 assert sha(blob)==r['candidate_sha256']and len(blob)==r['package_bytes']
 H=struct.unpack_from('<8s10I',blob);assert H[0]==b'RE4DCTX\0'and H[1:7]==(2,48,96,1,48,144)
 T=struct.unpack_from('<64s8I',blob,48);side=T[1];assert side==T[2]and side in(16,32,64,128,256)
 assert T[3]==0 and T[4]==144 and T[6:]==(4,2,0),'opaque VQ mip descriptor contract'
 assert [side,side]==r['physical']and r['format']==0 and r['flags']==4 and r['payload_type']==2 and r['uv_scale']==[1.,1.]
 assert H[7]==T[5]==len(blob)-144==r['candidate_payload'];assert H[8]==r['candidate_crc32']==zlib.crc32(blob[48:])&0xffffffff,'canonical bodyCRC required'
 assert T[5]==2048+sum(max(1,(1<<n)**2//4)for n in range(side.bit_length())),'complete mip chain byte count'
 assert r['scoped_key']==scoped(r['original_key'],sha(blob)),'scoped namespace formula'
 return dict(body_crc32=H[8],descriptor_hex=blob[48:144].hex(),physical=side,payload=T[5],mip_levels=side.bit_length())
def reader(path):
 assert file_sha(path)==READER_SHA
 spec=importlib.util.spec_from_file_location('owned_known_texpack_reader',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ['base','base-members','batch415','batch177','coverage','reader','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();assert not a.out.exists(),'preserve existing metadata';a.out.mkdir();known=reader(a.reader)
 roots={'next415':a.batch415,'next177':a.batch177};seals={'next415':'49010939c9dea59c2fc18bef0995b23d27e57edfd37aa1222a11e74fa352e624','next177':'3ce4276121e366c8435e576de8f4567535565524bb7422936cd32031af6a27a6'}
 counts={name:seal(root,seals[name])for name,root in roots.items()};proofs={name:json.loads((root/'conversion-receipt.json').read_text())for name,root in roots.items()};expected={};pins=[]
 for name,root in roots.items():
  for n in ['SHA256SUMS.txt','conversion-receipt.json','virtual-pack-manifest.json','host-gate.json','world-proposals.json','summary.json']:pins.append(dict(path=str(root/n),sha256=file_sha(root/n)))
  host=json.loads((root/'host-gate.json').read_text());assert host['status']=='PASS_ACTUAL_PACKAGE_SHARED_BATCH_HOST_ONLY'and host['strict_adopt_and_stream_CRC1']and host['positive_cases']==(415 if name=='next415'else 177)and host['mip_disabled_rejections']==host['positive_cases']and len(host['negative_cases'])==12
 for line in a.base_members.read_text().splitlines():
  key,n,h,offset,_old,_kind=line.split('\t');assert key not in expected;expected[key]=(int(n),h,int(offset))
 assert len(expected)==6537 and a.base.stat().st_size==156248064 and file_sha(a.base)==BASE_SHA
 coverage=json.loads(a.coverage.read_text());assert all(p['coverage_sha256']==file_sha(a.coverage)and p['canonical1004_preserved']==BASE_SHA for p in proofs.values())
 occupied=set(expected)|{r['key']for r in coverage['loose_and_quality_rows']}|{'3662c0aa-c9e71c00','fefdf580-f15c1f47'};new={};checks=[];originals=set();base_identity=a.base.stat();rows={};new_by_group={}
 with a.base.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view:
  count,base_crc=known.verify(view);assert count==6537
  for i in range(count):
   k0,k1,off,n=struct.unpack_from('<4I',view,2048+i*16);key='%08x-%08x'%(k0,k1);size,h,old=expected[key];assert(size,old)==(n,off)
   rows[key]=dict(bytes=n,sha256=h,source='canonical1004',old_offset=off)
  for name,p in proofs.items():
   assert len(p['selected'])==(415 if name=='next415'else 177);group={}
   for r in p['selected']:
    key=r['scoped_key'];assert KEY.fullmatch(key)and key not in occupied,'base/loose/reserved/scoped collision';occupied.add(key);assert r['original_key']not in originals,'cohort source overlap';originals.add(r['original_key'])
    rel=Path(r['relative_path']);assert not rel.is_absolute()and'..'not in rel.parts and rel.as_posix()=='textures/'+key+'.re4tex'
    path=roots[name]/rel;blob=path.read_bytes();c=candidate(blob,r);group[key]=dict(bytes=len(blob),sha256=sha(blob),source=name,old_offset=None,relative_path=rel.as_posix());new[key]=group[key]
    checks.append({**c,'key':key,'original_key':r['original_key'],'sha256':sha(blob),'source':name,'relative_path':rel.as_posix(),'logical':r['logical'],'uv_scale':r['uv_scale'],'base_exact':r['base_exact'],'original_package_sha256':r['source_package_sha256']})
   new_by_group[name]=group
  intermediate=dict(rows);append(intermediate,new_by_group['next415']);h415,i415,r415,n415=layout(intermediate);v415=json.loads((a.batch415/'virtual-pack-manifest.json').read_text());assert len(r415)==6952 and n415==159334400
  assert [(r['key'],r['offset'],r['bytes'],r['sha256'])for r in r415]==[(r['key'],r['offset'],r['bytes'],r['sha256'])for r in v415['manifest']]
  append(rows,new);head,index,ordered,size=layout(rows);v=json.loads((a.batch177/'virtual-pack-manifest.json').read_text());assert len(ordered)==7129 and size==160094208
  assert [(r['key'],r['offset'],r['bytes'],r['sha256'])for r in ordered]==[(r['key'],r['offset'],r['bytes'],r['sha256'])for r in v['manifest']]
  digest=hashlib.sha256(head+index);preserved=0
  for r in ordered:
   blob=bytes(view[r['old_offset']:r['old_offset']+r['bytes']])if r['source']=='canonical1004'else(roots[r['source']]/r['relative_path']).read_bytes()
   assert len(blob)==r['bytes']and sha(blob)==r['sha256'];digest.update(blob);digest.update(bytes((-len(blob))%2048));preserved+=r['source']=='canonical1004'
  assert preserved==6537 and digest.hexdigest()==v['virtual_pack_sha256']==FINAL_SHA
 assert(a.base.stat().st_size,a.base.stat().st_mtime_ns,a.base.stat().st_ino)==(base_identity.st_size,base_identity.st_mtime_ns,base_identity.st_ino)
 with(a.out/'MEMBERS-7129.tsv').open('x')as t:
  for r in ordered:t.write('\t'.join(str(r[k])if r.get(k)is not None else'-'for k in['key','bytes','sha256','offset','old_offset','source'])+'\n')
 with(a.out/'expected-header.bin').open('xb')as t:t.write(head)
 with(a.out/'expected-index.bin').open('xb')as t:t.write(index)
 emit(a.out/'APPENDED-592.json',checks)
 worlds={}
 for name,root in roots.items():worlds[name]={w['path']:w for w in json.loads((root/'world-proposals.json').read_text())['worlds']}
 assert set(worlds['next415'])==set(worlds['next177'])and len(worlds['next415'])==29
 holds=[]
 for path,w in worlds['next177'].items():assert w['parent_sha256']==worlds['next415'][path]['candidate_sha256'];holds.append(dict(path=path,status='UNSELECTED',source_original_sha256=w['source_original_sha256'],after415_sha256=w['parent_sha256'],after177_sha256=w['candidate_sha256'],bytes=w['bytes'],physical_body_crc=w['physical_body_crc'],physical_file_fnv=w['physical_file_fnv'],metadata='UNQUALIFIED_CURRENT_RUNTIME; no source certificate/table selection',hardhold='AREAoriginal9081e7fd/71placements vsretained43dc8ff9'if w['room']=='r107'else'physicalprofile/ownershipfingerprint'if w['room']=='r11f'else'physicalsourceWorldCRC/deepwholefileFNVownership'if w['room']=='r200'else'room metadata/lifecycle/consumer/look/resource selection review pending'))
 emit(a.out/'UNSELECTED-29-WORLDS.json',holds)
 plan=dict(status='SOURCE_ONLY_IMMUTABLE_APPEND_PLAN_NOT_MATERIALIZED_NOT_SELECTED',base=dict(path=str(a.base),bytes=156248064,sha256=BASE_SHA,members=6537,mips=1004,preserved_members=6537,repairs_or_replacements=0),append=dict(roots={n:str(p)for n,p in roots.items()},keys=592,by_group={'next415':415,'next177':177},strict_bodyCRC_format_VQ_mip_descriptor_checks=592,scope_formula='SHA256(RE4DC_WORLD_RECT21_COMPACT_V1 NUL + original_pair_LE + candidate_package_SHA256) first8bytes as pairLE',collisions=0,original_source_cohort_overlap=0,loose_quality_reserved_collision_checked=True),expected=dict(sha256=FINAL_SHA,bytes=size,members=7129,mips_if_selected=1596,index_sectors=len(index)//2048,index_capacity=len(index)//16,index_crc32=zlib.crc32(index)&0xffffffff,data_offset=2048+len(index),runtime_total_capacity=8192,remaining_total_slots=8192-7129,remaining_current_index_slots=len(index)//16-7129,archive_growth_bytes=size-156248064,old_disc_slot_bytes=156254208,old_disc_slot_overflow_bytes=size-156254208,old_disc_slot_overflow_sectors=(size-156254208)//2048),producer_seals=seals,producer_sealed_files=counts,input_pins=pins,known_reader=dict(path=str(a.reader),sha256=READER_SHA,current_base_verify=True),virtual_hash_independent=True,all_current_member_hashes_checked=True,intermediate415_members_index_offsets_hashes_match_sealed_manifest=True,world_selection='ALL29 UNSELECTED; no R4PW/certificate/provenance/metadata changes or runtime/gameprogramme selection by this unit',materialization='Root authoritative known bounded streamed writer adaptation/allocation only; use expectedheader/index+MEMBERS TSV and unchangedbase/or592singlecandidateinputs. No executable fullpack writer or authorization here.',resources=dict(new_onepack_plus_C_mirror_uncompressed_bytes=2*size,proposed_metadata_budget=12*1024**2,proposed_incremental_content_bound=2*size+12*1024**2,existing_and_failed_outputs='Alreadyclosed source files counted through fresh freeC; rootledger mustretain allfailed/held namespaces andcharge samefileID allocationonce. Never silently reuse historicalquota or remove evidence.',native_compression_credit='Onlyrootauth sameSHA/readback+fileID/volume/creationtime/singlelink frozenNTFS receipt andfreshnativeallocatedquery. Unknown/symlink/outside/changedfiles conservativecharged/rejected; no logicalsize credit.',fresh_admission='RootactualCfree after remaining uncompressedpack+mirror+metadata+allpeerreservations mustremain18GiB+64MiB; include global64MiBsourcepeer exactlyonce andallotheractiveallocations. Freshcurrentguardreceipt required, nothardcodedhistoricalfree.',writer='Singleownedprocess/onewriter; read-onlysourcepins/heldnamespaces, prospectiveperwritebudget, expensiveC/ledgerprobe<=5Hz (0.2s), absolutedeadline/rootcontrolledjob/retainedprocessidentity, boundedlog, failclosed preservepartials, nooverwriteexclusivepublication, fullknownreader+all7129memberhashes+wholeSHA+WSL/Cbytecompare beforeclosure.',image_hold='Newpackdoesnotfitexisting156254208extent. Nooldextentoverwrite/programmetailreuse; freshdisc-layout/integration/programme/source/observerallocation separate.'),limits=['Compact base approximations/lookheld; original6537incl36world+20actorallbyteexact.','No netVRAM/performance/chosenLOD/physicalDreamcast acceptance fromdescriptorarithmetic.','No fullpack, mirroredpack, image, build, guest, runtime source, SD, release orthirdparty action.'])
 emit(a.out/'PLAN.json',plan)
 with(a.out/'SHA256SUMS').open('x')as t:
  for p in sorted(a.out.iterdir()):
   if p.is_file()and p.name!='SHA256SUMS':t.write(file_sha(p)+'  '+p.name+'\n')
 print(json.dumps(dict(result='PASS_SOURCE_ONLY_PLAN',pack_sha256=digest.hexdigest(),members=len(ordered),preserved=preserved,bytes=size,metadata_bytes=sum(p.stat().st_size for p in a.out.iterdir()if p.is_file()),seal=file_sha(a.out/'SHA256SUMS'))))
if __name__=='__main__':main()

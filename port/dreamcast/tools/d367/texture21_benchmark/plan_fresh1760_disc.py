#!/usr/bin/env python3
"""SOURCE ONLY fresh relocated1760 pair; programme binding deliberately pending."""
import argparse,collections,hashlib,json,mmap,os,struct,subprocess,zlib
from pathlib import Path
from mipmap_pair_plan import local
from matched_pair_readback import both,name_of
from plan_append1596 import file_sha,emit,reader
BASE_SHA='71c3d56260b4d748c2d001db08e678ec27b976ede2c70f44877fd2904774baa2'
M0_SHA='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef'
M1_SHA='1838d97ae07637fa47beed574033e2d4f79595f86fb024ace6e6e7cc752f6477'
SELECT_SHA='a8e5a20512639e775e8f31415cbcf72957236204caf11a96045dbc0e13949339'
SOURCE='63644457a2251a398de174f47be650e1b2b4c791'
FULL_TRACK=1032499200;LBA0=45000;SECTOR=2048
PROGRAMME_PATHS=['/1ST_READ.BIN','/dc/em22.ovl','/dc/em2b.ovl','/dc/em2f.ovl','/dc/em35.ovl','/dc/em3b.ovl','/dc/pl0f.ovl','/dc/pl11.ovl','/dc/pl14.ovl','/dc/sscrn.ovl','/dc/st1_0.ovl','/dc/st1_1.ovl','/dc/st1_2.ovl','/dc/st1_3.ovl','/dc/st2_0.ovl']
def require(ok,why):
 if not ok:raise ValueError(why)
def rounded(n):return(n+2047)//2048*2048
def digest(b):return hashlib.sha256(b).hexdigest()
def fnv(b):
 h=2166136261
 for v in b:h=((h^v)*16777619)&0xffffffff
 return h

def directory(view):
 pvd=bytes(view[16*2048:17*2048]);require(pvd[:7]==b'\x01CD001\x01'and view[17*2048]==255,'primary-only/noJoliet source')
 root=pvd[156:190];todo=[('',both(root,2),both(root,10))];seen=set();files={};records=[]
 while todo:
  prefix,e,n=todo.pop();require(e not in seen and e>=LBA0 and(e-LBA0)*2048+n<=len(view),'directory extent/cycle');seen.add(e);buf=view[(e-LBA0)*2048:(e-LBA0)*2048+n];off=0
  while off<len(buf):
   ln=buf[off]
   if not ln:off=(off//2048+1)*2048;continue
   rec=bytes(buf[off:off+ln]);require(len(rec)==ln and off%2048+ln<=2048,'directory record boundary');raw=rec[33:33+rec[32]]
   if raw not in(b'\0',b'\1'):
    path=prefix+'/'+name_of(rec);ee=both(rec,2);nn=both(rec,10);isd=bool(rec[25]&2);row=dict(path=path,extent=ee,bytes=nn,is_directory=isd,record_lba=e,record_offset=off,record_hex=rec.hex());records.append(row)
    if isd:todo.append((path,ee,nn))
    else:require(path not in files,'duplicate ISO path');files[path]=row
   off+=ln
 return files,records,dict(PVD_blocks=both(pvd,80),fulltrack_sectors=len(view)//2048,primary_only_noJoliet=True)

def package_inventory(pack,known,expected_sha):
 require(digest(pack)==expected_sha,'actual native pack fullSHA');count,index_crc=known.verify(pack);sha_map=bytearray();rows_digest=hashlib.sha256();counts=collections.Counter();dimensions=collections.Counter();crc_modes=collections.Counter();mips=[];sizes=collections.Counter()
 for i in range(count):
  k0,k1,off,n=struct.unpack_from('<4I',pack,2048+i*16);key='%08x-%08x'%(k0,k1);blob=pack[off:off+n];h=struct.unpack_from('<8s10I',blob);require(h[:4]==(b'RE4DCTX\0',2,48,96)and h[4]>0 and h[5]==48 and h[5]+96*h[4]<=h[6]<=n and h[6]+h[7]==n,'native Package header/descriptor extents');sha=hashlib.sha256(blob).digest();sha_map+=sha;rows_digest.update((key+' '+str(n)+' '+sha.hex()+'\n').encode());sizes['member_logical_bytes']+=n;sizes['member_sector_rounded_bytes']+=rounded(n);is_mip=False
  mode='canonical_descriptor_payload'if h[8]==zlib.crc32(blob[48:])&0xffffffff else'legacy_payload_only'if h[8]==zlib.crc32(blob[h[6]:])&0xffffffff else'unexplained';crc_modes[mode]+=1
  for j in range(h[4]):
   t=struct.unpack_from('<64s8I',blob,h[5]+96*j);require(t[4]>=h[6]and t[4]+t[5]<=n,'texture data extent');counts['descriptors']+=1;counts['payload_'+str(t[7])]+=1;counts['format_'+str(t[3])]+=1;dimensions[str(t[1])+'x'+str(t[2])]+=1;sizes['descriptor_payload_bytes']+=t[5]
   if t[6]&4:counts['mip_descriptors']+=1;counts['mip_payload_'+str(t[7])]+=1;is_mip=True
  counts['mip_packages']+=is_mip
  if is_mip:mips.append(dict(key=key,bytes=n,sha256=sha.hex()))
  if isinstance(blob,memoryview):blob.release()
 return dict(pack_sha256=expected_sha,pack_bytes=len(pack),members=count,index_crc32=index_crc,source_index_sha256=digest(pack[2048:2048+rounded(count*16)]),member_identity_digest=rows_digest.hexdigest(),counts=dict(counts),dimensions=dict(dimensions),sizes=dict(sizes),CRC_categories=dict(crc_modes),existing_mip_members=mips if expected_sha==M0_SHA else None,mip_member_identity_digest=digest(json.dumps(mips,sort_keys=True).encode())),bytes(sha_map)

def world_parity(before,after,spec,ids,classes,mesh):
 def wh(blob):
  require(len(blob)>=32,'world header');h=struct.unpack_from('<4s7I',blob);require(h[:2]==(b'R4PW',1)and h[6:]==(0,0)and len(blob)==32+16*h[3]+52*h[2]and zlib.crc32(blob[32:])&0xffffffff==h[5],'genuine R4PW CRC/counts');return h
 a=wh(before);b=wh(after);require(digest(before)==spec['original_sha256']and digest(after)==spec['candidate_sha256']and len(after)==spec['bytes'],'selected/original exactworld identities');require(a[:5]+a[6:]==b[:5]+b[6:]and a[5]==spec['canonical_source_crc']and b[5]==spec['physical_body_crc']and fnv(after)==spec['physical_file_fnv'],'source physical/canonical identity')
 changed=0
 for i in range(a[3]):
  p=before[32+i*16:48+i*16];q=after[32+i*16:48+i*16];require(p[8:]==q[8:],'non-key material/dimensions/pass/cull flags altered');changed+=p[:8]!=q[:8]
 require(before[32+16*a[3]:]==after[32+16*b[3]:],'placement bytes changed');require(len(ids)>=16 and struct.unpack_from('<4s3I',ids)==(b'R4ID',1,a[2],a[5])and len(ids)>=16+a[2],'original IDs naturally bound')
 th=struct.unpack_from('<4s5I',classes)if classes is not None else None
 if th is not None:require(th[:5]==(b'R4TC',1,1,a[3],a[5])and len(classes)==24+((a[3]+3)&~3)and th[5]==zlib.crc32(classes[24:24+a[3]])&0xffffffff,'original R4TC naturally bound')
 mh=struct.unpack_from('<4s19I',mesh);require(mh[:3]==(b'R4IM',3,len(mesh))and mh[3]==spec['mesh_crc']and mh[4:6]==(a[4],a[3])and digest(mesh)==spec['mesh_sha256']and len(mesh)==spec['mesh_bytes']and zlib.crc32(mesh[80:])&0xffffffff==mh[3],'original exact geometry/headerCRC')
 return dict(original_world_sha256=digest(before),candidate_world_sha256=digest(after),source_crc=a[5],M0_actual_header_crc=a[5],M1_physical_header_crc=b[5],M1_cert_expected_source_crc=spec['canonical_source_crc'],physical_fullfile_fnv=fnv(after),key_only_changed_parts=changed,all_non_key_material_and_placements_exact=True,geometry_exact=True,ids_header_count=a[2],ids_payload_sha256=digest(ids[16:]),classes_present=classes is not None,classes_crc=th[5]if th else None,class_histogram=dict(collections.Counter(map(str,classes[24:24+a[3]])))if classes is not None else None,metadata_bytes_unchanged_across_arms=True)

def append_layout(files,selected):
 cursor=FULL_TRACK;assets=[];pack=files['/dc/tex.pak'];require(pack['sha256']==M0_SHA and pack['bytes']==156254208,'actual original M0 identity')
 assets.append(dict(path='/dc/tex.pak',new_extent=LBA0+cursor//2048,reserved_bytes=162555904,M0=dict(bytes=156254208,sha256=M0_SHA,source='authenticated_base_file_range',source_offset=(pack['extent']-LBA0)*2048),M1=dict(bytes=162555904,sha256=M1_SHA,source='actual1760_private_pack')));cursor+=162555904
 for room,s in sorted(selected.items()):
  path='/'+s['path'];old=files[path];require((old['bytes'],old['sha256'])==(s['bytes'],s['original_sha256']),'original world baseline alignment');assets.append(dict(path=path,room=room,new_extent=LBA0+cursor//2048,reserved_bytes=rounded(s['bytes']),M0=dict(bytes=s['bytes'],sha256=s['original_sha256'],source='authenticated_base_file_range',source_offset=(old['extent']-LBA0)*2048),M1=dict(bytes=s['bytes'],sha256=s['candidate_sha256'],source_path=s['selected_path'])));cursor+=rounded(s['bytes'])
 require(len(assets)==28 and cursor==1195433984,'fresh1760 assetprefix extents');return assets,cursor

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('base','baseline','selected','candidate-pack','candidate-closeout','reader','out'):ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();require(not a.out.exists(),'preserve existing freshlayout namespace');require(a.base.stat().st_size==FULL_TRACK and file_sha(a.base)==BASE_SHA,'authenticated original-control baseimage');baseline=json.loads(a.baseline.read_text());files=baseline['files'];require(len(files)==1743 and baseline['track']['sha256']==BASE_SHA,'full1743 original-control readback')
 require(file_sha(a.selected)==SELECT_SHA,'root selected792 receipt pin');selected=json.loads(a.selected.read_text());require(len(selected['selected'])==27 and set(selected['held'])=={'r11f','r200'}and selected['world_rect21_default']==0,'root27 selected/held/default0');known=reader(a.reader);candidate_closeout=json.loads(a.candidate_closeout.read_text());require(candidate_closeout['status']=='PASS_ACTUAL_ROOT1760_CLOSED_PRIVATE_NOT_ADOPTED','actual1760 closeout')
 candidate_identity=next(p for p in candidate_closeout['pack_identities']if p['path'].lower().startswith('c:'));require(candidate_identity['sha256']==M1_SHA and candidate_identity['native_identity']['logical_bytes']==162555904,'actual candidate source identity')
 world_reports=[];metadata_refs={};host_cases=[]
 with a.base.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view:
  df,records,misc=directory(view);require(len(df)==1743 and len(records)==1874 and all((df[p]['extent'],df[p]['bytes'])==(r['extent'],r['bytes'])for p,r in files.items()),'actual directory matches sealed fullreadback')
  def get(path):
   r=files[path];b=bytes(view[(r['extent']-LBA0)*2048:(r['extent']-LBA0)*2048+r['bytes']]);require(digest(b)==r['sha256'],'baseline member identity '+path);return b
  pack_info=files['/dc/tex.pak'];pack_start=(pack_info['extent']-LBA0)*2048;packview=memoryview(view)[pack_start:pack_start+pack_info['bytes']];m0,member_sha=package_inventory(packview,known,M0_SHA);packview.release()
  for room,s in sorted(selected['selected'].items()):
   prefix='/dc/native/'+room+'/';before=get('/'+s['path']);after=local(s['selected_path']).read_bytes();ids=get(prefix+'ps2-world.ids');tc=get(prefix+'ps2-world.r4tc')if prefix+'ps2-world.r4tc'in files else None;mesh=get(prefix+'ps2-world.re4mesh');r=world_parity(before,after,s,ids,tc,mesh);r['room']=room;r['runtime_gate']='Fresh792programme policy/AREA/PCL/IDs/OCCL active witness pending';world_reports.append(r)
   for path in files:
    if path.startswith(prefix)and any(x in path for x in('interior.cell','ps2-world.r4sg','ps2-world.r4pvs')):metadata_refs[path]=files[path]
  for room,s in selected['held'].items():require(files['/'+s['path']]['sha256']==s['original_sha256'],'held room original identity must remain')
 with a.candidate_pack.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view:m1,_unused=package_inventory(view,known,M1_SHA)
 require(m0['members']==6501 and m0['counts']['mip_packages']==5 and m1['members']==7293 and m1['counts']['mip_packages']==1760,'actual original/candidate native descriptor cohorts');assets,end=append_layout(files,selected['selected']);byrecord={p:[r for r in records if r['path']==p and not r['is_directory']]for p in set(x['path']for x in assets)|set(PROGRAMME_PATHS)};require(all(len(rs)==1 for rs in byrecord.values()),'exact43 file directory patches')
 patches=[]
 for path,rs in sorted(byrecord.items()):
  r=rs[0];pos=(r['record_lba']-LBA0)*2048+r['record_offset'];patches.append(dict(path=path,record_file_offset=pos,extent_LE_BE_offset=pos+2,size_LE_BE_offset=pos+10,original_record_hex=r['record_hex'],new_extent=next((x['new_extent']for x in assets if x['path']==path),None),programme_binding_pending=path in PROGRAMME_PATHS))
 a.out.mkdir();(a.out/'M0-MEMBER-SHA256.bin').write_bytes(member_sha);emit(a.out/'PACK-DESCRIPTOR-COUNTS.json',dict(M0=m0,M1=m1,CRC_control_hold='M0487legacy_payload_only reject strictnonstreamedadopt/streamCRC1; preserve18f, exactnewprogramme policy/admission must qualify; no CRC weakening/repair by this unit'));emit(a.out/'WORLD27-SOURCE-PARITY.json',dict(status='SOURCE_BYTES_27_PARITY_RUNTIME_ACTIVE_GATES_PENDING',rooms=world_reports,shared_metadata_refs=metadata_refs,r107_area_bridge=dict(original_policy_crc='43dc8ff9',source792_guard='room107,placements71,WORLD_RECT1 explicit bridge to existing AREA table; active runtime target gate pending'),held=['r11f','r200']));emit(a.out/'ASSET-APPEND-LAYOUT.json',dict(assets=assets,base_fulltrack_bytes=FULL_TRACK,pack_LBA=549150,assetprefix_end_bytes=end,new_programme_start_LBA=LBA0+end//2048,programme15_after_assets=PROGRAMME_PATHS));emit(a.out/'DIRECTORY-PATCH-CONTRACT.json',dict(records=patches,PVD_volume_LE_BE_offset=16*2048+80,PVD_before=misc['PVD_blocks'],PVD_after=None,extent_and_size_patches_only=True,primary_only_noJoliet=True,files1743_unchanged_count=True,held_originals_not_relocated=['r11f','r200']))
 plan=dict(status='SOURCE_ONLY_ASSET_LAYOUT_READY_PROGRAMME792_PENDING_NO_IMAGE_ALLOCATION',source792=SOURCE,base=dict(path=str(a.base),sha256=BASE_SHA,bytes=FULL_TRACK,all1743readback_path=str(a.baseline),all1743readback_sha256=file_sha(a.baseline),same_complete_old_track_preserved_except_directory_PVD=True),selected27_root_receipt=dict(path=str(a.selected),sha256=SELECT_SHA,held=['r11f','r200']),M0_pack=dict(sha256=M0_SHA,bytes=156254208,members=6501,actual_preexisting_mips=5,member_binary_sha256=digest(member_sha),actual_native_counts='PACK-DESCRIPTOR-COUNTS.json',legacy487_hold=True),M1_pack=dict(path=str(a.candidate_pack),sha256=M1_SHA,bytes=162555904,members=7293,mips=1760,actual_closeout_path=str(a.candidate_closeout),actual_closeout_sha256=file_sha(a.candidate_closeout)),asset_append_end_bytes=end,asset_common_capacity=True,programme_binding=None,programme_hold='New792qualified actualprogramme/ELF/all15flags/source/toolclosure+slotheaderimageID required; do not reuse69f/1748 or guessedhash. All15newprogrammefiles append afterassets in identical physicalorder/capacities acrossarms; compute finalLBAs/PVD/wholeimageSHA only after freeze.',programme_required_paths=PROGRAMME_PATHS,arm_asset_differences=['/dc/tex.pak']+['/'+s['path']for s in selected['selected'].values()],comparison='FULLtexturepipeline: original6501 with5protectedmips vs1760(compact/VQ/mips/scoped792). Not globallymipOFF or isolatedmips causality; filteredlook/approximation sourceproof distinct.',resources_proposal=dict(one_image_bytes_formula=str(end)+' + sum(roundup(qualified15programmebytes,2048))',two_image_bytes_formula='2*one_image_bytes + actualsmalltracks_GDI + rootmetadatacap',allocated=False,NTFS_credit='Only after full1743independentreadback/frozenfullSHA/nativeID+freshallocated receipt; no hypothetical compressioncredit',freshguards='18GiB+64MiB+global64MiBsourcepeer+otherallocations; actualallfiles/partials/failed/closed chargedonce; newnamespace/nooverwrite/rootowned51orapprovedwriter/130job bounds reviewed before allocation'),readback_hold='Newreadback must allow explicit43 relocated files, verify1743 fullfileSHA+all1874directory records,28asset differences/all15programme identical, unchanged IP/smalltracks and exactnewPVD/tracksize. OldallLBAs-preserved verifier cannot certify newlayout.',functional_hold='New cold lineage first; newELF/DWARF/phase observer and exactstageidentities before guest; no oldprogramme state transfer. Macro/admission/metadata/look/VRAM and baseline487CRC route gates required beforepairedperformance.',images_written=0)
 emit(a.out/'PLAN.json',plan);(a.out/'SHA256SUMS').write_text(''.join(file_sha(p)+'  '+p.name+'\n'for p in sorted(a.out.iterdir())if p.is_file()));print(json.dumps(dict(status=plan['status'],assetprefix_end=end,programme_start_LBA=LBA0+end//2048,M0_mips=5,M0_legacy_payload_CRC=487,M1_mips=1760,seal=file_sha(a.out/'SHA256SUMS'),metadata_bytes=sum(p.stat().st_size for p in a.out.iterdir()))))
if __name__=='__main__':main()

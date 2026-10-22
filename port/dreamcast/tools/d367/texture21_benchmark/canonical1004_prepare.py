#!/usr/bin/env python3
"""Bind the already-qualified canonical1004 inputs; no assessment/composition."""
import argparse,json,hashlib
from pathlib import Path
from mipmap_pair_plan import sha,local
SOURCE='0425534d848973c1dae3ab960d0006ac9afcf363'
MANIFEST='acf4abe0a6d449f31aaefa8ab7046cd14265b625edf90a03b429f7cd040ba7c6'
PACK='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62'
def emit(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def prepare(manifest,pack,out):
 if sha(manifest)!=MANIFEST:raise ValueError('canonical manifest drift')
 m=json.loads(manifest.read_text());v=m['virtual']
 if m['source']['integrated_commit']!=SOURCE or v['members']!=6537 or v['mips']!=1004 or v['total_header_repairs']!=171 or v['pack_sha256']!=PACK:raise ValueError('wrong frozen canonical family')
 if pack.stat().st_size!=156248064 or sha(pack)!=PACK:raise ValueError('actual closed pack identity')
 sm={}
 for w in m['world_sidecars']:
  c=w['candidate'];p=local(c['path'])
  if p.stat().st_size!=c['bytes']or sha(p)!=c['sha256']:raise ValueError('canonical sidecar drift')
  sm['/'+w['path']]={'source_path':str(p),'bytes':c['bytes'],'sha256':c['sha256']}
 if set(sm)!={'/dc/native/'+r+'/ps2-world.r4pw'for r in ['r100','r101','r103']}:raise ValueError('exact three world family required')
 for row in m['source']['integrated_files']:
  p=local(row['path'])
  if p.stat().st_size!=row['bytes']or sha(p)!=row['sha256']:raise ValueError('integrated table/certificate/source drift')
 normalized={'schema':'canonical1004-stream-input-adapter1','virtual':v,'sidecars':m['world_sidecars'],'pipeline_label':'FULL texture pipeline: M0original6501 versus canonical1004 (compact/VQ+mips+36scopedworld+20actor); original control retains protected existing Ganado mips, not globally mip-off or isolated mip-only attribution.','canonical_manifest_reference':{'path':str(manifest),'sha256':MANIFEST,'scope':'Original immutable source composition reused; no cohort reassessment. Its virtual pack_written:false predates actual owner-qualified materialization below.'},'actual_closed_pack':{'path':str(pack),'bytes':pack.stat().st_size,'sha256':sha(pack),'owner_full_reader_qualification':'Root reports all6537 members/fullhash/readback/bytecompare PASS. This adapter checks wholeartifactSHA only; does not repeat assessment.'}}
 emit(out/'canonical-inputs.json',normalized);emit(out/'candidate-worlds.json',sm)
 resources={'status':'SOURCE_PLAN_ONLY_NO_STAGE_OR_GUEST_ALLOCATION','source':SOURCE,'manifest_sha256':MANIFEST,'actual_pack':normalized['actual_closed_pack'],'original_pack_bytes':156254208,'candidate_pack_bytes':156248064,'original_slot_slack_bytes':6144,'index_members':6537,'index_capacity':6656,'remaining_index_slots':119,'candidate_first':True,'first_arm_hard_cap_bytes':1288490189,'peer_reservation_bytes':134217728,'other_source_reservation_bytes':67108864,'combined_peer_reservation_bytes':201326592,'runtime_floor_bytes':18*1024**3+64*1024**2,'new_source_tools_metadata_limit':4*1024**2,'pack_reservation':'Actualpackclosed; alreadycharged through Cfree/ownerbudget, no newpack reservation/copy','sequence':['Root allocates only M1 candidate writer after fullprogramme/static/source-plan and correctedguard review.','M1 full1743 readback then root NTFScompression; sameuncompressedSHA/singlelink/fileID/nativeallocated/query receipt, no rawdeletion.','Root allocates concrete TWOarm aggregate only from actualcreditedM1allocation +M0prospectiveuncompressed+metadata/failures andfreshCfree+peers. Do not assume bothfit1.2GiB, silentlyraisecap orlowerfloor.','FreshactualELF ABI/phase/control/perkeydraw oracle required beforeanyguest.'],'runtime_oracle_limits':'New69f actualCU/DIE/path/pointer/duplicate/phase binding pending. Admission/native load success is not emittedTCW/miplevel proof. HeaderTCW31+physicaldimensions+UV owner join beforedrawclaims; automaticselectedLOD stillrequiresPVRderivative/hardwareevidence. Farmcows/chickens/ambientr103dog off; scriptedr100dog/crows/traps sceneeligible, conditionalLVQ/GVQ/pl08 remain separate.','source_and_pixel_limits':'Reuse all sourcecontracts/CRCqualifiedcohorts; keep approximationRMSE/basepixels distinct from filteredrender look and performance; no tolerance/cherrypick/replay edits. Farm/woods primary; r101nine separatelydeclared.'}
 emit(out/'resource-and-qualification-plan.json',resources)
 return {'normalized_sha256':sha(out/'canonical-inputs.json'),'candidate_worlds_sha256':sha(out/'candidate-worlds.json'),'resources_sha256':sha(out/'resource-and-qualification-plan.json'),'pack_slot_slack':6144,'images_written':0}
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ['manifest','pack','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();print(json.dumps(prepare(a.manifest,a.pack,a.out)))
if __name__=='__main__':main()

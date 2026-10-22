#!/usr/bin/env python3
"""Prepare immutable nativeworld/table/certificate proposals; no active input or full pack writes."""
from pathlib import Path
import collections,hashlib,json,struct,sys,zlib
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parent),str(HERE.parents[1])]
import world_bindings as world

def sha(b):return hashlib.sha256(b).hexdigest()
def fnv(b):
 h=2166136261
 for x in b:h=((h^x)*16777619)&0xffffffff
 return h
def main():
 O=Path(sys.argv[1]);prior=Path(sys.argv[2])if len(sys.argv)>2 else None;r=json.loads((O/'conversion-receipt.json').read_text());assert r['converted_keys']in(415,177,4,18)and not r['held'];mapping={x['original_key']:x for x in r['selected']};R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021');bind=json.loads((R/'native-bindings-01/bindings.json').read_text());files=json.loads((R/'image-plan-04/baseline-file-identities.json').read_text())['files'];B=R/'standalone-B-01/gdemu/track03.iso'
 count=len(mapping);parent_count=json.loads((prior/'world-proposals.json').read_text())['combined_scoped_keys']if prior else 36;combined_count=parent_count+count
 canon_root=Path('/root/re4data/private/texture-world36-canonical-crc-20261021');worlds=[];covered=collections.Counter();certs=[];table=[]
 for x in r['selected']:
  a,b=(int(y,16)for y in x['scoped_key'].split('-'));w,h=x['logical'];s=x['physical'][0]
  table.append('{0x%08xU,0x%08xU,%dU,%dU,{%dU,%dU,0U,4U,%dU,%dU,0x%08xU},1.0f,1.0f},'%(a,b,w,h,s,s,x['payload_type'],x['candidate_payload'],x['candidate_crc32']))
 with B.open('rb')as iso:
  for item in bind['matched_worlds']:
   name=item['path'];room=name.split('/')[2];original=(R/'native-bindings-01/inputs'/name).read_bytes();assert sha(original)==item['sha256'];oldhead=struct.unpack_from('<4s7I',original);parent=(prior/'proposed-worlds'/name)if prior else(canon_root/name);base=parent.read_bytes()if parent.exists()else original
   rows=world.inspect_sidecar(base);out=bytearray(base);changes=[];allowed=set(range(20,24))
   for row in rows:
    x=mapping.get(row['key'])
    if x is None:continue
    assert [row['width'],row['height']]==x['logical'];ref=next(z for z in x['world_refs']if z['world']==name and z['part']==row['part']);assert all(ref[k]==row[k]for k in('width','height','render_pass','cull','texture','flags'))
    at=32+16*row['part'];key=tuple(int(z,16)for z in x['scoped_key'].split('-'));struct.pack_into('<II',out,at,*key);allowed.update(range(at,at+8));changes.append(dict(part=row['part'],source_key=row['key'],candidate_key=x['scoped_key'],render_pass=row['render_pass'],flags=row['flags'],texture_slot=row['texture']));covered[row['key']]+=1
   if not changes and(base==original or count==18):continue
   struct.pack_into('<I',out,20,zlib.crc32(out[32:])&0xffffffff);assert len(out)==len(base)==len(original)and all(a==b or n in allowed for n,(a,b)in enumerate(zip(base,out)))
   # Existing36 remain byteexact where no new415 key is selected; no geometry/UV/material field changed.
   part_end=32+16*oldhead[3];assert out[part_end:]==original[part_end:]
   for n in range(oldhead[3]):assert out[32+16*n+8:48+16*n]==original[32+16*n+8:48+16*n]
   after=world.inspect_sidecar(bytes(out));assert len(after)==len(rows)
   mesh_name='/'+name.replace('ps2-world.r4pw','ps2-world.re4mesh');m=files[mesh_name];iso.seek((m['extent']-45000)*2048);mh=hashlib.sha256();left=m['bytes'];header=None
   while left:
    chunk=iso.read(min(left,1024*1024));assert chunk
    if header is None:header=chunk[:80]
    mh.update(chunk);left-=len(chunk)
   assert mh.hexdigest()==m['sha256'];h=struct.unpack_from('<4s19I',header);assert h[0]==b'R4IM'and h[2]==m['bytes']and h[4]==oldhead[4]and h[5]==oldhead[3]
   physical=struct.unpack_from('<I',out,20)[0];roomnum=int(room[1:],16);c=(roomnum,len(out),oldhead[2],oldhead[3],oldhead[4],physical,fnv(out),h[3],m['bytes'],oldhead[5]);certs.append('{0x%03xU,%dU,%dU,%dU,%dU,0x%08xU,0x%08xU,0x%08xU,%dU,0x%08xU},'%c)
   dest=O/'proposed-worlds'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(out)
   worlds.append(dict(path=name,room=room,source_original_sha256=sha(original),parent_sha256=sha(base),parent_is_canonical36=prior is None and base!=original,parent_lineage=str(parent),candidate_sha256=sha(out),bytes=len(out),physical_body_crc=physical,physical_file_fnv=fnv(out),original_source_crc=oldhead[5],mesh_sha256=m['sha256'],mesh_bytes=m['bytes'],mesh_crc=h[3],parts=oldhead[3],placements=oldhead[2],meshes=oldhead[4],new_key_only_records=len(changes),changes=changes,all_other_part_fields_and_placement_UVs_byteexact=True,consumer_hold='HARDHOLD_AREA_baseline_originalCRC43dc8ff9_differs_table9081e7fd; generic_policy_argument_fix_insufficient'if room=='r107'else'New world-specific coupled/lifetime acceptance not claimed; parent selects/integrates exact cohort'))
 assert set(covered)==set(mapping)and all(covered[k]==len(mapping[k]['world_refs'])for k in covered)
 (O/('proposed_scoped_representations_add%d.inc'%count)).write_text('// PRIVATE PROPOSAL ONLY:%d new immutable keys; no active header modification.\n'%count+'\n'.join(table)+'\n')
 current=((prior/('proposed_scoped_representations_combined%d.inc'%parent_count))if prior else(HERE/'scoped_representations.inc')).read_bytes();(O/('proposed_scoped_representations_combined%d.inc'%combined_count)).write_bytes(current+b'\n// PRIVATE NEXT COHORT PROPOSAL, unselected\n'+'\n'.join(table).encode()+b'\n')
 (O/'proposed_provenance_certificates.inc').write_text('// PRIVATE geometry/material-policy tuples; active helper/table remain unchanged.\n'+'\n'.join(certs)+'\n')
 report=dict(status='PRIVATE_WORLD_PROPOSAL_NOT_ACTIVE_OR_TARGET_ACCEPTANCE',converted_keys=count,new_native_material_refs=sum(covered.values()),rooms=len(worlds),worlds=worlds,world_alias_coverage_exact=True,texture_slot_zero_refs=sum(c['texture_slot']==0 for w in worlds for c in w['changes']),new_OP=sum(c['render_pass']==0 for w in worlds for c in w['changes']),new_VA=sum(bool(c['flags']&1)for w in worlds for c in w['changes']),combined_scoped_keys=combined_count,source_original_metadata_unchanged=True,source_compiled_frozen='0425534d848973c1dae3ab960d0006ac9afcf363',programme_frozen='733afabf6567a9f086eacb48b70559aef764cf52a5b534f44602da3a8bc68a9e',canonical1004_frozen='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62',limits=['Private proposedworld copies only, all current canonical36 worlds untouched.','Codebook retained, filtered baseRGB approximation; mesh/UV/placement/pass/cull/textureindex/VA bytes exact.','No blanket future runtime eligibility; r107 AREA baseline originalCRC/table mismatch remains explicit HARDHOLD; r11f/r200 physical ownership also held. Current three-room certificate helper is not modified.','Original R4ID/R4TC/PCL/OCCL/SG bytes remain original; fresh expanded policy/lifetime gates/main selection required before new programme/image.'])
 (O/'world-proposals.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('converted_keys','new_native_material_refs','rooms','new_OP','new_VA','texture_slot_zero_refs')}))
if __name__=='__main__':main()
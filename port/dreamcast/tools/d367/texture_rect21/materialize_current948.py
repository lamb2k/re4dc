#!/usr/bin/env python3
"""Materialize the frozen 948-mip/scoped17 data overlay without staging a game."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,struct,subprocess,sys,time
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parent),str(HERE.parents[1])]
import texpack
from vram.vq_pak import read_pak
import world_bindings
BASE='e19cfc464e789e97ca96864adfc2a4cd44443a9f4775bebd842c3e184a65559b'
EXPECTED='bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026'
BUDGET=512*1024**2;START_FLOOR=18*1024**3+768*1024**2;RUN_FLOOR=18*1024**3+64*1024**2

def sha(blob):return hashlib.sha256(blob).hexdigest()
def file_sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def key(text):return tuple(int(x,16) for x in text.split('-'))
def name(value):return '%08x-%08x'%value
def json_bytes(value):return (json.dumps(value,indent=2)+'\n').encode()
def free():return shutil.disk_usage('/mnt/c').free
def guard():
 if free()<RUN_FLOOR:raise RuntimeError('C runtime floor18GiB+64MiB')

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for v in ['base-pack','reference-pack','fixture','binding-root','plan','out','mirror','evidence']:ap.add_argument('--'+v,type=Path,required=True)
 a=ap.parse_args();started=time.monotonic();initial=free();assert initial>=START_FLOOR,'C fresh start floor18GiB+768MiB'
 assert not a.out.exists() and not a.mirror.exists() and not a.evidence.exists(),'Preserve prior output'
 raw=a.base_pack.read_bytes();reference_raw=a.reference_pack.read_bytes();plan_raw=a.plan.read_bytes();plan=json.loads(plan_raw);fixture_raw=(a.fixture/'receipt.json').read_bytes();fixture=json.loads(fixture_raw)
 assert sha(raw)==BASE==plan['base_pack_sha256'];assert plan['expected_combined_pack_sha256']==EXPECTED
 assert sha(reference_raw)==fixture['source_pack_sha256']==plan['reference_pack_sha256']
 texpack.verify(raw);texpack.verify(reference_raw);base=read_pak(raw);reference=read_pak(reference_raw)
 assert len(base)==len(reference)==6501 and set(base)==set(reference)
 inherited={k for k in base if base[k]!=reference[k]};assert len(inherited)==1077
 merged=dict(base);added={};selected={r['original_key']:r for r in fixture['selected']};assert len(selected)==17
 for row in selected.values():
  old,new=key(row['original_key']),key(row['scoped_key']);assert new not in merged
  assert sha(base[old])==row['source_sha256'];blob=(a.fixture/'textures'/(row['scoped_key']+'.re4tex')).read_bytes();assert sha(blob)==row['candidate_sha256'];added[new]=blob;merged[new]=blob
 reserved={key(v) for v in fixture['reserved_atlas_keys']};assert not(set(added)&reserved) and not(set(base)&reserved),'Atlas additions remain separate'
 combined,count=texpack.build(merged);texpack.verify(combined);assert count==6518 and sha(combined)==EXPECTED
 parsed=read_pak(combined);assert set(parsed)==set(base)|set(added)
 assert all(parsed[k]==v for k,v in base.items()) and all(parsed[k]==v for k,v in added.items())
 protected=key('6da8c35b-a936da0c');assert parsed[protected]==base[protected]
 membership=[dict(key=name(k),base_sha256=sha(base[k]) if k in base else None,reference_sha256=sha(reference[k]) if k in reference else None,output_sha256=sha(parsed[k]),bytes=len(parsed[k]),inherited_change=k in inherited,kind='base-preserved' if k in base else 'scoped17-appended') for k in sorted(parsed)]
 sidecars={};side_proofs=[];expected_paths={'dc/native/r100/ps2-world.r4pw','dc/native/r103/ps2-world.r4pw'}
 assert {v['path'] for v in fixture['worlds']}==expected_paths
 for row in fixture['worlds']:
  path=row['path'];old=(a.binding_root/'inputs'/path).read_bytes();new=(a.fixture/path).read_bytes();assert sha(old)==row['source_sha256'] and sha(new)==row['candidate_sha256']
  before=world_bindings.inspect_sidecar(old);after=world_bindings.inspect_sidecar(new);assert len(before)==len(after) and len(old)==len(new)
  changed=[];allowed=set(range(20,24))
  for p,q in zip(before,after):
   wanted=selected[p['key']]['scoped_key'] if p['key'] in selected else p['key'];assert q['key']==wanted
   assert all(p[field]==q[field] for field in p if field!='key')
   if wanted!=p['key']:
    changed.append(p['part']);allowed.update(range(32+16*p['part'],40+16*p['part']))
  assert changed==[v['part'] for v in row['changed_parts']]
  assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(old,new)))
  part_end=32+16*len(before);assert old[part_end:]==new[part_end:]
  assert all(key(q['key']) in parsed for q in after if q['texture'])
  sidecars[path]=new;side_proofs.append(dict(path=path,bytes=len(new),source_sha256=sha(old),output_sha256=sha(new),frozen_copy_exact=True,part_count=len(before),changed_parts=changed,unchanged_logical_material_fields=True,placements_byte_exact=True,only_key_words_and_body_crc_changed=True))
 proof=json_bytes(dict(schema='re4dc-rect21-combined-membership-1',members=membership,all6501_base_members_byte_exact=True,all1077_inherited_changes_preserved=True,only17_scoped_keys_appended=True,protected_efm=dict(key=name(protected),base_sha256=sha(base[protected]),output_sha256=sha(parsed[protected]),preserved_exact=True),sidecars=side_proofs))
 receipt=dict(schema='re4dc-rect21-current948-scoped17-data-1',scope='Data overlay only. No program, disc stage, guest, runtime/source or production recipe change.',base_pack_sha256=BASE,base_pack_bytes=len(raw),candidate_pack_sha256=EXPECTED,candidate_pack_bytes=len(combined),archive_delta_bytes=len(combined)-len(raw),base_members_preserved_exact=6501,inherited_original_changes_preserved=1077,appended_members=17,output_members=6518,protected_efm_key=name(protected),reserved_atlas_keys=fixture['reserved_atlas_keys'],fixture_receipt_sha256=sha(fixture_raw),integration_plan_sha256=sha(plan_raw),membership_proof_sha256=sha(proof),sidecars=side_proofs,runtime_source='004cf224674fa60cf08dc10e641c723de238a0fd or main reviewed matching integration',runtime_program=None,required_knobs=plan['required_knobs'],allocation=dict(max_total_new_bytes=BUDGET,start_floor_bytes=START_FLOOR,runtime_floor_bytes=RUN_FLOOR,forecast_scope='exact logical output files plus exact mirror; small evidence reserve included',planned_total_payload_bytes=0),limits=['Selected base6501 members are unchanged, including1077 pre-existing changes versus original. This does not restore all original-reference bytes.','Atlas2 and heldr101nine remain excluded. No input pack or frozen fixture is changed.','Archive grows69632 bytes. Texture payload/request figures are source accounting, not actual target allocation or performance.','Main owns program/source freeze and target qualification; no full-build, staging, look, regression, timing, release or physical Dreamcast acceptance here.'])
 payload={'tex.pak':combined,**sidecars,'membership-proof.json':proof}
 # Include receipt/self size and manifest in an exact fixed-point logical forecast.
 for _ in range(8):
  payload['qualification.json']=json_bytes(receipt)
  sums=''.join(f'{sha(blob)}  {path}\n' for path,blob in sorted(payload.items())).encode();single=sum(map(len,payload.values()))+len(sums);total=single*2+32768
  if receipt['allocation']['planned_total_payload_bytes']==total:break
  receipt['allocation']['planned_total_payload_bytes']=total
 else:raise RuntimeError('Forecast did not converge')
 assert total<=BUDGET and initial-total>=RUN_FLOOR,'Measured output+mirror cannot fit allocation/floor'
 assert free()>=START_FLOOR and free()-total>=RUN_FLOOR,'Fresh pre-output headroom check'
 # Nothing above this line creates output directories or files.
 a.evidence.mkdir(parents=True);a.out.mkdir(parents=True)
 reservation=dict(pid=os.getpid(),proc_start=Path('/proc/self/stat').read_text().split()[21],source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),planned_logical_output_bytes=single,planned_output_plus_mirror_and_evidence_reserve_bytes=total,budget_bytes=BUDGET,c_free_before_bytes=initial,guards=dict(start=START_FLOOR,runtime=RUN_FLOOR))
 reservation_blob=json_bytes(reservation)
 with (a.evidence/'reservation.json').open('xb') as reservation_file:assert reservation_file.write(reservation_blob)==len(reservation_blob)
 written=0
 def write(path,blob):
  nonlocal written
  guard();path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as f:
   for at in range(0,len(blob),4*1024**2):guard();chunk=blob[at:at+4*1024**2];written+=f.write(chunk)
  assert file_sha(path)==sha(blob)
 for path,blob in sorted(payload.items()):write(a.out/path,blob)
 write(a.out/'SHA256SUMS',sums)
 a.mirror.mkdir(parents=True)
 for path in sorted(payload):
  src=a.out/path;guard();dst=a.mirror/path;dst.parent.mkdir(parents=True,exist_ok=True)
  with src.open('rb') as source,dst.open('xb') as dest:
   while True:
    guard();chunk=source.read(4*1024**2)
    if not chunk:break
    written+=dest.write(chunk)
  assert file_sha(src)==file_sha(dst)==sha(payload[path])
 write(a.mirror/'SHA256SUMS',sums)
 expected=set(payload)|{'SHA256SUMS'}
 for root in [a.out,a.mirror]:
  assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==expected
  assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()}=={'dc','dc/native','dc/native/r100','dc/native/r103'}
  for line in sums.decode().splitlines():
   digest,path=line.split('  ',1);assert file_sha(root/path)==digest
 assert written==single*2
 result=dict(**reservation,completed=True,actual_new_logical_data_bytes=single,actual_output_and_mirror_bytes_written=written,expected_output_and_mirror_bytes=single*2,budget_remaining_bytes=BUDGET-written,c_free_after_bytes=free(),c_free_delta_observed_bytes=initial-free(),c_free_delta_caution='Host free-space delta includes other work and filesystem effects; it is not attributed write cost.',elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(sums),pack_sha256=EXPECTED,output=str(a.out),mirror=str(a.mirror),exact_file_count_per_copy=len(expected),exact_directory_set_verified=True,all_member_semantics_verified=True)
 result.update(actual_evidence_bytes_written=0,actual_all_job_output_bytes_written=0)
 for _ in range(8):
  completion_blob=json_bytes(result);evidence_bytes=len(reservation_blob)+len(completion_blob)
  if result['actual_evidence_bytes_written']==evidence_bytes:break
  result['actual_evidence_bytes_written']=evidence_bytes;result['actual_all_job_output_bytes_written']=written+evidence_bytes
 else:raise RuntimeError('Completion byte cost did not converge')
 assert evidence_bytes<=32768 and written+evidence_bytes<=BUDGET
 with (a.evidence/'completion.json').open('xb') as completion_file:assert completion_file.write(completion_blob)==len(completion_blob)
 guard();print(json.dumps(result))
if __name__=='__main__':main()

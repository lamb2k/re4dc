#!/usr/bin/env python3
"""Prepare an exact read-only combination receipt; never stage or write a pack."""
from pathlib import Path
import argparse,hashlib,json,sys
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE.parent),str(HERE.parents[1])]
import texpack
from vram.vq_pak import read_pak

def sha(blob):return hashlib.sha256(blob).hexdigest()
def key(value):return tuple(int(v,16) for v in value.split('-'))
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['reference-pack','base-pack','fixture','out']:ap.add_argument('--'+k,type=Path,required=True)
 ap.add_argument('--protect-key',action='append',default=[])
 a=ap.parse_args();assert not a.out.exists(),'Preserve prior combination receipt'
 fixture=json.loads((a.fixture/'receipt.json').read_text());reference_blob=a.reference_pack.read_bytes();base_blob=a.base_pack.read_bytes();assert sha(reference_blob)==fixture['source_pack_sha256']
 texpack.verify(reference_blob);texpack.verify(base_blob);reference=read_pak(reference_blob);base=read_pak(base_blob)
 assert len(reference)==6501 and set(reference)<=set(base),'Selected base drops original keys'
 assert all(key(name) in base for name in a.protect_key),'Protected key absent from selected base'
 merged=dict(base);overlays=[]
 for row in fixture['selected']:
  old,new=key(row['original_key']),key(row['scoped_key']);assert old in base and new not in base,'Scoped key collision or missing source'
  assert sha(base[old])==row['source_sha256'],'Base changed the selected rectangular source; requalification required'
  path=a.fixture/'textures'/(row['scoped_key']+'.re4tex');blob=path.read_bytes();assert sha(blob)==row['candidate_sha256'];merged[new]=blob;overlays.append(dict(key=row['scoped_key'],sha256=sha(blob),bytes=len(blob),file=str(path)))
 combined,count=texpack.build(merged);texpack.verify(combined);parsed=read_pak(combined);assert all(parsed[k]==v for k,v in base.items()) and count==len(base)+17
 r=dict(schema='re4dc-rect21-readonly-integration-1',scope='Read-only expected combination receipt. No pack, game image, build or guest was written.',required_source='004cf224674fa60cf08dc10e641c723de238a0fd or reviewed integration containing exact guarded runtime/helper hashes',required_knobs={'WORLD_RECT21':1,'CAST_MIPMAP':1,'PS2_WORLD_DRAW':1,'PS2_WORLD_MESH':1,'MESH_DIRECT':1},reference_pack_sha256=sha(reference_blob),base_pack_sha256=sha(base_blob),base_members=len(base),protected_base_members=[dict(key=name,sha256=sha(base[key(name)]),bytes=len(base[key(name)]),preserved_exact=parsed[key(name)]==base[key(name)]) for name in a.protect_key],base_changes_inherited_from_original=sum(base[k]!=v for k,v in reference.items()),all_base_members_preserved_exact=len(base),append_members=overlays,expected_combined_pack_sha256=sha(combined),expected_combined_pack_bytes=len(combined),expected_combined_members=count,archive_delta_from_selected_base=len(combined)-len(base_blob),native_sidecar_overlays=[dict(path=v['path'],source_sha256=v['source_sha256'],sha256=v['candidate_sha256'],file=str(a.fixture/v['path'])) for v in fixture['worlds']],protected_global_atlas_keys=fixture['reserved_atlas_keys'],limits=['Install only the2 exact sidecar overlays together with appended17 packages and the exact enabled guarded program.','The supplied standalone fixture pack is based on original6501 bytes. Do not install it over another texture candidate and silently drop inherited changes; rebuild the selected combination and check this receipt.','Keep baseline controls on original sidecars/assets. Checkpoints belong to exact program/image identities and cannot be transplanted.','Physical residency, originals/candidate coexistence, visible look, gameplay/frame-time, complete-program OFF identity and release/hardware checks remain open.'])
 a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['base_members','base_changes_inherited_from_original','all_base_members_preserved_exact','expected_combined_pack_sha256','expected_combined_members','archive_delta_from_selected_base']}))
if __name__=='__main__':main()

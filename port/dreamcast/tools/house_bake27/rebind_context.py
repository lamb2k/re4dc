"""Explicitly re-pin a bake to an unchanged ordered shell in a new room context."""
import argparse,copy,hashlib,json
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__)
for name in ('original-exchange','new-exchange','atlas','out'):ap.add_argument('--'+name,type=Path,required=True)
a=ap.parse_args();assert not a.out.exists()
old=json.loads(a.original_exchange.read_text());new=json.loads(a.new_exchange.read_text());atlas=json.loads(a.atlas.read_text())
assert atlas['geometry_candidate_sha256']==old['candidate_sha256']
for role in ('wall','roof'):
 assert old[role]['source']==new[role]['source'] and old[role]['target']==new[role]['target'],'C9 source/target ordered geometry/UV/prelight must remain exact'
 assert old[role]['uv_origin_step']==new[role]['uv_origin_step'] and old[role]['source_material_key']==new[role]['source_material_key']
result=copy.deepcopy(atlas);result['geometry_candidate_sha256']=new['candidate_sha256']
result['context_migration']=dict(old_candidate_sha256=old['candidate_sha256'],new_candidate_sha256=new['candidate_sha256'],old_exchange_sha256=hashlib.sha256(a.original_exchange.read_bytes()).hexdigest(),new_exchange_sha256=hashlib.sha256(a.new_exchange.read_bytes()).hexdigest(),source407_and_target107_geometry_uv_prelight_exact=True,baked_pixels_unchanged=True,reason='Use original pinned A room context; remove inherited C8 omissions outside the chosen core')
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['context_migration'],indent=2))

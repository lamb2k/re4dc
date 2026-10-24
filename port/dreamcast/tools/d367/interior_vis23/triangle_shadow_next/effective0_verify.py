"""Independent effective0 fact verifier from the final copied physical package."""
from pathlib import Path
import feasibility as f
EXPECTED_CAPABILITY_GUARD='#if !defined(RE4DC_PS2_PVS_EFFECTIVE0_SOURCES) || RE4DC_PS2_PVS_EFFECTIVE0_SOURCES != 1 || \\\n    !defined(RE4DC_PS2_WORLD_NONEMPTY_LOD) || RE4DC_PS2_WORLD_NONEMPTY_LOD != 1\n#error Effective-only0 source certificate requires reviewed capability and actual nonempty fallback\n#endif\n'


def verify(receipt,root,repo,pack):
 root=Path(root);repo=Path(repo)
 for name,digest in f.audit.FROZEN_INPUT_SHA256.items():
  path=root/name
  if f.digest(path)!=digest or receipt['final_inputs'].get(name)!=f.identity(path):raise ValueError('Final input/report pin mismatch '+name)
 if type(receipt.get('enabled')) is not bool or type(receipt.get('nonempty')) is not bool:raise ValueError('Capability values must be explicit booleans')
 p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw');policy=(root/'ps2-world.r4pw').read_bytes();ids=(root/'ps2-world.ids').read_bytes()[16:16+len(p.placements)];fields=f.audit.conditional_fields(ids);materials,mpins=f.material_census(repo,Path(pack),p)
 if mpins!=receipt['material_pins']:raise ValueError('Actual material pins changed')
 expected=[]
 if receipt['enabled'] and not receipt['nonempty']:raise ValueError('Missing real fallback')
 for pi,pl in enumerate(p.placements):
  mesh=p.meshes[pl['mesh']];_,det=f.mapping(p,pi)
  for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
   m=p.pmeta[part];ordinary=m['pass_']==0 and m['cull'] in (0,2) and not(policy[32+16*part+15]&1)
   if not det or pl['placement'] in fields or not ordinary or not materials[part]['eligible']:continue
   first,n=p.plod[part]
   for ci in range(first,first+n):
    cl=p.clusters[ci];levels=[p.levels[cl['first_level']+j] for j in range(cl['level_count'])];counts=[x[1] for x in levels]
    if not receipt['enabled'] or not receipt['nonempty'] or len(counts)<2 or not counts[0]:continue
    # Independently enumerate actual fallback for EVERY raw choice.
    mapped=[]
    for raw in range(len(counts)):
     effective=raw
     while effective>0 and counts[effective]==0:effective-=1
     mapped.append(effective)
    if any(lv!=0 for lv in mapped):continue
    fm,nm,_=levels[0];keys=set()
    for li in range(fm,fm+nm):
     corners,triangles=p.let_tris(li)
     for tri in triangles:
      points=tuple(tuple(0 if mesh['step'][k]==0 else int(corners[j][k]) for k in range(3)) for j in tri);key=f.audit.canonical(points)
      if key is not None:keys.add(key)
    expected.append(dict(placement=pi,field=pl['placement'],part=part,cluster=ci,meshlet_counts=counts,effective_source_levels=[0],raw_to_effective=mapped,base_first_meshlet=fm,base_meshlet_count=nm,oriented_faces=len(keys)))
 if receipt['clusters']!=expected or receipt['physical_clusters']!=len(expected) or receipt['oriented_faces']!=sum(r['oriented_faces'] for r in expected):raise ValueError('Effective source facts do not match final package')
 if receipt.get('capability_guard') != (EXPECTED_CAPABILITY_GUARD if expected else ''):raise ValueError('Noncanonical source capability requirement')
 if receipt.get('runtime_admitted_cuts')!=0:raise ValueError('Source facts cannot assert runtime cuts')
 for name,digest in f.audit.FROZEN_INPUT_SHA256.items():
  if f.digest(root/name)!=digest or receipt['final_inputs'].get(name)!=f.identity(root/name):raise ValueError('Final input changed during independent verification '+name)
 return dict(verified=True,physical_clusters=len(expected),oriented_faces=sum(r['oriented_faces'] for r in expected),actual_raw_choices=sum(len(r['meshlet_counts']) for r in expected),visibility_admitted=False)

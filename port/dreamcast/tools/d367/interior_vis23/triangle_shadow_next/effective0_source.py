"""Owned producer-side effective-only0 source facts, never visibility data."""
from pathlib import Path
import hashlib,json
import feasibility as f
CAPABILITY_GUARD="""#if !defined(RE4DC_PS2_PVS_EFFECTIVE0_SOURCES) || RE4DC_PS2_PVS_EFFECTIVE0_SOURCES != 1 || \\
    !defined(RE4DC_PS2_WORLD_NONEMPTY_LOD) || RE4DC_PS2_WORLD_NONEMPTY_LOD != 1
#error Effective-only0 source certificate requires reviewed capability and actual nonempty fallback
#endif
"""


def source_levels(counts,enabled=False,nonempty=False):
 if not counts or any(type(n) is not int or n<0 for n in counts):return ()
 if len(counts)==1:return (0,)
 if not enabled or not nonempty or counts[0]==0 or any(counts[1:]):return ()
 return (0,)


def final_inputs(root):
 root=Path(root)
 for name,digest in f.audit.FROZEN_INPUT_SHA256.items():
  if f.digest(root/name)!=digest:raise ValueError('Final copied source input changed '+name)
 return {name:f.identity(root/name) for name in f.audit.FROZEN_INPUT_SHA256}


def produce(root,repo,pack,enabled=False,nonempty=False):
 if type(enabled) is not bool or type(nonempty) is not bool:raise ValueError('Capability values must be explicit booleans')
 root=Path(root);repo=Path(repo);pins=final_inputs(root);p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw');policy=(root/'ps2-world.r4pw').read_bytes();ids=(root/'ps2-world.ids').read_bytes()[16:16+len(p.placements)];conditional=f.audit.conditional_fields(ids);materials,mpins=f.material_census(repo,Path(pack),p);rows=[]
 if enabled and not nonempty:raise ValueError('Effective0 requires actual nonempty fallback')
 for pi,pl in enumerate(p.placements):
  mesh=p.meshes[pl['mesh']];_,det=f.mapping(p,pi)
  if not det or pl['placement'] in conditional:continue
  for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
   meta=p.pmeta[part]
   if meta['pass_']!=0 or meta['cull'] not in (0,2) or policy[32+16*part+15]&1 or not materials[part]['eligible']:continue
   first,n=p.plod[part]
   for ci in range(first,first+n):
    cl=p.clusters[ci];levels=[p.levels[cl['first_level']+lv] for lv in range(cl['level_count'])];counts=[lv[1] for lv in levels]
    if cl['level_count']<=1 or source_levels(counts,enabled,nonempty)!=(0,):continue
    fm,nm,_=levels[0];facets=set()
    for li in range(fm,fm+nm):
     cs,ts=p.let_tris(li)
     for tri in ts:
      facet=f.audit.canonical(tuple(tuple(0 if mesh['step'][k]==0 else int(cs[j][k]) for k in range(3)) for j in tri))
      if facet is not None:facets.add(facet)
    rows.append(dict(placement=pi,field=pl['placement'],part=part,cluster=ci,meshlet_counts=counts,effective_source_levels=[0],raw_to_effective=[0]*len(counts),base_first_meshlet=fm,base_meshlet_count=nm,oriented_faces=len(facets)))
 if final_inputs(root)!=pins:raise ValueError('Final input changed while producing facts')
 return dict(kind='Effective0 source eligibility facts ONLY, not geometric/source receipt or visibility admission',enabled=bool(enabled),nonempty=bool(nonempty),final_inputs=pins,material_pins=mpins,clusters=rows,physical_clusters=len(rows),oriented_faces=sum(r['oriented_faces'] for r in rows),capability_guard=CAPABILITY_GUARD if rows else '',runtime_admitted_cuts=0)

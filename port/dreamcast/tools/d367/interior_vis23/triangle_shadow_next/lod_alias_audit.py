#!/usr/bin/env python3
"""Read-only all-effective-source-LOD triangle alias census; no rays/certificates."""
import argparse,collections,hashlib,json,resource,struct
from pathlib import Path
import feasibility as f


def minimum_alias_cover(masks,nlevels):
 if not 0<nlevels<=16 or any(type(m) is not int or m<=0 or m>=(1<<nlevels) for m in masks):raise ValueError('Invalid effective-level masks')
 full=(1<<nlevels)-1;best={0:()}
 for i,mask in enumerate(masks):
  for have,path in list(best.items()):
   merged=have|mask;candidate=path+(i,)
   if merged not in best or len(candidate)<len(best[merged]):best[merged]=candidate
 return best.get(full)


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--r6',required=True,type=Path);ap.add_argument('--base-evidence',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior audit')
 resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
 bpath=a.base_evidence/'bounded512-report.json'
 if f.digest(bpath)!='2350db18183592f05d8d9b3fb7bcd8b13f5357f21951e4b7633434477b2436b0' or f.digest(a.r6/'report.json')!=f.REPORT_SHA:raise ValueError('Frozen source reports changed')
 d=json.loads(bpath.read_text());source=f.audit.bind_source(a.source_tree,a.r6/'current-resolved-knobs.txt')
 for pin in d['inputs'].values():
  if f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Exact package/physical affine/ID input changed')
 root=Path(d['inputs']['ps2-world.r4pw']['path']).parent;p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw');policy=(root/'ps2-world.r4pw').read_bytes();ids=(root/'ps2-world.ids').read_bytes()[16:16+len(p.placements)];conditional=f.audit.conditional_fields(ids);materials,mpins=f.material_census(a.source_tree,Path(d['material']['pack']['path']),p)
 totals=collections.Counter();hist=collections.defaultdict(collections.Counter);clusters=[];examples=[];focus=[]
 for pi,pl in enumerate(p.placements):
  mesh=p.meshes[pl['mesh']];world,det=f.mapping(p,pi);static=pl['placement'] not in conditional and det!=0
  for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
   meta=p.pmeta[part];ordinary=meta['pass_']==0 and meta['cull'] in (0,2) and not policy[32+16*part+15]&1;eligible=ordinary and static and materials[part]['eligible'];fc,nc=p.plod[part]
   for ci in range(fc,fc+nc):
    cl=p.clusters[ci];levels=[];counts=[];occurrences=[]
    for lv in range(cl['level_count']):
     first,nm,_=p.levels[cl['first_level']+lv];counts.append(nm);facets=set();refs=collections.defaultdict(list)
     for li in range(first,first+nm):
      cs,triples=p.let_tris(li)
      for ordinal,tri in enumerate(triples):
       raw=tuple(tuple(0 if mesh['step'][k]==0 else int(cs[j][k]) for k in range(3)) for j in tri);facet=f.audit.canonical(raw)
       if facet is None:continue
       facets.add(facet);refs[facet].append(dict(level=lv,meshlet=li,ordinal=ordinal,corners=tuple(tri),raw=raw,vertex_count=p.lets[li]['vc']))
     levels.append(facets);occurrences.append(refs)
    keep,selected=f.audit.invariant(levels,counts);totals['all_invariant_faces']+=len(keep)
    if ordinary:totals['ordinary_shape_invariant_faces']+=len(keep)
    if eligible:totals['eligible_invariant_faces']+=len(keep)
    alias_hist=collections.Counter();possible_hist=collections.Counter();samecache_hist=collections.Counter();saved_example=None
    for facet in sorted(keep):
     byalias={}
     for li,lv in enumerate(selected):
      for ref in occurrences[lv][facet]:
       key=(ref['meshlet'],ref['corners']);alias=byalias.setdefault(key,dict(meshlet=ref['meshlet'],corners=ref['corners'],effective_level_mask=0,levels=[],occurrence_ordinals=[],vertex_count=ref['vertex_count']))
       alias['effective_level_mask']|=1<<li
       if lv not in alias['levels']:alias['levels'].append(lv)
       alias['occurrence_ordinals'].append([lv,ref['ordinal']])
     alternatives=list(byalias.values());cover=minimum_alias_cover([x['effective_level_mask'] for x in alternatives],len(selected))
     if cover is None:raise ValueError('Invariant set has uncovered effective level')
     needed=len(cover);alias_hist[needed]+=1;possible_hist[len(alternatives)]+=1
     cache_signature={tuple(ref['corners']) for lv in selected for ref in occurrences[lv][facet]};samecache_hist[len(cache_signature)]+=1
     if eligible:
      typ='one_declared_level' if cl['level_count']==1 else 'multiple_declared_levels'
      hist[typ+'_minimum_aliases'][needed]+=1;hist[typ+'_effective_level_count'][len(selected)]+=1;hist[typ+'_all_available_aliases'][len(alternatives)]+=1
      totals[typ+'_faces']+=1;totals[typ+'_minimum_alias_descriptors']+=needed;totals[typ+'_all_available_alias_descriptors']+=len(alternatives)
      if any(alternatives[k]['vertex_count']>256 for k in cover):totals['eligible_faces_min_cover_exceeds_matcher_count']+=1
      if needed>1 and saved_example is None:
       saved_example=dict(placement=pi,field=pl['placement'],mesh=pl['mesh'],part=part,cluster=ci,declared_levels=cl['level_count'],effective_levels=selected,minimum_alias_count=needed,available_alias_count=len(alternatives),facet_grid_sha256=hashlib.sha256(json.dumps(facet,separators=(',',':')).encode()).hexdigest(),exact_world_triangle=[[str(v) for v in world(q)] for q in facet],minimum_aliases=[alternatives[k] for k in cover],material=materials[part],raw_id=int(ids[pl['placement']]),conditional=False,affine_sha256=hashlib.sha256(struct.pack('<12f',*[x for row in pl['affine'] for x in row])).hexdigest(),actual_emission_or_raster_receipt='UNPROVEN')
    row=dict(placement=pi,field=pl['placement'],part=part,cluster=ci,declared_level_count=cl['level_count'],meshlet_counts=counts,effective_levels=selected,invariant_faces=len(keep),ordinary=ordinary,static=static,material_eligible=materials[part]['eligible'],eligible=eligible,minimum_alias_histogram=dict(alias_hist),available_alias_histogram=dict(possible_hist),distinct_corner_signature_histogram=dict(samecache_hist))
    clusters.append(row)
    if saved_example is not None and (len(examples)<12 or pi in (44,45)):examples.append(saved_example)
    if pi in (44,45):focus.append(row)
 if totals['ordinary_shape_invariant_faces']!=33409 or totals['eligible_invariant_faces']!=24874:raise ValueError('Existing invariance/material census changed')
 header=a.source_tree/'port/dreamcast/game/platform/include/pvs23_proof.hpp';runtime=header.with_name('pvs23_runtime.inc');hs=header.read_text()
 if f.digest(header)!='1881d1d814fdc7bb787991a2cd6f67ebab293d5c2a7efa42cdd515fb07821ba4' or f.digest(runtime)!='09a05d430e31216570bcce9e7ef6a8c5fde929bd32f4c2b6979a25df967609a0' or 'kMaxPanels=16' not in hs:raise ValueError('Frozen actual receipt cap/source changed')
 out=dict(kind='Read-only physical all-effective-source-LOD exact triangle alias census, no admission',tool=f.identity(Path(__file__)),source=source,inputs=d['inputs'],preserved_surface_report=f.identity(a.r6/'report.json'),material_pins=mpins,receipt_sources={x.name:f.identity(x) for x in (header,runtime)},current_kMaxPanels=16,current_committed_word_bits=32,totals=dict(totals),histograms={k:dict(v) for k,v in hist.items()},physical_clusters=clusters,practical_examples=examples,placements44_45=focus,alias_budget_note='Minimum set cover counts actual same(placement,part,meshlet,parity triple) descriptors covering every effective level. Duplicate-triangle Panel is only a mechanical single-triangle witness. Current flat AND completion does NOT implement OR aliases.',runtime_admitted_cuts=0,modelled_ms=None,limits=dict(address_space_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['Canonical cyclic oriented GRID equality within SAME mesh/part/cluster is exact physical triangle equality after the same pinned affine, not coordinate welding or cross-cluster retessellation.','Corner/color/UV/cache and projected kernel identities may differ by alias. Geometry equality does not establish runtime numeric/raster/seam or opacity/clip/source receipt admission.','Present in authored effective LOD does not mean selected near/far/frustum/SG path submitted the triangle. Missing or partial receipts fail open.','No source guard/ABI/certificate/data/table/runtime change, new rays/proofs/SDK/guest or sourcepool expansion.'])
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(dict(totals=out['totals'],histograms=out['histograms'],practical_examples=len(examples),current_kMaxPanels=16,limits=out['limits'])))
if __name__=='__main__':main()

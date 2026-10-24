#!/usr/bin/env python3
"""Saved-host-work counterfactual and pinned batching source inventory only.

Does not replay selection, trace queues, choose candidates or infer saved ms.
"""
import argparse,json,re,resource
from pathlib import Path
import feasibility as f

R6='7a1bb45dc427edc011e0322eb1bc3495157b2b3d794ac23d72fe3d3732d17a60'

def summarize(instances,prefix,example):
 parts={}
 for x in instances:
  key=(x['placement'],x['part']);row=parts.setdefault(key,dict(placement=key[0],part=key[1],selected_replay_corners=0,selected_meshlets=0,selected_clusters=0))
  row['selected_replay_corners']+=x['corners'];row['selected_meshlets']+=x['meshlets'];row['selected_clusters']+=int(x['level']>=0)
 def stats(rows):return dict(physical_part_draws=len(rows),selected_replay_corners=sum(x['selected_replay_corners'] for x in rows),selected_meshlets=sum(x['selected_meshlets'] for x in rows))
 selected=[x for x in parts.values() if x['selected_meshlets']>0 or x['selected_replay_corners']>0];eligible=[x for x in selected if x['placement']>prefix]
 return dict(all_selected_parts=stats(selected),hypothetical_global_set_prefix_eligible=stats(eligible),failed_pilot_example_only=stats([x for x in eligible if (x['placement'],x['part'])==example]),physical_parts=sorted(parts.values(),key=lambda x:(x['placement'],x['part'])))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--r6',required=True,type=Path);ap.add_argument('--root-plan',required=True,type=Path);ap.add_argument('--meter-note',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior census')
 resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
 if f.digest(a.r6/'report.json')!=R6:raise ValueError('Frozen R6 changed')
 if f.digest(a.meter_note)!='205fac9cc1096b6bde00369cbdd5df056894bc55a350c049d20c931b0ccc447e':raise ValueError('Meter note changed')
 d=json.loads((a.r6/'report.json').read_text());source=f.audit.bind_source(a.source_tree,a.r6/'current-resolved-knobs.txt');profile=(a.r6/'current-resolved-knobs.txt').read_text();keys=('SCENERY_SELECT_ONLY','SCENERY_REPLAY_LEAN','SCENERY_SUBMIT_BATCH','SCENERY_UV_SNAPSHOT','SCENERY_EMIT_PREFETCH','SCENERY_SELECT_LEAN2','PS2_PVS','PS2_WORLD_TRANSITION_OWNER','PS2_WORLD_DYNAMIC','WORLD_SCRATCH','SCENERY_PIECE_STATE')
 knobs={k:sorted(set(re.findall(r'^'+k+r'=(.*)$',profile,re.M))) for k in keys};views=[]
 for label in ('hut','turn','walk'):
  p=a.r6/(label+'-selected-instances.json');sha=next(x['input']['sha256'] for x in d['historical_camera_weights'] if Path(x['input']['path']).name==p.name)
  if f.digest(p)!=sha:raise ValueError('Saved replay changed')
  rows=json.loads(p.read_text());row=next(x for x in rows if x['frame']==647)
  if len(row['instances'])!=318:raise ValueError('Namespace mismatch')
  views.append(dict(label=label,frame=647,input=f.identity(p),**summarize(row['instances'],165,(209,268))))
 anchors={}
 for rel,needles in {
 'port/dreamcast/game/platform/native_static.cpp':['struct ChunkPart {','kChunkParts=48,kChunkPicks=320','struct CullScope {','struct UvScope {','const float* affine=pl.affine;','const unsigned pvs_source_placement=','e.chunk_restart();','e.pvs_finish(result>0);','x.count=d.chunk_select(cpk+npk);','re4dc_source_world_uv(pl.placement,pl.mesh,index,pass,part.uv_offset)','if(nctx==kChunkParts || npk+selected_part.meshlet_count>kChunkPicks)','if(chunk_flush()<0)return -1;'],
 'port/dreamcast/game/platform/include/scenery_chunk_select.inc':['&& !pvs_set','unsigned chunk_select(Pick* out)'],
 'port/dreamcast/game/platform/include/pvs23_runtime.inc':['bool pvs::can_cut(unsigned placement)','if(!sync(epoch) || !receipts.complete(cert->npanels))','checked_fpscr!=control','std::memcmp(key,current,sizeof(key))']}.items():
  p=a.source_tree/rel;lines=p.read_text().splitlines();found={}
  for needle in needles:
   found[needle]=[dict(line=i+1,text=x.strip()) for i,x in enumerate(lines) if needle in x]
   if not found[needle]:raise ValueError('Source anchor changed '+needle)
  anchors[rel]=dict(identity=f.identity(p),anchors=found)
 out=dict(kind='Read-only batching critique census from saved R6 host weights; no new replay/proof/trace',tool=f.identity(Path(__file__)),source=source,root_plan=f.identity(a.root_plan),meter_note=f.identity(a.meter_note),pinned_profile_knobs=knobs,source_sites=anchors,views=views,hypothetical_prefix_example=165,failed_pilot_physicalpart_example=[209,268],actual_finer_candidate_cohort=None,actual_queue_and_cost_census=dict(extra_drains=None,queue_peaks=None,binds=None,batch_open_close=None,borrow_prime=None,source_or_uv_generation_changes=None,current_target_elapsed_ms=None),runtime_admitted_cuts=0,modelled_ms=None,limits=dict(address_space_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['Prefix-eligible host part count is a counterfactual upper exposure, not actual nonnull-set or successful-receipt census.','Physical parts with no saved selected work can still cause metadata-triggered drains; saved weights cannot count those drains.','The failed31-corner pilot is an illustration of fallback scope, not an admitted or selected future cohort.','Pinned R6 PS2_PVS0 and UV_SNAPSHOT0/TRANSITION_OWNER0 do not certify future typedfine or GC-UV composition.','No runtime/schema, Pick/replay/vertex layout, data, proof search, SDK, guest or recipe change.'])
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(dict(views=[{k:v for k,v in r.items() if k!='physical_parts'} for r in views],knobs=knobs,limits=out['limits'])))
if __name__=='__main__':main()

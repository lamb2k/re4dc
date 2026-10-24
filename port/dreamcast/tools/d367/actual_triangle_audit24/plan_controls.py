"""Pinned private METADATA-only negative controls; no shadow predicate calls."""
import argparse,copy,json,resource
from pathlib import Path
import runner as r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--seal',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise ValueError('Fresh control output required')
 resource.setrlimit(resource.RLIMIT_AS,(r.RAM,r.RAM));d=r.bind(a.prepared,a.seal);cases=r.cases_from_report(d)
 if len(cases)!=75:raise ValueError('Fixed75 positive control')
 def first_bound(x):return next(t for t in x['targets'] if any('panel_id' in s for s in t['source_faces']))
 def source(x):return next(s for s in first_bound(x)['source_faces'] if 'panel_id'in s)
 def prune(x):x['targets'][0]['complete_target_faces'].pop()
 def reorder(x):x['targets'][0]['complete_target_faces'].reverse()
 def duplicate_buddy(x):s=source(x);s['panel_face_ordinals'][1]=s['panel_face_ordinals'][0]
 def wrong_face(x):s=source(x);s['panel_face']=1-s['panel_face']
 def wrong_corners(x):s=source(x);s['panel_record'][-1]+=1
 def alias_id(x):x['panel_atlas'][1]['identifier']=x['panel_atlas'][0]['identifier']
 def alias_record(x):x['panel_atlas'][1]['record']=x['panel_atlas'][0]['record']
 def drop_buddy(x):
  t=first_bound(x);s=source(x);ordinal=s['panel_face_ordinals'][1];key=s['key'][:6]+[ordinal];t['source_faces']=[q for q in t['source_faces'] if q['key']!=key]
 def reorder_domain(x):
  ix=[i for i,row in enumerate(x['domains']) if row['label']=='hut' and row['frame']==647];x['domains'][ix[0]],x['domains'][ix[1]]=x['domains'][ix[1]],x['domains'][ix[0]]
 probes={}
 for fn in (prune,reorder,duplicate_buddy,wrong_face,wrong_corners,alias_id,alias_record,drop_buddy,reorder_domain):
  bad=copy.deepcopy(d);fn(bad)
  try:r.cases_from_report(bad)
  except (ValueError,KeyError) as e:probes[fn.__name__]=dict(refused=True,reason=str(e))
  else:raise ValueError('Metadata mutant accepted '+fn.__name__)
 result=dict(classification='METADATA_BINDING_CONTROLS_ONLY_NO_SHADOW_PREDICATES',positive_cases=len(cases),refusals=probes,actual_shadow_predicate_calls=0,new_rays=0,ledger_accesses=0,tool=r.pin(Path(__file__)),prepared=r.pin(a.prepared))
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()

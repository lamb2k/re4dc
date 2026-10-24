"""Independent readback of root's completed hut647 run; no oracle import."""
import argparse,collections,hashlib,json,subprocess,resource
from pathlib import Path
SOURCE='78cbd962ee0d98dc700d0fb452500a16ac35b14c'
REPORT='7e301a48c99a46afc2397d9e823aab08c1b5b0c0e9add46af7ed80d3835afef8'
GRANT='7d19a1a098aeb7d7cf0beab055af7271f67395c3de57e213d65f30696451f28e'
REVIEW='6318f97f6832bac3fa7f1e024468e5faf843db1dc48c8f6d2f82f906eeb53766'
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--lane',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise ValueError('Fresh readback output required')
 report=a.evidence/'actual-triangle-hut647-root-r1/report.json';grant=a.lane/'ROOT-HUT647-RUN-GRANT-v1.json';review=a.lane/'root-runner-review-v3/REVIEW.json'
 for p,s in ((report,REPORT),(grant,GRANT),(review,REVIEW)):
  if pin(p)['sha256']!=s:raise ValueError('Frozen root input changed '+str(p))
 d=json.loads(report.read_text());g=json.loads(grant.read_text());v=json.loads(review.read_text());plan=json.loads((a.evidence/'actual-triangle-runner24-plan-r3/report.json').read_text())
 if not g['authorized'] or g['source']!=SOURCE or g['review_sha256']!=REVIEW or v['status']!='ROOT_INDEPENDENT_RUNNER_SOURCE_HOST_CLEAR' or v['host_groups']!=24:raise ValueError('Root grant/review chain')
 blob=subprocess.check_output(['git','-C',str(a.repo),'show',SOURCE+':port/dreamcast/tools/d367/actual_triangle_audit24/runner.py'])
 if hashlib.sha256(blob).hexdigest()!=g['runner_sha256'] or d['tool']['sha256']!=g['runner_sha256']:raise ValueError('Actual source/tool binding')
 for key in ('plan','held_camera_cases','limits','prepared','seal','generic_source','generic_sha256','preparation_source'):
  if d[key]!=plan[key]:raise ValueError('Actual execution/plan drift '+key)
 rows=d['results'];refusals=collections.Counter()
 if len(rows)!=75 or len({tuple(x['case']) for x in rows})!=75:raise ValueError('Complete unique75 cases required')
 for row,expected in zip(rows,plan['plan']):
  if row['case']!=expected['case'] or row['status']!='UNKNOWN_NO_FIXED_SOURCE' or not row['started'] or 'assignments'in row or row['final_triangle_calls_upper']!=0:raise ValueError('Unexpected wholecase status/order')
  refusals.update(row['refusals'])
 if dict(refusals)!={'EYE_SIDE':262,'EDGE_VOLUME':2691,'TARGET_DEPTH':288,'UNKNOWN_UNREPRESENTABLE_PANEL':9}:raise ValueError('Independent refusal aggregation')
 if sum(x['candidate_calls'] for x in rows)!=3255 or d['work']['candidate_calls']!=3255 or d['work']['final_batch_invocations']!=0 or d['work']['final_triangle_calls_upper']!=0 or d['actual_private_predicate_calls']!=3255:raise ValueError('Work readback')
 if d['held_camera_cases']['total']!=9600 or d['held_camera_cases']['status']!='UNTESTED_UNKNOWN' or d['new_rays'] or d['ledger_accesses'] or d['runtime_admitted'] or d['seconds']>120 or d['peak_rss_kib']>256*1024:raise ValueError('Scope/resources')
 controls=a.evidence/'actual-triangle-runner24-plan-r3/metadata-controls.json';c=json.loads(controls.read_text())
 if c['positive_cases']!=75 or len(c['refusals'])!=9 or not all(x['refused'] for x in c['refusals'].values()) or c['actual_shadow_predicate_calls']!=0:raise ValueError('Metadata control receipt')
 rootlog=a.lane/'root-runner-review-v3/HOST.log';text=rootlog.read_text()
 if 'Ran 24 tests'not in text or '\nOK'not in text:raise ValueError('Root independent host control receipt')
 out=dict(classification='INDEPENDENT_FINAL_READBACK_MATCH_NO_NEW_PREDICATES',source=SOURCE,inputs=[pin(p) for p in (report,grant,review,controls,rootlog)],cases=75,wholelet_candidates=0,statuses={'UNKNOWN_NO_FIXED_SOURCE':75},candidate_calls=3255,final_batch_invocations=0,refusals=dict(refusals),other_cases_untested=9600,seconds=d['seconds'],peak_rss_kib=d['peak_rss_kib'],new_readback_predicates=0,new_rays=0,ledger_accesses=0,runtime_admitted=False,limitations=['Only authentic hut647 at unchanged2000/500/250 fullY, not all129 cameras.','Failure of sufficient fixed-source coverage is UNKNOWN, not visibility or no possible occlusion.','Partial triangle successes cannot authorize any wholelet hide; final assignment calls0.','Ledger was not accessed by this readback; root run counters are0.','No gain, SDK, render, numeric/raster or console acceptance.'])
 a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()

"""Parent-authorized native NON-emulator controls only; fresh outputs, no retries."""
import datetime,hashlib,json,pathlib,sys
from contain import run
P=pathlib.Path(__file__).parent
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');results=[]
for case in ('normal','deadline','assignfail','descendant','late','cap'):
 output=P/'controls'/(stamp+'-'+case)
 r=run([sys.executable,'-B',str(P/'control_child.py'),case,str(output)],output,guard_seconds=.7,closure_seconds=1.7,cap=200000 if case=='cap' else 4*1024**2,control=case)
 expected=(r['qualified'] is (case=='normal') and r['job_empty'] and r['original_retained_finalized'] and r['handles_closed'] and r['execution_closure_seconds']<=1.7)
 if case in ('late','assignfail'):expected=expected and not r['resumed'] and not (output/'child-entered.txt').exists()
 if case in ('normal','descendant'):
  current=json.loads((output/'current-job-pids.json').read_text());expected=expected and r['retained_pid']==current['self'] and current['self'] in current['pids']
  if case=='descendant':
   child=int((output/'descendant.pid').read_text());held={row['pid']:row for row in r['retained_members']}
   expected=expected and child in current['pids'] and child in held and held[child]['phase']=='exited' and held[child]['wait_status']==0
 if case=='cap':expected=expected and any('cap' in x for x in r['errors'])
 results.append({'case':case,'expected_controls_pass':expected,'output':str(output),'result':r})
 print(case,expected,r['execution_closure_seconds'],r['errors'])
report={'scope':'actual native non-emulator children only; no Flycast, framebuffers, controller input or image','source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.glob('*.py')},'controls':results,'passed':all(x['expected_controls_pass'] for x in results)}
(P/('native-controls-'+stamp+'.json')).write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise SystemExit(1)

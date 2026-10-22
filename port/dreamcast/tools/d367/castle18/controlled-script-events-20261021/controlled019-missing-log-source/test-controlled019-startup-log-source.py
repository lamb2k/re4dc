from pathlib import Path
import ast,json,hashlib,types
L=Path(__file__).parent;P=L/'observe-controlled-ch32-door019.py';tree=ast.parse(P.read_text());env=dict(re=__import__('re'),dict=dict)
for name in ['startup_log_mapping','wait_startup_mapping']:
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),'actual019startup','exec'),env)
class FakeLog:
 def __init__(self,missing,content):self.missing=missing;self.content=content;self.reads=0
 def read_text(self,**kwargs):
  self.reads+=1
  if self.missing is None or self.reads<=self.missing:raise FileNotFoundError('simulated not-created exactcurrentlog')
  return self.content
class Cap:
 def __init__(self,log):self.log=log
 def __truediv__(self,name):return self.log if name=='flycast.log'else Path(r'C:\cap019')/name
results=[]
for case,missing in [('missing-log-then-created-current-load',2),('permanent-absence-bounded-timeout',None)]:
 now=[.01];calls=dict(identity=0,regions=0,readmemory=0,writememory=0,inputs=0);events=[];base=Path(r'C:\cap019');content='00:00:613 RAM(16 MB) 00007FF400000000 VRAM64\n00:00:730 Loaded state ver 854 from '+str(base/'data/disc.state')+' size 28204558\n';log=FakeLog(missing,content)
 def identity():calls['identity']+=1
 def region(host,n):calls['regions']+=1;return dict(committed=True,accessible=True,covers=True)
 def sleep(seconds):now[0]+=seconds
 env.update(age=lambda:now[0],time=types.SimpleNamespace(sleep=sleep),check=identity,cap=Cap(log),region_query=region,region_failure_count=0,owner=dict(pid=51601,start_filetime=123),events=events,read_diagnostics=[])
 result=env['wait_startup_mapping']();assert len([e for e in events if e.get('startup_log_not_created_pending')])==1;assert calls['readmemory']==calls['writememory']==calls['inputs']==0
 if missing is not None:assert result['RAM']==0x7ff400000000 and result['mapping_precedes_load']and log.reads==3 and calls['regions']==1 and now[0]<38
 else:assert result is None and now[0]>=38 and now[0]<38.04 and calls['regions']==0
 results.append(dict(case=case,passed=True,returned_mapping=result,final_process_age=now[0],log_reads=log.reads,calls=calls,events=events))
# Only the exact missing-file exception is admitted as pending; other errors retain the existing failclosed path.
n=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='wait_startup_mapping');handlers=[h for n in ast.walk(n)if isinstance(n,ast.Try)for h in n.handlers];assert len(handlers)==1 and isinstance(handlers[0].type,ast.Name)and handlers[0].type.id=='FileNotFoundError'
r=dict(scope='Two focused source cases execute actual019startup wait path using mocklog/clock/identity/region only. No OSchild/DLL/Flycast/input/memoryprobe; no unrelated44/17/31rerun.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),passed=2,cases=results,only_missing_file_pending=True);(L/'controlled019-startup-log-source-cases.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS2',r['observer_sha256'])
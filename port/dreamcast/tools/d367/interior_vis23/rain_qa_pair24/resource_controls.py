"""Host mocks and one live RAM observation; no SDK or memory admission claim."""
from pathlib import Path
import json,resource,signal,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as c
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120)
def main():
 out=Path(sys.argv[1]).resolve();checks=[];budget=c.load()['budget'];G=1024**3;M=1024**2
 def info(n):return 'MemTotal: 999999999 kB\nMemAvailable: '+str(n//1024)+' kB\n'
 def good(name,t,m,want):
  value=c.ram_observation(t,info(m));assert value==dict(RAM_free=want,tmpfs_available_bytes=t,MemAvailable_bytes=m);checks.append(dict(name=name,pass_=True,observed=value));return value
 def refuse(name,fn):
  try:fn()
  except RuntimeError as e:checks.append(dict(name=name,refused=True,reason=str(e)))
  else:raise AssertionError(name+' escaped')
 def values(r):return dict(r,C_free=64*G,owned_bytes=0,release_active=False)
 good('MemAvailable-is-lower',9*G,4*G,4*G);good('tmpfs-is-lower',4*G,9*G,4*G);good('equal-observations',4*G,4*G,4*G)
 for name,t,m,admit in [('mem-below-admission',9*G,3*G-1024,True),('tmpfs-below-admission',3*G-1024,9*G,True),('mem-below-floor',9*G,512*M-1024,False),('tmpfs-below-floor',512*M-1024,9*G,False)]:
  r=c.ram_observation(t,info(m));refuse(name,lambda r=r,a=admit:c.boundaries(values(r),budget,admission=a))
 for name,n,a in [('exact-admission',3*G,True),('exact-floor',512*M,False)]:c.boundaries(values(c.ram_observation(n,info(n))),budget,admission=a);checks.append(dict(name=name,pass_=True))
 for name,text in [('missing','MemFree: 999999999 kB\n'),('duplicate',info(4*G)+info(4*G)),('negative','MemAvailable: -1 kB\n'),('wrong-unit','MemAvailable: 4 MB\n'),('malformed','MemAvailable: NaN kB\n')]:refuse(name,lambda text=text:c.ram_observation(4*G,text))
 refuse('negative-tmpfs',lambda:c.ram_observation(-1,info(4*G)));refuse('noninteger-tmpfs',lambda:c.ram_observation('4',info(4*G)))
 observed=c.resources(c.ROOT);assert observed['RAM_free']==min(observed['tmpfs_available_bytes'],observed['MemAvailable_bytes']);checks.append(dict(name='live-lower-figure-preserved',pass_=True,observed=observed))
 result=dict(status='RAM_OBSERVER_HOST_PASS',count=len(checks),checks=checks,SDK_commands=0,Make_queries=0,SDK_bootstrap=0,stage=0,guest=0,scope='Mock floor/admission logic plus current observation only; no SDK or game heap qualification')
 c.exclusive_json(out/'RAM-CONTROLS.json',result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()

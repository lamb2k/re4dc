"""Fixed backface pixel invocation. Validation only unless root allocated execution."""
from pathlib import Path
import argparse,json,sys
from contain import P,run,sha,validate_pixel

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--profile',required=True);p.add_argument('--profile-sha256',required=True)
 p.add_argument('--allocation',required=True);p.add_argument('--allocation-sha256',required=True)
 p.add_argument('--execute',action='store_true');a=p.parse_args()
 authority=(a.profile,a.profile_sha256,a.allocation,a.allocation_sha256)
 if sha(a.profile)!=a.profile_sha256:raise ValueError('profile pin differs')
 profile=json.loads(Path(a.profile).read_text());argv=[sys.executable,'-B',str(P/'stock_child.py'),a.profile]
 validate_pixel(argv,profile['output'],authority)
 if not a.execute:
  print(json.dumps(dict(execute=False,argv=argv,output=profile['output'],controller_sha256=sha(P/'contain.py'))));return
 result=run(argv,profile['output'],authority=authority,cap=60*1024**2)
 print(json.dumps(dict(qualified=result['qualified'],output=profile['output'],errors=result['errors'])))
 if not result['qualified']:raise SystemExit(1)
if __name__=='__main__':main()

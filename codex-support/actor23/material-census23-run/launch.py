"""Only explicit separate main one-attempt allocation may launch mode1 census."""
from pathlib import Path
import argparse,json,sys
from contain import P,run,sha,validate_pixel
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('profile','profile-sha256','allocation','allocation-sha256'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--execute',action='store_true');a=parser.parse_args();authority=(a.profile,a.profile_sha256,a.allocation,a.allocation_sha256)
 if sha(a.profile)!=a.profile_sha256:raise ValueError('profile changed')
 p=json.loads(Path(a.profile).read_text());argv=[sys.executable,'-B',str(P/'stock_child.py'),a.profile];validate_pixel(argv,p['output'],authority)
 if not a.execute:print(json.dumps(dict(execute=False,output=p['output'],observation_only=True)));return
 result=run(argv,p['output'],authority=authority,cap=60*1024**2);print(json.dumps(dict(qualified=result['qualified'],output=p['output'],errors=result['errors'],observation_only=True,actor_hiding_gate=False,census_only=True)))
 if not result['qualified']:raise SystemExit(1)
if __name__=='__main__':main()

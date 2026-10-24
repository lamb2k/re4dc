#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, subprocess
if not __debug__: raise RuntimeError('assertions must be enabled')
p=argparse.ArgumentParser();p.add_argument('--repo',type=pathlib.Path,default=pathlib.Path('.'));p.add_argument('--revision',default='HEAD');p.add_argument('--source-root',type=pathlib.Path);a=p.parse_args()
r='port/dreamcast/docs/qualification/audits23-20261023/'
def blob(path):return subprocess.check_output(['git','-C',str(a.repo),'show',a.revision+':'+path])
m=json.loads(blob(r+'tools-snapshot.json'));total=0
for row in m['included']:
 b=blob(row['snapshot_path']);assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['snapshot_path'];total+=len(b)
 if a.source_root:
  original=(a.source_root/row['source_relative_path']).read_bytes();assert original==b,row['source_relative_path']
assert blob(r+'.gitattributes')==b'* -text whitespace=cr-at-eol,-blank-at-eof\n'
print(json.dumps({'revision':a.revision,'included_files':len(m['included']),'included_bytes':total,'excluded_files':len(m['excluded']),'committed_blobs_verified':True,'originals_rechecked':bool(a.source_root)}))

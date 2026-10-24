#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
here=pathlib.Path(__file__).resolve().parent
repo=pathlib.Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=here,text=True).strip())
manifest=json.loads((here/'manifest.json').read_text())
for row in manifest['included']:
 path=(here/row['path']).relative_to(repo).as_posix()
 blob=subprocess.check_output(['git','show','HEAD:'+path],cwd=repo)
 assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],path
print('COMMITTED_ORIGINAL_BYTES_IDENTICAL',len(manifest['included']))

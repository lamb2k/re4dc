from pathlib import Path
import hashlib,json,os,subprocess,sys
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes')
P=L/'actor-visibility23/build-eligibility-witness23-r2'
R=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration')
T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
copy=R/'SDK-SOURCE-READBACK.json';actual=json.loads(copy.read_bytes());manifest=P/'SDK-COPY-MANIFEST.json'
assert actual['only_owned_marker_retired'] and actual['failed_attempt_preserved'] and len(actual['files'])==54
for row in json.loads(manifest.read_bytes())['files']:
 q=T/'port/dreamcast/game/third_party/sh4zam'/row['relative']
 assert q.stat().st_size==row['bytes'] and sha(q)==row['sha256']
receipt=R/'SDK-COPY-READBACK.json'
with receipt.open('x') as f:json.dump(dict(status='RETAINED_SDK54_COPY_VERIFIED_SOURCE_ONLY',source='f2405bb06ebaff6e2a7681479d5308ec5d3b988a',actual_copy=dict(path=str(copy),sha256=sha(copy)),independent_manifest=dict(path=str(manifest),sha256=sha(manifest)),actual_files_checked=54,build=False),f,indent=2)
res=subprocess.run([sys.executable,'-B',str(L/'pvs23/root-native-resources-material23.py')],check=True,capture_output=True,text=True)
print(res.stdout,flush=True);resource=Path(json.loads(res.stdout)['path'])
subprocess.run([sys.executable,'-B',str(P/'run.py'),'on','--resources',str(resource),'--resources-sha256',sha(resource),'--release-priority-clear','--execute'],env=dict(os.environ,ACTOR23_ARM_OUTPUT='on2'),check=True)
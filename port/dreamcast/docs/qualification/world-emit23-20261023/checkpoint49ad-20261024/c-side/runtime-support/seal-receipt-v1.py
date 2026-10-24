import hashlib,json,pathlib,datetime
root=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776');support=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
out={'source':'7a3af776ff8c14070f96272cd48074e5895d0490','sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'bounded guest census and MODELLED PT matrix only; no SDK/source edits, no still/gates/physical-console speed claim','files':{},'accepted_caps':{},'excluded_caps':['R-m-b1-q1','L-m-b1-q1']}
for p in support.iterdir():
 if p.is_file():out['files'][str(p)]={'bytes':p.stat().st_size,'sha256':sha(p)}
for name in ['census-summary.json','meter-summary.json']:
 p=root/'runtime-support'/name;out['files'][str(p)]={'bytes':p.stat().st_size,'sha256':sha(p)}
for arm in 'RLEB':
 for typ in (['m','n'] if arm=='R' else ['m']):
  for suffix in ['resolved-knobs.txt','stack.txt','programmes.sha256','syms.txt','master.log']:
   p=root/'identities'/f'{arm}-{typ}-{suffix}';out['files'][str(p)]={'bytes':p.stat().st_size,'sha256':sha(p)}
for name in ['R-n-b1-q1','R-n-s2-q1','R-m-b1-q2','L-m-b1-q2','E-m-b1-q1','B-m-b1-q1','R-m-s2-q1','L-m-s2-q1','E-m-s2-q1','B-m-s2-q1']:
 cap=root/'runtime-support'/name; result=json.loads((cap/'run-result.json').read_text());launch=json.loads((cap/'bounded-launch.json').read_text())
 assert result['status']=='RUN_COMPLETE' and not result['errors'] and result['reader_exit']==0 and not launch['deadline_fired'] and launch['guest_exited']
 assert result['tracks']['track03_sha256']==(root/'_discs'/name[:3]/'track03.sha256').read_text().strip()
 out['accepted_caps'][name]={n:sha(cap/n) for n in ['run-output.txt','run-result.json','bounded-launch.json','fixture-warp.txt','syms.txt','disc.gdi','emu.cfg','read-log.err']}
 p=root/'runtime-support/launch-receipts'/f'{name}.txt';out['accepted_caps'][name]['launch_receipt_sha256']=sha(p)
assert json.loads((root/'runtime-support/meter-summary.json').read_text())['owned_meter_guests_disjoint']
p=support/'RECEIPT.json';p.write_text(json.dumps(out,indent=2)+'\n');(root/'runtime-support/RECEIPT.json').write_bytes(p.read_bytes());print('sealed',p,sha(p))
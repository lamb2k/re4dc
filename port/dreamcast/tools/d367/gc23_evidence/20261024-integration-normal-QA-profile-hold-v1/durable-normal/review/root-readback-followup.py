from pathlib import Path
import hashlib,json,subprocess,tarfile,importlib.util,datetime
base=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-link-review')
prior=base/'INDEPENDENT-READBACK.json';prior_sha=hashlib.sha256(prior.read_bytes()).hexdigest()
new=base/'root-followup-v1';assert not new.exists();new.mkdir()
spec=importlib.util.spec_from_file_location('independent_full_link_verifier',base/'verify_completed_pair.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=new;m.main()
assert hashlib.sha256(prior.read_bytes()).hexdigest()==prior_sha
p=json.loads((base.parent/'full-link-prep/PREPARATION.json').read_text());expected=p['source_manifest'];seen={}
def archive(repo,commit,prefix=''):
 proc=subprocess.Popen(['git','-c','pack.threads=1','-C',repo,'archive','--format=tar',commit],stdout=subprocess.PIPE)
 with tarfile.open(fileobj=proc.stdout,mode='r|') as t:
  for item in t:
   if not item.isfile():continue
   name=prefix+item.name;assert name in expected,name
   f=t.extractfile(item);h=hashlib.sha256();size=0
   for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
   assert size==expected[name]['bytes'] and h.hexdigest()==expected[name]['sha256'],name
   assert name not in seen,name;seen[name]={'bytes':size,'sha256':h.hexdigest()}
 assert proc.wait()==0
archive('/root/work/lanes/gc-motion24','aab201ceac0e18107f64a3212398afe916793327')
archive('/root/work/lanes/gc-port23/port/dreamcast/game/third_party/sh4zam','33fa4850cacb30dd0ad35485ef035526ec4ce782','port/dreamcast/game/third_party/sh4zam/')
assert set(seen)==set(expected),(set(expected)-set(seen))
r={'status':'ROOT_REEXECUTED_INDEPENDENT_FULL_READBACK_AND_GIT_EXPORT_BINDING_PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':p['source'],'submodule':p['submodule_commit'],'original_independent_receipt_sha256':prior_sha,'original_independent_receipt_preserved':True,'source_export_members_bound_to_exact_git_archives':len(seen),'source_export_bytes':sum(x['bytes'] for x in seen.values()),'new_readback_sha256':hashlib.sha256((new/'INDEPENDENT-READBACK.json').read_bytes()).hexdigest(),'execution':'Read-only Python and Git only, noSDK/Make/guest','scope':'Source/programme/all14/ELF/link graph/import/end checks only; not heap/terminal/coverage/provenance/look/performance or physical acceptance'}
out=new/'ROOT-GIT-EXPORT-BINDING.json';out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));print('root_receipt_sha256',hashlib.sha256(out.read_bytes()).hexdigest())

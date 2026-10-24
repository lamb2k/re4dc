import datetime,hashlib,json,pathlib,subprocess
here=pathlib.Path(__file__).parent;proof=json.loads((here/'BACKING-PROOF.json').read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
legacy=pathlib.Path(proof['legacy_receipt']);old=json.loads(legacy.read_text())
assert sha(legacy)=='d7026d14e8a096469eac12aed583767ce135b8ef3b0ab8a10c78c00428354835'
for path,rec in old['files'].items():assert sha(path)==rec['sha256'],path
assert sha(here.parent/'RECEIPT.json')=='9fd3ff6d801655ba46edaf75becd31b880a302b3ad84b54011e6df7e14540dee'
r=subprocess.run(['python3',str(here/'test-sparse-refusal.py')],env={'PYTHONDONTWRITEBYTECODE':'1','PATH':'/usr/bin:/bin'},capture_output=True,text=True);(here/'HOST-CONTROLS.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
out={'source':proof['source'],'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'claim':'source/host correction only; current native backing unsupported and refused before process access; no sparse reader, SDK, guest or strict pixel qualification','legacy_seal_and_all_files_unchanged':True,'legacy_receipt_sha256':sha(legacy),'old7a_receipt_unchanged':True,'files':{str(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in here.iterdir() if p.is_file() and p.name!='RECEIPT.json'},'correction_index_sha256':sha(here.parent/'CORRECTIONS.md'),'source_contract':proof}
p=here/'RECEIPT.json';p.write_text(json.dumps(out,indent=2)+'\n');print('correction receipt',sha(p));print(r.stdout)
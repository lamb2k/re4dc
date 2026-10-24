import datetime,hashlib,json,pathlib,subprocess
here=pathlib.Path(__file__).parent;layout=json.loads((here/'observer-layout-R-g.json').read_text());tree=pathlib.Path('/root/work/lanes/world-emit23-current-R')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==layout['source']
assert not subprocess.check_output(['git','-C',str(tree),'status','--porcelain'],text=True).strip()
assert sha(pathlib.Path(layout['elf']))==layout['elf_sha256']
r=subprocess.run(['python3',str(here/'test-observer.py')],env={'PYTHONDONTWRITEBYTECODE':'1','PATH':'/usr/bin:/bin'},capture_output=True,text=True);(here/'HOST-CONTROLS.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
out={'source':layout['source'],'elf':layout['elf'],'elf_sha256':layout['elf_sha256'],'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'claim':'source/ELF/host controls only; no SDK build/guest/image/runtime edits; strict pixel qualification unsupported by existing completed bindings','source_tree_clean':True,'host_returncode':r.returncode,'files':{str(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in here.iterdir() if p.is_file() and p.name!='RECEIPT.json'},'source_pins':layout['source_pins'],'kos_pins':layout['kos_pins'],'backend_pins':layout['backends'],'profile_sha256':sha(pathlib.Path(layout['elf']).with_name('resolved-knobs.txt')),'stack_sha256':sha(pathlib.Path(layout['elf']).with_name('stack.txt')),'old7a_receipt_unchanged':sha(pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/RECEIPT.json'))}
assert out['old7a_receipt_unchanged']=='9fd3ff6d801655ba46edaf75becd31b880a302b3ad84b54011e6df7e14540dee'
p=here/'RECEIPT.json';p.write_text(json.dumps(out,indent=2)+'\n');print('receipt',sha(p));print(r.stdout)
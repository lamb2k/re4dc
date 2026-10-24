"""Root-owned one-file PRIVATE stage, only after independent source review.
No runtime/recipe/source changes; production assets remain untouched.
"""
from pathlib import Path
import importlib.util,hashlib,json,os,shutil,subprocess,sys
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
KEY='dc/tex/7/7d4e1e92-052bdc2e.re4tex'
SHA='18978dc1b97247dcd5fda5f5f1744b74e9d1b97c34dc5779977525b0a2dc477e'
BASE=Path('/root/work/lanes/stat-bytes23-takeover-scratch/release')
HERE=Path(__file__).resolve().parent
PKG=Path('/mnt/c/Game Dev/Emulators/re4-assets-private/worldemit-ui-pair23-20261023-v2')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9')
WORK=Path('/root/probe/worldemit-ui-pair23-private-stage-v1')
OUT=E/'_discs/B-t-ps2hair-v1'
GATE=HERE.parent.parent/'world-emit23/current-gates/current_gates_root_v1.py'
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def row(p):return {'size':p.stat().st_size,'sha256':sha(p)}
def fresh(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(o,f,indent=2);f.write('\n')
def main():
 if len(sys.argv)!=2 or sys.argv[1]!='--execute-private':raise SystemExit('Explicit --execute-private required; preparation never enables production.')
 g=load('current_stage_contract',GATE);unit=g.inspect('B','t');assert unit['source']==SOURCE
 assert sha(GATE)=='1861ed9e055c6d6c2a356360257775a51b22800e22a1562d36d4f5c5c93515ae', 'root helper pin changed'
 control=g.check_base(E/'_discs/B-t',unit)
 proof=HERE.parent/'PACK-ABSENCE.json';assert sha(proof)=='3c6d25c05314e584a57d01d53be6ab6209c2514803c8178c33b410a713a9a6fe'
 absent=json.loads(proof.read_text());assert absent['found'] is False and absent['source']==SOURCE and absent['query']=='7d4e1e92-052bdc2e'
 assert sha(Path(absent['pack']['path']))==absent['pack']['sha256']
 for rel,pin in absent['lookup_sources'].items():assert sha(g.tree('B')/rel)==pin['sha256']
 candidate=PKG/'files'/KEY;assert row(candidate)=={'size':32912,'sha256':SHA}
 opts=json.loads((PKG/'local-pack.json').read_text());assert opts['default']==0 and opts['production_enabled'] is False and opts['replace']=={KEY:str(candidate)}
 base=json.loads((BASE/'manifest.json').read_text());assert KEY not in base and not (BASE/'tree'/KEY).exists()
 assert shutil.disk_usage('/mnt/c').free>=24*1024**3,'C staging floor'
 assert not WORK.exists() and not OUT.exists(),'New owned destinations only; preserve prior attempts'
 WORK.mkdir(parents=True)
 tree=WORK/'tree';subprocess.run(['cp','-al',str(BASE/'tree'),str(tree)],check=True)
 dest=tree/KEY;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(candidate.read_bytes())
 derived=dict(base);derived[KEY]=row(dest);fresh(WORK/'manifest.json',derived)
 assert {k for k in set(base)|set(derived) if base.get(k)!=derived.get(k)}=={KEY}
 tools=g.tools('B');pre={'unit':unit,'control':control,'candidate':row(candidate),'new_manifest':row(WORK/'manifest.json'),'original_manifest':row(BASE/'manifest.json'),'stage_helper':row(tools/'fullplay/fp_master.sh'),'root_helper':row(Path(__file__)),'pack_absence_proof':row(proof),'private_only':True,'look_approved':False}
 fresh(WORK/'preflight.json',pre)
 log=WORK/'master.log'
 with log.open('x') as f:subprocess.run(['bash',str(tools/'fullplay/fp_master.sh'),str(tree),str(WORK/'manifest.json'),str(BASE/'IP.BIN'),str(OUT),unit['output']],env=dict(os.environ,PRUNE_AUTO='0',RE4DC_STAGE_EXT4='1'),stdout=f,stderr=subprocess.STDOUT,check=True)
 staged=json.loads((OUT/'base-manifest.json').read_text());original=json.loads((E/'_discs/B-t/base-manifest.json').read_text())
 assert {k for k in set(staged)|set(original) if staged.get(k)!=original.get(k)}=={KEY}
 assert staged[KEY]==row(candidate)
 assert staged['1ST_READ.BIN']==unit['programme']['main']
 assert {k[3:]:v for k,v in staged.items() if k.startswith('dc/') and k.endswith('.ovl')}==unit['programme']['overlays']
 iso=load('private_stage_iso',tools/'fullplay/fp_iso.py');tr=iso.Track(OUT/'track03.iso',45000)
 matches=[(p,e,s) for p,e,s in iso.files(tr) if p.lstrip('/')==KEY];assert len(matches)==1
 p,e,n=matches[0];readback=tr.read_bytes(e,n);assert len(readback)==32912 and hashlib.sha256(readback).hexdigest()==SHA;tr.f.close()
 assert sha(OUT/'track03.iso')==(OUT/'track03.sha256').read_text().strip()
 receipt=dict(pre,staged_manifest=row(OUT/'base-manifest.json'),track03=row(OUT/'track03.iso'),readback_sha256=SHA,sole_asset_change=KEY,source_or_programme_changes=False,stage_success=True,guest_or_look_acceptance=False)
 fresh(WORK/'stage-receipt.json',receipt);fresh(E/'private-ps2-hair-v1-stage.json',receipt)
 print(json.dumps({'stage':str(OUT),'stage_success':True,'guest_or_look_acceptance':False,'track03':receipt['track03']}))
if __name__=='__main__':main()
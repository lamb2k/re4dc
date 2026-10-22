#!/usr/bin/env python3
"""Run the actual r200 source-world reader before/after the mip layout fix.

Only host fixtures compile. Source/cache/GPU services are synthetic, so these
checks establish admission logic, not VRAM fit, guest draw or console acceptance.
"""
from pathlib import Path
import argparse, hashlib, json, os, resource, subprocess, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
REL='port/dreamcast/game/platform/include/native_ui_source_world.inc'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--out',type=Path,required=True)
 p.add_argument('--current-pack',type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 sys.path.insert(0,str(HERE.parent/'texsrc22'));import convert as cv
 pack=a.current_pack.read_bytes();member=cv.read_pak(pack)[cv.key_tuple('fa6fe38c-1a02365f')]
 kind,n,*_=cv.identify(member)
 assert kind=='vq' and n.mipmapped and len(n.payload)==23894
 assert cv.digest(member)=='141f816730cc37d2d3f16f5ea5cea2e1772d3ea55dd0fc31837bc9e4cfab8274'
 a.out.mkdir(parents=True)
 baseline=subprocess.check_output(['git','-C',str(ROOT),'show','3d9a37e1:'+REL])
 override=a.out/'baseline-source';override.mkdir()
 (override/'native_ui_source_world.inc').write_bytes(baseline)
 driver=ROOT/'port/dreamcast/tests/test_source_world_r200.py'
 source=driver.read_text()
 sys.path.insert(0,str(driver.parent))
 env0=os.environ.get('RE4DC_TEST_ARTIFACT_DIR')
 results=[];deleted=[]
 for name,vq,mip,before in [('before-mip',1,1,True),('legacy-only',0,0,False),
                             ('vq-base-only',1,0,False),('vq-mip',1,1,False)]:
  out=a.out/name
  os.environ['RE4DC_TEST_ARTIFACT_DIR']=str(out)
  injected=source.replace("'-std=c++17'",repr('-DRE4DC_PS2_WORLD_SOURCE_TEX_VQ='+str(vq))+','+
      repr('-DRE4DC_CAST_MIPMAP='+str(mip))+",'-std=c++17'",1)
  if before:
   injected=injected.replace("'-I',str(INC)","'-I',"+repr(str(override))+",'-I',str(INC)",1)
  assert injected!=source
  failed=False
  try:
   exec(compile(injected,str(driver),'exec'),dict(__name__='__main__',__file__=str(driver)))
  except subprocess.CalledProcessError:
   failed=True
  assert failed==before,(name,'unexpected host result')
  assert (out/'run-output.txt').exists(), 'expected execution, not compilation failure'
  run_output=(out/'run-output.txt').read_text()
  results.append(dict(name=name,vq=vq,mip=mip,baseline_override=before,
      expected_result='refuse current mip representation' if before else 'all expanded actual-reader checks pass',
      actual_result='expected baseline failure' if failed else 'PASS',
      run_output=run_output,runtime_sha256=sha(baseline if before else (ROOT/REL).read_bytes())))
  # Own, safely rebuildable host products only; preserve command/source/logs.
  for leaf in ('test','osalloc.o'):
   product=out/leaf
   assert product.parent==out
   if product.exists():
    deleted.append(dict(path=str(product),bytes=product.stat().st_size,sha256=sha(product.read_bytes())))
    product.unlink()
  assert sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file())<4*1024**2
 if env0 is None:os.environ.pop('RE4DC_TEST_ARTIFACT_DIR',None)
 else:os.environ['RE4DC_TEST_ARTIFACT_DIR']=env0
 summary=dict(schema='re4dc-mipmap23-r200-prep-host-1',
   key='fa6fe38c-1a02365f',current_pack=str(a.current_pack),current_pack_sha256=sha(pack),
   member_sha256=sha(member),member_payload_bytes=23894,
   old_runtime_sha256=sha(baseline),new_runtime_sha256=sha((ROOT/REL).read_bytes()),
   source_claim=REL,results=results,deleted_owned_host_products=deleted,
   guest_run=False,full_game_build=False,
   limits='Actual production preparation/readiness with synthetic source/cache/GPU; no measured VRAM fit, sampling or console acceptance.')
 (a.out/'host-proof.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

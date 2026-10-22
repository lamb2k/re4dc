#!/usr/bin/env python3
"""Feed sealed selected files through the actual native Package reader."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_mipmap_runtime as fixture

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repeat',type=Path);ap.add_argument('--compact',type=Path);ap.add_argument('--cohort',type=Path,action='append',default=[]);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 cls=fixture.RuntimeMipmapAdmission;cls.setUpClass();results=[]
 try:
  root=cls.owner.root;scene=fixture.host.ROOT/'room';exe=root/'reader-selected-sanitized'
  command=['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DRE4DC_CAST_MIPMAP=1','-DRE4DC_TEX_RESIDENT=1','-DRE4DC_STORAGE_BOUNCE_BYTES=16384','-I'+str(root),'-I'+str(scene),str(root/'reader-mip.cpp'),str(scene/'texture_package.cpp'),str(scene/'room_storage.cpp'),'-o',str(exe)]
  subprocess.run(command,check=True,capture_output=True)
  directories=[(name,path) for name,path in [('repeat',a.repeat),('compact',a.compact)] if path is not None]+[(path.name,path) for path in a.cohort]
  assert directories,'Provide at least one sealed cohort'
  for family,directory in directories:
   r=json.loads((directory/'receipt.json').read_text())
   for row in r['selected']:
    path=directory/'packages'/(row['key']+'.re4tex');blob=path.read_bytes();assert hashlib.sha256(blob).hexdigest()==row['candidate_sha256']
    p=subprocess.run([str(exe),str(path)],capture_output=True,text=True,check=True);lines=p.stdout.splitlines();assert lines[0].split('|')[-1]=='ok',lines
    format_word=int(lines[1].split(':')[1],16);assert format_word&0xc0000000==0xc0000000
    off=subprocess.run([str(cls.owner.exe['1']),str(path)],capture_output=True,text=True,check=True);assert off.stdout.splitlines()[0]!='ok|ok'
    results.append(dict(family=family,key=row['key'],sha256=row['candidate_sha256'],actual_reader=p.stdout.splitlines(),mip_disabled_reject=off.stdout.splitlines(),sanitizer_stderr=p.stderr))
  out=dict(actual_package_cases=len(results),all_passed=True,reader_command=command,results=results,limits=['Actual native Package host reader with ASan/UBSan and exact selected files; no target allocation, rendering or runtime packet gate.'])
  (a.out/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['actual_package_cases','all_passed']}))
 finally:cls.tearDownClass()
if __name__=='__main__':main()

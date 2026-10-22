#!/usr/bin/env python3
"""Qualify the exact scoped fixture through actual Package and table receipts."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_mipmap_runtime as fixture
import convert_tpl as tpl

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 receipt=json.loads((a.fixture/'receipt.json').read_text());table=(HERE/'scoped_representations.inc').read_text();table_ids=re.findall(r'\{0x([0-9a-f]{8})U,0x([0-9a-f]{8})U',table)
 assert {'%s-%s'%key for key in table_ids}=={v['scoped_key'] for v in receipt['selected']}
 cls=fixture.RuntimeMipmapAdmission;cls.setUpClass();results=[]
 try:
  root=cls.owner.root;scene=fixture.host.ROOT/'room';exe=root/'reader-scoped-sanitized'
  command=['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DRE4DC_CAST_MIPMAP=1','-DRE4DC_TEX_RESIDENT=1','-DRE4DC_STORAGE_BOUNCE_BYTES=16384','-I'+str(root),'-I'+str(scene),str(root/'reader-mip.cpp'),str(scene/'texture_package.cpp'),str(scene/'room_storage.cpp'),'-o',str(exe)]
  subprocess.run(command,check=True,capture_output=True)
  for row in receipt['selected']:
   path=a.fixture/'textures'/(row['scoped_key']+'.re4tex');blob=path.read_bytes();assert sha(path)==row['candidate_sha256'];h=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,h[5]);assert h[8]==row['candidate_crc32'] and t[1:4]==(64,64,0) and t[5:8]==(3414,4,2)
   p=subprocess.run([str(exe),str(path)],capture_output=True,text=True,check=True);lines=p.stdout.splitlines();assert lines[0].split('|')[-1]=='ok';assert int(lines[1].split(':')[1],16)&0xc0000000==0xc0000000
   off=subprocess.run([str(cls.owner.exe['1']),str(path)],capture_output=True,text=True,check=True);assert off.stdout.splitlines()[0].split('|')[-1]!='ok'
   results.append(dict(key=row['scoped_key'],sha256=sha(path),reader=p.stdout.splitlines(),disabled_reader=off.stdout.splitlines(),sanitizer_stderr=p.stderr))
  out=dict(schema='re4dc-rect21-scoped-host-1',actual_package_cases=len(results),all_passed=True,active_table_ids_match_fixture=True,active_table_sha256=sha(HERE/'scoped_representations.inc'),reader_command=command,results=results,limits=['Actual Package host checks and immutable selected table/descriptor proofs. No complete program, target packet, rendering or timing gate.'])
  (a.out/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['actual_package_cases','all_passed','active_table_ids_match_fixture']}))
 finally:cls.tearDownClass()
if __name__=='__main__':main()

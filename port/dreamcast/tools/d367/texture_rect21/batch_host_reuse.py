#!/usr/bin/env python3
"""Reuse sealed actual Package host binaries for a new shared cohort, no rebuild."""
from pathlib import Path
import hashlib,json,subprocess,sys,zlib,struct
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 O,P=map(Path,sys.argv[1:3]);r=json.loads((O/'conversion-receipt.json').read_text());old=json.loads((P/'host-gate.json').read_text());H=O/'host-reused';H.mkdir();paths=[O/x['relative_path']for x in r['selected']];assert len(paths)==4
 for path,digest in old['source_pins'].items():assert sha(Path(path).read_bytes())==digest
 outputs={}
 for mode in('on','off'):
  exe=P/'host'/('reader-'+mode);assert sha(exe.read_bytes())==old['outputs'][mode]['exe_sha256'];run=subprocess.run([str(exe),*map(str,paths)],capture_output=True,text=True,timeout=15);(H/('output-'+mode+'.txt')).write_text(run.stdout);(H/('stderr-'+mode+'.txt')).write_text(run.stderr);assert run.returncode==0 and not run.stderr
  lines=run.stdout.splitlines()
  if mode=='on':assert len(lines)==2*len(paths)and all(lines[2*i]=='ok|ok'and int(lines[2*i+1].split(':')[1],16)&0xc0000000==0xc0000000 for i in range(len(paths)))
  else:assert len(lines)==len(paths)and all(x!='ok|ok'for x in lines)
  outputs[mode]=dict(exe=str(exe),sha256=sha(exe.read_bytes()),cases=len(paths),result='PASS'if mode=='on'else'ALL_REJECT')
 negatives=[]
 for side in sorted({x['physical'][0]for x in r['selected']}):
  row=next(x for x in r['selected']if x['physical'][0]==side);blob=(O/row['relative_path']).read_bytes()
  for kind in('legacy_texel_only_crc','payload_bit','truncated'):
   bad=bytearray(blob)
   if kind=='legacy_texel_only_crc':struct.pack_into('<I',bad,36,zlib.crc32(bad[144:])&0xffffffff)
   elif kind=='payload_bit':bad[-1]^=1
   else:bad=bad[:-1]
   path=H/('negative-%d-%s.re4tex'%(side,kind));path.write_bytes(bad);negatives.append(dict(path=str(path),kind=kind,dimension=side))
 run=subprocess.run([str(P/'host/reader-on'),*[x['path']for x in negatives]],capture_output=True,text=True,timeout=15);(H/'output-negative.txt').write_text(run.stdout);(H/'stderr-negative.txt').write_text(run.stderr);assert run.returncode==0 and not run.stderr and len(run.stdout.splitlines())==len(negatives)and all(x!='ok|ok'for x in run.stdout.splitlines())
 report=dict(status='PASS_ACTUAL_PACKAGE_SHARED_BATCH_REUSED_IMMUTABLE_HOST_BINARY',positive_cases=len(paths),strict_adopt_and_stream_CRC1=True,mip_disabled_rejections=len(paths),negative_cases=negatives,outputs=outputs,source_pins=old['source_pins'],original_commands=old['commands'],binary_reuse_from=str(P/'host-gate.json'),limits=old['limits']);(O/'host-gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(positive=len(paths),OFF_rejects=len(paths),corrupt_rejects=len(negatives),no_rebuild=True)))
if __name__=='__main__':main()
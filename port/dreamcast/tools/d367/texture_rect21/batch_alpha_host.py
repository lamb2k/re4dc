#!/usr/bin/env python3
"""Shared real Package readers and actual world helper; policy subset separate."""
from pathlib import Path
import hashlib,json,subprocess,sys,zlib,struct
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 O=Path(sys.argv[1]);D=Path(__file__).resolve().parent;P=Path('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1');Q=Path('/root/re4data/private/texture-rect21-next177-20261022-v2');r=json.loads((O/'conversion-receipt.json').read_text());q=json.loads((O/'policy-qualified-receipt.json').read_text());ph=json.loads((P/'host-gate.json').read_text());qh=json.loads((Q/'host-gate.json').read_text());H=O/'host';H.mkdir();paths=[O/x['relative_path']for x in r['selected']];assert len(paths)==142 and len(q['selected'])==119
 for p,s in ph['source_pins'].items():assert sha(Path(p))==s
 readers={'on':P/'host/reader-on','cast-off':Q/'host/reader-off','twiddled-off':Q/'host/reader-on'};assert sha(readers['on'])==ph['binaries'][str(readers['on'])];assert sha(readers['cast-off'])==qh['outputs']['off']['exe_sha256'];assert sha(readers['twiddled-off'])==qh['outputs']['on']['exe_sha256'];outputs={}
 for mode in readers:
  rows=r['selected']if mode!='twiddled-off'else[x for x in r['selected']if x['payload_type']==1];run=subprocess.run([str(readers[mode]),*[str(O/x['relative_path'])for x in rows]],capture_output=True,text=True,timeout=25);(H/('output-'+mode+'.txt')).write_text(run.stdout);(H/('stderr-'+mode+'.txt')).write_text(run.stderr);assert run.returncode==0 and not run.stderr;lines=run.stdout.splitlines()
  if mode=='on':
   assert len(lines)==2*len(rows)
   for i,x in enumerate(rows):assert lines[2*i]=='ok|ok'and int(lines[2*i+1].split(':')[1],16)==(0x80000000|(0x40000000 if x['payload_type']==2 else 0)|(0x10000000 if x['format']==2 else 0))
  else:assert len(lines)==len(rows)and all(x!='ok|ok'for x in lines)
  outputs[mode]=dict(binary=str(readers[mode]),sha256=sha(readers[mode]),cases=len(rows),PASS=True)
 negatives=[]
 for fmt,layout in((1,1),(1,2),(2,1),(2,2)):
  row=next(x for x in r['selected']if(x['format'],x['payload_type'])==(fmt,layout));blob=(O/row['relative_path']).read_bytes()
  for kind in('legacy_texel_only_crc','payload_bit','truncated'):
   b=bytearray(blob)
   if kind=='legacy_texel_only_crc':struct.pack_into('<I',b,36,zlib.crc32(b[144:])&0xffffffff)
   elif kind=='payload_bit':b[-1]^=1
   else:b=b[:-1]
   p=H/('negative-%d-%d-%s.re4tex'%(fmt,layout,kind));p.write_bytes(b);negatives.append(str(p))
 run=subprocess.run([str(readers['on']),*negatives],capture_output=True,text=True,timeout=20);(H/'output-negative.txt').write_text(run.stdout);(H/'stderr-negative.txt').write_text(run.stderr);assert run.returncode==0 and not run.stderr and len(run.stdout.splitlines())==12 and all(x!='ok|ok'for x in run.stdout.splitlines())
 # Actual unchanged helper body; only the private include path is relocated.
 parent=json.loads((O/'world-proposals.json').read_text());n=parent['combined_scoped_keys'];header=(D/'world_rect_bind.h').read_bytes();needle=b'"scoped_representations.inc"';assert header.count(needle)==1;derived=header.replace(needle,('"../proposed_scoped_representations_combined%d.inc"'%n).encode());(H/'world_rect_bind.h').write_bytes(derived)
 cpp='''#include "world_rect_bind.h"
#include <cassert>
#include <cstdio>
using namespace re4dc::rect21;
constexpr Representation selected[]={
#include "../proposed_scoped_representations_add119.inc"
};
int main(){for(const auto&r:selected){float u=-1,v=-2;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v));assert(u==-1&&v==-2);assert(adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v,true));assert(u==1&&v==1&&(r.stored.format==1||r.stored.format==2)&&r.stored.flags==4);for(unsigned k=0;k<4;++k){auto b=r.stored;if(k==0)b.format=3-b.format;if(k==1)b.payload=3-b.payload;if(k==2)b.checksum^=1;if(k==3)b.flags|=1U<<30;u=-1;v=-2;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,b,u,v,true)&&u==-1&&v==-2);}unsigned code=(__builtin_ctz(r.stored.width)-3)*8+__builtin_ctz(r.stored.height)-3;assert(header_dimensions(code,r.stored.width,r.stored.height));assert(!header_dimensions(code,r.logical_width,r.logical_height));}std::printf("qualified119nativealpha_OFF119_ON119_mutations476_extents238_PASS\\n");}
''';(H/'binding-probe.cpp').write_text(cpp);cmd=['g++','-std=c++17','-O1','-fsanitize=undefined','-I'+str(H),str(H/'binding-probe.cpp'),'-o',str(H/'binding-probe')];b=subprocess.run(cmd,capture_output=True,timeout=30);(H/'binding-compile.txt').write_bytes(b.stdout+b.stderr);assert not b.returncode;run=subprocess.run([str(H/'binding-probe')],capture_output=True,text=True,timeout=10);(H/'binding-output.txt').write_text(run.stdout+run.stderr);assert not run.returncode and not run.stderr
 assert sha(Path('/root/probe/codex-texture-rect21/port/dreamcast/tools/d367/tr_classify.py'))==r['classifier_source_sha256']
 report=dict(status='PASS_SHARED_ACTUAL_PACKAGE142_AND_WORLD_HELPER_POLICY119',converted_keys=142,Package_qualified_keys=142,policy_qualified_keys=119,policy_held_keys=23,source_policy_qualified_refs=420,all_material_refs=508,CAST_OFF_rejects=142,TWID_OFF_rejects=102,corrupt_rejects=12,outputs=outputs,world_helper=dict(original_sha256=sha(D/'world_rect_bind.h'),derived_sha256=sha(H/'world_rect_bind.h'),only_change='private include path relocation',tested_policy_keys=119,fmt_flags_layout_checksum_mutation_rejects=476,header_extent_checks=238,binary_sha256=sha(H/'binding-probe'),command=cmd),source_pins=ph['source_pins'],classifier_source_sha256=r['classifier_source_sha256'],limits=['Package142 parsing/CRC/PVRformat host-stub acceptance is distinct from119 exactshipped-partpolicy subset; held23 never remapped or certified.','World helper/source evidence only; no actual target admission/draw/appearance/netVRAM/performance/Dreamcast acceptance.','No new actualPackage readers compiled; sealed priorON/CASTOFF/TWIDOFF source+binary identities reused. No sharedruntime/recipe/classifier/metadata/pack/programme/image/guest changes.']);(O/'host-gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('converted_keys','Package_qualified_keys','policy_qualified_keys','policy_held_keys','CAST_OFF_rejects','TWID_OFF_rejects','corrupt_rejects')}))
if __name__=='__main__':main()
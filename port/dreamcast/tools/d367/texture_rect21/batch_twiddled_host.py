#!/usr/bin/env python3
"""Shared TWID Package host gate plus actual immutable world descriptor helper."""
from pathlib import Path
import hashlib,json,subprocess,sys,zlib,struct
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 O,P=map(Path,sys.argv[1:3]);D=Path(__file__).resolve().parent;ROOT=D.parents[2];r=json.loads((O/'conversion-receipt.json').read_text());old=json.loads((P/'host-gate.json').read_text());H=O/'host';H.mkdir();paths=[O/x['relative_path']for x in r['selected']];assert len(paths)==18
 for p,digest in old['source_pins'].items():assert sha(Path(p))==digest
 cmd=list(old['commands']['on']);cmd[-1]=str(H/'reader-on');cmd.insert(cmd.index('-o'),'-DRE4DC_TEX_TWIDDLED_MIPMAP=1');pins={str(x):sha(x)for x in(P/'host').rglob('*')if x.is_file()and(x.suffix in('.h','.cpp')or x.name=='reader-on')};build=subprocess.run(cmd,capture_output=True,timeout=40);(H/'compile.txt').write_bytes((build.stdout+build.stderr)[:65536]);assert build.returncode==0 and all(sha(Path(p))==s for p,s in pins.items())
 for mode,exe in [('on',H/'reader-on'),('twiddled-off',P/'host/reader-on')]:
  if mode!='on':assert sha(exe)==old['outputs']['on']['exe_sha256']
  run=subprocess.run([str(exe),*map(str,paths)],capture_output=True,text=True,timeout=20);(H/('output-'+mode+'.txt')).write_text(run.stdout);(H/('stderr-'+mode+'.txt')).write_text(run.stderr);assert run.returncode==0 and not run.stderr;lines=run.stdout.splitlines()
  if mode=='on':assert len(lines)==36 and all(lines[2*i]=='ok|ok'and int(lines[2*i+1].split(':')[1],16)&0xc0000000==0x80000000 for i in range(18))
  else:assert len(lines)==18 and all(x!='ok|ok'for x in lines)
 negatives=[];blob=paths[0].read_bytes()
 for kind in('legacy_texel_only_crc','payload_bit','truncated'):
  b=bytearray(blob)
  if kind=='legacy_texel_only_crc':struct.pack_into('<I',b,36,zlib.crc32(b[144:])&0xffffffff)
  elif kind=='payload_bit':b[-1]^=1
  else:b=b[:-1]
  p=H/('negative-'+kind+'.re4tex');p.write_bytes(b);negatives.append(str(p))
 run=subprocess.run([str(H/'reader-on'),*negatives],capture_output=True,text=True,timeout=15);(H/'output-negative.txt').write_text(run.stdout);(H/'stderr-negative.txt').write_text(run.stderr);assert run.returncode==0 and not run.stderr and len(run.stdout.splitlines())==3 and all(x!='ok|ok'for x in run.stdout.splitlines())
 (H/'world_rect_bind.h').write_bytes((D/'world_rect_bind.h').read_bytes());(H/'scoped_representations.inc').write_bytes((O/'proposed_scoped_representations_combined650.inc').read_bytes());(H/'selected18.inc').write_bytes((O/'proposed_scoped_representations_add18.inc').read_bytes())
 probe='''#include "world_rect_bind.h"
#include <cassert>
#include <cstdio>
using namespace re4dc::rect21;
constexpr Representation selected[]={
#include "selected18.inc"
};
int main(){for(const auto&r:selected){float u=-1,v=-2;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v));assert(u==-1&&v==-2);assert(adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v,true));assert(u==1&&v==1&&r.stored.width==16&&r.stored.height==16&&r.stored.payload==1&&r.stored.flags==4);auto bad=r.stored;bad.payload=2;u=-1;v=-2;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,bad,u,v,true)&&u==-1&&v==-2);bad=r.stored;bad.checksum^=1;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,bad,u,v,true));assert(header_dimensions(9,16,16));assert(!header_dimensions(9,r.logical_width,r.logical_height));}std::printf("selected18_TWID_ON18_OFF18_VQmutation18_CRCmutation18_extent36_PASS\\n");}
''';(H/'binding-probe.cpp').write_text(probe);bc=['g++','-std=c++17','-O1','-fsanitize=undefined','-I'+str(H),str(H/'binding-probe.cpp'),'-o',str(H/'binding-probe')];b=subprocess.run(bc,capture_output=True,timeout=20);(H/'binding-compile.txt').write_bytes(b.stdout+b.stderr);assert b.returncode==0;run=subprocess.run([str(H/'binding-probe')],capture_output=True,text=True,timeout=10);(H/'binding-output.txt').write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr
 native=ROOT/'game/platform/native_ui.cpp';text=native.read_text();a=text.index('    const Key key{k[0],k[1]};',text.index('int re4dc_ps2_world_direct_begin'));b=text.index('    const unsigned pass=k[4];',text.index('    const auto& t=handle->package.textures()[0];',a));clip=text[a:b];assert clip.count('if(!rect_scale(*handle))')==2 and 't.payload,t.data_size' in clip and 'header_dimensions' in clip and 'kPayloadVq'not in clip;(H/'actual-direct-hot-cold-source.txt').write_text(clip)
 report=dict(status='PASS_TWID_PACKAGE_AND_SOURCE_WORLD_BINDING_HOST_ONLY',positive_cases=18,strict_adopt_and_stream_CRC1=True,twiddled_OFF_rejects=18,corrupt_rejects=3,PVR_format_bit31=True,PVR_VQ_bit30=False,physical_dimensions=[16,16],world_descriptor_helper='Unchanged actual helper accepts18candidate descriptor/key/logical tuple; OFF/VQ-layout/CRC/extent negatives pass; cached+cold actualsource both invoke gate.',commands=dict(Package=cmd,binding=bc),binaries={str(H/'reader-on'):sha(H/'reader-on'),str(P/'host/reader-on'):sha(P/'host/reader-on'),str(H/'binding-probe'):sha(H/'binding-probe')},source_pins=old['source_pins'],reuse_pins_pre_post=pins,world_bind_sha256=sha(D/'world_rect_bind.h'),native_ui_sha256=sha(native),source_guard_scope='No VQ-only guard in actual world immutable descriptor helper or direct hot/cold gate; payload1/mip4 allowed only after exact table selection. Generic held world-profile guards unchanged.',limits=['Host Package/PVR stubs and actual helper/sourcepath proof; no target draw/native admission/TA/VRAM/look/performance acceptance.','Source programme/TU unchanged. Private650table and15delta worlds unselected; lifecycle and main integration gates remain.']);(O/'host-gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('status','positive_cases','twiddled_OFF_rejects','corrupt_rejects')}))
if __name__=='__main__':main()
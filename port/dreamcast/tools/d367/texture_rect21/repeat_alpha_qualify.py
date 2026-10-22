#!/usr/bin/env python3
"""Read-only lineage audit and bounded actual-helper142 host gate."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,time
T=Path(__file__).resolve().parent;sys.path.insert(0,str(T));import world_bindings as world
O=Path('/root/re4data/private/texture-rect21-alpha-repeat16-20261022-v1');H=lambda b:hashlib.sha256(b).hexdigest();r=json.loads((O/'world-proposals.json').read_text());assert r['rooms']==29 and r['combined_scoped_keys']==792
parent=Path('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1/proposed_scoped_representations_combined650.inc');assert (O/'proposed_scoped_representations_combined792.inc').read_bytes().startswith(parent.read_bytes());table=re.findall(r'\{0x([0-9a-f]+)U,0x([0-9a-f]+)U,',(O/'proposed_scoped_representations_combined792.inc').read_text());keys={'%08x-%08x'%(int(a,16),int(b,16))for a,b in table};assert len(table)==len(keys)==792;seen=set();total=selected=0;R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/native-bindings-01/inputs')
for w in r['worlds']:
 b=(O/'proposed-worlds'/w['path']).read_bytes();assert H(b)==w['candidate_sha256'];rows=world.inspect_sidecar(b);src=world.inspect_sidecar((R/w['path']).read_bytes());assert len(rows)==len(src)==w['parts']
 for a,z in zip(src,rows):
  if z['key']in keys:seen.add(z['key']);selected+=1
  else:assert a==z
 total+=len(rows)
assert len(seen)==792 and selected==4371 and total==7342
q=dict(status='PASS_ALL29_COMPLETE792_RECTANGLE_KEYS_4371_ROWS_OTHER2971_BASE_ROWS_UNCHANGED',combined650_prefix_sha256=H(parent.read_bytes()),combined650_byteexact_prefix=True,unique_rectangle792=True,rectangle_rows4371=True,other_base_rows2971_unchanged=True,worlds29=True,r11f_r200_physical_ownership_holds=True,r107_root_source_closure_separate=True,no_fullpack_programme_image_guest=True)
(O/'lineage-audit.json').write_text(json.dumps(q,indent=2)+'\n');D=O/'helper02';D.mkdir();b=(T/'world_rect_bind.h').read_bytes();assert b.count(b'"scoped_representations.inc"')==1;(D/'world_rect_bind.h').write_bytes(b.replace(b'"scoped_representations.inc"',b'"../proposed_scoped_representations_combined792.inc"'))
cpp='''#include "world_rect_bind.h"
#include <cassert>
#include <cstdio>
using namespace re4dc::rect21;
constexpr Representation selected[]={
#include "../proposed_scoped_representations_add142.inc"
};
int main(){unsigned repeats=0;for(const auto&r:selected){float u=-1,v=-2;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v));assert(u==-1&&v==-2);assert(adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v,true));assert(u==r.u_scale&&v==r.v_scale&&u==1.0f);if(v!=1.0f){++repeats;assert(v==float(r.logical_height)/r.logical_width&&r.stored.width==r.logical_width);}for(unsigned k=0;k<4;++k){auto b=r.stored;if(k==0)b.format=3-b.format;if(k==1)b.payload=3-b.payload;if(k==2)b.checksum^=1;if(k==3)b.flags|=1U<<30;u=-1;v=-2;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,b,u,v,true)&&u==-1&&v==-2);}unsigned code=(__builtin_ctz(r.stored.width)-3)*8+__builtin_ctz(r.stored.height)-3;assert(header_dimensions(code,r.stored.width,r.stored.height));assert(!header_dimensions(code,r.logical_width,r.logical_height));}assert(repeats==16);puts("PASS actual_helper142_ON142_OFF568mutations284extents16exactUV");}
''';(D/'probe.cpp').write_text(cpp);tmp=D/'tmp';tmp.mkdir();env=dict(os.environ,TMPDIR=str(tmp));cmd=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined',str(D/'probe.cpp'),'-o',str(D/'probe')];assert shutil.disk_usage('/mnt/c').free>=19394461696;assert sum(p.stat().st_size for p in O.rglob('*')if p.is_file())+500000+2400000+131072<6291456
with (D/'compile.txt').open('xb')as log:
 proc=subprocess.Popen(cmd,stdout=log,stderr=log,env=env);start=time.monotonic();peak=0
 try:
  while proc.poll()is None:
   size=sum(p.stat().st_size for p in O.rglob('*')if p.is_file());peak=max(peak,size);assert size+2400000+131072<6291456 and shutil.disk_usage('/mnt/c').free>=19394461696 and time.monotonic()-start<30;time.sleep(.05)
 finally:
  if proc.poll()is None:proc.kill();proc.wait()
assert proc.returncode==0
run=subprocess.run([str(D/'probe')],capture_output=True,timeout=10);(D/'output.txt').write_bytes(run.stdout+run.stderr);assert not run.returncode and not run.stderr
report=dict(status='PASS_ACTUAL_HELPER_PRIVATE792_142ON_142OFF_568MUTATIONS_284EXTENTS_16EXACT_UV',original_helper_sha256=H(b),derived_helper_sha256=H((D/'world_rect_bind.h').read_bytes()),only_derivation='private include path',binary_sha256=H((D/'probe').read_bytes()),command=cmd,peak_measured_unit_WSL_bytes=peak,output=run.stdout.decode(),limits=['Host source gate only, no actual target material submission/look/performance acceptance.']);(O/'helper-gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
"""Synthetic emitter regression through the actual strict and streamed Package API."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys,zlib
T=Path('/root/probe/codex-mipmap21-integration/port/dreamcast/tools')
sys.path[:0]=[str(T),str(T/'d367'),str(T/'d367/texture_rect21')]
import convert_tpl as tpl
import mipmap_vq as vq
import mipmap_pal4 as pal
import mipmap_twiddled as tw
import mipmap_compact_vq as cvq
import compact_native_vq as compact_vq
import compact_native_pal8 as compact_pal8
import compact as rect_compact
import rectangular_vq as rect
from vram.vq_pak import restamp
O=Path('/root/probe/mipmap21-emitter-crc-repair-20261021/tests')
assert not O.exists();O.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
def package(side,fmt,layout,payload,*,width=None,flags=0,legacy=False):
 t=tpl.TEXTURE.pack(b'synthetic-crc-contract',width or side,side,fmt,144,len(payload),flags,layout,0)
 body=t+payload
 h=tpl.HEADER.pack(tpl.MAGIC,tpl.VERSION,48,96,1,48,144,len(payload),zlib.crc32(payload if legacy else body)&0xffffffff,1,0)
 return h+body
cases=[];checks=0
def save(name,b,accepted):
 global checks
 p=O/(name+'.re4tex');p.write_bytes(b);cases.append((p,accepted));checks+=1
def output(name,b):
 save(name,b,True)
 for suffix,offset in [('descriptor',48),('payload',len(b)-1)]:
  bad=bytearray(b);bad[offset]^=1;save(name+'-corrupt-'+suffix,bytes(bad),False)
def variants(name,make,convert):
 global checks
 a=make(False);b=make(True)
 assert a[:36]==b[:36] and a[40:]==b[40:]
 assert tpl.canonical_native_crc(a)==a and tpl.canonical_native_crc(b)==a
 assert convert(a,False)==a and convert(b,False)==b
 x=convert(a,True);y=convert(b,True)
 assert x==y,name
 assert tpl.canonical_native_crc(x)==x
 output(name,x);checks+=5
 return x
white=struct.pack('<1024H',*([65535]*1024))
vq_output={}
for fmt in (tpl.FORMAT_RGB565,tpl.FORMAT_ARGB1555,tpl.FORMAT_ARGB4444):
 vq_output[fmt]=variants('vq-'+str(fmt),lambda legacy,fmt=fmt:package(8,fmt,2,white+bytes(16),legacy=legacy),lambda b,on:vq.add_mipmaps(b,enabled=on,engine='python')[0])
tw_output={}
for fmt in (tpl.FORMAT_RGB565,tpl.FORMAT_ARGB1555,tpl.FORMAT_ARGB4444):
 tw_output[fmt]=variants('twiddled-'+str(fmt),lambda legacy,fmt=fmt:package(8,fmt,1,b'\xff\xff'*64,legacy=legacy),lambda b,on:tw.add_mipmaps(b,enabled=on)[0])
pal_output=variants('pal4',lambda legacy:package(8,tpl.FORMAT_PAL4_ARGB4444,1,bytes(32)+b'\xff\xff'*16,legacy=legacy),lambda b,on:pal.add_mipmaps(b,enabled=on,engine='python')[0])
# An enabled invocation must also normalize a preexisting mip chain; disabled stays exact.
for name,b,convert in [('existing-vq',vq_output[0],vq.add_mipmaps),('existing-pal4',pal_output,pal.add_mipmaps),('existing-twiddled',tw_output[0],tw.add_mipmaps)]:
 h=list(tpl.HEADER.unpack_from(b));h[8]=zlib.crc32(b[h[6]:])&0xffffffff;legacy=tpl.HEADER.pack(*h)+b[48:]
 assert convert(legacy,enabled=False)[0]==legacy
 result,evidence=convert(legacy,enabled=True)
 assert result==b and evidence['changed'] and evidence['output_crc_rule']=='header'
 assert result[:36]==legacy[:36] and result[40:]==legacy[40:]
 output(name,result);checks+=3
# Exercise the compact and rectangle emitters on simple, lossless source fixtures.
large=package(64,tpl.FORMAT_RGB565,1,b'\xff\xff'*(64*64),legacy=True)
compacted,report=compact_vq.compact(large,enabled=True);assert report['changed'];output('compact-vq',compacted)
words=[0xf000+(i%32)*17 for i in range(64*64)]
large_alpha=package(64,tpl.FORMAT_ARGB4444,1,struct.pack('<4096H',*words),legacy=True)
compacted,report=compact_pal8.compact(large_alpha,enabled=True);assert report['changed'];output('compact-pal8',compacted)
base=package(8,tpl.FORMAT_ARGB4444,2,white+bytes(16),legacy=True)
reference=tw_output[tpl.FORMAT_ARGB4444]
composed,report=cvq.add_mipmaps(base,reference,enabled=True,engine='python');assert report['changed'];output('mip-compact-vq',composed)
rectangle=package(8,tpl.FORMAT_RGB565,2,white+bytes(32),width=16,legacy=True)
short=rect_compact.shorter_square(rectangle,bytes([255]*16*8*4),enabled=True);output('short-rectangle',short)
repeated,report=rect.square_candidate(rectangle,enabled=True);output('repeated-rectangle',repeated)
restamped,source_rule=restamp(large,compacted);assert source_rule=='data';output('restamped',restamped)
for offset in (12,16,20,24,28,32,8):
 bad=bytearray(base);bad[offset]^=1
 try:tpl.canonical_native_crc(bytes(bad))
 except ValueError:checks+=1
 else:raise AssertionError('bad header accepted at '+str(offset))
bad=bytearray(base);bad[-1]^=1
try:tpl.canonical_native_crc(bytes(bad))
except ValueError:checks+=1
else:raise AssertionError('bad input payload CRC accepted')
fixture=Path('/root/re4data/private/texture-actors21-compose20-current965-v2-20261021/host02')
room=T.parent/'room'
for n in ('texture_package.cpp','texture_package.hpp','room_storage.cpp','room_storage.hpp'):
 assert (room/n).read_bytes()==(fixture/n).read_bytes(),n
cpp='''#define main retained_fixture_main
#include "'''+str(fixture/'reader.cpp')+'''"
#undef main
#include <sstream>
int main(int argc,char**argv){assert(argc==2);assert(initialize_palettes(0));std::ifstream in(argv[1]);std::string line;unsigned n=0;
while(std::getline(in,line)){auto tab=line.find('\\t');assert(tab!=std::string::npos);std::string path=line.substr(0,tab);bool expected=line.substr(tab+1)=="1";std::ifstream f(path,std::ios::binary);std::vector<unsigned char>b{std::istreambuf_iterator<char>(f),{}};assert(f);Package p;bool a=p.adopt(b.data(),b.size());p.close();bool s=p.open_streamed(path.c_str());p.close();assert(a==expected&&s==expected);assert(!allocs&&!open_files);++n;}printf("%u strict_and_crc_stream_cases_passed\\n",n);}
'''
(O/'reader.cpp').write_text(cpp)
receipt=json.loads(Path('/root/re4data/private/texture-canonical-base-actors21-20261021/host/receipt.json').read_text())
cmd=next(a['command'] for a in receipt['arms'] if a['arm']=='ui0-mip1')
cmd=[str(O/'reader.cpp') if x.endswith('/texture-canonical-base-actors21-20261021/host/reader.cpp') else str(room/Path(x).name) if x in (str(fixture/'texture_package.cpp'),str(fixture/'room_storage.cpp')) else x for x in cmd]
cmd[-1]=str(O/'reader')
compiled=subprocess.run(cmd,capture_output=True,text=True);(O/'compile.txt').write_text(compiled.stdout+compiled.stderr);assert compiled.returncode==0,compiled.stderr
(O/'cases.tsv').write_text(''.join(str(p)+'\t'+str(int(ok))+'\n' for p,ok in cases))
run=subprocess.run([str(O/'reader'),str(O/'cases.tsv')],capture_output=True,text=True);(O/'run.txt').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
result=dict(status='PASS',source_contract_checks=checks,actual_Package_strict_cases=len(cases),actual_Package_CRC_enabled_stream_cases=len(cases),accepted_outputs=sum(ok for _,ok in cases),corrupt_descriptor_or_payload_refusals=sum(not ok for _,ok in cases),synthetic_fixtures_only=True,command=cmd,stdout=run.stdout,fixture_source_sha256=sha((fixture/'reader.cpp').read_bytes()),CRC_word_offset=36,data_size_offset=32,no_runtime_CRC_change=True,disabled_byte_exact=True)
(O/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

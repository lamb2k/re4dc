#!/usr/bin/env python3
"""Characterize unmodified actual AICA layout failure control flow; no game data."""
from pathlib import Path
import argparse,subprocess,tempfile,json,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args();root=Path(__file__).resolve().parents[5];out=a.out or Path(tempfile.mkdtemp(prefix='audio-layout-audit-'));out.mkdir(parents=True,exist_ok=True)
p=root/'port/dreamcast/game/platform/audio_aica.cpp';s=p.read_text();first=s.index('bool layout_init(');end=s.index('// A build-time converted bank:',first);function=s[first:end]
prefix=r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
using u32=std::uint32_t;
struct AicaBankHeader {u32 slot_bytes[9]{};};
struct Slot {u32 base=0,size=0;};Slot g_slot[9];bool g_layout,g_layoutWarned;u32 g_aicaUsed,g_strRing;
constexpr u32 kStrRingBytes=128,kAicaPoolBytes=4096,kMovieReserveBytes=256;
unsigned alloc_calls,fail_call;std::map<u32,u32> held;
void re4dc_log(const char*,...){}
u32 snd_mem_malloc(u32 n){++alloc_calls;if(alloc_calls==fail_call)return 0;u32 a=alloc_calls*256;held[a]=n;return a;}
void snd_mem_free(u32 a){assert(held.erase(a)==1);}
void reset(){std::memset(g_slot,0,sizeof(g_slot));g_layout=g_layoutWarned=false;g_aicaUsed=g_strRing=0;alloc_calls=fail_call=0;held.clear();}
"""
main=r"""
int main(){
 AicaBankHeader h{};h.slot_bytes[0]=h.slot_bytes[1]=h.slot_bytes[2]=1024;
 reset();assert(layout_init(h));assert(g_aicaUsed==3200&&held.size()==4&&g_strRing);auto calls=alloc_calls;assert(layout_init(h)&&alloc_calls==calls);
 reset();fail_call=1;assert(!layout_init(h));assert(g_aicaUsed==0&&held.empty()&&!g_layout);fail_call=0;assert(layout_init(h));
 reset();fail_call=2;assert(!layout_init(h));assert(held.empty()&&!g_layout);assert(g_aicaUsed==1024); // Characterizes phantom accounting after rollback.
 fail_call=0;calls=alloc_calls;assert(!layout_init(h)&&alloc_calls==calls); // Retry is refused although the allocator holds zero bytes.
 reset();fail_call=4;assert(layout_init(h));assert(g_layout&&!g_strRing&&held.size()==3);calls=alloc_calls;fail_call=0;assert(layout_init(h)&&alloc_calls==calls&&!g_strRing); // Ring failure is latched as complete.
 std::puts("PASS characterization: warm reuse; first allocation retry; partial rollback leaves phantom bytes; ring failure does not retry");
}
"""
cpp=prefix+function+main;(out/'actual-audio-layout.cpp').write_text(cpp);cmd=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(out/'actual-audio-layout.cpp'),'-o',str(out/'test')]
c=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
r=subprocess.run([str(out/'test')],capture_output=True,text=True);(out/'run.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
receipt={'source':str(p.relative_to(root)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'function_sha256':hashlib.sha256(function.encode()).hexdigest(),'result':r.stdout.strip(),'scope':'Unmodified actual function with mock AICA allocator and reduced synthetic capacities. Failure-path characterization, not a runtime fix or observed console cause.'};(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

#!/usr/bin/env python3
"""Actual-source off/on AICA initialization and ring recovery; synthetic allocator, no game data."""
from pathlib import Path
import argparse,subprocess,tempfile,hashlib,json
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args();root=Path(__file__).resolve().parents[5];out=a.out or Path(tempfile.mkdtemp(prefix='audio-recovery-source-'));out.mkdir(parents=True,exist_ok=True)
p='port/dreamcast/game/platform/audio_aica.cpp';candidate=(root/p).read_text();base=subprocess.check_output(['git','show','c7e0358a44677a15123a7f4233c4115eba627694:'+p],cwd=root,text=True)
def extract(s):
 start=s.index('// First converted bank:');begin=s.rfind('#if defined(RE4DC_AICA_LAYOUT_RECOVER)',s.index('u32 fnv1a('),start);start=begin if begin!=-1 else start;return s[start:s.index('// A build-time converted bank:',start)]
# Verify the real two caller boundaries, independently of the test wrappers below.
assert 'mutex_lock(&g_lock);\n                bool ok = pre ? blk_begin_prebuilt' in candidate
assert 'if(!g_strRing){\n            mutex_lock(&g_lock);\n            stream_ring_retry_locked(timer_us_gettime64());\n            mutex_unlock(&g_lock);\n        }' in candidate
prefix=r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <mutex>
#include <thread>
#include <vector>
using u32=std::uint32_t;using u64=std::uint64_t;
"""
common=r"""
struct AicaBankHeader {u32 slot_bytes[9]{};};struct Slot {u32 base=0,size=0;};Slot g_slot[9];bool g_layout,g_layoutWarned;u32 g_aicaUsed,g_strRing;
constexpr u32 kStrRingBytes=128,kAicaPoolBytes=4096,kMovieReserveBytes=256;
u64 now;unsigned alloc_calls,fail_call,external_on_fail;bool check_private;std::map<u32,u32> held;std::mutex mu;thread_local bool locked;
struct Gate{std::lock_guard<std::mutex> g;Gate():g(mu){assert(!locked);locked=true;}~Gate(){locked=false;}};
void re4dc_log(const char*,...){}u64 timer_us_gettime64(){return now;}
u32 snd_mem_malloc(u32 n){assert(locked);++alloc_calls;if(check_private)for(auto&s:g_slot)assert(!s.base);
 if(alloc_calls==fail_call){if(external_on_fail){held[90000]=external_on_fail;g_aicaUsed+=external_on_fail;}return 0;}u32 a=alloc_calls*256;assert(!held.count(a));held[a]=n;return a;}
void snd_mem_free(u32 a){assert(locked);assert(held.erase(a)==1);}
"""
wrapper=r"""
void reset(){Gate l;std::memset(g_slot,0,sizeof(g_slot));g_layout=g_layoutWarned=false;g_aicaUsed=g_strRing=0;alloc_calls=fail_call=external_on_fail=0;now=100;check_private=false;held.clear();
#if RE4DC_AICA_LAYOUT_RECOVER
 g_ringRetryAt=0;
#endif
}
std::vector<u32> snapshot(){std::vector<u32>v={g_layout,g_layoutWarned,g_aicaUsed,g_strRing,alloc_calls};for(auto&s:g_slot){v.push_back(s.base);v.push_back(s.size);}for(auto [a,n]:held){v.push_back(a);v.push_back(n);}return v;}
"""
main=r"""
unsigned checks;
#define CK(c) do{assert(c);++checks;}while(0)
int main(){
 ref::AicaBankHeader rh{};off::AicaBankHeader oh{};on::AicaBankHeader h{};for(unsigned i=0;i<9;++i)rh.slot_bytes[i]=oh.slot_bytes[i]=h.slot_bytes[i]=64;
 ref::reset();off::reset();on::reset();{ref::Gate a;off::Gate b;on::Gate c;CK(ref::layout_init(rh));CK(off::layout_init(oh));CK(on::layout_init(h));CK(ref::snapshot()==off::snapshot());CK(ref::snapshot()==on::snapshot());CK(on::g_aicaUsed==704);}
 {ref::Gate a;off::Gate b;on::Gate c;auto calls=on::alloc_calls;CK(ref::layout_init(rh));CK(off::layout_init(oh));CK(on::layout_init(h));CK(on::alloc_calls==calls);CK(ref::snapshot()==off::snapshot());CK(ref::snapshot()==on::snapshot());}
 // A later header with a different layout keeps the first working bank addresses and accounting.
 {ref::Gate a;off::Gate b;on::Gate c;auto rr=rh;auto oo=oh;auto hh=h;rr.slot_bytes[0]=oo.slot_bytes[0]=hh.slot_bytes[0]=96;auto calls=on::alloc_calls;CK(ref::layout_init(rr));CK(off::layout_init(oo));CK(on::layout_init(hh));CK(ref::snapshot()==off::snapshot());CK(ref::snapshot()==on::snapshot());CK(on::alloc_calls==calls&&on::g_slot[0].size==64&&on::g_layoutWarned);}
 // Fault every slot with an existing unrelated allocation; no partial publication or unrelated free/account rollback.
 for(unsigned f=1;f<=9;++f){on::reset();{on::Gate l;on::held[80000]=128;on::g_aicaUsed=128;on::fail_call=f;on::check_private=true;CK(!on::layout_init(h));CK(!on::g_layout&&!on::g_strRing);CK(on::g_aicaUsed==128&&on::held.size()==1&&on::held.at(80000)==128);for(auto&s:on::g_slot)CK(s.base==0&&s.size==0);on::fail_call=0;on::check_private=false;CK(on::layout_init(h));CK(on::g_aicaUsed==832&&on::held.at(80000)==128);}}
 // A second owner changes accounting during a failed allocation callback. Subtract owned bytes, never restore a snapshot.
 on::reset();{on::Gate l;on::g_aicaUsed=128;on::held[80000]=128;on::fail_call=3;on::external_on_fail=64;CK(!on::layout_init(h));CK(on::g_aicaUsed==192&&on::held.size()==2&&on::held.at(90000)==64);}
 // Sparse slot lists and aligned-size accounting.
 for(unsigned f=1;f<=3;++f){on::reset();on::AicaBankHeader sparse{};sparse.slot_bytes[0]=33;sparse.slot_bytes[4]=65;sparse.slot_bytes[8]=97;{on::Gate l;on::fail_call=f;CK(!on::layout_init(sparse));CK(on::g_aicaUsed==0&&on::held.empty());on::fail_call=0;CK(on::layout_init(sparse));CK(on::g_aicaUsed==64+96+128+128);}}
 // Native budget refusal leaves all ownership untouched.
 on::reset();{on::Gate l;on::g_aicaUsed=4000;on::held[80000]=4000;CK(!on::layout_init(h));CK(on::alloc_calls==0&&on::g_aicaUsed==4000&&on::held.size()==1);}
 // Ring failure leaves one-shot slots valid. Both repeated bank entry and reader recovery are bounded and preserve them.
 on::reset();{on::Gate l;on::fail_call=10;CK(on::layout_init(h));CK(on::g_layout&&!on::g_strRing&&on::g_aicaUsed==576);auto calls=on::alloc_calls;auto slots=std::vector<on::Slot>(on::g_slot,on::g_slot+9);for(unsigned i=0;i<100;++i){on::now+=9999;CK(on::layout_init(h));CK(on::alloc_calls==calls);}on::now=1000100;on::fail_call=11;on::stream_ring_retry_locked(on::now);CK(on::alloc_calls==11&&!on::g_strRing);on::now=1000101;on::fail_call=0;on::stream_ring_retry_locked(on::now);CK(on::alloc_calls==11);on::now=2000100;on::stream_ring_retry_locked(on::now);CK(on::g_strRing&&on::g_aicaUsed==704&&on::alloc_calls==12);for(unsigned i=0;i<9;++i)CK(on::g_slot[i].base==slots[i].base&&on::g_slot[i].size==slots[i].size);on::stream_ring_retry_locked(on::now+9000000);CK(on::alloc_calls==12);}
 // Reader polling before a layout, or while remaining aggregate budget cannot cover ring+movie reserve, does nothing destructive.
 on::reset();{on::Gate l;on::stream_ring_retry_locked(on::now);CK(on::alloc_calls==0&&on::g_ringRetryAt==0);on::fail_call=10;CK(on::layout_init(h));auto slots=std::vector<on::Slot>(on::g_slot,on::g_slot+9);on::now+=1000000;on::g_aicaUsed=3840-127;on::fail_call=0;on::stream_ring_retry_locked(on::now);CK(on::alloc_calls==10&&!on::g_strRing);on::g_aicaUsed=576;on::now+=1000000;on::stream_ring_retry_locked(on::now);CK(on::g_strRing&&on::g_aicaUsed==704);for(unsigned i=0;i<9;++i)CK(on::g_slot[i].base==slots[i].base);}
 // The real callers use this lock order: bank initialization and reader polling cannot publish two rings.
 on::reset();{on::Gate l;on::fail_call=10;CK(on::layout_init(h));on::fail_call=0;on::now+=1000000;}
 std::thread bank([&]{for(unsigned i=0;i<100;++i){on::Gate l;assert(on::layout_init(h));}}),reader([&]{for(unsigned i=0;i<100;++i){on::Gate l;on::stream_ring_retry_locked(on::now);}});bank.join();reader.join();{on::Gate l;CK(on::alloc_calls==11&&on::held.size()==10&&on::g_aicaUsed==704);}
 // Two serialized first bank owners: failed partial publication cannot destroy the successful retry.
 on::reset();{on::Gate l;on::fail_call=3;}bool outcomes[2]{};
 std::thread first([&]{on::Gate l;outcomes[0]=on::layout_init(h);}),second([&]{on::Gate l;outcomes[1]=on::layout_init(h);});first.join();second.join();{on::Gate l;CK(outcomes[0]!=outcomes[1]);CK(on::g_layout&&on::g_strRing&&on::g_aicaUsed==704&&on::held.size()==10);}
 // Characterize default-off preservation at the original failure, in addition to target object identity.
 ref::reset();off::reset();{ref::Gate a;off::Gate b;ref::fail_call=off::fail_call=3;CK(!ref::layout_init(rh));CK(!off::layout_init(oh));CK(ref::snapshot()==off::snapshot());CK(ref::g_aicaUsed==128);}
 std::printf("PASS checks=%u actual-source layout/ring recovery; disabled matches control; serialized owner/reader race\n",checks);
}
"""
cpp=prefix
for name,src,on in [('ref',base,0),('off',candidate,0),('on',candidate,1)]:cpp+='\nnamespace '+name+' {\n#undef RE4DC_AICA_LAYOUT_RECOVER\n#define RE4DC_AICA_LAYOUT_RECOVER '+str(on)+'\n'+common+extract(src)+wrapper+'\n}\n'
cpp+=main;(out/'actual-source.cpp').write_text(cpp);cmd=['g++','-std=c++17','-O1','-g','-pthread','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(out/'actual-source.cpp'),'-o',str(out/'test')];c=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
r=subprocess.run([str(out/'test')],capture_output=True,text=True);(out/'run.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
receipt={'base':'c7e0358a44677a15123a7f4233c4115eba627694','source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'generated_sha256':hashlib.sha256(cpp.encode()).hexdigest(),'result':r.stdout.strip(),'scope':'Actual layout/helper functions with mock allocator/timer; ASan+UBSan, serialized bank/reader threads; exact real lock callsites checked. No full backend/console or disc I/O diagnosis.'};(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

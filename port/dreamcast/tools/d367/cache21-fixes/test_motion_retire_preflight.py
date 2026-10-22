"""Actual bulk motion retirement control-flow tests; allocator/discard/lock are boundaries."""
from pathlib import Path
import argparse,hashlib,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[5]
def extract(text,name):
 start=text.index(name);opening=text.index('{',start);level=1;end=opening+1
 while level:
  level+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 assert shutil.disk_usage('/mnt/c').free>=18*1024**3+64*1024**2
 a.out.mkdir(parents=True,exist_ok=False)
 src=ROOT/'port/dreamcast/game/platform/native_motion.cpp'
 data=src.read_text();release=extract(data,'void release_binding(')
 retire=extract(data,'extern "C" void re4dc_motion_retire_all(')
 baseline=subprocess.check_output(['git','-C',str(ROOT),'show','3c154c8e6:port/dreamcast/game/platform/native_motion.cpp'],text=True)
 old=extract(baseline,'extern "C" void re4dc_motion_retire_all(')
 pre=r'''
#include <cassert>
#include <cstring>
#include <cstdint>
#include <cstdio>
#include <vector>
struct Slot { const unsigned char* data; unsigned pins; };
struct Binding { const void* archive; Slot* slots; unsigned count,hot_bytes,resident,slab_bytes; void* slab[2]; bool joined,bounded; unsigned char*seen; };
Binding bindings[3];Slot slots[3];
struct { unsigned metadata_bytes,hot_bytes,resident_bytes; }stats;
std::vector<std::uintptr_t> frees;unsigned discards,failed,journal;bool held;
struct Stop{};
[[noreturn]]void fail(const char*){assert(held);++failed;throw Stop{};}
struct Locked{Locked(){assert(!held);held=true;}~Locked(){held=false;}};
unsigned aligned(unsigned n){return(n+31u)&~31u;}
void re4dc_motion_free(void*p){assert(held);frees.push_back(std::uintptr_t(p));}
void discard(Binding&b,unsigned i){assert(held);assert(!b.slots[i].pins);++discards;b.slots[i].data=nullptr;}
struct {void binding_changed(unsigned){assert(held);++journal;}}resume_journal;
'''
 tests=r'''
void setup(){
 std::memset(bindings,0,sizeof(bindings));std::memset(slots,0,sizeof(slots));
 stats={};frees.clear();discards=failed=journal=0;held=false;
 for(unsigned i=0;i<3;++i){
  auto&b=bindings[i];b.archive=(void*)(std::uintptr_t(0x1000+i*0x100));b.slots=&slots[i];b.count=1;b.hot_bytes=7+i;slots[i].data=(unsigned char*)std::uintptr_t(0x2000+i*0x100);
  stats.metadata_bytes+=aligned(sizeof(Slot));stats.hot_bytes+=b.hot_bytes;
#if RE4DC_MOTION_RESERVE
  b.slab_bytes=32;b.slab[0]=(void*)std::uintptr_t(0x3000+i*0x100);
#if RE4DC_MOTION_RESERVE_PACK
  b.joined=true;b.slab[1]=(char*)b.slab[0]+32;
#else
  b.slab[1]=(void*)std::uintptr_t(0x4000+i*0x100);
#endif
  stats.metadata_bytes+=64;
#endif
 }
}
bool run(){try{re4dc_motion_retire_all();return false;}catch(const Stop&){return true;}}
int main(){
 unsigned cases=0;
 for(unsigned pin=0;pin<3;++pin){
  setup();slots[pin].pins=1;Binding before[3];std::memcpy(before,bindings,sizeof before);auto meta=stats.metadata_bytes,hot=stats.hot_bytes;
  assert(run());assert(failed==1&&!held);
#if RE4DC_MOTION_RETIRE_PREFLIGHT
  assert(frees.empty()&&discards==0&&journal==0);assert(std::memcmp(before,bindings,sizeof before)==0);assert(stats.metadata_bytes==meta&&stats.hot_bytes==hot);
#else
  assert(discards==pin);for(unsigned i=0;i<pin;++i)assert(!bindings[i].archive);assert(bindings[pin].archive);
#endif
  ++cases;
 }
 setup();assert(!run());assert(!failed&&!held&&discards==3);assert(!stats.metadata_bytes&&!stats.hot_bytes);for(auto&b:bindings)assert(!b.archive);++cases;
 setup();bindings[1].archive=nullptr;slots[1].pins=1;assert(!run());assert(discards==2&&!failed&&!held);assert(slots[1].pins==1);++cases;
 setup();for(auto&b:bindings)b.archive=nullptr;slots[2].pins=1;assert(!run());assert(!discards&&frees.empty()&&!failed&&!held);++cases;
 setup();bindings[1].count=0;slots[1].pins=1;assert(!run());assert(discards==2&&!failed&&!held);++cases;
 setup();slots[0].pins=1;slots[2].pins=2;assert(run());assert(!discards&&frees.empty()&&!held);++cases;
 std::printf("MOTION_RETIRE_CASES=%u guard=%d reserve=%d pack=%d PASS\n",cases,RE4DC_MOTION_RETIRE_PREFLIGHT,RE4DC_MOTION_RESERVE,RE4DC_MOTION_RESERVE_PACK);
}
'''
 rows=[]
 for reserve,pack in ((0,0),(1,0),(1,1)):
  offhash=None
  for mode,body in (('baseline',old),('off',retire),('on',retire)):
   guard=int(mode=='on');folder=a.out/f'reserve{reserve}-pack{pack}'/mode;folder.mkdir(parents=True)
   code=pre+release+'\n'+body+'\n'+tests
   source=a.out/'actual.cpp';source.write_text(code)
   cmd=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all',f'-DRE4DC_MOTION_RETIRE_PREFLIGHT={guard}',f'-DRE4DC_MOTION_RESERVE={reserve}',f'-DRE4DC_MOTION_RESERVE_PACK={pack}','-DRE4DC_MOTION_BOUNDED_R11F=0','-DRE4DC_MOTION_RESUME=1','-DRE4DC_MOTION_USAGE_LOG=0']
   compile=subprocess.run(cmd+[str(source),'-o',str(folder/'actual')],text=True,capture_output=True)
   (folder/'compile.log').write_text(compile.stdout+compile.stderr);assert compile.returncode==0
   run=subprocess.run([str(folder/'actual')],text=True,capture_output=True)
   (folder/'run.log').write_text(run.stdout+run.stderr);assert run.returncode==0
   print(run.stdout.strip())
   rows.append({'reserve':reserve,'pack':pack,'mode':mode,'command':cmd,'run':run.stdout.strip(),'source_sha256':hashlib.sha256(code.encode()).hexdigest()})
 receipt={'kind':'actual-source-host-control-flow','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'functions':{n:hashlib.sha256(b.encode()).hexdigest()for n,b in [('release_binding',release),('retire_all',retire)]},'variants':rows,'limits':['Lock ordering is a host assertion boundary, not KOS scheduling proof.','Discard/allocator frees are exact call boundaries, no actual memory allocator.','No whole-room reset/weapon/overlay/admission freeze or target acceptance.']}
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()


"""Actual room allocation adapter: budgets, failure, and detach-before-free.
The source UI translation unit tail is compiled unchanged with a small fake
source allocator; no renderer or allocation policy is reimplemented here.
Room heap-4 cells are freed to heap 4 by handle (never to the OS current
heap), only while the heap generation they came from is live.
"""
from pathlib import Path
import shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[3]
@unittest.skipUnless(shutil.which("g++"),"host compiler required")
class PreparationStorage(unittest.TestCase):
 def test_room_owner_budget_and_retirement(self):
  game=ROOT/"port/dreamcast/game"
  implementation=(game/"ui_bridge.cpp").read_text().split('#include "native_model.h"',1)[1]
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   code=r"""
#include "native_model.h"
#include <cassert>
#include <cstdarg>
#include <cstring>
#include <cstdint>
constexpr unsigned kCell=32;
alignas(32) unsigned char storage[131072+kCell];
struct MemHeap {int handle;std::uintptr_t start,end;}; MemHeap Heap[13];
int current=4,active=1,free_bytes=213824,allocations=0,frees=0,detaches=0;
bool fail=false,live=false;
int MemGetCurrentHeap(){return current;}
int memCheckHeapActive(int heap){assert(heap==4);return active;}
extern "C" int OSCheckHeap(int){return free_bytes;}
void* mem_calloc(unsigned bytes,const char*,int,int flag,int heap){
 assert(bytes==sizeof(storage) && !flag && heap==4 && !live);
 ++allocations;if(fail)return nullptr;
 free_bytes-=bytes+64;live=true;std::memset(storage,0xA5,bytes);std::memset(storage,0,bytes);return storage;
}
void* mem_alloc(unsigned,const char*,int,int,int){assert(!"static packages are not built here");return nullptr;}
extern "C" void OSFreeToHeap(int handle,void* p){
 assert(handle==Heap[4].handle && p==storage && live && detaches>frees);++frees;live=false;free_bytes+=sizeof(storage)+64;
}
extern "C" void re4dc_model_detach_retained_storage(){++detaches;}
extern "C" void re4dc_log(const char*,...){}
"""+'#include "native_model.h"'+implementation+r"""
unsigned char* const payload=storage+kCell;
int main(){unsigned bytes=1,generation,cells,cell_bytes,stale,refused;
 Heap[4]={7,reinterpret_cast<std::uintptr_t>(storage),reinterpret_cast<std::uintptr_t>(storage)+sizeof(storage)};
 // No room heap yet (boot, title): nothing may be carved from heap 4.
 re4dc_model_preparation_owner((void*)1);
 assert(!re4dc_model_retained_storage(&bytes) && bytes==0 && allocations==0);
 re4dc_model_preparation_owner(nullptr);
 re4dc_room4_open();
 assert(!re4dc_model_retained_storage(&bytes) && bytes==0 && allocations==0);
 re4dc_model_preparation_owner((void*)1);current=3;
 assert(!re4dc_model_retained_storage(&bytes) && !allocations);
 current=4;active=0;assert(!re4dc_model_retained_storage(&bytes) && !allocations);active=1;
 for(unsigned cycle=0;cycle<3;++cycle){
  re4dc_model_preparation_owner(reinterpret_cast<void*>(std::uintptr_t(1+cycle)));
  assert(re4dc_model_retained_storage(&bytes)==payload && bytes==131072 && free_bytes==82656);
  const int count=allocations;payload[0]=7;
  assert(re4dc_model_retained_storage(&bytes)==payload && payload[0]==7 && allocations==count);
  // During the inventory swap, room ownership survives but heap 12 draws
  // cannot reacquire this room cell. Restoring heap 4 reuses the same cell.
  current=12;active=0;
  for(unsigned draw=0;draw<3;++draw)
   assert(!re4dc_model_retained_storage(&bytes) && bytes==0 && allocations==count && live && payload[0]==7);
  current=4;active=1;
  assert(re4dc_model_retained_storage(&bytes)==payload && bytes==131072 && allocations==count && payload[0]==7);
  assert(re4dc_room4_state(&generation,&cells,&cell_bytes,&stale,&refused) && cells==1 && cell_bytes==131072);
  re4dc_model_preparation_owner(nullptr);assert(!live && free_bytes==213824);
  re4dc_model_preparation_owner(nullptr);assert(!live);
  assert(re4dc_room4_state(&generation,&cells,&cell_bytes,&stale,&refused) && cells==0 && !stale);
 }
 assert(allocations==3 && frees==3);
 free_bytes=66592;re4dc_model_preparation_owner((void*)4);
 assert(!re4dc_model_retained_storage(&bytes) && bytes==0 && allocations==3);
 free_bytes=213824;assert(!re4dc_model_retained_storage(&bytes) && allocations==3);
 re4dc_model_preparation_owner(nullptr);re4dc_model_preparation_owner((void*)5);
 fail=true;assert(!re4dc_model_retained_storage(&bytes) && allocations==4);
 fail=false;assert(!re4dc_model_retained_storage(&bytes) && allocations==4);
 re4dc_model_preparation_owner(nullptr);re4dc_model_preparation_owner((void*)6);
 assert(re4dc_model_retained_storage(&bytes)==payload && allocations==5);
 re4dc_model_preparation_owner((void*)7);assert(!live && frees==4);
 assert(re4dc_model_retained_storage(&bytes)==payload && allocations==6);
 re4dc_model_preparation_owner(nullptr);assert(!live && free_bytes==213824);
 // StageSet closed the room heap: the next room's owner gets nothing until
 // gameRoomMemInit rebuilt heap 4.
 re4dc_room4_close();re4dc_model_preparation_owner((void*)8);
 assert(!re4dc_model_retained_storage(&bytes) && allocations==6);
 re4dc_model_preparation_owner(nullptr);
 // A cell that outlives its heap generation (heap 4 rebuilt without the
 // retirement) is dropped, never freed into the rebuilt heap.
 re4dc_room4_open();re4dc_model_preparation_owner((void*)9);
 assert(re4dc_model_retained_storage(&bytes)==payload && allocations==7);
 re4dc_room4_close();re4dc_room4_open();
 live=false;free_bytes=213824; // the source rebuilt heap 4 over the old cell
 re4dc_model_preparation_owner(nullptr);
 assert(frees==5 && re4dc_room4_state(&generation,&cells,&cell_bytes,&stale,&refused) && stale==1 && refused==2);
}
"""
   (root/"fixture.cpp").write_text(code)
   exe=root/"check"
   subprocess.run(["g++","-std=c++20","-O2","-DRE4DC_D349_RENDERER_STACK=1","-fsanitize=address,undefined","-fno-omit-frame-pointer","-I"+str(game/"platform/include"),str(root/"fixture.cpp"),"-o",str(exe)],check=True)
   subprocess.run([str(exe)],check=True)

 def test_subscreen_detaches_before_window_reuse(self):
  source=(ROOT/"port/dreamcast/game/sscrn_bridge.cpp").read_text()
  body=source.split('extern "C" void re4dc_subscreen_swap_open(SubScreenWork* wk)',1)[1].split('extern "C" void re4dc_subscreen_swap_close',1)[0]
  # The real swap entry must detach before packing can use the window as
  # scratch, and before loading inventory data over the retained cache.
  detach=body.index("re4dc_model_detach_retained_storage();")
  self.assertLess(detach,body.index("re4dc_ssb_put_packed("))
  self.assertLess(detach,body.index("memset(wk->pBuf"))
  # This game translation unit does not receive the renderer's private knob
  # header. Compile its actual entry without that macro: the platform detach
  # API itself handles builds with the retained renderer disabled.
  entry=body.split("    build_spans(lo, hi);",1)[0]+"}"
  code=r"""
#include <cassert>
#include <cstdint>
using u32=std::uintptr_t;
struct SubScreenWork {void* pBuf;};
bool swapped=false;constexpr u32 kSsAramSize=0x300000;
int detaches=0;
void re4dc_missing(const char*){assert(false);}
unsigned long long re4dc_ssb_us(){return 0;}
void re4dc_model_detach_retained_storage(){++detaches;}
void swap_entry(SubScreenWork* wk)
"""+entry+r"""
int main(){SubScreenWork wk{(void*)0x800000};swap_entry(&wk);assert(detaches==1);}
"""
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp);(path/"swap.cpp").write_text(code)
   subprocess.run(["g++","-std=c++20",str(path/"swap.cpp"),"-o",str(path/"check")],check=True)
   subprocess.run([str(path/"check")],check=True)


 def test_movie_loan_ownership(self):
  # MOVIE_HEAP_EVICT: the cache lent to a route movie is explicit state (architect review 2026-10-03). While lent a
  # model draw gets nothing and latches no attempt; the movie's retirement re-arms and allocates; a failed
  # reallocation is reported and retried at the next draw.
  game=ROOT/"port/dreamcast/game"
  implementation=(game/"ui_bridge.cpp").read_text().split('#include "native_model.h"',1)[1]
  # the free-map diagnostic walks 32-bit OS heap cells: not part of the ownership logic, left out on the host
  a=implementation.index("#if RE4DC_MOVIE_HEAP_EVICT\n// MOVIE_HEAP_EVICT diagnostic")
  b=implementation.index('#endif\nextern "C" void* re4dc_model_retained_storage',a)
  implementation=implementation[:a]+implementation[b+len("#endif\n"):]
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   code=r"""
#include "native_model.h"
#include <cassert>
#include <cstdarg>
#include <cstring>
#include <cstdint>
#include <cstdio>
constexpr unsigned kCell=32;
alignas(32) unsigned char storage[131072+kCell];
struct MemHeap {int handle;std::uintptr_t start,end;}; MemHeap Heap[13];
int current=4,active=1,free_bytes=213824,allocations=0,frees=0,detaches=0;
bool fail=false,live=false;
int MemGetCurrentHeap(){return current;}
int memCheckHeapActive(int heap){assert(heap==4);return active;}
extern "C" int OSCheckHeap(int){return free_bytes;}
void* mem_calloc(unsigned bytes,const char*,int,int flag,int heap){
 assert(bytes==sizeof(storage) && !flag && heap==4 && !live);
 ++allocations;if(fail)return nullptr;
 free_bytes-=bytes+64;live=true;std::memset(storage,0,bytes);return storage;
}
void* mem_alloc(unsigned,const char*,int,int,int){assert(!"not used");return nullptr;}
extern "C" void OSFreeToHeap(int handle,void* p){
 assert(handle==Heap[4].handle && p==storage && live && detaches>frees);++frees;live=false;free_bytes+=sizeof(storage)+64;
}
extern "C" void re4dc_model_detach_retained_storage(){++detaches;}
extern "C" void re4dc_log(const char*,...){}
"""+'#include "native_model.h"'+implementation+r"""
unsigned char* const payload=storage+kCell;
int main(){unsigned bytes=1,requests=9;
 Heap[4]={7,reinterpret_cast<std::uintptr_t>(storage),reinterpret_cast<std::uintptr_t>(storage)+sizeof(storage)};
 re4dc_room4_open();re4dc_model_preparation_owner((void*)1);
 assert(re4dc_model_retained_storage(&bytes)==payload && allocations==1);
 assert(!re4dc_model_return_retained(&bytes,&requests) && bytes==0);        // nothing lent
 // lend: freed for the movie's staging
 assert(re4dc_model_release_retained()==131072 && !live && frees==1);
 assert(re4dc_model_release_retained()==0);                                  // one loan at a time
 // a stepped movie's game frame draws models during the loan: nothing, and no attempt is latched
 for(int i=0;i<3;++i)assert(!re4dc_model_retained_storage(&bytes) && bytes==0 && allocations==1);
 // retirement (after the staging is freed): the loan ends, the cache comes back, the draws are counted
 assert(re4dc_model_return_retained(&bytes,&requests)==1 && bytes==131072 && requests==3 && live && allocations==2);
 assert(re4dc_model_retained_storage(&bytes)==payload && allocations==2);
 assert(!re4dc_model_return_retained(&bytes,&requests));
 // the reallocation fails (heap 4 short at retirement): reported as 0 B, retried at the next draw
 assert(re4dc_model_release_retained()==131072 && !live);
 fail=true;
 assert(re4dc_model_return_retained(&bytes,&requests)==1 && bytes==0 && requests==0 && allocations==3);
 fail=false;
 assert(re4dc_model_retained_storage(&bytes)==payload && bytes==131072 && allocations==4);
 // a movie retiring while the current heap is not 4: 0 B now, the next draw on heap 4 allocates
 assert(re4dc_model_release_retained()==131072);
 current=3;assert(re4dc_model_return_retained(&bytes,&requests)==1 && bytes==0 && allocations==4);
 current=4;assert(re4dc_model_retained_storage(&bytes)==payload && allocations==5);
 // the room retires during the loan: no owner when the movie retires, nothing allocated, no stale state
 assert(re4dc_model_release_retained()==131072);
 re4dc_model_preparation_owner(nullptr);
 assert(re4dc_model_return_retained(&bytes,&requests)==1 && bytes==0 && allocations==5);
 re4dc_model_preparation_owner((void*)2);
 assert(re4dc_model_retained_storage(&bytes)==payload && allocations==6);
 re4dc_model_preparation_owner(nullptr);assert(!live);
 std::printf("MOVIE_LOAN_OWNERSHIP PASS\n");
}
"""
   (root/"fixture.cpp").write_text(code)
   exe=root/"check"
   subprocess.run(["g++","-std=c++20","-O2","-DRE4DC_D349_RENDERER_STACK=1","-DRE4DC_MOVIE_HEAP_EVICT=1","-fsanitize=address,undefined","-fno-omit-frame-pointer","-I"+str(game/"platform/include"),str(root/"fixture.cpp"),"-o",str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
if __name__=="__main__":unittest.main()

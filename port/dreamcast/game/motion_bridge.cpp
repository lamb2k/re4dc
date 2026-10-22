// Source heap ownership is retained across current-heap changes.
#include "main_mem.h"
#include "dolphin/os/OSAlloc.h"
#include "native_motion.h"
struct MotionAllocation { int heap; unsigned reserved[7]; };
extern "C" int re4dc_motion_current_heap() { return MemGetCurrentHeap(); }
extern "C" void* re4dc_motion_alloc(unsigned bytes) {
    const int owner=Heap[MemGetCurrentHeap()].handle;
    auto* p=(MotionAllocation*)mem_alloc(bytes+sizeof(MotionAllocation),
        "native motion residency",0,1,MEM_HEAP_CURRENT);
    if(!p)return 0;
    p->heap=owner;return p+1;
}
#if RE4DC_SUBSCREEN
// 1 while the heap that allocated `p` still exists (sub screen close drops heap 12's).
extern "C" int re4dc_motion_owner_live(const void* p) {
    const int handle=((const MotionAllocation*)p-1)->heap;
    for(int h=0;h<MEM_HEAP_NUM;++h)if(Heap[h].handle==handle)return 1;
    return 0;
}
#endif
extern "C" void re4dc_motion_free(void* p) {
    if(!p)return;
    auto* allocation=(MotionAllocation*)p-1;
    OSFreeToHeap(allocation->heap,allocation);
}

#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
extern "C" int re4dc_motion_heap_handle() {
    return memCheckHeapActive(4)?Heap[4].handle:-1;
}
extern "C" void* re4dc_motion_source_try_alloc(int heap,unsigned bytes) {
    if(heap<0 || re4dc_motion_heap_handle()!=heap)return nullptr;
    return OSAllocFromHeap(heap,bytes);
}
extern "C" void* re4dc_motion_alloc_optional(unsigned bytes) {
    const int owner=re4dc_motion_heap_handle();
    if(owner<0)return nullptr;
    auto* p=(MotionAllocation*)mem_alloc(bytes+sizeof(MotionAllocation),
        "native motion overflow",0,0,4);
    if(!p)return nullptr;
    p->heap=owner;return p+1;
}
#endif

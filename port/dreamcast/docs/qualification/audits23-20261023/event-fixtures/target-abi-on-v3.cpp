#include "em.h"
#include "room_data.h"
#include "global.h"
template<class T> struct alignas(32) Chunk {
    Chunk<T>* next;
    u32 first, count, bytes;
    u32 reserved[4];
    T* parts() { return (T*)(this + 1); }
};
template<class T> struct alignas(32) Pool {
    Chunk<T>* chunks;
    u32 capacity, bytes, peak, chunks_count, reclaims, failures;
    int heap, handle;
    u32 reserved[7];
    T** slots() { return (T**)(this + 1); }
};

static_assert(sizeof(unsigned int)==4);
extern "C" __attribute__((used,section(".rodata.aud23_abi"))) const unsigned int aud23_abi_v3[] = {
  0x33494241u /* magic */,
  3u /* schema */,
  sizeof(void*) /* pointer_bytes */,
  sizeof(u32) /* u32_bytes */,
  sizeof(cEmMgr) /* manager.sizeof */,
  __builtin_offsetof(cEmMgr,pArray) /* manager.pArray */,
  __builtin_offsetof(cEmMgr,nArray) /* manager.nArray */,
  __builtin_offsetof(cEmMgr,size) /* manager.stride */,
  __builtin_offsetof(cEmMgr,pAlive) /* manager.pAlive */,
  __builtin_offsetof(cEmMgr,Guid) /* manager.Guid */,
  __builtin_offsetof(cEmMgr,pArrayPush) /* manager.pArrayPush */,
  __builtin_offsetof(cEmMgr,pAlivePush) /* manager.pAlivePush */,
  __builtin_offsetof(cEmMgr,nArrayPush) /* manager.nArrayPush */,
  sizeof(cEm) /* actor.sizeof */,
  __builtin_offsetof(cEm,be_flag) /* actor.be_flag */,
  __builtin_offsetof(cEm,pNext) /* actor.pNext */,
  __builtin_offsetof(cEm,serial) /* actor.serial */,
  __builtin_offsetof(cEm,id) /* actor.id */,
  __builtin_offsetof(cEm,type) /* actor.type */,
  __builtin_offsetof(cEm,kindid) /* actor.kindid */,
  __builtin_offsetof(cEm,emset_no) /* actor.emset_no */,
  __builtin_offsetof(cEm,pos) /* actor.pos */,
  __builtin_offsetof(cEm,stat) /* actor.stat */,
  __builtin_offsetof(cEm,pMotion) /* actor.pMotion */,
  __builtin_offsetof(cEm,motState) /* actor.motState */,
  __builtin_offsetof(cEm,frame) /* actor.frame */,
  __builtin_offsetof(cEm,frameMax) /* actor.frameMax */,
  sizeof(cRoomData) /* roomdata.sizeof */,
  __builtin_offsetof(cRoomData,num) /* roomdata.num */,
  __builtin_offsetof(cRoomData,pSaveBuf) /* roomdata.pSaveBuf */,
  __builtin_offsetof(cRoomData,pSave) /* roomdata.pSave */,
  sizeof(RoomSave) /* roomsave.sizeof */,
  __builtin_offsetof(GlobalWork,Status_flg)+sizeof(u32) /* global.SF1 */,
  __builtin_offsetof(GlobalWork,Frame_cnt) /* global.Frame_cnt */,
  __builtin_offsetof(GlobalWork,room_id) /* global.room_id */,
  sizeof(Pool<cEm>) /* pool.sizeof */,
  sizeof(Chunk<cEm>) /* chunk.sizeof */,
  __builtin_offsetof(Pool<cEm>,chunks) /* pool.chunks */,
  __builtin_offsetof(Pool<cEm>,capacity) /* pool.capacity */,
  __builtin_offsetof(Pool<cEm>,bytes) /* pool.bytes */,
  __builtin_offsetof(Pool<cEm>,peak) /* pool.peak */,
  __builtin_offsetof(Pool<cEm>,chunks_count) /* pool.chunks_count */,
  __builtin_offsetof(Pool<cEm>,reclaims) /* pool.reclaims */,
  __builtin_offsetof(Pool<cEm>,failures) /* pool.failures */,
  __builtin_offsetof(Pool<cEm>,heap) /* pool.heap */,
  __builtin_offsetof(Pool<cEm>,handle) /* pool.handle */,
  __builtin_offsetof(Chunk<cEm>,next) /* chunk.next */,
  __builtin_offsetof(Chunk<cEm>,first) /* chunk.first */,
  __builtin_offsetof(Chunk<cEm>,count) /* chunk.count */,
  __builtin_offsetof(Chunk<cEm>,bytes) /* chunk.bytes */,
  RE4DC_WORKAT_INLINE /* target.WORKAT_INLINE */
};

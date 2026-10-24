#include "em.h"
#include "room_data.h"
#include "global.h"
static_assert(sizeof(unsigned int)==4);
extern "C" __attribute__((used,section(".rodata.aud23_abi"))) const unsigned int aud23_abi_v2[] = {
  0x32494241u /* magic */,
  2u /* schema */,
  sizeof(void*) /* pointer_bytes */,
  sizeof(u32) /* u32_bytes */,
  sizeof(cEmMgr) /* manager.sizeof */,
  __builtin_offsetof(cEmMgr,pArray) /* manager.pArray */,
  __builtin_offsetof(cEmMgr,nArray) /* manager.nArray */,
  __builtin_offsetof(cEmMgr,size) /* manager.stride */,
  __builtin_offsetof(cEmMgr,pAlive) /* manager.pAlive */,
  __builtin_offsetof(cEmMgr,Guid) /* manager.Guid */,
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
  __builtin_offsetof(GlobalWork,room_id) /* global.room_id */
};

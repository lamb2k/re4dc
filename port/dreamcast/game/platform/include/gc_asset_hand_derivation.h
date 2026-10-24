#pragma once
#include "gc_asset_hand_copy.h"
#include "gc_asset_payloads.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// One stable state per slot. Source-copy publication uses a new child serial;
// these recognized bounded representation writes preserve that origin serial.
struct HandDerivationState {unsigned serial=0,copy=0;};
inline unsigned hand_derive_begin(HandDerivationState& pending,PayloadProof& child,const HandCopyProof& copy,
    unsigned source,unsigned blob,const void* stream,unsigned capacity,const void* target,unsigned bytes){
    const auto base=reinterpret_cast<std::uintptr_t>(stream),at=reinterpret_cast<std::uintptr_t>(target);
    if(pending.serial || !hand_copy_valid(copy,source,blob) || !payload_copy_current(child) || !base || !at ||
       !capacity || capacity>~std::uintptr_t(0)-base || !bytes || at<base || at-base>capacity || bytes>capacity-unsigned(at-base)){
        child.serial=0;pending={};return 0;
    }
    pending={child.serial,copy.token};child.serial=0;return pending.serial;
}
inline bool hand_derive_end(HandDerivationState& pending,PayloadProof& child,const HandCopyProof& copy,
    unsigned source,unsigned blob,unsigned ticket,bool complete){
    const bool valid=ticket && pending.serial==ticket && pending.copy==copy.token && !child.serial &&
        hand_copy_valid(copy,source,blob) && complete;
    pending={};child.serial=valid?ticket:0;
    if(!valid || !payload_copy_current(child)){child.serial=0;return false;}
    return true;
}
}
#endif

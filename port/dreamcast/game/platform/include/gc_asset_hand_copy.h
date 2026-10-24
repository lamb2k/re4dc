#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// Fixed hand-storage tickets only. The actual owner must prove each blob's
// exact original range/count and issue read completion after a full successful
// CPU copy, joined worker read or synchronous G2 readback. No IO/hash/log here.
struct HandCopyProof {unsigned source=0,token=0;};
static_assert(sizeof(HandCopyProof)==8);
inline unsigned hand_copy_token(unsigned& serial,unsigned blob){
    if(blob>=24 || serial>=0x07ffffffU)return 0;
    return (++serial<<5)|blob;
}
inline bool hand_copy_valid(HandCopyProof proof,unsigned source,unsigned blob){
    return source && proof.source==source && (proof.token>>5) && (proof.token&31)==blob && blob<24;
}
inline HandCopyProof hand_read_begin(unsigned& serial,unsigned source,unsigned blob,unsigned offset,unsigned bytes,unsigned total){
    if(!source || !bytes || offset>total || bytes>total-offset)return {};
    const unsigned token=hand_copy_token(serial,blob);return token?HandCopyProof{source,token}:HandCopyProof{};
}
inline HandCopyProof hand_read_complete(HandCopyProof ticket,unsigned source,unsigned blob,bool complete){
    return complete && hand_copy_valid(ticket,source,blob)?ticket:HandCopyProof{};
}
inline HandCopyProof hand_copy_begin(HandCopyProof& destination,HandCopyProof origin,unsigned& serial,unsigned source,unsigned blob){
    const unsigned token=hand_copy_token(serial,blob);destination={0,token};
    return token && hand_copy_valid(origin,source,blob)?HandCopyProof{source,token}:HandCopyProof{};
}
inline bool hand_copy_complete(HandCopyProof& destination,HandCopyProof ticket,unsigned source,unsigned blob,bool complete){
    if(!complete || !destination.token || destination.source || destination.token!=ticket.token || !hand_copy_valid(ticket,source,blob))return false;
    destination=ticket;return true;
}
inline void hand_copy_invalidate(HandCopyProof& proof){proof={};}
}
#endif

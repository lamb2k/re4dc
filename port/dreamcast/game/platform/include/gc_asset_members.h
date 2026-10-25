#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
enum OwnerFamily : unsigned char { OtherOwner,PlayerOwner,WeaponOwner };
struct ModelMember {
    CheckedAsset asset;
    unsigned serial, arc, offset;
    char name[32];
    OwnerFamily family=OtherOwner;
};
// Diagnostic metadata only. Adopt before relocation/encoding, retire before
// source memory release or overwrite, even when the next owner reuses a pointer.
// Duplicate adoption of the same current view does not rehash relocated bytes.
bool member_adopt(const void* owner, void* archive, unsigned bytes, bool transient,OwnerFamily family=OtherOwner);
void member_retire(const void* owner);
void member_move(const void* owner,void* base);
void member_retire_transient();
// Called once before calcModelAddr changes source offsets. Never hashes a
// pointer until a live, bounded complete BIN member has been located.
bool member_capture(const void* data);
bool member_lookup(const void* data, ModelMember*);
// Memory-only full-span check against an already captured current generation.
bool member_contains(unsigned serial,const void* data,unsigned bytes);
// Accepted geometry latches only bounded metadata while SQ may be held.
// Flush at an unlocked frame/retirement boundary, never inside an emitter.
void member_accept(unsigned serial,unsigned consumer_mask);
void member_flush();
// Motion (bit 9): latch a played FCV/SEQ clip (source evaluator thread); flush emits.
void motion_use(const void* clip);
void motion_flush();
void motion_visit_reset();
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void member_test_serial(unsigned);
#endif
struct PayloadProof;
struct SourceUse { unsigned serial=0,mask=0;const void* model=nullptr;const void* info=nullptr;PayloadProof* payload=nullptr; };
extern SourceUse source_use;
struct ReplayUse {unsigned serial=0xffffffffU,mask=0;PayloadProof* payload=nullptr;};
extern ReplayUse replay_use;
struct ReplayScope {
    ReplayUse previous;
    ReplayScope(unsigned serial,unsigned mask,PayloadProof* payload=nullptr):previous(replay_use){replay_use={serial,mask,payload};}
    ~ReplayScope(){replay_use=previous;}
};
struct SourceScope {
    SourceUse previous;
    SourceScope():previous(source_use){source_use={};}
    ~SourceScope(){source_use=previous;}
};
}
#endif

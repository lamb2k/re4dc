#pragma once
#include "gc_asset_gate.h"
#include "gc_asset_actor_original.h"
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
void member_retire_transient();
// Called once before calcModelAddr changes source offsets. Never hashes a
// pointer until a live, bounded complete BIN member has been located.
bool member_capture(const void* data);
bool member_lookup(const void* data, ModelMember*);
// Memory-only full-span check against an already captured current generation.
bool member_contains(unsigned serial,const void* data,unsigned bytes);
// A full member is not sufficient: exact pre-relocation constituent metadata
// and a validated complete source part are required by every raw selection.
// Root frame owner supplies this fixed partition from an EXISTING owned slab
// before source loading. No heap or BSS backing is silently allocated here.
// It must exclude this partition from packet/loan/other writes until retire.
unsigned member_original_storage_bytes();
bool member_original_storage(void* memory,unsigned bytes);
void member_original_storage_retire();
bool member_original_source(unsigned serial,const OriginalModelInput&);
// Exact captured original color section only, with separately bounded actual
// replacement stream's maximum consumed color index. No whole-BIN inheritance.
bool member_original_colors(unsigned serial,const OriginalModelInput&,unsigned bytes);
bool member_serial_current(unsigned serial);
// Successful source skin/morph publication only. reset precedes every write
// attempt and info reuse; a failed/partial job publishes nothing.
void member_pose_reset(const void* info);
void member_shape_reset(const void* info,unsigned serial,unsigned frame);
void member_shape_source(const void* info,unsigned serial,unsigned frame,unsigned index,const void* delta,unsigned count);
bool member_pose_publish(const void* info,unsigned serial,const OriginalModelInput&,const void* positions,const void* normals,unsigned frame,bool lazy=false);
bool member_pose_current(const void* info,unsigned serial,const void* positions,const void* normals,unsigned frame);
// Recognized in-place native representation writes. Metadata only while SQ
// may be owned; failure permanently revokes this member generation.
unsigned member_derive_begin(const void* target,unsigned bytes);
void member_derive_end(unsigned ticket,bool completed);
struct MemberDerivationScope {
    unsigned ticket;bool completed=false;
    MemberDerivationScope(const void* target,unsigned bytes):ticket(member_derive_begin(target,bytes)){}
    void complete(){completed=true;}
    ~MemberDerivationScope(){if(ticket)member_derive_end(ticket,completed);}
};
// Accepted geometry latches only bounded metadata while SQ may be held.
// Flush at an unlocked frame/retirement boundary, never inside an emitter.
void member_accept(unsigned serial,unsigned consumer_mask);
void member_flush();
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void member_test_serial(unsigned);
#endif
struct PayloadProof;
struct SourceUse { unsigned serial=0,mask=0;const void* model=nullptr;const void* info=nullptr;PayloadProof* payload=nullptr; };
extern SourceUse source_use;
// This producer's real call-stack completion only. Root must first stop new
// admission and separately drain UI packets/windows/loaders/audio workers.
bool geometry_producer_enter();
void geometry_producer_leave(bool entered);
bool geometry_producers_idle();
struct GeometryProducerScope {
    bool entered=geometry_producer_enter();
    ~GeometryProducerScope(){geometry_producer_leave(entered);}
};
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

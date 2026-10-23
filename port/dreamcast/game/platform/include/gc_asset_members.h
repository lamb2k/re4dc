#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
struct ModelMember {
    Digest digest;
    unsigned serial, arc, offset;
    char name[32];
};
// Diagnostic metadata only. Adopt before relocation/encoding, retire before
// source memory release or overwrite, even when the next owner reuses a pointer.
// Duplicate adoption of the same current view does not rehash relocated bytes.
bool member_adopt(const void* owner, void* archive, unsigned bytes, bool transient);
void member_retire(const void* owner);
void member_retire_transient();
// Called once before calcModelAddr changes source offsets. Never hashes a
// pointer until a live, bounded complete BIN member has been located.
bool member_capture(const void* data);
bool member_lookup(const void* data, ModelMember*);
// Accepted geometry latches only bounded metadata while SQ may be held.
// Flush at an unlocked frame/retirement boundary, never inside an emitter.
void member_accept(unsigned serial,unsigned consumer_mask);
void member_flush();
struct SourceUse { unsigned serial=0,mask=0;const void* model=nullptr;const void* info=nullptr; };
extern SourceUse source_use;
struct SourceScope {
    SourceUse previous;
    SourceScope():previous(source_use){source_use={};}
    ~SourceScope(){source_use=previous;}
};
}
#endif

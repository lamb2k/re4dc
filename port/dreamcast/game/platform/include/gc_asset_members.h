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
}
#endif

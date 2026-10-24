#pragma once
#include "gc_asset_members.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// Embedded in a stable package-owner object, never in its freed file storage.
// The owner must prove complete immutable allocation bounds before capture and
// retire before overwrite/free. These records infer no origin from the API.
struct PayloadProof {
    const void* owner=nullptr;const void* base=nullptr;const void* layout=nullptr;
    unsigned bytes=0,layout_bytes=0;
    CheckedAsset asset{},layout_asset{};
    unsigned serial=0,uses=0;
    PayloadProof* next=nullptr;
    bool registered=false;
};
bool payload_capture(PayloadProof&,const void* owner,const void* base,unsigned bytes,const void* layout=nullptr,unsigned layout_bytes=0);
// Compiled source arrays have no contiguous file representation. Hash a
// versioned, length-framed sequence once at startup, outside submission/locks.
// Capture precedes first permitted in-place preparation. The caller owns the
// same backing spans for the proof's whole lifetime and must select it only
// after matching actual consumed arrays. Never rehash prepared/replaced bytes.
// No span table is retained.
struct PayloadSpan {const void* data;unsigned bytes;};
bool payload_capture_fragments(PayloadProof&,const void* owner,const PayloadSpan*,unsigned count);
void payload_retire(PayloadProof&);
void payload_accept(PayloadProof*,unsigned serial,unsigned consumer_mask);
void payload_flush_all();
// Borrowed, synchronous impostor batch. Only the exact committed vertex buffer
// and four vertices per saved quad may consume these original owner serials.
struct PayloadQuadUse { PayloadProof* proof;unsigned serial,mask; };
struct PayloadQuadBatch { const PayloadQuadUse* uses;unsigned count;const void* vertices;unsigned vertex_count; };
struct PayloadQuadScope {
    const PayloadQuadBatch* previous;
    explicit PayloadQuadScope(const PayloadQuadBatch&);
    ~PayloadQuadScope();
};
bool payload_quads_accept(const void* vertices,unsigned count);
struct PayloadScope {
    SourceUse previous;
    PayloadScope(PayloadProof&,const void* owner,const void* model=nullptr,const void* info=nullptr,unsigned mask=1U<<SourceGeometry);
    ~PayloadScope(){source_use=previous;}
};
}
#endif

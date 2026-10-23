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
void payload_retire(PayloadProof&);
void payload_accept(PayloadProof*,unsigned serial,unsigned consumer_mask);
void payload_flush_all();
struct PayloadScope {
    SourceUse previous;
    PayloadScope(PayloadProof&,const void* owner,const void* model=nullptr,const void* info=nullptr,unsigned mask=1U<<SourceGeometry);
    ~PayloadScope(){source_use=previous;}
};
}
#endif

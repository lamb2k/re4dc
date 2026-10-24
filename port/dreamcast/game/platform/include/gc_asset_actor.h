#pragma once
#include "gc_asset_payloads.h"
#if RE4DC_GC_ASSET_GATE
#ifndef RE4DC_GC_ASSET_LEON_HAND_PACK
#define RE4DC_GC_ASSET_LEON_HAND_PACK 0
#endif
struct Re4dcModelPart;
struct Re4dcActorSource;
extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_actor_select(const Re4dcModelPart*,const Re4dcActorSource*);
extern "C" void re4dc_gcasset_actor_startup();
#if RE4DC_GC_ASSET_LEON_HAND_PACK
extern "C" unsigned re4dc_gcasset_hand_derive_begin(const void*,unsigned);
extern "C" void re4dc_gcasset_hand_derive_end(unsigned,bool);
#endif
namespace re4dc_gcasset {
#if RE4DC_GC_ASSET_LEON_HAND_PACK
struct HandDerivationScope {
    unsigned ticket;bool completed=false;
    HandDerivationScope(const void* target,unsigned bytes):ticket(re4dc_gcasset_hand_derive_begin(target,bytes)){}
    void complete(){completed=true;}
    ~HandDerivationScope(){if(ticket)re4dc_gcasset_hand_derive_end(ticket,completed);}
};
#endif
// Memory-only selection/acknowledgement. A shared OneWindow may retain SQ
// ownership across chunks; neither this bridge nor selection may perform IO,
// hash, log, allocate or wait. Exact original identity is copied for this call.
struct ActorSourceScope {
    SourceUse previous,selected;
    ActorSourceScope(const Re4dcModelPart* part,const Re4dcActorSource* source)
        :previous(source_use),selected(re4dc_gcasset_actor_select(part,source)){source_use=selected;}
    ~ActorSourceScope(){source_use=previous;}
    void accepted(){payload_accept(selected.payload,selected.serial,selected.mask?selected.mask:1U<<SourceGeometry);}
};
}
#endif

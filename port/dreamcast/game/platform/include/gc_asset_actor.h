#pragma once
#include "gc_asset_payloads.h"
#if RE4DC_GC_ASSET_GATE
struct Re4dcModelPart;
struct Re4dcActorSource;
extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_actor_select(const Re4dcModelPart*,const Re4dcActorSource*);
extern "C" void re4dc_gcasset_actor_startup();
namespace re4dc_gcasset {
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

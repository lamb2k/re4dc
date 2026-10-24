#pragma once
#include "gc_asset_payloads.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// Cold, local serialization only. No component list survives publication.
enum StaticOwner : unsigned { StaticView=1,StaticMesh,StaticWorld,StaticShell,StaticIndex };
enum StaticRole : unsigned { R4PW=0,R4ID,R4TC,R4PV,R4SG,SCCN,SCPS,SCDD,SDO3_BASE80,R4TI_SELECTOR,STD_INDEX,PCL1_CELL,StaticRoleCount };
enum StaticState : unsigned { NotApplicable=0,Disabled,Absent,Rejected,Accepted,Unproven };
struct StaticManifest {
    unsigned char data[64+StaticRoleCount*52]{};
    unsigned seen=0,geometry_bytes=0;
    const void* geometry_base=nullptr;
};
static_assert(StaticRoleCount==12 && sizeof(StaticManifest)==(sizeof(void*)==4?700:704),"cold manifest caller budget");
bool static_manifest_begin(StaticManifest&,StaticOwner,unsigned room,unsigned profile,const void* geometry,unsigned geometry_bytes);
bool static_manifest_note(StaticManifest&,StaticRole,StaticState,unsigned bytes=0,unsigned version=0,unsigned flags=0,const Digest* digest=nullptr);
bool static_manifest_bytes(StaticManifest&,StaticRole,const void*,unsigned bytes,unsigned version=0,unsigned flags=0);
bool static_manifest_seal(const StaticManifest&,Digest&);
// All bytes/digests were captured before any controlled preparation. The full
// manifest must be sealed; physical bounds remain owned until retirement.
bool payload_capture_composite(PayloadProof&,const void* owner,const void* geometry,unsigned bytes,
    const void* layout,unsigned layout_bytes,const StaticManifest&);
// Memory-only, before an independent constituent is overwritten/freed. Prior
// accepted acknowledgements keep their old assets until an unlocked flush.
void payload_invalidate(PayloadProof&,const void* owner);
}
#endif

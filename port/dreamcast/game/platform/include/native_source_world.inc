// Read-only access to the already adopted r200 world. Package publication and
// retirement advance a token; a same-address reload never revives an old frame.
extern "C" int re4dc_ps2_source_package(unsigned* generation) {
    if(!generation || !sourceWorldPackageGeneration || sourceWorldPackageGeneration==~0U ||
       !ps2w.storage || !ps2w.parts || !ps2w.placements || !ps2w.lut || !ps2w.gather ||
       ps2w.room!=0x200 || ps2w.want!=0x200 || ps2w.nplacements!=90 ||
       sourceWorldSidecarCrc!=4040448078U || !dyn::ids || dyn::nids!=90)return 0;
    const auto& h=ps2w.package.header();
    if(h.version!=3 || h.bytes!=510048U || h.crc!=3459209119U || h.mesh_count!=63 || h.part_count!=152)return 0;
    *generation=sourceWorldPackageGeneration;return 1;
}
extern "C" int re4dc_ps2_source_texture(unsigned generation,Re4dcSourceWorldTexture* out) {
    unsigned current=0;
    if(!out || !re4dc_ps2_source_package(&current) || current!=generation)return 0;
    const auto& q=ps2w.parts[13];
    if(q.crc!=0xfa6fe38cU || q.fnv!=0x1a02365fU || q.width!=256 || q.height!=256 ||
       q.pass!=2 || q.texture!=17 || q.reserved)return 0;
    *out={current,q.crc,q.fnv,q.width,q.height,131072U};return 1;
}
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#include "source_world_r200_profile.h"
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
namespace {
unsigned sourceWorldNativeHash(const void* data,unsigned bytes){
    unsigned h=2166136261U;const auto* p=static_cast<const unsigned char*>(data);
    while(bytes--)h=(h^*p++)*16777619U;return h;
}
}
extern "C" int re4dc_ps2_source_group_package(unsigned* generation,int deep){
    namespace profile=source_world_r200_profile;
    constexpr unsigned mbytes=(profile::mesh_bytes+31U)&~31U,pbytes=(profile::side_bytes+31U)&~31U;
    constexpr unsigned bytes=mbytes+pbytes+kLutBytes+kGatherBytes;
    unsigned room=0,c,b,stale,refused;
    if(!generation || !sourceWorldPackageGeneration || sourceWorldPackageGeneration==~0U ||
       ps2w.room!=profile::room || ps2w.want!=profile::room || ps2w.bytes!=bytes ||
       ps2w.nplacements!=profile::placements || sourceWorldSidecarCrc!=profile::side_crc ||
       !re4dc_room4_state(&room,&c,&b,&stale,&refused) ||
       !re4dc_source_world_native_cell(ps2w.storage,bytes,room) ||
       !re4dc_source_world_native_cell(dyn::block,128,room))return 0;
    // No borrowed package/header/ids read occurs before current heap ownership.
    const auto* storage=ps2w.storage;const auto& header=ps2w.package.header();
    if(header.version!=3 || header.bytes!=profile::mesh_bytes || header.crc!=profile::mesh_crc ||
       header.mesh_count!=profile::meshes || header.part_count!=profile::parts ||
       header.mesh_offset!=128 || header.part_offset!=4416 ||
       reinterpret_cast<const void*>(ps2w.package.meshes())!=storage+128 ||
       reinterpret_cast<const void*>(ps2w.package.parts())!=storage+4416 ||
       reinterpret_cast<const void*>(ps2w.parts)!=storage+mbytes+sizeof(Ps2Head) ||
       reinterpret_cast<const void*>(ps2w.placements)!=storage+mbytes+sizeof(Ps2Head)+profile::parts*sizeof(Ps2Part) ||
       reinterpret_cast<const void*>(ps2w.lut)!=storage+mbytes+pbytes ||
       reinterpret_cast<const void*>(ps2w.gather)!=storage+mbytes+pbytes+kLutBytes ||
       dyn::nids!=profile::placements || dyn::ids!=dyn::block+sizeof(dyn::Head))return 0;
    if(deep && (sourceWorldNativeHash(storage,sizeof(re4dc::room::MeshHeader))!=0x52ae0d3U ||
       sourceWorldNativeHash(&header,sizeof(header))!=0x52ae0d3U ||
       sourceWorldNativeHash(ps2w.package.meshes(),profile::meshes*sizeof(re4dc::room::MeshRecord))!=0x9e2658b1U ||
       sourceWorldNativeHash(ps2w.package.parts(),profile::parts*sizeof(re4dc::room::MeshPart))!=0xea1e94a6U ||
       sourceWorldNativeHash(storage+mbytes,profile::side_bytes)!=0x590ce75bU ||
       sourceWorldNativeHash(dyn::block,128)!=0x4251c1d6U))return 0;
    *generation=sourceWorldPackageGeneration;return 1;
}
#if RE4DC_TRANSITION_GATE_DIAG
extern "C" void re4dc_ps2_source_group_package_diag(){
    namespace profile=source_world_r200_profile;
    constexpr unsigned mbytes=(profile::mesh_bytes+31U)&~31U,pbytes=(profile::side_bytes+31U)&~31U;
    constexpr unsigned bytes=mbytes+pbytes+kLutBytes+kGatherBytes;
    unsigned room=0,c,b,stale,refused;const int rs=re4dc_room4_state(&room,&c,&b,&stale,&refused);
    re4dc_log("TGD package gen=%u room=%03x want=%03x bytes=%u/%u nplacements=%u/%u side_crc=%08x/%08x room4=%d cell=%d dyncell=%d nids=%u\n",
        sourceWorldPackageGeneration,ps2w.room,ps2w.want,ps2w.bytes,bytes,ps2w.nplacements,profile::placements,
        sourceWorldSidecarCrc,profile::side_crc,rs,rs?re4dc_source_world_native_cell(ps2w.storage,bytes,room):-1,
        rs?re4dc_source_world_native_cell(dyn::block,128,room):-1,dyn::nids);
    if(!ps2w.storage)return;
    const auto& h=ps2w.package.header();
    re4dc_log("TGD package header version=%u bytes=%u/%u crc=%08x/%08x meshes=%u/%u parts=%u/%u mesh_off=%u part_off=%u\n",
        h.version,h.bytes,profile::mesh_bytes,h.crc,profile::mesh_crc,h.mesh_count,profile::meshes,h.part_count,profile::parts,
        h.mesh_offset,h.part_offset);
    re4dc_log("TGD package hashes mh=%08x hdr=%08x meshes=%08x parts=%08x side=%08x dyn=%08x (pins 052ae0d3 052ae0d3 9e2658b1 ea1e94a6 590ce75b 4251c1d6)\n",
        sourceWorldNativeHash(ps2w.storage,sizeof(re4dc::room::MeshHeader)),sourceWorldNativeHash(&h,sizeof(h)),
        h.mesh_count==profile::meshes?sourceWorldNativeHash(ps2w.package.meshes(),profile::meshes*sizeof(re4dc::room::MeshRecord)):0U,
        h.part_count==profile::parts?sourceWorldNativeHash(ps2w.package.parts(),profile::parts*sizeof(re4dc::room::MeshPart)):0U,
        ps2w.bytes>=mbytes+profile::side_bytes?sourceWorldNativeHash(ps2w.storage+mbytes,profile::side_bytes):0U,
        dyn::block?sourceWorldNativeHash(dyn::block,128):0U);
}
#endif
#endif

namespace {
unsigned sourceWorldImageFrame=~0U,sourceWorldImageGeneration;
int sourceWorldImageResult;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
struct SourceWorldPassReceipt {
    unsigned native=0,generation=0,attempted=0,completed=0,inflight=0;
    int result[3]{};
    bool active=false,bad=false;
} sourceWorldPassReceipt;
unsigned sourceWorldLegacyFrame;bool sourceWorldLegacySeen;
bool sourceWorldReceiptCurrent() {
    const auto& receipt=sourceWorldPassReceipt;unsigned generation=0;
    return receipt.active && receipt.native==re4dc_ui_frame() &&
        re4dc_source_world_binding_valid() && re4dc_ps2_source_group_package(&generation,1) && generation==receipt.generation;
}
#endif
}
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
extern "C" int re4dc_ps2_source_legacy_clean(unsigned native){return !sourceWorldLegacySeen || sourceWorldLegacyFrame!=native;}
extern "C" void re4dc_ps2_source_legacy_started(unsigned native) {
    sourceWorldLegacySeen=true;sourceWorldLegacyFrame=native;
    if(sourceWorldPassReceipt.active && sourceWorldPassReceipt.native==native)sourceWorldPassReceipt.bad=true;
}
extern "C" void re4dc_ps2_source_pass_begin(unsigned pass) {
    auto& receipt=sourceWorldPassReceipt;
    if(!receipt.active)return;
    if(pass>2 || !sourceWorldReceiptCurrent() || receipt.inflight || (receipt.attempted&(1U<<pass))){receipt.bad=true;return;}
    receipt.attempted|=1U<<pass;receipt.inflight=1U<<pass;
}
extern "C" void re4dc_ps2_source_pass_result(unsigned pass,int result) {
    auto& receipt=sourceWorldPassReceipt;
    if(!receipt.active)return;
    if(pass>2 || !sourceWorldReceiptCurrent() || receipt.inflight!=(1U<<pass)){receipt.bad=true;return;}
    receipt.inflight=0;receipt.result[pass]=result;
    const auto& count=ps2w.count[pass];
    if(result==1 && !count.fallback && !count.aborts)receipt.completed|=1U<<pass;
    else receipt.bad=true;
}
extern "C" int re4dc_ps2_source_receipt_complete(unsigned native,unsigned generation) {
    const auto& receipt=sourceWorldPassReceipt;
    if(!sourceWorldReceiptCurrent() || receipt.native!=native || receipt.generation!=generation ||
       receipt.bad || receipt.inflight || receipt.attempted!=7 || receipt.completed!=7)return 0;
    for(unsigned pass=0;pass<3;++pass)
        if(receipt.result[pass]!=1 || ps2w.count[pass].fallback || ps2w.count[pass].aborts)return 0;
    return 1;
}
#endif
extern "C" int re4dc_ps2_source_draw(unsigned generation) {
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    const re4dc::wc24::Scope wc_world(re4dc::wc24::NearOP,re4dc::wc24::Other);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorSourceDraw,re4dc::wc24::ErrorOwnerRejected,generation);
#endif
#endif
    unsigned current=0;const unsigned frame=re4dc_ui_frame();
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(re4dc_source_world_group_claimed() && !re4dc_source_world_binding_valid()){
        wc_result.why.first(re4dc::wc24::ErrorBindingLost,generation,frame);
        re4dc_source_world_binding_failed();return -1;
    }
#else
    if(re4dc_source_world_group_claimed() && !re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return -1;}
#endif
#endif
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc_ps2_source_package(&current)){wc_result.why.first(re4dc::wc24::ErrorPackageUnavailable,generation,current);return 0;}
    if(current!=generation){wc_result.why.first(re4dc::wc24::ErrorOwnerRejected,generation,current);return 0;}
#else
    if(!re4dc_ps2_source_package(&current) || current!=generation)return 0;
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=sourceWorldImageFrame==frame && sourceWorldImageGeneration==generation && sourceWorldImageResult>0;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(sourceWorldImageFrame==frame && !wc_result.complete)
        wc_result.why.first(sourceWorldImageGeneration!=generation?re4dc::wc24::ErrorOwnerRejected:re4dc::wc24::ErrorReceiptIncomplete,
            sourceWorldImageGeneration,uint32_t(sourceWorldImageResult));
#endif
#endif
    if(sourceWorldImageFrame==frame)return sourceWorldImageGeneration==generation?sourceWorldImageResult:0;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    const bool transition=re4dc_source_world_transition_owner(frame,generation)!=0;
    if(transition && sourceWorldLegacySeen && sourceWorldLegacyFrame==frame)return 0;
#endif
    float view[12],projection[7],viewport[6];
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc_coarse_source_camera(view,projection,viewport)){
        wc_result.why.first(re4dc::wc24::ErrorCameraUnavailable,frame,generation);return 0;
    }
#else
    if(!re4dc_coarse_source_camera(view,projection,viewport))return 0;
#endif
    sourceWorldImageFrame=frame;sourceWorldImageGeneration=generation;
    re4dc_ps2_mesh_camera(view,projection,viewport);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    sourceWorldPassReceipt={};
    if(transition){
        sourceWorldPassReceipt.native=frame;sourceWorldPassReceipt.generation=generation;
        sourceWorldPassReceipt.active=true;
    }
#endif
    const int drawn=re4dc_ps2_world_source_draw();
    const auto& c=ps2w.count[0];
    // A partial draw cannot fall back to GC geometry. Fail the scene explicitly.
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    sourceWorldImageResult=(transition?drawn==1:drawn!=0) && !c.fallback && !c.aborts?1:-1;
    if(transition && (sourceWorldPassReceipt.bad || sourceWorldPassReceipt.completed!=1))sourceWorldImageResult=-1;
#else
    sourceWorldImageResult=drawn && !c.fallback && !c.aborts?1:-1;
#endif
    if(sourceWorldImageResult<0)re4dc_model_packet_abort();
    re4dc_log("PS2SOURCE_DRAW f=%u gen=%u result=%d native=%u fallback=%u abort=%u\n",
        frame,generation,sourceWorldImageResult,c.native,c.fallback,c.aborts);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=sourceWorldImageResult>0;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!wc_result.complete)wc_result.why.first(re4dc::wc24::ErrorReceiptIncomplete,uint32_t(sourceWorldImageResult),
        (c.fallback?1U:0U)|(c.aborts?2U:0U));
#endif
#endif
    return sourceWorldImageResult;
}
extern "C" int re4dc_ps2_source_passes_complete() {
    for(const auto& count:ps2w.count)if(count.fallback || count.aborts)return 0;
    return 1;
}

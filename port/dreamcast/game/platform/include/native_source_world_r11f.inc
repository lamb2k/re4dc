// Native half of the r11f transaction. Package publication and each actual pass
// own explicit receipts; untouched zero counters cannot certify an omitted pass.
#include "source_world_r11f_profile.h"
namespace {
namespace r11fnp=source_world_r11f_profile;
unsigned r11fNativeFnv(const void* data,unsigned bytes) {
    unsigned h=2166136261U;const auto* p=static_cast<const unsigned char*>(data);
    while(bytes--)h=(h^*p++)*16777619U;return h;
}
struct R11fNativeReceipt {
    unsigned native=~0U,generation=0,source=0,attempted=0,completed=0;
    unsigned packet_before[3]{},packet_after[3]{},fallback[3]{},aborts[3]{};
    int result[3]{};float uv[2]{};
    bool planned=false,uv_valid=false,failed=false;
} r11fNativeReceipt;
unsigned r11fLegacyFrame=~0U;
int ps2_pass(unsigned pass,float zfar);
extern "C" int re4dc_coarse_source_camera(float*,float*,float*);
extern "C" void re4dc_ps2_mesh_camera(const float*,const float*,const float*);
extern "C" int re4dc_ps2_world_source_draw();
bool r11fNativeClaimed() {
    const auto& r=r11fNativeReceipt;
    return r.planned || r.attempted || r.failed;
}
int r11fNativePass(unsigned pass,float zfar) {
    auto& r=r11fNativeReceipt;
    if(pass>2 || r.failed || !r.planned || !r.uv_valid || r.native!=re4dc_ui_frame()) {
        re4dc_r11f_pass_failed(re4dc_ui_frame());return 0;
    }
    const unsigned bit=1U<<pass;
    if(r.attempted&bit) {
        if(!re4dc_r11f_current(r.native,r.generation,1)){re4dc_r11f_pass_failed(r.native);return 0;}
        return (r.completed&bit)?r.result[pass]:0;
    }
    // OP -> PT -> TR, including an empty/cull-only actual pass. All must have
    // returned numeric1. A blocked movie's old synthetic success cannot enter.
    if(r.completed!=bit-1U || !ps2w.camera || !re4dc_r11f_current(r.native,r.generation,1)) {
        re4dc_r11f_pass_failed(r.native);return 0;
    }
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie.unavailable() || !ps2_movie_current()){re4dc_r11f_pass_failed(r.native);return 0;}
    MovieWorldRead read;
#endif
    r.attempted|=bit;r.packet_before[pass]=re4dc_r11f_packet_bytes();
    const int result=ps2_pass(pass,zfar);
    r.result[pass]=result;r.fallback[pass]=ps2w.count[pass].fallback;r.aborts[pass]=ps2w.count[pass].aborts;
    r.packet_after[pass]=re4dc_r11f_packet_bytes();
    const bool complete=result==1 && !r.fallback[pass] && !r.aborts[pass] &&
        r.packet_after[pass]>=r.packet_before[pass] && re4dc_r11f_current(r.native,r.generation,1);
    if(complete)r.completed|=bit;
    else {r.failed=true;re4dc_r11f_pass_failed(r.native);}
    re4dc_log("R11FOWNER_PASS f=%u gen=%u pass=%u result=%d attempted=%x complete=%x packets=%u/%u fallback=%u abort=%u\n",
        r.native,r.generation,pass,result,r.attempted,r.completed,r.packet_before[pass],r.packet_after[pass],r.fallback[pass],r.aborts[pass]);
    return complete?1:0;
}
struct R11fUvScope {
    Re4dcModelPart& part;
    R11fUvScope(Re4dcModelPart& p,unsigned placement,unsigned mesh,unsigned index,unsigned pass):part(p) {
        part.uv_offset[0]=part.uv_offset[1]=0.f;
        const auto& r=r11fNativeReceipt;
        if(!pass && placement==0 && mesh==0 && index==0 && r.native==re4dc_ui_frame() &&
           r.planned && r.uv_valid && !r.failed && r.generation==r11fPackageGeneration) {
            part.uv_offset[0]=r.uv[0];part.uv_offset[1]=r.uv[1];
        }
    }
    ~R11fUvScope(){part.uv_offset[0]=part.uv_offset[1]=0.f;}
};
void r11fLegacyStamp(unsigned native) { r11fLegacyFrame=native; }
}
extern "C" int re4dc_r11f_package(unsigned* generation,int deep) {
    if(!generation || !r11fPackageGeneration || r11fPackageGeneration==~0U ||
       ps2w.room!=r11fnp::room || ps2w.want!=r11fnp::room || !ps2w.storage ||
       ps2w.bytes!=r11fnp::cell_bytes || ps2w.nplacements!=r11fnp::placements ||
       r11fSidecarCrc!=r11fnp::side_crc)return 0;
    // Prove the primary allocation BEFORE reading any package header or part.
    unsigned room=0;
    if(!re4dc_room4_live_generation(&room) ||
       !re4dc_room4_cell_valid(ps2w.storage,r11fnp::cell_bytes,room))return 0;
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie.phase!=movie_world::Phase::ready || !ps2_movie_current())return 0;
#endif
    const auto* s=ps2w.storage;const auto& h=ps2w.package.header();
    if(h.version!=3 || h.bytes!=r11fnp::mesh_bytes || h.crc!=r11fnp::mesh_crc ||
       h.mesh_count!=r11fnp::meshes || h.part_count!=r11fnp::parts ||
       h.mesh_offset!=128 || h.part_offset!=6592 ||
       reinterpret_cast<const void*>(ps2w.package.meshes())!=s+128 ||
       reinterpret_cast<const void*>(ps2w.package.parts())!=s+6592 ||
       reinterpret_cast<const void*>(ps2w.parts)!=s+r11fnp::mesh_bytes+sizeof(Ps2Head) ||
       reinterpret_cast<const void*>(ps2w.placements)!=s+r11fnp::mesh_bytes+sizeof(Ps2Head)+r11fnp::parts*sizeof(Ps2Part) ||
       reinterpret_cast<const void*>(ps2w.lut)!=s+r11fnp::mesh_bytes+((r11fnp::side_bytes+31U)&~31U) ||
       reinterpret_cast<const void*>(ps2w.gather)!=s+r11fnp::mesh_bytes+((r11fnp::side_bytes+31U)&~31U)+kLutBytes ||
       !dyn::block || dyn::nids!=r11fnp::placements ||
       !re4dc_room4_cell_valid(dyn::block,160,room) || dyn::ids!=dyn::block+sizeof(dyn::Head))return 0;
    if(deep) {
        if(r11fNativeFnv(s,sizeof(re4dc::room::MeshHeader))!=0x6ef77d6bU ||
           r11fNativeFnv(&h,sizeof(h))!=0x6ef77d6bU ||
           r11fNativeFnv(ps2w.package.meshes(),r11fnp::meshes*sizeof(re4dc::room::MeshRecord))!=0xec509cf6U ||
           r11fNativeFnv(ps2w.package.parts(),r11fnp::parts*sizeof(re4dc::room::MeshPart))!=0x9ac86df2U ||
           r11fNativeFnv(s+r11fnp::mesh_bytes,r11fnp::side_bytes)!=0x8c6e281dU ||
           r11fNativeFnv(dyn::block,160)!=0xb1700dc0U)return 0;
        const auto& pl=ps2w.placements[0];const auto& mesh=ps2w.package.meshes()[0];const auto& part=ps2w.parts[0];
        if(pl.mesh || pl.placement || mesh.first_part || mesh.part_count!=1 || dyn::ids[0] ||
           part.crc!=0xf417e94dU || part.fnv!=0x46e00253U || part.width!=256 || part.height!=128 ||
           part.pass || part.cull!=2 || part.texture!=17 || part.reserved)return 0;
        for(unsigned i=1;i<r11fnp::placements;++i)if(ps2w.placements[i].mesh==0 || dyn::ids[i]==0)return 0;
        for(unsigned i=1;i<r11fnp::parts;++i)
            if(ps2w.parts[i].crc==part.crc && ps2w.parts[i].fnv==part.fnv)return 0;
    }
    *generation=r11fPackageGeneration;return 1;
}
extern "C" int re4dc_r11f_binding_valid() {
    if(!r11fNativeClaimed())return 1;
    const auto& r=r11fNativeReceipt;
    return !r.failed && r.planned && r.uv_valid &&
        re4dc_r11f_check_current(r.native,r.generation,1);
}
extern "C" void re4dc_r11f_binding_failed() {
    if(!r11fNativeClaimed())return;
    auto& r=r11fNativeReceipt;r.failed=true;re4dc_r11f_pass_failed(r.native);
}
extern "C" int re4dc_r11f_native_plan(unsigned native,unsigned generation) {
    unsigned current=0;
    if(r11fLegacyFrame==native || !re4dc_r11f_package(&current,1) || current!=generation)return 0;
    r11fNativeReceipt={};auto& r=r11fNativeReceipt;
    r.native=native;r.generation=generation;r.planned=true;return 1;
}
extern "C" void re4dc_r11f_native_frame(unsigned native) {
    r11fNativeReceipt={};r11fNativeReceipt.native=native;
}
extern "C" void re4dc_r11f_native_cancel(int failed) {
    auto& r=r11fNativeReceipt;
    r.planned=false;r.uv_valid=false;r.uv[0]=r.uv[1]=0.f;
    if(failed || r.attempted)r.failed=true;
}
extern "C" int re4dc_r11f_native_draw(unsigned generation,unsigned source,const float* uv) {
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    const re4dc::wc24::Scope wc_world(re4dc::wc24::NearOP,re4dc::wc24::Other);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorR11fDraw,re4dc::wc24::ErrorOwnerRejected,generation,source);
#endif
#endif
    auto& r=r11fNativeReceipt;unsigned current=0;
    if(!uv || r.native!=re4dc_ui_frame() || !r.planned || r.failed || r.attempted ||
       r.generation!=generation || !re4dc_r11f_package(&current,1) || current!=generation ||
       !re4dc::render::is_finite(uv[0]) || !re4dc::render::is_finite(uv[1]) || !re4dc_r11f_op_window())return 0;
    float view[12],projection[7],viewport[6];
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc_coarse_source_camera(view,projection,viewport)){
        wc_result.why.first(re4dc::wc24::ErrorCameraUnavailable,r.native,generation);return 0;
    }
#else
    if(!re4dc_coarse_source_camera(view,projection,viewport))return 0;
#endif
    r.source=source;r.uv[0]=uv[0];r.uv[1]=uv[1];r.uv_valid=true;
    re4dc_ps2_mesh_camera(view,projection,viewport);
    (void)re4dc_ps2_world_source_draw();
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=!r.failed && (r.attempted&1U) && (r.completed&1U) && r.result[0]==1;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!wc_result.complete)wc_result.why.first(re4dc::wc24::ErrorReceiptIncomplete,uint32_t(r.result[0]),
        r.attempted|(r.completed<<8)|(unsigned(r.failed)<<16));
#endif
#endif
    return !r.failed && (r.attempted&1U) && (r.completed&1U) && r.result[0]==1;
}
extern "C" int re4dc_r11f_native_complete(unsigned native,unsigned generation,unsigned source) {
    const auto& r=r11fNativeReceipt;unsigned current=0;
    if(r.native!=native || r.generation!=generation || r.source!=source || !r.planned ||
       !r.uv_valid || r.failed || r.attempted!=7 || r.completed!=7 ||
       !re4dc_r11f_package(&current,1) || current!=generation)return 0;
    for(unsigned p=0;p<3;++p)if(r.result[p]!=1 || r.fallback[p] || r.aborts[p])return 0;
    return 1;
}

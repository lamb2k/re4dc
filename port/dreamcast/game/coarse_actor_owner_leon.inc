// Appended to coarse_actor.cpp. No copied private mesh arrays.
#if RE4DC_ACTOR_TRANSACTION
#include "coarse_actor_transaction.h"
#include "actor_material_owner.h"
#include "actor_lifetime.h"
#include "actor_material_policy.h"
#if RE4DC_PS2_LEON
// ps2leon.mk PS2_LEON: the arm's hair as one owned run per hair material it uses (A: 1, B: 2; tools/d367/ps2leon
// pack_arm.py, restripified as CHARBAKE_HAIR's runs), the leon_hair_runs.h API; its palette_count is chunk 7's.
#include "ps2leon_hair_runs.h"
#define RE4DC_LEON_HAIR_PALETTES leon_hair_runs::palette_count
#elif RE4DC_CHARBAKE_HAIR
#include "leon_hair_runs_g2.h" // charbake.mk CHARBAKE_HAIR: the same hair, one run per material (cb_hair.py)
#else
#include "leon_hair_runs.h"
#endif
#ifndef RE4DC_LEON_HAIR_PALETTES
#define RE4DC_LEON_HAIR_PALETTES 229
#endif
#include "warp_late.h"
#if !RE4DC_COARSE_SOURCE_ACTORS || !RE4DC_COARSE_ONE_SUBMIT || RE4DC_COARSE_SKIN_FTRV != 1 || !RE4DC_NATIVE_ACTOR_FAST
#error ACTOR_TRANSACTION requires the source ledger, ONE_SUBMIT and SKIN_FTRV=1 native path
#endif
#if RE4DC_ACTOR_SWAP || RE4DC_FRONT_NATIVE >= 2
#error ACTOR_TRANSACTION is incompatible with duplicate-draw/replay adapters
#endif
namespace {
unsigned owner_binding_revision;
cModel* owner_root_parts;
#if RE4DC_CHARBAKE_TOGGLE
// charbake.mk CHARBAKE_TOGGLE (test builds): the hair colour images take the selected variant's identity and key
// (coarse_actor.cpp re4dc_charbake_set); the materials draw the pair keys the runtime derives from those
// (native_ui.cpp model_mask_key; charbake_variants.h). Variant 0 holds the keys below the #else.
unsigned hair_tokens[re4dc_charbake::kCount][2],hair_mask_token;
Re4dcUiImage hair_colours[2]={{&hair_tokens[RE4DC_CHARBAKE_VARIANT%re4dc_charbake::kCount][0],nullptr,64,128,14,0xffffffffu,0},
                              {&hair_tokens[RE4DC_CHARBAKE_VARIANT%re4dc_charbake::kCount][1],nullptr,64,128,14,0xffffffffu,0}};
const Re4dcUiImage hair_mask{&hair_mask_token,nullptr,64,128,0,0xffffffffu,0};
unsigned hair_colour_crc[2]={kCharbakeBoot.hair_colour_crc[0],kCharbakeBoot.hair_colour_crc[1]},
         hair_colour_fnv[2]={kCharbakeBoot.hair_colour_fnv[0],kCharbakeBoot.hair_colour_fnv[1]};
unsigned hair_pair_crc[2]={kCharbakeBoot.hair_pair_crc[0],kCharbakeBoot.hair_pair_crc[1]},
         hair_pair_fnv[2]={kCharbakeBoot.hair_pair_fnv[0],kCharbakeBoot.hair_pair_fnv[1]};
#else
unsigned hair_tokens[3];
const Re4dcUiImage hair_colours[2]={{&hair_tokens[0],nullptr,64,128,14,0xffffffffu,0},{&hair_tokens[1],nullptr,64,128,14,0xffffffffu,0}};
const Re4dcUiImage hair_mask{&hair_tokens[2],nullptr,64,128,0,0xffffffffu,0};
constexpr unsigned hair_colour_crc[2]={0xac381b1a,0x7a9de1fd},hair_colour_fnv[2]={0x3ade84b1,0x0e415f15};
constexpr unsigned hair_pair_crc[2]={0xfc24a99c,0x9cf7f055},hair_pair_fnv[2]={0x03d13534,0xd40aae38};
#endif
bool owner_leon_bind(cModel* m) {
    if(!m || m->id || m->nParts!=119 || !m->pList || !m->pParts || (m->be_flag&0x4000))return false;
    // Current dual archive/model adoption records supply exact role identity,
    // including hidden infos. No signature scan or pointer-only positive cache.
    if(!re4dc_actor_role_bindings(m,0x100,infos,8) || !re4dc_actor::exact_infos(m->pModelInfo,infos,8))return false;
    const unsigned revision=re4dc_actor_binding_revision(m);if(!revision)return false;
    if(owner!=m || owner_serial!=m->serial || owner_parts!=m->pList || owner_root_parts!=m->pParts || owner_binding_revision!=revision) {
        cParts* part=m->pList;
        for(unsigned i=0;i<119;++i) {
            if(!part)return false;parts[i]=part;
            for(unsigned j=0;j<12;++j)if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) ||
                __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f)return false;
            part=part->pList;
        }
        if(part)return false;
        owner=m;owner_serial=m->serial;owner_parts=m->pList;owner_root_parts=m->pParts;owner_binding_revision=revision;
    }
    for(unsigned i=0;i<119;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&parts[i]->lt_inv_mat[0][0])[j]) ||
           !coarse_finite((&parts[i]->mat[0][0])[j]))return false;
    return true;
}
#if RE4DC_ACTOR_TRANSACTION_DIAG
// WP2 census (diagnostic): the first owner_leon_bind clause that fails, in its order; detail = part index etc.
unsigned owner_leon_bind_why(cModel* m,unsigned* detail) {
    *detail=0;
    if(!m)return 1;
    if(m->id)return 2;
    if(m->nParts!=119){*detail=m->nParts;return 3;}
    if(!m->pList)return 4;
    if(!m->pParts)return 5;
    if(m->be_flag&0x4000)return 6;
    cModelInfo* roles[8]{};
    if(!re4dc_actor_role_bindings(m,0x100,roles,8))return 7;
    if(!re4dc_actor::exact_infos(m->pModelInfo,roles,8)){
        for(cModelInfo* f=m->pModelInfo;f && *detail<999;f=f->pList)++*detail;
        return 8;
    }
    if(!re4dc_actor_binding_revision(m))return 9;
    cParts* part=m->pList;
    for(unsigned i=0;i<119;++i) {
        if(!part){*detail=i;return 10;}
        for(unsigned j=0;j<12;++j)if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) ||
            __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f){*detail=i*16+j;return 11;}
        part=part->pList;
    }
    if(part)return 12;
    part=m->pList;
    for(unsigned i=0;i<119;++i,part=part->pList)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) || !coarse_finite((&part->mat[0][0])[j])){*detail=i;return 13;}
    return 0;
}
#endif
int owner_leon_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
    if(!owner_leon_bind(m) || !skin_init())return 0;
    for(unsigned i=0;i<8;++i)if(p.info[i]!=infos[i] || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    for(unsigned u=0;u<skin_used;++u) {
        const unsigned b=skin_bone[u];
        skin_jobs[u]={&parts[b]->mat[0][0],&parts[b]->lt_inv_mat[0][0],bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    for(unsigned i=0;i<8;++i) {
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],leon4k::chunks[i].palette_count);
        for(unsigned j=0;j<leon4k::chunks[i].palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
    }
    return 1;
}
}
extern "C" int re4dc_actor_plan_leon(cModel* m,Re4dcActorPlan* out) {
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    if(RE4DC_WARP_LATE(RE4DC_LATE_LEON_SOURCE))return 0; // test-only old-path arm (warp_late.h 0x10)
#endif
    if(!m || !out || m->id || m->ot_type!=7 || !owner_leon_bind(m))return 0;
    Re4dcActorPlan p{};p.count=8;p.appearance=0x100;p.image=image;p.crc=crc;p.fnv=fnv;p.palettes=owner_leon_palettes;
#define RE4DC_LEON_OWNER(role,prefix) re4dc_actor::plan_chunk(p,role,infos[role],leon4k::chunks[role],RE4DC_OWNER_INPUT(leon4k,prefix,leon4k::chunks[role],119))
    RE4DC_LEON_OWNER(0,i0);RE4DC_LEON_OWNER(1,i1);RE4DC_LEON_OWNER(2,i2);RE4DC_LEON_OWNER(3,i3);
    RE4DC_LEON_OWNER(4,i4);RE4DC_LEON_OWNER(5,i5);RE4DC_LEON_OWNER(6,i6);RE4DC_LEON_OWNER(7,i7);
#undef RE4DC_LEON_OWNER
#if RE4DC_PS2_LEON
    // The arm's palette / workspace bytes (ps2leon_runtime.h, from its chunks' palette counts).
    if(p.palette_bytes!=leon4k::plan_palette_bytes || p.workspace_bytes!=leon4k::plan_workspace_bytes)return 0;
#else
    if(p.palette_bytes!=32000 || p.workspace_bytes!=26112)return 0;
#endif
    p.material_count=3;
    p.materials[0].image=image;p.materials[0].crc=crc;p.materials[0].fnv=fnv;
    for(unsigned i=0;i<2;++i) {
        auto& mat=p.materials[i+1];mat.image=hair_colours[i];mat.mask=hair_mask;
        mat.crc=hair_pair_crc[i];mat.fnv=hair_pair_fnv[i];
        // Source attr04: alpha>0, SRC_ALPHA/INV_SRC_ALPHA, LEQUAL/write,
        // same-UV I4 mask, repeat/bilinear. Routing is not shader acceptance.
        mat.material_flags=4;mat.blend=0;mat.depth_mode=RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u;
        mat.mask_ref=0;mat.mask_same_uv=1;mat.wrap_s=mat.wrap_t=1;
        // The default-off native-look policy disables hair depth writes. This
        // prevents transparent texels writing depth and intentionally differs
        // from GC depthwrite+alpha-test. Exact-source policy stays unadmitted.
    }
    for(unsigned i=0;i<8;++i)p.immutable_asset_id[i]=i+1;
    for(unsigned i=0;i<7;++i) {
        const auto& c=p.input[i];auto& r=p.runs[p.run_count++];
        r.role=i;r.immutable_asset_id=i+1;r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
    }
    for(const auto& run:leon_hair_runs::runs) {
        auto& r=p.runs[p.run_count++];r.role=7;r.material=run.material;r.immutable_asset_id=run.asset_id;r.triangles=run.triangles;
        r.uv={leon_hair_runs::uv,sizeof(leon_hair_runs::uv)};r.stream={run.stream,run.bytes};
    }
    if((re4dc_actor_material_runs_capability(&p)&3u)!=3u)return 0;
    *out=p;return 1;
}
extern "C" int re4dc_actor_hair_texture_key(const Re4dcUiImage* i,unsigned* c,unsigned* f) {
    if(!i || !c || !f || i->palette || i->palette_bytes || i->palette_format!=0xffffffffu || i->width!=64 || i->height!=128)return 0;
    for(unsigned k=0;k<2;++k)if(i->pixels==hair_colours[k].pixels && i->format==14){*c=hair_colour_crc[k];*f=hair_colour_fnv[k];return 1;}
    if(i->pixels==hair_mask.pixels && i->format==0){*c=0x94e9dc56;*f=0x070dc44a;return 1;}
    return 0;
}
extern "C" unsigned re4dc_actor_material_runs_capability(const Re4dcActorPlan* p) {
    // The hair runs of the included header: 14 (leon_hair_runs.h), 2 with CHARBAKE_HAIR (leon_hair_runs_g2.h), the
    // arm's with PS2_LEON (ps2leon_hair_runs.h: 1 for A, 2 for B).
    constexpr unsigned kHair=leon_hair_runs::run_count;
#if RE4DC_ACTOR_PL08
    // pl08 (0x108): nine roles; the same hair (role 7, pl00's runs 7..20) and one role-8 run last, its whole chunk.
    const bool pl08=p && p->appearance==0x108;
    if(!p || (pl08?(p->count!=9 || p->run_count!=8+kHair || p->runs[7+kHair].role!=8 || p->runs[7+kHair].material ||
                    p->runs[7+kHair].triangles!=p->input[8].triangles || p->runs[7+kHair].stream.data!=p->input[8].stream.data):
                   (p->appearance!=0x100 || p->count!=8 || p->run_count!=7+kHair)) || p->material_count!=3 ||
       p->input[7].palette_count!=RE4DC_LEON_HAIR_PALETTES || p->immutable_asset_id[7]!=8 || !p->info[7] || !(p->info[7]->be_flag&0x40))return 0;
#else
    if(!p || p->appearance!=0x100 || p->count!=8 || p->material_count!=3 || p->run_count!=7+kHair ||
       p->input[7].palette_count!=RE4DC_LEON_HAIR_PALETTES || p->immutable_asset_id[7]!=8 || !p->info[7] || !(p->info[7]->be_flag&0x40))return 0;
#endif
    for(unsigned k=0;k<kHair;++k) {
        const auto& want=leon_hair_runs::runs[k];const auto& r=p->runs[7+k];
        if(r.role!=7 || r.material!=want.material || r.immutable_asset_id!=29+k || r.triangles!=want.triangles ||
           r.uv.data!=leon_hair_runs::uv || r.uv.size!=sizeof(leon_hair_runs::uv) || r.stream.data!=want.stream || r.stream.size!=want.bytes)return 0;
    }
    for(unsigned k=0;k<2;++k) {
        const auto& m=p->materials[k+1];
        if(m.image.pixels!=hair_colours[k].pixels || m.mask.pixels!=hair_mask.pixels || m.crc!=hair_pair_crc[k] || m.fnv!=hair_pair_fnv[k] ||
           m.image.width!=64 || m.image.height!=128 || m.image.format!=14 || m.mask.width!=64 || m.mask.height!=128 || m.mask.format!=0 ||
           m.material_flags!=4 || m.blend || m.depth_mode!=(RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u) || m.mask_ref || m.mask_same_uv!=1 || m.wrap_s!=1 || m.wrap_t!=1)return 0;
    }
    return 3u|(RE4DC_ACTOR_LEON_NATIVE_LOOK?4u:0u); // routing/order/native-look; live material certificate still gates admission
}
#if RE4DC_NATIVE_MODEL_REGISTRY
#include "coarse_actor_owner_registry.inc"
#endif
#include "coarse_actor_geometry_once.inc"
#if RE4DC_ACTOR_PL08_PACK
#include "coarse_actor_pl08_pack.inc" // ACTOR_PL08_PACK: the pl08-only chunks from a costume-resident heap-4 cell
#endif
#if RE4DC_ACTOR_PL08
#include "coarse_actor_owner_pl08.inc"
#endif
#include "coarse_actor_transaction.inc"
#if RE4DC_ACTOR_PL08_PACK
namespace { bool pl08_pack_owned_live() {return actor_owned_live;} }
#endif
#include "coarse_actor_material.inc" // actor-lifetime-r2 current-owner/material policy
#if RE4DC_ACTOR_EARLY_COARSE
#include "actor_early_coarse.inc"
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
#include "coarse_actor_registry_pack.inc" // the room-owned registry package (loader, publish, retire)
#endif
#endif

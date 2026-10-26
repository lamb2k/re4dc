// ACTOR_PL08 (crowd.mk, default 0): the no-jacket Leon (pl08.drs) on the transaction owner path. Included once by
// coarse_actor_owner_leon.inc after coarse_actor_geometry_once.inc. Same contract as the pl00 owner: the 0x108 role
// rows (actor_material_records_pl08*.inc, generated from the original pl08.drs) must prove all NINE source infos
// (exact_infos), the 119 bind matrices must equal the shared Leon bind, and the certificate runs unchanged. Any
// failure leaves the whole model on the source path. Roles 2..7 and the 14 hair runs use pl00's byte-identical arrays
// and their immutable IDs; roles 0, 1 and 8 (pl08 BIN4, BIN10, BIN16) are leon_pl08_runtime.h's own chunks.
namespace {
#if RE4DC_ACTOR_PL08_PACK
// ACTOR_PL08_PACK: roles 0, 1, 8 are the published package descriptors (coarse_actor_pl08_pack.inc).
const leon4k::Chunk* const pl08_chunk[9]={&pl08_pack_chunks[0],&pl08_pack_chunks[1],&leon4k::chunks[2],&leon4k::chunks[3],
    &leon4k::chunks[4],&leon4k::chunks[5],&leon4k::chunks[6],&leon4k::chunks[7],&pl08_pack_chunks[2]};
#else
const leon4k::Chunk* const pl08_chunk[9]={&leon_pl08::chunks[0],&leon_pl08::chunks[1],&leon4k::chunks[2],&leon4k::chunks[3],
    &leon4k::chunks[4],&leon4k::chunks[5],&leon4k::chunks[6],&leon4k::chunks[7],&leon_pl08::chunks[2]};
#endif
#if RE4DC_LEON_HAND_ANY
// LEON_HAND_DIR: the pl08 plan's role chunks with roles 5 / 6 following the hand poses, and their skin key.
const leon4k::Chunk* pl08_cur[9]={pl08_chunk[0],pl08_chunk[1],pl08_chunk[2],pl08_chunk[3],pl08_chunk[4],pl08_chunk[5],
    pl08_chunk[6],pl08_chunk[7],pl08_chunk[8]};
unsigned pl08_cur_key=1;
#define RE4DC_PL08_ROLES pl08_cur
#define RE4DC_PL08_SKIN_KEY pl08_cur_key
#else
#define RE4DC_PL08_ROLES pl08_chunk
#define RE4DC_PL08_SKIN_KEY 1
#endif
cModelInfo* pl08_infos[9];
cParts* pl08_parts[119];
cModel* pl08_owner;
unsigned pl08_owner_serial,pl08_binding_revision;
cParts* pl08_owner_parts;
cModel* pl08_root_parts;
bool owner_pl08_bind(cModel* m) {
    if(!m || m->id || m->nParts!=119 || !m->pList || !m->pParts || (m->be_flag&0x4000))return false;
    if(!re4dc_actor_role_bindings(m,0x108,pl08_infos,9) || !re4dc_actor::exact_infos(m->pModelInfo,pl08_infos,9))return false;
    const unsigned revision=re4dc_actor_binding_revision(m);if(!revision)return false;
    if(pl08_owner!=m || pl08_owner_serial!=m->serial || pl08_owner_parts!=m->pList || pl08_root_parts!=m->pParts ||
       pl08_binding_revision!=revision) {
        cParts* part=m->pList;
        for(unsigned i=0;i<119;++i) {
            if(!part)return false;pl08_parts[i]=part;
            for(unsigned j=0;j<12;++j)if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) ||
                (!RE4DC_LEON_RIG_SIM(i) && __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f))return false;
            part=part->pList;
        }
        if(part)return false;
        pl08_owner=m;pl08_owner_serial=m->serial;pl08_owner_parts=m->pList;pl08_root_parts=m->pParts;pl08_binding_revision=revision;
    }
    for(unsigned i=0;i<119;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&pl08_parts[i]->lt_inv_mat[0][0])[j]) ||
           !coarse_finite((&pl08_parts[i]->mat[0][0])[j]))return false;
    return true;
}
int owner_pl08_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
#if RE4DC_ACTOR_PL08_PACK
    if(!pl08_pack.published)return 0;
#endif
    if(!owner_pl08_bind(m) || !skin_build(RE4DC_PL08_SKIN_KEY,RE4DC_PL08_ROLES,9))return 0;
    for(unsigned i=0;i<9;++i)if(p.info[i]!=pl08_infos[i] || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    for(unsigned u=0;u<skin_used;++u) {
        const unsigned b=skin_bone[u];
        skin_jobs[u]={&pl08_parts[b]->mat[0][0],RE4DC_LEON_BIND_ROW(b,pl08_parts[b]),bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    for(unsigned i=0;i<9;++i) {
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],RE4DC_PL08_ROLES[i]->palette_count);
        for(unsigned j=0;j<RE4DC_PL08_ROLES[i]->palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
    }
    return 1;
}
#if RE4DC_LEON_HEADLESS
// LEON_HEADLESS (crowd.mk): Leon after cPlLeon::setHead(0) (pl_leon.cpp; chainsaw / claw / scythe / parasite kills):
// the head shape, hair and eye infos are deleted and the neck (player arc 0xB, TPL 7) appended. Appearance 0x109, seven
// compact roles: 0..2 pl08's roles 0..2, 3 the neck (the PS2 disc's pl00 arc 0xB, ps2leon_neck.h), 4 / 5 the current
// hands (as pl08's 5 / 6), 6 pl08's role 8. Same skeleton proof, own skin key; no hair runs.
}
#include "ps2leon_neck.h"
namespace {
cModelInfo* pl08h_infos[7];
const leon4k::Chunk* pl08h_cur[7];
unsigned pl08h_key=0x80000001u;
bool owner_pl08h_bind(cModel* m) {
    if(!m || m->id || m->nParts!=119 || !m->pList || !m->pParts || (m->be_flag&0x4000))return false;
    if(!re4dc_actor_role_bindings(m,0x109,pl08h_infos,7) || !re4dc_actor::exact_infos(m->pModelInfo,pl08h_infos,7))return false;
    const unsigned revision=re4dc_actor_binding_revision(m);if(!revision)return false;
    if(pl08_owner!=m || pl08_owner_serial!=m->serial || pl08_owner_parts!=m->pList || pl08_root_parts!=m->pParts ||
       pl08_binding_revision!=revision) {
        cParts* part=m->pList;
        for(unsigned i=0;i<119;++i) {
            if(!part)return false;pl08_parts[i]=part;
            for(unsigned j=0;j<12;++j)if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) ||
                (!RE4DC_LEON_RIG_SIM(i) && __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f))return false;
            part=part->pList;
        }
        if(part)return false;
        pl08_owner=m;pl08_owner_serial=m->serial;pl08_owner_parts=m->pList;pl08_root_parts=m->pParts;pl08_binding_revision=revision;
    }
    for(unsigned i=0;i<119;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&pl08_parts[i]->lt_inv_mat[0][0])[j]) ||
           !coarse_finite((&pl08_parts[i]->mat[0][0])[j]))return false;
    return true;
}
int owner_pl08h_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
#if RE4DC_ACTOR_PL08_PACK
    if(!pl08_pack.published)return 0;
#endif
    if(!owner_pl08h_bind(m) || !skin_build(pl08h_key,pl08h_cur,7))return 0;
    for(unsigned i=0;i<7;++i)if(p.info[i]!=pl08h_infos[i] || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    for(unsigned u=0;u<skin_used;++u) {
        const unsigned b=skin_bone[u];
        skin_jobs[u]={&pl08_parts[b]->mat[0][0],RE4DC_LEON_BIND_ROW(b,pl08_parts[b]),bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    for(unsigned i=0;i<7;++i) {
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],pl08h_cur[i]->palette_count);
        for(unsigned j=0;j<pl08h_cur[i]->palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
    }
    return 1;
}
int pl08_headless_plan(cModel* m,Re4dcActorPlan* out) {
    if(!m || !out || m->id || RE4DC_LEON_OT_BAD(m) || !RE4DC_LEON_LOD_READY() || !owner_pl08h_bind(m))return 0;
    Re4dcActorPlan p{};p.count=7;p.appearance=0x109;p.image=pl08_image;p.crc=pl08_crc;p.fnv=pl08_fnv;p.palettes=owner_pl08h_palettes;
    const LeonHandPick hand5=leon_hand_pick(5,pl08h_infos[4],leon4k::chunks[5],RE4DC_LEON_STD_INPUT(5));
    const LeonHandPick hand6=leon_hand_pick(6,pl08h_infos[5],leon4k::chunks[6],RE4DC_LEON_STD_INPUT(6));
    if(!hand5.chunk || !hand6.chunk)return 0;
#if RE4DC_ACTOR_PL08_PACK
#define RE4DC_PL08H_OWN(role,src,prefix,k) re4dc_actor::plan_chunk(p,role,pl08h_infos[role],pl08_pack_chunks[k],pl08_pack_input(k))
#else
#define RE4DC_PL08H_OWN(role,src,prefix,k) re4dc_actor::plan_chunk(p,role,pl08h_infos[role],leon_pl08::chunks[k],RE4DC_OWNER_INPUT(leon_pl08,prefix,leon_pl08::chunks[k],119))
#endif
    RE4DC_PL08H_OWN(0,0,r0,0);RE4DC_PL08H_OWN(1,1,r1,1);
    re4dc_actor::plan_chunk(p,2,pl08h_infos[2],leon4k::chunks[2],RE4DC_LEON_ROLE_INPUT(2,i2));
    re4dc_actor::plan_chunk(p,3,pl08h_infos[3],leon_neck::chunk,RE4DC_OWNER_INPUT(leon_neck,n,leon_neck::chunk,119));
    re4dc_actor::plan_chunk(p,4,pl08h_infos[4],*hand5.chunk,hand5.input);re4dc_actor::plan_chunk(p,5,pl08h_infos[5],*hand6.chunk,hand6.input);
    RE4DC_PL08H_OWN(6,8,r8,2);
#undef RE4DC_PL08H_OWN
    pl08h_cur[0]=pl08_chunk[0];pl08h_cur[1]=pl08_chunk[1];pl08h_cur[2]=pl08_chunk[2];pl08h_cur[3]=&leon_neck::chunk;
    pl08h_cur[4]=hand5.chunk;pl08h_cur[5]=hand6.chunk;pl08h_cur[6]=pl08_chunk[8];
    pl08h_key=leon_hand_key(1,hand5.pose,hand6.pose)|0x80000000u;  // never a pl00 / pl08 key: the stream is rebuilt
    p.material_count=1;
    p.materials[0].image=pl08_image;p.materials[0].crc=pl08_crc;p.materials[0].fnv=pl08_fnv;
    p.immutable_asset_id[0]=kActorPl08Asset0;p.immutable_asset_id[1]=kActorPl08Asset0+1u;p.immutable_asset_id[2]=3u;
    p.immutable_asset_id[3]=kLeonNeckAsset;p.immutable_asset_id[4]=hand5.asset;p.immutable_asset_id[5]=hand6.asset;
    p.immutable_asset_id[6]=kActorPl08Asset0+2u;
    for(unsigned i=0;i<7;++i) {
        const auto& c=p.input[i];auto& r=p.runs[p.run_count++];
        r.role=i;r.immutable_asset_id=p.immutable_asset_id[i];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
    }
    if(!p.palette_bytes || !p.workspace_bytes || (re4dc_actor_material_runs_capability(&p)&3u)!=3u)return 0;
    static unsigned logs;if(logs<4){++logs;re4dc_log("LEON_HEADLESS plan f=%u palette=%u workspace=%u neck_tris=%u\n",
        unsigned(pG->Frame_cnt),p.palette_bytes,p.workspace_bytes,leon_neck::chunk.triangles);}
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
    re4dc_atlas_apply(&p);
#endif
    *out=p;return 1;
}
#if defined(RE4DC_LEON_HEAD_IDS)
// LEON_HEADLESS v2: the flying head (SetObj01(player arc 0xC, TPL 7) in the head-loss deaths), appearance 0x10A. The
// player archives of the v2 data set hold, at arc 0xC, a stub the source loads and never draws (no display list
// bytes) followed by the PS2 head (build_head.py): one rigid role (one palette) drawn as a face run on Leon's atlas and
// a hair run on hair material 1. The payload is located and proved here (re4dc_stub_payload: magic, size inside the
// arc, CRC once per address); any failure leaves the head on the source path, which draws nothing from a stub and
// the original GameCube head from an unchanged archive.
struct LeonHead {
    const void* data=nullptr;  // the arc 0xC ModelData the payload was proved for
    bool ok=false;
    leon4k::Chunk chunk{};
    re4dc_source::ChunkInput input{};
    re4dc_source::ByteSpan face{},huv{},hair{};
    unsigned face_tris=0,hair_tris=0;
    alignas(32) unsigned char skin[128];
    unsigned groups=0;
    alignas(32) float T[1][12];
};
LeonHead leon_head;
unsigned leon_head_fail;
// Generic locator: a native payload after a stubbed source BIN, 32-aligned after its last header table, that must end
// inside the BIN's archive entry [d, end). Words: magic, version 1, total bytes, CRC-32 of the bytes after the header.
const unsigned* re4dc_stub_payload(const ModelData* d,const unsigned char* end,unsigned magic,unsigned header_words) {
    const unsigned char* base=reinterpret_cast<const unsigned char*>(d);
    if(!d || (int)(uintptr_t)d->pClr>=0 || !d->pParts)return nullptr;  // relocated (calcModelAddr) headers only
    uintptr_t at=reinterpret_cast<uintptr_t>(d->pParts)+uintptr_t(d->displist_num)*0x20u;
    if(d->flipTbl && d->flipTbl+0x20u>at)at=d->flipTbl+0x20u;
    at=(at+31u)&~uintptr_t(31);
    const unsigned* w=reinterpret_cast<const unsigned*>(at);
    if(at<=uintptr_t(base) || at+header_words*4u>uintptr_t(end) || w[0]!=magic || w[1]!=1u || w[2]<header_words*4u ||
       at+w[2]>uintptr_t(end))return nullptr;
    unsigned crc=0xffffffffu;
    for(const unsigned char* q=reinterpret_cast<const unsigned char*>(at)+header_words*4u;q<reinterpret_cast<const unsigned char*>(at)+w[2];++q) {
        crc^=*q;for(unsigned k=0;k<8;++k)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));
    }
    return (crc^0xffffffffu)==w[3]?w:nullptr;
}
bool leon_head_object(const cModel* m) {
    if(!m || m->id!=1 || m->nParts!=1 || !m->pModelInfo || m->pModelInfo->pList || !m->pList || !m->pParts || !pG->pPlayer)return false;
    return m->pModelInfo->pData==static_cast<const ModelData*>(PL_ARC_PTR(pG->pPlayer,0xC));
}
bool leon_head_refuse(unsigned why) {
    if(leon_head_fail++<4)re4dc_log("LEON_HEAD payload refused why=%u f=%u\n",why,unsigned(pG->Frame_cnt));
    return false;
}
bool leon_head_load(const cModel* m) {
    const ModelData* d=m->pModelInfo->pData;
    if(leon_head.data==d)return leon_head.ok;
    leon_head=LeonHead{};leon_head.data=d;actor_immutable_reset_head();
    const auto* end=static_cast<const unsigned char*>(PL_ARC_PTR(pG->pPlayer,0xD));
    const unsigned* w=re4dc_stub_payload(d,end,0x48344552u,32u);
    if(!w || w[4]!=7u || w[7]!=1u || w[8]!=w[22]+w[27] || w[28]!=1u)return leon_head_refuse(w?1u:0u);
    const unsigned char* b=reinterpret_cast<const unsigned char*>(w);
    static const unsigned char kSpanWords[8]={10,12,14,16,18,20,23,25};  // offset words, each followed by its size
    for(unsigned k:kSpanWords)if((w[k]&31u) || w[k]+w[k+1]>w[2])return leon_head_refuse(2);
    auto& c=leon_head.chunk;
    c={w[4],w[5],w[6],w[7],w[8],w[9],b+w[10],b+w[12],b+w[14],b+w[16],reinterpret_cast<const leon4k::Weight*>(b+w[18])};
    if(w[17]!=w[9] || w[19]!=16u)return leon_head_refuse(3);
    leon_head.input={{b+w[10],w[11]},{b+w[12],w[13]},{b+w[14],w[15]},{b+w[16],w[17]},{b+w[18],w[19]},
        c.position_count,c.normal_count,c.palette_count,c.triangles,119u};
    leon_head.face={b+w[20],w[21]};leon_head.face_tris=w[22];
    leon_head.huv={b+w[23],w[24]};leon_head.hair={b+w[25],w[26]};leon_head.hair_tris=w[27];
    unsigned char used[119]={};
    if(!coarse_group_build(c.weights,1,leon_head.skin,sizeof(leon_head.skin),&leon_head.groups,used) || !used[0])return leon_head_refuse(4);
    re4dc_log("LEON_HEAD payload f=%u tris=%u face=%u hair=%u bytes=%u\n",unsigned(pG->Frame_cnt),c.triangles,w[22],w[27],w[2]);
    return leon_head.ok=true;
}
int leon_head_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
    if(!leon_head_object(m) || !leon_head_load(m) || p.info[0]!=m->pModelInfo || !output[0])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    CoarseBoneJob job={&m->pList->mat[0][0],&m->pList->lt_inv_mat[0][0],leon_head.T[0]};
    re4dc_coarse_skin_bones(invx,&job,1);
    re4dc_coarse_skin_groups(leon_head.skin,leon_head.groups,&leon_head.T[0][0],output[0],1);
    for(unsigned j=0;j<12;++j)if(!coarse_finite(output[0][j]))return 0;
    return 1;
}
int leon_head_plan(cModel* m,Re4dcActorPlan* out) {
#if defined(RE4DC_LEON_HEAD_FORCE_DECLINE) && RE4DC_LEON_HEAD_FORCE_DECLINE
    return 0;  // LEON_HEAD_FORCE_DECLINE (test only): the source path must draw nothing from the stub and not crash
#endif
    if(!out || m->ot_type || !leon_head_load(m))return 0;  // an ordinary object model (OT 0), never the player's OT 7
    cModelInfo* info[1]{};
    if(!re4dc_actor_role_bindings(m,0x10A,info,1))return leon_head_refuse(5);
    if(!re4dc_actor::exact_infos(m->pModelInfo,info,1))return leon_head_refuse(6);
#if RE4DC_ACTOR_PL08_PACK
    const bool pl08=pl08_pack.published;
#else
    const bool pl08=true;
#endif
    Re4dcActorPlan p{};p.count=1;p.appearance=0x10A;p.palettes=leon_head_palettes;
    p.image=pl08?pl08_image:image;p.crc=pl08?pl08_crc:crc;p.fnv=pl08?pl08_fnv:fnv;
    const auto& c=leon_head.chunk;
    re4dc_actor::plan_chunk(p,0,info[0],c,leon_head.input);
    p.immutable_asset_id[0]=kLeonHeadAsset;
    p.material_count=2;
    p.materials[0].image=p.image;p.materials[0].crc=p.crc;p.materials[0].fnv=p.fnv;
    {
        auto& mat=p.materials[1];mat.image=hair_colours[0];mat.mask=hair_mask;mat.crc=hair_pair_crc[0];mat.fnv=hair_pair_fnv[0];
        mat.material_flags=4;mat.blend=0;mat.depth_mode=RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u;
        mat.mask_ref=0;mat.mask_same_uv=1;mat.wrap_s=mat.wrap_t=1;
    }
    {auto& r=p.runs[p.run_count++];r.role=0;r.material=0;r.immutable_asset_id=kLeonHeadAsset+1u;r.triangles=leon_head.face_tris;
        r.uv=p.input[0].uv;r.stream=leon_head.face;}
    {auto& r=p.runs[p.run_count++];r.role=0;r.material=1;r.immutable_asset_id=kLeonHeadAsset+2u;r.triangles=leon_head.hair_tris;
        r.uv=leon_head.huv;r.stream=leon_head.hair;}
    if(!p.palette_bytes || !p.workspace_bytes)return leon_head_refuse(7);
    if((re4dc_actor_material_runs_capability(&p)&3u)!=3u)return leon_head_refuse(8);
    static unsigned logs;if(logs<4){++logs;re4dc_log("LEON_HEAD plan f=%u palette=%u workspace=%u tris=%u pl08=%u\n",
        unsigned(pG->Frame_cnt),p.palette_bytes,p.workspace_bytes,c.triangles,unsigned(pl08));}
    *out=p;return 1;
}
#endif
#endif
}
extern "C" int re4dc_actor_plan_pl08(cModel* m,Re4dcActorPlan* out) {
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    if(RE4DC_WARP_LATE(RE4DC_LATE_LEON_SOURCE))return 0; // test-only old-path arm (warp_late.h 0x10), as the pl00 owner
#endif
#if defined(RE4DC_LEON_HEAD_IDS)
    // LEON_HEADLESS v2: the flying head (cObj01 of the player archive's arc 0xC) plans as 0x10A.
    if(m && m!=(cModel*)pPL && leon_head_object(m))return leon_head_plan(m,out);
#endif
#if RE4DC_LEON_HEADLESS
    // LEON_HEADLESS: once setHead(0) has run (cPlBody::pShape cleared), the player plans as 0x109.
    if(m && m==(cModel*)pPL && pPL->Body && !pPL->Body->pShape) {
#if RE4DC_ACTOR_PL08_PACK
        if(!pl08_pack.published)return 0;
#endif
        return pl08_headless_plan(m,out);
    }
#endif
#if RE4DC_ACTOR_PL08_PACK
    if(!pl08_pack.published)return 0;  // no costume package published: the whole model keeps the source path
#endif
    if(!m || !out || m->id || RE4DC_LEON_OT_BAD(m) || !RE4DC_LEON_LOD_READY() || !owner_pl08_bind(m))return 0;
    Re4dcActorPlan p{};p.count=9;p.appearance=0x108;p.image=pl08_image;p.crc=pl08_crc;p.fnv=pl08_fnv;p.palettes=owner_pl08_palettes;
#if RE4DC_ACTOR_PL08_PACK
#define RE4DC_PL08_OWN(role,prefix,k) re4dc_actor::plan_chunk(p,role,pl08_infos[role],pl08_pack_chunks[k],pl08_pack_input(k))
#else
#define RE4DC_PL08_OWN(role,prefix,k) re4dc_actor::plan_chunk(p,role,pl08_infos[role],leon_pl08::chunks[k],RE4DC_OWNER_INPUT(leon_pl08,prefix,leon_pl08::chunks[k],119))
#endif
#define RE4DC_PL08_SHARED(role,prefix) re4dc_actor::plan_chunk(p,role,pl08_infos[role],leon4k::chunks[role],RE4DC_LEON_ROLE_INPUT(role,prefix))
#if RE4DC_LEON_HAND_ANY
    const LeonHandPick hand5=leon_hand_pick(5,pl08_infos[5],leon4k::chunks[5],RE4DC_LEON_STD_INPUT(5));
    const LeonHandPick hand6=leon_hand_pick(6,pl08_infos[6],leon4k::chunks[6],RE4DC_LEON_STD_INPUT(6));
#if RE4DC_LEON_HAND_PACK
    if(!hand5.chunk || !hand6.chunk)return 0;
#endif
    RE4DC_PL08_OWN(0,r0,0);RE4DC_PL08_OWN(1,r1,1);RE4DC_PL08_SHARED(2,i2);RE4DC_PL08_SHARED(3,i3);RE4DC_PL08_SHARED(4,i4);
    re4dc_actor::plan_chunk(p,5,pl08_infos[5],*hand5.chunk,hand5.input);re4dc_actor::plan_chunk(p,6,pl08_infos[6],*hand6.chunk,hand6.input);
    RE4DC_PL08_SHARED(7,i7);RE4DC_PL08_OWN(8,r8,2);
    pl08_cur[5]=hand5.chunk;pl08_cur[6]=hand6.chunk;pl08_cur_key=leon_hand_key(1,hand5.pose,hand6.pose);
    const unsigned hand_palette=leon_r32(hand5.chunk->palette_count*48u)+leon_r32(hand6.chunk->palette_count*48u)
        -leon_r32(RE4DC_LEON_STD_PAL(5)*48u)-leon_r32(RE4DC_LEON_STD_PAL(6)*48u);
#else
    RE4DC_PL08_OWN(0,r0,0);RE4DC_PL08_OWN(1,r1,1);RE4DC_PL08_SHARED(2,i2);RE4DC_PL08_SHARED(3,i3);RE4DC_PL08_SHARED(4,i4);
    RE4DC_PL08_SHARED(5,i5);RE4DC_PL08_SHARED(6,i6);RE4DC_PL08_SHARED(7,i7);RE4DC_PL08_OWN(8,r8,2);
#endif
#undef RE4DC_PL08_OWN
#undef RE4DC_PL08_SHARED
    // Palette/workspace bytes of the nine role chunks (palettes 214,2,1,61,29,2,2,229,3).
#if RE4DC_PS2_LEON
    // PS2_LEON: roles 2..7 are the arm's (pl08's own 0, 1, 8 unchanged); totals precomputed in ps2leon_runtime.h.
#if RE4DC_LEON_HAND_ANY
    if(p.palette_bytes!=RE4DC_PL08_PLAN_PAL+hand_palette || p.workspace_bytes!=RE4DC_PL08_PLAN_WS)return 0;
#else
    if(p.palette_bytes!=leon4k::pl08_plan_palette_bytes || p.workspace_bytes!=leon4k::pl08_plan_workspace_bytes)return 0;
#endif
#else
    if(p.palette_bytes!=26144 || p.workspace_bytes!=26112)return 0;
#endif
    p.material_count=1+RE4DC_LEON_HAIR_MATERIALS;  // PS2_LEON: only the hair materials the arm's runs draw
    p.materials[0].image=pl08_image;p.materials[0].crc=pl08_crc;p.materials[0].fnv=pl08_fnv;
    for(unsigned i=0;i<RE4DC_LEON_HAIR_MATERIALS;++i) {
        auto& mat=p.materials[i+1];mat.image=hair_colours[i];mat.mask=hair_mask;
        mat.crc=hair_pair_crc[i];mat.fnv=hair_pair_fnv[i];
        // pl08's hair is pl00's BIN9 with pl00's TPL7 (byte-identical): the pl00 owner's hair materials, unchanged.
        mat.material_flags=4;mat.blend=0;mat.depth_mode=RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u;
        mat.mask_ref=0;mat.mask_same_uv=1;mat.wrap_s=mat.wrap_t=1;
    }
    for(unsigned i=2;i<8;++i)p.immutable_asset_id[i]=i+1;  // pl00's IDs: the same arrays
#if RE4DC_LEON_HAND_ANY
    p.immutable_asset_id[5]=hand5.asset;p.immutable_asset_id[6]=hand6.asset;
#endif
    p.immutable_asset_id[0]=kActorPl08Asset0;p.immutable_asset_id[1]=kActorPl08Asset0+1u;p.immutable_asset_id[8]=kActorPl08Asset0+2u;
    for(unsigned i=0;i<7;++i) {
        const auto& c=p.input[i];auto& r=p.runs[p.run_count++];
        r.role=i;r.immutable_asset_id=p.immutable_asset_id[i];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
    }
    for(const auto& run:leon_hair_runs::runs) {
        auto& r=p.runs[p.run_count++];r.role=7;r.material=run.material;r.immutable_asset_id=run.asset_id;r.triangles=run.triangles;
        r.uv={RE4DC_LEON_HAIR_UV_DATA,RE4DC_LEON_HAIR_UV_SIZE};r.stream={run.stream,run.bytes};
    }
    {
        const auto& c=p.input[8];auto& r=p.runs[p.run_count++];
        r.role=8;r.immutable_asset_id=p.immutable_asset_id[8];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
    }
    if((re4dc_actor_material_runs_capability(&p)&3u)!=3u)return 0;
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
    re4dc_atlas_apply(&p);
#endif
    *out=p;return 1;
}

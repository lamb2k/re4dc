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
                __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f)return false;
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
    if(!owner_pl08_bind(m) || !skin_build(1,pl08_chunk,9))return 0;
    for(unsigned i=0;i<9;++i)if(p.info[i]!=pl08_infos[i] || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    for(unsigned u=0;u<skin_used;++u) {
        const unsigned b=skin_bone[u];
        skin_jobs[u]={&pl08_parts[b]->mat[0][0],&pl08_parts[b]->lt_inv_mat[0][0],bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    for(unsigned i=0;i<9;++i) {
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],pl08_chunk[i]->palette_count);
        for(unsigned j=0;j<pl08_chunk[i]->palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
    }
    return 1;
}
}
extern "C" int re4dc_actor_plan_pl08(cModel* m,Re4dcActorPlan* out) {
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    if(RE4DC_WARP_LATE(RE4DC_LATE_LEON_SOURCE))return 0; // test-only old-path arm (warp_late.h 0x10), as the pl00 owner
#endif
#if RE4DC_ACTOR_PL08_PACK
    if(!pl08_pack.published)return 0;  // no costume package published: the whole model keeps the source path
#endif
    if(!m || !out || m->id || m->ot_type!=7 || !owner_pl08_bind(m))return 0;
    Re4dcActorPlan p{};p.count=9;p.appearance=0x108;p.image=pl08_image;p.crc=pl08_crc;p.fnv=pl08_fnv;p.palettes=owner_pl08_palettes;
#if RE4DC_ACTOR_PL08_PACK
#define RE4DC_PL08_OWN(role,prefix,k) re4dc_actor::plan_chunk(p,role,pl08_infos[role],pl08_pack_chunks[k],pl08_pack_input(k))
#else
#define RE4DC_PL08_OWN(role,prefix,k) re4dc_actor::plan_chunk(p,role,pl08_infos[role],leon_pl08::chunks[k],RE4DC_OWNER_INPUT(leon_pl08,prefix,leon_pl08::chunks[k],119))
#endif
#define RE4DC_PL08_SHARED(role,prefix) re4dc_actor::plan_chunk(p,role,pl08_infos[role],leon4k::chunks[role],RE4DC_OWNER_INPUT(leon4k,prefix,leon4k::chunks[role],119))
    RE4DC_PL08_OWN(0,r0,0);RE4DC_PL08_OWN(1,r1,1);RE4DC_PL08_SHARED(2,i2);RE4DC_PL08_SHARED(3,i3);RE4DC_PL08_SHARED(4,i4);
    RE4DC_PL08_SHARED(5,i5);RE4DC_PL08_SHARED(6,i6);RE4DC_PL08_SHARED(7,i7);RE4DC_PL08_OWN(8,r8,2);
#undef RE4DC_PL08_OWN
#undef RE4DC_PL08_SHARED
    // Palette/workspace bytes of the nine role chunks (palettes 214,2,1,61,29,2,2,229,3).
#if RE4DC_PS2_LEON
    // PS2_LEON: roles 2..7 are the arm's (pl08's own 0, 1, 8 unchanged); totals precomputed in ps2leon_runtime.h.
    if(p.palette_bytes!=leon4k::pl08_plan_palette_bytes || p.workspace_bytes!=leon4k::pl08_plan_workspace_bytes)return 0;
#else
    if(p.palette_bytes!=26144 || p.workspace_bytes!=26112)return 0;
#endif
    p.material_count=3;
    p.materials[0].image=pl08_image;p.materials[0].crc=pl08_crc;p.materials[0].fnv=pl08_fnv;
    for(unsigned i=0;i<2;++i) {
        auto& mat=p.materials[i+1];mat.image=hair_colours[i];mat.mask=hair_mask;
        mat.crc=hair_pair_crc[i];mat.fnv=hair_pair_fnv[i];
        // pl08's hair is pl00's BIN9 with pl00's TPL7 (byte-identical): the pl00 owner's hair materials, unchanged.
        mat.material_flags=4;mat.blend=0;mat.depth_mode=RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u;
        mat.mask_ref=0;mat.mask_same_uv=1;mat.wrap_s=mat.wrap_t=1;
    }
    for(unsigned i=2;i<8;++i)p.immutable_asset_id[i]=i+1;  // pl00's IDs: the same arrays
    p.immutable_asset_id[0]=kActorPl08Asset0;p.immutable_asset_id[1]=kActorPl08Asset0+1u;p.immutable_asset_id[8]=kActorPl08Asset0+2u;
    for(unsigned i=0;i<7;++i) {
        const auto& c=p.input[i];auto& r=p.runs[p.run_count++];
        r.role=i;r.immutable_asset_id=p.immutable_asset_id[i];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
    }
    for(const auto& run:leon_hair_runs::runs) {
        auto& r=p.runs[p.run_count++];r.role=7;r.material=run.material;r.immutable_asset_id=run.asset_id;r.triangles=run.triangles;
        r.uv={leon_hair_runs::uv,sizeof(leon_hair_runs::uv)};r.stream={run.stream,run.bytes};
    }
    {
        const auto& c=p.input[8];auto& r=p.runs[p.run_count++];
        r.role=8;r.immutable_asset_id=p.immutable_asset_id[8];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
    }
    if((re4dc_actor_material_runs_capability(&p)&3u)!=3u)return 0;
    *out=p;return 1;
}

// Included at file scope after the actual actor package owners. No source ABI
// is duplicated here; the caller's real Re4dcActorSource/part and chunk types
// supply the exact consumed array addresses and extents.
#if RE4DC_GC_ASSET_GATE
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**);
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned);
extern "C" int re4dc_actor_model_source(const void*,Re4dcActorSource*);
namespace {
unsigned gcasset_actor_consumer_mask(const Re4dcModelPart& part){
    using namespace re4dc_gcasset;
    const void* data=nullptr;ModelMember member;
    const unsigned identity=re4dc_gcasset_model_identity(part.model,part.info,&data);
    if(identity==0xffffffffU)return 0;
    const bool bound=member_lookup(data,&member);
    const unsigned kind=identity>>24,id=(identity>>16)&255U;
    // These classes are shared with non-weapons. Only a live original member
    // supplies their exact role; absent/retired binding cannot mean non-Weapon.
    if(!bound && ((kind==1 && id==0x0a) || (kind==0 && id==0x4f)))return 0;
    // Original BIN family/ARC selects a consumer only. It never supplies the
    // replacement's ancestry or replaces the selected package/copy serial.
    return (1U<<SourceGeometry)|(re4dc_gcasset_weapon_consumer(part.model,part.info,
        bound?member.arc:0,bound?unsigned(member.family):unsigned(OtherOwner))?1U<<Weapon:0U);
}
inline bool gcasset_actor_inside(const re4dc_gcasset::PayloadProof& proof,const void* data,unsigned bytes){
    if(!proof.owner || !proof.serial || !proof.base || !data || !bytes)return false;
    const auto base=reinterpret_cast<std::uintptr_t>(proof.base),at=reinterpret_cast<std::uintptr_t>(data);
    return at>=base && at-base<=proof.bytes && bytes<=proof.bytes-unsigned(at-base);
}
template<class Chunk>
bool gcasset_actor_chunk(const Chunk& c,unsigned uv_bytes,const Re4dcModelPart& p,const Re4dcActorSource& s){
    const auto start=reinterpret_cast<std::uintptr_t>(c.stream),at=reinterpret_cast<std::uintptr_t>(p.stream);
    return c.positions==s.positions && c.normals==s.normals && c.uv==p.uv &&
        c.position_count==s.position_count && c.normal_count==s.normal_count &&
        c.position_count==p.position_count && c.normal_count==p.normal_count &&
        c.palette_count==s.palette_entries && !s.small_normals && uv_bytes &&
        at>=start && at-start<=c.stream_bytes && p.stream_bytes && p.stream_bytes<=c.stream_bytes-unsigned(at-start);
}
template<class Chunk>
bool gcasset_actor_bound(const re4dc_gcasset::PayloadProof& proof,const Chunk& c,unsigned uv_bytes){
    return c.position_count<=32768 && c.normal_count<=32768 && c.palette_count<=256 &&
        gcasset_actor_inside(proof,c.positions,c.position_count*8) &&
        gcasset_actor_inside(proof,c.normals,c.normal_count*8) && gcasset_actor_inside(proof,c.uv,uv_bytes) &&
        gcasset_actor_inside(proof,c.stream,c.stream_bytes) && gcasset_actor_inside(proof,c.weights,c.palette_count*16);
}
}
namespace {
re4dc_gcasset::SourceUse gcasset_actor_current_select(const Re4dcModelPart* part,const Re4dcActorSource* source,bool classify){
    using namespace re4dc_gcasset;
    if(!part || !source)return {};
    PayloadProof* selected=nullptr;bool ambiguous=false;
    const auto accept=[&](PayloadProof& proof){if(selected && selected!=&proof)ambiguous=true;else selected=&proof;};
#if RE4DC_ACTOR_TRANSACTION && !(defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD)
    if(gcasset_compiled_actor.serial){
        for(unsigned k=0;k<8;++k){const auto input=gcasset_compiled_input(k);if(!gcasset_compiled_current(k))continue;
            if(gcasset_actor_chunk(leon4k::chunks[k],input.uv.size,*part,*source))accept(gcasset_compiled_actor);
        }
        auto hair=leon4k::chunks[7];hair.uv=RE4DC_LEON_HAIR_UV_DATA;
        for(const auto& run:leon_hair_runs::runs){hair.stream=run.stream;hair.stream_bytes=run.bytes;
            if(gcasset_compiled_current(7) && gcasset_actor_chunk(hair,RE4DC_LEON_HAIR_UV_SIZE,*part,*source))accept(gcasset_compiled_actor);
        }
    }
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY && RE4DC_NATIVE_MODEL_REGISTRY_PACK
    for(unsigned g=0;g<registry.geometry_count;++g){
#if RE4DC_NMR_MASK
        const auto c=registry_gview(g);
#else
        const auto& c=registry.chunks[g];
#endif
        if(gcasset_actor_chunk(c,c.uv_bytes,*part,*source))
            for(auto& proof:gcasset_registry)if(gcasset_actor_bound(proof,c,c.uv_bytes))accept(proof);
    }
#endif
#if RE4DC_ACTOR_PL08 && RE4DC_ACTOR_PL08_PACK
    if(pl08_pack.published)for(unsigned k=0;k<3;++k){const auto& c=pl08_pack_chunks[k];const unsigned uv_bytes=pl08_pack.view[k].bytes[2];
        if(gcasset_actor_chunk(c,uv_bytes,*part,*source) && gcasset_actor_bound(gcasset_pl08,c,uv_bytes))accept(gcasset_pl08);
    }
#endif
#if defined(RE4DC_GC_ASSET_HAND_SOURCE)
    for(unsigned side=0;side<2;++side)if(leon_hand_pack::gcasset_hand_chunk_current(side)){
        const auto& c=leon4k::chunks[5+side];const auto& x=leon_hand_pack::blobs[leon_hand_pack::slot_blob[side]];
        if(gcasset_actor_chunk(c,x.size[2],*part,*source))accept(leon_hand_pack::gcasset_hand_slot[side]);
    }
#endif
    // Other hand owners remain unqualified, never the caller BIN.
    if(!selected || ambiguous)return {};
    const unsigned mask=classify?gcasset_actor_consumer_mask(*part):1U<<SourceGeometry;
    if(!mask)return {};
    return {selected->serial,mask,part->model,part->info,selected};
}
}
extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_actor_select(const Re4dcModelPart* part,const Re4dcActorSource* source){
    using namespace re4dc_gcasset;
    if(!part || !source)return {};
    const ReplayUse saved=replay_use;
    if(saved.serial!=0xffffffffU){
        if(!saved.payload)return {};
        // Validate current consumed arrays against the SAVED identity only.
        // A matching current geometry never replaces its frozen class mask.
        const auto current=gcasset_actor_current_select(part,source,false);
        if(current.payload!=saved.payload || current.serial!=saved.serial)return {};
        return {saved.serial,saved.mask,part->model,part->info,saved.payload};
    }
    return gcasset_actor_current_select(part,source,true);
}
extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_actor_main_select(const Re4dcModelPart* part,const re4dc_gcasset::SourceUse* previous){
    using namespace re4dc_gcasset;
    if(!part)return {};
    const ReplayUse saved=replay_use;
    const bool replay=saved.serial!=0xffffffffU;
    const SourceUse frozen{saved.serial,saved.mask,part->model,part->info,saved.payload};
    Re4dcActorSource source{};
    if(!re4dc_actor_model_source(part->info,&source))return {};
    // Array-less parts consume the authenticated source via the existing lazy
    // skin path. Explicit arrays need an exact original-array match; an alien
    // or merely prepared pointer may not inherit a replacement descriptor.
    if(!part->positions || (part->positions==source.positions && part->normals==source.normals &&
       part->position_stride==8 && part->normal_stride==8 && part->normal_shift==14)){
        const auto replacement=re4dc_gcasset_actor_select(part,&source);
        if(replacement.serial)return replacement;
    }
    if(replay)previous=&frozen;
    // Preserve only the gateway's same original BIN, with all consumed source
    // arrays and complete stream bounded by that current captured generation.
    // Prepared non-BIN arrays without a controlled-copy receipt stay unknown.
    if(!previous || previous->payload || !previous->serial || previous->model!=part->model || previous->info!=part->info ||
       !source.position_count || source.position_count>32768 || !source.normal_count || source.normal_count>32768 ||
       source.position_count!=part->position_count || source.normal_count!=part->normal_count ||
       !member_contains(previous->serial,part->stream,part->stream_bytes) ||
       !member_contains(previous->serial,source.positions,source.position_count*8) ||
       !member_contains(previous->serial,source.normals,source.normal_count*(source.small_normals?4:8)))return {};
    if(part->positions && (part->positions!=source.positions || part->normals!=source.normals || part->position_stride!=8 ||
       part->normal_stride!=(source.small_normals?4U:8U) || part->normal_shift!=(source.small_normals?6U:14U)))return {};
    return *previous;
}
#endif

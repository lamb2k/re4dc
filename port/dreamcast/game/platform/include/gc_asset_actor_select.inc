// Included at file scope after the actual actor package owners. No source ABI
// is duplicated here; the caller's real Re4dcActorSource/part and chunk types
// supply the exact consumed array addresses and extents.
#if RE4DC_GC_ASSET_GATE
namespace {
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
extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_actor_select(const Re4dcModelPart* part,const Re4dcActorSource* source){
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
    // Other hand owners remain unqualified, never the caller BIN.
    if(!selected || ambiguous)return {};
    return {selected->serial,1U<<SourceGeometry,part->model,part->info,selected};
}
#endif

#if RE4DC_GC_ASSET_GATE
namespace {
re4dc_gcasset::PayloadProof gcasset_compiled_actor;
bool gcasset_compiled_started;
#if RE4DC_ACTOR_TRANSACTION && !(defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD)
re4dc_source::ChunkInput gcasset_compiled_input(unsigned role){
    switch(role){
#define GCA_COMPILED_ROLE(n) case n:return RE4DC_OWNER_INPUT(leon4k,i##n,leon4k::chunks[n],119)
    GCA_COMPILED_ROLE(0);GCA_COMPILED_ROLE(1);GCA_COMPILED_ROLE(2);GCA_COMPILED_ROLE(3);GCA_COMPILED_ROLE(4);
#if !RE4DC_LEON_HAND_PACK
    GCA_COMPILED_ROLE(5);GCA_COMPILED_ROLE(6);
#endif
    GCA_COMPILED_ROLE(7);
#undef GCA_COMPILED_ROLE
    default:return {};
    }
}
bool gcasset_compiled_current(unsigned role){
    const auto in=gcasset_compiled_input(role);const auto& c=leon4k::chunks[role];
    return in.positions.data && c.positions==in.positions.data && c.normals==in.normals.data &&
        c.uv==in.uv.data && c.stream==in.stream.data &&
        reinterpret_cast<const unsigned char*>(c.weights)==in.weights.data &&
        c.position_count<=in.positions.size/8 && c.normal_count<=in.normals.size/8 &&
        c.palette_count<=in.weights.size/16 && c.stream_bytes<=in.stream.size;
}
#endif
}
extern "C" void re4dc_gcasset_actor_startup(){
    using namespace re4dc_gcasset;
    if(gcasset_compiled_started)return;
    gcasset_compiled_started=true;
#if defined(RE4DC_GC_ASSET_HAND_SOURCE)
    leon_hand_pack::gcasset_hand_startup();
#endif
#if RE4DC_ACTOR_TRANSACTION && !(defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD)
    PayloadSpan spans[48];unsigned count=0,metadata[8][6]{};
    for(unsigned k=0;k<8;++k){const auto in=gcasset_compiled_input(k);if(!in.positions.data)continue;
        const auto& c=leon4k::chunks[k];
        metadata[k][0]=c.source_info;metadata[k][1]=c.position_count;metadata[k][2]=c.normal_count;
        metadata[k][3]=c.palette_count;metadata[k][4]=c.triangles;metadata[k][5]=c.stream_bytes;
        for(const auto span:{in.positions,in.normals,in.uv,in.stream,in.weights}){
            if(!span.data || !span.size || span.size>40U*1024*1024){unresolved(SourceGeometry,"compiled-span-bounds");return;}
            spans[count++]={span.data,unsigned(span.size)};
        }
    }
    spans[count++]={metadata,sizeof metadata};spans[count++]={leon4k::bind,sizeof(leon4k::bind)};
    spans[count++]={RE4DC_LEON_HAIR_UV_DATA,RE4DC_LEON_HAIR_UV_SIZE};
    for(const auto& run:leon_hair_runs::runs){
        if(count==48){unresolved(SourceGeometry,"compiled-span-capacity");return;}
        spans[count++]={run.stream,run.bytes};
    }
    if(ensure_disc_catalog())(void)payload_capture_fragments(gcasset_compiled_actor,&gcasset_compiled_actor,spans,count);
#else
    unresolved(SourceGeometry,"compiled-actor-profile");
#endif
}
#endif

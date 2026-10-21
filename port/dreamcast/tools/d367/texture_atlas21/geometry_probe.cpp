// Current retained QA ID layout: kRegistryAssetEnd=120, from exact preprocessed
// coarse_actor.cpp in object-v2-stack. Exercise the ACTUAL proof/reset source.
class cModelInfo { public:cModelInfo* pList=nullptr; };
#include "atlas_bind.h"
#include "atlas-bind-case.h"
#include <cassert>
#include <cstdio>
#include <vector>
constexpr unsigned kRegistryAssetEnd=120u;
#include "../../../game/coarse_actor_geometry_once.inc"
int main() {
    static_assert(kLeonAtlasAsset0==127u && RE4DC_IMMUTABLE_CHUNK_COUNT==148u);
    static_assert(kLeonAtlasAsset0>kLeonHeadAsset+2u);
    static_assert(sizeof(actor_immutable_chunks)/sizeof(actor_immutable_chunks[0])==RE4DC_IMMUTABLE_CHUNK_COUNT);
    auto b=case_data::bundle();
    const bool standard=b.appearance==0x100;
    const unsigned first=kLeonAtlasAsset0+(standard?0u:9u);
    assert(b.run_count==(standard?9u:13u));
    re4dc_source::ChunkProof proof{};
    auto first_input=b.source;first_input.uv=b.runs[0].uv;first_input.stream=b.runs[0].stream;first_input.triangles=b.runs[0].triangles;
    for(unsigned j=0;j<b.run_count;++j) {
        auto c=b.source;c.uv=b.runs[j].uv;c.stream=b.runs[j].stream;c.triangles=b.runs[j].triangles;
        assert(re4dc_actor_immutable_chunk_proof(first+j,c,proof)==re4dc_source::BlobError::None);
    }
    assert(re4dc_actor_immutable_chunk_proof(RE4DC_IMMUTABLE_CHUNK_COUNT+1u,first_input,proof)==re4dc_source::BlobError::Array);
    std::vector<unsigned char> new_positions(first_input.positions.data,first_input.positions.data+first_input.positions.size);
    auto relocated=first_input;relocated.positions={new_positions.data(),new_positions.size()};
    assert(re4dc_actor_immutable_chunk_proof(first,relocated,proof)==re4dc_source::BlobError::Array);
    actor_immutable_reset_head(); // only existing head IDs, disjoint from every tile run
    for(unsigned j=0;j<b.run_count;++j)assert(actor_immutable_chunks[first+j-1].state==2);
    const unsigned reset=actor_immutable_reset_pl08();
    assert(reset==(standard?0u:13u));
    for(unsigned j=0;j<b.run_count;++j)assert(actor_immutable_chunks[first+j-1].state==(standard?2u:0u));
    assert(re4dc_actor_immutable_chunk_proof(first,relocated,proof)==(standard?re4dc_source::BlobError::Array:re4dc_source::BlobError::None));
    std::printf("{\"actual_immutable_source\":true,\"global_first\":%u,\"global_last\":%u,\"runs\":%u,\"pl08_reset\":%u,\"old_ids_preserved\":true}\n",kLeonAtlasAsset0,RE4DC_IMMUTABLE_CHUNK_COUNT,b.run_count,reset);
}
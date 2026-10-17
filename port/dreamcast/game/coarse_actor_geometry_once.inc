// Include exactly once in coarse_actor.cpp under ACTOR_TRANSACTION.
// Asset bytes are checked on their first admission, before any native header.
// Later checks compare their complete immutable descriptors. Source archive
// lifetime and live material checks remain separate and mandatory.
#include "coarse_actor_geometry_once.h"
#include "actor_ganado_ps2_stump.h"
namespace {
struct ActorImmutableChunk {
    re4dc_source::ChunkInput input{};
    re4dc_source::ChunkProof proof{};
    re4dc_source::BlobError error{};
    unsigned state=0; // 0 unseen, 1 validating, 2 terminal (pass OR failure)
};
#if RE4DC_NATIVE_MODEL_REGISTRY
// NATIVE_MODEL_REGISTRY: the registry chunks follow the fixed IDs (coarse_actor_owner_registry.inc kRegistryAsset0).
constexpr unsigned kActorImmutableChunks=kRegistryAssetEnd-1u;
#elif RE4DC_CROWD_FAR
// Lane crowd far tier: IDs 47..66 are the far bundle's chunks (coarse_actor_owner_ganado.inc kOwnerFarAsset+a*4+role).
constexpr unsigned kActorImmutableChunks=66+RE4DC_GANADO_STUMP_IDS;
#else
constexpr unsigned kActorImmutableChunks=46+RE4DC_GANADO_STUMP_IDS;
#endif
#if RE4DC_ACTOR_PL08
// ACTOR_PL08: the three pl08-only chunks (roles 0, 1, 8) follow every fixed ID. Its other roles and the 14 hair runs
// use pl00's arrays and IDs unchanged (byte-identical source sections; NS/pl08 merge_pack.py proofs).
constexpr unsigned kActorPl08Asset0=kActorImmutableChunks+1u;
#if RE4DC_LEON_HAND_TABLE
// LEON_HAND_POSES + LEON_HAND_DIR: the PS2 pose hands (ps2leon_hands.h) follow the pl08 IDs, one ID per pose.
constexpr unsigned kLeonHandAsset0=kActorImmutableChunks+4u;
ActorImmutableChunk actor_immutable_chunks[kActorImmutableChunks+3u+leon_hands::count];
#define RE4DC_IMMUTABLE_CHUNK_COUNT (kActorImmutableChunks+3u+leon_hands::count)
#else
ActorImmutableChunk actor_immutable_chunks[kActorImmutableChunks+3u];
#define RE4DC_IMMUTABLE_CHUNK_COUNT (kActorImmutableChunks+3u)
#endif
#else
#define RE4DC_IMMUTABLE_CHUNK_COUNT kActorImmutableChunks
#endif
#if !RE4DC_ACTOR_PL08
ActorImmutableChunk actor_immutable_chunks[kActorImmutableChunks];
#endif

bool actor_same_span(const re4dc_source::ByteSpan& a,
                     const re4dc_source::ByteSpan& b) {
    return a.data==b.data && a.size==b.size;
}
bool actor_same_chunk(const re4dc_source::ChunkInput& a,
                      const re4dc_source::ChunkInput& b) {
    // Do not memcmp a structure: padding is not an identity field.
    return actor_same_span(a.positions,b.positions) &&
        actor_same_span(a.normals,b.normals) && actor_same_span(a.uv,b.uv) &&
        actor_same_span(a.stream,b.stream) && actor_same_span(a.weights,b.weights) &&
        a.position_count==b.position_count && a.normal_count==b.normal_count &&
        a.palette_count==b.palette_count && a.triangles==b.triangles && a.bones==b.bones;
}
#if RE4DC_NMR_RUN_SHARE
bool actor_same_bytes(const re4dc_source::ByteSpan& a,const re4dc_source::ByteSpan& b) {
    return a.size==b.size && (a.data==b.data || (a.data && b.data && !__builtin_memcmp(a.data,b.data,a.size)));
}
bool actor_same_run_content(const re4dc_source::ChunkInput& a,const re4dc_source::ChunkInput& b) {
    return actor_same_span(a.uv,b.uv) && actor_same_span(a.stream,b.stream) &&
        a.position_count==b.position_count && a.normal_count==b.normal_count &&
        a.palette_count==b.palette_count && a.triangles==b.triangles && a.bones==b.bones &&
        actor_same_bytes(a.positions,b.positions) && actor_same_bytes(a.normals,b.normals) && actor_same_bytes(a.weights,b.weights);
}
#endif
}

extern "C" re4dc_source::BlobError re4dc_actor_immutable_chunk_proof(
    unsigned asset_id,const re4dc_source::ChunkInput& input,
    re4dc_source::ChunkProof& output) {
    using re4dc_source::BlobError;
    output={};
    if(!asset_id || asset_id>RE4DC_IMMUTABLE_CHUNK_COUNT)return BlobError::Array;
    auto& entry=actor_immutable_chunks[asset_id-1];
    if(entry.state==0) {
        // There are no callbacks or threads in preflight_chunk. The in-progress
        // state nevertheless refuses re-entry rather than exposing an empty proof.
        entry.state=1;
        entry.input=input;
        entry.error=re4dc_source::preflight_chunk(input,entry.proof);
        entry.state=2;
    }
    // An ID cannot be rebound, including after a failed first qualification.
    // New compile-time asset variants require their own ID/table revision.
#if RE4DC_NMR_RUN_SHARE
    // NATIVE_MODEL_REGISTRY_RUN_SHARE (native_model_registry.mk): a pool package stores an identical mask (pair) run
    // once (the pack check refuses a geometry stored twice), and two sections of one BIN under two TPLs (zealot-em1c-09h
    // 0x217 with TPL 0x218 / 0x219) both draw it; a run is proved with its role chunk's arrays, which are separate but
    // byte-identical copies. The same run (uv / stream spans) over equal arrays shares the bound proof.
    if(entry.state!=2 || (!actor_same_chunk(entry.input,input) && !actor_same_run_content(entry.input,input)))return BlobError::Array;
#else
    if(entry.state!=2 || !actor_same_chunk(entry.input,input))return BlobError::Array;
#endif
    if(entry.error==BlobError::None)output=entry.proof;
    return entry.error;
}
#if defined(RE4DC_GANADO_LOD) && RE4DC_GANADO_LOD
// GANADO_LOD (coarse_ganado_lod.inc): a level load rebinds the body / head IDs to the new bytes; called only from the
// actor retirement (no owned record holds a proof) or before any owner plan.
extern "C" void re4dc_actor_immutable_chunk_reset(unsigned asset_id) {
    if(asset_id && asset_id<=RE4DC_IMMUTABLE_CHUNK_COUNT)actor_immutable_chunks[asset_id-1]={};
}
#endif
#if RE4DC_ACTOR_PL08_PACK
namespace {
// ACTOR_PL08_PACK: the three pl08 IDs belong to one published costume package (coarse_actor_pl08_pack.inc). Every
// publish, unpublish and retire resets them, so a reload (also at the same address) is qualified again.
unsigned actor_immutable_reset_pl08() {
    unsigned n=0;
    for(unsigned id=kActorPl08Asset0;id<kActorPl08Asset0+3u;++id){auto& e=actor_immutable_chunks[id-1];n+=e.state!=0;e={};}
    return n;
}
}
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
namespace {
// NATIVE_MODEL_REGISTRY_PACK: the registry IDs belong to one published room package (its unique geometries). Only its
// retire resets them, after the transaction's owned records are revoked; the next package's geometry is
// qualified again on its first admission. The fixed IDs before kRegistryAsset0 are never reset.
unsigned actor_immutable_reset_registry() {
    unsigned n=0;
    for(unsigned id=kRegistryAsset0;id<kRegistryAssetEnd;++id){auto& e=actor_immutable_chunks[id-1];n+=e.state!=0;e={};}
    return n;
}
}
#endif

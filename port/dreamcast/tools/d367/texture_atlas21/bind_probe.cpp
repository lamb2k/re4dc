// Only the real plan header's inline list helper needs a source class here.
// No game object is created/dereferenced by this source-format host probe.
class cModelInfo { public: cModelInfo* pList=nullptr; };
#include "atlas_bind.h"
#include "atlas-bind-case.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <limits>
#include <vector>
#if RE4DC_ATLAS_RUNTIME_PROBE && RE4DC_LEON_ATLAS_SPLIT
constexpr unsigned kLeonAtlasAsset0=1000;
static struct {bool published;unsigned generation;} pl08_pack{true,1};
#include "../../../game/coarse_actor_atlas_split.inc"
// Routing sentinel only; actual unchanged capability is compiled in the SH4 gate.
extern "C" unsigned re4dc_actor_material_runs_capability(const Re4dcActorPlan*) {return 3u;}
#endif
using namespace re4dc_atlas_split;
static unsigned checks=0;
static int palettes(cModel*,const Re4dcActorPlan&,float* const*) { return 0; }
static Re4dcActorPlan source_plan(const Bundle& b) {
    // Foreign role descriptors are host fixture sentinels. Only the modified
    // role uses the exact selected source bytes. This is not live owner proof.
    static cModelInfo infos[9];static unsigned char hair_token;
    Re4dcActorPlan p{};p.appearance=b.appearance;p.count=b.appearance==0x100?8u:b.appearance==0x109?7u:9u;
    p.image=b.source_image;p.crc=b.source_crc;p.fnv=b.source_fnv;p.palette_bytes=1234;p.workspace_bytes=5678;p.palettes=palettes;
    p.material_count=b.appearance==0x109?1u:2u;p.materials[0].image=p.image;p.materials[0].crc=p.crc;p.materials[0].fnv=p.fnv;
    p.materials[1].image={&hair_token,nullptr,64,128,14,0xffffffffu,0};
    p.materials[1].material_flags=4;p.materials[1].mask_ref=0;p.materials[1].mask_same_uv=1;p.materials[1].wrap_s=p.materials[1].wrap_t=1;
    for(unsigned i=0;i<p.count;++i) {
        p.info[i]=&infos[i];p.input[i]=b.source;p.immutable_asset_id[i]=100+i;
#if RE4DC_ATLAS_DYNAMIC_PROBE
        if(b.appearance==0x109 && i==3)p.input[i]=case_data::neck_input();
#endif
        auto& r=p.runs[p.run_count++];r.role=i;r.material=i==7?1u:0u;r.immutable_asset_id=100+i;
        r.triangles=p.input[i].triangles;r.uv=p.input[i].uv;r.stream=p.input[i].stream;
        if(i==7) {auto& second=p.runs[p.run_count++];second=r;second.immutable_asset_id=200;}
    }
    return p;
}
static void unchanged(const Re4dcActorPlan& p,const std::vector<unsigned char>& before) {
    assert(before.size()==sizeof(p));assert(!std::memcmp(&p,before.data(),sizeof(p)));++checks;
}
static std::vector<unsigned char> bytes(const Re4dcActorPlan& p) {
    const auto* b=reinterpret_cast<const unsigned char*>(&p);return {b,b+sizeof(p)};
}
#if RE4DC_LEON_ATLAS_SPLIT
static bool same_run(const Re4dcActorPlannedRun& a,const Re4dcActorPlannedRun& b) {
    return a.role==b.role && a.material==b.material && a.immutable_asset_id==b.immutable_asset_id &&
        a.triangles==b.triangles && same(a.uv,b.uv) && same(a.stream,b.stream);
}
#endif
int main() {
    Bundle b=case_data::bundle();Qualified qualified{};auto source=source_plan(b),out=source;auto original=bytes(source),output=bytes(out);
#if !RE4DC_LEON_ATLAS_SPLIT
    assert(!qualify(b,qualified));
    assert(!bind(source,qualified,b.epoch,{1000,2000},out));unchanged(out,output);
    assert(!bind(source,qualified,b.epoch,{1000,2000},source));unchanged(source,original);
    std::printf("{\"enabled\":false,\"checks\":%u,\"output_unchanged\":true}\n",checks);return 0;
#else
    assert(qualify(b,qualified));++checks;
    assert(bind(source,qualified,b.epoch,{1000,1000+b.run_count-1},out));++checks;
    assert(out.count==source.count && out.appearance==source.appearance && out.palettes==source.palettes &&
           out.palette_bytes==source.palette_bytes && out.workspace_bytes==source.workspace_bytes);
    assert(out.run_count==source.run_count-1+b.run_count && out.material_count==source.material_count+1);++checks;
    for(unsigned i=0;i<source.count;++i) {
        assert(out.info[i]==source.info[i] && same(out.input[i],source.input[i]) && out.immutable_asset_id[i]==source.immutable_asset_id[i]);
    }
    for(unsigned i=0;i<source.material_count;++i)assert(!std::memcmp(&out.materials[i],&source.materials[i],sizeof(source.materials[i])));
    assert(same(out.image,source.image) && out.crc==source.crc && out.fnv==source.fnv);
    const auto& tile=out.materials[source.material_count];
    assert(same(tile.image,b.tile_image) && tile.crc==b.tile_crc && tile.fnv==b.tile_fnv && !tile.wrap_s && !tile.wrap_t && !tile.material_flags && !tile.blend && !tile.depth_mode);++checks;
    unsigned j=0;
    for(unsigned i=0;i<source.run_count;++i) {
        if(source.runs[i].role!=b.role)assert(same_run(source.runs[i],out.runs[j++]));
        else for(unsigned k=0;k<b.run_count;++k) {
            const auto& r=out.runs[j++];const auto& expected=b.runs[k];
            assert(r.role==b.role && r.material==(expected.isolated?source.material_count:0u) && r.immutable_asset_id==1000+k &&
                   r.triangles==expected.triangles && same(r.uv,expected.uv) && same(r.stream,expected.stream));
        }
    }
    assert(j==out.run_count);++checks;unchanged(source,original);
    Re4dcActorPlan projected{};
    assert(project(out,qualified,b.epoch,{1000,2000},projected));++checks;
    assert(projected.run_count==source.run_count && projected.material_count==source.material_count);
    for(unsigned i=0;i<source.run_count;++i)assert(same_run(projected.runs[i],source.runs[i]));
    auto corrupt=out;corrupt.runs[0].immutable_asset_id^=1;
    if(corrupt.runs[0].role!=b.role) { // unrelated IDs remain the ordinary owner's responsibility
        for(unsigned i=0;i<corrupt.run_count;++i)if(corrupt.runs[i].role==b.role){corrupt.runs[i].immutable_asset_id^=1;break;}
    }
    auto projection_destination=source;const auto projection_before=bytes(projection_destination);
    assert(!project(corrupt,qualified,b.epoch,{1000,2000},projection_destination));unchanged(projection_destination,projection_before);
    corrupt=out;corrupt.materials[corrupt.material_count-1].wrap_s=1;
    assert(!project(corrupt,qualified,b.epoch,{1000,2000},projection_destination));unchanged(projection_destination,projection_before);
#if RE4DC_ATLAS_RUNTIME_PROBE
    auto runtime=source;
    assert(re4dc_atlas_apply(&runtime));++checks;
    auto from_runtime=source;
    assert(re4dc_atlas_project(&runtime,&from_runtime));++checks;
    assert(from_runtime.run_count==source.run_count && from_runtime.material_count==source.material_count);
    unsigned runtime_crc=0,runtime_fnv=0;
    assert(re4dc_atlas_texture_key(&runtime.materials[runtime.material_count-1].image,&runtime_crc,&runtime_fnv));
    assert(runtime_crc==b.tile_crc && runtime_fnv==b.tile_fnv);++checks;
    if(b.appearance!=0x100) {
        re4dc_atlas_retire_pl08();const auto before_retired_project=bytes(from_runtime);
        assert(!re4dc_atlas_project(&runtime,&from_runtime));unchanged(from_runtime,before_retired_project);
        ++pl08_pack.generation; // identical source addresses, fresh publication
        assert(!re4dc_atlas_project(&runtime,&from_runtime));unchanged(from_runtime,before_retired_project);
        auto fresh=source;assert(re4dc_atlas_apply(&fresh));++checks;
        assert(re4dc_atlas_project(&fresh,&from_runtime));++checks;
        pl08_pack.published=false;
        assert(!re4dc_atlas_project(&fresh,&from_runtime));++checks;
    }
#endif
    auto reject=[&](const Re4dcActorPlan& p,unsigned epoch,ReservedIds ids) {
        auto destination=source;const auto old=bytes(destination);assert(!bind(p,qualified,epoch,ids,destination));unchanged(destination,old);
    };
    const ReservedIds ids{1000,2000};
    reject(source,0,ids);reject(source,b.epoch+1,ids);reject(source,b.epoch,{0,2000});
    reject(source,b.epoch,{1000,1000+b.run_count-2});reject(source,b.epoch,{std::numeric_limits<unsigned>::max(),0});
    auto p=source;p.appearance=0x10b;reject(p,b.epoch,ids);
    p=source;p.appearance=0x10a;p.count=1;reject(p,b.epoch,ids);
    p=source;p.input[b.role].positions.data++;reject(p,b.epoch,ids);
    p=source;p.crc^=1;reject(p,b.epoch,ids);
    p=source;p.material_count=kRe4dcActorMaterials;reject(p,b.epoch,ids);
    p=source;p.run_count=kRe4dcActorRuns;reject(p,b.epoch,ids);
    p=source;p.materials[0].wrap_s=1;reject(p,b.epoch,ids);
    p=source;p.materials[0].mask_same_uv=1;reject(p,b.epoch,ids);
    p=source;p.materials[0].depth_mode=1;reject(p,b.epoch,ids);
    p=source;p.materials[p.material_count++].image.pixels=b.tile_image.pixels;reject(p,b.epoch,ids);
    reject(source,b.epoch,{source.immutable_asset_id[b.role],2000});
    auto invalid=b;invalid.source.bones=118;Qualified bad{};assert(!qualify(invalid,bad));++checks;
    invalid=b;invalid.run_count=MaxSplitRuns+1;assert(!qualify(invalid,bad));++checks;
    invalid=b;invalid.runs[0].triangles++;assert(!qualify(invalid,bad));++checks;
    invalid=b;invalid.runs[0].stream.size=31;assert(!qualify(invalid,bad));++checks;
    // Selected optional LOD / pending mutation is outside this immutable proof.
    std::vector<unsigned char> lod(b.source.stream.data,b.source.stream.data+b.source.stream.size);
    lod[2]|=128;invalid=b;invalid.source.stream={lod.data(),lod.size()};assert(!qualify(invalid,bad));++checks;
    lod[2]&=127;lod[3]=1;assert(!qualify(invalid,bad));++checks;
    // A structurally valid UV perturbation must fail the exact affine proof.
    unsigned isolated=0;while(!b.runs[isolated].isolated)++isolated;
    std::vector<unsigned char> uv(b.runs[isolated].uv.data,b.runs[isolated].uv.data+b.runs[isolated].uv.size);
    uv[0]^=1;invalid=b;invalid.runs[isolated].uv={uv.data(),uv.size()};assert(!qualify(invalid,bad));++checks;
    unsigned dynamic_plans=0;
#if RE4DC_ATLAS_DYNAMIC_PROBE
    if(b.appearance==0x109) {
        re4dc_source::ChunkProof neck_proof{};
        assert(re4dc_source::preflight_chunk(source.input[3],neck_proof)==re4dc_source::BlobError::None);
        assert(same(out.input[3],source.input[3]) && out.input[3].triangles==37);++checks;
    }
#endif
#if RE4DC_ATLAS_DYNAMIC_PROBE
    // Each exact original hand blob replaces its current source role. The split
    // must copy the full role input, immutable ID, palette callback and run.
    for(unsigned h=0;h<case_data::hand_count;++h) {
        auto hand=source;const auto source_role=case_data::hand_role(h);
        const auto role=b.appearance==0x109?source_role-1:source_role;
        hand.input[role]=case_data::hand_input(h);hand.immutable_asset_id[role]=300+h;
        re4dc_source::ChunkProof proof{};
        assert(re4dc_source::preflight_chunk(hand.input[role],proof)==re4dc_source::BlobError::None);
        for(unsigned i=0;i<hand.run_count;++i)if(hand.runs[i].role==role) {
            auto& r=hand.runs[i];r.immutable_asset_id=hand.immutable_asset_id[role];
            r.uv=hand.input[role].uv;r.stream=hand.input[role].stream;r.triangles=hand.input[role].triangles;
        }
        const auto old=bytes(hand);auto result=hand;
        assert(bind(hand,qualified,b.epoch,ids,result));unchanged(hand,old);
        assert(same(result.input[role],hand.input[role]) && result.immutable_asset_id[role]==hand.immutable_asset_id[role] &&
               result.palettes==hand.palettes && result.palette_bytes==hand.palette_bytes && result.workspace_bytes==hand.workspace_bytes);
        unsigned matches=0;
        for(unsigned i=0;i<result.run_count;++i)if(result.runs[i].role==role) {
            const auto& r=result.runs[i];assert(r.immutable_asset_id==hand.immutable_asset_id[role] &&
                same(r.uv,hand.input[role].uv) && same(r.stream,hand.input[role].stream) && r.triangles==hand.input[role].triangles);++matches;
        }
        assert(matches==1);++checks;++dynamic_plans;
    }
#endif
    // Retire before source package reset. Even the same epoch/pointers decline.
    auto retired=qualified;retire(retired);auto after_retire=source;const auto retired_before=bytes(after_retire);
    assert(!bind(source,retired,b.epoch,ids,after_retire));unchanged(after_retire,retired_before);
    auto alias=source;assert(bind(alias,qualified,b.epoch,ids,alias));assert(alias.run_count==out.run_count);++checks;
    std::printf("{\"enabled\":true,\"checks\":%u,\"runs\":%u,\"materials\":%u,\"source_role_triangles\":%u,\"exact_original_hand_plans\":%u,\"actual_plan_type\":true,\"foreign_roles_are_host_sentinels\":true,\"runtime_admitted\":false}\n",
        checks,out.run_count,out.material_count,b.source.triangles,dynamic_plans);return 0;
#endif
}

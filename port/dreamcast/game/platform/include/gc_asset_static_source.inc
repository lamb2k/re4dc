// Included after the real Re4dcModelPart declaration. Memory-only class/use
// selection; original member role never supplies replacement ancestry.
#if RE4DC_GC_ASSET_GATE
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**);
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned);
namespace {
unsigned gcasset_static_consumer(const Re4dcModelPart* part){
    using namespace re4dc_gcasset;
    if(!part)return 1U<<SourceGeometry;
    const void* data=nullptr;ModelMember member{};
    const unsigned identity=re4dc_gcasset_model_identity(part->model,part->info,&data);
    if(identity==0xffffffffU)return 0;
    const bool bound=member_lookup(data,&member);
    const unsigned kind=identity>>24,id=(identity>>16)&255U;
    if(!bound && ((kind==1 && id==0x0a) || (kind==0 && id==0x4f)))return 0;
    return (1U<<SourceGeometry)|(re4dc_gcasset_weapon_consumer(part->model,part->info,
        bound?member.arc:0,bound?unsigned(member.family):unsigned(OtherOwner))?1U<<Weapon:0U);
}
struct GcStaticSourceScope {
    re4dc_gcasset::PayloadScope scope;
    GcStaticSourceScope(re4dc_gcasset::PayloadProof& proof,const void* owner,const Re4dcModelPart* part=nullptr)
        :scope(proof,owner,part?part->model:nullptr,part?part->info:nullptr,
            re4dc_gcasset::replay_use.serial!=0xffffffffU?re4dc_gcasset::replay_use.mask:gcasset_static_consumer(part)){
        auto& use=re4dc_gcasset::source_use;
        if(!use.mask){use.mask=1U<<re4dc_gcasset::SourceGeometry;use.serial=0;}
        // A full replacement package cannot authenticate a separately read
        // source colour array. Pose/motion remains an independent consumer.
        if(part && ((part->alpha_state&256) || (part->lighting &&
           (part->lighting->ambient_vertex || part->lighting->material_vertex))))use.serial=0;
    }
};
}
#endif

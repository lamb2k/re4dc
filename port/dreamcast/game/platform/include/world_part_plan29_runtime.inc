// Included beside Ps2World, under WORLD_PART_PLAN29 only.
#if RE4DC_WORLD_PREPARED09
extern "C" unsigned re4dc_room4_cell_incarnation(const void*,unsigned,unsigned);
#endif
#if RE4DC_WORLD_PREPARED09 && RE4DC_PS2_WORLD_SOURCE_OWNER
extern unsigned sourceWorldPackageGeneration;
#endif
#if RE4DC_WORLD_MUTATION31 && !RE4DC_PS2_WORLD_SOURCE_OWNER
extern unsigned sourceWorldPackageGeneration;
#endif
#if RE4DC_WORLD_MUTATION31
extern bool sourceWorldPackagePublished;
bool worldPackageCurrent();
#endif
namespace wplan29 {
using re4dc::wp29::Record;
extern "C" void* re4dc_world_part_plan29_alloc(unsigned);
void* allocation=nullptr;
const re4dc::wp29::Span* spans=nullptr;
const Record* records=nullptr;
const Ps2Part* bound_parts=nullptr;
const void* bound_mesh=nullptr;
unsigned bytes=0,meshes=0,loads=0,declines=0,planned=0,legacy=0;
#if RE4DC_WORLD_PREPARED09
unsigned incarnation=1,bound_incarnation=0,bound_room=~0U,bound_placements_count=0;
const void* bound_storage=nullptr;
const void* bound_placements=nullptr;
const re4dc::wp29::PlacementBounds* placement_boxes=nullptr;
unsigned box_count=0,allocation_bytes=0,allocation_generation=0,allocation_incarnation=0,bound_storage_incarnation=0;
unsigned refused_generation=~0U,unproven_return_bytes=0;
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_WORLD_MUTATION31
unsigned bound_package_generation=0;
#endif
bool current(unsigned token){
    unsigned generation=0;
#if RE4DC_WORLD_MUTATION31
    if(!worldPackageCurrent() || bound_package_generation!=sourceWorldPackageGeneration)return false;
#endif
    return token && token==incarnation && token==bound_incarnation && records && allocation &&
           re4dc_room4_live_generation(&generation) && generation==allocation_generation &&
           allocation_incarnation && re4dc_room4_cell_incarnation(allocation,allocation_bytes,generation)==allocation_incarnation &&
           bound_storage==ps2w.storage && bound_storage_incarnation &&
           re4dc_room4_cell_incarnation(bound_storage,ps2w.bytes,generation)==bound_storage_incarnation &&
           bound_parts==ps2w.parts && bound_mesh==ps2w.package.parts() &&
           bound_placements==ps2w.placements && bound_placements_count==ps2w.nplacements && bound_room==ps2w.room
#if RE4DC_PS2_WORLD_SOURCE_OWNER && !RE4DC_WORLD_MUTATION31
           && bound_package_generation==sourceWorldPackageGeneration
#endif
           ;
}
#endif
#if RE4DC_WORLD_PREPARED09
void close(){
    void* retired=allocation;const unsigned retired_bytes=allocation_bytes,retired_generation=allocation_generation,retired_token=allocation_incarnation;
    // Unpublish everything before an allocator/free callback can reenter.
    if(incarnation)++incarnation;
    allocation=nullptr;spans=nullptr;records=nullptr;bound_parts=nullptr;bound_mesh=nullptr;bytes=meshes=0;
    bound_incarnation=0;bound_storage=bound_placements=nullptr;bound_storage_incarnation=0;
    placement_boxes=nullptr;box_count=0;bound_room=~0U;bound_placements_count=0;
    allocation_bytes=allocation_generation=allocation_incarnation=0;
    // Generation alone cannot distinguish same-generation address/size reuse.
    if(retired && retired_token && re4dc_room4_cell_incarnation(retired,retired_bytes,retired_generation)==retired_token)
        re4dc_static_free(retired);
}
#else
void close(){
    if(allocation)re4dc_static_free(allocation);
    allocation=nullptr;spans=nullptr;records=nullptr;bound_parts=nullptr;bound_mesh=nullptr;bytes=meshes=0;
}
#endif

#if RE4DC_WORLD_PREPARED09
void open(){
    close();
#if RE4DC_WORLD_MUTATION31
    // The package may have been overwritten at the same address. Refuse
    // before measure(), parts(), or any prepared payload write.
    if(!worldPackageCurrent()){
        ++declines;return;
    }
#endif
    // A free callback may already have published a replacement. Do not
    // overwrite that newer owner when the outer call resumes.
    if(allocation || records)return;
    constexpr bool foliage=
#if defined(RE4DC_FOLIAGE_TRIM)
        true;
#else
        false;
#endif
    constexpr bool trans=
#if defined(RE4DC_TRANS_POLICY)
        true;
#else
        false;
#endif
    re4dc::wp29::Layout layout{};re4dc::wp29::BoundsLayout extra{};
    const int before=re4dc_static_heap_free();const char* why=nullptr;unsigned generation=0;
    const unsigned expected_plan=incarnation,expected_room=ps2w.room,expected_count=ps2w.nplacements,expected_bytes=ps2w.bytes;
    const void* expected_storage=ps2w.storage;const auto* expected_parts=ps2w.parts;
    const auto* expected_mesh=ps2w.package.parts();const auto* expected_placements=ps2w.placements;
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_WORLD_MUTATION31
    const unsigned expected_package=sourceWorldPackageGeneration;
#endif
    unsigned package_token=0;
    if(!incarnation)why="incarnation-exhausted";
    else if(!re4dc_room4_live_generation(&generation) ||
            !(package_token=re4dc_room4_cell_incarnation(expected_storage,expected_bytes,generation)))why="room/package-lifetime";
    else if(refused_generation==generation)why="unproven-publication";
    else if(!re4dc::wp29::measure(ps2w.package,ps2w.parts,foliage,trans,layout))why="layout/capacity";
    else if(before<0 || unsigned(before)<layout.bytes+31U+re4dc::wp29::kHeapFloor)why="headroom";
    else {
        if(refused_generation!=generation)unproven_return_bytes=0;
        unsigned budget=unsigned(before)-31U-re4dc::wp29::kHeapFloor;
        if(budget>re4dc::wp29::kMaxBytes)budget=re4dc::wp29::kMaxBytes;
        extra=re4dc::wp29::optional_bounds(layout.bytes,ps2w.nplacements,budget);
        const auto publication_current=[&](){
            unsigned now=0;
#if RE4DC_WORLD_MUTATION31
            if(!worldPackageCurrent())return false;
#endif
            return incarnation==expected_plan && !allocation && !records && re4dc_room4_live_generation(&now) && now==generation &&
                ps2w.storage==expected_storage && ps2w.bytes==expected_bytes && ps2w.parts==expected_parts &&
                ps2w.package.parts()==expected_mesh && ps2w.placements==expected_placements &&
                ps2w.room==expected_room && ps2w.nplacements==expected_count &&
                re4dc_room4_cell_incarnation(expected_storage,expected_bytes,generation)==package_token
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_WORLD_MUTATION31
                && sourceWorldPackageGeneration==expected_package
#endif
                ;
        };
        for(unsigned attempt=0;attempt<2;++attempt){
            if(!publication_current()){why="publication-changed";break;}
            const unsigned requested=extra.bytes+31U;
            void* candidate=re4dc_world_part_plan29_alloc(requested);
            const unsigned token=candidate?re4dc_room4_cell_incarnation(candidate,requested,generation):0;
            const int after=re4dc_static_heap_free();
            // Validate expected publication after every callback edge and
            // before the first write through the returned allocation.
            if(!publication_current() || (candidate && (!token || re4dc_room4_cell_incarnation(candidate,requested,generation)!=token))){
                refused_generation=generation;
                if(candidate && candidate!=allocation)unproven_return_bytes=requested;
                why="unproven-publication";break; // never free an unproven recycled pointer
            }
            if(!candidate || after<int(re4dc::wp29::kHeapFloor)){
                if(candidate && token && re4dc_room4_cell_incarnation(candidate,requested,generation)==token)re4dc_static_free(candidate);
                if(extra.count){extra={layout.bytes,0,layout.bytes};continue;}
                why="heap4";break;
            }
            auto* aligned=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(candidate)+31U)&~std::uintptr_t(31U));
            if(!re4dc::wp29::compile(aligned,layout.bytes,ps2w.package,ps2w.parts,foliage,trans,layout)){
                if(re4dc_room4_cell_incarnation(candidate,requested,generation)==token)re4dc_static_free(candidate);
                why="compile";break;
            }
            auto* boxes=extra.count?reinterpret_cast<re4dc::wp29::PlacementBounds*>(static_cast<unsigned char*>(aligned)+extra.offset):nullptr;
            for(unsigned i=0;i<extra.count;++i){
                const auto& pl=ps2w.placements[i];const auto& mesh=ps2w.package.meshes()[pl.mesh];
                boxes[i]=re4dc::wp29::placement_bounds(pl.affine,mesh.bounds_min,mesh.bounds_max);
            }
            allocation=candidate;allocation_bytes=requested;allocation_generation=generation;allocation_incarnation=token;
            spans=static_cast<const re4dc::wp29::Span*>(aligned);
            records=reinterpret_cast<const Record*>(static_cast<const unsigned char*>(aligned)+layout.offset);
            bound_parts=ps2w.parts;bound_mesh=ps2w.package.parts();meshes=layout.meshes;bytes=requested;
            bound_storage=ps2w.storage;bound_storage_incarnation=package_token;bound_placements=ps2w.placements;
            bound_placements_count=ps2w.nplacements;bound_room=ps2w.room;
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_WORLD_MUTATION31
            bound_package_generation=sourceWorldPackageGeneration;
#endif
            placement_boxes=boxes;box_count=extra.count;bound_incarnation=incarnation;++loads;break;
        }
    }
    if(why)++declines; // newer reentrant publication, if any, stays untouched
    re4dc_log("WPLAN29 prepared room=%03x status=%s bytes=%u bounds=%u incarnation=%u unproven=%u heap=%d->%d\n",
        ps2w.room,why?why:"ok",bytes,box_count,bound_incarnation,unproven_return_bytes,before,re4dc_static_heap_free());
}
const re4dc::wp29::PlacementBounds* bounds(unsigned placement,unsigned token){
    if(!current(token) || !placement_boxes || placement>=box_count || !(placement_boxes[placement].half[0]>=0.0f))return nullptr;
    return placement_boxes+placement;
}
#else
void open(){
    close();
    constexpr bool foliage=
#if defined(RE4DC_FOLIAGE_TRIM)
        true;
#else
        false;
#endif
    constexpr bool trans=
#if defined(RE4DC_TRANS_POLICY)
        true;
#else
        false;
#endif
    re4dc::wp29::Layout layout;
    const int before=re4dc_static_heap_free();
    const char* why=nullptr;
    if(!re4dc::wp29::measure(ps2w.package,ps2w.parts,foliage,trans,layout))why="layout/capacity";
    else if(before<0 || unsigned(before)<layout.bytes+31U+re4dc::wp29::kHeapFloor)why="headroom";
    else if(!(allocation=re4dc_world_part_plan29_alloc(layout.bytes+31U)))why="heap4";
    else {
        auto* aligned=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(allocation)+31U)&~std::uintptr_t(31U));
        if(re4dc_static_heap_free()<int(re4dc::wp29::kHeapFloor))why="post-headroom";
        else if(!re4dc::wp29::compile(aligned,layout.bytes,ps2w.package,ps2w.parts,foliage,trans,layout))why="compile";
        else {
            spans=static_cast<const re4dc::wp29::Span*>(aligned);
            records=reinterpret_cast<const Record*>(static_cast<const unsigned char*>(aligned)+layout.offset);
            bound_parts=ps2w.parts;bound_mesh=ps2w.package.parts();meshes=layout.meshes;bytes=layout.bytes+31U;++loads;
        }
    }
    if(why){close();++declines;}
    re4dc_log("WPLAN29 open room=%03x status=%s bytes=%u records=%u heap=%d->%d loads=%u declines=%u\n",
        ps2w.room,why?why:"ok",bytes,why?0U:layout.records,before,re4dc_static_heap_free(),loads,declines);
}
#endif
const Record* run(unsigned mesh,unsigned pass,unsigned& count){
#if RE4DC_WORLD_PREPARED09
    if(!current(bound_incarnation))return nullptr;
#endif
    if(!records || bound_parts!=ps2w.parts || bound_mesh!=ps2w.package.parts() || mesh>=meshes || pass>=3)return nullptr;
    const auto& span=spans[3U*mesh+pass];count=span.count;return records+span.first;
}
}

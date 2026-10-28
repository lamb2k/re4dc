// Included beside Ps2World, under WORLD_PART_PLAN29 only.
namespace wplan29 {
using re4dc::wp29::Record;
extern "C" void* re4dc_world_part_plan29_alloc(unsigned);
void* allocation=nullptr;
const re4dc::wp29::Span* spans=nullptr;
const Record* records=nullptr;
const Ps2Part* bound_parts=nullptr;
const void* bound_mesh=nullptr;
unsigned bytes=0,meshes=0,loads=0,declines=0,planned=0,legacy=0;
void close(){
    if(allocation)re4dc_static_free(allocation);
    allocation=nullptr;spans=nullptr;records=nullptr;bound_parts=nullptr;bound_mesh=nullptr;bytes=meshes=0;
}
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
const Record* run(unsigned mesh,unsigned pass,unsigned& count){
    if(!records || bound_parts!=ps2w.parts || bound_mesh!=ps2w.package.parts() || mesh>=meshes || pass>=3)return nullptr;
    const auto& span=spans[3U*mesh+pass];count=span.count;return records+span.first;
}
}

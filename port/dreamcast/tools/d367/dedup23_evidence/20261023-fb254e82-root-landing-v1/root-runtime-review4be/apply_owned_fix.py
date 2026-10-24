from pathlib import Path
p=Path('/root/probe/dedup-prefetch-context23/port/dreamcast/game/platform/native_static.cpp')
s=p.read_text();old='''    const re4dc::room::CompactVertex12* emit_corners(const re4dc::room::Meshlet& l,const Pick& pk){
        const auto* base=package.vertices()+l.first_vertex;
        if(!package.indexed(l))return base;'''
new='''    const re4dc::room::CompactVertex12* emit_corners(const re4dc::room::Meshlet& l,const Pick& pk){
        const auto* base=package.vertices()+l.first_vertex;
#if RE4DC_SCENERY_DEDUP==3
        // Match corners(): refresh or clear the decoder before every early return.
        const unsigned rep=package.repeat_count(l);
        dd_base=rep?base:nullptr;dd_unique=l.vertex_count-rep;dd_count=l.vertex_count;
#endif
        if(!package.indexed(l))return base;'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)

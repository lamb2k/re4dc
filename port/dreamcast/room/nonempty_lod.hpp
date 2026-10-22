#ifndef RE4DC_ROOM_NONEMPTY_LOD_HPP
#define RE4DC_ROOM_NONEMPTY_LOD_HPP

namespace re4dc { namespace room {
// A generated empty reduction cannot replace required visible PS2 geometry.
// The caller has already selected the coarsest level within its error policy.
// Finer levels retain that policy; an authored empty base stays empty.
template<class Level>
inline unsigned nonempty_lod(const Level* levels,unsigned count,unsigned selected){
    if(!levels || !count || selected>=count)return 0;
    while(selected && !levels[selected].meshlet_count)--selected;
    return selected;
}
}}
#endif

#pragma once
#include "effect_strip_geometry21.hpp"
namespace re4dc::cloth11 {
// Corners TL,BL,TR,BR are the source strip. The second triangle swaps its first
// two vertices for strip parity; a GX_QUADS diagonal would be different.
inline unsigned cell(const Re4dcEffectQuad& q,pvr_vertex_t (&out)[12]){
    const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
    render::ClipParameters clip{near,far,RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,effect_strip21::project,const_cast<Re4dcEffectQuad*>(&q)};
    render::RenderVertex v[4]{};
    for(unsigned i=0;i<4;++i){auto& p=v[i].position;
        p.world_x=p.x=q.positions[i][0];p.world_y=p.y=q.positions[i][1];p.world_z=p.z=q.positions[i][2];p.depth=-p.world_z;
        if(p.depth>=near)effect_strip21::project(p.x,p.y,p.z,clip.context);
        v[i].u=q.u[i];v[i].v=q.v[i];v[i].light_red=v[i].light_green=v[i].light_blue=1;}
    constexpr unsigned triangles[2][3]={{0,1,2},{2,1,3}};unsigned used=0;
    for(const auto& ix:triangles){const render::RenderVertex tri[]={v[ix[0]],v[ix[1]],v[ix[2]]};
        used+=3*render::clip_projected_triangle(tri,out+used,0,clip);}
    for(unsigned i=0;i<used;++i)out[i].argb=q.color;
    return used;
}
}

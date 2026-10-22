#pragma once
#include "native_ui.h"
#include "re4dc_screen.h"
#include "../../../room/pvr_geometry.hpp"
namespace re4dc::effect_strip21 {
inline void project(float& x,float& y,float& z,void* context){
    const auto& q=*static_cast<const Re4dcEffectQuad*>(context);
    const float* p=q.projection;const float* v=q.viewport;const float inv=1.0f/-z;
    x=(v[2]*.5f*(p[1]*x+p[2]*z)*inv+v[0]+v[2]*.5f)*RE4DC_SCREEN_WF/v[2];
    y=(-v[3]*.5f*(p[3]*y+p[4]*z)*inv+v[1]+v[3]*.5f)*RE4DC_SCREEN_HF/v[3];z=inv;
}
inline unsigned vertices(const Re4dcEffectQuad& q,pvr_vertex_t (&out)[12]){
    if(q.src>7 || q.dst>7 || q.wrap_s>1 || q.wrap_t>1 || q.projection[0]!=0 || q.viewport[2]<=0 || q.viewport[3]<=0)return 0;
    for(float f:q.projection)if(!render::is_finite(f))return 0;
    for(float f:q.viewport)if(!render::is_finite(f))return 0;
    for(unsigned i=0;i<4;++i){for(float f:q.positions[i])if(!render::is_finite(f))return 0;
        if(!render::is_finite(q.u[i]) || !render::is_finite(q.v[i]))return 0;}
    const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
    if(!render::is_finite(near) || !render::is_finite(far) || near<=0 || far<=near)return 0;
    render::ClipParameters clip{near,far,RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,project,const_cast<Re4dcEffectQuad*>(&q)};
    render::RenderVertex v[4]{};
    for(unsigned i=0;i<4;++i){auto& p=v[i].position;
        p.world_x=p.x=q.positions[i][0];p.world_y=p.y=q.positions[i][1];p.world_z=p.z=q.positions[i][2];p.depth=-p.world_z;
        if(p.depth>=near)project(p.x,p.y,p.z,clip.context);
        v[i].u=q.u[i];v[i].v=q.v[i];v[i].light_red=v[i].light_green=v[i].light_blue=1;}
    // Preserve the source GX_QUADS diagonal; a strip's alternative diagonal
    // changes perspective UVs when the four live corners are not coplanar.
    constexpr unsigned triangles[2][3]={{0,1,2},{0,2,3}};unsigned used=0;
    for(const auto& ix:triangles){const render::RenderVertex tri[]={v[ix[0]],v[ix[1]],v[ix[2]]};
        used+=3*render::clip_projected_triangle(tri,out+used,0,clip);}
    for(unsigned i=0;i<used;++i)out[i].argb=q.color;
    return used;
}
} // namespace re4dc::effect_strip21

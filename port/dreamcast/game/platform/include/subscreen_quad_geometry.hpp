#pragma once
// Reuse the accepted model clipper for source inventory colour quads.
#include "native_ui.h"
#include "re4dc_screen.h"
#include "../../../room/pvr_geometry.hpp"
namespace re4dc::subscreen {
inline void project(float& x,float& y,float& z,void* context){
    const auto& q=*static_cast<const Re4dcSubscreenQuad*>(context);
    const float* p=q.projection;const float* v=q.viewport;const float inv=1.0f/-z;
    x=(v[2]*.5f*(p[1]*x+p[2]*z)*inv+v[0]+v[2]*.5f)*RE4DC_SCREEN_WF/v[2];
    y=(-v[3]*.5f*(p[3]*y+p[4]*z)*inv+v[1]+v[3]*.5f)*RE4DC_SCREEN_HF/v[3];
    z=inv;
}
// At most two clipped triangles for each of the source strip's two triangles.
inline unsigned vertices(const Re4dcSubscreenQuad& q,pvr_vertex_t (&out)[12]){
    if(q.blend>3 || q.projection[0]!=0 || q.viewport[2]<=0 || q.viewport[3]<=0)return 0;
    for(float f:q.projection)if(!render::is_finite(f))return 0;
    for(float f:q.viewport)if(!render::is_finite(f))return 0;
    for(const auto& p:q.positions)for(float f:p)if(!render::is_finite(f))return 0;
    const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
    if(!render::is_finite(near) || !render::is_finite(far) || near<=0 || far<=near)return 0;
    render::ClipParameters clip{near,far,RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,project,const_cast<Re4dcSubscreenQuad*>(&q)};
    render::RenderVertex v[4]{};
    for(unsigned i=0;i<4;++i){
        auto& p=v[i].position;
        p.world_x=p.x=q.positions[i][0];p.world_y=p.y=q.positions[i][1];p.world_z=p.z=q.positions[i][2];
        p.depth=-p.world_z;
        if(p.depth>=near)project(p.x,p.y,p.z,clip.context);
        v[i].light_red=v[i].light_green=v[i].light_blue=1;
    }
    constexpr unsigned strips[2][3]={{0,1,2},{2,1,3}};
    unsigned used=0;
    for(const auto& indices:strips){
        const render::RenderVertex tri[]={v[indices[0]],v[indices[1]],v[indices[2]]};
        used+=3*render::clip_projected_triangle(tri,out+used,0,clip);
    }
    const unsigned argb=(q.color>>8)|(q.color<<24);
    for(unsigned i=0;i<used;++i)out[i].argb=argb;
    return used;
}
// Reuse the accepted native laser's depth clipping and perpendicular strip.
// Subscreen lines have uniform color, source GX width and no depth writes/fog.
inline unsigned line_vertices(const Re4dcSubscreenQuad& q,unsigned width,pvr_vertex_t (&out)[12]){
    if(!width || width>255 || q.blend>3 || q.projection[0]!=0 || q.viewport[2]<=0 || q.viewport[3]<=0)return 0;
    for(float f:q.projection)if(!render::is_finite(f))return 0;
    for(float f:q.viewport)if(!render::is_finite(f))return 0;
    for(unsigned i=0;i<2;++i)for(float f:q.positions[i])if(!render::is_finite(f))return 0;
    const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
    if(!render::is_finite(near) || !render::is_finite(far) || near<=0 || far<=near)return 0;
    const float d0=-q.positions[0][2],d1=-q.positions[1][2],dd=d1-d0;
    float t0=0,t1=1;
    if(dd==0){if(d0<near || d0>far)return 0;}
    else {
        float enter=(near-d0)/dd,leave=(far-d0)/dd;
        if(enter>leave){const float tmp=enter;enter=leave;leave=tmp;}
        if(enter>t0)t0=enter;
        if(leave<t1)t1=leave;
        if(t0>t1)return 0;
    }
    float p[2][3];
    for(unsigned i=0;i<2;++i){
        const float t=i?t1:t0;
        for(unsigned j=0;j<3;++j)p[i][j]=q.positions[0][j]+(q.positions[1][j]-q.positions[0][j])*t;
        project(p[i][0],p[i][1],p[i][2],const_cast<Re4dcSubscreenQuad*>(&q));
        for(float f:p[i])if(!render::is_finite(f))return 0;
    }
    const float dx=p[1][0]-p[0][0],dy=p[1][1]-p[0][1];
    const float length=std::sqrt(dx*dx+dy*dy);
    if(!render::is_finite(length) || length<.0001f)return 0;
    const float half_width=float(width)/12.0f;
    const float ox=-dy*(half_width/length),oy=dx*(half_width/length);
    if((p[0][0]<-half_width && p[1][0]<-half_width) ||
       (p[0][0]>RE4DC_SCREEN_WF+half_width && p[1][0]>RE4DC_SCREEN_WF+half_width) ||
       (p[0][1]<-half_width && p[1][1]<-half_width) ||
       (p[0][1]>RE4DC_SCREEN_HF+half_width && p[1][1]>RE4DC_SCREEN_HF+half_width))return 0;
    const unsigned argb=(q.color>>8)|(q.color<<24);
    for(unsigned i=0;i<4;++i){
        const unsigned end=i/2;const float side=i&1?-1.0f:1.0f;
        out[i]={i==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX,p[end][0]+side*ox,p[end][1]+side*oy,p[end][2],0,0,argb,0};
    }
    return 4;
}
} // namespace re4dc::subscreen

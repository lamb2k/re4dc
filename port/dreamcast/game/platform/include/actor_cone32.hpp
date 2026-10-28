#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>

// Build32: conservative admission for the existing actor cone proof. A failed
// guard keeps the normal vertex path. This is not a new cull/material policy.
namespace re4dc::cone32 {
enum PartWhy : unsigned { Cull, Transient, Mode, Source, Table, PartReasons };
struct Counters {
    unsigned admitted=0, declined=0, why[PartReasons]{};
    unsigned tested=0, rejected=0, near=0, numeric=0, empty=0, split_skipped=0;
    void decline(PartWhy reason) { ++declined; ++why[reason]; }
};
// Stored beside a cone table, in the same original stream allocation. It owns
// no memory and cannot outlive that stream. Palette matrices remain live state.
struct SourceIdentity {
    std::uintptr_t info=0, positions=0;
    unsigned count=0, stride=0;
    bool matches(const void* current_info,const void* current_positions,unsigned current_count,unsigned current_stride)const {
        return info==reinterpret_cast<std::uintptr_t>(current_info) && positions==reinterpret_cast<std::uintptr_t>(current_positions) &&
               count==current_count && stride==current_stride;
    }
};
struct Guard {
    float depth[4]{};
    float near=0, eye_error=0;
    bool ready=false;
};
inline bool finite(float x) {
    std::uint32_t u; std::memcpy(&u,&x,sizeof(u));
    return (u&0x7f800000U)!=0x7f800000U;
}
inline bool bounded(float x,float limit) { return finite(x) && std::fabs(x)<=limit; }
// The cofactor array is the adjugate, in row order, already computed by
// abc_eye. Reject ill-conditioned or excessively large transforms before the
// inverse eye can become authority. The extra radius bounds arithmetic error
// in that inverse and the two-stage palette/screen transform conservatively.
inline bool prepare(const float a[9],const float t[3],const float adj[9],
                    float det,const float eye[3],float near,Guard& out) {
    out.ready=false;
    if(!bounded(near,1.0e8f) || !(near>0.f) || !bounded(det,1.0e30f) || !(std::fabs(det)>1.0e-20f))return false;
    float anorm=0.f,cnorm=0.f,emax=1.f,residual=0.f;
    for(unsigned r=0;r<3;++r) {
        float ar=0.f,cr=0.f,mag=0.f,res=t[r];
        if(!bounded(t[r],1.0e10f) || !bounded(eye[r],1.0e8f))return false;
        if(std::fabs(eye[r])>emax)emax=std::fabs(eye[r]);
        for(unsigned c=0;c<3;++c) {
            if(!bounded(a[3*r+c],1.0e8f) || !bounded(adj[3*r+c],1.0e17f) || !bounded(eye[c],1.0e8f))return false;
            ar+=std::fabs(a[3*r+c]);cr+=std::fabs(adj[3*r+c]);
            const float product=a[3*r+c]*eye[c];res+=product;mag+=std::fabs(product);
        }
        if(ar>anorm)anorm=ar;
        if(cr>cnorm)cnorm=cr;
        // 64 ulps of the absolute input sum also covers FTRV/FMAC reassociation.
        const float err=std::fabs(res)+(mag+std::fabs(t[r])+1.f)*(64.f/8388608.f);
        if(err>residual)residual=err;
    }
    const float inverse=cnorm/std::fabs(det),condition=anorm*inverse;
    if(!finite(inverse) || !finite(condition) || !(condition<=4096.f))return false;
    const float error=inverse*residual+(emax+65536.f)*condition*(64.f/8388608.f)+2.f;
    if(!finite(error) || error>65536.f)return false;
    out.depth[0]=a[6];out.depth[1]=a[7];out.depth[2]=a[8];out.depth[3]=t[2];
    out.near=near;out.eye_error=error;out.ready=true;return true;
}
enum Result : unsigned { Keep, Reject, Near, Numeric, Empty };
template<class Cone,class Eye>
inline Result test(const Cone& cone,const Eye& eye,const Guard& guard,float cosine,float sine2) {
    if(!cone.k || cone.k>56U)return Empty;
    if(!guard.ready || !bounded(cosine,1.f) || !bounded(sine2,1.f) || cosine<0.f || sine2<0.f)return Numeric;
    // The old check mode only verifies triangles entirely beyond near. Make
    // that same domain mandatory for the actual early reject, including the
    // sphere's quantization and inverse-eye error margins.
    float depth=guard.depth[3],depth_mag=std::fabs(depth),row=0.f;
    for(unsigned a=0;a<3;++a) {
        const float v=guard.depth[a]*float(cone.c[a]);depth+=v;depth_mag+=std::fabs(v);row+=std::fabs(guard.depth[a]);
    }
    const float radius=float(cone.r)+guard.eye_error;
    const float span=radius*row;
    const float margin=(depth_mag+span+guard.near+1.f)*(64.f/8388608.f)+0.001f;
    if(!finite(depth) || !finite(span) || !(depth-span>guard.near+margin))return Near;
    const float ax=float(cone.a[0]),ay=float(cone.a[1]),az=float(cone.a[2]);
    const float len2=ax*ax+ay*ay+az*az;
    if(!(len2>0.f) || !finite(len2) || !bounded(eye.s,1.f) || std::fabs(eye.s)!=1.f)return Numeric;
    const float wx=float(cone.c[0])-eye.e[0],wy=float(cone.c[1])-eye.e[1],wz=float(cone.c[2])-eye.e[2];
    if(!bounded(wx,1.0e8f) || !bounded(wy,1.0e8f) || !bounded(wz,1.0e8f))return Numeric;
    // The builder measures cone angles after axis quantization and exact
    // normalization. Use that axis, rather than assuming its length is 32767.
    const float dw=eye.s*(ax*wx+ay*wy+az*wz)/std::sqrt(len2);
    const float length2=wx*wx+wy*wy+wz*wz;
    const float rest=length2-dw*dw;
    const float arithmetic=(std::fabs(dw)+radius+std::sqrt(length2)+1.f)*(64.f/8388608.f);
    const float t=dw*cosine-radius-arithmetic;
    if(!(t>0.f))return Keep;
    const float lhs=t*t,rhs=sine2*(rest>0.f?rest:0.f);
    if(!finite(lhs) || !finite(rhs))return Numeric;
    return lhs>rhs+(lhs+rhs+1.f)*(64.f/8388608.f)?Reject:Keep;
}
} // namespace re4dc::cone32

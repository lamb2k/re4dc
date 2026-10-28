// SCENERY_SELECT_LEAN2: exact chunk-selection setup with fewer transient reads
// and writes. Included inside namespace lean; no world data format changes.
//
// Read packed bounds directly. The old caller stored six converted floats that
// an out-of-line box helper immediately read back. Keep every original matrix
// and plane expression, including its comparison thresholds and operation order.
#if RE4DC_SCENERY_RECORD_SPLIT
template<class MeshletBounds>
inline int box_mask_grid(const MeshletBounds& l,const float* m,const float* am,
#else
inline int box_mask_grid(const re4dc::room::Meshlet& l,const float* m,const float* am,
#endif
        float near_distance,float far_distance){
    const float l0=float(l.bounds_min[0]),l1=float(l.bounds_min[1]),l2=float(l.bounds_min[2]);
    const float h0=float(l.bounds_max[0]),h1=float(l.bounds_max[1]),h2=float(l.bounds_max[2]);
    const float cx=(l0+h0)*0.5f,cy=(l1+h1)*0.5f,cz=(l2+h2)*0.5f;
    const float ex=(h0-l0)*0.5f,ey=(h1-l1)*0.5f,ez=(h2-l2)*0.5f;
    const float vz=m[8]*cx+m[9]*cy+m[10]*cz+m[11],rz=am[6]*ex+am[7]*ey+am[8]*ez;
    if(-vz+rz<near_distance || -vz-rz>far_distance)return -1;
    const float vx=m[0]*cx+m[1]*cy+m[2]*cz+m[3],rx=am[0]*ex+am[1]*ey+am[2]*ez;
    const float vy=m[4]*cx+m[5]*cy+m[6]*cz+m[7],ry=am[3]*ex+am[4]*ey+am[5]*ez;
    const Side& S=side;int mask=0;
    for(unsigned k=0;k<4;++k){
        const float v=k<2?vx:vy,r=k<2?rx:ry;
        const float sv=S.a[k]*v+S.c[k]*vz,t=S.aa[k]*r+S.ac[k]*rz;
        if(sv+t<-0.0001f)return -1;
        if(!(sv-t>0.0f))mask|=1<<k;
    }
    if(!(-vz-rz>near_distance))mask|=16;
    return mask;
}
#if RE4DC_SG_SELECT_LEAN
#if RE4DC_SCENERY_RECORD_SPLIT
template<class MeshletBounds>
inline int box_mask_grid_lean(const MeshletBounds& l,const float* m,const float* am,
#else
inline int box_mask_grid_lean(const re4dc::room::Meshlet& l,const float* m,const float* am,
#endif
        float near_distance,float far_distance){
    const float l0=float(l.bounds_min[0]),l1=float(l.bounds_min[1]),l2=float(l.bounds_min[2]);
    const float h0=float(l.bounds_max[0]),h1=float(l.bounds_max[1]),h2=float(l.bounds_max[2]);
    const float cx=(l0+h0)*0.5f,cy=(l1+h1)*0.5f,cz=(l2+h2)*0.5f;
    const float ex=(h0-l0)*0.5f,ey=(h1-l1)*0.5f,ez=(h2-l2)*0.5f;
    const float vz=m[8]*cx+m[9]*cy+m[10]*cz+m[11],rz=am[6]*ex+am[7]*ey+am[8]*ez;
    if(-vz+rz<near_distance || -vz-rz>far_distance)return -1;
    const float vx=m[0]*cx+m[1]*cy+m[2]*cz+m[3],rx=am[0]*ex+am[1]*ey+am[2]*ez;
    const float vy=m[4]*cx+m[5]*cy+m[6]*cz+m[7],ry=am[3]*ex+am[4]*ey+am[5]*ez;
    const Side& S=side;int mask=0;
#define RE4DC_SG_BM_PLANE(k,v,r) { \
        const float sv=S.a[k]*v+S.c[k]*vz,t=S.aa[k]*r+S.ac[k]*rz; \
        if(sv+t<-0.0001f)return -1; \
        if(!(sv-t>0.0f))mask|=1<<k; }
    RE4DC_SG_BM_PLANE(0,vx,rx) RE4DC_SG_BM_PLANE(1,vx,rx) RE4DC_SG_BM_PLANE(2,vy,ry) RE4DC_SG_BM_PLANE(3,vy,ry)
#undef RE4DC_SG_BM_PLANE
    if(!(-vz-rz>near_distance))mask|=16;
    return mask;
}
// chunk_ok limits groups to eight. Return the final Pick fields directly:
// group bits [0:7], low corner [8:15], high corner [16:23], culled count [24:27],
// kept count [28:31]. No temporary strip ranges on the ordinary path.
inline unsigned sg_pick_pack(unsigned bits,unsigned lo,unsigned hi,unsigned cut,unsigned nr){
    return bits|(lo<<8)|(hi<<16)|(cut<<24)|(nr<<28);
}
inline unsigned sg_pick_ranges(const std::uint16_t* g,unsigned n,const std::uint16_t* r0,
        const std::uint16_t* r1,unsigned lo,unsigned hi,unsigned cut,unsigned nr){
    unsigned bits=0,prev=0,j=0;
    for(unsigned k=0;k<n && j<nr;++k){
        const unsigned gend=g[8*k+6];
        if(gend==prev)continue;
        if(r0[j]==prev && r1[j]==gend){bits|=1U<<k;++j;}
        prev=gend;
    }
    return sg_pick_pack(bits,lo,hi,cut,nr);
}
// The producer writes increasing nonempty strip ends, but the package validator
// does not enforce this. Preserve the old range matching even for a decreasing
// sequence by rerunning the original helper before publishing any result.
__attribute__((noinline)) unsigned sg_pick_fallback_lean(const std::uint16_t* g,unsigned n,
        const SgPlane* planes,unsigned mask){
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if(mask)re4dc::dfa26::hit(re4dc::dfa26::WorldSgMalformed);
#endif
    std::uint16_t r0[8],r1[8];unsigned lo,hi,cut;
    const unsigned nr=sg_select_lean(g,n,planes,mask,r0,r1,lo,hi,cut);
    return sg_pick_ranges(g,n,r0,r1,lo,hi,cut,nr);
}
// One crossed plane: retain its four coefficients and three corner offsets for
// the complete group walk. The low/high count nibbles cannot carry for n<=8.
__attribute__((noinline)) unsigned sg_pick_one_lean(const std::uint16_t* g,unsigned n,const SgPlane* p){
    const std::uint16_t* const first=g;
    const float c0=p->c0,c1=p->c1,c2=p->c2,d=p->d;
    const int o0=p->o0,o1=p->o1,o2=p->o2;
    unsigned prev=0,counts=0,vlo=255,vhi=0,bits=0,bit=1;
    for(const std::uint16_t* const end=g+8*n;g!=end;g+=8,bit<<=1){
        const unsigned gend=g[6];
        if(gend<=prev){
            if(gend==prev)continue;
            return sg_pick_fallback_lean(first,n,p,1U);
        }
        const char* const gb=reinterpret_cast<const char*>(g);
        const float x0=float(*reinterpret_cast<const std::uint16_t*>(gb+o0));
        const float x1=float(*reinterpret_cast<const std::uint16_t*>(gb+o1));
        const float x2=float(*reinterpret_cast<const std::uint16_t*>(gb+o2));
        float t=c0*x0;
        t=__builtin_fmaf(c1,x1,t);
        t=__builtin_fmaf(c2,x2,t);
        t=t+d;
        prev=gend;
        if(t<-1.0f){counts+=16;continue;}
        bits|=bit;++counts;
        const unsigned w=g[7],v0=w&255U,v1=w>>8;
        if(v0<vlo)vlo=v0;
        if(v1>vhi)vhi=v1;
    }
    return sg_pick_pack(bits,vlo,vhi,counts>>4,counts&15U);
}
// Exactly the existing sg_select_lean multiply/FMA/FMA/add chain. Explicit FMA
// preserves which product is rounded first; no algebraic plane reassociation.
__attribute__((always_inline)) inline float sg_pick_distance(const std::uint16_t* g,
        float c0,float c1,float c2,float d,int o0,int o1,int o2){
    const char* const gb=reinterpret_cast<const char*>(g);
    const float x0=float(*reinterpret_cast<const std::uint16_t*>(gb+o0));
    const float x1=float(*reinterpret_cast<const std::uint16_t*>(gb+o1));
    const float x2=float(*reinterpret_cast<const std::uint16_t*>(gb+o2));
    float t=c0*x0;
    t=__builtin_fmaf(c1,x1,t);
    t=__builtin_fmaf(c2,x2,t);
    return t+d;
}
// Internal multi-plane path (the dispatcher handles every one-bit mask).
// Read strip ends during the first plane pass and corner ranges during the last;
// intervening planes touch only live groups. Each group's plane order is unchanged.
__attribute__((noinline)) unsigned sg_pick_planes_fused_lean(const std::uint16_t* g,unsigned n,
        const SgPlane* planes,unsigned mask){
    if(!mask)return sg_pick_fallback_lean(g,n,planes,mask);
    const std::uint16_t* const first=g;
    const unsigned endbit=1U<<n;
    const SgPlane* p=planes;unsigned work=mask;
    while(!(work&1U)){work>>=1;++p;}
    unsigned bits=0,nonempty=0;
    {
        const float c0=p->c0,c1=p->c1,c2=p->c2,d=p->d;
        const int o0=p->o0,o1=p->o1,o2=p->o2;
        unsigned prev=0;
        for(unsigned bit=1;bit!=endbit;bit<<=1,g+=8){
            const unsigned gend=g[6];
            if(gend<=prev){
                if(gend==prev)continue;
                return sg_pick_fallback_lean(first,n,planes,mask);
            }
            prev=gend;++nonempty;
            if(!(sg_pick_distance(g,c0,c1,c2,d,o0,o1,o2)<-1.0f))bits|=bit;
        }
    }
    work>>=1;++p;
    // The single-plane caller is dispatched separately. Each remaining plane
    // visits only live groups, and the last pass also collects corner ranges.
    while(work && bits){
        if(!(work&1U)){work>>=1;++p;continue;}
        const float c0=p->c0,c1=p->c1,c2=p->c2,d=p->d;
        const int o0=p->o0,o1=p->o1,o2=p->o2;
        g=first;
        if(work==1U){
            unsigned nr=0,vlo=255,vhi=0;
            for(unsigned bit=1;bit!=endbit;bit<<=1,g+=8)if(bits&bit){
                if(sg_pick_distance(g,c0,c1,c2,d,o0,o1,o2)<-1.0f){bits&=~bit;continue;}
                ++nr;
                const unsigned w=g[7],v0=w&255U,v1=w>>8;
                if(v0<vlo)vlo=v0;
                if(v1>vhi)vhi=v1;
            }
            return sg_pick_pack(bits,vlo,vhi,nonempty-nr,nr);
        }
        for(unsigned bit=1;bit!=endbit;bit<<=1,g+=8)if(bits&bit){
            if(sg_pick_distance(g,c0,c1,c2,d,o0,o1,o2)<-1.0f)bits&=~bit;
        }
        work>>=1;++p;
    }
    return sg_pick_pack(0,255,0,nonempty,0);
}
__attribute__((noinline)) unsigned sg_pick_lean(const std::uint16_t* g,unsigned n,
        const SgPlane* planes,unsigned mask){
    if(mask && !(mask&(mask-1U))){
        const SgPlane* p=planes;
        for(unsigned bit=1;!(mask&bit);bit<<=1)++p;
        return sg_pick_one_lean(g,n,p);
    }
    return sg_pick_planes_fused_lean(g,n,planes,mask);
}
#endif

#pragma once
// Diagnostic only: screen-space submitted area, before depth/alpha rejection.
// No renderer state, dynamic allocations, game memory or material writes.
#include <cmath>
#include <cstdint>
#include <cstring>
namespace re4dc_tamat {
#if defined(RE4DC_TEX_USAGE) && RE4DC_TEX_USAGE
// TEX_USAGE_LOG (lane texusage22): rows live for a whole window (many scenes), so the table is larger.
constexpr unsigned MaxRows=1024, Buckets=4096, None=~0u, Bins=5;
#else
constexpr unsigned MaxRows=256, Buckets=512, None=~0u;
#endif
struct Row {
    unsigned source, list, tsp, tcw, textured, crc, fnv, resolved, tris;
    float fill;
#if defined(RE4DC_TEX_USAGE) && RE4DC_TEX_USAGE
    unsigned hdrs;        // polygon / sprite headers selecting this row (draw submissions)
    float bin[Bins];      // clipped screen area by texels per pixel: <1, 1-2, 2-4, 4-8, >=8
    float texels;         // sum of (texels per pixel x clipped area): area-weighted mean = texels / fill
#endif
};
inline bool finite(float f) { return std::isfinite(f); }
inline float area(const float* xs,const float* ys,unsigned n) {
    if(n<3 || n>4)return -1;
    float ax[12],ay[12],bx[12],by[12];unsigned m=n;
    for(unsigned i=0;i<n;++i){if(!finite(xs[i]) || !finite(ys[i]))return -1;ax[i]=xs[i];ay[i]=ys[i];}
    for(unsigned e=0;e<4 && m;++e){
        unsigned k=0;
        for(unsigned i=0;i<m;++i){
            const unsigned j=(i+1)%m;
            const float pi=e==0?ax[i]:e==1?640.0f-ax[i]:e==2?ay[i]:480.0f-ay[i];
            const float pj=e==0?ax[j]:e==1?640.0f-ax[j]:e==2?ay[j]:480.0f-ay[j];
            if(pi>=0 && k<12){bx[k]=ax[i];by[k]=ay[i];++k;}
            if((pi>=0)!=(pj>=0) && k<12){const float t=pi/(pi-pj);bx[k]=ax[i]+t*(ax[j]-ax[i]);by[k]=ay[i]+t*(ay[j]-ay[i]);++k;}
        }
        m=k;for(unsigned i=0;i<m;++i){ax[i]=bx[i];ay[i]=by[i];}
    }
    float a=0;for(unsigned i=0;i<m;++i){const unsigned j=(i+1)%m;a+=ax[i]*ay[j]-ax[j]*ay[i];}
    if(!finite(a))return -1;
    return a<0?-a*0.5f:a*0.5f;
}
struct Census {
    Row rows[MaxRows]{};
    std::uint16_t buckets[Buckets]{};
    unsigned current[5]{None,None,None,None,None};
    float sprite_x[5][3]{},sprite_y[5][2]{};
    unsigned count=0, overflow=0, invalid=0, orphans=0;
    unsigned tris[5]{};float fill[5]{};
    unsigned select(unsigned list,unsigned source,unsigned tsp,unsigned tcw,bool textured) {
        if(list!=0 && list!=2 && list!=4)return None;
        const unsigned hash=(tcw^(tcw>>16)^tsp^(tsp>>9)^(source*31u)^list)&(Buckets-1);
        for(unsigned probe=0;probe<Buckets;++probe){
            auto& b=buckets[(hash+probe)&(Buckets-1)];
            if(b){const unsigned i=b-1;const Row& r=rows[i];
                if(r.source==source && r.list==list && r.tsp==tsp && r.tcw==tcw && r.textured==unsigned(textured))return current[list]=i;
            }else{
                if(count==MaxRows){++overflow;return current[list]=None;}
                const unsigned i=count++;rows[i]=Row{};rows[i].source=source;rows[i].list=list;rows[i].tsp=tsp;rows[i].tcw=tcw;
                rows[i].textured=unsigned(textured);b=std::uint16_t(i+1);return current[list]=i;
            }
        }
        ++overflow;return current[list]=None;
    }
    void add(unsigned list,const float* x,const float* y,unsigned n,unsigned triangles,const float* u=nullptr,const float* v=nullptr) {
        if(list!=0 && list!=2 && list!=4)return;
        const float a=area(x,y,n);
        if(a<0){++invalid;return;}
        tris[list]+=triangles;fill[list]+=a;
        const unsigned i=current[list];
        if(i==None){++orphans;return;}
        rows[i].tris+=triangles;rows[i].fill+=a;
#if defined(RE4DC_TEX_USAGE) && RE4DC_TEX_USAGE
        Row& r=rows[i];
        if(!u || !v || !r.textured || a<=0)return;
        // Unclipped screen area and UV area of the same polygon (shoelace); the texture size from the TSP.
        float sa=0,ua=0;
        for(unsigned k=0;k<n;++k){const unsigned j=(k+1)%n;sa+=x[k]*y[j]-x[j]*y[k];ua+=u[k]*v[j]-u[j]*v[k];}
        sa=std::fabs(sa)*0.5f;ua=std::fabs(ua)*0.5f;
        if(!finite(sa) || !finite(ua) || sa<1e-3f)return;
        const float tw=float(8u<<((r.tsp>>3)&7u)),th=float(8u<<(r.tsp&7u));
        const float tpp=ua*tw*th/sa;
        if(!finite(tpp))return;
        const unsigned b=tpp<1.0f?0u:tpp<2.0f?1u:tpp<4.0f?2u:tpp<8.0f?3u:4u;
        r.bin[b]+=a;r.texels+=(tpp<4096.0f?tpp:4096.0f)*a;
#endif
    }
    void sprite_first(unsigned list,const float* f) {
        sprite_x[list][0]=f[1];sprite_y[list][0]=f[2];
        sprite_x[list][1]=f[4];sprite_y[list][1]=f[5];sprite_x[list][2]=f[7];
    }
    void sprite_second(unsigned list,const float* f) {
        const float x[4]={sprite_x[list][0],sprite_x[list][1],sprite_x[list][2],f[2]};
        const float y[4]={sprite_y[list][0],sprite_y[list][1],f[0],f[3]};
#if defined(RE4DC_TEX_USAGE) && RE4DC_TEX_USAGE
        // Sprite UVs: words 13..15 (A, B, C) as 16-bit u (high) / v (low) halves; D completes the parallelogram.
        std::uint32_t w[3];std::memcpy(w,f+5,sizeof(w));
        float u[4],v[4];
        for(unsigned k=0;k<3;++k){const std::uint32_t hu=w[k]&0xffff0000u,hv=w[k]<<16;std::memcpy(&u[k],&hu,4);std::memcpy(&v[k],&hv,4);}
        u[3]=u[0]+u[2]-u[1];v[3]=v[0]+v[2]-v[1];
        add(list,x,y,4,2,u,v);
#else
        add(list,x,y,4,2);
#endif
    }
    // Totals use exactly the printed row floors. Independent float reduction
    // orders can differ by more than one pixel after thousands of triangles.
    bool integer_fill(unsigned (&out)[5]) const {
        for(auto& v:out)v=0;
        for(unsigned i=0;i<count;++i){const Row& r=rows[i];if(!r.tris)continue;
            if(!finite(r.fill) || r.fill<0 || r.fill>=4294967296.0f)return false;
            const unsigned a=unsigned(r.fill);
            if(a>~0u-out[r.list])return false;
            out[r.list]+=a;
        }
        return true;
    }
    void incomplete(bool pending) { if(pending)++invalid; }
    void clear() {
        count=overflow=invalid=orphans=0;
        std::memset(buckets,0,sizeof(buckets));std::memset(tris,0,sizeof(tris));std::memset(fill,0,sizeof(fill));
        for(auto& i:current)i=None;
    }
};
}

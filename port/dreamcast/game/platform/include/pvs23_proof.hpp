// Bounded private-QA proof contracts. No game vertex coordinates are stored here.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>

namespace re4dc::pvsproof {
struct Panel {
    unsigned placement,field,part,cluster,meshlet;
    unsigned corners[6]; // two oriented triangles, with strip parity already applied
};
struct Certificate {
    unsigned room,mesh_crc,mesh_bytes,policy_crc,table_bytes,table_crc,max_placement,npanels,margin_mm;
    const Panel* panels;
    double world_abs[3]; // outward absolute affine/grid operand envelope, not cancelled coordinates
};
constexpr unsigned kMaxPanels=16;

inline bool normal_or_zero(float x){
    std::uint32_t b;std::memcpy(&b,&x,4);b&=0x7fffffffU;
    return b==0 || (b>=0x00800000U && b<0x7f800000U);
}
inline bool finite(double x){std::uint64_t b;std::memcpy(&b,&x,8);return ((b>>52)&0x7ffU)!=0x7ffU;}

// Private-QA engineering envelope: gamma128 with u=2^-23 covers ordinary
// RN/RZ chain operations and the conservative FTRV product/alignment allowance;
// rho=2^-18 covers squared-depth plus the actual SH7091 FSRRA research envelope.
// Absolute row operands are retained through cancellation. This is a guarded
// QA contract, not universal verification of every SH-4 or camera state.
inline bool numeric(const Certificate& cert,const float* v,const float* p,const float* w,
                    float near,float far,float screen_w,float screen_h,const float* selected_eye,unsigned fpscr){
    if(!v || !p || !w || !selected_eye || !cert.margin_mm || cert.margin_mm>128U ||
       (fpscr&((1U<<19)|(31U<<7))) || (fpscr&3U)>1U)return false;
    for(unsigned i=0;i<12;++i)if(!normal_or_zero(v[i]) || std::fabs(v[i])>((i&3U)==3U?500000.0f:1.001f))return false;
    for(unsigned i=0;i<7;++i)if(!normal_or_zero(p[i]))return false;
    for(unsigned i=0;i<6;++i)if(!normal_or_zero(w[i]))return false;
    if(p[0]!=0 || std::fabs(p[1])<0.25f || std::fabs(p[1])>10 ||
       std::fabs(p[3])<0.25f || std::fabs(p[3])>10 || std::fabs(p[2])>2 || std::fabs(p[4])>2 ||
       w[2]<1 || w[2]>2048 || w[3]<1 || w[3]>2048 || std::fabs(w[0])>2048 || std::fabs(w[1])>2048 ||
       !normal_or_zero(near) || !normal_or_zero(far) || near<1 || far<=near || far>1000000 ||
       screen_w!=640 || screen_h!=480)return false;
    for(unsigned r=0;r<3;++r)for(unsigned s=0;s<3;++s){
        double dot=0;for(unsigned a=0;a<3;++a)dot+=double(v[4*r+a])*v[4*s+a];
        if(std::fabs(dot-(r==s?1.0:0.0))>0.005)return false;
    }
    const double a=v[0],b=v[1],c=v[2],d=v[4],e=v[5],f=v[6],g=v[8],h=v[9],i=v[10];
    const double cof[9]={e*i-f*h,c*h-b*i,b*f-c*e,f*g-d*i,a*i-c*g,c*d-a*f,d*h-e*g,b*g-a*h,a*e-b*d};
    const double det=a*cof[0]+b*cof[3]+c*cof[6];
    if(!finite(det) || std::fabs(det)<0.995)return false;
    double inv[9],H[3]{};
    for(unsigned q=0;q<9;++q)inv[q]=cof[q]/det;
    for(unsigned r=0;r<3;++r){
        double eye=0;
        for(unsigned q=0;q<3;++q){
            if(!(cert.world_abs[q]>0 && cert.world_abs[q]<=1000000))return false;
            H[r]+=std::fabs(double(v[4*r+q]))*cert.world_abs[q];eye-=inv[3*r+q]*v[4*q+3];
        }
        H[r]+=std::fabs(double(v[4*r+3]));
        // The well-conditioned, bounded double inverse has a deliberately
        // generous 1mm allowance. The actual float cell selector must fit the
        // certificate's expanded eye volume, including that allowance.
        if(!finite(eye) || !normal_or_zero(selected_eye[r]) ||
           std::fabs(double(selected_eye[r])-eye)+1.0>cert.margin_mm)return false;
    }
    constexpr double u=1.0/8388608.0,gamma=(128*u)/(1-128*u),rho=1.0/262144.0;
    const double ax=320.0*p[1],ay=-240.0*p[3],sx=640.0/w[2],sy=480.0/w[3];
    const double cx=sx*(double(w[0])+0.5*w[2])-320.0*p[2];
    const double cy=sy*(double(w[1])+0.5*w[3])+240.0*p[4];
    const double kx=320.0*std::fabs(double(p[2]))+std::fabs(sx)*(std::fabs(double(w[0]))+0.5*std::fabs(double(w[2])));
    const double ky=240.0*std::fabs(double(p[4]))+std::fabs(sy)*(std::fabs(double(w[1]))+0.5*std::fabs(double(w[3])));
    const double X=std::fabs(ax)*H[0]+kx*H[2],Y=std::fabs(ay)*H[1]+ky*H[2];
    const double ex=gamma*X,ey=gamma*Y,ew=gamma*H[2];
    const double EW=ew+rho*(H[2]+ew)/(1-rho);
    const double E[3]={(ex+u*(X+ex)+std::fabs(cx)*EW)/std::fabs(ax),
                       (ey+u*(Y+ey)+std::fabs(cy)*EW)/std::fabs(ay),EW};
    for(unsigned r=0;r<3;++r){
        double error=0;for(unsigned q=0;q<3;++q)error+=std::fabs(inv[3*r+q])*E[q];
        if(!finite(error) || error+1.0>cert.margin_mm)return false;
    }
    return true;
}

// Replacing the scene, changing any view/projection/window state, or changing
// package generation invalidates all observed and committed source witnesses.
struct Receipts {
    unsigned frame=~0U,scene=~0U,room=~0U,generation=~0U,committed=0;
    float state[27]{};
    void clear(){frame=scene=room=generation=~0U;committed=0;}
    void sync(unsigned f,unsigned s,unsigned r,unsigned g,const float* key){
        if(frame!=f || scene!=s || room!=r || generation!=g || std::memcmp(state,key,sizeof(state))){
            frame=f;scene=s;room=r;generation=g;committed=0;
            std::memcpy(state,key,sizeof(state));
        }
    }
    bool complete(unsigned n)const{return n && n<=kMaxPanels && committed==((1U<<n)-1U);}
};

// A whole successfully processed meshlet is the strict first cohort. Each
// qualifying source strip must have been emitted unchanged; partial SG picks do
// not call this predicate. Other strips may clip/cull. The source index stream
// must contain both exact triangles in qualifying strips.
// This is a witness of submitted inputs, never a claim of depth-visible pixels.
template<class Vertex>
inline bool panel_sent(const Panel& p,const Vertex* cache,const std::uint8_t* codes,unsigned count,
                       const std::uint8_t* strips,unsigned bytes,unsigned cull,unsigned limit){
    if(!cache || !codes || !strips || !count || count>256U || (cull!=0U && cull!=2U))return false;
    for(unsigned i=0;i<count;++i)
        if(!normal_or_zero(cache[i].x) || !normal_or_zero(cache[i].y) ||
           !normal_or_zero(cache[i].z) || cache[i].z<=0)return false;
    for(unsigned i:p.corners)if(i>=count || std::fabs(cache[i].x)>4096 || std::fabs(cache[i].y)>4096)return false;
    unsigned found=0;
    for(unsigned off=0;off<bytes;){
        const unsigned n=strips[off++];
        if(n<3 || n>bytes-off)return false;
        unsigned any=0,all=0x3fU;
        for(unsigned i=0;i<n;++i){
            if(strips[off+i]>=count)return false;
            const unsigned code=codes[strips[off+i]]&0x3fU;any|=code;all&=code;
        }
        // walk_lean also sends an oversized strip to the CPU clipper even when
        // it crosses no depth plane. The real post-borrow limit is mandatory.
        const bool unchanged=n<=limit && !(any&0x30U) && !(all&0x0fU);
        for(unsigned t=0;unchanged && t+2<n;++t){
            const unsigned a=strips[off+((t&1U)?t+2:t)];
            const unsigned b=strips[off+t+1];
            const unsigned c=strips[off+((t&1U)?t:t+2)];
            for(unsigned q=0;q<2;++q)
                if(a==p.corners[3*q] && b==p.corners[3*q+1] && c==p.corners[3*q+2])found|=1U<<q;
        }
        off+=n;
    }
    if(found!=3U)return false;
    for(unsigned q=0;q<2;++q){
        const auto& a=cache[p.corners[3*q]];const auto& b=cache[p.corners[3*q+1]];
        const auto& c=cache[p.corners[3*q+2]];
        const double area=(double(b.x)-a.x)*(double(c.y)-a.y)-(double(b.y)-a.y)*(double(c.x)-a.x);
        // Strong screen-area margin excludes degenerate/near-zero winding and
        // is much larger than single-precision area-rounding uncertainty here.
        if(!finite(area) || (cull==2U?area>=-256.0:std::fabs(area)<=256.0))return false;
    }
    return true;
}
} // namespace re4dc::pvsproof

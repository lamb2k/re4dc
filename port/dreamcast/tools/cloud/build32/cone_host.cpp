#include "../../../game/platform/include/actor_cone32.hpp"
#include <array>
#include <cassert>
#include <cstdio>
#include <limits>
#include <random>
#include <vector>

using namespace re4dc::cone32;
struct Cone { short c[3]; unsigned short r; short a[3]; unsigned char k,pal; };
struct Eye {float e[3],s;};
using V=std::array<float,3>;
using Triangle=std::array<V,3>;
static float dot(const V& a,const V& b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static V cross(const V& a,const V& b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static V normal(V a){const float r=std::sqrt(dot(a,a));assert(r>0);for(float& v:a)v/=r;return a;}
static V minus(const V& a,const V& b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static void inverse_data(const float a[9],float adj[9],float& det){
    adj[0]=a[4]*a[8]-a[5]*a[7];adj[1]=a[2]*a[7]-a[1]*a[8];adj[2]=a[1]*a[5]-a[2]*a[4];
    adj[3]=a[5]*a[6]-a[3]*a[8];adj[4]=a[0]*a[8]-a[2]*a[6];adj[5]=a[2]*a[3]-a[0]*a[5];
    adj[6]=a[3]*a[7]-a[4]*a[6];adj[7]=a[1]*a[6]-a[0]*a[7];adj[8]=a[0]*a[4]-a[1]*a[3];
    det=a[0]*adj[0]+a[1]*adj[3]+a[2]*adj[6];
}
static Eye eye_of(const float a[9],const float t[3],unsigned cull,float adj[9],float& det){
    inverse_data(a,adj,det);Eye e{};
    for(unsigned r=0;r<3;++r)e.e[r]=-(adj[3*r]*t[0]+adj[3*r+1]*t[1]+adj[3*r+2]*t[2])/det;
    e.s=((cull==2)==(det>0))?1.f:-1.f;return e;
}
static float area(const Triangle& triangle,const float a[9],const float t[3],float near){
    V screen[3];
    for(unsigned i=0;i<3;++i){
        for(unsigned r=0;r<3;++r)screen[i][r]=a[3*r]*triangle[i][0]+a[3*r+1]*triangle[i][1]+a[3*r+2]*triangle[i][2]+t[r];
        assert(screen[i][2]>near);
        screen[i][0]/=screen[i][2];screen[i][1]/=screen[i][2];
    }
    return (screen[1][0]-screen[0][0])*(screen[2][1]-screen[0][1])-
           (screen[1][1]-screen[0][1])*(screen[2][0]-screen[0][0]);
}
int main(){
    unsigned checks=0,rejects=0,keeps=0,near_refusals=0,forced_near=0;
    const float step=1.5707963f/63.f;
    std::mt19937 rng(0x32c0ffeeU);
    std::uniform_real_distribution<float> unit(-1.f,1.f),positive(0.f,1.f);
    // These normals and source positions are independent input fixtures. The
    // tested prepare/test methods are the actual production header, unchanged.
    // Each cone encloses eight explicitly checked integer-position triangles.
    for(unsigned sample=0;sample<12000;++sample){
        Cone cone{};V axis=normal({unit(rng),unit(rng),unit(rng)});
        for(unsigned k=0;k<3;++k)cone.a[k]=short(std::lrint(axis[k]*32767.f));
        axis=normal({float(cone.a[0]),float(cone.a[1]),float(cone.a[2])});
        cone.k=static_cast<unsigned char>(2+sample%55);cone.pal=static_cast<unsigned char>(sample%256);
        const float theta=float(cone.k)*step;
        std::vector<Triangle> triangles;
        float radius2=0.f;
        for(unsigned j=0;j<8;++j){
            V side=normal(cross(axis,std::fabs(axis[0])<.8f?V{1,0,0}:V{0,1,0}));
            const V side2=cross(axis,side);const float az=positive(rng)*6.2831853f;
            const float angle=(theta-.035f)*positive(rng);
            V n;for(unsigned k=0;k<3;++k)n[k]=axis[k]*std::cos(angle)+(side[k]*std::cos(az)+side2[k]*std::sin(az))*std::sin(angle);
            V u=normal(cross(n,std::fabs(n[0])<.8f?V{1,0,0}:V{0,1,0}));V v=cross(n,u);
            Triangle tr;
            for(unsigned k=0;k<3;++k){
                tr[0][k]=std::round(-400.f*u[k]-200.f*v[k]);
                tr[1][k]=std::round(400.f*u[k]-200.f*v[k]);
                tr[2][k]=std::round(400.f*v[k]);
            }
            V actual=normal(cross(minus(tr[1],tr[0]),minus(tr[2],tr[0])));
            assert(dot(actual,axis)>=std::cos(theta-.01745f));
            for(const V& point:tr)radius2=std::max(radius2,dot(point,point));
            triangles.push_back(tr);
        }
        cone.r=static_cast<unsigned short>(std::ceil(std::sqrt(radius2))+2.f);
        V camera=normal({unit(rng),unit(rng),unit(rng)});
        const float distance=4000.f+positive(rng)*36000.f;
        for(float& e:camera)e*=distance;
        V forward=normal({-camera[0],-camera[1],-camera[2]});
        V right=normal(cross(forward,std::fabs(forward[1])<.8f?V{0,1,0}:V{1,0,0}));
        V up=cross(right,forward);
        // Different scales and a reflected screen basis cover rigid and
        // single-palette skin transforms; normals stay in raw source space.
        float a[9],t[3]{};const float reflection=sample&1?1.f:-1.f;
        const float sx=64.f+positive(rng)*512.f,sy=64.f+positive(rng)*512.f;
        for(unsigned k=0;k<3;++k){
            a[k]=reflection*sx*right[k]+320.f*forward[k];
            a[3+k]=-sy*up[k]+240.f*forward[k];a[6+k]=forward[k];
        }
        for(unsigned r=0;r<3;++r)for(unsigned k=0;k<3;++k)t[r]-=a[3*r+k]*camera[k];
        for(unsigned cull=1;cull<=2;++cull){
            float adj[9],det;Eye eye=eye_of(a,t,cull,adj,det);Guard guard;
            const bool prepared=prepare(a,t,adj,det,eye.e,10.f,guard);
            ++checks;
            if(!prepared)continue;
            const auto result=test(cone,eye,guard,std::cos(theta),std::sin(theta)*std::sin(theta));
            if(result==Reject){
                ++rejects;
                for(const auto& tri:triangles){
                    const float projected=area(tri,a,t,10.f);
                    assert((cull==2?projected:-projected)>=0.f);++checks;
                }
            }else if(result==Near)++near_refusals;
            else ++keeps;
            Guard near_guard=guard;near_guard.near=distance;
            assert(test(cone,eye,near_guard,std::cos(theta),std::sin(theta)*std::sin(theta))==Near);++checks;++forced_near;
        }
    }
    assert(rejects>1000 && keeps>1000);
    float a[9]={1,0,0,0,1,0,0,0,1},t[3]={0,0,10000},adj[9],det;
    Eye eye=eye_of(a,t,2,adj,det);Guard guard;
    assert(prepare(a,t,adj,det,eye.e,10.f,guard));
    Cone c{{0,0,0},100,{0,0,32767},2,0};
    assert(test(c,eye,guard,std::cos(2*step),std::sin(2*step)*std::sin(2*step))==Reject);
    c.k=0;assert(test(c,eye,guard,1.f,0.f)==Empty);
    c.k=57;assert(test(c,eye,guard,1.f,0.f)==Empty);
    c.k=2;c.a[2]=0;assert(test(c,eye,guard,1.f,0.f)==Numeric);c.a[2]=32767;
    for(float bad:{std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),-std::numeric_limits<float>::infinity()}){
        float m[9];std::memcpy(m,a,sizeof(m));m[0]=bad;assert(!prepare(m,t,adj,det,eye.e,10.f,guard));
        assert(!prepare(a,t,adj,det,eye.e,bad,guard));checks+=2;
    }
    assert(!prepare(a,t,adj,0.f,eye.e,10.f,guard));
    assert(!prepare(a,t,adj,det,eye.e,0.f,guard));
    a[0]=1.e-8f;eye=eye_of(a,t,2,adj,det);assert(!prepare(a,t,adj,det,eye.e,10.f,guard));
    a[0]=1.e9f;eye=eye_of(a,t,2,adj,det);assert(!prepare(a,t,adj,det,eye.e,10.f,guard));
    const int info=1,positions=2,changed=3;
    SourceIdentity identity{reinterpret_cast<std::uintptr_t>(&info),reinterpret_cast<std::uintptr_t>(&positions),128,6};
    assert(identity.matches(&info,&positions,128,6));
    assert(!identity.matches(&changed,&positions,128,6));assert(!identity.matches(&info,&changed,128,6));
    assert(!identity.matches(&info,&positions,127,6));assert(!identity.matches(&info,&positions,128,8));
    Counters stats;for(unsigned i=0;i<PartReasons;++i)stats.decline(static_cast<PartWhy>(i));
    assert(stats.declined==PartReasons);for(unsigned n:stats.why)assert(n==1);
    std::printf("PASS cone32: %u checks, %u rejected cones with all projected triangles hidden, %u kept, %u ordinary / %u forced near refusals; source/finite/condition guards\n",checks,rejects,keeps,near_refusals,forced_near);
}

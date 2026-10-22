#include "shz_bounds.h"
#include <stdint.h>
#include <string.h>
static uint32_t bits(float x) { uint32_t u; memcpy(&u,&x,4);return u; }
static float word(uint32_t u) { float x;memcpy(&x,&u,4);return x; }
static int normal(float x) { uint32_t a=bits(x)&0x7fffffffU;return !a || (a>=0x00800000U && a<0x7f800000U); }
static int valid(shz_interval_t a) {return normal(a.lo)&&normal(a.hi)&&a.lo<=a.hi;}
int shz_bounds_mode_supported(unsigned s) {
    /* PR19, SZ20, FR21, enables7..11 and invalid rounding2/3. */
    return !(s & ((7U<<19)|(31U<<7)|2U));
}
int shz_bounds_point(float x,shz_interval_t* o) {o->lo=o->hi=x;return normal(x);}
/* Every basic operation rounds once. One adjacent float on either side
 * encloses the real result under RN and RZ. Exact zero may represent flushed
 * underflow; reject that unless the operation proves mathematical zero.
 * Boundary/subnormal output rejects, including its outward neighbours. */
static int enclosure(float x,int exactzero,shz_interval_t* o) {
    uint32_t u=bits(x),a=u&0x7fffffffU;
    if (!a) {if(!exactzero)return 0;o->lo=o->hi=0;return 1;}
    if(a<=0x00800001U || a>=0x7f7fffffU)return 0;
    o->lo=word((u>>31)?u+1:u-1);o->hi=word((u>>31)?u-1:u+1);return 1;
}
static float add(float a,float b) {
#if defined(__sh__)
    __asm__ volatile("fadd %1,%0":"+f"(a):"f"(b));return a;
#else
    volatile float c=a+b;return c;
#endif
}
static float mul(float a,float b) {
#if defined(__sh__)
    __asm__ volatile("fmul %1,%0":"+f"(a):"f"(b));return a;
#else
    volatile float c=a*b;return c;
#endif
}
static float divide(float a,float b) {
#if defined(__sh__)
    __asm__ volatile("fdiv %1,%0":"+f"(a):"f"(b));return a;
#else
    volatile float c=a/b;return c;
#endif
}
int shz_bounds_neg(shz_interval_t a,shz_interval_t* o) {if(!valid(a))return 0;o->lo=-a.hi;o->hi=-a.lo;return 1;}
int shz_bounds_add(shz_interval_t a,shz_interval_t b,shz_interval_t* o) {
    shz_interval_t l,h;if(!valid(a)||!valid(b))return 0;
    if(!enclosure(add(a.lo,b.lo),a.lo==-b.lo,&l)||!enclosure(add(a.hi,b.hi),a.hi==-b.hi,&h))return 0;
    o->lo=l.lo;o->hi=h.hi;return 1;
}
static int product(shz_interval_t a,shz_interval_t b,shz_interval_t* o,int div) {
    float av[2]={a.lo,a.hi},bv[2]={b.lo,b.hi};unsigned i,j;shz_interval_t v;
    if(!valid(a)||!valid(b)||(div && b.lo<=0 && b.hi>=0))return 0;
    for(i=0;i<2;i++)for(j=0;j<2;j++) {
        if(!enclosure(div?divide(av[i],bv[j]):mul(av[i],bv[j]),av[i]==0 || (!div&&bv[j]==0),&v))return 0;
        if(!i&&!j)*o=v;else {if(v.lo<o->lo)o->lo=v.lo;if(v.hi>o->hi)o->hi=v.hi;}
    }return 1;
}
int shz_bounds_mul(shz_interval_t a,shz_interval_t b,shz_interval_t* o) {return product(a,b,o,0);}
int shz_bounds_div(shz_interval_t a,shz_interval_t b,shz_interval_t* o) {return product(a,b,o,1);}
int shz_bounds_affine(const shz_interval_t m[12],const shz_interval_t in[3],shz_interval_t out[3]) {
    unsigned r,c;shz_interval_t v[3],p;
    for(r=0;r<3;r++) {v[r]=m[r*4+3];if(!valid(v[r]))return 0;
        for(c=0;c<3;c++)if(!shz_bounds_mul(m[r*4+c],in[c],&p)||!shz_bounds_add(v[r],p,&v[r]))return 0;
    }memcpy(out,v,sizeof(v));return 1;
}
static int subprod(shz_interval_t a,shz_interval_t b,shz_interval_t c,shz_interval_t d,shz_interval_t* o) {
    shz_interval_t x,y;return shz_bounds_mul(a,b,&x)&&shz_bounds_mul(c,d,&y)&&shz_bounds_neg(y,&y)&&shz_bounds_add(x,y,o);
}
int shz_bounds_inverse(const float in[12],shz_interval_t out[12]) {
    shz_interval_t m[12],co[9],det,p,t[3],n[3];unsigned r,c;
    for(r=0;r<12;r++)if(!shz_bounds_point(in[r],m+r))return 0;
    for(r=0;r<3;r++)for(c=0;c<3;c++) {
        unsigned a=(r+1)%3,b=(r+2)%3,x=(c+1)%3,y=(c+2)%3;
        if(!subprod(m[a*4+x],m[b*4+y],m[a*4+y],m[b*4+x],&co[r*3+c]))return 0;
    }
    det.lo=det.hi=0;
    for(c=0;c<3;c++)if(!shz_bounds_mul(m[c],co[c],&p)||!shz_bounds_add(det,p,&det))return 0;
    if(det.lo<=0&&det.hi>=0)return 0;
    for(r=0;r<3;r++)for(c=0;c<3;c++)if(!shz_bounds_div(co[c*3+r],det,out+r*4+c))return 0;
    for(r=0;r<3;r++){t[r]=m[r*4+3];out[r*4+3].lo=out[r*4+3].hi=0;}
    if(!shz_bounds_affine(out,t,n))return 0;
    for(r=0;r<3;r++)shz_bounds_neg(n[r],out+r*4+3);
    return 1;
}

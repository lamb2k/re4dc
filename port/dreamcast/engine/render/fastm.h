#pragma once
/* Branch-light scalar helpers for the bench's hot loops. No libm call may sit in a per-vertex or
   per-meshlet loop: newlib's fminf/fmaxf call __fpclassifyf for every operand. */
#include <stdint.h>
static inline float m1_minf(float a,float b){return a<b?a:b;}
static inline float m1_maxf(float a,float b){return a>b?a:b;}
static inline float m1_clampf(float x,float lo,float hi){return x<lo?lo:(x>hi?hi:x);}
/* 0..255 channel from a float, through a signed conversion (ftrc): float to unsigned is a libgcc call. */
static inline uint32_t m1_byte(float x){int v=(int)x;return v<0?0u:(v>255?255u:(uint32_t)v);}
/* 1/w for w>0 through fsrra(w*w): no divide on the store path. */
static inline float m1_rcp_pos(float w){
#if defined(__SH4__) || defined(__sh__)
    float r=w*w;__asm__("fsrra %0":"+f"(r));return r;
#else
    return 1.0f/w;
#endif
}

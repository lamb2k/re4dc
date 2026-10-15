/* game30 GAME_TRIG=1 (needs GAME_FDLIBM=1): sinf / cosf of the game's recovered fdlibm
 * (src/lib/fdlibm, newlib 1.8.2) with their helpers copied in as static inline functions:
 *   __kernel_sinf (kf_sin.c), __kernel_cosf (kf_cos.c) and the |x| <= 2^7*pi/2 paths of
 *   __ieee754_rem_pio2f (ef_rem_pio2.c); larger or non-finite arguments still call the original
 *   __ieee754_rem_pio2f, which recomputes from x.
 * Every float operation is the original's, in the original's order, on the original constants; the
 * file is compiled -O2 -ffp-contract=off (no fmac, no reassociation without -ffast-math), so each
 * result is bit-identical by construction. What goes away is two call levels per evaluation (the
 * r100 tick makes ~2,800 sin/cos kernel evaluations per frame) and the helpers' spread over four
 * objects in the I-cache. Checked exhaustively on the host (all 2^32 inputs of both functions,
 * flush-to-zero like the SH-4's FPSCR.DN=1): tools/trig_exhaustive.c.
 * sf_sin.o and sf_cos.o drop out of the link (game30.mk); the kernels and ef_rem_pio2 stay for
 * tanf and the large-argument path.
 * GAME_SINCOS=1 (design-logic P6) adds re4dc_sincosf: sinf and cosf of one argument with the |x| test
 * and the argument reduction done once. Each output is the same kernel call on the same reduced
 * argument (rem_pio2f is a pure function of x) that sinf / cosf make, so both are bit-identical by
 * construction; checked for all 2^32 inputs on the host (tools/game30/sincos_exhaustive.sh).
 * GAME_TRIG_LEAN=1 (lane gskel, at the end of the file) replaces the three public functions with
 * leaf versions of the same operations (see there).
 */
#if defined(RE4DC_SH4_APPROX_LOGIC) && RE4DC_SH4_APPROX_LOGIC
/* SH4_APPROX_LOGIC (game30.mk, lane approx; NOT exact): Bruceleeto's fe2aed7945. sh4zam pulls in newlib's __int32_t
 * (long); fdlibm.h typedefs its own (int): keep fdlibm's under other names. */
#include <sh4zam/shz_trig.h>
#define __int32_t re4dc_fd_int32_t
#define __uint32_t re4dc_fd_uint32_t
#endif
#include "fdlibm.h"

static const float
/* kf_sin.c */
k_half =  5.0000000000e-01, /* 0x3f000000 */
S1  = -1.6666667163e-01, /* 0xbe2aaaab */
S2  =  8.3333337680e-03, /* 0x3c088889 */
S3  = -1.9841270114e-04, /* 0xb9500d01 */
S4  =  2.7557314297e-06, /* 0x3638ef1b */
S5  = -2.5050759689e-08, /* 0xb2d72f34 */
S6  =  1.5896910177e-10, /* 0x2f2ec9d3 */
/* kf_cos.c */
one =  1.0000000000e+00, /* 0x3f800000 */
C1  =  4.1666667908e-02, /* 0x3d2aaaab */
C2  = -1.3888889225e-03, /* 0xbab60b61 */
C3  =  2.4801587642e-05, /* 0x37d00d01 */
C4  = -2.7557314297e-07, /* 0xb493f27c */
C5  =  2.0875723372e-09, /* 0x310f74f6 */
C6  = -1.1359647598e-11, /* 0xad47d74e */
/* ef_rem_pio2.c */
r_half =  5.0000000000e-01, /* 0x3f000000 */
invpio2 =  6.3661980629e-01, /* 0x3f22f984 */
pio2_1  =  1.5707855225e+00, /* 0x3fc90f80 */
pio2_1t =  1.0804334124e-05, /* 0x37354443 */
pio2_2  =  1.0804273188e-05, /* 0x37354400 */
pio2_2t =  6.0770999344e-11, /* 0x2e85a308 */
pio2_3  =  6.0770943833e-11, /* 0x2e85a300 */
pio2_3t =  6.1232342629e-17; /* 0x248d3132 */

/* ef_rem_pio2.c */
static const __int32_t npio2_hw[] = {
0x3fc90f00, 0x40490f00, 0x4096cb00, 0x40c90f00, 0x40fb5300, 0x4116cb00,
0x412fed00, 0x41490f00, 0x41623100, 0x417b5300, 0x418a3a00, 0x4196cb00,
0x41a35c00, 0x41afed00, 0x41bc7e00, 0x41c90f00, 0x41d5a000, 0x41e23100,
0x41eec200, 0x41fb5300, 0x4203f200, 0x420a3a00, 0x42108300, 0x4216cb00,
0x421d1400, 0x42235c00, 0x4229a500, 0x422fed00, 0x42363600, 0x423c7e00,
0x4242c700, 0x42490f00
};

/* kf_sin.c __kernel_sinf */
static inline __attribute__((always_inline)) float k_sinf(float x, float y, int iy)
{
	float z,r,v;
	__int32_t ix;
	GET_FLOAT_WORD(ix,x);
	ix &= 0x7fffffff;			/* high word of x */
	if(ix<0x32000000)			/* |x| < 2**-27 */
	   {if((int)x==0) return x;}		/* generate inexact */
	z	=  x*x;
	v	=  z*x;
	r	=  S2+z*(S3+z*(S4+z*(S5+z*S6)));
	if(iy==0) return x+v*(S1+z*r);
	else      return x-((z*(k_half*y-v*r)-y)-v*S1);
}

/* kf_cos.c __kernel_cosf */
static inline __attribute__((always_inline)) float k_cosf(float x, float y)
{
	float a,hz,z,r,qx;
	__int32_t ix;
	GET_FLOAT_WORD(ix,x);
	ix &= 0x7fffffff;			/* ix = |x|'s high word*/
	if(ix<0x32000000) {			/* if x < 2**27 */
	    if(((int)x)==0) return one;		/* generate inexact */
	}
	z  = x*x;
	r  = z*(C1+z*(C2+z*(C3+z*(C4+z*(C5+z*C6)))));
	if(ix < 0x3e99999a) 			/* if |x| < 0.3 */
	    return one - ((float)0.5*z - (z*r - x*y));
	else {
	    if(ix > 0x3f480000) {		/* x > 0.78125 */
		qx = (float)0.28125;
	    } else {
	        SET_FLOAT_WORD(qx,ix-0x01000000);	/* x/4 */
	    }
	    hz = (float)0.5*z-qx;
	    a  = one-qx;
	    return a - (hz - (z*r-x*y));
	}
}

/* ef_rem_pio2.c __ieee754_rem_pio2f, callers' |x| > pi/4 already established */
static inline __attribute__((always_inline)) __int32_t rem_pio2f(float x, float *y)
{
	float z,w,t,r,fn;
	__int32_t i,j,n,ix,hx;
	GET_FLOAT_WORD(hx,x);
	ix = hx&0x7fffffff;
	if(ix<0x4016cbe4) {  /* |x| < 3pi/4, special case with n=+-1 */
	    if(hx>0) {
		z = x - pio2_1;
		if((ix&0xfffffff0)!=0x3fc90fd0) { /* 24+24 bit pi OK */
		    y[0] = z - pio2_1t;
		    y[1] = (z-y[0])-pio2_1t;
		} else {		/* near pi/2, use 24+24+24 bit pi */
		    z -= pio2_2;
		    y[0] = z - pio2_2t;
		    y[1] = (z-y[0])-pio2_2t;
		}
		return 1;
	    } else {	/* negative x */
		z = x + pio2_1;
		if((ix&0xfffffff0)!=0x3fc90fd0) { /* 24+24 bit pi OK */
		    y[0] = z + pio2_1t;
		    y[1] = (z-y[0])+pio2_1t;
		} else {		/* near pi/2, use 24+24+24 bit pi */
		    z += pio2_2;
		    y[0] = z + pio2_2t;
		    y[1] = (z-y[0])+pio2_2t;
		}
		return -1;
	    }
	}
	if(ix<=0x43490f80) { /* |x| ~<= 2^7*(pi/2), medium size */
	    t  = fabsf(x);
	    n  = (__int32_t) (t*invpio2+r_half);
	    fn = (float)n;
	    r  = t-fn*pio2_1;
	    w  = fn*pio2_1t;	/* 1st round good to 40 bit */
	    if(n<32&&(ix&0xffffff00)!=npio2_hw[n-1]) {
		y[0] = r-w;	/* quick check no cancellation */
	    } else {
	        __uint32_t high;
	        j  = ix>>23;
	        y[0] = r-w;
		GET_FLOAT_WORD(high,y[0]);
	        i = j-((high>>23)&0xff);
	        if(i>8) {  /* 2nd iteration needed, good to 57 */
		    t  = r;
		    w  = fn*pio2_2;
		    r  = t-w;
		    w  = fn*pio2_2t-((t-r)-w);
		    y[0] = r-w;
		    GET_FLOAT_WORD(high,y[0]);
		    i = j-((high>>23)&0xff);
		    if(i>25)  {	/* 3rd iteration need, 74 bits acc */
		    	t  = r;	/* will cover all possible cases */
		    	w  = fn*pio2_3;
		    	r  = t-w;
		    	w  = fn*pio2_3t-((t-r)-w);
		    	y[0] = r-w;
		    }
		}
	    }
	    y[1] = (r-y[0])-w;
	    if(hx<0) 	{y[0] = -y[0]; y[1] = -y[1]; return -n;}
	    else	 return n;
	}
	/* large arguments (and inf/NaN, excluded by the callers): the original, from x */
	return __ieee754_rem_pio2f(x,y);
}

#if !(defined(RE4DC_TRIG_LEAN) && RE4DC_TRIG_LEAN)
/* sf_sin.c */
float sinf(float x)
{
	float y[2],z=0.0;
	__int32_t n,ix;
	GET_FLOAT_WORD(ix,x);
    /* |x| ~< pi/4 */
	ix &= 0x7fffffff;
	if(ix <= 0x3f490fd8) return k_sinf(x,z,0);
    /* sin(Inf or NaN) is NaN */
	else if (ix>=0x7f800000) return x-x;
    /* argument reduction needed */
	else {
	    n = rem_pio2f(x,y);
	    switch(n&3) {
		case 0: return  k_sinf(y[0],y[1],1);
		case 1: return  k_cosf(y[0],y[1]);
		case 2: return -k_sinf(y[0],y[1],1);
		default:
			return -k_cosf(y[0],y[1]);
	    }
	}
}

/* sf_cos.c */
float cosf(float x)
{
	float y[2],z=0.0;
	__int32_t n,ix;
	GET_FLOAT_WORD(ix,x);
    /* |x| ~< pi/4 */
	ix &= 0x7fffffff;
	if(ix <= 0x3f490fd8) return k_cosf(x,z);
    /* cos(Inf or NaN) is NaN */
	else if (ix>=0x7f800000) return x-x;
    /* argument reduction needed */
	else {
	    n = rem_pio2f(x,y);
	    switch(n&3) {
		case 0: return  k_cosf(y[0],y[1]);
		case 1: return -k_sinf(y[0],y[1],1);
		case 2: return -k_cosf(y[0],y[1]);
		default:
		        return  k_sinf(y[0],y[1],1);
	    }
	}
}

#if defined(RE4DC_SINCOS) && RE4DC_SINCOS
/* design-logic P6: *s = sinf(x), *c = cosf(x) (the two functions above, one argument reduction) */
void re4dc_sincosf(float x, float *s, float *c)
{
	float y[2],z=0.0;
	__int32_t n,ix;
	GET_FLOAT_WORD(ix,x);
	ix &= 0x7fffffff;
	if(ix <= 0x3f490fd8) {
	    *s = k_sinf(x,z,0);
	    *c = k_cosf(x,z);
	} else if (ix>=0x7f800000) {
	    *s = x-x;
	    *c = x-x;
	} else {
	    n = rem_pio2f(x,y);
	    switch(n&3) {
		case 0: *s =  k_sinf(y[0],y[1],1); *c =  k_cosf(y[0],y[1]); break;
		case 1: *s =  k_cosf(y[0],y[1]);   *c = -k_sinf(y[0],y[1],1); break;
		case 2: *s = -k_sinf(y[0],y[1],1); *c = -k_cosf(y[0],y[1]); break;
		default:
			*s = -k_cosf(y[0],y[1]);   *c =  k_sinf(y[0],y[1],1); break;
	    }
	}
}
#endif /* RE4DC_SINCOS */
#endif /* !RE4DC_TRIG_LEAN */

#if defined(RE4DC_TRIG_LEAN) && RE4DC_TRIG_LEAN
/* GAME_TRIG_LEAN (game30.mk, lane gskel; exact): sinf, cosf and re4dc_sincosf above, reshaped for the
 * SH-4 without changing any float operation or its operands:
 *  - x's word (and the reduced argument's) goes through FPUL (flds / sts), not a store and a reload;
 *  - |x| > 2^7*pi/2 and non-finite x take separate functions holding the original code (tail calls), so
 *    the common paths are leaf functions with the reduced argument in registers (no PR save, no frame);
 *  - a kernel's |x| < 2^-27 case returns x (sin) or one (cos) as the original does: its "(int)x == 0"
 *    test is always true there and only raised the inexact flag;
 *  - the quadrant switch takes one kernel value and negates it (sinf, cosf) or swaps and negates the two
 *    (re4dc_sincosf), instead of inlining each kernel once per case (re4dc_sincosf was 2.4 KB).
 * Checked for all 2^32 inputs of all three functions against the recovered fdlibm on the host
 * (tools/game30/trig_lean_exhaustive.sh, FTZ/DAZ like FPSCR.DN=1).
 */
static inline __attribute__((always_inline)) __int32_t lfbits(float x)
{
	__int32_t i;
#if defined(__sh__)
	__asm__("flds\t%1,fpul\n\tsts\tfpul,%0" : "=r"(i) : "f"(x) : "fpul");
#else
	GET_FLOAT_WORD(i,x);
#endif
	return i;
}

/* __kernel_sinf(x,y,0) for 2^-27 <= |x| */
static inline __attribute__((always_inline)) float lk_sin0(float x)
{
	float z,r,v;
	z	=  x*x;
	v	=  z*x;
	r	=  S2+z*(S3+z*(S4+z*(S5+z*S6)));
	return x+v*(S1+z*r);
}

/* __kernel_sinf(x,y,1); ix = |x|'s word */
static inline __attribute__((always_inline)) float lk_sin1(float x, float y, __int32_t ix)
{
	float z,r,v;
	if(ix<0x32000000) return x;		/* |x| < 2**-27 */
	z	=  x*x;
	v	=  z*x;
	r	=  S2+z*(S3+z*(S4+z*(S5+z*S6)));
	return x-((z*(k_half*y-v*r)-y)-v*S1);
}

/* __kernel_cosf(x,y); ix = |x|'s word */
static inline __attribute__((always_inline)) float lk_cos(float x, float y, __int32_t ix)
{
	float a,hz,z,r,qx;
	if(ix<0x32000000) return one;		/* |x| < 2**-27 */
	z  = x*x;
	r  = z*(C1+z*(C2+z*(C3+z*(C4+z*(C5+z*C6)))));
	if(ix < 0x3e99999a) 			/* if |x| < 0.3 */
	    return one - ((float)0.5*z - (z*r - x*y));
	else {
	    if(ix > 0x3f480000) {		/* x > 0.78125 */
		qx = (float)0.28125;
	    } else {
	        SET_FLOAT_WORD(qx,ix-0x01000000);	/* x/4 */
	    }
	    hz = (float)0.5*z-qx;
	    a  = one-qx;
	    return a - (hz - (z*r-x*y));
	}
}

/* rem_pio2f above for pi/4 < |x| <= 2^7*pi/2; hx = x's word, ix = |x|'s; y[0] / y[1] in registers */
static inline __attribute__((always_inline)) __int32_t lrem_pio2f(float x, __int32_t hx, __int32_t ix, float *y0, float *y1)
{
	float z,w,t,r,fn,u;
	__int32_t i,j,n;
	if(ix<0x4016cbe4) {  /* |x| < 3pi/4, special case with n=+-1 */
	    if(hx>0) {
		z = x - pio2_1;
		if((ix&0xfffffff0)!=0x3fc90fd0) { /* 24+24 bit pi OK */
		    u = z - pio2_1t;
		    *y1 = (z-u)-pio2_1t;
		} else {		/* near pi/2, use 24+24+24 bit pi */
		    z -= pio2_2;
		    u = z - pio2_2t;
		    *y1 = (z-u)-pio2_2t;
		}
		*y0 = u;
		return 1;
	    } else {	/* negative x */
		z = x + pio2_1;
		if((ix&0xfffffff0)!=0x3fc90fd0) { /* 24+24 bit pi OK */
		    u = z + pio2_1t;
		    *y1 = (z-u)+pio2_1t;
		} else {		/* near pi/2, use 24+24+24 bit pi */
		    z += pio2_2;
		    u = z + pio2_2t;
		    *y1 = (z-u)+pio2_2t;
		}
		*y0 = u;
		return -1;
	    }
	}
	/* medium size */
	t  = fabsf(x);
	n  = (__int32_t) (t*invpio2+r_half);
	fn = (float)n;
	r  = t-fn*pio2_1;
	w  = fn*pio2_1t;	/* 1st round good to 40 bit */
	if(n<32&&(ix&0xffffff00)!=npio2_hw[n-1]) {
	    u = r-w;	/* quick check no cancellation */
	} else {
	    __uint32_t high;
	    j  = ix>>23;
	    u = r-w;
	    high = lfbits(u);
	    i = j-((high>>23)&0xff);
	    if(i>8) {  /* 2nd iteration needed, good to 57 */
		t  = r;
		w  = fn*pio2_2;
		r  = t-w;
		w  = fn*pio2_2t-((t-r)-w);
		u = r-w;
		high = lfbits(u);
		i = j-((high>>23)&0xff);
		if(i>25)  {	/* 3rd iteration need, 74 bits acc */
		    t  = r;	/* will cover all possible cases */
		    w  = fn*pio2_3;
		    r  = t-w;
		    w  = fn*pio2_3t-((t-r)-w);
		    u = r-w;
		}
	    }
	}
	t = (r-u)-w;
	if(hx<0) {*y0 = -u; *y1 = -t; return -n;}
	*y0 = u;
	*y1 = t;
	return n;
}

/* |x| > 2^7*pi/2, inf or NaN: the original sf_sin.c path (rem_pio2f above hands these to
   __ieee754_rem_pio2f) */
static __attribute__((noinline)) float sinf_big(float x)
{
	float y[2];
	__int32_t n,ix;
	GET_FLOAT_WORD(ix,x);
	ix &= 0x7fffffff;
	if (ix>=0x7f800000) return x-x;
	n = __ieee754_rem_pio2f(x,y);
	switch(n&3) {
		case 0: return  k_sinf(y[0],y[1],1);
		case 1: return  k_cosf(y[0],y[1]);
		case 2: return -k_sinf(y[0],y[1],1);
		default:
			return -k_cosf(y[0],y[1]);
	}
}

static __attribute__((noinline)) float cosf_big(float x)
{
	float y[2];
	__int32_t n,ix;
	GET_FLOAT_WORD(ix,x);
	ix &= 0x7fffffff;
	if (ix>=0x7f800000) return x-x;
	n = __ieee754_rem_pio2f(x,y);
	switch(n&3) {
		case 0: return  k_cosf(y[0],y[1]);
		case 1: return -k_sinf(y[0],y[1],1);
		case 2: return -k_cosf(y[0],y[1]);
		default:
		        return  k_sinf(y[0],y[1],1);
	}
}

float sinf(float x)
{
	float y0,y1,v;
	__int32_t n,hx,ix;
	hx = lfbits(x);
	ix = hx&0x7fffffff;
	if(ix <= 0x3f490fd8) {			/* |x| ~< pi/4 */
	    if(ix<0x32000000) return x;		/* __kernel_sinf: |x| < 2**-27 */
	    return lk_sin0(x);
	}
	if(ix > 0x43490f80) return sinf_big(x);	/* large, inf or NaN */
	n = lrem_pio2f(x,hx,ix,&y0,&y1);
	ix = lfbits(y0)&0x7fffffff;
	/* n&3: 0 sin, 1 cos, 2 -sin, 3 -cos */
	v = (n&1) ? lk_cos(y0,y1,ix) : lk_sin1(y0,y1,ix);
	return (n&2) ? -v : v;
}

float cosf(float x)
{
	float y0,y1,v;
	__int32_t n,hx,ix;
	hx = lfbits(x);
	ix = hx&0x7fffffff;
	if(ix <= 0x3f490fd8)			/* |x| ~< pi/4 */
	    return lk_cos(x,0.0f,ix);
	if(ix > 0x43490f80) return cosf_big(x);	/* large, inf or NaN */
	n = lrem_pio2f(x,hx,ix,&y0,&y1);
	ix = lfbits(y0)&0x7fffffff;
	/* n&3: 0 cos, 1 -sin, 2 -cos, 3 sin */
	v = (n&1) ? lk_sin1(y0,y1,ix) : lk_cos(y0,y1,ix);
	return ((n+1)&2) ? -v : v;
}

#if defined(RE4DC_SINCOS) && RE4DC_SINCOS
static __attribute__((noinline)) void sincosf_big(float x, float *s, float *c)
{
	float y[2];
	__int32_t n,ix;
	GET_FLOAT_WORD(ix,x);
	ix &= 0x7fffffff;
	if (ix>=0x7f800000) {
	    *s = x-x;
	    *c = x-x;
	    return;
	}
	n = __ieee754_rem_pio2f(x,y);
	switch(n&3) {
		case 0: *s =  k_sinf(y[0],y[1],1); *c =  k_cosf(y[0],y[1]); break;
		case 1: *s =  k_cosf(y[0],y[1]);   *c = -k_sinf(y[0],y[1],1); break;
		case 2: *s = -k_sinf(y[0],y[1],1); *c = -k_cosf(y[0],y[1]); break;
		default:
			*s = -k_cosf(y[0],y[1]);   *c =  k_sinf(y[0],y[1],1); break;
	}
}

#if defined(RE4DC_TRIG_FSCA) && RE4DC_TRIG_FSCA
#define re4dc_sincosf re4dc_exact_sincosf	/* GAME_TRIG_FSCA: this exact body under another name (end of file) */
#endif
void re4dc_sincosf(float x, float *s, float *c)
{
	float y0,y1,ks,kc,a,b;
	__int32_t n,hx,ix;
	hx = lfbits(x);
	ix = hx&0x7fffffff;
#if defined(RE4DC_SH4_APPROX_LOGIC) && RE4DC_SH4_APPROX_LOGIC
	/* SH4_APPROX_LOGIC (Bruceleeto fe2aed7945): sin / cos from shz_sincosf (ftrc + FSCA) for every caller; large,
	 * inf and NaN arguments keep the exact sincosf_big path. */
	if(ix > 0x43490f80) {			/* large, inf or NaN */
	    sincosf_big(x,s,c);
	    return;
	}
	{
	    shz_sincos_t r = shz_sincosf(x);
	    *s = r.sin;
	    *c = r.cos;
	    return;
	}
#endif
	if(ix <= 0x3f490fd8) {			/* |x| ~< pi/4 */
	    if(ix<0x32000000) {			/* both kernels: |x| < 2**-27 */
		*s = x;
		*c = one;
		return;
	    }
	    *s = lk_sin0(x);
	    *c = lk_cos(x,0.0f,ix);
	    return;
	}
	if(ix > 0x43490f80) {			/* large, inf or NaN */
	    sincosf_big(x,s,c);
	    return;
	}
	n = lrem_pio2f(x,hx,ix,&y0,&y1);
	ix = lfbits(y0)&0x7fffffff;
	ks = lk_sin1(y0,y1,ix);
	kc = lk_cos(y0,y1,ix);
	/* n&3: (s, c) = 0 (ks, kc), 1 (kc, -ks), 2 (-ks, -kc), 3 (-kc, ks) */
	a = (n&1) ? kc : ks;
	b = (n&1) ? ks : kc;
	*s = (n&2) ? -a : a;
	*c = ((n+1)&2) ? -b : b;
}
#endif /* RE4DC_SINCOS */
#endif /* RE4DC_TRIG_LEAN */

#if defined(RE4DC_TRIG_FSCA) && RE4DC_TRIG_FSCA
#if !(defined(RE4DC_TRIG_LEAN) && RE4DC_TRIG_LEAN && defined(RE4DC_SINCOS) && RE4DC_SINCOS)
#error "GAME_TRIG_FSCA needs GAME_TRIG_LEAN=1 and GAME_SINCOS=1"
#endif
#undef re4dc_sincosf
/* GAME_TRIG_FSCA (game30.mk; lane fm 2026-10-05). Last-bit FP policy (user decision 2026-09-23 (3)), NOT
 * exact: re4dc_sincosf -- RotMatrix's three angles (its callers other than the parts when GAME_ROT_FSCA=1
 * runs those), PSMTXRotRad and PSMTXRotAxisRad -- from FSCA plus the residual correction
 * (platform/include/re4dc_fsca.h): |x| <= 2 pi directly, 2 pi < |x| <= 2^7 pi/2 after the exact reduction
 * above (lrem_pio2f: FSCA index + n * 16384, the tail y1 added to the residual). |x| < 2^-27 (sin = x,
 * cos = 1), larger and non-finite arguments keep the exact results. sinf and cosf stay exact.
 * =2: check build, re4dc_exact_sincosf runs beside every call, the FSCA results are returned and the
 * differences counted ("TRIGF" log lines every 65536 calls).
 */
#include "platform/include/re4dc_fsca.h"
void re4dc_exact_sincosf(float x, float *s, float *c);

#if RE4DC_TRIG_FSCA == 2
void re4dc_log(const char *fmt, ...);
/* per output (0 sin, 1 cos): identical words, |difference| <= 2^-27 .. 2^-21 and above; the largest
   |difference| (word) and its x; results differing by more than 4 of their own ulps (small results) */
static unsigned trigf_calls, trigf_hist[2][9], trigf_max[2], trigf_maxx[2], trigf_rel4[2];
static void trigf_note(int o, float x, float got, float ref)
{
	float d = got - ref;
	__int32_t gb = lfbits(got), rb = lfbits(ref), db, h, u;
	if (d < 0.0f) d = -d;
	db = lfbits(d);
	if (gb == rb) h = 0;
	else if (d <= 0x1p-27f) h = 1;
	else if (d <= 0x1p-26f) h = 2;
	else if (d <= 0x1p-25f) h = 3;
	else if (d <= 0x1p-24f) h = 4;
	else if (d <= 0x1p-23f) h = 5;
	else if (d <= 0x1p-22f) h = 6;
	else if (d <= 0x1p-21f) h = 7;
	else h = 8;
	trigf_hist[o][h]++;
	if (h && (unsigned) db > trigf_max[o]) {
	    trigf_max[o] = db;
	    trigf_maxx[o] = lfbits(x);
	}
	u = gb - rb;
	if ((gb ^ rb) < 0 || u > 4 || u < -4) trigf_rel4[o]++;
}
static void trigf_report(void)
{
	re4dc_log("TRIGF calls=%u sin same=%u le27=%u le26=%u le25=%u le24=%u le23=%u le22=%u le21=%u gt21=%u max=%08x x=%08x rel4=%u\n",
	          trigf_calls, trigf_hist[0][0], trigf_hist[0][1], trigf_hist[0][2], trigf_hist[0][3], trigf_hist[0][4],
	          trigf_hist[0][5], trigf_hist[0][6], trigf_hist[0][7], trigf_hist[0][8], trigf_max[0], trigf_maxx[0],
	          trigf_rel4[0]);
	re4dc_log("TRIGF calls=%u cos same=%u le27=%u le26=%u le25=%u le24=%u le23=%u le22=%u le21=%u gt21=%u max=%08x x=%08x rel4=%u\n",
	          trigf_calls, trigf_hist[1][0], trigf_hist[1][1], trigf_hist[1][2], trigf_hist[1][3], trigf_hist[1][4],
	          trigf_hist[1][5], trigf_hist[1][6], trigf_hist[1][7], trigf_hist[1][8], trigf_max[1], trigf_maxx[1],
	          trigf_rel4[1]);
}
#endif

void re4dc_sincosf(float x, float *s, float *c)
{
	float y0,y1,a,b;
	__int32_t n,hx,ix;
	hx = lfbits(x);
	ix = hx&0x7fffffff;
	if(ix <= RE4DC_FSCA_XMAX_BITS) {	/* |x| <= 2 pi */
	    if(ix<0x32000000) {			/* |x| < 2**-27: the exact results */
		a = x;
		b = one;
	    } else {
		RE4DC_FSCA_SINCOS(x, a, b, "fr2", "fr3", "dr2");
	    }
	} else if(ix <= 0x43490f80) {		/* |x| <= 2^7*pi/2: the exact reduction, then FSCA */
	    n = lrem_pio2f(x,hx,ix,&y0,&y1);
	    RE4DC_FSCA_SINCOS_RED(y0, y1, n, a, b, "fr2", "fr3", "dr2");
	} else {				/* large, inf or NaN: exact */
	    sincosf_big(x,s,c);
	    return;
	}
#if RE4DC_TRIG_FSCA == 2
	{
	    float rs, rc;
	    re4dc_exact_sincosf(x, &rs, &rc);
	    trigf_note(0, x, a, rs);
	    trigf_note(1, x, b, rc);
	    if ((++trigf_calls & 0xFFFF) == 0) trigf_report();
	}
#endif
	*s = a;
	*c = b;
}
#endif /* RE4DC_TRIG_FSCA */

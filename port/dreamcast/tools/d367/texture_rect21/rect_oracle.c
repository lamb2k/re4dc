/* Rectangular base oracle using the independent pinned pvrtex decoder. */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "pvr_texture_decoder.h"
int rect_oracle_decode(const void* p,size_t n,unsigned fmt,unsigned w,unsigned h,unsigned char* out,size_t cap){
 const ptPixelFormat formats[3]={PT_RGB565,PT_ARGB1555,PT_ARGB4444};
 if(fmt>2||w<8||h<8||w>1024||h>1024||(w&(w-1))||(h&(h-1))||cap<w*h*4)return -1;
 if(n!=CalcTextureSize(w,h,formats[fmt],0,1,2048))return -2;
 PvrTexDecoder d;ptdInit(&d);ptdSetSize(&d,w,h,0);ptdSetPixelFormat(&d,formats[fmt]);
 ptdSetCompressedSource(&d,NULL,p,PVR_FULL_CODEBOOK,0);ptdDecode(&d);
 memcpy(out,d.result_mips[0],w*h*4);ptdFree(&d);return w*h*4;
}
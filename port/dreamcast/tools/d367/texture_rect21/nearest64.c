/* Host-only exact nearest-vector accelerator; no Dreamcast/runtime code. */
#include <stddef.h>
#include <stdint.h>
#include <limits.h>
int rect21_nearest64(const int32_t *target,size_t nt,const int32_t *book,size_t nb,size_t width,uint8_t *out){
 if(!target||!book||!out||!nt||nt>1000000||!nb||nb>256||(width!=4&&width!=16))return -1;
 for(size_t i=0;i<nt*width;++i)if(target[i]<0||target[i]>65025)return -2;
 for(size_t i=0;i<nb*width;++i)if(book[i]<0||book[i]>65025)return -2;
 for(size_t i=0;i<nt;++i){uint64_t best=UINT64_MAX;unsigned chosen=0;
  for(size_t j=0;j<nb;++j){uint64_t total=0;
   for(size_t k=0;k<width;++k){int64_t d=(int64_t)target[i*width+k]-book[j*width+k];total+=(uint64_t)(d*d);if(total>=best)break;}
   if(total<best){best=total;chosen=(unsigned)j;}
  }out[i]=(uint8_t)chosen;
 }return 0;
}
/* Exact quarter-channel metric at original2:1 texel centers under normalized periodic bilinear UVs. */
int rect21_error4(const uint8_t *src,const uint8_t *square,unsigned side,uint64_t *sse4,unsigned *maximum4){
 if(!src||!square||!sse4||!maximum4||side<8||side>1024||(side&(side-1)))return -1;
 uint64_t sum=0;unsigned worst=0;
 for(unsigned y=0;y<side;++y)for(unsigned x=0;x<2*side;++x){unsigned center=x/2;
  unsigned left=(x&1)?center:(center+side-1)%side,right=(left+1)%side;
  unsigned wl=(x&1)?3:1,wr=4-wl;
  for(unsigned c=0;c<3;++c){int d=4*(int)src[(y*2*side+x)*4+c]-(int)(wl*square[(y*side+left)*4+c]+wr*square[(y*side+right)*4+c]);
   unsigned a=(unsigned)(d<0?-d:d);sum+=(uint64_t)a*a;if(a>worst)worst=a;
  }
 }*sse4=sum;*maximum4=worst;return 0;
}
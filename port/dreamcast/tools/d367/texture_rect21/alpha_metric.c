/* Host-only exact normalized periodic source-center RGBA error. */
#include <stddef.h>
#include <stdint.h>
int alpha_metric(const uint8_t*src,const uint8_t*sq,unsigned w,unsigned side,uint64_t*sse,unsigned*max,unsigned*threshold_disagreements){
 if(!src||!sq||!sse||!max||!threshold_disagreements||side<8||side>256||(side&(side-1))||w%side||w>1024)return -1;
 unsigned r=w/side;if(r!=2&&r!=4&&r!=8)return -2;unsigned den=2*r;for(unsigned c=0;c<4;++c)sse[c]=max[c]=0;*threshold_disagreements=0;
 for(unsigned y=0;y<side;++y)for(unsigned x=0;x<w;++x){unsigned q=x/r,k=x%r,left,wr;if(2*k+1<r){left=(q+side-1)%side;wr=2*k+1+r;}else{left=q;wr=2*k+1-r;}unsigned right=(left+1)%side,wl=den-wr;
  for(unsigned c=0;c<4;++c){unsigned v=wl*sq[(y*side+left)*4+c]+wr*sq[(y*side+right)*4+c];int d=(int)(den*src[(y*w+x)*4+c])-(int)v;unsigned a=d<0?-d:d;sse[c]+=(uint64_t)a*a;if(a>max[c])max[c]=a;if(c==3&&(src[(y*w+x)*4+c]>=128)!=(v>=128*den))++*threshold_disagreements;}
 }return 0;
}

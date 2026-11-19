/* eng-look: effects, included by native_layers.inc after the billboard pool.
   1. Colour as the source sets it (esp_sub.cpp ChannelSet / the GX TEV): Tool_flg 0x80 scales the colour by 4 and
      0x20000 the alpha by 4 (clamped), unless Tool_flg 0x40.
   2. The frame-alpha glow (filter03, driven by effect 0x46): the effects that write the frame's alpha (Tool_flg
      0x8000 without the 0x200000 constant-zero alpha) are the glow mask; the filter blurs that alpha at quarter size
      and adds it over the screen in the driver's colour x alpha / 255, doubled by its TEV scale. Here each such
      sprite is drawn once more, additive (source alpha, one), 1.25 x its size, with a baked white texture whose
      alpha is the sprite's alpha shrunk to the middle 80% and blurred (the bake's glow header, kept in the record's
      second key word); overlapping glow sprites share their weight (1 / sqrt(neighbours)) so a cluster does not
      add up past the source's single alpha. CS_GLOW 0 turns it off.
   3. Effect density cap (CS_EFFECTS): step 1 drops sprites under 1.5 pixels and nearly clear ones (alpha under 3);
      steps 2 and 3 also keep only the 64 / 32 largest by projected area x alpha, ranked stably with a 25% bonus
      for a sprite (by effect slot) drawn last picture. */
#include "content.h"
static uint16_t particle_slot[1024];
static Billboard glow_src[64];static unsigned glow_hdr[64],glow_n,glow_on;static uint32_t glow_rgb;
static uint8_t fx_drawn_last[512];   /* per effect slot: drawn last picture (cap hysteresis) */
static uint32_t fx_color(const NativeEffect* v){
    float c[4]={v->rgba[0],v->rgba[1],v->rgba[2],v->rgba[3]};
    if(!(v->tool&0x40)){
        if(v->tool&0x80){c[0]*=4;c[1]*=4;c[2]*=4;}
        if(v->tool&0x20000)c[3]*=4;
    }
    return argb4(c);
}
static void fx_frame(void){glow_n=0;glow_on=0;glow_rgb=0;}
/* the glow driver: Esp46_Trans colour = rgb x a / 255 (truncated), doubled by the filter's TEV scale */
static void fx_glow_driver(const NativeEffect* v){
    float a=v->rgba[3]*(1.f/255);unsigned rgb=0;
    for(unsigned k=0;k<3;k++){unsigned c=m1_byte(v->rgba[k]*a);c=c*2>255?255:c*2;rgb|=c<<(16-8*k);}
    glow_rgb=rgb;glow_on=1;
}
static void fx_glow_note(const NativeEffect* v,const Billboard* b){
    if(m1_content[CS_GLOW] && v->fnv!=~0u && glow_n<64){glow_src[glow_n]=*b;glow_hdr[glow_n++]=v->fnv;}
}
static void fx_glow_draw(NativeScene* s){
    if(!m1_content[CS_GLOW] || !glow_on || !glow_n)return;
    static const float uv[]={0,0,1,1};unsigned last=~0u;
    for(unsigned i=0;i<glow_n;i++){
        const Billboard* b=glow_src+i;float r=m1_maxf(b->rx,b->ry);unsigned k=0;
        for(unsigned j=0;j<glow_n;j++){float dx=glow_src[j].x-b->x,dy=glow_src[j].y-b->y;k+=dx*dx+dy*dy<r*r;}
        float a=(float)(b->color>>24)/sqrtf((float)k);
        if(last!=glow_hdr[i]){last=glow_hdr[i];submit_header(&s->assets,last);}
        rectangle(b->x,b->y,b->iw,1.25f*b->rx,1.25f*b->ry,b->angle,uv,m1_byte(a)<<24|glow_rgb);
    }
    m1_content_counts[6]+=glow_n;
}
static int fx_score_cmp(const void* a,const void* b){float x=*(const float*)a,y=*(const float*)b;return (x<y)-(x>y);}
/* Applies the density cap in place (before the depth sort); returns the new count. */
static unsigned fx_cap(Billboard* p,unsigned count){
    unsigned step=m1_content[CS_EFFECTS];
    if(!step)return count;
    unsigned n=0;
    for(unsigned i=0;i<count;i++){
        if((p[i].rx<1.5f && p[i].ry<1.5f) || (p[i].color>>24)<3)continue;
        p[n]=p[i];particle_slot[n]=particle_slot[i];n++;
    }
    unsigned cap=step==2?64:step==3?32:1024;
    if(n>cap){
        static float score[1024][2];
        for(unsigned i=0;i<n;i++){
            float sc=p[i].rx*p[i].ry*(float)(p[i].color>>24);
            if(fx_drawn_last[particle_slot[i]&511])sc*=1.25f;
            score[i][0]=sc;score[i][1]=(float)i;
        }
        qsort(score,n,sizeof(score[0]),fx_score_cmp);
        float floor=score[cap-1][0];unsigned m=0;
        for(unsigned i=0;i<n && m<cap;i++){
            const Billboard* q=p+i;float sc=q->rx*q->ry*(float)(q->color>>24)*(fx_drawn_last[particle_slot[i]&511]?1.25f:1.f);
            if(sc>=floor){p[m]=*q;particle_slot[m]=particle_slot[i];m++;}
        }
        n=m;
    }
    m1_content_counts[7]+=count-n;
    memset(fx_drawn_last,0,sizeof(fx_drawn_last));
    for(unsigned i=0;i<n;i++)fx_drawn_last[particle_slot[i]&511]=1;
    return n;
}

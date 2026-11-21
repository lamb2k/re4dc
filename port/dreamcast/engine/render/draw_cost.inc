/* Lane eng-draw1: the definitions behind draw_cost.h (included by render.c in the native images). Measurement only. */
#include "draw_cost.h"
#include <arch/timer.h>
#include <stdio.h>
uint32_t dc_n[DC_COUNT];
unsigned dc_clip=DC_W_CLIPTRIS;
uint32_t dc_arm_now,dc_lab_bench,dc_frame_base;
unsigned dc_interleave,dc_mute;
volatile union DcNan dc_nan={0x7fc00000u};
extern volatile uint32_t m1_frame;
#define DC_PICS 640
#define DC_PH 11   /* the spans between consecutive stamps DS_VIS0 .. DS_HUD1 */
#define DC_PC 4    /* per-picture counters kept for the reader */
static uint16_t dc_pic[DC_PICS][DC_PH];
static uint32_t dc_picn[DC_PICS][DC_PC];
static const uint8_t dc_pick[DC_PC]={DC_W_CORNERS,DC_W_CLIPTRIS,DC_A_CORNERS,DC_A_POS};
static uint32_t dc_t[DS_COUNT],dc_have;
static uint64_t dc_sum[DC_COUNT];
static uint32_t dc_max[DC_COUNT],dc_maxat[DC_COUNT],dc_pics;
static unsigned dc_lo=41,dc_hi=640;   /* the E1 selector's pictures; the bench sets 1..600 a window */
static const char* const dc_phase_name[DC_PH]={"select","begin","sky","preworld","worldOP","actors","worldPT","listgap",
                                              "worldTR","TRextra","hud"};
static const char* const dc_count_name[DC_COUNT]={"w_pieces","w_places","w_headers","w_staged","w_strips","w_corners",
    "w_clipstrips","w_cliptris","w_clipout","w_meshlets","w_selected","a_calls","a_parts","a_parts_bound","a_ws","a_pos",
    "a_nrm","a_nrmlights","a_lights","a_headers","a_strips","a_strips_out","a_corners","a_clipstrips","a_cliptris",
    "a_clipout","h_rects"};
static int dc_boot(const char* path){file_t f=fs_open(path,O_RDONLY);if(f<0)return 0;fs_close(f);return 1;}
/* E1 images: the boot sets, read once when the pack opens (before play) */
void dc_lab_open(void){
    static int done;if(done)return;done=1;
    if(dc_boot("/cd/DLA"))dc_interleave=1;else if(dc_boot("/cd/DLB"))dc_interleave=2;else if(dc_boot("/cd/DLC"))dc_interleave=3;
    static const char* const sets[3]={
        "picture % 6: 1 stage twice, 2 copy twice, 3 select twice, 4 HUD twice, 5 near plane not a number",
        "picture % 5: 1 weight sets twice, 2 normals lit twice, 3 actor emission twice, 4 2 ms delay in the world OP pass",
        "picture % 4: 1 world without a stage (X), 2 world copy v2 (V), 3 world near clamp instead of clipping (G)"};
    if(dc_interleave)printf("DC LAB set %c: %s\n",'A'+dc_interleave-1,sets[dc_interleave-1]);
}
static uint32_t dc_arms_for(unsigned idx){
    if(dc_interleave==1){static const uint32_t a[6]={0,DL_STAGE2,DL_COPY2,DL_SELECT2,DL_HUD2,DL_NAN};return a[idx%6];}
    if(dc_interleave==2){static const uint32_t b[5]={0,DL_WS2,DL_LIGHT2,DL_EMIT2,DL_DELAY};return b[idx%5];}
    if(dc_interleave==3){static const uint32_t c[4]={0,DL_DIRECT,DL_COPYV2,DL_CLAMP};return c[idx%4];}
    return dc_lab_bench;
}
void dc_window_begin(void){
    dc_lo=1;dc_hi=600;dc_pics=0;
    for(unsigned k=0;k<DC_COUNT;k++){dc_sum[k]=0;dc_max[k]=0;dc_maxat[k]=0;}
}
static void dc_finish(void){
    const unsigned idx=m1_frame-dc_frame_base;
    uint32_t t=dc_t[DS_VIS0];
    uint16_t* row=idx>=1&&idx<=DC_PICS?dc_pic[idx-1]:NULL;
    for(unsigned k=1;k<DS_COUNT;k++){
        uint32_t v=(dc_have>>k&1)?dc_t[k]:t;   /* a stamp not reached this picture (the hill: no world) spans 0 */
        if(row)row[k-1]=(uint16_t)(v-t>65535?65535:v-t);
        t=v;
    }
    if(row)for(unsigned j=0;j<DC_PC;j++)dc_picn[idx-1][j]=dc_n[dc_pick[j]];
    if(idx>=dc_lo && idx<=dc_hi){
        dc_pics++;
        for(unsigned k=0;k<DC_COUNT;k++){dc_sum[k]+=dc_n[k];if(dc_n[k]>dc_max[k]){dc_max[k]=dc_n[k];dc_maxat[k]=idx;}}
    }
}
void dc_stamp(unsigned k){
    const uint32_t now=(uint32_t)timer_us_gettime64();
    if(k==DS_VIS0){
        for(unsigned j=0;j<DC_COUNT;j++)dc_n[j]=0;
        dc_have=0;dc_arm_now=dc_arms_for(m1_frame-dc_frame_base);
    }
    dc_t[k]=now;dc_have|=1u<<k;
    if(k==DS_HUD1)dc_finish();
}
static void dc_print(const char* tag){
    static uint16_t v[DC_PICS];
    for(unsigned p=0;p<DC_PH;p++){
        unsigned n=0,worst=0,at=0;uint64_t sum=0;
        for(unsigned i=dc_lo;i<=dc_hi && i<=DC_PICS;i++){unsigned x=dc_pic[i-1][p];v[n++]=x;sum+=x;if(x>worst){worst=x;at=i;}}
        if(!n)continue;
        for(unsigned i=1;i<n;i++){uint16_t x=v[i];unsigned j=i;while(j && v[j-1]>x){v[j]=v[j-1];j--;}v[j]=x;}
        printf("%s PHASE %s m%lu p%lu w%lu@%u (us, pictures %u-%u)\n",tag,dc_phase_name[p],(unsigned long)(sum/n),
               (unsigned long)v[n-1-n/100],(unsigned long)worst,at,dc_lo,dc_hi);
    }
    for(unsigned k=0;k<DC_COUNT;k++)
        printf("%s COUNT %s m%lu w%lu@%lu (sum %lu over %lu pictures)\n",tag,dc_count_name[k],
               (unsigned long)(dc_pics?dc_sum[k]/dc_pics:0),(unsigned long)dc_max[k],(unsigned long)dc_maxat[k],
               (unsigned long)dc_sum[k],(unsigned long)dc_pics);
}
void native_draw_report(void){
    printf("DC BEGIN set %u pictures %u-%u phases select begin sky preworld worldOP actors worldPT listgap worldTR TRextra hud"
           " | counters w_corners w_cliptris a_corners a_pos\n",dc_interleave,dc_lo,dc_hi);
    dc_print("DC");
    /* per-picture lines carry the trace prefix "T" so the console loop's report leaves them out (skip=T, the default):
       they made the fight's report reach its cap (no end line, the scene FAILED); the serial log keeps them */
    for(unsigned i=1;i<=DC_PICS && i<=dc_hi;i++){
        const uint16_t* r=dc_pic[i-1];const uint32_t* c=dc_picn[i-1];
        printf("T DCP %u %u %u %u %u %u %u %u %u %u %u %u %lu %lu %lu %lu\n",i,r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],
               r[10],(unsigned long)c[0],(unsigned long)c[1],(unsigned long)c[2],(unsigned long)c[3]);
    }
    printf("DC END\n");
}
void native_draw_report_window(unsigned window){
    char tag[16];snprintf(tag,sizeof(tag),"DCB %u",window);
    printf("DCB %u BEGIN arms %lx\n",window,(unsigned long)dc_lab_bench);
    dc_print(tag);
}

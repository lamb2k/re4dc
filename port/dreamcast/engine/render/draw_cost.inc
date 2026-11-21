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
static unsigned dc_census_seen;   /* the census ran in this window (or scene): only then are its counters printed */
static unsigned dc_lo=41,dc_hi=640;   /* the E1 selector's pictures; the bench sets 1..600 a window */
static const char* const dc_phase_name[DC_PH]={"select","begin","sky","preworld","worldOP","actors","worldPT","listgap",
                                              "worldTR","TRextra","hud"};
static const char* const dc_count_name[DC_COUNT]={"w_pieces","w_places","w_headers","w_staged","w_strips","w_corners",
    "w_clipstrips","w_cliptris","w_clipout","w_meshlets","w_selected","w_facedrop","a_calls","a_parts","a_parts_bound","a_ws","a_pos",
    "a_nrm","a_nrmlights","a_lights","a_headers","a_strips","a_strips_out","a_corners","a_clipstrips","a_cliptris",
    "a_clipout","h_rects",
    "v_w_tris","v_w_off","v_w_nocull","v_w_neg","v_w_pos","v_w_area_nocull","v_w_area_neg","v_w_area_pos",
    "v_w_deadstrips_n","v_w_deadstrips_p","v_w_deadcorners_n","v_w_deadcorners_p","v_w_deadvtx_n","v_w_deadvtx_p",
    "v_w_clip_front","v_w_clip_behind","v_w_clip_cross","v_tr_area",
    "v_a_tris","v_a_off","v_a_nocull","v_a_neg","v_a_pos","v_a_area_nocull","v_a_area_neg","v_a_area_pos",
    "v_a_deadstrips_n","v_a_deadstrips_p","v_a_deadcorners_n","v_a_deadcorners_p","v_a_deadpos_n","v_a_deadpos_p",
    "v_a_deadnrm_n","v_a_deadnrm_p","v_a_iw_neg","v_a_iw_pos","v_a_cullmode_cw","v_a_cullmode_ccw",
    "v_w_cullmode_cw","v_w_cullmode_ccw",
    "v_a_nc_neg","v_a_nc_pos","v_a_nc_area_neg","v_a_nc_area_pos","v_a_cdeadstrips_n","v_a_cdeadstrips_p",
    "v_a_cdeadcorners_n","v_a_cdeadcorners_p","v_a_cdeadpos_n","v_a_cdeadpos_p"};
_Static_assert(sizeof(dc_count_name)/sizeof(dc_count_name[0])==DC_COUNT,"one name a counter");
/* ---- census (arm Z / DLV): measurement only ---- */
static float dc_clip_area(float x0,float y0,float x1,float y1,float x2,float y2){
    float px[12],py[12],qx[12],qy[12];unsigned n=3;
    px[0]=x0;py[0]=y0;px[1]=x1;py[1]=y1;px[2]=x2;py[2]=y2;
    for(unsigned e=0;e<4;e++){   /* Sutherland-Hodgman against x>=0, x<=640, y>=0, y<=480 */
        unsigned m=0;
        for(unsigned i=0;i<n;i++){
            float ax=px[i],ay=py[i],bx=px[(i+1)%n],by=py[(i+1)%n];
            float da=e==0?ax:e==1?640.f-ax:e==2?ay:480.f-ay,db=e==0?bx:e==1?640.f-bx:e==2?by:480.f-by;
            if(da>=0){qx[m]=ax;qy[m]=ay;m++;}
            if((da>=0)!=(db>=0)){float t=da/(da-db);qx[m]=ax+(bx-ax)*t;qy[m]=ay+(by-ay)*t;m++;}
        }
        n=m;for(unsigned i=0;i<n;i++){px[i]=qx[i];py[i]=qy[i];}
        if(n<3)return 0;
    }
    float a=0;for(unsigned i=0;i<n;i++){unsigned j=(i+1)%n;a+=px[i]*py[j]-px[j]*py[i];}
    return a<0?-.5f*a:.5f*a;
}
static int dc_offscreen(float x0,float y0,float x1,float y1,float x2,float y2){
    return (x0<0&&x1<0&&x2<0)||(x0>640&&x1>640&&x2>640)||(y0<0&&y1<0&&y2<0)||(y0>480&&y1>480&&y2>480);
}
/* cull: the header's culling bits (0 none, 1 small, 2 CCW, 3 CW). The triangle is given in the strip's drawing order
   (odd triangles already swapped). kept: bit 1 if kept when the negative-area sign is the culled one, bit 2 when the
   positive one is. */
void dc_census_tri(unsigned b,float x0,float y0,float z0,float x1,float y1,float z1,float x2,float y2,float z2,
                   unsigned cull,unsigned* kept){
    *kept=0;dc_n[b]++;
    if(dc_offscreen(x0,y0,x1,y1,x2,y2)){dc_n[b+1]++;return;}
    float s=(x1-x0)*(y2-y0)-(x2-x0)*(y1-y0),area=dc_clip_area(x0,y0,x1,y1,x2,y2);
    if(b==DC_V_A_TRIS){
        dc_n[cull==3?DC_V_A_CULLMODE_CW:cull==2?DC_V_A_CULLMODE_CCW:DC_V_A_NOCULL+0]+=cull>=2;
        uint32_t iw=(uint32_t)((z0+z1+z2)*(16777216.f/3.f));dc_n[s<0?DC_V_A_IW_NEG:DC_V_A_IW_POS]+=iw;
    }else dc_n[cull==3?DC_V_W_CULLMODE_CW:DC_V_W_CULLMODE_CCW]+=cull>=2;
    if(cull<2){dc_n[b+2]++;dc_n[b+5]+=(uint32_t)area;
        if(b==DC_V_A_TRIS){if(s<0){dc_n[DC_V_A_NC_NEG]++;dc_n[DC_V_A_NC_AREA_NEG]+=(uint32_t)area;*kept=3|8;}
                           else{dc_n[DC_V_A_NC_POS]++;dc_n[DC_V_A_NC_AREA_POS]+=(uint32_t)area;*kept=3|4;}return;}
        *kept=3;return;}
    if(s<0){dc_n[b+3]++;dc_n[b+6]+=(uint32_t)area;*kept=2|8;}   /* kept only if the positive sign is the culled one */
    else{dc_n[b+4]++;dc_n[b+7]+=(uint32_t)area;*kept=1|4;}
}
void dc_census_tr(float x0,float y0,float x1,float y1,float x2,float y2){
    if(!dc_offscreen(x0,y0,x1,y1,x2,y2))dc_n[DC_V_TR_AREA]+=(uint32_t)dc_clip_area(x0,y0,x1,y1,x2,y2);
}
static int dc_boot(const char* path){file_t f=fs_open(path,O_RDONLY);if(f<0)return 0;fs_close(f);return 1;}
/* E1 images: the boot sets, read once when the pack opens (before play) */
void dc_lab_open(void){
    static int done;if(done)return;done=1;
    if(dc_boot("/cd/DLA"))dc_interleave=1;else if(dc_boot("/cd/DLB"))dc_interleave=2;else if(dc_boot("/cd/DLC"))dc_interleave=3;
    else if(dc_boot("/cd/DLV"))dc_interleave=4;
    static const char* const sets[4]={
        "picture % 6: 1 stage twice, 2 copy twice, 3 select twice, 4 HUD twice, 5 near plane not a number",
        "picture % 5: 1 weight sets twice, 2 normals lit twice, 3 actor emission twice, 4 2 ms delay in the world OP pass",
        "picture % 4: 1 world without a stage (X), 2 world copy v2 (V), 3 world near clamp instead of clipping (G)",
        "every picture: the census (counts of invisible work; never a timing run)"};
    if(dc_interleave)printf("DC LAB set %c: %s\n",'A'+dc_interleave-1,sets[dc_interleave-1]);
}
static uint32_t dc_arms_for(unsigned idx){
    if(dc_interleave==1){static const uint32_t a[6]={0,DL_STAGE2,DL_COPY2,DL_SELECT2,DL_HUD2,DL_NAN};return a[idx%6];}
    if(dc_interleave==2){static const uint32_t b[5]={0,DL_WS2,DL_LIGHT2,DL_EMIT2,DL_DELAY};return b[idx%5];}
    if(dc_interleave==3){static const uint32_t c[4]={0,DL_DIRECT,DL_COPYV2,DL_CLAMP};return c[idx%4];}
    if(dc_interleave==4)return DL_CENSUS;
    return dc_lab_bench;
}
void dc_window_begin(void){
    dc_lo=1;dc_hi=600;dc_pics=0;dc_census_seen=0;
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
        if(dc_arm_now&DL_CENSUS)dc_census_seen=1;
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
    /* the census's counters only when it ran: with them the bench's report (and nearly the fight's) reached the console
       loop's cap, and a report that does has no end line and its scene FAILS (disc d6's bench) */
    for(unsigned k=0;k<(dc_census_seen?(unsigned)DC_COUNT:(unsigned)DC_V_W_TRIS);k++)
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

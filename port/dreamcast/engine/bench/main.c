/* E0 bench: replays the recorded inputs of the village cross and the farm hay-fork view through the native
   renderer and measures every picture.

   Run-time schedule (eng-e0b). The program runs a list of 600-picture windows in one boot. Each window names a
   room and an arm, so survey arms are compared A/B/A in the same boot:
     c / f   room: village cross / farm hay-fork view
     0 a b   arm: 0 default, a world stage in operand-cache RAM, b three short loops over 32-vertex blocks
     n       no baked visibility (draw the full set)
     d       control: 5 ms busy-wait inside the timed drawing of every picture (must show in the draw rows)
     h       control: picture 300 is held for 40 ms after its scene is finished (must show in the presented rows)
     p       control: the engine's light pick made wrong on purpose (the light-pick test must report mismatches)
   eng-look: content steps follow the room and flags as ".<item><step>" groups (render/content.h): L character
   distance levels, W world distance cap and level shift, P far props as flat cards, E effect density cap, B baked
   static lighting (steps 0-3; 0 = today's full detail), G the frame-alpha glow (0 off, 1 on: the default). Example:
   "c0.L2 f0.W3.E1". An unknown token, flag, item or step refuses the whole schedule (stage 94, nothing runs).
   Default (the staged disc): c0 f0 ca c0 cb c0 fa f0 fb f0, then the content candidates' lightest steps against
   step 0 in the same boot (eng-look): c0.L3 c0 c0.W3 c0.P3 c0.E3 c0.B3 c0 f0.L3 f0.W3 f0.P3 f0.E3 f0.B3 f0, and
   the controls c0dh (24 windows, about 6 minutes). /cd/SCHEDULE.TXT overrides it (one line of
   tokens); /cd/FARM1 alone means "f0 c0" (test images). After the schedule the summary stays on screen.

   Raw rows, every picture of every window (m1_rows): drawing time (after PVR readiness to scene finish, us),
   PVR wait (us), presented-field interval (60 Hz fields between this picture's page flip and the previous one,
   counted by a vblank handler that watches the display address), and two counters over the drawing time:
   PRFC0 = pipeline freeze by operand-cache miss (cycles), PRFC1 = one of six events, rotated every 100 pictures
   (CPU-register freeze, on-chip I/O accesses, operand-cache fill cycles, instruction-cache freeze, FPU freeze,
   instructions issued). A boot calibration (m1_calib) runs an operand-cache-miss loop, a store-queue-to-TA loop
   and a plain loop under each event, so the console run shows which counter grows with store-queue waiting and
   which with cache misses.
   Per window (m1_windows, screen, serial): mean, p99, worst with picture and lap, count over 14 ms and over
   33.3 ms for the drawing rows; mean PVR wait; presented intervals over two fields and the worst. Every raw row
   is also printed to the serial log ("ROW ..."). */
#include "replay.h"
#ifndef M1_NATIVE
#error "the E0 bench builds the native image only"
#endif
#include "native_scene.h"
#include <dc/perfctr.h>
#include <dc/biosfont.h>
#include <dc/vblank.h>
#include <dc/cache.h>
#include <arch/cache.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "memmap.h"
#include "content.h"
KOS_INIT_FLAGS(INIT_DEFAULT);
int __real_cdrom_read_toc(cd_toc_t*,bool);
int __wrap_cdrom_read_toc(cd_toc_t *toc,bool hd){
    int rc=__real_cdrom_read_toc(toc,true);
    return rc && !hd ? __real_cdrom_read_toc(toc,false) : rc;
}

#define WINDOWS 24
volatile uint32_t m1_frame __attribute__((aligned(32)));
volatile uint32_t m1_state[8]; /* scene, picture, still request, ack, framebuffer, stage, completed windows, delay */
volatile uint32_t m1_timing[600][8];   /* this window's phase times (us): world, actors, PT, TR, FX, HUD, wait, draw */
typedef struct { uint32_t draw_us,wait_us,fields,ev0,ev1,ev1_id,vis,pad; } RawRow;
volatile RawRow m1_rows[WINDOWS][600];
/* per window: room, arm, flags, pictures, draw mean/p99/worst (us), worst picture, worst lap, over 14, over 33.3,
   wait mean, flips seen, intervals over 2 fields, worst interval, its picture, ev0 mean, pictures on a vis mask */
volatile uint32_t m1_windows[WINDOWS][20];
volatile uint32_t m1_schedule_n;
volatile uint32_t m1_calib[3][10];     /* loop (cache miss, store queue to TA, plain) x event */
volatile uint32_t m1_vis_state[300];   /* per picture: VIS_NONE, VIS_OUTSIDE, VIS_UNBAKED, VIS_HEIGHT or VIS_MASK */
static const uint8_t calib_events[10]={0x25,0x28,0x0d,0x22,0x24,0x29,0x13,0x0f,0x23,0x04};
static const uint8_t ev1_list[6]={0x28,0x0d,0x22,0x24,0x29,0x13};
static uint32_t sorted[600];
static const char *names[]={"CROSS","FARM"};
typedef struct { uint8_t scene,arm,novis,delay,hold,content[CS_COUNT]; uint16_t lab; } Window;
/* lane eng-draw1 (render/draw_cost.h): lab arms as "/X" tokens after a window's room and flags, each repeating one phase of
   the drawing (or changing its near plane) for every picture of the window: S stage the world twice, C copy (or clip) the
   world twice, Q select the world twice, H the HUD twice, N near plane not a number (as the E1 images before lane eng-e1l),
   B weight sets twice, L normals lit twice, E actor emission twice, D 2 ms busy wait in the world's opaque pass (the
   control: must read +2 ms), K positions skinned twice. The boot file DRAWLAB runs DRAWLAB_SCHEDULE below (in place of
   SCHEDULE.TXT and the default). */
#include "draw_cost.h"
static const char lab_letters[]="SCQHNBLEDK";
static const uint16_t lab_bits[]={DL_STAGE2,DL_COPY2,DL_SELECT2,DL_HUD2,DL_NAN,DL_WS2,DL_LIGHT2,DL_EMIT2,DL_DELAY,DL_SKIN2};
#define DRAWLAB_SCHEDULE "c0 c0/S c0/C c0/Q c0/K c0/B c0/L c0/E c0/H c0/D c0 c0/N f0 f0/S f0/C f0/Q f0/K f0/B f0/L f0/E f0/H f0/N f0"
static Window schedule[WINDOWS];
volatile uint32_t m1_content[CS_COUNT]=CONTENT_DEFAULT_INIT;
volatile uint32_t m1_content_counts[8];
volatile uint32_t m1_schedule_error;   /* 0, or the 1-based character offset of the refused token */
static const char content_items[]="LWPEBG";
void native_cards(NativeScene*);

static int exists(const char *p){FILE *f=fopen(p,"rb");if(!f)return 0;fclose(f);return 1;}
static int cmp(const void *a,const void *b){uint32_t x=*(const uint32_t*)a,y=*(const uint32_t*)b;return (x>y)-(x<y);}
/* Returns the window count, or 0 with m1_schedule_error set when any token is not understood (eng-look: an unknown
   arm, flag, content item or step is refused, never skipped). */
static unsigned parse_schedule(const char* text){
    unsigned n=0;const char* s=text;
    while(*s){
        while(*s==' '||*s=='\n'||*s=='\r'||*s=='\t')s++;
        if(!*s)break;
        const char* token=s;
        if((*s!='c'&&*s!='f')||n==WINDOWS){m1_schedule_error=token-text+1;return 0;}
        Window w={*s=='f',0,0,0,0,CONTENT_DEFAULT_INIT,0};s++;
        for(;*s && *s!=' ' && *s!='\n' && *s!='\r' && *s!='\t';s++){
            if(*s=='0')continue;
            if(*s=='/'){   /* lane eng-draw1: a lab arm; an unknown letter refuses the schedule */
                const char* at=s[1]?strchr(lab_letters,s[1]):NULL;
                if(!at){m1_schedule_error=token-text+1;return 0;}
                w.lab|=lab_bits[at-lab_letters];s++;continue;
            }
            else if(*s=='a')w.arm=1;else if(*s=='b')w.arm=2;else if(*s=='n')w.novis=1;else if(*s=='d')w.delay=1;else if(*s=='h')w.hold=1;
            else if(*s=='p')w.content[CS_PICK_CONTROL]=1;
            else if(*s=='.'){
                const char* item=s[1]?strchr(content_items,s[1]):NULL;unsigned step=(unsigned)(s[2]-'0');
                if(!item||step>(s[1]=='G'?1u:3u)){m1_schedule_error=token-text+1;return 0;}
                w.content[item-content_items]=step;s+=2;
            }else{m1_schedule_error=token-text+1;return 0;}
        }
        schedule[n++]=w;
    }
    return n;
}

/* ---- presented pictures: a vblank handler counts fields and records each change of the display address ---- */
static volatile uint32_t vbl_fields,flip_n,last_sof;
static volatile uint32_t flip_field[640];
static void on_vblank(uint32_t code,void* data){
    (void)code;(void)data;
    vbl_fields++;
    uint32_t sof=*(volatile uint32_t*)0xa05f8050;
    if(sof!=last_sof){last_sof=sof;if(flip_n<640)flip_field[flip_n]=vbl_fields;flip_n++;}
}

/* ---- boot calibration of the counter events ---- */
static uint8_t* calib_buffer;   /* 512 KB, allocated for the calibration only */
static void calib_loop(unsigned kind){
    if(kind==0){   /* operand-cache misses: one load per 32-byte line over 512 KB, twice */
        volatile uint32_t sum=0;
        for(unsigned r=0;r<2;r++)for(unsigned i=0;i<512*1024;i+=32)sum+=*(volatile uint32_t*)(calib_buffer+i);
    }else if(kind==1){   /* store queue to the TA: 6,000 small on-screen triangles in one opaque list */
        pvr_scene_begin();pvr_list_begin(PVR_LIST_OP_POLY);
        pvr_poly_cxt_t cxt;pvr_poly_hdr_t hdr __attribute__((aligned(32)));
        pvr_poly_cxt_col(&cxt,PVR_LIST_OP_POLY);pvr_poly_compile(&hdr,&cxt);
        pvr_vertex_t* sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
        memcpy(sq,&hdr,32);__asm__ __volatile__("pref @%0"::"r"(sq));sq=(pvr_vertex_t*)((uintptr_t)sq^32);
        for(unsigned t=0;t<6000;t++)for(unsigned k=0;k<3;k++){
            sq->flags=k==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;sq->x=(t%60)*10+(k&1)*4;sq->y=(t/60%45)*10+(k>>1)*4;sq->z=.001f;
            sq->u=sq->v=0;sq->argb=0xff000000;sq->oargb=0;
            __asm__ __volatile__("pref @%0"::"r"(sq));sq=(pvr_vertex_t*)((uintptr_t)sq^32);
        }
        sq_wait();sq_unlock();
        pvr_list_finish();pvr_scene_finish();
    }else{   /* plain loop */
        volatile uint32_t x=0;for(unsigned i=0;i<100000;i++)x+=i;
    }
}
static void calibrate(void){
    calib_buffer=memalign(32,512*1024);if(!calib_buffer)return;
    for(unsigned kind=0;kind<3;kind++)for(unsigned e=0;e<10;e++){
        if(kind==1){pvr_wait_ready();}
        perf_cntr_stop(PRFC1);perf_cntr_clear(PRFC1);perf_cntr_start(PRFC1,(perf_cntr_event_t)calib_events[e],PMCR_COUNT_CPU_CYCLES);
        calib_loop(kind);
        perf_cntr_stop(PRFC1);m1_calib[kind][e]=(uint32_t)perf_cntr_count(PRFC1);
    }
    pvr_wait_ready();free(calib_buffer);calib_buffer=NULL;
    printf("CALIB events");for(unsigned e=0;e<10;e++)printf(" %02x",calib_events[e]);printf("\n");
    static const char* kinds[]={"cache-miss","sq-to-TA","plain"};
    for(unsigned k=0;k<3;k++){printf("CALIB %s",kinds[k]);for(unsigned e=0;e<10;e++)printf(" %lu",(unsigned long)m1_calib[k][e]);printf("\n");}
}

/* ---- per-window report ---- */
/* 18 rows of 26 pixels from y = 8: the last ends at y = 474, inside the 480-line frame buffer (text drawn past
   its end lands in the texture memory that follows it). */
static void line(uint16_t* fb,unsigned row,const char* s){if(row<18)bfont_draw_str(fb+640*(8+26*row)+8,640,1,s);}
static void report(unsigned w,unsigned n_flips){
    volatile uint32_t* out=m1_windows[w];const Window* sw=schedule+w;
    uint64_t sum=0,wait=0,ev0=0;unsigned over14=0,over33=0,worst=0,wi=0,over2=0,wf=0,wfi=0,mask=0;
    for(unsigned i=0;i<600;i++){
        const volatile RawRow* r=&m1_rows[w][i];unsigned v=r->draw_us;
        sorted[i]=v;sum+=v;wait+=r->wait_us;ev0+=r->ev0;over14+=v>14000;over33+=v>33333;
        if(v>worst){worst=v;wi=i;}
        if(i && r->fields>2)over2++;
        if(i && r->fields>wf){wf=r->fields;wfi=i;}
        mask+=r->vis==VIS_MASK;
    }
    qsort(sorted,600,4,cmp);
    unsigned steps=0;char cs[24];unsigned cn=0;cs[0]=0;
    for(unsigned k=0;k<CS_COUNT;k++){steps|=sw->content[k]<<(4*k);
        if(k<CS_GLOW?sw->content[k]!=0:k==CS_GLOW?sw->content[k]==0:sw->content[k]!=0){
            if(cn+3<sizeof(cs)){cs[cn++]=k==CS_PICK_CONTROL?'p':content_items[k];cs[cn++]=k==CS_PICK_CONTROL?' ':'0'+sw->content[k];cs[cn]=0;}}}
    unsigned vals[20]={sw->scene,sw->arm,sw->novis|sw->delay<<1|sw->hold<<2,600,(unsigned)(sum/600),sorted[593],worst,wi%300+1,wi/300+1,
                       over14,over33,(unsigned)(wait/600),n_flips,over2,wf,wfi%300+1,(unsigned)(ev0/600),mask,wfi/300+1,steps};
    for(unsigned k=0;k<20;k++)out[k]=vals[k];
    static const char arms[]="0ab";
    printf("WINDOW %u %s arm %c%s%s%s draw mean %.3f p99 %.3f worst %.3f (picture %u lap %u) over14 %u over33.3 %u wait %.3f flips %u "
           "intervals>2 %u worst %u fields (picture %u lap %u) ev25 %lu vis-mask %u content [%s] counts %lu %lu %lu %lu %lu %lu %lu %lu\n",
           w,names[sw->scene],arms[sw->arm],sw->novis?" novis":"",sw->delay?" delay5":"",sw->hold?" hold300":"",
           sum/600/1000.,sorted[593]/1000.,worst/1000.,wi%300+1,wi/300+1,over14,over33,wait/600/1000.,n_flips,over2,wf,wfi%300+1,wfi/300+1,
           (unsigned long)(ev0/600),mask,cs,(unsigned long)m1_content_counts[0],(unsigned long)m1_content_counts[1],(unsigned long)m1_content_counts[2],
           (unsigned long)m1_content_counts[3],(unsigned long)m1_content_counts[4],(unsigned long)m1_content_counts[5],(unsigned long)m1_content_counts[6],
           (unsigned long)m1_content_counts[7]);
    for(unsigned i=0;i<600;i++){const volatile RawRow* r=&m1_rows[w][i];
        printf("ROW %u %u %lu %lu %lu %lu %lu %02lx %lu\n",w,i+1,(unsigned long)r->draw_us,(unsigned long)r->wait_us,(unsigned long)r->fields,
               (unsigned long)r->ev0,(unsigned long)r->ev1,(unsigned long)r->ev1_id,(unsigned long)r->vis);}
    /* screen: this window, then every finished window so far */
    vid_waitvbl();
    uint16_t* fb=(uint16_t*)(0xa5000000u+((*(volatile uint32_t*)0xa05f8050)&0x7ffffc));
    char s[64];
    snprintf(s,sizeof(s),"E0 bench  window %u/%lu  ms, 600 pictures",w+1,(unsigned long)m1_schedule_n);line(fb,0,s);
    for(unsigned k=(w>15?w-15:0);k<=w;k++){
        const volatile uint32_t* v=m1_windows[k];
        char st[16];unsigned sn=0;st[0]=0;
        for(unsigned c=0;c<CS_GLOW && sn+2<sizeof(st);c++){unsigned x=v[19]>>(4*c)&15;if(x){st[sn++]=content_items[c];st[sn++]='0'+x;st[sn]=0;}}
        if(!(v[19]>>(4*CS_GLOW)&15) && sn+2<sizeof(st)){st[sn++]='G';st[sn++]='0';st[sn]=0;}
        snprintf(s,sizeof(s),"%c%c%s m%.2f p%.2f w%.2f@%lu/%lu %lu|%lu f%lu %s",names[v[0]][0],arms[v[1]],v[2]&1?"n":v[2]&2?"d":v[2]&4?"h":" ",
                 v[4]/1000.,v[5]/1000.,v[6]/1000.,(unsigned long)v[7],(unsigned long)v[8],(unsigned long)v[9],(unsigned long)v[10],(unsigned long)v[13],st);
        line(fb,1+k-(w>15?w-15:0),s);
    }
    line(fb,17,"m mean p p99 w worst@pic/lap >14|>33.3 f >2 fields");
    thd_sleep(1500);
}

int main(void){
    pvr_init_params_t params={.opb_sizes={PVR_BINSIZE_16,PVR_BINSIZE_8,PVR_BINSIZE_16,0,PVR_BINSIZE_16},.vertex_buf_size=1024*1024,.vbuf_doublebuf_disabled=0};
    memmap_boot();
    m1_state[5]=1;if(pvr_init(&params)<0||pvr_set_vbuf_doublebuf(true)<0){m1_state[5]=90;return 1;}
    PVR_SET(PVR_PT_ALPHA_REF,128);pvr_set_zclip(0.0f);pvr_set_shadow_scale(true,0.5f);
    perf_cntr_timer_disable();   /* PRFC0 is ours; the bench's clock is the TMU (timer_us_gettime64) */
    vblank_handler_add(on_vblank,NULL);
    int stills=exists("/cd/STILLS");
    {   /* schedule */
        static char text[256];FILE* f=fopen("/cd/SCHEDULE.TXT","rb");unsigned n=0;
        if(f){n=fread(text,1,sizeof(text)-1,f);fclose(f);text[n]=0;}
        const char* def=exists("/cd/FARM1")?"f0 c0":"c0 f0 ca c0 cb c0 fa f0 fb f0 c0.L3 c0 c0.W3 c0.P3 c0.E3 c0.B3 c0 f0.L3 f0.W3 f0.P3 f0.E3 f0.B3 f0 c0dh";
        if(exists("/cd/DELAY5"))def=exists("/cd/FARM1")?"f0d c0d":"c0d f0d";
        if(exists("/cd/DRAWLAB")){def=DRAWLAB_SCHEDULE;n=0;printf("DRAWLAB: lane eng-draw1 lab schedule %s\n",def);}
        m1_schedule_n=parse_schedule(n?text:def);
        if(!m1_schedule_n){   /* eng-look: refused, never replaced by the default */
            printf("SCHEDULE REFUSED at character %lu: %s\n",(unsigned long)m1_schedule_error,n?text:def);
            m1_state[5]=94;for(;;)thd_sleep(100);
        }
    }
    calibrate();
    NativeScene native={0};int open=-1;
    for(unsigned w=0;w<m1_schedule_n;w++){
        const Window* sw=schedule+w;unsigned scene=sw->scene;
        m1_state[0]=scene;m1_state[5]=2;m1_state[7]=sw->delay;
        if(open!=(int)scene){
            if(open>=0)native_close(&native);
            if(!native_open(&native,scene?"/cd/FARM.PAK":"/cd/CROSS.PAK")){printf("M1 native pack REFUSED\n");m1_state[5]=91;for(;;)thd_sleep(100);}
            open=scene;
        }else native_reset(&native);     /* same room: new window starts with every change flag cleared */
        native_select_arm(sw->arm);
        for(unsigned k=0;k<CS_COUNT;k++)m1_content[k]=sw->content[k];
        for(unsigned k=0;k<8;k++)m1_content_counts[k]=0;
        NativeVis* vis=native.world.vis;if(sw->novis)native.world.vis=NULL;
        memmap_sample(scene);
        m1_state[5]=3;
        pvr_wait_ready();pvr_wait_render_done();vid_waitvbl();vid_waitvbl();
        flip_n=0;
        dc_frame_base=m1_frame;dc_lab_bench=sw->lab;dc_window_begin();   /* lane eng-draw1 */
        for(unsigned i=0;i<600;i++){
            m1_frame++;m1_state[1]=i+1;uint64_t begin=timer_us_gettime64();
            pvr_wait_ready();uint64_t now=timer_us_gettime64();m1_timing[i][6]=now-begin;
            unsigned ev1=ev1_list[(i/100)%6];
            perf_cntr_stop(PRFC0);perf_cntr_clear(PRFC0);perf_cntr_start(PRFC0,PMCR_PIPELINE_FREEZE_BY_DCACHE_MISS_MODE,PMCR_COUNT_CPU_CYCLES);
            perf_cntr_stop(PRFC1);perf_cntr_clear(PRFC1);perf_cntr_start(PRFC1,(perf_cntr_event_t)ev1,PMCR_COUNT_CPU_CYCLES);
            native_update(&native,i%300);
            const float* camera=(const float*)native.state[0];
            unsigned vs=native_vis_select(&native.world,camera);m1_vis_state[i%300]=vs;
            if(!native_prepare_world(&native.world,camera,native.assets.header.n)){m1_state[5]=92;return 1;}
            pvr_scene_begin();
            for(unsigned k=0;k<6;k++){
                uint64_t t=timer_us_gettime64();
                if(k==0||k==2||k==3)pvr_list_begin(k==0?PVR_LIST_OP_POLY:k==2?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY);
                if(k==0)native_sky(&native);
                if(k==0||k==2||k==3)native_world_pass(&native.assets,&native.world,camera,k==0?0:k-1);
                if(k==1)native_actor_pass(&native,0);
                if(k==2)native_cards(&native);          /* eng-look: far props as flat cards (step P) */
                if(k==3)native_actor_pass(&native,1);   /* eng-look: Leon's hair layer, blended in the translucent list */
                if(k==4)native_effects(&native);
                if(k==5)native_hud(&native);
                if(k==1||k==2||k==5)pvr_list_finish();
                if(k==1)native_shadows(&native);
                m1_timing[i][k]=timer_us_gettime64()-t;
            }
            if(sw->delay){uint64_t t=timer_us_gettime64();while(timer_us_gettime64()-t<5000){}}
            pvr_scene_finish();uint64_t end=timer_us_gettime64();m1_timing[i][7]=end-now;
            perf_cntr_stop(PRFC0);perf_cntr_stop(PRFC1);
            volatile RawRow* r=&m1_rows[w][i];
            r->draw_us=end-now;r->wait_us=now-begin;r->ev0=(uint32_t)perf_cntr_count(PRFC0);r->ev1=(uint32_t)perf_cntr_count(PRFC1);
            r->ev1_id=ev1;r->vis=vs;r->fields=0;
            if(sw->hold && i==299){uint64_t t=timer_us_gettime64();while(timer_us_gettime64()-t<40000){}}
            if(stills && i<300){
                pvr_wait_render_done();vid_waitvbl();vid_waitvbl();
                m1_state[4]=0xa5000000+2*(*(volatile uint32_t*)0xa05f8050&0x7ffffc);
                m1_state[2]=scene*600+i+1;while(m1_state[3]!=m1_state[2])thd_pass();
            }
        }
        pvr_wait_ready();pvr_wait_render_done();vid_waitvbl();vid_waitvbl();vid_waitvbl();
        unsigned flips=flip_n;
        for(unsigned i=1;i<600 && i<flips;i++)m1_rows[w][i].fields=flip_field[i]-flip_field[i-1];
        native.world.vis=vis;
        memmap_check();
        {   /* lane eng-draw1: the bench's own phase clock (m1_timing: world OP, actors, PT, TR, effects, HUD, wait, draw) and
               the renderer's stamps and counters, this window */
            static const char* const kn[8]={"world+sky","actors+shadows","PT","TR+hair","effects","hud","wait","draw"};
            for(unsigned k=0;k<8;k++){uint64_t sum=0;unsigned worst=0;
                for(unsigned i=0;i<600;i++){unsigned v=m1_timing[i][k];sum+=v;if(v>worst)worst=v;}
                printf("DCB %u TIMING %s m%lu w%u (us)\n",w,kn[k],(unsigned long)(sum/600),worst);}
            native_draw_report_window(w);
        }
        m1_state[6]++;report(w,flips);
    }
    printf("SCHEDULE DONE %lu windows\n",(unsigned long)m1_schedule_n);
    for(;;)thd_sleep(1000);
}

/* E0 bench: replays the recorded inputs of the village cross and the farm hay-fork view through the native
   renderer and measures every picture.

   Run-time schedule (eng-e0b). The program runs a list of 600-picture windows in one boot. Each window names a
   room and an arm, so survey arms are compared A/B/A in the same boot:
     c / f   room: village cross / farm hay-fork view
     0 a b   arm: 0 default, a world stage in operand-cache RAM, b three short loops over 32-vertex blocks
     n       no baked visibility (draw the full set)
     d       control: 5 ms busy-wait inside the timed drawing of every picture (must show in the draw rows)
     h       control: picture 300 is held for 40 ms after its scene is finished (must show in the presented rows)
   Default (the staged disc): c0 f0 ca c0 cb c0 fa f0 fb f0 c0dh. /cd/SCHEDULE.TXT overrides it (one line of
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
KOS_INIT_FLAGS(INIT_DEFAULT);
int __real_cdrom_read_toc(cd_toc_t*,bool);
int __wrap_cdrom_read_toc(cd_toc_t *toc,bool hd){
    int rc=__real_cdrom_read_toc(toc,true);
    return rc && !hd ? __real_cdrom_read_toc(toc,false) : rc;
}

#define WINDOWS 16
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
typedef struct { uint8_t scene,arm,novis,delay,hold; } Window;
static Window schedule[WINDOWS];

static int exists(const char *p){FILE *f=fopen(p,"rb");if(!f)return 0;fclose(f);return 1;}
static int cmp(const void *a,const void *b){uint32_t x=*(const uint32_t*)a,y=*(const uint32_t*)b;return (x>y)-(x<y);}
static unsigned parse_schedule(const char* s){
    unsigned n=0;
    while(*s && n<WINDOWS){
        while(*s==' '||*s=='\n'||*s=='\r'||*s=='\t')s++;
        if(*s!='c'&&*s!='f'){if(*s)s++;continue;}
        Window w={*s=='f',0,0,0,0};s++;
        for(;*s && *s!=' ' && *s!='\n' && *s!='\r';s++){
            if(*s=='a')w.arm=1;else if(*s=='b')w.arm=2;else if(*s=='n')w.novis=1;else if(*s=='d')w.delay=1;else if(*s=='h')w.hold=1;
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
static void line(uint16_t* fb,unsigned row,const char* s){bfont_draw_str(fb+640*(8+26*row)+8,640,1,s);}
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
    unsigned vals[20]={sw->scene,sw->arm,sw->novis|sw->delay<<1|sw->hold<<2,600,(unsigned)(sum/600),sorted[593],worst,wi%300+1,wi/300+1,
                       over14,over33,(unsigned)(wait/600),n_flips,over2,wf,wfi%300+1,(unsigned)(ev0/600),mask,wfi/300+1,0};
    for(unsigned k=0;k<20;k++)out[k]=vals[k];
    static const char arms[]="0ab";
    printf("WINDOW %u %s arm %c%s%s%s draw mean %.3f p99 %.3f worst %.3f (picture %u lap %u) over14 %u over33.3 %u wait %.3f flips %u "
           "intervals>2 %u worst %u fields (picture %u lap %u) ev25 %lu vis-mask %u\n",
           w,names[sw->scene],arms[sw->arm],sw->novis?" novis":"",sw->delay?" delay5":"",sw->hold?" hold300":"",
           sum/600/1000.,sorted[593]/1000.,worst/1000.,wi%300+1,wi/300+1,over14,over33,wait/600/1000.,n_flips,over2,wf,wfi%300+1,wfi/300+1,
           (unsigned long)(ev0/600),mask);
    for(unsigned i=0;i<600;i++){const volatile RawRow* r=&m1_rows[w][i];
        printf("ROW %u %u %lu %lu %lu %lu %lu %02lx %lu\n",w,i+1,(unsigned long)r->draw_us,(unsigned long)r->wait_us,(unsigned long)r->fields,
               (unsigned long)r->ev0,(unsigned long)r->ev1,(unsigned long)r->ev1_id,(unsigned long)r->vis);}
    /* screen: this window, then every finished window so far */
    vid_waitvbl();
    uint16_t* fb=(uint16_t*)(0xa5000000u+((*(volatile uint32_t*)0xa05f8050)&0x7ffffc));
    char s[64];
    snprintf(s,sizeof(s),"E0 bench  window %u/%lu  ms, 600 pictures",w+1,(unsigned long)m1_schedule_n);line(fb,0,s);
    for(unsigned k=0;k<=w && k<16;k++){
        const volatile uint32_t* v=m1_windows[k];
        snprintf(s,sizeof(s),"%c%c%s m%.2f p%.2f w%.2f@%lu/%lu %lu|%lu f%lu",names[v[0]][0],arms[v[1]],v[2]&1?"n":v[2]&2?"d":v[2]&4?"h":" ",
                 v[4]/1000.,v[5]/1000.,v[6]/1000.,(unsigned long)v[7],(unsigned long)v[8],(unsigned long)v[9],(unsigned long)v[10],(unsigned long)v[13]);
        line(fb,1+k,s);
    }
    line(fb,18,"m mean p p99 w worst@pic/lap >14|>33.3 f >2 fields");
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
        const char* def=exists("/cd/FARM1")?"f0 c0":"c0 f0 ca c0 cb c0 fa f0 fb f0 c0dh";
        if(exists("/cd/DELAY5"))def=exists("/cd/FARM1")?"f0d c0d":"c0d f0d";
        m1_schedule_n=parse_schedule(n?text:def);
        if(!m1_schedule_n)m1_schedule_n=parse_schedule(def);
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
        NativeVis* vis=native.world.vis;if(sw->novis)native.world.vis=NULL;
        memmap_sample(scene);
        m1_state[5]=3;
        pvr_wait_ready();pvr_wait_render_done();vid_waitvbl();vid_waitvbl();
        flip_n=0;
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
                if(k==1||k==2)native_actor_pass(&native,k==2);   /* hair: punch-through list */
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
        m1_state[6]++;report(w,flips);
    }
    printf("SCHEDULE DONE %lu windows\n",(unsigned long)m1_schedule_n);
    for(;;)thd_sleep(1000);
}

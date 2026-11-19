#include "replay.h"
#ifdef M1_NATIVE
#include "native_scene.h"
#endif
#include <dc/perfctr.h>
#include <dc/biosfont.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
KOS_INIT_FLAGS(INIT_DEFAULT);
int __real_cdrom_read_toc(cd_toc_t*,bool);
int __wrap_cdrom_read_toc(cd_toc_t *toc,bool hd){
    int rc=__real_cdrom_read_toc(toc,true);
    return rc && !hd ? __real_cdrom_read_toc(toc,false) : rc;
}

volatile uint32_t m1_frame __attribute__((aligned(32)));
volatile uint32_t m1_state[8]; /* scene, picture, still request, ack, framebuffer, stage, completed windows, delay */
volatile uint32_t m1_timing[600][8];
static uint32_t sorted[600];
volatile uint32_t m1_results[2][14];
volatile uint32_t m1_pmc[2][5];
char m1_log[2][512];

static const char *names[]={"CROSS","FARM"};
static const unsigned events[]={0x25,0x24,0x04,0x05,0x08};
static int exists(const char *p){FILE *f=fopen(p,"rb");if(!f)return 0;fclose(f);return 1;}
static int cmp(const void *a,const void *b){uint32_t x=*(const uint32_t*)a,y=*(const uint32_t*)b;return (x>y)-(x<y);}
static void summary(unsigned scene){
    volatile uint32_t *out=m1_results[scene];
    for(unsigned k=0;k<8;k++){uint64_t sum=0;for(unsigned i=0;i<600;i++)sum+=m1_timing[i][k];out[k]=sum/600;}
    unsigned over20=0,over26=0,over33=0;
    for(unsigned i=0;i<600;i++){unsigned v=m1_timing[i][7];sorted[i]=v;over20+=v>20000;over26+=v>26000;over33+=v>33333;}
    qsort(sorted,600,4,cmp);out[8]=sorted[593];out[9]=sorted[599];out[10]=over20;out[11]=over26;out[12]=over33;out[13]=600;
    snprintf(m1_log[scene],512,
             "M1 %s n=600 ms world %.3f actor %.3f PT %.3f TR %.3f FX %.3f HUD %.3f wait %.3f mean %.3f p99 %.3f worst %.3f over20/26/33 %lu/%lu/%lu\n"
             "PMC_ROW per picture ev25 %lu ev24 %lu ev04 %lu ev05 %lu ev08 %lu\n",
             names[scene],out[0]/1000.,out[1]/1000.,out[2]/1000.,out[3]/1000.,out[4]/1000.,out[5]/1000.,
             out[6]/1000.,out[7]/1000.,out[8]/1000.,out[9]/1000.,out[10],out[11],out[12],
             m1_pmc[scene][0],m1_pmc[scene][1],m1_pmc[scene][2],m1_pmc[scene][3],m1_pmc[scene][4]);
    puts(m1_log[scene]);
}
static void display(unsigned scene){
    volatile uint32_t *v=m1_results[scene];char line[75];vid_waitvbl();
    unsigned offset=(*(volatile uint32_t*)0xa05f8050)&0x7ffffc;
    uint16_t *fb=(uint16_t*)(0xa5000000u+offset);
    snprintf(line,sizeof(line),"%s / 600 pictures  ms",names[scene]);bfont_draw_str(fb+640*16+16,640,1,line);
    for(unsigned i=0;i<4;i++){
        static const char *const labels[]={"world/actor","PT/TR","FX/HUD","wait/mean"};
        snprintf(line,sizeof(line),"%s %.3f / %.3f",labels[i],v[2*i]/1000.,v[2*i+1]/1000.);bfont_draw_str(fb+640*(44+28*i)+16,640,1,line);
    }
    snprintf(line,sizeof(line),"p99/worst %.2f / %.2f   over 20ms %lu",v[8]/1000.,v[9]/1000.,v[10]);bfont_draw_str(fb+640*160+16,640,1,line);
    thd_sleep(1000);
}
int main(void){
    pvr_init_params_t params={.opb_sizes={PVR_BINSIZE_16,PVR_BINSIZE_8,PVR_BINSIZE_16,0,PVR_BINSIZE_16},.vertex_buf_size=1024*1024,.vbuf_doublebuf_disabled=0};
    m1_state[5]=1;if(pvr_init(&params)<0||pvr_set_vbuf_doublebuf(true)<0){m1_state[5]=90;return 1;}
    PVR_SET(PVR_PT_ALPHA_REF,128);pvr_set_zclip(0.0f);pvr_set_shadow_scale(true,0.5f);
    int stills=exists("/cd/STILLS"),delay=exists("/cd/DELAY5");m1_state[7]=delay;
    unsigned farm_first=exists("/cd/FARM1");
    for(unsigned pass=0;;pass++){
        unsigned scene=(pass+farm_first)%2;
#ifdef M1_NATIVE
        NativeScene native={0};
#else
        Scene s={0};
#endif
        m1_state[0]=scene;m1_state[5]=2;
        #ifdef M1_NATIVE
        if(!native_open(&native,scene?"/cd/FARM.PAK":"/cd/CROSS.PAK")){printf("M1 native pack REFUSED\n");m1_state[5]=91;for(;;)thd_sleep(100);}
#else
        if(!open_scene(&s,scene?"/cd/FARM.PAK":"/cd/CROSS.PAK")){m1_state[5]=91;for(;;)thd_sleep(100);}
#endif
        m1_state[5]=3;
        for(unsigned i=0;i<600;i++){
            if(i%120==0){perf_cntr_stop(PRFC1);perf_cntr_clear(PRFC1);perf_cntr_start(PRFC1,(perf_cntr_event_t)events[i/120],PMCR_COUNT_CPU_CYCLES);}
            m1_frame++;m1_state[1]=i+1;uint64_t begin=timer_us_gettime64();
            pvr_wait_ready();uint64_t now=timer_us_gettime64();m1_timing[i][6]=now-begin;
#ifdef M1_NATIVE
            native_update(&native,i%300);
            const float* camera=(const float*)native.state[0];
            if(!native_prepare_world(&native.world,camera,native.assets.header.n)){m1_state[5]=92;return 1;}
#else
            Picture pic;open_picture(&s,i%300,&pic);
#endif
            pvr_scene_begin();
            for(unsigned k=0;k<6;k++){
                uint64_t t=timer_us_gettime64();
                if(k==0||k==2||k==3)pvr_list_begin(k==0?PVR_LIST_OP_POLY:k==2?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY);
#ifdef M1_NATIVE
                if(k==0)native_sky(&native);
                if(k==0||k==2||k==3)native_world_pass(&native.assets,&native.world,camera,k==0?0:k-1);
                if(k==1||k==3)native_actor_pass(&native,k==3);
                if(k==4)native_effects(&native);
                if(k==5)native_hud(&native);
#else
                render_phase(&s,&pic,k);
#endif
                if(k==1||k==2||k==5)pvr_list_finish();
#ifndef M1_NATIVE
                if(k==1)draw_shadows(&pic);
#else
                if(k==1)native_shadows(&native);
#endif
                m1_timing[i][k]=timer_us_gettime64()-t;
            }
            if(delay){uint64_t t=timer_us_gettime64();while(timer_us_gettime64()-t<5000){}}
            pvr_scene_finish();m1_timing[i][7]=timer_us_gettime64()-now;
            if(i%120==119)m1_pmc[scene][i/120]=perf_cntr_count(PRFC1)/120;
            if(i%120==119)printf("PMC: ev=%02x per_drawn=%llu drawn=120\n",events[i/120],(unsigned long long)perf_cntr_count(PRFC1)/120);
            if(stills && (
#ifdef M1_NATIVE
                i<300
#else
                i==0||i==149||i==299
#endif
            )){
                pvr_wait_render_done();vid_waitvbl();vid_waitvbl();
                m1_state[4]=0xa5000000+2*(*(volatile uint32_t*)0xa05f8050&0x7ffffc);
                m1_state[2]=scene*600+i+1;while(m1_state[3]!=m1_state[2])thd_pass();
            }
        }
        pvr_wait_ready();pvr_wait_render_done();summary(scene);m1_state[6]++;display(scene);
#ifdef M1_NATIVE
        native_close(&native);
#else
        close_scene(&s);
#endif
    }
}





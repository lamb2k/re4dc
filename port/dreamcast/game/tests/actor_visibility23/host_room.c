/* Synthetic certificate plumbing; production room_occl.c is compiled unchanged. */
#include <stdint.h>
#include <string.h>
#include "room_file.h"
#include "room_vis.h"
static unsigned char section[160];static unsigned len,frame,good=1,placed=1;
static re4dc_room_header header={1,1,40000,-20000,-20000};
void re4dc_log(const char* fmt,...){(void)fmt;}
unsigned re4dc_ui_frame(void){return frame;}
int re4dc_ps2_world_intact(unsigned room,uint32_t crc){(void)room;(void)crc;return good;}
int re4dc_ps2_placements_intact(unsigned room,const unsigned char* f,unsigned n){(void)room;(void)f;(void)n;return placed;}
const void* re4dc_room_section(const char tag[4],unsigned* bytes,unsigned* version,unsigned* flags,const re4dc_room_header** h){
 (void)tag;*bytes=len;*version=2;*flags=0;*h=&header;return section;
}
static void u16(unsigned char* p,unsigned x){p[0]=x;p[1]=x>>8;}
void host_panel(unsigned mode){
 ++frame;good=mode!=3;placed=mode!=4;unsigned n=mode==1?2:1;len=32+56*n+4+4+4;memset(section,0,sizeof(section));
 u16(section,1);u16(section+2,1);u16(section+4,1);u16(section+6,n);u16(section+8,n);u16(section+10,2500);u16(section+22,1);
 for(unsigned i=0;i<n;i++){
  float l=-5000,r=5000,z=mode==2?-13000:-6000,half=10;
  if(mode==1){if(!i)r=-200;else l=200;}
  float q[12]={l,-5000,z,r,-5000,z,r,5000,z,l,5000,z};unsigned char* p=section+32+56*i;
  memcpy(p,q,48);memcpy(p+48,&half,4);p[52]=1;p[53]=1;
 }
 unsigned char* cells=section+32+56*n;cells[2]=n;for(unsigned i=0;i<n;i++)u16(cells+4+i*2,i);
 re4dc_room_vis_enter(0x119);
}

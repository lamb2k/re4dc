/* Real candidate OCCL plumbing; production room_occl.c stays unchanged. */
#include <stdint.h>
#include <string.h>
#include "room_file.h"
#include "room_vis.h"
static unsigned char section[4096];static unsigned len,frame,good=1;
static re4dc_room_header header={136,33,1000,-2000,-10000};
void re4dc_log(const char* fmt,...){(void)fmt;}
unsigned re4dc_ui_frame(void){return frame;}
int re4dc_ps2_world_intact(unsigned room,uint32_t crc){return good&&room==0x119&&crc==0xfb5072f8;}
const void* re4dc_room_section(const char tag[4],unsigned* bytes,unsigned* version,unsigned* flags,const re4dc_room_header** h){
 (void)tag;*bytes=len;*version=2;*flags=0;*h=&header;return section;
}
int host_real_load(const void* source,unsigned bytes){if(bytes>sizeof(section))return 0;memcpy(section,source,bytes);len=bytes;++frame;re4dc_room_vis_enter(0x119);return re4dc_room_vis_active();}
void host_real_identity(unsigned ok){good=ok;++frame;}

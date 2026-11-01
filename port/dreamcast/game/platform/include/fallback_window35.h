#ifndef RE4DC_FALLBACK_WINDOW35_H
#define RE4DC_FALLBACK_WINDOW35_H

#include <stdint.h>
namespace re4dc { namespace fw35 {
void begin_tick(uint32_t tick,uint32_t room);
void end_tick(bool draw,const uint32_t* dfa,uint32_t dfa_overflow,
              const uint32_t* fa,uint32_t fa_overflow,uint32_t outside_room);
void pause();
void resume();
void reset();
bool available();
uint64_t fa_sum(unsigned reason);
unsigned dfa_line_count();
int dfa_format_line(unsigned row,char* out,unsigned capacity);
int fa_header(char* out,unsigned capacity);
} }
#endif

// PRELOAD_SKIP_GCIDLE=1 only: force-included into native_ui.o by game30.mk (no line of native_ui.cpp moves, so a knob-off
// build is byte-identical; the call site is the RE4DC_GCIDLE_SKIP macro on the room-pass drop line of preload_select).
#pragma once
// PRELOAD_SKIP_GCIDLE=1 (render only, lane purge-cast24): GameCube pictures of the player/enemy archives (pl00, pl08,
// em26) that TEX_USE_CENSUS=2 saw loaded at entry and never drawn are left out of every entry preload pass. The list
// is generated with each key's source archive and its 0-draw evidence rooms; a listed key that is ever drawn still
// loads on first sight (DISC_READ_METER gate).
static const unsigned preload_gcidle_keys[][2]={
#include "preload_skip_gcidle.inc"
};
static bool preload_gcidle(unsigned crc,unsigned fnv){
    for(const auto& k:preload_gcidle_keys)if(k[0]==crc && k[1]==fnv)return true;
    return false;
}

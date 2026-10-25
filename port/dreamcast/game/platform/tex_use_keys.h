// TEX_USE_CENSUS=2 (lane purge-cast24, test only): force-included into native_ui.o by game30.mk, so no line of
// native_ui.cpp moves (knob-off builds byte-identical). RE4DC_TEX_USE_KEYS() runs at the top of re4dc_ui_present: from
// frame 600, every resident key and the frames since a draw or a preload touched it, 4 keys a frame so the log ring
// keeps every line.
#pragma once
#define RE4DC_TEX_USE_KEYS() \
    { static unsigned use_key_from=0,use_key_next=0; \
      if(frame>=600 && !use_key_from)use_key_from=frame; \
      if(use_key_from && frame>use_key_from && use_key_from!=0xffffffffu){ \
        unsigned i=0,printed=0; \
        for(const auto& e:entries){ \
            if(!e.valid)continue; \
            if(i++<use_key_next)continue; \
            re4dc_log("tex use key: frame=%u key=%08x-%08x idle=%u\n",use_key_from,e.key.crc,e.key.fnv, \
                      (e.frame>=use_key_from?0U:use_key_from-e.frame)); \
            ++use_key_next;if(++printed==4)break; \
        } \
        if(!printed)use_key_from=0xffffffffu; } }

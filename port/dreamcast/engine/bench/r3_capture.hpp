#pragma once
#include <stdint.h>

// Private one-tick input stream. One writer, one acknowledged picture.
// Asset descriptions belong in the static room/model pack, outside this stream.
namespace m1r3 {
enum Kind : unsigned { Camera=1, Actor, SourceLight, Effect, Caster, Hud, Glyph, Environment };
struct Control {
    volatile unsigned mode; // 0: unarmed, 1: capture inputs and hold each displayed picture
    volatile unsigned sequence,ack;
    unsigned picture,tick,room,bytes,overflow,framebuffer,capacity;
    unsigned char *data;
};
extern "C" Control m1r3_control;
extern bool recording;
void append(Kind,const void*,unsigned);
void begin(unsigned room,unsigned tick);
void finish();
void present();
}

#pragma once
#include <stdint.h>

// Private one-tick input stream. One writer, one acknowledged picture.
// Asset descriptions belong in the static room/model pack, outside this stream.
namespace m1r3 {
enum Kind : unsigned { Camera=1, Actor, SourceLight, Effect, Caster, Hud, Glyph, Environment, ModelLight };
struct Control {
    volatile unsigned mode; // 0: unarmed, 1: capture inputs and hold each displayed picture
    volatile unsigned sequence,ack;
    unsigned picture,tick,room,bytes,overflow,framebuffer,capacity;
    unsigned char *data;
    volatile unsigned start; // eng-boss: 0, or the first game tick (Frame_cnt) to record (host-written, offset 44)
};
extern "C" Control m1r3_control;
extern bool recording;
void texture_image_key(const void*,const void*,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned (&)[2]);
template<class Descriptor> void texture_key(const Descriptor* d,unsigned (&key)[2]){
    key[0]=key[1]=0;
    if(!d || !d->textureHeader)return;
    auto* t=d->textureHeader;
    auto* c=(t->format>=8 && t->format<=10)?d->CLUTHeader:nullptr;
    texture_image_key(t->data,c?c->data:nullptr,t->width,t->height,t->format,
                      c?c->format:0xffffffffU,c?c->numEntries*2:0,key);
}
void append(Kind,const void*,unsigned);
void begin(unsigned room,unsigned tick);
void finish();
void present();
}

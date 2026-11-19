#pragma once
#include <kos.h>
typedef struct {
    uint32_t n;
    const unsigned* offset;
    uint8_t* base;
} Table;
typedef struct { Table texture, header, geometry, pose, light, draw, frame; void* storage; } Scene;
static inline void* row(const Table *t, unsigned i) { return t->base+t->offset[i]; }
static inline unsigned bytes(const Table *t,unsigned i) { return t->offset[i+1]-t->offset[i]; }
typedef struct { float x,y,z,u,v; uint32_t color; uint16_t bone; int16_t normal[3]; } Vertex;
typedef struct { uint16_t n,bone; float low[3],high[3]; } Strip;
typedef struct { const unsigned *ids[6]; unsigned count[6]; const float *camera; } Picture;
int open_scene(Scene*,const char*);
void close_scene(Scene*);
void open_picture(const Scene*,unsigned,Picture*);
void render_phase(const Scene*,const Picture*,unsigned);
extern pvr_ptr_t m1_textures[256];



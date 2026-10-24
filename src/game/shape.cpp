#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "gc_asset_motion_source.h"
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
#include "gc_asset_members.h"
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "native_motion.h"
#endif
// game/shape: vertex-morph ("shape") animation of a model part — the face morphs of the player /
// partner and the mouth / eye shapes of the enemies. A ShapeData holds per-channel Hermite key
// tables of blend weights; up to 5 shapes play at once on a cModelInfo (info->shape[]). ShapeSet
// starts one, ShapeMove (per frame from the model trans) advances the frames, CalculateShape_new
// adds the weighted vertex deltas of the model's shape table onto the vertex buffer `dst`.
#include "types.h"
#include "vec.h"
#include "db_log.h"
#include "main_mem.h"
#include "model.h"

// game/motion.cpp
struct HermiteParam {
    f32 t;           // 0x00  current frame
    f32 frames;      // 0x04  total frames
    s32 x8;          // 0x08  = 2
    u8 type;         // 0x0C  interpolation type
    void* table;     // 0x10  key table
};
extern "C" void HermiteInterpolation(HermiteParam* p, void* result, void* work);

extern "C" {
void* memcpy(void* dst, const void* src, unsigned int n);
int ShapeMove(cModelInfo* info);
void SetOriginalShape(cModelInfo* info);
void ClrShape(cModel* m);
int SetShape(cModelInfo* info, ShapeData* data, f32 rate);
void ResetShape(cModelInfo* info, void* dst);
void CalculateShape_new(cModelInfo* info, ShapeData* data, f32 rate, u8* dst);
}

#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
extern "C" void re4dc_gcasset_shape_reset(const void* info,const void* dst);
extern "C" void re4dc_gcasset_shape_source(const void* info,unsigned index,const void* delta,unsigned count);
#endif

void ShapeEnd(void* work);

// Start a shape animation on a model part. Returns 0 when the data has no frames.
int ShapeSet(void* work, int frame, void* data, int flags)
{
    cModelInfo* info = (cModelInfo*) work;
    ShapeData* sd = (ShapeData*) data;

    info->shape_frame = frame;
    info->pShape = sd;
    info->shapeFlags = flags;
    if (flags & 4) {
        info->shape_frame = sd->nFrame - 1;
    }
    if (sd->nFrame == 0) {
        pLog->err(0, 0, "ShapeSet : frame 0 data");
        ShapeEnd(work);
        return 0;
    }
    return 0;
}

// Advance the shape animations of a parts list.
int ShapeMove(cModelInfo* info)
{
    cModelInfo* p;

    if (info == NULL) {
        return 0;
    }
    for (p = info; p != NULL; p = p->pList) {
        if (p->pShape != NULL) {
            u32 flags;
            ShapeData* sd;

            SetOriginalShape(p);
            SetShape(p, p->pShape, (f32) p->shape_frame);
            flags = p->shapeFlags;
            sd = p->pShape;
            if (flags & 4) {
                p->shape_frame--;
                if (p->shape_frame < 0) {
                    if (flags & 1) {
                        p->shape_frame = 0;
                        p->shape_frame = sd->nFrame - 1;
                    } else if (flags & 2) {
                        p->shape_frame++;
                    } else {
                        ShapeEnd(p);
                    }
                }
            } else {
                p->shape_frame++;
                if (p->shape_frame >= sd->nFrame - 1) {
                    if (flags & 1) {
                        p->shape_frame = 0;
                    } else if (flags & 2) {
                        p->shape_frame--;
                    } else {
                        ShapeEnd(p);
                    }
                }
            }
        }
    }
    return 1;
}

// Stops the shape animation of a model info and restores the neutral shape.
void ShapeEnd(void* work)
{
    cModelInfo* info = (cModelInfo*) work;

    info->shape_frame = 0;
    info->pShape = NULL;
    SetOriginalShape(info);
}

// Clears the five shape slots (neutral face).
void SetOriginalShape(cModelInfo* info)
{
    int i;

    for (i = 0; i < 5; i++) {
        memclr_asm(&info->shape[i], sizeof(ShapeKey));
    }
}

// Stop the shape animations of every part of a model.
void ClrShape(cModel* m)
{
    cModelInfo* info;

    for (info = m->pModelInfo; info != NULL; info = info->pList) {
        if (info->be_flag & 2) {
            info->shape_frame = 0;
            info->pShape = NULL;
            info->shapeFlags = 0;
            SetOriginalShape(info);
        }
    }
}

// Register a shape at `rate` in the first free channel. Returns 1 when rate == frame count.
int SetShape(cModelInfo* info, ShapeData* data, f32 rate)
{
    int i = 0;
    int n;

    if (info->shape[i].data == NULL) {
        info->shape[i].rate = rate;
        info->shape[i].data = data;
    } else {
    retry:
        i++;
        if (i <= 4) {
            if (info->shape[i].data != NULL) {
                goto retry;
            }
            info->shape[i].rate = rate;
            info->shape[i].data = data;
        }
    }
    n = data->nFrame;
    return (f32) n < rate;
}

#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
extern "C" void re4dc_log(const char*, ...);
void* re4dc_otwc_shape_model;      // trans.cpp commonScreenMatSub: the model whose info is being morphed
u32 re4dc_otwc_shape_model_id;
#endif
// Restore the original vertex positions.
void ResetShape(cModelInfo* info, void* dst)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_GC_ASSET_MOTION_SOURCE
    re4dc_gcasset::MotionProducerScope gcasset_motion_producer;
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    re4dc_gcasset::GeometryProducerScope gcasset_geometry_scope;
#endif
    memcpy(dst, info->pData->vtxOrig, info->pData->nVtx * 8);
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    re4dc_gcasset_shape_reset(info,dst);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_GC_ASSET_MOTION_SOURCE
    // Actual neutral vertex overwrite ends prior morph-output ancestry.
    re4dc_gcasset::motion_source_reset(info);
    re4dc_gcasset::motion_source_note(info,info->pData,re4dc_gcasset::MotionBind);
#endif
}

// Shape evaluation work (0xD0 bytes, cleared).
struct ShapeWork {
    ShapeData* data;   // 0x00
    s32* table;        // 0x04  per channel key tables (relocated)
    u8 pad_8[0x18];
    f32 frames;        // 0x20  frame count + 1
    f32 rate;          // 0x24
    u8 pad_28[8];
    u8 num;            // 0x30
    u8 pad_31[3];
    u8* idx;           // 0x34  shape table index per channel
    u16_un* flags;     // 0x38  per channel flags
    u8 pad_3C[4];
    u16 x40;           // 0x40
    u8 pad_42[2];
    u32 x44;           // 0x44
    u8 pad_48[0x7C];
    u8 xC4;            // 0xC4
    u8 pad_C5[0xB];
};

struct ShapeEntry {
    u32 ofs;     // 0x00  offset of the delta list from the shape table
    s32 num;     // 0x04  entries: vertex index, dx, dy, dz (s16 each)
};

// Apply the shape `data` at `rate` to the vertex buffer `dst` (8-byte vertices, s16 xyz).
#if defined(__PPC__)
#define PSQ_L_S16(p) ({ f32 f_; asm volatile("psq_l %0,0(%1),1,5" : "=f"(f_) : "b"(p)); f_; })
#else
#define PSQ_L_S16(p) ((f32) *(const s16*) (p))
#endif
#if defined(__PPC__)
#define PSQ_ST_S16(f, p) asm volatile("psq_st %0,0(%1),1,5" : : "f"(f), "b"(p) : "memory")
#else
#define PSQ_ST_S16(f, p) (*(s16*) (p) = (s16) (f))
#endif

// Applies shape `data` at frame `rate` to the vertex buffer `dst`: for every channel flagged 4 the
// Hermite weight (percent / 100, x1.37 with shapeFlags bit3) scales that channel's delta list
// (vertex index + s16 dx/dy/dz from the model's shape table) and adds it to the vertices.
void CalculateShape_new(cModelInfo* info, ShapeData* data, f32 rate, u8* dst)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_GC_ASSET_MOTION_SOURCE
    re4dc_gcasset::MotionProducerScope gcasset_motion_producer;
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    re4dc_gcasset::GeometryProducerScope gcasset_geometry_scope;
#endif
    ShapeWork work;
    ShapeWork* w = &work;
    HermiteParam prm;
    HermiteParam* pp = &prm;
    f32 result[4];
    s16 tmp[1];
    u8 out[8];
    u32 i;
    s32* p;

    memclr_asm(w, sizeof(ShapeWork));
    w->data = data;
    w->frames = (f32) (data->nFrame & 0x3FFF) + 1.0f;
    w->num = w->data->num;
    w->flags = (u16*) ((u8*) w->data + 3);
    w->idx = (u8*) w->data + (w->num * 2 + 3);
    p = (s32*) (w->idx + w->num);
    p = (s32*) (((u32) p + 3) & ~3);
#if defined(RE4DC_GAME) && !defined(__PPC__)
    ++p;
    Re4dcMotionLease keys(data, (unsigned**) &w->table, (unsigned*) p);
    if (keys.external()) p = w->table;
    else if (*p >= 0) {
#else
    if (*++p >= 0) {
#endif
        for (i = 0; i < w->num; i++) {
            p[i] += (u32) w->data;
        }
    }
    w->table = p;
    w->x44 = 0;
    w->x40 = 0;
    w->xC4 = 0;
    w->rate = rate;

    if (dst != NULL) {
        ShapeEntry* tbl = (ShapeEntry*) (info->pData->shapeOfs + (u32) info->pData + 4);

        pp->t = rate;
        pp->frames = w->frames;
        pp->x8 = 2;
        for (i = 0; i < w->num; i++) {
            if (w->flags[i] & 4) {
                f32 v;
                pp->type = w->flags[i] >> 12;
                pp->table = (void*) w->table[i];
                memclr_asm(out, 6);
                HermiteInterpolation(pp, result, out);
                v = result[1] / 100.0f;
                if (info->shapeFlags & 8) {
                    v *= 1.37f;
                }
                if (v != 0.0f) {
                    ShapeEntry* e = (ShapeEntry*) (w->idx[i] * 8 + (u32) tbl);
                    s16* src = (s16*) (e->ofs + (u32) tbl);
                    s32 num = e->num;
                    s32 n;
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
                    re4dc_gcasset_shape_source(info,w->idx[i],src,(unsigned)num);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_GC_ASSET_MOTION_SOURCE
                    if (num > 0) {
                        re4dc_gcasset::motion_source_note_key(info,data,(const void*) w->table[i],w->flags[i] >> 12,re4dc_gcasset::MotionShape);
                        re4dc_gcasset::motion_source_note(info,info->pData,re4dc_gcasset::MotionBind);
                    }
#endif

#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
                    {
                        static u32 reports;
                        s32 lo = 0x7fffffff, hi = -0x7fffffff - 1;
                        const s16* q = src;
                        for (n = 0; n < num; n++, q += 4) { if (*q < lo) lo = *q; if (*q > hi) hi = *q; }
                        if (num > 0 && (lo < 0 || hi >= (s32) info->pData->nVtx) && reports++ < 8) {
                            re4dc_log("OTWC shape out of range: info %08x data %08x channel %u entries %d index %d..%d nVtx %u "
                                      "dst %08x pPosBuf %08x/%08x caller %08x\n", (unsigned) (u32) info, (unsigned) (u32) data,
                                      (unsigned) i, (int) num, (int) lo, (int) hi, (unsigned) info->pData->nVtx,
                                      (unsigned) (u32) dst, (unsigned) (u32) info->pPosBuf[0], (unsigned) (u32) info->pPosBuf[1],
                                      (unsigned) (u32) __builtin_return_address(0));
                            if (reports <= 2) {
                                const u32* h = (const u32*) info->pData;
                                const u8* sd = (const u8*) data;
                                re4dc_log("OTWC   model %08x id %02x pData %08x: %08x %08x %08x %08x | +20 %08x %08x %08x %08x | +30 %08x %08x %08x %08x %08x %08x\n",
                                          (unsigned) (u32) re4dc_otwc_shape_model, (unsigned) re4dc_otwc_shape_model_id,
                                          (unsigned) (u32) h, h[0], h[1], h[2], h[3], h[8], h[9], h[10], h[11], h[12], h[13],
                                          h[14], h[15], h[16], h[17]);
                                re4dc_log("OTWC   shape table %08x first words %08x %08x %08x %08x %08x %08x; ShapeData nFrame %u num %u idx %u %u %u %u %u %u %u %u\n",
                                          (unsigned) (u32) tbl, ((const u32*) tbl)[-1], ((const u32*) tbl)[0], ((const u32*) tbl)[1],
                                          ((const u32*) tbl)[2], ((const u32*) tbl)[3], ((const u32*) tbl)[4],
                                          (unsigned) (*(const u16*) sd & 0x3FFF), (unsigned) sd[2],
                                          w->idx[0], w->idx[1], w->idx[2], w->idx[3], w->idx[4], w->idx[5], w->idx[6], w->idx[7]);
                            }
                        }
                    }
#endif
                    for (n = 0; n < num; n++) {
                        s16* vtx = (s16*) (dst + *src++ * 8);
                        PSQ_ST_S16(PSQ_L_S16(src++) * v, tmp);
                        *vtx++ += tmp[0];
                        PSQ_ST_S16(PSQ_L_S16(src++) * v, tmp);
                        *vtx++ += tmp[0];
                        PSQ_ST_S16(PSQ_L_S16(src++) * v, tmp);
                        *vtx += tmp[0];
                    }
                }
            }
        }
    }
}

// Never called (superseded by CalculateShape_new): the original linker dropped the body but kept
// its constant pool (the double 0.0 at the end of .rodata).
static void CalculateShape(cModelInfo* info, ShapeData* data, f32 rate, u8* dst)
{
    if (rate != 0.0) {
        CalculateShape_new(info, data, rate, dst);
    }
}

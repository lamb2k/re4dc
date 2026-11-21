// Offline motion keys of the native skeleton service (lanes eng-svc2, eng-svc3): the pack bake/motion_keys.py writes,
// as the service reads it. Write-up: docs/engine/SERVICES.md sections 10 and 16.
//
// A clip's pose at an integer frame k is one row (row k: every pose joint's three values, in clip order; row
// maxFrame: each axis's last key, the answer past the end of a clip that does not loop), as float32 or as 16-bit
// steps between a column's minimum and maximum (value = offset + step x scale). Joints whose three axes never change
// keep their values in the const table. Root motion (Null_pos, Null_rot) and the attach camera's channels have float32
// aux rows. Fractional frames, and clips the pack does not hold (outside the room's set), are decoded from the clip's
// own key blocks by mk_decode (skel.cpp): no copy of the keys is baked. Everything is little-endian, offsets from the
// clip.
#pragma once
#include "types.h"

#define MK_MAGIC0 0x4D344552u   // "RE4M"
#define MK_MAGIC1 0x0000324Bu   // "K2\0\0"

struct MkPack {             // 32 B
    u32 magic[2];
    u32 nClip, oIndex, bytes, flags, pad[2];   // flags 1: s16 pose rows
};
struct MkIndex {            // 8 B, sorted by identity
    u32 ident, off;
};
struct MkClip {             // 64 B
    u32 ident;
    u16 maxFrame, n;
    u16 nRows, stride;      // stride: values a pose row (f32: a multiple of 8, s16: of 16; rows start on a 32-byte line)
    u16 nConst, flags;      // flags 1: pose rows are s16 steps (quant table: scale, offset a column)
    u16 nAux, auxStride;    // aux rows: float32, unpadded
    u32 oJoint, oRows, oConst, oAux, oQuant, srcBytes, pad[5];
};
struct MkJoint {            // 8 B
    u16 info;               // the original's kind word: kind | camera channel << 8 | key type << 12
    u8 pno, src;            // parts; MK_ROWS, MK_CONST, MK_AUX, MK_NONE
    u16 col, pad;
};
enum { MK_ROWS = 0, MK_CONST = 1, MK_AUX = 2, MK_NONE = 3 };
enum { MK_S16 = 1 };

inline const MkJoint* mk_joints(const MkClip* k) { return (const MkJoint*) ((const u8*) k + k->oJoint); }
inline const f32* mk_rows(const MkClip* k) { return (const f32*) ((const u8*) k + k->oRows); }
inline const u16* mk_qrows(const MkClip* k) { return (const u16*) ((const u8*) k + k->oRows); }
inline const f32* mk_quant(const MkClip* k) { return (const f32*) ((const u8*) k + k->oQuant); }
inline const f32* mk_const(const MkClip* k) { return (const f32*) ((const u8*) k + k->oConst); }
inline const f32* mk_aux(const MkClip* k) { return (const f32*) ((const u8*) k + k->oAux); }

// The evaluator's row rule: the baked row of a frame, or -1 (decode from the keys): an integer frame before the end;
// the last row at or past the end of a clip that does not loop; a looping clip wraps once first. (Lane eng-e1n: here
// from skel.cpp, so the camera service reads its converted tracks by the same rule.)
inline int mk_row_of(const MkClip* k, f32 f, f32 maxFrame, u32 flags)
{
    if (maxFrame <= f) {
        if ((flags & 6) != 4) return k->maxFrame;
        f -= maxFrame;
        if (maxFrame <= f) return -1;
    }
    const int fi = (int) f;
    return (f32) fi == f && fi >= 0 ? fi : -1;
}

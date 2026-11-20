// Offline motion keys of the native skeleton service (lane eng-svc2): the pack bake/motion_keys.py writes, as the
// service reads it. Write-up: docs/engine/SERVICES.md section 10.
//
// A clip's pose at an integer frame k is one row of floats (row k: every pose joint's three values, in clip order;
// row maxFrame: each axis's last key, the answer past the end of a clip that does not loop). Joints whose three
// axes never change keep their values in the const table. Fractional frames take the clip's own key blocks (cold
// section) through the original decoder with its history off. Everything is little-endian, offsets from the clip.
#pragma once
#include "types.h"

#define MK_MAGIC0 0x4D344552u   // "RE4M"
#define MK_MAGIC1 0x0000314Bu   // "K1\0\0"

struct MkPack {             // 32 B
    u32 magic[2];
    u32 nClip, oIndex, bytes, pad[3];
};
struct MkIndex {            // 8 B, sorted by identity
    u32 ident, off;
};
struct MkClip {             // 64 B
    u32 ident;
    u16 maxFrame, n;
    u16 nRows, stride;      // stride: floats a row (a multiple of 8)
    u16 nConst, flags;
    u32 oJoint, oRows, oConst, oColdTab, oCold, coldBytes, srcBytes, pad;
};
struct MkJoint {            // 8 B
    u16 info;               // the original's kind word: kind | camera channel << 8 | key type << 12
    u8 pno, src;            // parts; 0 rows, 1 const, 2 not a pose channel (the original path)
    u16 col, pad;
};
enum { MK_ROWS = 0, MK_CONST = 1, MK_OTHER = 2 };

inline const MkJoint* mk_joints(const MkClip* k) { return (const MkJoint*) ((const u8*) k + k->oJoint); }
inline const f32* mk_rows(const MkClip* k) { return (const f32*) ((const u8*) k + k->oRows); }
inline const f32* mk_const(const MkClip* k) { return (const f32*) ((const u8*) k + k->oConst); }
inline const u32* mk_cold_tab(const MkClip* k) { return (const u32*) ((const u8*) k + k->oColdTab); }
inline const u8* mk_cold(const MkClip* k) { return (const u8*) k + k->oCold; }

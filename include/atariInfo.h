#ifndef ATARIINFO_H
#define ATARIINFO_H

#include "types.h"
#include "vec.h"

class cModel;

#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
// GAME_ATCHK_CACHE (game30.mk; G, collision traversal; exact): at_mod keeps each list's em-em candidates
// and reuses them while no body's collidable test changed. That test reads m_flag bit 0x200 and
// m_radius2 != 0, so both fields go through these wrappers (same size, alignment and values): a write
// that flips the test's part notes the info; a reuse re-tests the noted infos against the kept list.
// GAME_ATCHK_DISTINCT29=1 coalesces writes to each info independently for the enemy and object readers.
// Zeroing a whole info (AtariInfoConstruct) and the rooms'
// volatile flag helpers note it through RE4DC_ATARI_TOUCH. Copies between infos are deleted (a copy into a
// local buffer uses a byte copy: the buffer is in no list), and so is taking a field's address: a write
// through a pointer would pass the wrapper, so every such site fails to compile until it takes the
// address with __builtin_addressof and notes the info (the flag helpers, the at_mod prefetches).
extern "C" u32 re4dc_atari_seq;
extern "C" const void* re4dc_atari_dirty[64];
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
extern "C" void re4dcAtariNoteDistinct29(const void* info);
#endif
static inline void re4dcAtariNote(const void* info)
{
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
    re4dcAtariNoteDistinct29(info);
#else
    re4dc_atari_dirty[re4dc_atari_seq & 63] = info;
    ++re4dc_atari_seq;
#endif
}
struct AtFlag16 {
    u16 v;
    operator u16() const { return v; }
    AtFlag16& operator=(const AtFlag16&) = delete;  // between infos: assign the value (u16)
    void operator&() const = delete;                  // a write through a pointer would not be noted
    AtFlag16& operator=(u32 x) { put((u16) x); return *this; }
    AtFlag16& operator|=(u32 x) { put((u16) (v | x)); return *this; }
    AtFlag16& operator&=(u32 x) { put((u16) (v & x)); return *this; }
    AtFlag16& operator^=(u32 x) { put((u16) (v ^ x)); return *this; }
    void put(u16 n)
    {
        if ((v ^ n) & 0x200) {
            re4dcAtariNote((const u8*) this - 0x1A);  // cAtariInfo::m_flag (asserted below)
        }
        v = n;
    }
};
struct AtRadius {
    f32 v;
    operator f32() const { return v; }
    AtRadius& operator=(const AtRadius&) = delete;  // between infos: assign the value (f32)
    void operator&() const = delete;                  // a write through a pointer would not be noted
    AtRadius& operator=(f32 x) { put(x); return *this; }
    AtRadius& operator+=(f32 x) { put(v + x); return *this; }
    void put(f32 n)
    {
        if ((v != 0.0f) != (n != 0.0f)) {
            re4dcAtariNote((const u8*) this - 0x10);  // cAtariInfo::m_radius2 (asserted below)
        }
        v = n;
    }
};
#define RE4DC_AT_FLAG16 AtFlag16
#define RE4DC_AT_RADIUS AtRadius
#define RE4DC_ATARI_TOUCH(info) re4dcAtariNote(info)
#else
#define RE4DC_AT_FLAG16 u16
#define RE4DC_AT_RADIUS f32
#define RE4DC_ATARI_TOUCH(info) ((void) 0)
#endif

enum PRIORITY {
    PRI_NORMAL = 0,
    PRI_LV1 = 1,
    PRI_LV2 = 2,
    PRI_LV3 = 3
};

// Character collision info (game/atariInfo.cpp), 0x4C bytes; embedded in cPlayer at 0x2B4.
// The flag helpers are parameterless in-class inlines on purpose: the original accesses go
// `addi rX,this,0x2B4; lhz 0x1A(rX); andi. 0xFCFF` (address computed once, used by the load and
// the store; the mask folded to 16 bits). A direct member access folds the address into one
// displacement; an inline taking the bit as a parameter gives `rlwinm` instead of `andi.`.
class cAtariInfo {
public:
    Vec m_offset;         // 0x00  offset from the model (rotated by the model's rot)
    f32 m_radius;       // 0x0C  push rectangle half size along local X (pl_push) / cylinder radius
    RE4DC_AT_RADIUS m_radius2;       // 0x10  along local Z
    f32 m_height;           // 0x14  half height
    s16 m_parts_no;     // 0x18  parts index + 1 the info follows, 0 = the model (pl_dmg Pl_R0_Die sets 4)
    RE4DC_AT_FLAG16 m_flag;       // 0x1A  bit1: rectangle (dispRect), bits 3-4: priority, bits 8-9 (0x300): collide with enemies
    f32 m_radius_n;      // 0x1C  rect size `move` interpolates m_radius/m_radius2 towards
    f32 m_radius2_n;      // 0x20
    u16 m_hokan;         // 0x24  frames left of the interpolation
    u16 m_stat;         // 0x26  (init0 sets 1) bit0: no character collision this frame (at_mod EmAtCheck)
    cModel* m_pMod;   // 0x28  model pushed along with this one (at_mod At_em_sphere_sphere_ck)
    f32 m_radius3;         // 0x2C
    Vec m_Pos;    // 0x30  getPos result of this frame (at_mod EmAtCheck)
    Vec m_oldPos; // 0x3C  m_Pos of the previous frame
    union {
        u32 x48;             // 0x48
        cAtariInfo* m_pList;    // 0x48  next info of the chain (at_mod DrawOba)
    };

#if defined(__PPC__)
    cAtariInfo();
#endif
    void init0(int parts, int hokan, int flags, f32 x, f32 y, f32 z, f32 rx, f32 rz, f32 w, f32 h);
    // init(parts, flags, hokan, ...) = init0(parts, hokan, flags, ...); m_flag |= 1
    void init(int parts, int flags, int hokan, f32 x, f32 y, f32 z, f32 rx, f32 rz, f32 w, f32 h);
    void setPriority(int prio);  // flags bits 3-4
    // mode < 0: rect = (100, 100), rect2 = a/b, cnt = -mode; mode == 0: rect = rect2 = a/b; > 0: rect2 only, cnt = mode
    void set(int mode, f32 a, f32 b);
    void move();
    // World position (`getPos`) and the positions before/after this frame's move (`getSpeedVector`).
    void getSpeedVector(cModel* m, Vec* oldPos, Vec* pos);
    void getPos(cModel* m, Vec* out);
    void disp(cModel* m);
    void dispRect(cModel* m);
    void throughOn() { m_flag &= ~0x300; }   // pass through enemies (mahoThroughOn)
    void throughOff() { m_flag |= 0x300; }
    void clrFlag100() { m_flag &= ~0x100; }  // obj20 SetObaModel
    void setFlag100() { m_flag |= 0x100; }   // sce_com SceUpCutEnd
    void clrFlag200() { m_flag &= ~0x200; }  // emhit setParent: the parent no longer collides with enemies
    void setFlag200() { m_flag |= 0x200; }   // obj13 objLadderSatSet
    void scrOn() { m_flag &= ~0x200; m_flag |= 0x100; }  // obj00 setScrAtari
};
#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
static_assert(__builtin_offsetof(cAtariInfo, m_flag) == 0x1A && __builtin_offsetof(cAtariInfo, m_radius2) == 0x10,
              "AtFlag16 / AtRadius note their info by these offsets");
#endif

#endif

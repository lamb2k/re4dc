#ifndef ESP_H
#define ESP_H

#include "types.h"
#include "vec.h"
#include "gx.h"
#include "model.h"
#include "trans_ot.h"

struct EspGenPrmW {
    u32 xCC;           // 0xCC
    u32 xD0;           // 0xD0
};
struct EspGenPrmH {
#if defined(__PPC__)
    u16 xCC;           // 0xCC
    u16 xCE;           // 0xCE
    u16 xD0;           // 0xD0
    u16 xD2;           // 0xD2
#else
    // Names identify source word lanes, not native byte offsets.
    u16 xCE, xCC;
    u16 xD2, xD0;
#endif
};
struct EspGenPrmB {
#if defined(__PPC__)
    u8 xCC, xCD, xCE, xCF;  // 0xCC
    u8 xD0, xD1, xD2, xD3;  // 0xD0
#else
    u8 xCF, xCE, xCD, xCC;
    u8 xD3, xD2, xD1, xD0;
#endif
};
union EspGenPrm {
    EspGenPrmW w;
    EspGenPrmH h;
    EspGenPrmB b;
};

// Effect generator record (game/eff_sys.cpp, game/espgen*.cpp): one 0x12C byte entry of an
// EspSeqData (PS2 cEspSeqTbl, 1:1). GC types kept where the PS2 byte is signed.
struct EspGenWork {
    u8 Be_flg;         // 0x00 (PS2 Be_flg)
    u8 Id;             // 0x01 esp id / generator sub type (PS2 Id)
    u8 Tex_id;         // 0x02 (PS2 Tex_id)
    u8 Type;           // 0x03 (PS2 Type) -> cEsp::m_Type
    u16 Set_time;      // 0x04 sequence time (espgen10 compares it with the frame counter) (PS2 Set_time)
    u8 Parent_no;      // 0x06 event model index (EspEvModList) (PS2 Parent_no)
    u8 Parts_no;       // 0x07 (PS2 Parts_no)
    u32 Tool_flg;      // 0x08 (PS2 Tool_flg)
    Vec Pos;           // 0x0C generator position (PS2 Pos)
    Vec R_pos;         // 0x18 position random range (esp1a: .x/.y min / max distance factor) (PS2 R_pos)
    Vec Speed;         // 0x24 (PS2 Speed)
    f32 D_speed;       // 0x30 (PS2 D_speed)
    Vec R_speed;       // 0x34 (PS2 R_speed)
    Vec Speed_plus;    // 0x40 acceleration (PS2 Speed_plus)
    Vec R_speed_plus;  // 0x4C acceleration random range (PS2 R_speed_plus)
    Vec Ang;           // 0x58 (PS2 Ang)
    Vec R_ang;         // 0x64 rotation random range (PS2 R_ang)
    Vec Ang_plus;      // 0x70 rotation speed (PS2 Ang_plus)
    Vec R_ang_plus;    // 0x7C rotation speed random range (PS2 R_ang_plus)
    f32 Size_base_x;   // 0x88 (PS2 Size_base_x)
    f32 Size_base_y;   // 0x8C (PS2 Size_base_y)
    f32 R_size_base;   // 0x90 (PS2 R_size_base)
    f32 Size_plus;     // 0x94 (Espgen43: extra z scale, +1) (PS2 Size_plus)
    f32 D_size_plus;   // 0x98 (PS2 D_size_plus)
    u8 Col_start_r;    // 0x9C colour r (PS2 Col_start_r)
    u8 Col_start_g;    // 0x9D colour g
    u8 Col_start_b;    // 0x9E colour b
    u8 Col_start_a;    // 0x9F colour a
    f32 Col_d_r;       // 0xA0 colour step per frame as 0..1 floats (PS2 Col_d_r)
    f32 Col_d_g;       // 0xA4
    f32 Col_d_b;       // 0xA8
    f32 Col_d_a;       // 0xAC
    u16 Col_max_cnt;   // 0xB0 (esp_efm: fade start frame) (PS2 Col_max_cnt)
    u16 Col_start_cnt; // 0xB2 (esp_efm: fade length) (PS2 Col_start_cnt)
    u16 Pos_start_cnt; // 0xB4 (esp_efm: move start frame) (PS2 Pos_start_cnt)
    u16 Size_start_cnt; // 0xB6 (esp_efm: scale start frame) (PS2 Size_start_cnt)
    u16 Life_max;      // 0xB8 (esp_efm: life) (PS2 Life_max)
    u16 Life_time;     // 0xBA (esp_efm: start frame) (PS2 Life_time)
    u8 Ptn_no;         // 0xBC (esp_sub: start animation pattern) (PS2 Ptn_no)
    u8 Anm_rate;       // 0xBD (esp_sub: animation speed - 0x20) (PS2 sint8 Anm_rate)
    u16 Anm_cnt;       // 0xBE (esp_sub: animation counter) (PS2 Anm_cnt)
    u8 Release_time;   // 0xC0 (esp_efm: parent release frame) (PS2 Release_time)
    u8 Groupe_no;      // 0xC1 (PS2 Groupe_no)
    u8 Blend_type;     // 0xC2 (esp_sub: blend type, bl[] index) (PS2 Blend_type)
    u8 Shimmer_type;   // 0xC3 (esp_sub: cEsp m_Shimmer_type) (PS2 Shimmer_type)
    u8 Shimmer_pow;    // 0xC4 (esp_sub: cEsp m_Shimmer_pow) (PS2 Shimmer_pow)
    u8 MaskTex_id;     // 0xC5 (esp_sub: mask texture id) (PS2 MaskTex_id)
    u8 Del_far;        // 0xC6 (esp_sub: cEsp m_Del_far / 10) (PS2 Del_far)
    u8 Del_near;       // 0xC7 (esp_sub: cEsp m_Del_near / 10) (PS2 Del_near)
    u8 Work8[4];       // 0xC8 per-effect byte parameters (SE number, area number, type, ...) (PS2 signed char Work8[4])
    EspGenPrm prm;     // 0xCC .. 0xD4: per-effect integer parameters (word or halfword view) (PS2 int Work32[0..1])
    u32 xD4;           // 0xD4 (PS2 Work32[2])
    Vec Vec0;          // 0xD8 per-effect float parameters (esp_efm: obj05 burst centre / obj09 size) (PS2 Vec0)
    Vec Vec1;          // 0xE4 (esp_efm: bounce) (PS2 Vec1)
    Vec Vec2;          // 0xF0 (esp_efm: burst centre random range; esp0e .z: visible cone angle in degrees) (PS2 Vec2)
    u8 WorkSp8[4];     // 0xFC ([3]: esp_efm obj04 motion type) (PS2 WorkSp8[4])
    // 0x100..0x12C: sequence record tail (records of an EspSeqData are 0x12C bytes)
    u8 pad_100[0x104 - 0x100];
    u8 Espgen_work8_4[4]; // 0x104 (espgen02: path id, path number, path position offset, its random range) (PS2 Espgen_work8_4)
    u8 Kind;           // 0x108 0 = esp, 1 = espgen (PS2 Kind)
    u8 Espgen_id;      // 0x109 generator id (0xFF = loop marker) (PS2 Espgen_id)
    u8 Espgen_type;    // 0x10A (PS2 Espgen_type)
    u8 Espgen_flg;     // 0x10B (PS2 Espgen_flg)
    u8 x10C;           // 0x10C (PS2 signed char Espgen_work8[0])
    u8 x10D;           // 0x10D (PS2 Espgen_work8[1])
    s8 x10E;           // 0x10E (PS2 Espgen_work8[2])
    u8 x10F;           // 0x10F (PS2 Espgen_work8[3])
    s16 Espgen_work16[4]; // 0x110 (PS2 Espgen_work16[4])
    Vec Espgen_vec0;   // 0x118 (espgen02: scale - 1 in 10ths) (PS2 Espgen_vec0)
    u8 x124;           // 0x124 (PS2 signed char Espgen_work8_2[0])
    u8 x125;           // 0x125 (PS2 Espgen_work8_2[1])
    u8 x126;           // 0x126 (PS2 Espgen_work8_2[2])
    u8 x127;           // 0x127 (PS2 Espgen_work8_2[3])
    u8 Espgen_work8_3[4]; // 0x128 ([1]: espgen02 rotation x in 1/256 turns, [2]: rotation y, [3]: path orientation mode bits) (PS2 Espgen_work8_3)
};

// Effect sequence data block: 0x30 byte header followed by 0x12C byte records.
struct EspSeqData {
    u16 num;           // 0x00 number of records
    u8 pad_2[6];
    u16 flags;         // 0x08
    u8 parts;          // 0x0A default parts number (EstSet with no = -1)
    u8 pad_B;
    Vec pos;           // 0x0C default position (EstSet with pos = NULL)
    Vec rot;           // 0x18 default rotation in degrees (EstSet with rot = NULL)
    u8 pad_24[0x30 - 0x24];
    EspGenWork rec[1]; // 0x30
};

// Texture animation data returned by EspGetAnmAddr (eff_sys.cpp). Partial layout.
struct EspAnmData {
    u16 Width;         // 0x00 texture width (PS2 cAnm::Width)
    u16 Height;        // 0x02 texture height (PS2 cAnm::Height)
    s16 Cx;            // 0x04 sprite width / centre x (PS2 cAnm::Cx)
    s16 Cy;            // 0x06 sprite height / centre y (PS2 cAnm::Cy)
    union {
        u16 Frames;    // 0x08 number of patterns (PS2 cAnm::Frames)
        struct {
            u8 x8;
            u8 x9;     // 0x09 low byte of Frames
        };
    };
    u8 Xn;             // 0x0A (PS2 cAnm::Xn)
    u8 Loop;           // 0x0B bits 0-1: loop mode (PS2 cAnm::Loop)
    u8 Data_num;       // 0x0C 0 = fixed pattern time (PS2 cAnm::Data_num)
    u8 pad_0D[3];
    u8 Frame_cnt[1];   // 0x10 pattern table: Frames entries, then the per-pattern display times (PS2 cAnm::Frame_cnt)
};

// Effect owner info at the head of every cEsp (copied as a block by esp3f).
struct EspInfo {
    u16 Core_flg;            // 0x00
    u8 Core_kind;             // 0x02
    u8 owner;             // 0x03
    union {
        u32 Call_no;        // 0x04
        struct {
            u8 x4;     // 0x04
            u8 x5;     // 0x05
            u8 x6;     // 0x06
            u8 x7;     // 0x07
        } b;
    };
    u32 Core_pEm;            // 0x08
};

// One effect sprite (game/esp.cpp, game/esp_sub.cpp). sizeof 0xF8; the vptr sits at 0xF4.
class cEsp {
public:
    EspInfo info;      // 0x00
    u8 m_Be_flg;           // 0x0C bit0: in use
    u8 m_Id;             // 0x0D effect id
    u8 m_Tex_id;       // 0x0E texture animation id (EspGetAnmAddr; EspGenWork Tex_id) (PS2 m_Tex_id)
    u8 m_Type;         // 0x0F EspGenWork Type (PS2 m_Type)
    u8 m_Rno0;         // 0x10 routine numbers (PS2 m_Rno0..3)
    u8 m_Rno1;         // 0x11
    u8 m_Rno2;         // 0x12 (PS2 m_Rno2)
    u8 m_Rno3;         // 0x13 (PS2 m_Rno3)
    u16 m_Del_near;    // 0x14 near delete distance (EspGenWork Del_near * 10) (PS2 m_Del_near)
    u16 m_Del_far;           // 0x16
    u32 m_Tool_flg;         // 0x18 effect option bits
    cModel* m_pMod;    // 0x1C model the effect is attached to
    u32 m_Guid_pMod;           // 0x20
    cCoord* parent;    // 0x24 parent coordinate (pEffParentWorld = world)
    u8 m_Parts_no;        // 0x28 parts of pModel the effect follows
    u8 m_Release_time;      // 0x29 frames to stay attached to parent (0xFF = forever)
    u16 m_Flg;      // 0x2A bit1: sizeY is a world-space length (beam sprites)
    Vec m_Pos;           // 0x2C
    Vec m_Speed;           // 0x38
    f32 m_D_speed;      // 0x44
    Vec m_Speed_plus;           // 0x48
    Vec m_Ang;           // 0x54
    Vec m_Ang_plus;        // 0x60
    f32 m_Size_base_x;         // 0x6C
    f32 m_Size_base_y;         // 0x70
    f32 m_Size_mul;         // 0x74
    f32 m_Size_plus;      // 0x78
    f32 m_D_size_plus;    // 0x7C
    u8 m_Col_start_r;            // 0x80 (esp0c: copied into the est work colour bytes)
    u8 m_Col_start_g;            // 0x81
    u8 m_Col_start_b;            // 0x82
    u8 m_Col_start_a;            // 0x83
    f32 m_Col_r;          // 0x84
    f32 m_Col_g;          // 0x88
    f32 m_Col_b;          // 0x8C
    f32 m_Col_a;          // 0x90
    f32 m_Col_d_r;       // 0x94
    f32 m_Col_d_g;       // 0x98
    f32 m_Col_d_b;       // 0x9C
    f32 m_Col_d_a;       // 0xA0
    u8 xA4;            // 0xA4 GXSetBlendMode type (xA5 src factor, xA6 dst factor, xA7 logic op)
    u8 xA5;            // 0xA5
    u8 xA6;            // 0xA6
    u8 xA7;            // 0xA7
    u16 m_Col_max_cnt;           // 0xA8
    u16 m_Col_start_cnt;           // 0xAA
    u16 m_Pos_start_cnt;        // 0xAC frames the speed is applied (0 = always)
    u16 m_Size_start_cnt;      // 0xAE frames the scale speed is applied (0 = always)
    u16 m_Life_max;          // 0xB0 life time in frames (0 = infinite)
    u16 m_Life_time;           // 0xB2 frame counter
    u8 m_Ptn_no;         // 0xB4 current animation pattern
    u8 m_Anm_rate;         // 0xB5
    u16 m_Anm_cnt;        // 0xB6
    f32 m_Radius;           // 0xB8
    Mtx m_Mat;           // 0xBC model matrix built by the Trans functions
    union {
        u8 pad_EC[0xF4 - 0xEC];
        struct {
            u8 m_Shimmer_type;        // 0xEC  (EspGenWork xC3; esp.cpp: 0 = plain EspCommonTrans)
            u8 m_Shimmer_pow;        // 0xED  (EspGenWork xC4)
            u16 m_MaskAnm_cnt;   // 0xEE  mask texture animation counter
            u8 m_MaskPtn_no;    // 0xF0  mask texture animation pattern
            u8 m_MaskTex_id;     // 0xF1  mask texture animation id (EspGenWork xC5)
            u8 m_Blend_type;  // 0xF2  EspGenWork xC2 (3: colour bytes scaled by the fade)
            u8 xF3;
        };
    };
    // 0xF4 vptr

    void* operator new(unsigned int size);
    cEsp();
    virtual ~cEsp();
    virtual void move();
    virtual int SetFreeWork(EspGenWork* gen, u32* seed);
    virtual void Destruct();

    int CommonMove();
    int AnmMove();
    int ColorUpdate();
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE == 2
    int CommonMoveSrc();   // GAME_FX_MOVE=2: the source functions beside the kernels (esp_sub.cpp)
    int AnmMoveSrc();
#endif
    void ApplyMatrix(Mtx m);
    void CommonStateSet();
    int ChannelSet();   // col.a != 0 (esp18 tests it)
};
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE
// GAME_FX_MOVE (game30.mk, lane fx): field access through a walking pointer. FXL loads *p and advances
// p by one float, FXS stores x at the float before p and moves p there (SH-4 fmov.s @Rm+ / @-Rn: FP
// loads and stores have no displacement form, so a field is otherwise reached in three
// instructions). Only loads and stores are asm; every float operation stays C (contraction off).
#define FXL(p, x) __asm__ __volatile__("fmov.s @%1+,%0" : "=f"(x), "+r"(p) : : "memory")
#define FXS(p, x) __asm__ __volatile__("fmov.s %1,@-%0" : "+r"(p) : "f"(x) : "memory")
#endif

// game/esp3f.cpp: vector buffer owned by an effect (see esp3f.cpp for the class)
class cEsp3f;
int Esp3f_Alloc(u32 size, u32 num, cEsp3f** out, EspInfo* info);
Vec* Esp3f_GetVecPtr(cEsp3f* p, u32 no);

// game/esp.cpp
typedef cEsp* (*EspCreateFunc)();
typedef void (*EspTransFunc)(cEsp*);
void PushEsp(cEsp* esp);
// GAME_ESP_OWNER (game30.mk, square plan: active effects): live esp slots counted per bucket of
// info.Core_pEm, so EspDelete with an owner (c != 0) returns at once when no live slot can have that
// owner (cEm10::move deletes its own effects every tick in several states; the slot loop then finds
// nothing). The count follows every change of a live slot's Core_pEm: PullEsp / PushEsp, and the
// three info copies (ESP_INFO_SET); pool alloc / free / push / pop mark it stale and the next
// EspDelete recounts. =2 (check build): every early return is also checked by the slot loop.
#if defined(RE4DC_ESP_OWNER) && RE4DC_ESP_OWNER
extern "C" unsigned short re4dc_esp_own[64];
extern "C" unsigned long re4dc_esp_own_valid;
extern "C" void re4dc_esp_info_set(cEsp* esp, const EspInfo* info);
static inline unsigned long re4dcEspOwnB(unsigned long pEm)
{
    return ((pEm >> 4) ^ (pEm >> 10)) & 63;
}
#define ESP_INFO_SET(esp, inf) re4dc_esp_info_set((cEsp*) (esp), (inf))
#else
#define ESP_INFO_SET(esp, inf) ((esp)->info = *(inf))
#endif
// GAME_FX_SCAN (game30.mk, lane fx; exact; needs GAME_ESP_OWNER=1): slot bitmaps beside the owner
// counts, so the per-tick pool scans visit only slots that can pass their tests, in the same
// ascending order. re4dc_fx_esp_live: every live slot (PullEsp sets, PushEsp clears); row B of
// re4dc_fx_esp_ownmap: every live slot whose Core_pEm is non-zero and falls in owner bucket B (the
// three info copies move it). They follow re4dc_esp_own_valid (pool alloc / free / push / pop make
// them stale; the next user rebuilds them) and describe pools of up to 1024 slots
// (re4dc_fx_esp_ok). The loops keep the source shape (every slot in order, the source test on
// each one reached) and step over runs of clear bits while the maps are the ones they checked
// (re4dc_fx_esp_gen unchanged); the word is re-read at every step, so a slot pulled or pushed by a
// call is seen or skipped exactly as the source loop would, and after a pool change the rest of the
// pass tests every slot.
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
#ifndef RE4DC_FX_ESP_WORDS
#define RE4DC_FX_ESP_WORDS 32   // ESP_MAP_WORDS (effects30.mk; lane lake66r): 57 covers r10b's 1800-slot pool
#endif
extern "C" unsigned long re4dc_fx_esp_live[RE4DC_FX_ESP_WORDS];
extern "C" unsigned long re4dc_fx_esp_ownmap[64][RE4DC_FX_ESP_WORDS];
extern "C" unsigned long re4dc_fx_esp_ok;
extern "C" int re4dc_fx_esp_ready();   // syncs when stale; 1 when the maps describe the pool
extern "C" unsigned long re4dc_fx_esp_gen;   // bumped when the maps go stale or are rebuilt
extern "C" unsigned long re4dc_fx_chk[16];   // =2 check counters (esp.cpp logs them)
enum {
    FXC_ESP_MOVE,   // EspMove passes
    FXC_ESP_DEL,    // EspDelete calls through the owner rows
    FXC_EG_MOVE,    // EspgenMove / EspgenTrans passes
    FXC_EG_DEL,     // EspgenDelete calls through the occupied map
    FXC_EFM,        // EfmDelete calls through the candidate list
    FXC_EFM_BUILD,  // candidate list rebuilds
    FXC_MIS_ESP,    // skipped esp slots the source would have moved / deleted
    FXC_MIS_EG,     // skipped controllers the source would have moved / drawn / deleted
    FXC_MIS_EFM,    // skipped objects the source would have tested (id 4 / 5 / 9)
    FXC_MAP_ERR,    // map bits that disagree with the pool (live / owner rows)
    FXC_FALLBACK,   // loops finished by the source loop after a pool change
    FXC_VISIT,      // slots visited by the fast loops
};
// Index of the lowest set bit of x (x != 0).
static inline unsigned long re4dcFxCtz(unsigned long x)
{
    static const unsigned char tbl[32] = {0,  1,  28, 2,  29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4,  8,
                                          31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6,  11, 5,  10, 9};
    return tbl[((x & (0u - x)) * 0x077CB531u) >> 27];
}
#endif
extern "C" {
void EspFuncTblSet(int id, EspCreateFunc create, EspTransFunc trans);
int PullEsp(cEsp** out, int id);
cEsp* EspGetDmyPtr();
void EspAddOtAfterRender(cEsp* esp, void (*func)(cEsp*));
void EspArrayClear();
// game/esp_app.cpp
void EffSetId();
void EspFreeSizeCheckAll();
void EffCrearRoomSeFunc();
void EffAreaUpdate();
void EffEm2d_setTexRender(cModel* m);
void EspDrawLaserLine2(Vec* from, Vec* to, u8 r, u8 g, u8 b, u8 a);
void EspSetGatling(Vec pos, Vec dir);   // Vec by value (obj15)
void setPlWaterOtType();
// game/eff_sys.cpp
void EffSetAreaState(int no, int on);
// game/esp_efm.cpp
void EfmDelete(int a, int b, int c);
void EfmDeleteEvent();
void EfmArrayClear();
// game/esp_app.cpp
int EffAreaCheckInRoom(Vec* pos);
// game/esp01.cpp
void EspStrip_draw_poly(cEsp* esp, int no, Vec* v, u8 texRepeat, int flag);
// game/trans_ot.cpp: AddOtWorldPos & co. are declared in trans_ot.h (void* data / u16 kind).
// game/esp_sub.cpp
void EspCommonTrans(cEsp* esp);
int EspEstSetSelect(int owner, int id, int no, cEsp** out, int bNoSuspend);   // objWep drawPoint: (0, 0x50, 0, &esp, 1)
// game/esp_app.cpp: laser sight line (objWep drawLaserSight), Vec by value
void EspDrawLaserLine(Vec from, Vec to, f32 width);
// game/eff_sys.cpp
int EspGetAnmAddr(int no, EspAnmData** out);
void EspTexSet(int anmNo, int ptn);
void* EspGetPathAddr(u32 owner, int id);
struct EspSeqData* EspGetEstAddr(u32 owner, int id, int quiet);
void EspGenSetMoveLoop(int loop);
void EspGenLoopMove();
// game/path.cpp
int PathHasWeight(void* path);
f32 PathGetLength(void* path);
int PathGetPos(void* path, f32 dist, u16* seg, Vec* out);  // f32 second: callee copies f1 right after r3
int PathGetPosEm(void* path, f32 dist, cModel* model, u16* seg, Vec* out);
int EspGetTplAddr(int no, void** out);
// game/est.cpp. void: no caller reads r3 after the call, and with an `int` result the call's
// set of r3 changes the haifa depend counts, moving `li r3,0` to the end of the arg setup
// (obj01/obj10 move00, obj10AddSpeed).
void EstSet(int a, int b, Vec* pos, Vec* rot, int c, int d, int e, int f, u32 g, void* h);
}
// game/eff_sys.cpp
int EspGenGetMoveLoop();
extern cCoord* pEffParentWorld;
extern char* owner_name_tbl[0xD1];   // effect owner names 0..0xD0 (debug display; eff_sys.cpp)
// Struct-member view of the same pointer (the pLog trick, db_log.h): a load through it is not
// hoisted above a preceding struct copy through `this` (esp01 move: `w->pos0 = pos; parent =
// pEffParentWorld`). Only use where the target shows the load after such stores; wrapping the
// global itself changes load order in units that already match (esp0b, esp1a, esp40).
struct EffParentWorldPtr {
    cCoord* p;
};
#define pEffParentWorldS (((EffParentWorldPtr*) &pEffParentWorld)->p)
// game/esp_app.cpp
extern "C" void EspCallSeType(int type, Vec* pos);
void EffCallRoomSeFunc(int no, Vec* pos);
int EffAreaCheckNo(Vec* pos, u8 areaNo);
void EspFootCall(int type, int no, Vec* pos);
int EspPlWaterCall(int type, Vec* pos);
// game/Espgen42.cpp
int GetWaterHeight(Vec* pos, f32* height);
extern "C" void AddWaterPower(Vec* pos, f32 power);
extern "C" {
void EspWaterInit();
void Espgen42SetNoWater(int on);
int GetWaterCrossPos(Vec* pos, Vec* dir, Vec* out);
}
// game/Espgen43.cpp
extern "C" {
int GetSandHeight(Vec* pos, f32* height);
void AddSandPower(Vec* pos, f32 power);
// game/eff_sys.cpp
int EspChkTexId(int no);   // 1 when texture `no` has an object
GXTexObj* EspGetTexObj(int no, int ptn_no);
GXTlutObj* EspGetTlutObj(int no);
struct EspTexWk* EspGetTexWk(int id, int quiet);   // NULL (and an error unless quiet) when the id has no texture
int EspGetTexOwner(int id, u32* out);
int EspGetEfmAddr(int id, void** model, void** tpl);
int EspGetEfmMotAddr(int id, u32 no, void** out);
u8 EspPullCoreKind();
int EffAreaDataLoad(struct SstArea* area);
int EffIsSetFinalCol();
void EffGetFinalCol(GXColor* col);
void EffSetFinalCol(u8 r, u8 g, u8 b, u8 a);
int EffGetAreaState(int no);
void EffSetToolState(int state);
u8 EffGetToolState();
void EffClearToolState();
void EffSetToolStateCallBack(int no, void (*on)(), void (*off)());
void EffCallToolStateCallBack();
// Loads the effect data at `addr` under `owner` (the rooms load their EFF sub-files)
int EspDataLoad(u32 addr, u32 owner, int flag);
}
// game/eff_sys.cpp (C++ linkage): the TPL of effect model `id`; 0 when not registered
int EspGetEfmTplAddr(int id, void** tpl);
// game/eff_sys.cpp: quad display list shared by the sprite effects (esp_sub)
extern u8 g_EspCommonDisplayList[0x60];
// game/trans.cpp: fallback texture used when an effect texture id has no object
extern GXTexObj Specular;

// Sprite texture-corner selection (esp_sub/esp0f/esp12/esp16/esp18 Trans; esp08 has its own leaf
// shapes): flags bit1 flips s, bit2 flips t, screen sprites are drawn upside down. One combined
// condition and corners built from a `zero` variable: each leaf is a jump target where cse knows
// neither operand of `zero + z`, which keeps the `fadds` (nested ifs with literals fold 0 + z).
#define ESP_SPRITE_SCREEN(esp) ((s8) (esp)->m_Parts_no >= -8 && (s8) (esp)->m_Parts_no <= -3)
#define ESP_SPRITE_FLIP_T(esp)                                                                    \
    ((ESP_SPRITE_SCREEN(esp) && !((esp)->m_Tool_flg & 4)) || (!ESP_SPRITE_SCREEN(esp) && ((esp)->m_Tool_flg & 4)))
#define ESP_SPRITE_CORNERS(esp, zero, z, s0, s1, t0, t1)                                          \
    if ((esp)->m_Tool_flg & 2) {                                                                  \
        if (ESP_SPRITE_FLIP_T(esp)) {                                                             \
            s0 = zero + z;                                                                        \
            s1 = zero;                                                                            \
            t0 = s0;                                                                              \
            t1 = s1;                                                                              \
        } else {                                                                                  \
            s0 = zero + z;                                                                        \
            t0 = zero;                                                                            \
            s1 = zero;                                                                            \
            t1 = s0;                                                                              \
        }                                                                                         \
    } else {                                                                                      \
        if (ESP_SPRITE_FLIP_T(esp)) {                                                             \
            s0 = zero;                                                                            \
            s1 = s0 + z;                                                                          \
            t1 = s0;                                                                              \
            t0 = s1;                                                                              \
        } else {                                                                                  \
            s0 = zero;                                                                            \
            s1 = s0 + z;                                                                          \
            t0 = s0;                                                                              \
            t1 = s1;                                                                              \
        }                                                                                         \
    }

// game/emdata.cpp: swap enemy module `id`'s effect data in / out around a room event.
void EspEmDataSwapPush(int id);
void EspEmDataSwapPop(int id);
// game/eff_sys.cpp: registers a scroll model's texture palette for the room's effect models.
void RoomEfmRegist(cModel* m, u8 no);
// game/eff_sys.cpp: releases the effect data of owner `id` (C linkage).
extern "C" int EspDataRelease(u32 owner, int flag, int warn);
// Debug tools (tools.cpp ToolArrayPush/ToolWorkPop): swap the esp work pool for a Debug_alloc'd one of
// `num` works and back; 1 when done, 0 when a pool is already pushed / none is.
extern "C" int EspArrayPush(u32 num);
extern "C" int EspArrayPop();

#endif

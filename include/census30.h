// CENSUS30 (census30.mk; lane perf30-census 2026-11-10; diagnostic, measurement builds only, log only): per-tick counts
// that size the 30 fps plan's Phase 1 items (PERF-PLAN-30FPS-20261110.md): effects live / moved versus drawn and the
// draw cut that stopped each one, and skeleton world passes / pose / IK / cloth per actor, split by whether the tick's
// picture was drawn or dropped by the pacer. Hooks only count; no game state is read back.
// Included at the end of include/types.h. The hooks sit on existing source lines (no line is added to a game file, so
// __LINE__ and #line numbering are unchanged); with the knob off every C30_* macro is ((void) 0) or its argument.
#ifndef RE4DC_CENSUS30_H
#define RE4DC_CENSUS30_H
#if !defined(__ASSEMBLER__)
#if defined(RE4DC_CENSUS30) && RE4DC_CENSUS30
#ifdef __cplusplus
extern "C" {
#endif
void re4dc_c30_tick_open(void);          // main.cpp, before TaskScheduler: closes the previous tick
void re4dc_c30_decided(int drop);        // main.cpp, after re4dc_pace_decide_image: this tick's picture dropped?
void re4dc_c30_render(void);             // main.cpp, after re4dc_pace_begin: the next iteration's Render() (phase N)
void re4dc_c30_em(void* em);             // em.cpp emMove: the enemy whose move() runs (0 after)
void re4dc_c30_pwc(void* m, void* ra);   // model.cpp cModel::partsWorldCalc
void re4dc_c30_motion(void* m);          // motion.cpp MotionMove
void re4dc_c30_ik(void* m);              // motion.cpp InverseKinematics call
void re4dc_c30_pen(void* m);             // pendulum.cpp PenClothMove / 2 / 3 (attempt)
void re4dc_c30_penskip(void* m);         // pendulum.cpp PEN_CLOTH_LOD skip
void re4dc_c30_cloth(void* c);           // cloth.cpp Cloth::move
void re4dc_c30_ptr(void* ra);            // model.cpp cModel::getPartsPtr(no >= 0)
void re4dc_c30_esp_live(const void* esp, int moved);   // esp.cpp EspMove: a live slot after the model check
void re4dc_c30_esp_mark(const void* esp, unsigned bit);
void re4dc_c30_esp_cur(const void* esp);              // esp_sub.cpp EspSpriteEmit: the sprite being emitted
void re4dc_c30_cut(unsigned bit);                    // native_ui.cpp: a cut of the current sprite
void re4dc_c30_trim(const void* esp, int why, int drawn);   // esp_sub.cpp FxLevelSprite
extern int re4dc_pace_drop_models;                   // pace.cpp
#ifdef __cplusplus
}
#endif
#endif
// effect slot bits (one tick)
#define C30_LIVE 0x0001u
#define C30_MOVED 0x0002u
#define C30_QUEUED 0x0004u    // EspTrans queued it (full pass)
#define C30_TCAP 0x0008u      // ESP_TYPE_CAP: not queued
#define C30_CUSTOM 0x0010u    // queued with a trans other than EspCommonTrans
#define C30_TRANS 0x0020u     // EspCommonTrans entered
#define C30_HAZE 0x0040u      // HAZE_SPRITE_CUT (early or at the emit)
#define C30_ESS 0x0080u       // FX_LEVEL=3 Essential (setup, sprite or strip)
#define C30_TRIM 0x0100u      // FX_TRIM thin / far / small / budget
#define C30_LEVEL 0x0200u     // FX_LEVEL base (depth cap / room budget)
#define C30_NONE 0x0400u      // FX_PS2_NONE_CUT
#define C30_EMIT 0x0800u      // EspSpriteEmit entered
#define C30_DRAWN 0x1000u     // a sprite or strip published
#define C30_LOGICQ 0x2000u    // queued by a logic-only (dropped picture) EspTrans pass
#define C30_STRIP 0x4000u     // FX_STRIP21 strip entered
#if defined(RE4DC_CENSUS30) && RE4DC_CENSUS30
#define C30_TICK_OPEN() re4dc_c30_tick_open()
#define C30_DECIDED() re4dc_c30_decided(re4dc_pace_drop_models)
#define C30_RENDER() re4dc_c30_render()
#define C30_EM(e) re4dc_c30_em((void*) (e))
#define C30_PWC(m) re4dc_c30_pwc((void*) (m), __builtin_return_address(0))
#define C30_PTR() re4dc_c30_ptr(__builtin_return_address(0))
#define C30_MOTION(m) re4dc_c30_motion((void*) (m))
#define C30_IK(m) re4dc_c30_ik((void*) (m))
#define C30_PEN(m) re4dc_c30_pen((void*) (m))
#define C30_PENSKIP(m) re4dc_c30_penskip((void*) (m))
#define C30_CLOTH(c) re4dc_c30_cloth((void*) (c))
#define C30_ESP_LIVE(e, mv) re4dc_c30_esp_live((e), (mv))
#define C30_ESP_MARK(e, b) re4dc_c30_esp_mark((e), (b))
#define C30_TRIMWHY(e, why, drawn) re4dc_c30_trim((e), (why), (drawn))
#ifdef __cplusplus
// a NativeDrawResult passes through; the slot is marked (emit / strip, published, a policy skip of a strip = Essential)
template <class R> inline R c30_emit_result(const void* e, R r)
{
    re4dc_c30_esp_mark(e, C30_EMIT | (r.published() ? C30_DRAWN : 0u));
    re4dc_c30_esp_cur(0);
    return r;
}
template <class R> inline R c30_strip_result(const void* e, R r)
{
    re4dc_c30_esp_mark(e, C30_STRIP | (r.published() ? C30_DRAWN : 0u) | ((unsigned) r.outcome == 3u ? C30_ESS : 0u));
    return r;
}
#define C30_EMITR(e, x) c30_emit_result((e), (re4dc_c30_esp_cur(e), (x)))
#define C30_STRIPR(e, x) c30_strip_result((e), (x))
#endif
#else
#define C30_TICK_OPEN() ((void) 0)
#define C30_DECIDED() ((void) 0)
#define C30_RENDER() ((void) 0)
#define C30_EM(e) ((void) 0)
#define C30_PWC(m) ((void) 0)
#define C30_PTR() ((void) 0)
#define C30_MOTION(m) ((void) 0)
#define C30_IK(m) ((void) 0)
#define C30_PEN(m) ((void) 0)
#define C30_PENSKIP(m) ((void) 0)
#define C30_CLOTH(c) ((void) 0)
#define C30_ESP_LIVE(e, mv) ((void) 0)
#define C30_ESP_MARK(e, b) ((void) 0)
#define C30_TRIMWHY(e, why, drawn) ((void) 0)
#define C30_EMITR(e, x) (x)
#define C30_STRIPR(e, x) (x)
#endif
#endif
#endif

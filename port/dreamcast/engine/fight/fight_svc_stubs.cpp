// fight_svc_stubs.cpp (lane eng-e2d, item 3): logged stubs for the fight image's remaining service functions that the
// village fight does not reach, each counted (core/globals.cpp e1_stub_hit: "E1 STUBCOUNT <name> calls=<n>" at the end
// of a run). The hosted bodies are made weak (game/fight.mk WEAKEN_game/*), so these are linked and --gc-sections drops
// the originals. A stub that is ever called in a fight scene is a gap: its count must be 0 there (the Flycast function
// check's counters, docs/engine/lanes/eng-e2d.md).
//
//   - the binocular's ID widget and the focus blur (cam_extra: IdBinocular, IDApplication, FocusAnimation): drawing (an
//     ID screen and a screen filter), reached only through the binocular and scope cameras;
//   - the save file's storage (game: cGameSave load, save, address and offset fix-ups), reached only by a continue or a
//     save point (no save service yet);
//   - sce_com's debug print SceDebugDisp and debug trigger DebugTrg are reached in the fight (Flycast B1: 1,480 and 862
//     calls): they are the engine's bodies, not stubs: no debug text (the cursor still advances) and no trigger (0, the
//     original's answer when the warp rig is not built), counted.
#include "types.h"
#include "game.h"
#include "sce.h"
#include "sce_sys.h"
#include "e1_engine.h"

// ---- cam_extra: the binocular's widget and the focus blur ----
// Under their assembler names, without the class header: defining the widget's members here would emit its vtable and
// the header's inline members in this object too (the vtable stays cam_extra's, and reaches these by name). The header
// inlines IDApplication::init and IdBinocular's destructors are taken from here the same way.
#define ENG_STUB_FN(sym, fn, label) \
    extern "C" void fn(void*, int, void*, void*) asm(sym); \
    extern "C" void fn(void*, int, void*, void*) { e1_stub_hit(label, 0); }
ENG_STUB_FN("__ZN11IdBinocular4initEP6CameraPvS2_", eng_idbino_init, "IdBinocular::init")
ENG_STUB_FN("__ZN11IdBinocular4moveEPv", eng_idbino_move, "IdBinocular::move")
ENG_STUB_FN("__ZN11IdBinocular4quitEPv", eng_idbino_quit, "IdBinocular::quit")
ENG_STUB_FN("__ZN14FocusAnimation4initEi", eng_focus_init, "FocusAnimation::init")
ENG_STUB_FN("__ZN14FocusAnimation4moveEi", eng_focus_move, "FocusAnimation::move")
ENG_STUB_FN("__ZN14FocusAnimation4quitEv", eng_focus_quit, "FocusAnimation::quit")
ENG_STUB_FN("__ZN13IDApplication4initEPv", eng_idapp_init, "IDApplication::init")
ENG_STUB_FN("__ZN11IdBinocularD0Ev", eng_idbino_d0, "IdBinocular::~IdBinocular (deleting)")
ENG_STUB_FN("__ZN11IdBinocularD1Ev", eng_idbino_d1, "IdBinocular::~IdBinocular")
ENG_STUB_FN("__ZN11IdBinocularD2Ev", eng_idbino_d2, "IdBinocular::~IdBinocular (base)")
// Lane eng-e2f item 4: cam_extra is built without inlining in this image (game/fight.mk), so the widget's in-class members
// that GCC had inlined into CameraBinocular's constructor and destructor (split problems) are functions of their own: the
// widget's, taken from here the same way. The two constructors set the record's table pointer as the implicit ones do
// (the base's, then the widget's: the vtables stay cam_extra's, reached by name); the rest have empty bodies, as the
// header's. Counted: the binocular camera is not reached in the fight (0 calls).
extern "C" void* eng_vt_idbino[] asm("__ZTV11IdBinocular");
extern "C" void* eng_vt_idapp[] asm("__ZTV13IDApplication");
#define ENG_CTOR_FN(sym, fn, vt, label) \
    extern "C" void fn(void*) asm(sym); \
    extern "C" void fn(void* self) { e1_stub_hit(label, 0); *(void***) self = vt + 2; }
ENG_CTOR_FN("__ZN11IdBinocularC1Ev", eng_idbino_c1, eng_vt_idbino, "IdBinocular::IdBinocular")
ENG_CTOR_FN("__ZN11IdBinocularC2Ev", eng_idbino_c2, eng_vt_idbino, "IdBinocular::IdBinocular (base)")
ENG_CTOR_FN("__ZN13IDApplicationC1Ev", eng_idapp_c1, eng_vt_idapp, "IDApplication::IDApplication")
ENG_CTOR_FN("__ZN13IDApplicationC2Ev", eng_idapp_c2, eng_vt_idapp, "IDApplication::IDApplication (base)")
ENG_STUB_FN("__ZN13IDApplicationD0Ev", eng_idapp_d0, "IDApplication::~IDApplication (deleting)")
ENG_STUB_FN("__ZN13IDApplicationD1Ev", eng_idapp_d1, "IDApplication::~IDApplication")
ENG_STUB_FN("__ZN13IDApplicationD2Ev", eng_idapp_d2, "IDApplication::~IDApplication (base)")
ENG_STUB_FN("__ZN13IDApplication4moveEPv", eng_idapp_move, "IDApplication::move")
ENG_STUB_FN("__ZN13IDApplication4quitEPv", eng_idapp_quit, "IDApplication::quit")
ENG_STUB_FN("__ZN13IDApplicationdlEPvj", eng_idapp_delete, "IDApplication::operator delete")

// ---- game: the save file's storage ----
int cGameSave::load(void*) { e1_stub_hit("cGameSave::load", 0); return 0; }
void cGameSave::checkAddr(GameSaveData*) { e1_stub_hit("cGameSave::checkAddr", 0); }
void cGameSave::calcOffset(GameSaveData*, void*) { e1_stub_hit("cGameSave::calcOffset", 0); }
void cGameSave::calcAddr(GameSaveData*) { e1_stub_hit("cGameSave::calcAddr", 0); }
int GameSaveSave(cGameSave*, void*, int mode) { e1_stub_hit("cGameSave::save", mode); return 0; }

// ---- sce_com: the debug print and the debug trigger ----
// The engine's: no debug text is drawn; the text cursor advances as the original's does (the fight reaches it every
// tick through sce_at's debug display: Flycast B1, 1,480 calls), so nothing that reads it sees a difference.
void SceDebugDisp(const char*, ...)
{
    e1_stub_hit("SceDebugDisp", 0);
    SceSys.m_debug_disp_y += 0xF;
}
int DebugTrg(int no)
{
    e1_stub_hit("DebugTrg", no);
    return 0;
}

// sce_at_weak.h (lane eng-e2f): force-included into the hosted sce_at.cpp (game/fight.mk; the PC check's copy,
// hostref svc/svc.mk), as lane eng-e2c's r119_weak.h does for r119's statics (integrator ruling, 2026-11-21).
//
// sce_at's scene attachment system keeps its state in file statics: the system record (SceAtSys, 0x124 bytes) and the
// pointer the decisions read it through (pS), and its shadow area handler is a static function reached only through
// the handler table (sceAtFunc_tbl). The engine's room set-up (services/scene/sce_at_svc.cpp SceAtInit: the room's
// attachment data validated and linked into the at-list) must point pS at the record, and the engine's shadow handler
// must take the table's entry. Declared weak here, before the file, the assembler makes each a weak global symbol and
// every reference to it a reference to the symbol: the engine's objects reach the same record by name, and the
// engine's strong handler replaces the original's (--gc-sections drops it). No source is edited and no code changes:
// only the symbols' binding. tools/engine/split_check.py --sceat checks the object (weak, referenced by symbol only).
#pragma once
#define SCEATW_STR2(x) #x
#define SCEATW_STR(x) SCEATW_STR2(x)
#define SCEATW_SYM(name) SCEATW_STR(__USER_LABEL_PREFIX__) #name
asm(".weak " SCEATW_SYM(_ZL2pS) "\n\t.weak " SCEATW_SYM(_ZL8SceAtSys) "\n\t.weak " SCEATW_SYM(sceAtFunc_shd_disp));

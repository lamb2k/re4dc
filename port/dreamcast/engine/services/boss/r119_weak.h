// r119_weak.h (lane eng-e2c; integrator ruling on the thunder, 2026-11-21): force-included into the hosted r119.cpp
// (game/boss.mk; the PC reference's exercise copy, hostref svc/svc.mk). r119.cpp's three thunder functions are `static`
// and its R119Init names the task by its section, so an engine body could not take their place by symbol. Declared weak
// here, before the file, the assembler keeps them as weak global symbols and every reference to them (R119Init's task,
// the task's two callbacks) as a reference to the symbol: services/boss/r119_thunder.cpp's strong bodies are linked and
// --gc-sections drops the original's. No source is edited and no code changes: only the symbols' binding.
// game/r119_split_check.py checks the hosted object (weak, referenced by symbol only, no copy inlined elsewhere).
#pragma once
#define R119W_STR2(x) #x
#define R119W_STR(x) R119W_STR2(x)
#define R119W_SYM(name) R119W_STR(__USER_LABEL_PREFIX__) #name
asm(".weak " R119W_SYM(_ZL16r119_ThunderMovev) "\n\t.weak " R119W_SYM(_ZL18r119_ThunderFlagOnv) "\n\t.weak "
    R119W_SYM(_ZL19r119_ThunderFlagOffv));

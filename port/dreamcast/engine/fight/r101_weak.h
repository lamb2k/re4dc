// r101_weak.h (lane eng-e2f): force-included into the hosted st1/r101.cpp (game/fight.mk), as lane eng-e2c's
// r119_weak.h does for r119's thunder. r101.cpp's Ganado voice task (r101_callGanadoVoice) is `static` and the room
// script hands it to the scenario by address (SceAtDataSet_exec), so an engine body could not take its place by symbol.
// Declared weak here, before the file, the assembler keeps it as a weak global symbol and every reference to it as a
// reference to the symbol: fight/r101_voice.cpp's strong body is linked and --gc-sections drops the original's. No
// source is edited and no code changes: only the symbol's binding. tools/engine/split_check.py checks the object.
#pragma once
#define R101W_STR2(x) #x
#define R101W_STR(x) R101W_STR2(x)
#define R101W_SYM(name) R101W_STR(__USER_LABEL_PREFIX__) #name
asm(".weak " R101W_SYM(_ZL20r101_callGanadoVoicev));

#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
extern "C" void re4dc_gcasset_room_enter(unsigned room);
extern "C" void re4dc_gcasset_finish();
extern "C" unsigned re4dc_gcasset_audio_admission(unsigned open);
#endif

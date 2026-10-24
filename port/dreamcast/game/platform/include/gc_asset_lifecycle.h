#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
extern "C" void re4dc_gcasset_room_enter(unsigned room);
extern "C" void re4dc_gcasset_retire();
extern "C" void re4dc_gcasset_finish();
extern "C" unsigned re4dc_gcasset_audio_quiesce(unsigned* checkpoints);
extern "C" unsigned re4dc_gcasset_os_frame_boundary();
extern "C" unsigned re4dc_gcasset_os_quiesce(unsigned* blocked);
extern "C" unsigned re4dc_gcasset_audio_admission(unsigned open);
extern "C" unsigned re4dc_gcasset_audio_handoff(unsigned room,unsigned visit);
#endif

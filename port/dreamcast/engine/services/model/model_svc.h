// Native model service (lane eng-svc4; model_svc.cpp, docs/engine/SERVICES.md section 27): the model record's set-up
// (cModel's constructor, modelInit, the joint set-up), its chain of model data (cModelInfo: one per .bin + TPL), the
// two pools under them (PartsMgr: one cParts per joint, taken as a contiguous run when one is free; ModInfoMgr), the
// relocation of model and texture files from offsets to pointers, and the bounding boxes. The pose itself (parts
// matrices, world, history, parenting) is the skeleton service's (services/skeleton/skel.cpp). Engine bodies for the
// entry points of the original unit model.cpp; the behaviour keeps calling them by their names.
#pragma once
#include "types.h"

struct ModelCounters {
    u32 inits;          // modelInit calls that made a model
    u32 infos;          // model infos created (ModInfoMgr)
    u32 parts_runs;     // parts lists taken as one contiguous run (be_flag 0x2000)
    u32 parts_single;   // parts lists taken one part at a time (no run free)
    u32 parts_made;     // parts created
    u32 relocs;         // model or texture files relocated from offsets to pointers
    u32 debug_draws;    // debug skeletons and bounding boxes (counted, not drawn)
};

extern "C" {
extern ModelCounters model_cnt;
// Control (re4ref, RE4_SVC_CONTROL): 1 "modelslot": a contiguous parts run starts one slot later than the first free
// one (a wrong slot search).
extern int model_control;
}

// Original service units that have no native service yet and are not linked (lane eng-e1c, owner 2026-11-19: no
// original service code stays in the engine image): logged stubs, each counted in the stub report.
//   - facial shape keys (game/shape.cpp ShapeSet / ShapeMove / ShapeEnd): the engine renderer draws no shape keys.
//   - cloth: lane eng-e1d links the native cloth service (services/cloth, game/hosted.mk). What stays a stub is its
//     fallback for a chain it cannot resolve (pen_orig_*: the original bodies, not linked; never reached by Leon's or
//     Ashley's chains); the wind globals are engine data (pendulum.cpp is not linked). In the boss image (BOSS=1) the
//     whole cloth stays stubbed as before (El Gigante's loincloth and ropes).
#include "e1_engine.h"
#include "model.h"
#include "pl_cloth.h"
#include "pendulum.h"

void ShapeSet(void*, int a, void*, int) { e1_stub_hit("ShapeSet (shape keys: not drawn)", a); }
void ShapeEnd(void*) { e1_stub_hit("ShapeEnd (shape keys: not drawn)", 0); }
extern "C" int ShapeMove(cModelInfo*) { e1_stub_hit("ShapeMove (shape keys: not drawn)", 0); return 0; }

#ifndef E2_BOSS
// The cloth's wind (pendulum.cpp's globals, set per room by light.cpp's PenWindSet, which is not hosted): engine data at
// the original's start values (20 units along +z, phase step pi / 3).
Vec GlobalWind = {0.0f, 0.0f, 20.0f};
f32 GlobalWindAdd = 1.0471976f;
// The native cloth's fallback (services/cloth/cloth.cpp): a chain the service cannot resolve keeps its animated pose.
extern "C" void pen_orig_Set(cModel*, PenCloth*, f32) { e1_stub_hit("pen_orig_Set (cloth chain not resolved: no swing)", 0); }
extern "C" void pen_orig_Move(cModel*, PenCloth*) { e1_stub_hit("pen_orig_Move (cloth chain not resolved)", 0); }
extern "C" void pen_orig_Move3(cModel*, PenCloth*) { e1_stub_hit("pen_orig_Move3 (cloth chain not resolved)", 0); }
extern "C" void pen_orig_FixSet(cModel*, PenCloth*, int no, Vec*) { e1_stub_hit("pen_orig_FixSet (cloth chain not resolved)", no); }
extern "C" void pen_orig_FixClear(cModel*, PenCloth*, int no) { e1_stub_hit("pen_orig_FixClear (cloth chain not resolved)", no); }
#else
// Boss image: no cloth service linked (lane eng-e1c's stubs). The cloth bones keep their animated pose; a move keeps the
// cloth's one effect on the actor's state, clearing the chains' reset / warp request bits (be_flag 0x00E00000).
PlCloth leonHair, leonJacket, leonHolster, girlHair, girlSkirt, girlSweater;
void PlClothSetLeon(cModel*, PlCloth*, PlCloth*, PlCloth*) { e1_stub_hit("PlClothSetLeon (cloth: no native service)", 0); }
void PlClothMoveLeon(cModel* pl, PlCloth*, PlCloth*, PlCloth*) { e1_stub_hit("PlClothMoveLeon (cloth: no native service)", 0); pl->be_flag &= ~0x00E00000; }
void PlClothSetGirl(cModel*, PlCloth*, PlCloth*, PlCloth*, int e) { e1_stub_hit("PlClothSetGirl (cloth: no native service)", e); }
void PlClothMoveGirl(cModel* pl, PlCloth*, PlCloth*, PlCloth*) { e1_stub_hit("PlClothMoveGirl (cloth: no native service)", 0); pl->be_flag &= ~0x00E00000; }
// El Gigante's loincloth and ropes (em2b): the cloth bones keep their animated pose.
void PenClothSet(cModel*, PenCloth*, f32) { e1_stub_hit("PenClothSet (cloth: no native service)", 0); }
void PenClothMove(cModel*, PenCloth*) { e1_stub_hit("PenClothMove (cloth: no native service)", 0); }
void PenClothMove3(cModel*, PenCloth*) { e1_stub_hit("PenClothMove3 (cloth: no native service)", 0); }
#endif

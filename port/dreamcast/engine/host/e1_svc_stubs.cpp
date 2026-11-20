// Original service units that have no native service yet and are no longer linked (lane eng-e1c, owner 2026-11-19:
// no original service code stays in the engine image): logged stubs, each counted in the stub report.
//   - cloth (game/pl_cloth.cpp and game/pendulum.cpp: Leon's hair, jacket and holster, Ashley's hair, skirt and
//     sweater): the cloth bones keep the pose the skeleton service gives them (animated, no swing). Presentation only:
//     no behaviour reads the cloth bones (SERVICES.md section 4 census); its generator draws (wind) are gone with it.
//   - facial shape keys (game/shape.cpp ShapeSet / ShapeMove / ShapeEnd): the engine renderer draws no shape keys.
// A native cloth service is the replacement (not built).
#include "e1_engine.h"
#include "model.h"
#include "pl_cloth.h"

PlCloth leonHair, leonJacket, leonHolster, girlHair, girlSkirt, girlSweater;

void PlClothSetLeon(cModel*, PlCloth*, PlCloth*, PlCloth*) { e1_stub_hit("PlClothSetLeon (cloth: no native service)", 0); }
// The cloth's one effect on the actor's state is kept: a move clears the chains' reset / warp request bits
// (be_flag 0x00E00000, pl_cloth.cpp), which the behaviour sets and the move consumes.
void PlClothMoveLeon(cModel* pl, PlCloth*, PlCloth*, PlCloth*) { e1_stub_hit("PlClothMoveLeon (cloth: no native service)", 0); pl->be_flag &= ~0x00E00000; }
void PlClothSetGirl(cModel*, PlCloth*, PlCloth*, PlCloth*, int e) { e1_stub_hit("PlClothSetGirl (cloth: no native service)", e); }
void PlClothMoveGirl(cModel* pl, PlCloth*, PlCloth*, PlCloth*) { e1_stub_hit("PlClothMoveGirl (cloth: no native service)", 0); pl->be_flag &= ~0x00E00000; }
void ShapeSet(void*, int a, void*, int) { e1_stub_hit("ShapeSet (shape keys: not drawn)", a); }
void ShapeEnd(void*) { e1_stub_hit("ShapeEnd (shape keys: not drawn)", 0); }
extern "C" int ShapeMove(cModelInfo*) { e1_stub_hit("ShapeMove (shape keys: not drawn)", 0); return 0; }
// The pendulum cloth of other models (El Gigante's loincloth and ropes, em2b): no native service; the cloth bones
// keep their animated pose (PenClothSet's skip-blend bits are not set, so the skeleton blends them as other bones).
#include "pendulum.h"
void PenClothSet(cModel*, PenCloth*, f32) { e1_stub_hit("PenClothSet (cloth: no native service)", 0); }
void PenClothMove(cModel*, PenCloth*) { e1_stub_hit("PenClothMove (cloth: no native service)", 0); }
void PenClothMove3(cModel*, PenCloth*) { e1_stub_hit("PenClothMove3 (cloth: no native service)", 0); }

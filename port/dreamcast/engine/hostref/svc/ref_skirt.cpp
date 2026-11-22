// ref_skirt.cpp (lane eng-cloth2): the PC reference's skirt at two constraint passes, as the engine runs it.
//
// A reference change (HANDOVERS.md H-017.8: kept switchable, run as a refctl.sh row). Cause: the owner's look choice
// of 2026-11-22 ("Ok option B", H-032): Ashley's skirt runs two constraint passes where the original runs four. In the
// original source the passes are PenCloth::Bundle_num, set to 4 for the skirt by pl_cloth.cpp's girl set-up (as for
// every garment but Ada's dress) and read by pendulum.cpp's PenClothMove / PenClothMove3 constraint loops
// (`for (k = 0; k < c->Bundle_num; k++)`); the engine's cloth (services/cloth/cloth.cpp) clamps the skirt's to
// CLOTH_SKIRT_PASSES. The odump build (svc/svc.mk, SKIRT_PASSES=2, the default) links with
// --wrap=PenClothMove --wrap=PenClothMove3: every call from the behaviour reaches these wrappers, which give the skirt
// (CLOTH_IS_SKIRT, the engine's own test) two passes for the call and restore the field after it, so the behaviour's
// memory is what it was. Every other chain is passed through untouched. SKIRT_PASSES=4 is the old reference (no wrap),
// a control build only. src/ is not edited.
#include "pendulum.h"
#include "../../services/cloth/cloth.h"   // CLOTH_IS_SKIRT, CLOTH_SKIRT_PASSES (the game's include/ has a cloth.h too)

extern "C" {
void __real_PenClothMove(cModel* m, PenCloth* c);
void __real_PenClothMove3(cModel* m, PenCloth* c);
unsigned ref_skirt_calls;   // calls that ran the skirt at two passes (svc_dump's counters may read it)

static inline u32 skirt_begin(PenCloth* c)
{
    const u32 had = c->Bundle_num;
    if (CLOTH_IS_SKIRT(c) && had > CLOTH_SKIRT_PASSES) {
        c->Bundle_num = CLOTH_SKIRT_PASSES;
        ref_skirt_calls++;
    }
    return had;
}

void __wrap_PenClothMove(cModel* m, PenCloth* c)
{
    const u32 had = skirt_begin(c);
    __real_PenClothMove(m, c);
    c->Bundle_num = had;
}

void __wrap_PenClothMove3(cModel* m, PenCloth* c)
{
    const u32 had = skirt_begin(c);
    __real_PenClothMove3(m, c);
    c->Bundle_num = had;
}
}

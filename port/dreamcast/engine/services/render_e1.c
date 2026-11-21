/* E1 renderer translation unit (lane eng-e1): the E0 renderer (render/render.c, unchanged and shared with the bench)
   plus the E1 actor pass, which draws characters from the engine actor table in place (cModel->mat and the cParts
   chain world matrices written once by the skeleton service). Kept in this new file so the shared render files are
   not edited (lane eng-look works there). */
#include "light_view.h"   /* lane eng-e1j: characters lit from their model records in place (render/source_light.inc) */
#include "../render/render.c"
#include "actor_e1.inc"
#ifdef E2_FIGHT
#include "fight_draw.inc"   /* lane eng-e2: the fight's Ganados and native effect sprites */
#endif

// svc5_dump.cpp (game side; lane eng-svc5): the round-5 native services' controls, exercises and counters in re4ref,
// linked into odump (the original units) and native (the engine bodies) alike. RE4_SVC_CONTROL names a control (each
// must make the comparison with the reference fail; svc_controls.sh); RE4_SVC_EXERCISE=costume plants calls; RE4_SVC_OUT
// =<dir> receives svc5.txt, the native counters (absent in the reference). The equivalence itself is judged on the
// bones, queries, the round-4 boundary log and the traces (svc_controls.sh), which every round-5 service lies under.
#include "hostref.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "pl_cloth.h"
#include "../../services/math/math_svc.h"
#include "../../services/cloth/garment.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
extern MathCounters math_cnt __attribute__((weak));
extern int math_control __attribute__((weak));
extern GarmentCounters garment_cnt __attribute__((weak));
extern int garment_control __attribute__((weak));
}

namespace {
void* g_f;
int g_exercise = -1;
const char* g_note = "";
bool is(const char* c, const char* name) { return c && !__builtin_strcmp(c, name); }

// Exercise "costume": the garments of the other costumes, which no fixture wears. At the start of tick 1 Leon changes to
// costume 1 (the holster strap instead of the jacket) and his garments are set again; Ashley, when her model has the
// alternate costume's parts (the ribbon's 144-155, the lapels' 0x8D, 0x8E), changes to costume 1 (ribbon and lapels).
// Both builds get the same calls; the comparison stays original against native on the same inputs.
void exercise_costume(unsigned t)
{
    if (t != 1) return;
    if (pPL) {
        pG->pl_costume = 1;
        PlClothSetLeon(pPL, &leonHair, &leonJacket, &leonHolster);
    }
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == pPL || e->id != 3) continue;
        if (e->nParts <= 155) {
            g_note = "ashley: model has too few parts for the alternate costume";
            host_log("exercise costume: Ashley's model has %u parts (the alternate costume needs 156): not changed", e->nParts);
            continue;
        }
        pG->game_costume = 1;
        PlClothSetGirl(e, &girlHair, &girlSkirt, &girlSweater, 0);
        g_note = "ashley: costume 1";
    }
}
}   // namespace

extern "C" void svc5_ready()
{
    const char* c = svc_env("RE4_SVC_CONTROL");
    if (&math_control) {
        if (is(c, "mathsin")) math_control = 1;
        if (is(c, "mathmuku")) math_control = 2;
    }
    if (&garment_control) {
        if (is(c, "garmenthair")) garment_control = 1;
        if (is(c, "garmentskirt")) garment_control = 2;
        if (is(c, "lapelrate")) garment_control = 3;
    }
    const char* e = svc_env("RE4_SVC_EXERCISE");
    g_exercise = is(e, "costume") ? 1 : 0;
    g_f = svc_out_open("svc5.txt", "w");
}

extern "C" void svc5_tick(unsigned t, int begin)
{
    if (begin && g_exercise == 1) exercise_costume(t);
}

extern "C" void svc5_finish()
{
    if (!g_f) return;
    if (&math_cnt)
        svc_out_printf(g_f, "# math: scratch_stack %u scratch_heap %u normalize_zero %u series %u control %d\n",
                       math_cnt.scratch_stack, math_cnt.scratch_heap, math_cnt.normalize_zero, math_cnt.series,
                       &math_control ? math_control : -1);
    if (&garment_cnt)
        svc_out_printf(g_f, "# garment: sets %u moves %u lapels %u skipped %u control %d\n", garment_cnt.sets, garment_cnt.moves,
                       garment_cnt.lapels, garment_cnt.skipped, &garment_control ? garment_control : -1);
    svc_out_printf(g_f, "# exercise: %d %s; costumes pl %d game %d\n", g_exercise, g_note, pG ? pG->pl_costume : -1,
                   pG ? pG->game_costume : -1);
    svc_out_close(g_f);
    g_f = 0;
}

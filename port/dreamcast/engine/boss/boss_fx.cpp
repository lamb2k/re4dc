// E2 boss slice (lane eng-boss): the engine effect service the hosted boss and room script call, first form.
//
// The hosted code asks for effects through the original entry points (EspDataLoad, EstSet, EspPullCoreKind,
// QuakeExec, the delete calls ...). The engine records each request as an event in its own table (tick, kind, the
// caller's arguments) and keeps the live sets the hosted code can query; it does not simulate or draw them yet (the
// bench draws the captured effects). Events are counted and printed with the report, so a plays-right check can compare
// the boss's effect requests with the reference's. Generator draws the original effect code makes are NOT made here:
// the hosted boss therefore sees a different generator stream than in the reference (ENGINE_PLAN shared-generator
// risk), which is why the boss check compares discrete events and positions, not generator state.
#include "global.h"
#include "model.h"
#include "em.h"
#include "esp.h"
#include "est.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "boss_e2.h"
#include <string.h>
#include <stdio.h>

struct FxEvent { uint16_t tick, kind; uint32_t a, b, c; };
enum { FX_DATA_LOAD = 1, FX_EST_SET, FX_PULL_CORE, FX_QUAKE, FX_TOOL_CB, FX_ESP_DELETE, FX_ESPGEN_DELETE, FX_EFM_DELETE,
       FX_DATA_RELEASE, FX_KINDS };
static const char* const fx_names[FX_KINDS] = {"", "EspDataLoad", "EstSet", "EspPullCoreKind", "QuakeExec",
    "EffSetToolStateCallBack", "EffectEspDelete", "EffectEspgenDelete", "EffectEfmDelete", "EspDataRelease"};
#define FX_EVENTS 2048
static FxEvent fx_events[FX_EVENTS];
static unsigned fx_n, fx_count[FX_KINDS];
static void fx(unsigned kind, uint32_t a, uint32_t b, uint32_t c)
{
    fx_count[kind]++;
    if (fx_n < FX_EVENTS) fx_events[fx_n++] = {(uint16_t) e1_tick, (uint16_t) kind, a, b, c};
}

int EspDataLoad(u32 data, u32 owner, int mode) { fx(FX_DATA_LOAD, data, owner, mode); return 0; }
extern "C" int EspDataRelease(u32 owner, int a, int b) { fx(FX_DATA_RELEASE, owner, a, b); return 0; }
extern "C" void EstSet(int a, int b, Vec*, Vec*, int c, int d, int, int, u32 owner, void*) { fx(FX_EST_SET, a << 16 | (b & 0xFFFF), c << 16 | (d & 0xFFFF), owner); }
void EffectEspDelete(int a, int b, u32 c, cModel*) { fx(FX_ESP_DELETE, a, b, c); }
void EffectEspgenDelete(int a, int b, int c) { fx(FX_ESPGEN_DELETE, a, b, c); }
void EffectEfmDelete(int a, int b, int c) { fx(FX_EFM_DELETE, a, b, c); }

void e2_fx_move() {}
void e2_after_tick() {}
void e2_report()
{
    for (unsigned k = 1; k < FX_KINDS; k++) if (fx_count[k]) e1_log("E2 FX %s count=%u\n", fx_names[k], fx_count[k]);
    for (unsigned i = 0; i < fx_n; i++)
        e1_log("E2 FXEV t=%u %s %08lx %08lx %08lx\n", fx_events[i].tick, fx_names[fx_events[i].kind],
               (unsigned long) fx_events[i].a, (unsigned long) fx_events[i].b, (unsigned long) fx_events[i].c);
}

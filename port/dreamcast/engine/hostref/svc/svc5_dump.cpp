// svc5_dump.cpp (game side; lane eng-svc5): the round-5 native services' controls and counters in re4ref, linked into
// odump (the original units) and native (the engine bodies) alike. RE4_SVC_CONTROL names a control (each must make the
// comparison with the reference fail; svc_controls.sh); RE4_SVC_OUT=<dir> receives svc5.txt, the native counters
// (absent in the reference). The equivalence itself is judged on the bones, queries, the round-4 boundary log and the
// traces (svc_controls.sh), which every round-5 service lies under.
#include "hostref.h"
#include "../../services/math/math_svc.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
extern MathCounters math_cnt __attribute__((weak));
extern int math_control __attribute__((weak));
}

namespace {
void* g_f;
bool is(const char* c, const char* name) { return c && !__builtin_strcmp(c, name); }
}

extern "C" void svc5_ready()
{
    const char* c = svc_env("RE4_SVC_CONTROL");
    if (&math_control) {
        if (is(c, "mathsin")) math_control = 1;
        if (is(c, "mathmuku")) math_control = 2;
    }
    g_f = svc_out_open("svc5.txt", "w");
}

extern "C" void svc5_tick(unsigned) {}

extern "C" void svc5_finish()
{
    if (!g_f) return;
    if (&math_cnt)
        svc_out_printf(g_f, "# math: scratch_stack %u scratch_heap %u normalize_zero %u series %u control %d\n",
                       math_cnt.scratch_stack, math_cnt.scratch_heap, math_cnt.normalize_zero, math_cnt.series,
                       &math_control ? math_control : -1);
    svc_out_close(g_f);
    g_f = 0;
}

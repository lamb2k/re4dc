/* libmtest.c (lane eng-svc5): the engine's float math library (the toolchain's newlib 4.6.0 libm: sinf, cosf, tanf,
 * atanf, atan2f, asinf, acosf, sqrtf; its sources compiled for the PC with the reference's flags and every symbol
 * prefixed nl_, svc.mk libmtest) against the game's own fdlibm (src/lib, which re4ref links), bit for bit, on random
 * inputs: angles, large arguments (the Payne-Hanek reduction path), tiny ones, the [-1, 1] domain and outside it,
 * zeros of both signs, infinities and NaNs.
 *
 *   libmtest [count]   LIBMTEST_CONTROL=sinulp: the newlib side's sinf one float step off on 1 input in 64 (must FAIL)
 * Exit 0 PASS, 1 when any output differs (a NaN against a NaN counts as equal; their payloads are listed apart). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

float sinf(float), cosf(float), tanf(float), atanf(float), atan2f(float, float), asinf(float), acosf(float), sqrtf(float);
float nl_sinf(float), nl_cosf(float), nl_tanf(float), nl_atanf(float), nl_atan2f(float, float), nl_asinf(float),
    nl_acosf(float), nl_sqrtf(float);
int nl___errno_dummy;
int* nl___errno(void) { return &nl___errno_dummy; }

static uint32_t seed = 0x1234567u;
static uint32_t rnd(void) { seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed; }
static float bitsf(uint32_t u) { float f; memcpy(&f, &u, 4); return f; }
static uint32_t fbits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static float uni(float lo, float hi) { return lo + (hi - lo) * ((rnd() >> 8) * (1.0f / 16777216.0f)); }
static float val(void)
{
    switch (rnd() % 12) {
    case 0: return bitsf(rnd());                      /* any float, NaN and infinity included */
    case 1: return uni(-1.0f, 1.0f);
    case 2: return uni(-1.2f, 1.2f);
    case 3: return uni(-1e-4f, 1e-4f);
    case 4: return uni(-1e6f, 1e6f);
    case 5: return uni(-1e30f, 1e30f);
    case 6: return (rnd() & 1) ? 0.0f : -0.0f;
    case 7: return (rnd() & 1) ? bitsf(0x7f800000u) : bitsf(0xff800000u);
    case 8: return uni(0.0f, 40000.0f);
    default: return uni(-25.0f, 25.0f);
    }
}
struct row { const char* name; unsigned n, diff, nanpay; char first[128]; };
static struct row rows[8] = {{"sinf"}, {"cosf"}, {"tanf"}, {"atanf"}, {"atan2f"}, {"asinf"}, {"acosf"}, {"sqrtf"}};
static int control;
static void cmp(int i, float x, float y, float a, float b)
{
    struct row* r = &rows[i];
    r->n++;
    if (fbits(a) == fbits(b)) return;
    if (a != a && b != b) { r->nanpay++; return; }
    if (!r->diff++) snprintf(r->first, sizeof r->first, "(%08x, %08x): game %08x newlib %08x", fbits(x), fbits(y), fbits(a), fbits(b));
}
static float ctl(float v) { return control && (rnd() % 64) == 0 ? bitsf(fbits(v) + 1) : v; }

int main(int argc, char** argv)
{
    unsigned N = argc > 1 ? (unsigned) atoi(argv[1]) : 2000000;
    const char* c = getenv("LIBMTEST_CONTROL");
    control = c && !strcmp(c, "sinulp");
    for (unsigned it = 0; it < N; it++) {
        float x = val(), y = val();
        cmp(0, x, 0, sinf(x), ctl(nl_sinf(x)));
        cmp(1, x, 0, cosf(x), nl_cosf(x));
        cmp(2, x, 0, tanf(x), nl_tanf(x));
        cmp(3, x, 0, atanf(x), nl_atanf(x));
        cmp(4, x, y, atan2f(x, y), nl_atan2f(x, y));
        cmp(5, x, 0, asinf(x), nl_asinf(x));
        cmp(6, x, 0, acosf(x), nl_acosf(x));
        cmp(7, x, 0, sqrtf(x), nl_sqrtf(x));
    }
    int bad = 0;
    for (int i = 0; i < 8; i++) {
        printf("%-7s inputs %8u differ %7u (NaN payloads only: %u)%s%s\n", rows[i].name, rows[i].n, rows[i].diff, rows[i].nanpay,
               rows[i].diff ? "  first " : "", rows[i].diff ? rows[i].first : "");
        if (rows[i].diff) bad = 1;
    }
    printf("%s\n", bad ? "FAIL: outputs differ" : "PASS: every output bit-identical");
    return bad;
}

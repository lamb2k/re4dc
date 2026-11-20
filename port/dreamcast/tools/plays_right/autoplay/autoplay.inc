// autoplay.inc (lane eng-ref): the outcome check's closed-loop player, one source for both sides.
//
// The same code runs in the old game's split reference (patched into the warp rig's pad hook by refsplit.py when the
// fixture says `autoplay`) and in the engine image (autoplay_engine.cpp wraps PADRead at link time; nothing in the
// engine's own code changes). Each pad read it:
//   - picks the nearest living Ganado (enemy id 0x15) by ground distance from Leon;
//   - holds R (aim) and turns with the stick toward it, the stick proportional to the yaw error;
//   - fires (A for 2 reads) when the aim has been within 3.4 degrees (0.06 rad) for 3 reads and 12 reads have
//     passed since the last shot (a smaller stick than 40 does not turn the aim: the first try never fired).
// The stick's turn direction is learnt, not assumed: if the error grows for 3 reads while turning, the sign flips.
// It reads only game state both sides share (pPL, EmMgr's alive list); it keeps its own clock (pad reads since Leon
// exists), so it needs no pad script. Deterministic: the same state gives the same pad.

namespace re4ap {
static int n, last_shot = -1000, aimed, sign = 1, grow;
static float prev_err;
static unsigned shots;
}

// own atan2 and abs (no libm: the two builds link different maths; this keeps both sides bit-identical)
static inline float re4ap_abs(float a) { return a < 0 ? -a : a; }
static float re4ap_atan2(float y, float x)
{
    const float ay = re4ap_abs(y) + 1e-10f;
    float r, a;
    if (x >= 0) { r = (x - ay) / (x + ay); a = 0.78539816f; }
    else { r = (x + ay) / (ay - x); a = 2.35619449f; }
    a += (0.1963f * r * r - 0.9817f) * r;
    return y < 0 ? -a : a;
}

static inline float re4ap_wrap(float a)
{
    while (a > 3.14159265f) a -= 6.2831853f;
    while (a < -3.14159265f) a += 6.2831853f;
    return a;
}

// buttons / stick of pad 0, replaced. Returns 1 when it drove the pad.
static int re4ap_pad(unsigned short* buttons, signed char* sx, signed char* sy)
{
    using namespace re4ap;
    if (!pPL) return 0;
    ++n;
    *buttons = 0; *sx = 0; *sy = 0;
    if (n < 20) return 1;
    cEm* best = 0;
    float bd = 1e30f, bdx = 0, bdz = 0;
    for (cUnit* u = (cUnit*) EmMgr.pAlive; u; u = u->pNext) {
        cEm* e = (cEm*) u;
        if (e->id != 0x15 || (short) e->hp <= 0) continue;
        const float dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d = dx * dx + dz * dz;
        if (d < bd) { bd = d; best = e; bdx = dx; bdz = dz; }
    }
    if (!best) { aimed = 0; return 1; }
    const float err = re4ap_wrap(re4ap_atan2(bdx, bdz) - pPL->ang.y);
    *buttons = 0x0020;   // R: aim
    const float ae = re4ap_abs(err);
    if (ae > 0.06f) {
        if (ae > re4ap_abs(prev_err) + 0.002f && n > 21) {
            if (++grow >= 3) { sign = -sign; grow = 0; }
        } else {
            grow = 0;
        }
        int s = (int) (ae * 150.0f);
        if (s < 40) s = 40;
        if (s > 80) s = 80;
        *sx = (signed char) (sign * (err > 0 ? s : -s));
        aimed = 0;
    } else {
        grow = 0;
        ++aimed;
    }
    prev_err = err;
    if (aimed >= 3 && n - last_shot >= 12) { last_shot = n; ++shots; }
    if (n - last_shot < 2) *buttons |= 0x0100;   // A: fire
    return 1;
}

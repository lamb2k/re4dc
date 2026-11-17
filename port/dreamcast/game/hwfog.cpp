// HW_FOG_HAZE (hwfog.mk; lane hwfog 2026-10-14, issue #29): the distant camera haze as PVR table fog.
//
// The room generator's camera haze (Esp15, owner 0xd0; EFFECT_PS2_HAZE draws it with the PS2 recipe) keeps its
// particles in a box in front of the camera. Near the camera the sprites are large drifting blotches (the visible mist,
// kept); deep in the box they only lay an even veil, yet each still costs a full translucent fill (TA-stats: 30-77 % of
// the haze fill of r106 / r107 / r109 / r11b lies beyond 3 m). Those deep sprites are replaced here by the fog table:
// - re4dc_hwfog_haze(room, depth, indoor) is asked by esp_sub.cpp (the effects lane's hook in the EFFECT_PS2_HAZE draw)
//   for each haze sprite it would draw: 1 = skip it (the room has a row and the sprite's view depth is beyond the keep
//   depth). It notes the room, the haze's indoor fade (8 steps) and the FX_LEVEL for the fog table.
// - re4dc_hwfog_key() gives native_static.cpp's re4dc_fog_frame that note (0: no haze room in the last kHold frames);
//   re4dc_hwfog_table() folds the row's veil into the GXSetFog table: the veil in front of a surface at depth z is the
//   replaced sprites' alpha (the recipe's near / far fades) integrated from the keep depth to z (the box has a fixed
//   width, so each depth slab covers the same screen share), x indoor, combined as 1 - (1 - fog)(1 - veil).
// The fog colour stays the room's GXSetFog colour (the PVR has one table fog colour, which is also the background):
// moving it toward the haze colour brightened the whole fogged distance and the sky (r11b +27/255 at a 0.10 veil
// against +1/255 from the sprites it replaced), so rooms whose fog colour is dark (night: r11b, r119) get no veil.
// The table changes only when the row, the indoor step or the level changes (each change fences the TA double buffer).
// Render only: nothing here is read by game logic; generators, their Rnd() draws, the pool and sprite motion are as before.
#include <cstdint>
#ifndef RE4DC_HW_FOG_VEIL_PCT
#define RE4DC_HW_FOG_VEIL_PCT 100   // hwfog.mk HW_FOG_VEIL_PCT (test builds: veil calibration arms)
#endif

extern "C" void re4dc_log(const char* fmt, ...);
extern "C" unsigned re4dc_ui_frame();
#if defined(RE4DC_HW_FOG_HAZE_TOGGLE) && RE4DC_HW_FOG_HAZE_TOGGLE
extern "C" unsigned re4dc_vi_retrace_count(void);
#endif

namespace {
struct HwFogRow {
    unsigned room;
    float keep;     // mm: haze sprites at a view depth beyond this are replaced (FX_LEVEL 0)
    float box;      // mm: the haze box depth (the PS2 recipe's range): the veil is complete behind it
    float veil;     // the mean veil of the replaced sprites, full indoor fade (0..1)
};
// Per-room rows (port/dreamcast/docs/HW_FOG_HAZE.md). keep = the recipe's full-alpha near-fade depth (3 m), box = the PS2 recipe range,
// veil = matched on frozen stills (the replaced sprites' mean brightness against the fog's, same tick and camera):
// r106 0.92 x 0.10, r109 0.43 x 0.10, r107 below 0.12 x 0.10 (its far sprites added 0.0-0.2 / 255). r103 is
// EFFECT_HAZE_LEAN M3's (its own table veil and sprite subset) and has no row. r100 and r101 keep M3's table veil and
// near subset; their rows replace the M3 subset sprites (1 in 16 / 1 in 7 slots, alpha x 1.5, drawn at every depth)
// beyond the keep depth, and the row veil stands in for them (about subset share x 1.5 of a full far layer).
const HwFogRow kRows[] = {
    {0x100, 3000.0f, 5000.0f, 0.010f},  // 8d8775: the M3 subset (1 in 16) beyond 3 m (M3's own table veil stays)
    {0x101, 3000.0f, 5000.0f, 0.015f},  // 716c5a: the M3 subset beyond 3 m (M3's own table veil stays)
    {0x106, 3000.0f, 5000.0f, 0.09f},   // fog colour 6e6a59
    {0x107, 3000.0f, 5000.0f, 0.02f},   // 5f6059
    {0x109, 3000.0f, 5000.0f, 0.04f},   // 737166
    // r119 / r11b (night, fog colour 191c1d / 262727) had rows that cut every haze sprite beyond 3 m with no veil. Test
    // 12.1 drops them (lane t12dark, T12-DARK-ROOMS-20261015.md): a console player saw r11b's lake sky near-black in test
    // 12 where test 10 drew a light grey mist. Flycast draws those far sprites faintly (they added ~1/255 to the stills
    // this row was calibrated on), so it does not show the loss. Both rooms draw their whole haze again, as in test 10.
};
constexpr unsigned kRowCount = sizeof(kRows) / sizeof(kRows[0]);
constexpr unsigned kHold = 60;   // native frames the last note stays valid (the haze pass need not run every frame)
unsigned note_key, note_frame, kept, replaced, log_frame = ~0U, last_key = ~0U;
unsigned hwfog_off, hwfog_osd_until;   // HW_FOG_HAZE_TOGGLE: 1 = every haze sprite drawn, no veil (as knob off)
}

#if defined(RE4DC_HW_FOG_HAZE_TOGGLE) && RE4DC_HW_FOG_HAZE_TOGGLE
// HW_FOG_HAZE_TOGGLE (hwfog.mk, test discs): X + D-pad up + START (pad.cpp) switches the fog replacement off / on
// live, for console A/B with the fps meter; the label shows for 3 s (native_static.cpp re4dc_look_osd_text).
// Off draws every haze sprite and folds no veil (the fog table is rewritten on the next frame: key 0).
extern "C" void re4dc_hwfog_toggle(void)
{
    hwfog_off ^= 1U;
    hwfog_osd_until = re4dc_vi_retrace_count() + 180U;
    re4dc_log("hwfog: toggle %s frame=%u\n", hwfog_off ? "off" : "on", re4dc_ui_frame());
}
extern "C" const char* re4dc_hwfog_osd_text(void)
{
    if (int(hwfog_osd_until - re4dc_vi_retrace_count()) <= 0) return nullptr;
    return hwfog_off ? "HW fog OFF: all haze sprites" : "HW fog ON: far haze as fog";
}
#endif

// FX_LEVEL (effects30.mk, the effects-quality dial; weak: absent without FX_LEVEL): a lower level moves more of the
// haze to the fog. The keep depth comes 0.5 m nearer per level (3.0 / 2.5 / 2.0 m for 0 / 1 / 2); the veil keeps the
// level-0 density of the replaced layers (the fog costs no fill, so the replaced sprites are not thinned first).
extern "C" int re4dc_fx_level_get(void) __attribute__((weak));
static unsigned hwfog_level()
{
    const int l = re4dc_fx_level_get ? re4dc_fx_level_get() : 0;
    return l <= 0 ? 0U : l >= 2 ? 2U : unsigned(l);
}
static float hwfog_keep(const HwFogRow& r, unsigned level)
{
    const float k = r.keep - 500.0f * float(level);
    return k < 1000.0f ? 1000.0f : k;
}
// The replaced sprites' alpha by view depth d, as the PS2 recipe draws them: near fade 0.5 m -> 3.0 m, far fade over
// the last 30 % of the box. The veil in front of depth z is the integral of it from the keep depth to z.
static float hwfog_alpha(const HwFogRow& r, float d)
{
    float a = (d - 500.0f) / 2500.0f;
    a = a < 0.0f ? 0.0f : a > 1.0f ? 1.0f : a;
    if (d > r.box * 0.7f) a *= 1.0f - (d - r.box * 0.7f) / (r.box * 0.3f);
    return a > 0.0f ? a : 0.0f;
}
static float hwfog_integral(const HwFogRow& r, float from, float to)
{
    if (!(to > from)) return 0.0f;
    const unsigned n = 24;
    const float h = (to - from) / float(n);
    float sum = 0.0f;
    for (unsigned i = 0; i < n; ++i) sum += hwfog_alpha(r, from + (float(i) + 0.5f) * h);
    return sum * h;
}

// key: row (bits 0..7, index + 1), indoor step 0..8 (bits 8..11), FX_LEVEL (bits 12..13)
extern "C" int re4dc_hwfog_haze(unsigned room, float depth, float indoor)
{
    if (hwfog_off) return 0;
    for (unsigned i = 0; i < kRowCount; ++i) {
        if (kRows[i].room != room) continue;
        const float s = indoor < 0.0f ? 0.0f : indoor > 1.0f ? 1.0f : indoor;
        const unsigned level = hwfog_level();
        note_key = (i + 1) | (unsigned(s * 8.0f + 0.5f) << 8) | (level << 12);
        note_frame = re4dc_ui_frame();
        if (depth > hwfog_keep(kRows[i], level)) { ++replaced; return 1; }
        ++kept;
        return 0;
    }
    return 0;
}

// FXDEAD (esp_sub.cpp fxdClass): 1 when re4dc_hwfog_haze keeps a note for this room (it is a table row), so its haze sprites feed the fog.
extern "C" int re4dc_hwfog_has_row(unsigned room)
{
    for (unsigned i = 0; i < kRowCount; ++i) {
        if (kRows[i].room == room) return 1;
    }
    return 0;
}

extern "C" unsigned re4dc_hwfog_key(void)
{
    const unsigned frame = re4dc_ui_frame();
    const unsigned key = (!hwfog_off && note_key && frame - note_frame <= kHold) ? note_key : 0U;
    if (key != last_key || (frame % 600U == 0 && frame != log_frame)) {
        log_frame = frame;
        const unsigned row = key & 255U, level = (key >> 12) & 3U;
        re4dc_log("hwfog: frame=%u room=%03x step=%u/8 level=%u veil=%u/1000 keep=%u box=%u kept=%u replaced=%u\n",
                  frame, row ? kRows[row - 1].room : 0U, (key >> 8) & 15U, level,
                  row ? unsigned(kRows[row - 1].veil * float(RE4DC_HW_FOG_VEIL_PCT) * 10.0f) : 0U,
                  row ? unsigned(hwfog_keep(kRows[row - 1], level)) : 0U, row ? unsigned(kRows[row - 1].box) : 0U,
                  kept, replaced);
        last_key = key;
    }
    return key;
}

// table[j] is the fog amount at depth tfar / v(j), v(j) = 2^(j >> 4) x ((j & 15) + 16) / 16 (KOS pvr_fog.c), j < 128;
// table[128] is the far plane / 256. The row's veil is the level-0 replaced layers' (keep .. box) mean veil; a lower
// level's nearer keep depth adds the replaced near layers' share by the same alpha integral.
extern "C" void re4dc_hwfog_table(float* table, float tfar, unsigned key)
{
    const unsigned row = key & 255U, step = (key >> 8) & 15U, level = (key >> 12) & 3U;
    if (!row || row > kRowCount || !step) return;
    const HwFogRow& r = kRows[row - 1];
    const float keep = hwfog_keep(r, level), base = hwfog_integral(r, r.keep, r.box);
    if (!(base > 0.0f)) return;
    const float b = r.veil * float(RE4DC_HW_FOG_VEIL_PCT) / 100.0f * float(step) / 8.0f / base;
    for (unsigned j = 0; j < 129; ++j) {
        const float v = j < 128 ? float((j & 15U) + 16U) / 16.0f * float(1U << (j >> 4)) : 256.0f;
        const float z = tfar / v;
        float veil = b * hwfog_integral(r, keep, z < r.box ? z : r.box);
        veil = veil > 0.95f ? 0.95f : veil;
        table[j] = 1.0f - (1.0f - table[j]) * (1.0f - veil);
    }
}

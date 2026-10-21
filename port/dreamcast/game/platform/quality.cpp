// D367 quality modes (QUALITY=1): state, presets, /cd/dc/quality.txt, VMU file RE4DCCFG, freeze.
// Design: design-lowmode DESIGN.md A1/A3/A4. Render-side only; see quality.h.
//
// /cd/dc/quality.txt (test fixture, wins over the VMU; skips the picker unless picker=1):
//   mode=standard|original   features=+lod,-lod   picker=0|1   pace=0..3 (calls set_pace)
//   render=quality|standard|fast or perf=0|1 (RENDER_OPTION; calls set_render)
//   speed=off|vmu|screen|both (RENDER_OPTION; calls set_speed)
// Stored choice: the 32-byte RE4DCCFG record (quality.h Re4dcQualityCfg, design-vmu layout),
// read once at the title and stored only when the picker's choice changes, through
// re4dc_quality_cfg_load/store. The VMU layer (design-vmu S5) owns the card file; the weak
// versions here keep the record in memory for this boot and never touch a card.
#include <stdlib.h>
#include <stddef.h>
#include <string.h>

#include "re4dc_platform.h"
#include "quality.h"
#include "warp_late.h"

#ifndef RE4DC_QUALITY_DEFAULT
#define RE4DC_QUALITY_DEFAULT 1
#endif
#ifndef RE4DC_QUALITY_PICKER
#define RE4DC_QUALITY_PICKER 1
#endif
#ifndef RE4DC_MESH_LOD_PX
#define RE4DC_MESH_LOD_PX 3
#endif
#ifndef RE4DC_RENDER_OPTION
#define RE4DC_RENDER_OPTION 0
#endif
#if RE4DC_RENDER_OPTION
extern "C" void re4dc_res_set(unsigned mode);  // res_mode.cpp
#if defined(RE4DC_PACE_STEADY) && RE4DC_PACE_STEADY
#define RQ_KEEP (uint32_t(RQ_PACE_MASK) | uint32_t(RQ_RENDER_MASK) | uint32_t(RQ_SPEED_MASK) | uint32_t(RQ_PACE_STEADY_BIT))
#else
#define RQ_KEEP (uint32_t(RQ_PACE_MASK) | uint32_t(RQ_RENDER_MASK) | uint32_t(RQ_SPEED_MASK))  // settings kept across mode presets
#endif
#else
#define RQ_KEEP uint32_t(RQ_PACE_MASK)
#endif

extern "C" int re4dc_fixture_read(const char* path, char* buffer, unsigned size);   // os.cpp
extern "C" void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room);

namespace {
constexpr uint32_t kPreset[2] = {0u, RQ_LOD_COARSE};

Re4dcQuality q = {RE4DC_QUALITY_DEFAULT, 0, RE4DC_QSRC_DEFAULT, 0, kPreset[RE4DC_QUALITY_DEFAULT],
                  RE4DC_QUALITY_DEFAULT ? 5.0f : float(RE4DC_MESH_LOD_PX)};
bool inited;
int file_picker = -1;              // quality.txt picker= (-1: not given)
int file_pace = -1;                // quality.txt pace= (-1: not given; test fixture for set_pace)
#if RE4DC_RENDER_OPTION
int file_render = -1;
int file_speed = -1;               // quality.txt speed=off|vmu|screen|both (-1: not given)                // quality.txt render= / perf= (-1: not given)
#endif
uint32_t file_set, file_clear;     // quality.txt feature overrides
uint8_t stored_mode = 0xFF;        // mode in the stored record (0xFF: none)
uint32_t stored_features;

#ifndef RE4DC_QUALITY_LOD_PX
#define RE4DC_QUALITY_LOD_PX 5 // Standard (RQ_LOD_COARSE) mesh LOD error in projected pixels
#endif
void apply(int mode)
{
    q.mode = uint8_t(mode ? RE4DC_QUALITY_STANDARD : RE4DC_QUALITY_ORIGINAL);
    q.features = ((kPreset[q.mode] | file_set) & ~file_clear & ~RQ_KEEP) | (q.features & RQ_KEEP);
    q.lod_px = (q.features & RQ_LOD_COARSE) ? float(RE4DC_QUALITY_LOD_PX) : float(RE4DC_MESH_LOD_PX);
}

uint32_t crc32(const uint8_t* p, unsigned n)
{
    uint32_t c = 0xFFFFFFFFu;
    while (n--) {
        c ^= *p++;
        for (int k = 0; k < 8; ++k) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}

uint32_t feature_bit(const char* name, unsigned len)
{
    if (len == 3 && !memcmp(name, "lod", 3)) return RQ_LOD_COARSE;
    return 0;
}

// "key=value" tokens separated by whitespace or commas inside features=.
void parse_file(char* t)
{
    int mode = -1;
    for (char* s = strtok(t, " \t\r\n"); s; s = strtok(nullptr, " \t\r\n")) {
        if (!strncmp(s, "mode=", 5)) {
            if (!strcmp(s + 5, "standard")) mode = RE4DC_QUALITY_STANDARD;
            else if (!strcmp(s + 5, "original")) mode = RE4DC_QUALITY_ORIGINAL;
            else re4dc_log("quality: quality.txt unknown mode '%s'\n", s + 5);
        } else if (!strncmp(s, "pace=", 5)) {
#if defined(RE4DC_PACE_STEADY) && RE4DC_PACE_STEADY
            file_pace = atoi(s + 5) & 7;   // 4 = Steady
            if (file_pace > RE4DC_PACE_SET_STEADY) file_pace = 0;
#else
            file_pace = atoi(s + 5) & 3;
#endif
#if RE4DC_RENDER_OPTION
        } else if (!strncmp(s, "render=", 7)) {  // Rendering: quality | standard | fast
#if defined(RE4DC_RENDER_FSAA) && RE4DC_RENDER_FSAA
            // RENDER_FSAA: standard | fsaa (the row's values 0 / 1; anything else is Standard)
            file_render = !strcmp(s + 7, "fsaa") ? 1 : RE4DC_RENDER_QUALITY;
#else
            file_render = !strcmp(s + 7, "fast") ? RE4DC_RENDER_FAST
                          : !strcmp(s + 7, "standard") ? RE4DC_RENDER_STANDARD : RE4DC_RENDER_QUALITY;
#endif
        } else if (!strncmp(s, "speed=", 6)) {   // speed display: off | vmu | screen | both
            const char* v = s + 6;
            file_speed = !strcmp(v, "vmu") ? RE4DC_SPEED_VMU : !strcmp(v, "screen") ? RE4DC_SPEED_SCREEN
                         : !strcmp(v, "both") ? RE4DC_SPEED_BOTH : RE4DC_SPEED_OFF;
        } else if (!strncmp(s, "perf=", 5)) {    // alias of render=: 1 standard (640x240), 0 quality
            file_render = atoi(s + 5) ? RE4DC_RENDER_STANDARD : RE4DC_RENDER_QUALITY;
#endif
        } else if (!strncmp(s, "picker=", 7)) {
            file_picker = atoi(s + 7) ? 1 : 0;
        } else if (!strncmp(s, "features=", 9)) {
            for (const char* f = s + 9; *f;) {
                const char sign = *f;
                if (sign == '+' || sign == '-') ++f;
                const char* e = f;
                while (*e && *e != ',') ++e;
                const uint32_t bit = feature_bit(f, unsigned(e - f));
                if (!bit) re4dc_log("quality: quality.txt unknown feature '%.*s'\n", int(e - f), f);
                else if (sign == '-') { file_clear |= bit; file_set &= ~bit; }
                else { file_set |= bit; file_clear &= ~bit; }
                f = *e ? e + 1 : e;
            }
        }
    }
    if (mode >= 0) { apply(mode); q.source = RE4DC_QSRC_FILE; }
    else apply(q.mode);
}

uint32_t cfg_crc(const Re4dcQualityCfg* r)
{
    return crc32(reinterpret_cast<const uint8_t*>(r), offsetof(Re4dcQualityCfg, crc));
}

void cfg_read()
{
    Re4dcQualityCfg r;
    if (!re4dc_quality_cfg_load(&r)) { re4dc_log("quality: no stored RE4DCCFG record\n"); return; }
    if (memcmp(r.magic, "R4CF", 4) || r.version != 1 || r.mode > 1 || r.crc != cfg_crc(&r)) {
        re4dc_log("quality: RE4DCCFG record invalid; defaults\n");
        return;
    }
    stored_mode = r.mode;
    stored_features = r.features;
    q.features = (q.features & ~RQ_KEEP) | (r.features & RQ_KEEP);
    apply(r.mode);
    q.source = RE4DC_QSRC_VMU;
    re4dc_log("quality: RE4DCCFG mode=%s\n", r.mode == RE4DC_QUALITY_STANDARD ? "standard" : "original");
}

void cfg_write()
{
    Re4dcQualityCfg r;
    memset(&r, 0, sizeof(r));
    memcpy(r.magic, "R4CF", 4);
    r.version = 1;
    r.mode = q.mode;
    r.features = q.features;
    r.crc = cfg_crc(&r);
    if (!re4dc_quality_cfg_store(&r)) { re4dc_log("quality: RE4DCCFG not stored (no card, full or removed)\n"); return; }
    stored_mode = q.mode;
    stored_features = q.features;
    re4dc_log("quality: RE4DCCFG stored mode=%s\n", q.mode == RE4DC_QUALITY_STANDARD ? "standard" : "original");
}

void log_state(const char* what)
{
    static const char* const kSrc[] = {"default", "vmu", "file", "picker"};
    re4dc_log("quality: %s mode=%s source=%s features=%08lx lod_px=%u\n", what, q.mode == RE4DC_QUALITY_STANDARD ? "standard" : "original",
              kSrc[q.source & 3], (unsigned long) q.features, unsigned(q.lod_px));
}
}  // namespace

// In-memory persistence until the VMU layer links strong versions (design-vmu S5).
static_assert(sizeof(Re4dcQualityCfg) == 32, "RE4DCCFG record");
static Re4dcQualityCfg g_cfg_mem;
static int g_cfg_mem_valid;
extern "C" __attribute__((weak)) int re4dc_quality_cfg_load(Re4dcQualityCfg* out)
{
    if (!g_cfg_mem_valid) return 0;
    *out = g_cfg_mem;
    return 1;
}
extern "C" __attribute__((weak)) int re4dc_quality_cfg_store(const Re4dcQualityCfg* rec)
{
    g_cfg_mem = *rec;
    g_cfg_mem_valid = 1;
    return 1;
}

#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
// Late-activation arms (warp_late.h bit 1): world LOD error 20 px from the activation tick on.
extern "C" const Re4dcQuality* re4dc_quality(void) {
    if (RE4DC_WARP_LATE(RE4DC_LATE_WORLD_LOD20)) {
        static Re4dcQuality diagnostic;
        diagnostic = q;
        diagnostic.lod_px = 20.0f;
        return &diagnostic;
    }
    return &q;
}
#else
extern "C" const Re4dcQuality* re4dc_quality(void) { return &q; }
#endif

extern "C" void re4dc_quality_init(void)
{
    if (inited) return;
    inited = true;
    unsigned kos_free0, kos_break0, kos_free1, kos_break1, used;
    re4dc_kos_heap_state(&kos_free0, &used, &kos_break0);
    cfg_read();
    static char text[256];
    const int n = re4dc_fixture_read("/cd/dc/quality.txt", text, sizeof(text) - 1);
    if (n > 0) { text[n] = 0; parse_file(text); }
    if (file_pace >= 0) re4dc_quality_set_pace(file_pace);
#if RE4DC_RENDER_OPTION
    if (file_speed >= 0) re4dc_quality_set_speed(file_speed);
#if defined(RE4DC_RENDER_FSAA_BOOT) && RE4DC_RENDER_FSAA_BOOT
    if (file_render < 0) file_render = 1;  // RENDER_FSAA_BOOT (test twins only): this boot starts in FSAA
#endif
    if (file_render >= 0) re4dc_quality_set_render(file_render);
    else re4dc_res_set(re4dc_quality_render() == RE4DC_RENDER_FAST ? 4U : re4dc_quality_render() == RE4DC_RENDER_STANDARD ? 1U : 0U);
#endif
    re4dc_kos_heap_state(&kos_free1, &used, &kos_break1);
    if (!RE4DC_QUALITY_PICKER || file_picker == 0 || (n > 0 && file_picker != 1)) q.chosen = 1;
    re4dc_log("quality: init kos_free %u->%u break %u->%u file=%d picker=%s\n", kos_free0, kos_free1, kos_break0,
              kos_break1, n, q.chosen ? "skip" : "show");
    log_state("init");
}

extern "C" int re4dc_quality_picker_wanted(void)
{
    re4dc_quality_init();
    return !q.chosen && !q.frozen;
}

extern "C" void re4dc_quality_set_mode(int mode, int source)
{
    if (q.frozen) { re4dc_log("quality: set_mode(%d) after freeze ignored\n", mode); return; }
    apply(mode);
    q.source = uint8_t(source);
}

extern "C" void re4dc_quality_toggle(uint32_t feature)
{
    if (q.frozen) return;
    q.features ^= feature & RQ_WIRED;
    q.lod_px = (q.features & RQ_LOD_COARSE) ? float(RE4DC_QUALITY_LOD_PX) : float(RE4DC_MESH_LOD_PX);
}

extern "C" int re4dc_quality_pace(void)
{
#if defined(RE4DC_PACE_STEADY) && RE4DC_PACE_STEADY
    if (q.features & RQ_PACE_STEADY_BIT) return RE4DC_PACE_SET_STEADY;
#endif
    return int((q.features & RQ_PACE_MASK) >> RQ_PACE_SHIFT);
}

extern "C" int re4dc_quality_set_pace(int pace)
{
    re4dc_quality_init();
#if defined(RE4DC_PACE_STEADY) && RE4DC_PACE_STEADY
    // Steady: the bit plus Fast in the 2-bit field (what a build without Steady reads).
    q.features &= ~uint32_t(RQ_PACE_STEADY_BIT);
    if (pace == RE4DC_PACE_SET_STEADY) { q.features |= RQ_PACE_STEADY_BIT; pace = RE4DC_PACE_FAST; }
#endif
    q.features = (q.features & ~uint32_t(RQ_PACE_MASK)) | ((uint32_t(pace) << RQ_PACE_SHIFT) & RQ_PACE_MASK);
    re4dc_log("quality: pace=%d\n", re4dc_quality_pace());
    if (stored_mode == q.mode && stored_features == q.features) return 1;
    cfg_write();
    return stored_features == q.features;
}

#if RE4DC_RENDER_OPTION
extern "C" int re4dc_quality_speed(void) { return int((q.features & RQ_SPEED_MASK) >> RQ_SPEED_SHIFT); }

extern "C" int re4dc_quality_set_speed(int speed)
{
    static const char* const kName[4] = {"off", "vmu", "screen", "both"};
    re4dc_quality_init();
    speed &= 3;
    q.features = (q.features & ~uint32_t(RQ_SPEED_MASK)) | (uint32_t(speed) << RQ_SPEED_SHIFT);
    re4dc_log("quality: speed display=%s\n", kName[speed]);
    if (stored_mode == q.mode && stored_features == q.features) return 1;
    cfg_write();
    return stored_features == q.features;
}

#if defined(RE4DC_RENDER_FSAA) && RE4DC_RENDER_FSAA
// RENDER_FSAA (game30.mk): Rendering = Standard / FSAA (res_mode.cpp modes 0, 3; Standard = the 640x480 Quality
// mode), for this boot only: every boot starts in Standard (or quality.txt render=), the stored RE4DCCFG field is
// ignored and never rewritten, so FSAA never sticks to the VMU.
static int fsaa_render;
extern "C" int re4dc_quality_render(void) { return fsaa_render; }

extern "C" int re4dc_quality_set_render(int render)
{
    static const unsigned kMode[2] = {0U, 3U};
    static const char* const kName[2] = {"standard", "fsaa"};
    if (render < 0 || render > 1) render = 0;
    fsaa_render = render;
    re4dc_log("quality: render=%s (this boot only)\n", kName[render]);
    re4dc_res_set(kMode[render]);
    return 1;
}
#elif RE4DC_RENDER_QUALITY_ONLY
// RENDER_QUALITY_ONLY (game30.mk): always Quality; the stored field is ignored and left as it is.
extern "C" int re4dc_quality_render(void) { return RE4DC_RENDER_QUALITY; }

extern "C" int re4dc_quality_set_render(int render)
{
    re4dc_log("quality: render=quality (fixed; asked %d)\n", render);
    re4dc_res_set(0U);
    return 1;
}
#else
extern "C" int re4dc_quality_render(void) { return int((q.features & RQ_RENDER_MASK) >> RQ_RENDER_SHIFT); }

extern "C" int re4dc_quality_set_render(int render)
{
    static const unsigned kMode[3] = {0U, 1U, 4U};  // res_mode.cpp: Quality 640x480, Standard 640x240, Fast 320x240
    static const char* const kName[3] = {"quality", "standard", "fast"};
    re4dc_quality_init();
    if (render < RE4DC_RENDER_QUALITY || render > RE4DC_RENDER_FAST) render = RE4DC_RENDER_QUALITY;
    q.features = (q.features & ~uint32_t(RQ_RENDER_MASK)) | (uint32_t(render) << RQ_RENDER_SHIFT);
    re4dc_log("quality: render=%s\n", kName[render]);
    re4dc_res_set(kMode[render]);
    if (stored_mode == q.mode && stored_features == q.features) return 1;
    cfg_write();
    return stored_features == q.features;
}
#endif
#endif

extern "C" void re4dc_quality_picker_done(void)
{
    q.chosen = 1;
    log_state("picked");
    if (stored_mode != q.mode || stored_features != q.features) cfg_write();
}

extern "C" void re4dc_quality_freeze(const char* where)
{
    if (q.frozen) return;
    re4dc_quality_init();
    q.frozen = 1;
    q.chosen = 1;
    log_state(where);
}

#if RE4DC_QUALITY_ASSETS
extern "C" int re4dc_quality_std_assets(void) { return q.frozen && q.mode == RE4DC_QUALITY_STANDARD; }
#endif

extern "C" int re4dc_quality_hud(unsigned v[2])
{
    v[0] = q.mode;
    v[1] = q.features;
    return 2;
}

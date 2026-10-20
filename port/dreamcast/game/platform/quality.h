// D367 quality modes (QUALITY=1; design: design-lowmode DESIGN.md section A).
//
// One render-side state, written only before gameplay (title picker, VMU file RE4DCCFG,
// /cd/dc/quality.txt) and frozen when the game starts (titleExit, or the first room entry
// for paths that skip the title). Readers are render-side code only; nothing on the logic
// side may branch on it, so the logic trace stays STRICT across modes.
#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Mode names are the user's: STANDARD is the budget-first mode and the default; ORIGINAL is the
// faithful GameCube look. The values are stored in the RE4DCCFG record.
enum {
    RE4DC_QUALITY_ORIGINAL = 0,
    RE4DC_QUALITY_STANDARD = 1,
};

// Where the mode came from.
enum {
    RE4DC_QSRC_DEFAULT = 0,   // build default (QUALITY_DEFAULT)
    RE4DC_QSRC_VMU = 1,       // RE4DCCFG on the first VMU
    RE4DC_QSRC_FILE = 2,      // /cd/dc/quality.txt
    RE4DC_QSRC_PICKER = 3,    // the title picker this boot
};

// Feature bits (render-only switches). Only RQ_LOD_COARSE is wired today; the other bits are
// reserved for the Standard-mode options as their owners land them (records, occlusion, FTRV matrices,
// light cap, Leon merge, low-poly Ganados, crowd ladder, effect draw cap).
enum {
    RQ_LOD_COARSE = 1u << 0,   // native static meshlet LOD threshold 5 px instead of MESH_LOD_PX
    RQ_RECORDS = 1u << 1,
    RQ_OCC_AGGR = 1u << 2,
    RQ_FTRV_MTX = 1u << 3,
    RQ_LIGHT_CAP = 1u << 4,
    RQ_LEON_MERGE = 1u << 5,
    RQ_GANADO_LOW = 1u << 6,
    RQ_CROWD = 1u << 7,
    RQ_FX_DRAWCAP = 1u << 8,
    RQ_WIRED = RQ_LOD_COARSE,
    // Frame pacing setting (design-pacing; the pacing builder reads it): a 2-bit field, not a
    // preset bit. Kept across mode changes and stored in RE4DCCFG with the mode.
    RQ_PACE_SHIFT = 16,
    RQ_PACE_MASK = 3u << 16,
    // RENDER_OPTION (game30.mk): Rendering setting, a 2-bit field kept across mode presets and stored like pacing:
    // 0 Quality (640x480), 1 Standard (640x240 alternating lines), 2 Fast (320x240).
    RQ_RENDER_SHIFT = 18,
    RQ_RENDER_MASK = 3u << 18,
    // RENDER_OPTION: speed display (R + START cycles it), a 2-bit field: RE4DC_SPEED_*.
    RQ_SPEED_SHIFT = 20,
    RQ_SPEED_MASK = 3u << 20,
    // PACE_STEADY (pace.mk): the Steady pacing mode, stored as this bit with the 2-bit field at Fast, so a build without
    // Steady reads the record as Fast. re4dc_quality_pace() returns RE4DC_PACE_STEADY when it is set.
    RQ_PACE_STEADY_BIT = 1u << 22,
};
enum {
    RE4DC_PACE_DEFAULT = 0,   // the build's PACE_* knobs
    RE4DC_PACE_SMOOTH = 1,
    RE4DC_PACE_FAST = 2,
    RE4DC_PACE_OFF = 3,
    RE4DC_PACE_SET_STEADY = 4,   // PACE_STEADY builds only
};

enum {
    RE4DC_SPEED_OFF = 0,     // bit 0: the VMU speed page, bit 1: the on-screen counter
    RE4DC_SPEED_VMU = 1,
    RE4DC_SPEED_SCREEN = 2,
    RE4DC_SPEED_BOTH = 3,
};
enum {
    RE4DC_RENDER_QUALITY = 0,
    RE4DC_RENDER_STANDARD = 1,
    RE4DC_RENDER_FAST = 2,
};

typedef struct Re4dcQuality {
    uint8_t mode;       // RE4DC_QUALITY_*
    uint8_t frozen;     // 1 once the game has started: later writes are ignored (logged)
    uint8_t source;     // RE4DC_QSRC_*
    uint8_t chosen;     // picker shown (or skipped) this boot
    uint32_t features;  // RQ_* (mode preset, then quality.txt / debug overrides)
    float lod_px;       // native static LOD threshold in projected pixels
} Re4dcQuality;

// RE4DCCFG record (design-vmu DESIGN.md: 2-block VMS file, header + icon, then this 32-byte
// record; written only when the picker's choice changes). crc = CRC-32 of the first 28 bytes.
typedef struct Re4dcQualityCfg {
    char magic[4];      // "R4CF"
    uint8_t version;    // 1
    uint8_t mode;       // RE4DC_QUALITY_*
    uint8_t pad[2];
    uint32_t features;  // feature override word (RQ_*)
    uint8_t reserved[16];
    uint32_t crc;
} Re4dcQualityCfg;
// Persistence, owned by the VMU layer (design-vmu S5, vmu_store). quality.cpp defines weak
// in-memory versions (this boot only, never touches a card) until the VMU shim links strong
// ones. load: 1 and *out filled when a record exists (the caller checks magic/version/crc);
// store: 1 when saved.
int re4dc_quality_cfg_load(Re4dcQualityCfg* out);
int re4dc_quality_cfg_store(const Re4dcQualityCfg* rec);

const Re4dcQuality* re4dc_quality(void);
// Reads /cd/dc/quality.txt and the stored record once (idempotent). Called at the title.
void re4dc_quality_init(void);
// Picker: 1 when it should open now (first main menu this boot, no file override).
int re4dc_quality_picker_wanted(void);
// Mode preset (+ file overrides). Ignored once frozen. `source` = RE4DC_QSRC_*.
void re4dc_quality_set_mode(int mode, int source);
// Debug submenu: toggle one feature bit on top of the preset. Ignored once frozen.
void re4dc_quality_toggle(uint32_t feature);
// Picker done: marks chosen, stores the record when the choice changed.
void re4dc_quality_picker_done(void);
// Game start (titleExit / first room entry): freezes the state and logs it.
void re4dc_quality_freeze(const char* where);
// Pacing setting (RE4DC_PACE_*). set_pace works before and after the freeze (an options
// setting, not a render preset) and stores RE4DCCFG when the value changes (a VMU write of
// about 35 vblanks when the VMU layer is linked). Returns 1 when stored or unchanged.
int re4dc_quality_pace(void);
int re4dc_quality_set_pace(int pace);
// RENDER_OPTION: Rendering setting (RE4DC_RENDER_*); set_render switches the render mode at the next safe point and
// stores RE4DCCFG like set_pace.
int re4dc_quality_render(void);
int re4dc_quality_set_render(int render);
// RENDER_OPTION: speed display setting (RE4DC_SPEED_*); set_speed stores RE4DCCFG like set_pace.
int re4dc_quality_speed(void);
int re4dc_quality_set_speed(int speed);
// QUALITY_ASSETS: 1 when the frozen mode is Standard (select the Standard asset set).
int re4dc_quality_std_assets(void);
// PERF_HUD: v[0] = mode, v[1] = feature word. Returns 2.
int re4dc_quality_hud(unsigned v[2]);

#ifdef __cplusplus
}
#endif

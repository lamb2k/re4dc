// Native effect service (lane eng-e2, milestone E2): effect sequences and their sprites simulated by the engine in
// structure-of-arrays form and submitted to the renderer as they are. The hosted behaviour starts and stops effects
// through the original entry points (EstSet, EspSetEatEffect, EffectEspDelete ...), whose engine bodies are in fx.cpp.
//
// Data: the effect tables the hosted code registers (EspDataLoad: the original EffData blocks of the archives), read in
// place; packed records (the Dreamcast tree's ESQ tables) decoded when a sequence spawns them.
// Randomness: presentation only (owner decision 2026-11-19, "Split it"): the engine's own generator (fx_rng) seeds
// each sequence; the per-sprite spreads come from that seed with the original's per-instance LCG (fRandSeed1_1 form),
// so the service never draws from the game's generator (Rnd) and the AI's stream is the behaviour's alone.
// Layout: sprites in SoA rows (positions, speeds, accelerations, sizes, colours, counters), one kernel per field group
// over the dense live range; a dead sprite is swapped with the last live one (order is not observable: the renderer
// sorts by depth).
#ifndef ENGINE_FX_H
#define ENGINE_FX_H
#include <stdint.h>

#define FX_MAX 512        // live sprites
#define FX_SEQ_MAX 64     // live sequence players

#ifdef __cplusplus
extern "C" {
#endif
struct FxSprites {
    unsigned n;                                   // live count (dense 0..n-1)
    float px[FX_MAX], py[FX_MAX], pz[FX_MAX];     // position (parent space while attached)
    float vx[FX_MAX], vy[FX_MAX], vz[FX_MAX];     // speed
    float ax[FX_MAX], ay[FX_MAX], az[FX_MAX];     // speed_plus (gravity and drift)
    float dv[FX_MAX];                             // speed damping (D_speed)
    float rx[FX_MAX], ry[FX_MAX], rz[FX_MAX];     // angle (radians)
    float wx[FX_MAX], wy[FX_MAX], wz[FX_MAX];     // angle speed
    float sbx[FX_MAX], sby[FX_MAX];               // base size
    float smul[FX_MAX], splus[FX_MAX], sdamp[FX_MAX];   // size multiplier, its speed, the speed's damping
    float cr[FX_MAX], cg[FX_MAX], cb[FX_MAX], ca[FX_MAX];       // colour
    float dr[FX_MAX], dg[FX_MAX], db[FX_MAX], da[FX_MAX];       // colour multiplier per tick after the hold
    uint8_t c0r[FX_MAX], c0g[FX_MAX], c0b[FX_MAX], c0a[FX_MAX]; // fade-in colour
    uint16_t colmax[FX_MAX], colhold[FX_MAX], posstart[FX_MAX], sizestart[FX_MAX], lifemax[FX_MAX], life[FX_MAX];
    uint16_t anmcnt[FX_MAX];
    uint8_t tex[FX_MAX], ptn[FX_MAX], anmrate[FX_MAX], blend[FX_MAX], id[FX_MAX], release[FX_MAX], owner[FX_MAX];
    uint32_t tool[FX_MAX];
    const float* parent[FX_MAX];                  // the bone's world matrix (3x4, read in place) or 0 = world
    void* model[FX_MAX];                          // the model the sprite follows (killed with it) or 0
    uint32_t guid[FX_MAX];
    uint32_t pem[FX_MAX];                         // owner info: the Core_pEm the deletes match
    uint32_t uid[FX_MAX];                         // spawn number (the equivalence check matches sprites by it)
};
extern struct FxSprites fx_sprites;

// Service calls (engine)
void fx_room_init(void);
void fx_move(void);                 // once a tick: sequence players, then the sprite kernels
unsigned fx_live_count(void);
void fx_report(void);
void fx_bind_archive(const void* base, unsigned bytes);   // an archive whose ESQ table packs records (DC tree)
// Texture of a sprite pattern for the renderer: the (texture id, pattern) the sprite shows this tick.
// Check build: the sequence seeds come from fx_check_seed instead of the engine generator.
extern unsigned (*fx_check_seed)(void);
// Counters
struct FxStats { uint32_t est_calls, est_nodata, seq_started, seq_full, spawned, full, kind1, efm, died, deleted, no_tex; uint32_t peak; };
extern struct FxStats fx_stats;
#ifdef __cplusplus
}
#endif
#endif

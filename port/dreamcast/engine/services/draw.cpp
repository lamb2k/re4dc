// E1 drawing glue (lane eng-e1): the camera record from the hosted camera (pG->Cam: the look-at matrix and the
// projection the camera code computed this tick) and the live HUD words, handed to the C renderer (core/draw_e1.c),
// which reads Leon's matrices in place from the actor table and the native skeleton's tables (lane eng-e1c).
#include "global.h"
#include "player.h"
#include "pl_npc.h"
#include "camera.h"
#include "view.h"
#include "e1_core.h"
#include "e1_engine.h"
#include "e1_kos.h"
#include "skel.h"
#include "e1_skel_view.h"
#include <string.h>

extern "C" {
int e1_draw_open_c(const char* pack);
void e1_draw_picture_c(const float* camera, const uint32_t* hud, const void* leon, const E1SkelView* leon_skel, unsigned identity,
                       uint32_t* wait_us, uint32_t* draw_us, const E1SkelView* partner, int world, const void* partner_record);
}
extern "C" int PlGetWeaponNo();
static int headless;

// The native skeleton table of a model as the renderer reads it (pointers only; lane eng-e1c)
static int skel_view(const cModel* m, E1SkelView* v)
{
    const SkelTable* t = m ? skel_table_of(m) : 0;
    if (!t) return 0;
    v->world = &t->world[0].m[0][0];
    v->pal = &t->pal[0].m[0][0];
    v->bind[0] = t->soa + SK_BX * t->cap;
    v->bind[1] = t->soa + SK_BY * t->cap;
    v->bind[2] = t->soa + SK_BZ * t->cap;
    v->n = t->n;
    return 1;
}

void e1_draw_open()
{
    file_t f = fs_open("/cd/HEADLESS", O_RDONLY);
    if (f >= 0) { fs_close(f); headless = 1; e1_log("E1 draw: headless\n"); return; }
    if (!e1_draw_open_c(e1_scene == E1_SCENE_HILL ? "/cd/HILL.PAK" : "/cd/CROSS.PAK")) { headless = 1; e1_log("E1 draw: renderer refused the pack, headless\n"); }
}

void e1_draw_picture(E1Timing& tm)
{
    if (headless) { tm.draw_us = 0; return; }
    const Camera& c = pG->Cam;
    float cam[26];
    memcpy(cam, c.v_mat, 48);
    cam[12] = 0.0f;                  // GX_PERSPECTIVE
    cam[13] = c.ProjMat[0][0];
    cam[14] = c.ProjMat[0][2];
    cam[15] = c.ProjMat[1][1];
    cam[16] = c.ProjMat[1][2];
    cam[17] = c.ProjMat[2][2];
    cam[18] = c.ProjMat[2][3];
    cam[19] = 0.0f; cam[20] = 0.0f; cam[21] = 640.0f; cam[22] = 480.0f; cam[23] = 0.0f; cam[24] = 1.0f;
    cam[25] = ZFAR > 0.0f ? ZFAR : 18750.0f;
    static int shown;
    if (!shown++) e1_log("E1 draw: camera p %d %d %d proj %d/1000 %d/1000 %d/1000 %d/1000 far %d\n", (int) c.param.pos.x,
                         (int) c.param.pos.y, (int) c.param.pos.z, (int) (cam[13] * 1000), (int) (cam[15] * 1000),
                         (int) (cam[17] * 1000), (int) (cam[18] * 1000), (int) cam[25]);
    uint32_t hud[4] = {pG->pl_life, pG->pl_life_max, pG->weapon_no, (uint32_t) PlGetWeaponNo()};
    unsigned identity = (unsigned) pPL->id | ((unsigned) pPL->type << 8);
    uint32_t wait = 0, draw = 0;
    // lane eng-e1b: the partner's record; lane eng-e1d: each scene draws its own room's bake (DNOWORLD: none)
    static int diag = -1;   // diagnostic boot options: DNOWORLD (no world drawn), DNOMARK (no partner drawn)
    if (diag < 0) { diag = 0; file_t f = fs_open("/cd/DNOWORLD", O_RDONLY); if (f >= 0) { fs_close(f); diag |= 1; } f = fs_open("/cd/DNOMARK", O_RDONLY); if (f >= 0) { fs_close(f); diag |= 2; } }
    E1SkelView leon, partner;
    const int have_leon = skel_view(pPL, &leon), have_partner = !(diag & 2) && skel_view(pSUB, &partner);
    e1_draw_picture_c(cam, hud, pPL, have_leon ? &leon : 0, identity, &wait, &draw, have_partner ? &partner : 0,
                      !(diag & 1), pSUB);
    tm.draw_us = draw;
    tm.pvr_us = wait;   // PVR readiness wait (the graphics chip, not CPU work)
}

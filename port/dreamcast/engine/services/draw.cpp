// E1 drawing glue (lane eng-e1): the camera record from the hosted camera (pG->Cam: the look-at matrix and the
// projection the camera code computed this tick) and the live HUD words, handed to the C renderer (core/draw_e1.c),
// which reads Leon's matrices in place from the actor table.
#include "global.h"
#include "player.h"
#include "camera.h"
#include "view.h"
#include "e1_core.h"
#include "e1_engine.h"
#include "e1_kos.h"
#include <string.h>

extern "C" {
int e1_draw_open_c(void);
void e1_draw_picture_c(const float* camera, const uint32_t* hud, const void* leon, unsigned identity, uint32_t* wait_us,
                       uint32_t* draw_us);
}
extern "C" int PlGetWeaponNo();
static int headless;

void e1_draw_open()
{
    file_t f = fs_open("/cd/HEADLESS", O_RDONLY);
    if (f >= 0) { fs_close(f); headless = 1; e1_log("E1 draw: headless\n"); return; }
    if (!e1_draw_open_c()) { headless = 1; e1_log("E1 draw: renderer refused the pack, headless\n"); }
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
    e1_draw_picture_c(cam, hud, pPL, identity, &wait, &draw);
    tm.draw_us = draw;
    tm.wait_us = wait;
}

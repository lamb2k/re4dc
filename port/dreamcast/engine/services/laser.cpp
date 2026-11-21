// laser.cpp (lane eng-e1h, H-014.3): the laser sight's drawing setters. cObjWep::drawLaserSight is hosted decision
// code (where the laser points, the target, the don't-fire flag); its drawing calls land here, in every image, and
// write the renderer's laser state (services/e1_laser.h) in place: the line (EspDrawLaserLine; Draw_line3d_222 /
// Draw_line3d_local_222 in the shooting range) and the dot on an enemy (drawPoint). core/draw_e1.c e1_laser_pass
// draws them in the picture of the same tick. objWep's own drawPoint and Draw_line3d_* (GX immediate drawing) are made
// weak in the hosted unit (game/Makefile WEAKEN_game/objWep), so these bodies are linked and --gc-sections drops the
// originals.
#include "global.h"
#include "esp.h"
#include "camera.h"
#include "e1_engine.h"
#include "e1_laser.h"
#include "camera/eng_camera.h"   // lane eng-e1j: the view matrix is the camera service's record's
#include <math.h>

extern "C" E1Laser e1_laser;
E1Laser e1_laser;

// The line of the effect interface: red, faded to nothing at 12,000 units (esp19's max_laser_dist), as the original
// laser effect (esp19 Draw_line3d_local_222 under EspDrawLaserLine).
static void set_line(const Vec* a, const Vec* b, uint32_t rgb, float fade, float width, uint32_t view, uint32_t ztest)
{
    E1Laser& l = e1_laser;
    if (l.tick != e1_tick) {
        l.tick = e1_tick;
        l.lines = 0;
    }
    if (l.lines >= E1_LASER_LINES) return;
    E1LaserLine& s = l.line[l.lines++];
    s.p[0][0] = a->x; s.p[0][1] = a->y; s.p[0][2] = a->z;
    s.p[1][0] = b->x; s.p[1][1] = b->y; s.p[1][2] = b->z;
    s.rgb = rgb;
    s.fade = fade;
    s.width = width;
    s.view = view;
    s.ztest = ztest;
    l.sets++;
}

void EspDrawLaserLine(Vec from, Vec to, f32 width)
{
    set_line(&from, &to, 0xFF2010u, 12000.0f, width, 0, 1);
}

extern "C" {
// The shooting range's line (objWep.cpp): from p0 toward p1 in view matrix `mtx`, clipped to and faded over 8,000
// units; alpha byte 0xFE in `color` turns the depth test off. The end points are kept in view space.
void Draw_line3d_local_222(Vec* p0, Vec* p1, Mtx mtx, u32 color, int blend)
{
    (void) blend;
    Vec v[2];
    const Vec* p[2] = {p0, p1};
    for (int i = 0; i < 2; i++) {
        v[i].x = mtx[0][0] * p[i]->x + mtx[0][1] * p[i]->y + mtx[0][2] * p[i]->z + mtx[0][3];
        v[i].y = mtx[1][0] * p[i]->x + mtx[1][1] * p[i]->y + mtx[1][2] * p[i]->z + mtx[1][3];
        v[i].z = mtx[2][0] * p[i]->x + mtx[2][1] * p[i]->y + mtx[2][2] * p[i]->z + mtx[2][3];
    }
    set_line(&v[0], &v[1], color & 0xFFFFFFu, 8000.0f, 1.0f, 1, (color >> 24) != 0xFE);
}
void Draw_line3d_222(Vec* p0, Vec* p1, u32 color, int blend)
{
    Draw_line3d_local_222(p0, p1, eng_cam.view, color, blend);
}
// The dot on an enemy (objWep.cpp drawPoint: effect 0x50 at p1), scaled with the camera distance as the original:
// up to 3x (6x in rooms 22C / 228 and with Status_flg[3] 0x02000000). Debug_flg[3] 0x40 hides it.
void drawPoint(Vec* p0, Vec* p1)
{
    (void) p0;
    if (pG->Debug_flg[3] & 0x40) return;
    const float dx = pG->Cam.param.pos.x - p1->x, dy = pG->Cam.param.pos.y - p1->y, dz = pG->Cam.param.pos.z - p1->z;
    float size = sqrtf(dx * dx + dy * dy + dz * dz);
    if ((pG->Status_flg[3] & 0x02000000) || (pG->room_id32 & 0xFFFF0000) == 0x022C0000 ||
        (pG->room_id32 & 0xFFFF0000) == 0x02280000) {
        size = size * 0.00033333333f + 1.0f;
        if (size > 6.0f) size = 6.0f;
    } else {
        size = size * (1.0f / 8000.0f) + 0.8f;
        if (size > 3.0f) size = 3.0f;
    }
    E1Laser& l = e1_laser;
    l.dot_tick = e1_tick;
    l.dot[0] = p1->x; l.dot[1] = p1->y; l.dot[2] = p1->z;
    l.dot_r = 16.0f * size;   // the effect's base size (effect data, not hosted): 16 units
    l.dot_rgb = (pG->Status_flg[1] & 1) ? 0xFF4040u : 0xFF2010u;
    l.sets++;
}
}

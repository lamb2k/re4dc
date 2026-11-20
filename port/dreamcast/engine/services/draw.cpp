// E1 drawing glue (lane eng-e1): the C renderer (core/draw_e1.c) reads Leon's matrices in place from the actor table and
// the native skeleton's tables (lane eng-e1c). Lane eng-e1e: the camera (pG->Cam, the native camera service's look-at
// matrix and projection) and the HUD's live words are written in the renderer's form once a tick by the steps that
// produce them, and the characters' light records are kept by the light service below; the picture copies none of them.
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
void e1_draw_picture_c(const void* leon, const E1SkelView* leon_skel, unsigned identity,
                       uint32_t* wait_us, uint32_t* draw_us, const E1SkelView* partner, int world, const void* partner_record);
}
extern "C" int PlGetWeaponNo();

// A character's light inputs (lane eng-e1d), read from its model record in the actor table: the fields of the
// capture's ModelLight record (bench/r3_inputs.inc m1r3_snapshot_light, same bits), in its layout (17 words). The TEV
// scale (gxCsScale of the group: room light data, not hosted) is left 0 for the renderer to fill.
extern "C" int e1_light_record(const void* model, uint32_t* o)
{
    const cModel* m = (const cModel*) model;
    const cLightInfo& li = m->LightInfo;
    unsigned flags = ((m->be_flag & 0x8000) ? 1u : 0u) | ((m->be_flag & 8) ? 2u : 0u) | ((li.Flag & 4) ? 8u : 0u);
    if (m->pModelInfo && m->pModelInfo->pData && (m->pModelInfo->pData->flags & 0x40000000)) flags |= 4;
    o[0] = 0; o[1] = 0; o[2] = (uint32_t) (uintptr_t) m;
    o[3] = (unsigned) li.Flag | ((unsigned) (u8) li.PartsNo << 8) | ((unsigned) li.EnableMask << 16) | (flags << 24);
    o[4] = li.SelectMask;
    memcpy(o + 5, &li.Offset, 12);
    memcpy(o + 8, &li.Size, 12);
    o[11] = 0;
    if (m->pModelInfo) memcpy(o + 11, m->pModelInfo->color, 4);
    o[12] = (unsigned) m->TevScaleGroup;
    o[13] = (unsigned) m->AddAmb_r | ((unsigned) m->AddAmb_g << 8) | ((unsigned) m->AddAmb_b << 16);
    o[14] = o[15] = 0xFFFFFFFFu;
    o[16] = pG->Status_flg[1];
    return 1;
}

// ---- the light service's records (lane eng-e1e, E1 audit section 2) ----
// Each character but Leon (who keeps the pack's record) has its light record here, in the renderer's ModelLight layout
// with its TEV scale resolved: kept between pictures and rebuilt only when one of its inputs changes. Once a tick after
// the behaviour (e1_light_service_tick, inside the services row), each alive character's inputs (the light volume and
// masks of cModel::LightInfo, the be_flag bits, the material word and flag, the TEV group, the added ambient, the room
// status word) are compared with the ones its record was built from. The renderer reads the record in place
// (e1_light_rec_of). The TEV scale of a group is room light data the renderer resolves once from its pack
// (services/actor_e1.inc e1_light_tables -> e1_tev_scale_of_group).
#include "em.h"
extern "C" {
uint16_t e1_tev_scale_of_group[256];   // scale + 1, filled by the renderer at open (0: not resolved, 255 used)
uint32_t e1_light_checks, e1_light_builds;
// Controls (boot options, read at open): LIGHTCTL every record built with a black material, PALCTL the pass reads the
// palette with the old 12-float stride (services/actor_e1.inc), CAMSTALE the camera stream keeps the room's first
// camera: each must change the pictures. LIGHTSTALE (a record never rebuilt after its first build) shows what the
// rebuilds change (lanes/eng-e1e.md).
int e1_light_stale, e1_light_control, e1_pal_control, e1_cam_stale;   // LIGHTCTL: every record built with a black material
}
struct E1LightSlot { const cModel* m; uint32_t in[14]; uint32_t rec[17]; };
static E1LightSlot light_slot[16];
static unsigned light_slots;
static void light_inputs(const cModel* m, uint32_t* in)
{
    memcpy(in, &m->LightInfo.EnableMask, 32);   // EnableMask, Flag, PartsNo, x53, SelectMask, Offset, Size
    in[8] = m->be_flag & 0x8008u;
    in[9] = (m->pModelInfo && m->pModelInfo->pData) ? (m->pModelInfo->pData->flags & 0x40000000u) : 0;
    in[10] = 0;
    if (m->pModelInfo) memcpy(&in[10], m->pModelInfo->color, 4);
    in[11] = m->TevScaleGroup;
    in[12] = (unsigned) m->AddAmb_r | ((unsigned) m->AddAmb_g << 8) | ((unsigned) m->AddAmb_b << 16);
    in[13] = pG->Status_flg[1];
}
static void light_build(E1LightSlot& s)
{
    e1_light_record(s.m, s.rec);
    const unsigned group = s.rec[12] & 255;
    const unsigned v = e1_tev_scale_of_group[group];
    s.rec[12] = group | (v ? v - 1 : 255u) << 8;
    if (e1_light_control) s.rec[11] = 0;   // LIGHTCTL (control): the material colour black
    e1_light_builds++;
}
void e1_light_service_tick()
{
    for (cEm* p = EmMgr.pAlive; p; p = (cEm*) p->pNext) {
        if (p == (cEm*) pPL) continue;
        const cModel* m = p;
        unsigned i = 0;
        while (i < light_slots && light_slot[i].m != m) i++;
        uint32_t in[14];
        light_inputs(m, in);
        e1_light_checks++;
        if (i == light_slots) {
            if (light_slots == 16) { e1_stub_hit("light service: more than 16 characters", 0); continue; }
            light_slots++;
            light_slot[i].m = m;
        } else if (e1_light_stale || !memcmp(in, light_slot[i].in, sizeof in)) {   // LIGHTSTALE: never rebuilt
            continue;
        }
        memcpy(light_slot[i].in, in, sizeof in);
        light_build(light_slot[i]);
    }
}
// The record of a model (ModelLight layout, 17 words) or 0 when the service has none.
extern "C" const uint32_t* e1_light_rec_of(const void* model)
{
    for (unsigned i = 0; i < light_slots; i++)
        if (light_slot[i].m == (const cModel*) model) return light_slot[i].rec;
    return 0;
}
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

// ---- camera and HUD state in the renderer's form (lane eng-e1e, E1 audit section 2) ----
// The renderer's camera stream (26 words: view 3x4, projection type and six terms, viewport, far plane) and the HUD's
// four live words (life, life max, weapon, stance) are written in place by the tick steps that produce them: the camera
// right after the camera service's CameraMove (e1_camera_draw_tick, core/main.cpp), the HUD at the end of the tick
// (e1_hud_draw_tick). The constant words (projection type, viewport, far plane) are written once at open. The picture
// no longer repacks or copies either (draw_e1.c reads its streams as they are).
static float* draw_cam;        // the renderer's camera stream (0: headless)
static uint32_t* draw_hud;     // the HUD stream's four live words (0: none in the pack)
extern "C" float* e1_draw_cam_stream(void);
extern "C" uint32_t* e1_draw_hud_stream(void);
void e1_camera_draw_tick()
{
    if (!draw_cam || e1_cam_stale) return;
    const Camera& c = pG->Cam;
    memcpy(draw_cam, c.v_mat, 48);
    draw_cam[13] = c.ProjMat[0][0];
    draw_cam[14] = c.ProjMat[0][2];
    draw_cam[15] = c.ProjMat[1][1];
    draw_cam[16] = c.ProjMat[1][2];
    draw_cam[17] = c.ProjMat[2][2];
    draw_cam[18] = c.ProjMat[2][3];
}
void e1_hud_draw_tick()
{
    if (!draw_hud) return;
    draw_hud[0] = pG->pl_life;
    draw_hud[1] = pG->pl_life_max;
    draw_hud[2] = pG->weapon_no;
    draw_hud[3] = (uint32_t) PlGetWeaponNo();
}
static int diag;   // diagnostic boot options: DNOWORLD (no world drawn), DNOMARK (no partner drawn); read at open

void e1_draw_open()
{
    file_t f = fs_open("/cd/HEADLESS", O_RDONLY);
    if (f >= 0) { fs_close(f); headless = 1; e1_log("E1 draw: headless\n"); return; }
    if (!e1_draw_open_c(e1_scene == E1_SCENE_HILL ? "/cd/HILL.PAK" : "/cd/CROSS.PAK")) { headless = 1; e1_log("E1 draw: renderer refused the pack, headless\n"); return; }
    f = fs_open("/cd/DNOWORLD", O_RDONLY); if (f >= 0) { fs_close(f); diag |= 1; }
    f = fs_open("/cd/DNOMARK", O_RDONLY); if (f >= 0) { fs_close(f); diag |= 2; }
    draw_cam = e1_draw_cam_stream();
    draw_hud = e1_draw_hud_stream();
    f = fs_open("/cd/LIGHTSTALE", O_RDONLY); if (f >= 0) { fs_close(f); e1_light_stale = 1; e1_log("E1 LIGHTSTALE: light records never rebuilt (control)\n"); }
    f = fs_open("/cd/LIGHTCTL", O_RDONLY); if (f >= 0) { fs_close(f); e1_light_control = 1; e1_log("E1 LIGHTCTL: light records with a black material (control)\n"); }
    f = fs_open("/cd/PALCTL", O_RDONLY); if (f >= 0) { fs_close(f); e1_pal_control = 1; e1_log("E1 PALCTL: palette read with a 12-float stride (control)\n"); }
    draw_cam[12] = 0.0f;   // GX_PERSPECTIVE
    draw_cam[19] = 0.0f; draw_cam[20] = 0.0f; draw_cam[21] = 640.0f; draw_cam[22] = 480.0f; draw_cam[23] = 0.0f; draw_cam[24] = 1.0f;
    draw_cam[25] = ZFAR > 0.0f ? ZFAR : 18750.0f;
    e1_camera_draw_tick();   // the room's first camera (CameraRoomInit ran in room_init)
    f = fs_open("/cd/CAMSTALE", O_RDONLY); if (f >= 0) { fs_close(f); e1_cam_stale = 1; e1_log("E1 CAMSTALE: the first camera only (control)\n"); }
    e1_hud_draw_tick();
    e1_log("E1 draw: camera stream far %d, HUD words %s\n", (int) draw_cam[25], draw_hud ? "live" : "none");
}

void e1_draw_picture(E1Timing& tm)
{
    if (headless) { tm.draw_us = 0; return; }
    unsigned identity = (unsigned) pPL->id | ((unsigned) pPL->type << 8);
    uint32_t wait = 0, draw = 0;
    // lane eng-e1b: the partner's record; lane eng-e1d: each scene draws its own room's bake (DNOWORLD: none)
    E1SkelView leon, partner;
    const int have_leon = skel_view(pPL, &leon), have_partner = !(diag & 2) && skel_view(pSUB, &partner);
    e1_draw_picture_c(pPL, have_leon ? &leon : 0, identity, &wait, &draw, have_partner ? &partner : 0,
                      !(diag & 1), pSUB);
    tm.draw_us = draw;
    tm.pvr_us = wait;   // PVR readiness wait (the graphics chip, not CPU work)
}

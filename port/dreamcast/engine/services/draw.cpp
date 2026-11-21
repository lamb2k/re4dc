// E1 drawing glue (lane eng-e1): the C renderer (core/draw_e1.c) reads Leon's matrices in place from the actor table and
// the native skeleton's tables (lane eng-e1c). Lane eng-e1j (ruling H-016.2): nothing is converted into a draw record
// each tick. The camera is the camera service's record (services/camera/eng_camera.h), which the renderer reads in
// place; the HUD's life, weapon and stance are read in place from the game state; a character's light inputs are read
// in place from its model record by the light rule (render/source_light.inc, services/actor_e1.inc). The ammo digits
// are the HUD's own state, set once a tick (lane eng-e1i).
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
#include "camera/eng_camera.h"
#include <string.h>

extern "C" {
int e1_draw_open_c(const char* pack);
void e1_draw_picture_c(const void* leon, const E1SkelView* leon_skel, unsigned identity,
                       uint32_t* wait_us, uint32_t* draw_us, const E1SkelView* partner, int world, const void* partner_record);
}
extern "C" int PlGetWeaponNo();

// A character's light inputs (lane eng-e1d) in the capture's ModelLight layout (17 words; bench/r3_inputs.inc
// m1r3_snapshot_light, same bits). Used once a run, for the check of Leon's live inputs against the pack's record
// (services/actor_e1.inc e1_light_check); the characters are lit from their model records in place (below).
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

// ---- a character's light inputs, read in place (lane eng-e1j, ruling H-016.2) ----
// The light rule reads each input where the behaviour keeps it: the light volume and masks in cModel::LightInfo, the
// be_flag bits, the model data's flag word, the material colour, the TEV group, the added ambient, the room status
// word. Only addresses are gathered for a picture (as the skeleton's views); nothing is copied or compared. The
// behaviour writes these fields directly (em10's damage flash writes the material colour, parts show and hide by
// be_flag), so there is no setter to hang a record on: the record is the model itself.
#include "light_view.h"
#include <stddef.h>
extern "C" {
uint16_t e1_tev_scale_of_group[256];   // the TEV scale of each group + 1 (0 not resolved), resolved by the renderer at open
int e1_light_control, e1_pal_control;   // LIGHTCTL, PALCTL (controls, below)
extern int e1_light_miss_control;       // LIGHTMISS (control, lane eng-e1n): services/actor_e1.inc
}
extern "C" int e1_light_view(const void* model, E1LightView* v)
{
    static const uint8_t black[4] = {0, 0, 0, 0};
    const cModel* m = (const cModel*) model;
    if (!m) return 0;
    const cLightInfo& li = m->LightInfo;
    v->model = m;
    v->info = (const E1LightInfoIn*) &li.EnableMask;
    v->be_flag = (const uint32_t*) &m->be_flag;
    v->data_flags = m->pModelInfo && m->pModelInfo->pData ? (const uint32_t*) &m->pModelInfo->pData->flags : 0;
    v->color = m->pModelInfo && !e1_light_control ? (const uint8_t*) m->pModelInfo->color : black;   // LIGHTCTL: black
    v->tev_group = (const uint8_t*) &m->TevScaleGroup;
    v->addamb = (const uint8_t*) &m->AddAmb_r;
    v->status = (const uint32_t*) &pG->Status_flg[1];
    v->tev_table = e1_tev_scale_of_group;
    return 1;
}
static_assert(sizeof(((cLightInfo*) 0)->EnableMask) == 1 && sizeof(((cLightInfo*) 0)->Flag) == 1, "light view: EnableMask, Flag bytes");
static_assert(sizeof(((cModel*) 0)->be_flag) == 4, "light view: be_flag word");
static_assert(offsetof(cLightInfo, Flag) == offsetof(cLightInfo, EnableMask) + 1, "light view: Flag after EnableMask");
static_assert(offsetof(cLightInfo, PartsNo) == offsetof(cLightInfo, EnableMask) + 2, "light view: PartsNo");
static_assert(offsetof(cLightInfo, SelectMask) == offsetof(cLightInfo, EnableMask) + 4, "light view: SelectMask");
static_assert(offsetof(cLightInfo, Offset) == offsetof(cLightInfo, EnableMask) + 8, "light view: Offset");
static_assert(offsetof(cLightInfo, Size) == offsetof(cLightInfo, EnableMask) + 20, "light view: Size");
// (AddAmb_r, _g, _b are the bytes 0x139, 0x13A, 0x13B of cModel: model.h)
// Controls (boot options, read at open): LIGHTCTL every character lit with a black material, PALCTL the pass reads the
// palette with the old 12-float stride (services/actor_e1.inc), CAMSTALE the camera record keeps the first camera,
// PUBCOPY the camera service copies its record into a draw stream once a tick (counted: the selector must fail the
// scene). Each must change the pictures or the scene's verdict.
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

// ---- the HUD's live state (lane eng-e1j: the four words are read in place) ----
// The renderer reads the stance (the knife part) from the game state when it draws (e1_hud_stance), and the ammo count
// when it draws the digits (render/native_scene.h hud_magazine_live; lane eng-e1n, H-017.4: the renderer splits it into
// the three glyphs then, in the drawing row; nothing is made per tick). The count is the equipped weapon's loaded
// count, shown as cockpit.cpp BulletInfo::move / dispBulletDigit show it (guns only, not for pl_type 1). Not covered:
// the "EMPTY" sign for an empty gun with no spare rounds, and the no-weapon player states.
extern "C" {
extern int (*hud_magazine_live)(unsigned* n);
extern unsigned (*hud_stance_live)(void);   // render/native_actor.inc: the stance read when drawing (0: the pack's word)
}
static int hud_freeze;           // HUDFREEZE lab arm (control): the count the HUD shows is the one at open
static unsigned hud_frozen_count;
#include "item.h"
static int e1_gun_shows_count(unsigned no)
{
    if (pG->pl_type == 1) return 0;
    switch (no) {
    case 1: case 2: case 3: case 4: case 5: case 6: case 7: case 8: case 9: case 0xA: case 0xB: case 0xC: case 0xD:
    case 0xE: case 0xF: case 0x11: case 0x13: case 0x16: case 0x17: case 0x19: case 0x1C: case 0x1D: case 0x1F:
    case 0x20: case 0x21:
        return 1;
    }
    return 0;
}
extern "C" unsigned e1_hud_magazine(void) { return ItemMgr.bulletNum(); }
static unsigned e1_hud_stance(void) { return (unsigned) PlGetWeaponNo(); }
// the count the HUD shows, read when the renderer draws the digits: 1 when the equipped weapon shows it
static int e1_hud_magazine_live(unsigned* n)
{
    *n = hud_freeze ? hud_frozen_count : ItemMgr.bulletNum();
    return e1_gun_shows_count(pG->weapon_no);
}
// lane eng-look1: Leon's weapons (services/weapon.cpp): the run's trace choice before play, the record after each picture
void e1_weapon_boot();
void e1_weapon_picture_end(unsigned tick);
static int diag;   // diagnostic boot options: DNOWORLD (no world drawn), DNOMARK (no partner drawn); read at open

static int boot_file(const char* name)
{
    file_t f = fs_open(name, O_RDONLY);
    if (f < 0) return 0;
    fs_close(f);
    return 1;
}

void e1_draw_open()
{
    if (boot_file("/cd/HEADLESS")) { headless = 1; e1_log("E1 draw: headless\n"); return; }
    if (!e1_draw_open_c(e1_scene == E1_SCENE_HILL ? "/cd/HILL.PAK" : "/cd/CROSS.PAK")) { headless = 1; e1_log("E1 draw: renderer refused the pack, headless\n"); return; }
    if (boot_file("/cd/DNOWORLD")) diag |= 1;
    if (boot_file("/cd/DNOMARK")) diag |= 2;
    if (boot_file("/cd/LIGHTCTL")) { e1_light_control = 1; e1_log("E1 LIGHTCTL: characters lit with a black material (control)\n"); }
    if (boot_file("/cd/PALCTL")) { e1_pal_control = 1; e1_log("E1 PALCTL: palette read with a 12-float stride (control)\n"); }
    if (boot_file("/cd/CAMSTALE")) { eng_cam.frozen = 1; e1_log("E1 CAMSTALE: the camera record keeps its next camera (control)\n"); }
    if (boot_file("/cd/PUBCOPY")) { eng_pub_copy = 1; e1_log("E1 PUBCOPY: the camera record copied once a tick (control)\n"); }
    e1_light_miss_control = e1_lab.lightmiss;   // LIGHTMISS (control; its boot file read by e1_lab_boot, core/frame.cpp)
    hud_stance_live = e1_hud_stance;
    hud_magazine_live = e1_hud_magazine_live;
    if (e1_lab.hudfreeze) {   // HUDFREEZE (control; its boot file read by e1_lab_boot, core/frame.cpp)
        hud_freeze = 1;
        hud_frozen_count = ItemMgr.bulletNum();
        e1_log("E1 HUDFREEZE: the HUD's ammo count frozen at %u (control)\n", hud_frozen_count);
    }
    e1_log("E1 draw: camera from the camera service's record (far %d), HUD read in place\n", (int) eng_cam.zfar);
    e1_weapon_boot();
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
    e1_weapon_picture_end(e1_tick);   // lane eng-look1: the weapon's record, after the drawing span
}

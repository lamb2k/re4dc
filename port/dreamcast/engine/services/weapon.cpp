// weapon.cpp (lane eng-look1): Leon's weapon objects for the renderer, and the weapon's record (E1 WEP lines).
//
// The cause this answers (docs/engine/lanes/eng-look1.md): the engine drew no live weapon at all. The pistol seen in the
// village's first pictures was a static copy of the weapon in the room's PS2 world package (placement 209 of
// dc/native/r101/ps2-world.r4pw: the old port's STATIC_OBJ_BAKE baked the held cObjRuger, kind 1 id 0x21, at Leon's
// warp-start pose), drawn every picture where Leon's hand was at tick 1. The old port draws the weapon live through the
// original model pass and that copy only while the gun's matrices equal the baked pose (origin/t15/int
// game/model_bridge.cpp sobake, PS2_PLACE_GATE). The engine now draws the weapon object itself, through the E1 actor
// pass (services/weapon_draw.inc), and retires the world copy when the pack opens.
//
// What is read here, each picture, in place: the player's two weapon display objects (cPlWep::m_pWep, pObj2), each
// one's be_flag and the room status word (the hosted draw gate, weapon_view.h), its model data's address (which
// archive slot it is: the catalogue entry the bake tagged), its native skeleton table (pointers), and the bone of
// Leon's table its root hangs on. Nothing is converted or copied: the renderer reads the object and its table.
#include "global.h"
#include "player.h"
#include "pl_wep.h"
#include "model.h"
#include "e1_core.h"
#include "e1_engine.h"
#include "e1_kos.h"
#include "skel.h"
#include "weapon_view.h"
#include <stdio.h>
#include <string.h>

extern "C" {
int e1_weapon_off;                   // NOWEP (control; read by the renderer at open, services/weapon_draw.inc)
unsigned e1_weapon_world_retired;    // world copies retired at pack open (services/weapon_draw.inc)
}

// The weapon archive the engine loads (core/loader.cpp ReadWepData: weapons 2 and 3, em/wep02; any other weapon is
// refused there and logged as an unhosted stub): read.cpp wep_data_leon's file slot 2.
static const unsigned kFileSlot = 2;

// The original's model pass draws a model only with be_flag bits 1, 2 and 4, and in an event only with 0x800
// (src/game/trans.cpp ModelTrans and commonScreenMat); cObjWep::move keeps bit 2 (src/game/objWep.cpp).
static unsigned hosted_gate(const cModel* m)
{
    const u32 f = m->be_flag;
    if ((pG->Status_flg[1] & 0x10000000) && !(f & 0x800)) return 0;
    return (f & 7) == 7;
}

// PL_ARC_PTR's slot of the model's data in the loaded weapon archive (src/include/global.h PlArc: word k of the archive
// body is slot k's offset; words 4 .. 4 + n - 1 are the entries), -1 when the data is not one of them.
static int arc_slot_of(const cModel* m)
{
    const uint8_t* arc = (const uint8_t*) pG->pWep;
    if (!arc || !m->pModelInfo || !m->pModelInfo->pData) return -1;
    const uint32_t* w = (const uint32_t*) arc;
    const unsigned n = w[0];
    if (n > 0xFB) return -1;
    for (unsigned k = 4; k < 4 + n; k++)
        if (arc + w[k] == (const uint8_t*) m->pModelInfo->pData) return (int) k;
    return -1;
}

// this picture (the renderer's views and answers), the run's sums, and the trace's run-length record
static unsigned pic_present, pic_visible, pic_drawn, pic_onscreen, pic_hidden_drawn, pic_unmapped;
static int pic_bone = -1, pic_slot = -1;
static unsigned pic_vis[E1_WEAPON_MAX], pic_views;
static unsigned n_pictures, n_present, n_visible, n_drawn, n_onscreen, n_hidden_drawn, n_unmapped, n_lines;
static int tracing = -1;   // the run is traced (no NOTRACE boot file): the E1 WEP lines go to the trace
static uint32_t last_key = 0xFFFFFFFFu;

// Before play (services/draw.cpp e1_draw_open): is the run traced. A boot file read before the first picture (no file is
// opened in play: core/play_files.c).
void e1_weapon_boot()
{
    file_t f = fs_open("/cd/NOTRACE", O_RDONLY);
    tracing = f < 0;
    if (f >= 0) fs_close(f);
}

extern "C" unsigned e1_weapon_views(E1WeaponView* out, unsigned max)
{
    pic_present = pic_visible = pic_drawn = pic_onscreen = pic_hidden_drawn = pic_unmapped = 0;
    pic_bone = pic_slot = -1;
    pic_views = 0;
    if (!pPL || !pPL->Wep) return 0;
    cObjWep* const objs[E1_WEAPON_MAX] = {pPL->Wep->m_pWep, pPL->Wep->pObj2};
    SkelTable* const leon = skel_table_of(pPL);
    unsigned n = 0;
    for (unsigned k = 0; k < E1_WEAPON_MAX && n < max && n < E1_WEAPON_MAX; k++) {
        const cModel* m = (const cModel*) objs[k];
        if (!m) continue;
        E1WeaponView& v = out[n];
        v.model = m;
        v.file_slot = kFileSlot;
        v.arc_slot = arc_slot_of(m);
        v.visible = hosted_gate(m);
        const SkelTable* t = skel_table_of(m);
        v.has_skel = t != 0;
        v.parent_bone = -1;
        if (t) {
            v.skel.world = &t->world[0].m[0][0];
            v.skel.pal = &t->pal[0].m[0][0];
            v.skel.bind[0] = t->soa + SK_BX * t->cap;
            v.skel.bind[1] = t->soa + SK_BY * t->cap;
            v.skel.bind[2] = t->soa + SK_BZ * t->cap;
            v.skel.n = t->n;
            if (leon && t->extParent) v.parent_bone = skel_record_bone(leon, t->extParent);
        } else {
            memset(&v.skel, 0, sizeof(v.skel));
        }
        pic_present++;
        pic_visible += v.visible;
        pic_vis[n] = v.visible;
        if (n == 0) { pic_bone = v.parent_bone; pic_slot = v.arc_slot; }
        n++;
    }
    pic_views = n;
    return n;
}

extern "C" void e1_weapon_note(unsigned i, unsigned drawn, unsigned on_screen)
{
    if (i >= pic_views) return;
    if (drawn) { pic_drawn++; if (!pic_vis[i]) pic_hidden_drawn++; }
    else if (pic_vis[i]) pic_unmapped++;
    pic_onscreen += on_screen != 0;
}

// After each drawn picture (services/draw.cpp): the run's sums, and in a traced run the tick's decision. The record is
// run-length: an "E1 WEP t=" line is written at the first tick and whenever any of its fields changes, and holds until
// the next one (the trace buffer goes to the report before the rows, so one line a tick would crowd them out).
void e1_weapon_picture_end(unsigned tick)
{
    n_pictures++;
    n_present += pic_present; n_visible += pic_visible; n_drawn += pic_drawn; n_onscreen += pic_onscreen;
    n_hidden_drawn += pic_hidden_drawn; n_unmapped += pic_unmapped;
    if (tracing <= 0) return;
    const uint32_t key = pic_present | pic_visible << 4 | pic_drawn << 8 | pic_onscreen << 12 |
                         (uint32_t) (pic_bone & 0xFF) << 16 | (uint32_t) (pic_slot & 0xFF) << 24;
    if (key == last_key) return;
    last_key = key;
    char line[160];
    const int k = snprintf(line, sizeof(line), "E1 WEP t=%u present %u bone %d visible %u drawn %u on-screen %u slot %d\n",
                           tick, pic_present, pic_bone, pic_visible, pic_drawn, pic_onscreen, pic_slot);
    if (k > 0) e1_trace_put(line, (unsigned) k < sizeof(line) ? (unsigned) k : sizeof(line) - 1);
    n_lines++;
}

// The run's line (host/e1_svc_mem.cpp, beside E1 PUB): the selector fails an e1 scene whose weapon was not drawn every
// picture the hosted code said it is drawn (visible != drawn), or drawn when it said not (drawn-hidden), or without the
// line. Pictures counts the drawn pictures (a headless image draws none: all zero).
void e1_weapon_report()
{
    e1_log("E1 WEP pictures %u present %u visible %u drawn %u drawn-hidden %u not-drawable %u on-screen %u "
           "world-copies-retired %u trace-lines %u control %u\n", n_pictures, n_present, n_visible, n_drawn,
           n_hidden_drawn, n_unmapped, n_onscreen, e1_weapon_world_retired, n_lines, (unsigned) e1_weapon_off);
}

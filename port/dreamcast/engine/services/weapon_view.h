/* weapon_view.h (lane eng-look1): Leon's weapon objects as the renderer draws them. C and C++.

   The weapon is a hosted object (cObjWep, made by the weapon archive's module: em/wep02 for the handguns) whose model
   hangs on Leon's hand (its root part's parent is Leon's part 10, src/wep/objRuger.cpp init). The hosted code decides
   each tick whether it is drawn: cObjWep::move sets or clears be_flag bit 2 from its three display types and the
   parent's own drawing (src/game/objWep.cpp), and the original's model pass (ModelTrans, src/game/trans.cpp) draws a
   model only with be_flag bits 1, 2 and 4 set, and in an event only with 0x800. That gate is `visible` below.

   Nothing is copied: a view holds the object's address (its light inputs are read in place, services/light_view.h)
   and its native skeleton table's pointers (the palette the actor pass skins with), gathered for the picture as
   Leon's own view is (services/draw.cpp skel_view). The renderer draws a visible view through the E1 actor pass with
   the catalogue model the pack holds for the weapon's model (bake/weapon_model.py tags it with its archive slot). */
#ifndef E1_WEAPON_VIEW_H
#define E1_WEAPON_VIEW_H
#include "e1_skel_view.h"
#ifdef __cplusplus
extern "C" {
#endif
#define E1_WEAPON_MAX 2   /* cPlWep::m_pWep and pObj2 (src/include/pl_wep.h) */
typedef struct {
    const void* model;        /* the cObjWep (a cModel): its light inputs and its coordinate matrix, read in place */
    E1SkelView skel;          /* its native skeleton table (pointers only) */
    unsigned file_slot;       /* the weapon archive (read.cpp wep_data_leon: 2 = em/wep02) */
    int arc_slot;             /* the archive slot of its model data (PL_ARC_PTR), -1 when not found */
    int parent_bone;          /* the bone of Leon's table its root hangs on, -1 when none */
    unsigned visible;         /* the hosted gate above, this tick */
    unsigned has_skel;
} E1WeaponView;
/* The player's weapon objects this picture (services/weapon.cpp): the count of views filled (present objects). */
unsigned e1_weapon_views(E1WeaponView* out, unsigned max);
/* The renderer's answer for view i of this picture: it took the weapon into the actor pass (drawn), and the weapon's
   projected box touched the screen (on_screen). */
void e1_weapon_note(unsigned i, unsigned drawn, unsigned on_screen);
/* NOWEP (boot file, the check's control): the renderer leaves every weapon undrawn. Read at the renderer's open. */
extern int e1_weapon_off;
/* World placements retired at pack open because they are a static copy of a weapon object (render side). */
extern unsigned e1_weapon_world_retired;
#ifdef __cplusplus
}
#endif
#endif

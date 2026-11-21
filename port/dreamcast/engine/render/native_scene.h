#pragma once
#include "replay.h"
#include "native_world.h"
typedef struct { Scene assets; float sky_top,sky_bottom; NativeWorld world; Table models,frames,delta[9]; uint32_t *state[9]; unsigned words[9]; void* runtime; NativeVis vis; void* vis_data; } NativeScene;
int native_open(NativeScene*,const char*);
void native_close(NativeScene*);
/* lane eng-draw2 (step 0, the stills made repeatable): a still must show its own picture. pvr_wait_render_done returns
   at once while the picture's render has not started (KOS starts it only after the previous picture is flipped), so a
   still could show the picture before it. native_flip_mark: every scene finished so far is shown (call when settled);
   native_scene_done after each pvr_scene_finish; native_wait_shown waits, field by field, until the chip has flipped
   to every finished scene (at most 120 fields; 0 when it never did). */
void native_flip_mark(void);
void native_scene_done(void);
int native_wait_shown(void);
void native_reserve(const char* const* names,unsigned n);
extern unsigned native_release_keep;   /* control: native_release keeps one texture in video memory */
void native_reset(NativeScene*);
void native_update(NativeScene*,unsigned);
int native_prepare_world(const NativeWorld*,const float*,unsigned);
void native_world_pass(Scene*,const NativeWorld*,const float*,unsigned);
void native_actor_pass(NativeScene*,unsigned);
void native_effects(NativeScene*);
void native_hud(NativeScene*);
/* lane eng-e1i, eng-e1n (H-017.4): the ammo digits are made by the renderer when it draws the HUD, from the live
   magazine count. hud_magazine_live (the E1 images set it: services/draw.cpp) returns 1 when the equipped weapon shows
   its count (cockpit.cpp dispBulletDigit's list) and puts the count in *n; native_hud splits it into ones, tens and
   hundreds (the hundreds only when not 0, as BulletInfo::move) for that picture. Nothing is made per tick.
   hud_magazine_live 0 (the bench): the pack's own digit pictures. hud_ammo_drawn: the digit each cell drew in the last
   picture (0xff none). */
extern int (*hud_magazine_live)(unsigned* n);
extern uint8_t hud_ammo_drawn[3];
extern int hud_blend_control;
void native_shadows(NativeScene*);
void native_sky(NativeScene*);
void native_select_arm(unsigned);
int native_actor_open(NativeScene*);
void native_actor_close(NativeScene*);

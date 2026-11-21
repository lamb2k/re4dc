#pragma once
#include "replay.h"
#include "native_world.h"
typedef struct { Scene assets; float sky_top,sky_bottom; NativeWorld world; Table models,frames,delta[9]; uint32_t *state[9]; unsigned words[9]; void* runtime; NativeVis vis; void* vis_data; } NativeScene;
int native_open(NativeScene*,const char*);
void native_close(NativeScene*);
void native_reset(NativeScene*);
void native_update(NativeScene*,unsigned);
int native_prepare_world(const NativeWorld*,const float*,unsigned);
void native_world_pass(Scene*,const NativeWorld*,const float*,unsigned);
void native_actor_pass(NativeScene*,unsigned);
void native_effects(NativeScene*);
void native_hud(NativeScene*);
/* lane eng-e1i: the ammo digits' live state. The E1 images point hud_ammo at theirs and write it once a tick
   (services/draw.cpp e1_hud_draw_tick: the magazine split as cockpit.cpp BulletInfo::move splits it); the renderer
   reads it in place. digit[0] ones, [1] tens, [2] hundreds; shown bit k: cell k drawn. hud_ammo 0 (the bench): the
   pack's own digit pictures. hud_ammo_drawn: the digit each cell drew in the last picture (0xff none). */
typedef struct { uint32_t tick; uint8_t digit[3]; uint8_t shown; } HudAmmo;
extern HudAmmo* hud_ammo;
extern uint8_t hud_ammo_drawn[3];
extern int hud_blend_control;
void native_shadows(NativeScene*);
void native_sky(NativeScene*);
void native_select_arm(unsigned);
int native_actor_open(NativeScene*);
void native_actor_close(NativeScene*);

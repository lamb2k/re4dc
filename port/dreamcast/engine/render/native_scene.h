#pragma once
#include "replay.h"
#include "native_world.h"
typedef struct { Scene assets; float sky_top,sky_bottom; NativeWorld world; Table models,frames,delta[8]; uint32_t *state[8]; unsigned words[8]; void* runtime; NativeVis vis; void* vis_data; } NativeScene;
int native_open(NativeScene*,const char*);
void native_close(NativeScene*);
void native_update(NativeScene*,unsigned);
int native_prepare_world(const NativeWorld*,const float*,unsigned);
void native_world_pass(Scene*,const NativeWorld*,const float*,unsigned);
void native_actor_pass(NativeScene*,unsigned);
void native_effects(NativeScene*);
void native_hud(NativeScene*);
void native_shadows(NativeScene*);
void native_sky(NativeScene*);
int native_actor_open(NativeScene*);
void native_actor_close(NativeScene*);

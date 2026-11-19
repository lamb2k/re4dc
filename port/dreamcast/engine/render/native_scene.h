#pragma once
#include "replay.h"
#include "native_world.h"
typedef struct { Scene assets; NativeWorld world; Table frames,delta[8]; uint32_t *state[8]; unsigned words[8]; } NativeScene;
int native_open(NativeScene*,const char*);
void native_close(NativeScene*);
void native_update(NativeScene*,unsigned);
int native_prepare_world(const NativeWorld*,const float*,unsigned);
void native_world_pass(Scene*,const NativeWorld*,const float*,unsigned);

#pragma once
#ifndef RE4DC_ACTOR_VISIBILITY23
#define RE4DC_ACTOR_VISIBILITY23 0
#endif
#if RE4DC_ACTOR_VISIBILITY23
#include <sh4zam/shz_bounds.h>
extern "C" {
struct Re4dcActorVisibility23Stats {
 unsigned queries,material_draw,identity_draw,cache_hits,cache_misses,source_records,capacity_draw,
 numeric_draw,bounded_sections,bounded_records,wall_tests,hidden_sections,potential_records,positions_avoided,triangles_avoided,bound_groups,resets,world_receipt_ready,world_receipt_draw,metadata_checks,metadata_bytes;
};
extern unsigned re4dc_actor_visibility23_mode; // 0=off,1=census,2=reject; boot0
const Re4dcActorVisibility23Stats* re4dc_actor_visibility23_stats();
void re4dc_actor_visibility23_reset();
int re4dc_actor_visibility23_receipt(int ready);
int re4dc_actor_visibility23_set(unsigned mode);
// Actual owner workspace binds (also reachable from crowd Trans notes).
// Counters describe preceding bind; these are not guaranteed drawn frames.
void re4dc_actor_visibility23_metadata_check(unsigned bytes);
int re4dc_actor_world23_context(unsigned room);
void re4dc_actor_visibility23_bind(unsigned render,unsigned funded,unsigned transformed);
void re4dc_actor_visibility23_frame(unsigned render,unsigned open,unsigned mask,unsigned transformed);
unsigned re4dc_actor_visibility23_view(float view[12],const void* model,const void* info);
int re4dc_actor_visibility23_wall(const void* model,const float view[12],const float projection[7],const float viewport[6],const float lo[3],const float hi[3]);
}
namespace actor_visibility23 {
struct Group { short lo[3],hi[3];unsigned short palette; };
struct Key {
 const void *positions,*blob,*records; unsigned epoch,position_count,stream_bytes;
 unsigned short meshlet,vertices;unsigned char stride,record_words;
};
const Group* acquire(const Key&,unsigned* count);
bool opaque_world_error(const float view[12],const float projection[7],const float viewport[6],float near,const float absolute_operands[3],float maximum);
bool camera_bounds(const Group*,unsigned,const float* palette,unsigned entries,float q,const float modelview[12],const float view[12],const float projection[7],const float viewport[6],float near,float far,float lo[3],float hi[3]);
}
#endif

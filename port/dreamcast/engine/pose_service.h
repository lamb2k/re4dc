/* Phase 1B pose primitives. Source controllers own clocks, events and root movement.
 * No draw dependency, global actor cache, allocator, or fixed skeleton size.
 * EDCL v1 sampling is derived from edemo_engine.c / bake_clips.py. */
#ifndef RE4DC_POSE_SERVICE_H
#define RE4DC_POSE_SERVICE_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef struct { float q[4], t[3], s[3]; } re4ps_local;
/* Row-major affine matrices, matching the game's existing Mtx interface. */
typedef struct { float m[12]; } re4ps_matrix;
typedef struct {
    const uint8_t *rotation, *translation, *scale;
    float translation_scale;
    uint16_t rotation_keys, translation_keys;
    uint8_t rotation_shift, translation_shift, translation_mode;
} re4ps_track;
typedef struct {
    uint32_t bone_count;
    const int32_t *parent; /* parent before child, -1 for a root */
    const float *rest_translation; /* 3 * bone_count floats */
} re4ps_skeleton;
typedef struct {
    uint32_t bone_count, frames;
    const re4ps_track *tracks; /* caller-owned, immutable after open */
    const uint8_t *root_track;
    float root_scale;
} re4ps_clip;
typedef struct {
    const re4ps_clip *clip;
    float frame, weight;
    const uint8_t *bone_mask; /* NULL: all; nonzero: override this bone */
} re4ps_layer;
typedef struct {
    uint32_t destination, source;
} re4ps_dependency; /* requested destination also requires source (IK/blends etc.) */

enum { RE4PS_OK = 0, RE4PS_ARGUMENT = -1, RE4PS_FORMAT = -2,
       RE4PS_CAPACITY = -3, RE4PS_HIERARCHY = -4, RE4PS_NUMERIC = -5 };

int re4ps_validate_skeleton(const re4ps_skeleton *skeleton);
/* Validate the whole EDCL table, locate a clip, then build bounded track views.
 * No game asset bytes are copied. Input and track storage outlive the clip.
 * v1's 8-bit on-disc count is a format limit, not a service/actor limit. */
int re4ps_open_edcl(re4ps_clip *out, re4ps_track *tracks, size_t capacity,
                   const void *data, size_t bytes, uint16_t entry,
                   const re4ps_skeleton *skeleton);
/* Close over parents AND explicit procedural/blend dependencies. NULL requested
 * means full pose. Caller stores the plan per topology/action, not per frame. */
int re4ps_required(const re4ps_skeleton *skeleton, const uint8_t *requested,
                   const re4ps_dependency *dependencies, size_t dependency_count,
                   uint8_t *required, size_t capacity);
/* Sample required locals only. Other output elements are untouched. No clocks,
 * root movement, events, floor IK or source blend tables are executed here. */
int re4ps_sample(const re4ps_skeleton *skeleton, const re4ps_clip *clip, float frame,
                 const uint8_t *required, re4ps_local *out, size_t capacity);
/* Ordered masked override layers. Additive/source-specific blends remain with
 * the source adapter until separately qualified; they must never be ignored. */
int re4ps_layers(const re4ps_skeleton *skeleton, const re4ps_layer *layers,
                 size_t count, const uint8_t *required,
                 re4ps_local *out, size_t capacity);
/* Procedural local edits can be made between sample/layers and compose. World
 * procedural solvers can compose, adjust locals, then compose affected closure.
 * required must contain every parent. Multiple roots/parts are supported.
 * This is ordinary affine composition, not the game's nonuniform-scale
 * cancellation or addRot pass. Those source behaviors require an adapter;
 * calling this function alone does not reproduce MotionMove. */
int re4ps_compose(const re4ps_skeleton *skeleton, const re4ps_local *local,
                  const uint8_t *required, const re4ps_matrix *root,
                  re4ps_matrix *out, size_t capacity);

#ifdef __cplusplus
}
#endif
#endif

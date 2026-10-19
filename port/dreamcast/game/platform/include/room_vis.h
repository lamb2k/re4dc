/* room_vis.h: ENEMY_VIS_CULL (=1 platform/room_occl.c OCCL occluders; =2 platform/room_vis.c VIS v2, not shipped;
 * lane engine19; render only). near / far: the next Render's near plane and the far it culls the world at. */
#ifndef ROOM_VIS_H
#define ROOM_VIS_H
#ifdef __cplusplus
extern "C" {
#endif
void re4dc_room_vis_enter(unsigned room);   /* after re4dc_room_file_enter */
void re4dc_room_vis_leave(void);
int re4dc_room_vis_active(void);            /* 1 while this room's VIS section is loaded */
/* 1 when the room's world hides the world box lo..hi from the camera of the world-to-view affine `view` (3x4 rows,
 * the Trans camera pG->Cam.v_mat); 0 otherwise (no VIS, eye outside its cells, box outside the bands / range, a sight
 * line possibly open, or the PS2 world not as compiled this frame). */
int re4dc_room_vis_hidden(const float* view, float near, float far, const float lo[3], const float hi[3]);
#ifdef __cplusplus
}
#endif
#endif

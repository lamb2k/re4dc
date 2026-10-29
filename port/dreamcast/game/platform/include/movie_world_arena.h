// D38: private retained world-cell movie ownership, never a general heap.
#pragma once
#ifndef RE4DC_MOVIE_WORLD_ARENA
#define RE4DC_MOVIE_WORLD_ARENA 0
#endif
#if RE4DC_MOVIE_WORLD_ARENA || RE4DC_CABIN_SOURCE
#ifdef __cplusplus
extern "C" {
#endif
int re4dc_movie_world_before_heap_change(const void* start, unsigned bytes);
int re4dc_ui_movie_try_close(void);
#ifdef __cplusplus
}
#endif
#endif
#if RE4DC_MOVIE_WORLD_ARENA
#ifdef __cplusplus
extern "C" {
#endif
int re4dc_room4_cell_valid(const void*, unsigned bytes, unsigned generation);
int re4dc_room4_live_generation(unsigned* generation);
int re4dc_ui_movie_handoff_ready(void);
void re4dc_ps2_world_movie_discard(void);
int re4dc_ps2_mesh_movie_blocked(void);
unsigned re4dc_ps2_mesh_movie_borrow(unsigned id);
int re4dc_ps2_mesh_movie_valid(unsigned token);
void* re4dc_ps2_mesh_movie_alloc(unsigned token, unsigned bytes);
int re4dc_ps2_mesh_movie_free(unsigned token, void* p);
int re4dc_ps2_mesh_movie_return(unsigned token, int retiring);
void re4dc_movie_world_scope(unsigned id);
int re4dc_movie_world_before_room_retire(void);
void* re4dc_movie_world_sep_alloc(unsigned bytes);
int re4dc_movie_world_sep_free(void* p);
int re4dc_movie_world_active(void);
#ifdef __cplusplus
}
#endif
#endif
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
#ifdef __cplusplus
extern "C" {
#endif
unsigned re4dc_room4_cell_incarnation(const void*, unsigned bytes, unsigned generation);
#ifdef __cplusplus
}
#endif
#endif

/* room_file.h: the per-room data file (R4RC v1, platform/room_file.c; lane engine19). */
#ifndef ROOM_FILE_H
#define ROOM_FILE_H
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { unsigned short w, h; unsigned cell_mm; float x0, z0; } re4dc_room_header;   /* the shared lattice */
/* room lifecycle (ui_bridge.cpp): room = (stage << 8) | room; enter reads the sections this program uses */
void re4dc_room_file_enter(unsigned room);
void re4dc_room_file_leave(void);
/* a loaded section (16 B aligned in heap 4, valid until the room leave), or 0 */
const void* re4dc_room_section(const char tag[4], unsigned* len, unsigned* version, unsigned* flags,
                               const re4dc_room_header** hdr);
unsigned re4dc_room_file_room(void);
/* the loaded sections' heap-4 block (a room-4 cell, for movie-arena validity checks), or 0; built with ROOMFILE_SCDD */
const void* re4dc_room_file_block(void);
#ifdef __cplusplus
}
#endif
#endif

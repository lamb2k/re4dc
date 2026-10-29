#ifndef RE4DC_FRONTEND_TPL_OWNER34_H
#define RE4DC_FRONTEND_TPL_OWNER34_H

// FRONT_TPL_OWNER=1: exact native room/SMD lifetime and TPL-write publication.
// The frontend retains its full descriptor comparison for every unqualified pair.
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
extern "C" void re4dc_front_tpl_bind_room(const void* room, unsigned bytes);
extern "C" void re4dc_front_tpl_retire_room();
extern "C" void re4dc_front_tpl_smd_begin(const void* smd, const void* common);
extern "C" void re4dc_front_tpl_smd_clear();
extern "C" void re4dc_front_tpl_smd_publish(const void* info, const void* zero_tpl,
                                              const void* smd, const void* common);
extern "C" void re4dc_front_tpl_smd_slide(const void* smd);
extern "C" void re4dc_front_tpl_info_changed(const void* info);
// Structural TPL relocation/remap revokes the certified generation. Header
// notification below is solely for the exact wrapS/T writes in trans.cpp.
extern "C" void re4dc_front_tpl_palette_changed(const void* tpl);
extern "C" void re4dc_front_tpl_header_changed(const void* header);
#endif

#endif

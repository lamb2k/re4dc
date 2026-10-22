#pragma once
// Private CABIN_SOURCE adapters. The recovered source sound engine owns IDs,
// readiness, playback clocks and retirement; these hooks own output tagging.
#if defined(RE4DC_CABIN_SOURCE) && RE4DC_CABIN_SOURCE
extern "C" {
#if defined(RE4DC_EVD_ARAM_ALLOC_RETRY) && RE4DC_EVD_ARAM_ALLOC_RETRY
// Read-only exact immutable-preload epoch; zero means no accepted receipt.
unsigned re4dc_cabin_carrier_preload_epoch(const void* unit,unsigned logical,unsigned bytes);
#endif
int re4dc_cabin_preflight(unsigned costume);
int re4dc_cabin_begin(unsigned id,const void* heap,unsigned heap_bytes,const void* room,unsigned room_bytes);
void re4dc_cabin_event_bound(const void* event,const char* key);
void re4dc_cabin_cancel_accepted(const void* event);
void re4dc_cabin_death_committed(const void* event);
void re4dc_cabin_event_deleted(const void* event);
void re4dc_cabin_before_events();
void re4dc_cabin_after_events();
void re4dc_cabin_source_done(unsigned id,int keep);
int re4dc_cabin_aftermath(unsigned id);
int re4dc_cabin_before_heap_change(const void* start,unsigned bytes);
int re4dc_movie_cabin_available(unsigned id);
int re4dc_movie_stream_cabin_alloc(void*(*callback)(int,int,int*),unsigned bytes);
int re4dc_movie_stream_cabin_start(int handle,unsigned generation);
int re4dc_movie_stream_cabin_progress(int handle,unsigned generation,int final_pcm);
unsigned re4dc_ui_movie_cabin_generation();
unsigned re4dc_ui_movie_cabin_upload();
unsigned re4dc_ui_movie_cabin_shown();
int re4dc_ui_movie_cabin_try_close(unsigned generation);
#if RE4DC_CABIN_COMPLETE_HANDOFF
int re4dc_cabin_complete_current(unsigned generation,unsigned id);
int re4dc_movie_cabin_complete_current(unsigned generation);
int re4dc_ui_movie_cabin_complete(unsigned generation,const void* texture,unsigned final_upload,unsigned movie_generation);
int re4dc_movie_cabin_complete(unsigned generation);
#endif
unsigned re4dc_movie_cabin_open(unsigned id);
int re4dc_movie_cabin_skip(unsigned generation);
int re4dc_movie_cabin_step(unsigned generation);
int re4dc_movie_cabin_status(unsigned generation);
int re4dc_movie_cabin_close(unsigned generation);
int re4dc_movie_cabin_abort(unsigned generation);
unsigned re4dc_cabin_audio_owner_open(const void* event, unsigned movie_id);
int re4dc_cabin_audio_owner_close(unsigned generation);
unsigned re4dc_cabin_audio_error(unsigned generation);
unsigned re4dc_cabin_audio_request_begin(const void* event, const char* event_key,
                                        int block, int number);
void re4dc_cabin_audio_request_end(unsigned token);
unsigned re4dc_cabin_audio_prepare_begin(unsigned block, unsigned number, const void* header);
void re4dc_cabin_audio_prepare_end(unsigned token);
unsigned re4dc_cabin_audio_publish_begin(void* stream_work);
void re4dc_cabin_audio_publish_end(unsigned token);
}
#endif

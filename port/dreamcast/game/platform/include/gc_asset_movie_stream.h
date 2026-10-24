#pragma once
#ifndef RE4DC_GC_ASSET_GATE
#define RE4DC_GC_ASSET_GATE 0
#endif
#if RE4DC_GC_ASSET_GATE
#ifdef __cplusplus
extern "C" {
#endif
void re4dc_gcasset_movie_stream_arm(int handle,unsigned owner,unsigned asset);
void re4dc_gcasset_movie_stream_cancel(int handle);
// Fixed-size copies only. These functions never hash, log or read files.
void re4dc_gcasset_movie_audio_ticket(unsigned* slot,unsigned* serial);
void re4dc_gcasset_movie_audio_submit(unsigned slot,unsigned serial,unsigned asset);
#ifdef __cplusplus
}
#endif
#endif

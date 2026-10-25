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
// gc-catalog24b: a movie's token is bound at its natural end (digest of the
// bytes it played); until then its uses are held as pending, never emitted.
#define RE4DC_GCA_MOVIE_PENDING 0xffffffffU
void re4dc_gcasset_movie_resolved(unsigned owner,unsigned asset,int complete);
#ifdef __cplusplus
}
#endif
#endif

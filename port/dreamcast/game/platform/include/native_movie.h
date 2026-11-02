#pragma once
// PS2 prerecorded cinematic presentation (R4FMV003 transport). The source event
// caller stays authoritative for every gameplay effect; this layer presents the
// picture and sound only and reports how the presentation ended.
//
// Movie ids are (room << 8) | event number written as hex digits, so r100s03 is
// 0x10003 and r101s21 is 0x10121; the file is /cd/dc/movie/rRRRsEE.seq.
#ifdef __cplusplus
extern "C" {
#endif
enum {
    RE4DC_MOVIE_RUNNING = 0,
    RE4DC_MOVIE_EOF = 1,        // natural end: last picture shown, audio drained
    RE4DC_MOVIE_SKIP = 2,       // a new press of `mask` (GameCube PAD bits) after release
    RE4DC_MOVIE_ERROR = 3,      // presentation failed after it was attempted
    RE4DC_MOVIE_CANCEL = 4,     // owner cancelled (room retire)
    RE4DC_MOVIE_UNHANDLED = 5,  // no media for this id: nothing presented, source path applies
};
typedef void (*RouteMoviePictureTick)(unsigned picture);
// 1 when /cd/dc/movie/<id>.seq exists and carries a valid header.
int re4dc_movie_available(unsigned id);
// Plays the whole movie before returning (movie-owned presentation at 29.97 fps
// on the vblank clock; the caller's game frame does not run meanwhile). `tick`
// sees each presented picture index, for source per-cut hooks. Skip: `mask` in
// GameCube PAD bits (START 0x1000 = the source event cancel key, Key bit 29).
int re4dc_movie_play(unsigned id, unsigned mask, RouteMoviePictureTick tick);
#if RE4DC_MOVIE_SOURCE_CURSOR
// Optional source clock: called before cancel on each playback iteration,
// including dropped/undisplayed pictures. Existing presented-picture tick stays
// unchanged. Available only in ROUTE_FINAL builds, currently used by r333 S00.
int re4dc_movie_play_source(unsigned id, unsigned mask, RouteMoviePictureTick tick,
                           RouteMoviePictureTick source_tick);
#endif
int re4dc_movie_cancel(void);
// Route QTE cuts (r104s00, the PS2 pattern): play up to picture `stop_at` movie-owned, then hand
// the open movie to the caller's game frames: re4dc_movie_step once per frame (the frame draws the
// picture behind its UI, re4dc_ui_movie_background), re4dc_movie_end to retire it. _stepped opens one
// for stepping only. Bit 24 of an id names the event's cancel clip (r104s00c).
enum { RE4DC_MOVIE_CANCEL_CLIP = 0x1000000 };
int re4dc_movie_play_until(unsigned id, unsigned mask, RouteMoviePictureTick tick, unsigned stop_at);
int re4dc_movie_play_stepped(unsigned id);
int re4dc_movie_step(RouteMoviePictureTick tick);
int re4dc_movie_end(void);
// Index of the last presented picture; 0 before the first.
unsigned re4dc_movie_picture(void);
#ifdef __cplusplus
}
#endif

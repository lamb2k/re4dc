#pragma once
// Route cutscenes: a source event presented by its PS2 prerecorded movie while
// the source caller keeps every gameplay effect (docs/ROUTE_CUTSCENES.md).
#include "native_movie.h"
enum {
    ROUTE_MOVIE_SND_EVENT = 1,  // evd header sndFlag bit31 clear: SndEventInit/SndEventEnd
    ROUTE_MOVIE_KEEP_POSE = 2,  // caller sets Event StatusFlag 0x800: ExeEndEvt keeps the pose
    // RouteMoviePlayQte only (ROUTE_CH13 builds): the cut runs Event::ExecActBtn each frame (the source
    // Event::Run's button-mash prompt and count) and the end func sees that same event (GetActBtnCount).
    ROUTE_MOVIE_ACT_COUNT = 4,
    // ROUTE_CH21 builds: the source call was EvtReadExec(.., flags 0x80), the "true" scenario start: SceEventStart(1)
    // leaves enemies / objects out of event mode (r119 s30, the parasite, mid-fight); EvtReadExec's camera
    // Comeback runs at the end, as SceEventEnd's mode-1 path does not.
    ROUTE_MOVIE_SCE_TRUE = 8,
};
class Event;
typedef void (*RouteEvtFunc)(Event*);
typedef void (*RouteMovieTick)(unsigned picture);  // per-cut source hooks, by movie picture
// Runs in the caller's scenario task until the movie ends. Returns the movie
// terminal (EOF/SKIP/ERROR); RE4DC_MOVIE_UNHANDLED means nothing happened and
// the caller's source event path applies unchanged.
int RouteMoviePlay(unsigned id, unsigned flags, RouteEvtFunc func, RouteMovieTick tick);
// An event whose cancel cut is a QTE (r104 s00: ActBtn A+B / L+R, success -> s01, else s02), the PS2
// pattern: the movie plays to the cut's first picture (`qte_picture`, PS2 evd camera cuts), then the
// cut runs as `qte_frames` game frames over the rest of the movie: `func` in mode 1 at cut `qte_cut`
// each frame (the source ActBtn.set), the game's own ActBtn / HUD drawn over the picture, until the
// handler cancels (StatusFlag 0x4000, the QTE passed) or the cut ends. A skip (START) jumps to the cut
// as RunEvtCancel does (func mode 3), and the cut runs over the event's cancel clip (rRRRsEEc).
int RouteMoviePlayQte(unsigned id, unsigned flags, RouteEvtFunc func, unsigned qte_cut, unsigned qte_picture,
                      unsigned qte_frames);

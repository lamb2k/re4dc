#!/usr/bin/env python3
# edit_movies.py: ROUTE_MOVIES_CH4 hooks (lane ch4found16): chapter 4 events presented by their PS2 movies.
T = '/root/probe/lanes-20261016/ch4found/tree/src/st2/'


def sub(s, old, new, n=1):
    assert s.count(old) == n, (old[:80], s.count(old))
    return s.replace(old, new)


def head(room, R, mid, what):
    return '''#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ROUTE_MOVIES && defined(RE4DC_ROUTE_MOVIES_CH4) && RE4DC_ROUTE_MOVIES_CH4
// ROUTE_MOVIES_CH4 (lane ch4found16 2026-10-16): %s presented by the PS2 movies (BIO4MOV.AFS ->
// tools/convert_route_movies.py, private dc/movie). While a movie owns the event no evd is read; the handler's
// begin / end / skip modes run and the rest of the source is unchanged (docs/ROUTE_CUTSCENES.md). A missing movie
// falls back to the source event.
#include "route_movie.h"
#include "game.h"
#define %s_ROUTE_MOVIES 1
static int %sMovieOwns;
#define %s_MOVIES_OWN() (re4dc_movie_available(0x%s))
#else
#define %s_ROUTE_MOVIES 0
#endif
''' % (what, R, room, R, mid, R)


def guard_open(R, room):
    return '#if %s_ROUTE_MOVIES\n        %sMovieOwns = %s_MOVIES_OWN();\n        if (!%sMovieOwns) {\n#endif\n' % (R, room, R, room)


GC = '#if %s_ROUTE_MOVIES\n        }\n#endif\n'

# ---- r212: s00 (the roof trap)
p = T + 'r212.cpp'; s = open(p).read()
s = sub(s, '#include "pl_npc.h"\n', '#include "pl_npc.h"\n' + head('r212', 'R212', '21200', 'r212 s00 (the roof trap) is'))
old = '''        r212_work.p->evd = DC.setData(EvtMgr.NameChange("evd/r212s00.evd"));
        r212_work.p->evd->setCommand(CMND_ARAM_LOAD, 0, 0);
'''
s = sub(s, old, guard_open('R212', 'r212') + old + GC % 'R212')
old = '    if (r212_work.p->evd->waitLoadOk() == 1 && m != 0) {\n'
s = sub(s, old, '''#if R212_ROUTE_MOVIES
    if (r212MovieOwns) {
        RouteMoviePlay(0x21200, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R212S00_Func, 0);
    } else
#endif
''' + old)
open(p, 'w').write(s)

# ---- r214: s00 (typewriter area 0x12; EvtReadExec flags 0x20 = keep the pose)
p = T + 'r214.cpp'; s = open(p).read()
s = sub(s, '#include "sscrn.h"\n', '#include "sscrn.h"\n' + head('r214', 'R214', '21400', 'r214 s00 is'))
old = '            EvtMgr.EvtReadAram("event/evd/r214s00.evd", (u8) GetEmIdFromListI(0xE4), 0, 0, 0);\n'
s = sub(s, old, '''#if R214_ROUTE_MOVIES
            r214MovieOwns = R214_MOVIES_OWN();
            if (!r214MovieOwns)
#endif
''' + old)
old = '    EvtMgr.EvtReadExec("event/evd/r214s00.evd", (u8) GetEmIdFromListI(0xE4), 0x20);\n'
s = sub(s, old, '''#if R214_ROUTE_MOVIES
    if (r214MovieOwns && RouteMoviePlay(0x21400, ROUTE_MOVIE_SND_EVENT | ROUTE_MOVIE_KEEP_POSE,
                                        (RouteEvtFunc) Evt_R214S00_Func, 0) != RE4DC_MOVIE_UNHANDLED) {
    } else
#endif
''' + old)
open(p, 'w').write(s)

# ---- r215: s00 (QTE cut 0xA: PS2 picture 708, 45 frames; cancel clip r215s00c), s01 (pass), s02 (died demo)
p = T + 'r215.cpp'; s = open(p).read()
s = sub(s, '#include "fade.h"\n', '#include "fade.h"\n' + head('r215', 'R215', '21500', 'r215 s00 (QTE), s01 and s02 are'))
old = '        EvtMgr.EvtReadMram("event/evd/r215s00.evd", 0, 0, 0, 0);\n'
s = sub(s, old, '''#if R215_ROUTE_MOVIES
        r215MovieOwns = R215_MOVIES_OWN();
        if (!r215MovieOwns)
#endif
''' + old)
old = '        EvtMgr.EvtReadExec("event/evd/r215s00.evd", 0, 0);\n'
s = sub(s, old, '''#if R215_ROUTE_MOVIES
        // The QTE cut 0xA starts at PS2 picture 708 (cuts 0..9: 140 + 145 + 38 + 130 + 95 + 15 + 30 + 18 + 32 + 65)
        // and runs 45 game frames (cut 0xA maxFrame 44); r215_succeedAction clears Room_flg[0] bit 31.
        if (r215MovieOwns) {
            RouteMoviePlayQte(0x21500, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R215S00_Func, 0xA, 708, 45);
        } else
#endif
''' + old)
old = '            EvtMgr.EvtReadExec("event/evd/r215s01.evd", 0, 0);\n'
s = sub(s, old, '''#if R215_ROUTE_MOVIES
            if (r215MovieOwns) {
                RouteMoviePlay(0x21501, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R215S01_Func, 0);
            } else
#endif
''' + old)
old = '            EvtMgr.EvtReadExec("event/evd/r215s02.evd", 0, 2);\n'
s = sub(s, old, '''#if R215_ROUTE_MOVIES
            // EvtReadExec flags 2: a died-demo event (Event::Run starts DiedemoExec at its end).
            if (r215MovieOwns) {
                RouteMoviePlay(0x21502, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R215S02_Func, 0);
                DiedemoExec(0, 1);
            } else
#endif
''' + old)
open(p, 'w').write(s)

# ---- r227: s00 (QTE cut 0xB: PS2 picture 1220, 55 frames; cancel clip r227s00c), s01 (pass), s02 (died demo)
p = T + 'r227.cpp'; s = open(p).read()
s = sub(s, '#include "cSceObj.h"\n', '#include "cSceObj.h"\n' + head('r227', 'R227', '22700',
        'the r227 entrance event s00 (QTE), s01 and s02 are (on the GameCube path their three evd files take\n'
        '// 2.5 MB of heap 4 at room entry)'))
old = '''        r227_work.p->evd[0] = DC.setData(EvtMgr.NameChange("evd/r227s00.evd"));
        r227_work.p->evd[0]->setCommand(CMND_MRAM_LOAD, 0, 0);
        r227_work.p->evd[1] = DC.setData(EvtMgr.NameChange("evd/r227s01.evd"));
        r227_work.p->evd[1]->setCommand(CMND_ARAM_LOAD, 0, 0);
        r227_work.p->evd[2] = DC.setData(EvtMgr.NameChange("evd/r227s02.evd"));
        r227_work.p->evd[2]->setCommand(CMND_ARAM_LOAD, 0, 0);
'''
s = sub(s, old, guard_open('R227', 'r227') + old + GC % 'R227')
old = '    if (r227_work.p->evd[0]->waitLoadOk() != 0) {\n        u32 key0;\n'
s = sub(s, old, '''#if R227_ROUTE_MOVIES
    // The QTE cut 0xB starts at PS2 picture 1220 and runs 55 game frames (cut 0xB maxFrame 54); the evd's
    // StatusFlag 0x800 keeps the pose; r227_succeedAction sets Room_flg[0] bit 31 (pass -> s01, else s02).
    if (r227MovieOwns) {
        RouteMoviePlayQte(0x22700, ROUTE_MOVIE_SND_EVENT | ROUTE_MOVIE_KEEP_POSE, (RouteEvtFunc) Evt_R227S00_Func,
                          0xB, 1220, 55);
        pG->System_flg |= 0x400;
        if ((int) pG->Room_flg[0] < 0) {
            RouteMoviePlay(0x22701, ROUTE_MOVIE_SND_EVENT | ROUTE_MOVIE_KEEP_POSE, (RouteEvtFunc) Evt_R227S01_Func, 0);
        } else {
            // StatusFlag 0x100000 | 0x200 (EvtReadExec flags 2): the died demo at the end.
            RouteMoviePlay(0x22702, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R227S02_Func, 0);
            DiedemoExec(0, 1);
            SceExit();
        }
    } else
#endif
''' + old)
old = '''    r227_work.p->evd[1]->setCommand(CMND_DEL_DATA, 0, 0);
    r227_work.p->evd[2]->setCommand(CMND_DEL_DATA, 0, 0);
'''
s = sub(s, old, '''#if R227_ROUTE_MOVIES
    if (!r227MovieOwns) {
#endif
''' + old + '''#if R227_ROUTE_MOVIES
    }
#endif
''')
open(p, 'w').write(s)

# ---- r228: s00, s01, s02 (Salazar's throne room; s01 / s02 follow unless the previous one was skipped)
p = T + 'r228.cpp'; s = open(p).read()
s = sub(s, '#include "db_log.h"\n', '#include "db_log.h"\n' + head('r228', 'R228', '22800', 'r228 s00, s01 and s02 are'))
old = '        EvtMgr.EvtReadMram("event/evd/r228s00.evd", 0, 0, 0, 0);\n'
s = sub(s, old, '''#if R228_ROUTE_MOVIES
        r228MovieOwns = R228_MOVIES_OWN();
        if (!r228MovieOwns)
#endif
''' + old)
old = '''    EvtMgr.EvtReadExec("event/evd/r228s00.evd", 0, 0);
    if ((int) pG->Room_flg[0] >= 0) {
        EvtMgr.EvtReadExec("event/evd/r228s01.evd", 0, 0);
        if ((int) pG->Room_flg[0] >= 0) {
            EvtMgr.EvtReadExec("event/evd/r228s02.evd", 0, 0);
        }
    }
'''
s = sub(s, old, '''#if R228_ROUTE_MOVIES
    // A skip (mode 3) sets Room_flg[0] bit 31, which ends the chain as on the source path.
    if (r228MovieOwns) {
        RouteMoviePlay(0x22800, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R228S00_Func, 0);
        if ((int) pG->Room_flg[0] >= 0) {
            RouteMoviePlay(0x22801, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R228S01_Func, 0);
            if ((int) pG->Room_flg[0] >= 0) {
                RouteMoviePlay(0x22802, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R228S02_Func, 0);
            }
        }
    } else {
#endif
''' + old + '''#if R228_ROUTE_MOVIES
    }
#endif
''')
open(p, 'w').write(s)
print('ok')

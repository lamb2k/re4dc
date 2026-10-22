# Ending entry and integration basis audit, 2026-10-22

Main-thread bounded source review against runtime babfaa7d8ee868c9b81305aef7024ffd543eb6f6. No compiler, linked programme, state write or guest was run for this review.

GameTask dispatches index five to gameEnding. gameEnding case zero calls gameRoomMemInit before loading Etc/Ending.tpl and then displaying the ending screen. gameRoomMemInit retires motion/effect/UI before heap replacement and calls re4dc_room_enter after heap work. This establishes the local order but does not establish that a currently live Room4 owner reaches this path. A source search of all current src C/C++/headers/assembly found no direct pG->Rno0=5 or pG->mode32=5 assignment. Other assignments, packed mode writes, indirect scenario actions, external content and generated code can still determine entry. No normal ending-entry proof is claimed; no speculative owner-retirement patch is justified by this search.

The normal room initialization caller is gameRoomInit at game.cpp502. The actual GameTask loop yields after dispatch. MovieReader cancellation remains separately dispositioned in the independent movie-reader-reachability-01 report: no reachable normal source-yield window was established, and a generic I/O lease can deadlock the scheduler token path. Keep that proposed patch rejected. Active-movie reset completion and DVD error/disc-change concurrency remain target qualification items.

Current QA 52190ed2/GANADO_ROUTINE_BYTES=1 is the selected cache integration basis. The historical 8942/GANADO0 plan remains reference only. Fresh OFF current-QA reconstruction, fourteen overlays and allocated/loadable ELF comparison must pass before SS_RESTORE_VALIDATE_FIRST/RESET_RETIRE_BEFORE_HEAPS are enabled. Event ON and whole-branch adoption remain separate, with no reuse of the older actor/VMU0 Event object claims.

## Reviewed source identities

225f4680a055b4849e5415d9361fec1988d83d39c26fbec882316f031ed02d90 src/game/game.cpp
b0956d568914717092569c137ea60eba27e557880351998d4e51105156815e35 src/game/main.cpp
6479263912945cd5e396f270a2872d88262a69b85bbf4dc357e9e6f4212ea5ce src/game/scheduler.cpp
93df753579f4191495a5827939a2cda784937c2931839b978104c09015155500 port/dreamcast/game/platform/native_movie.cpp
f861a5b9ebb9c6555fc642922af604674fa1acc16a90ba757f55e8ea135b7c92 port/dreamcast/game/platform/os.cpp

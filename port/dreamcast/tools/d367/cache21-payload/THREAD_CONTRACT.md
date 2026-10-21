# Caller and epoch contract

Pinned source base is 892c10ddeadcfcc0bb55bcf53c9b4ac25fd035e8; candidate source identities are in validation.json.

- src/game/main_sub.cpp:224 Render_before calls re4dc_ui_begin at line 233; rendering consumers subsequently call native load through their existing UI/model paths.
- src/game/game.cpp:1507 gameRoomMemInit calls re4dc_ui_retire_room at line 1518. Direct ending initialization also calls gameRoomMemInit at line 1193.
- port/dreamcast/game/ui_bridge.cpp:397 re4dc_room_leave calls re4dc_ui_retire_room at line 426.
- src/game/scheduler.cpp:172 launches a recovered task hook with OSCreateThread and resumes it at line 174. platform/os.cpp:351 implements this using thd_create_ex labelled re4-task.
- The preserved native_ui room-retirement source explicitly says a task can retire while the main thread owns an unfinished TA list; it marks the stream aborted/deferred rather than waiting there.

There is no demonstrated general same-thread serialization contract between all load and room-retirement calls. The initial unprotected bitmap candidate was therefore not accepted as race-safe. The revision holds the existing texpack index mutex around every new bitmap advance/check/update/reset and epoch publication. Its internal reset assumes the already-held lock; external wrappers acquire once, avoiding recursive acquisition. find publishes ordinal+epoch while locked. A stale epoch refuses before candidate eviction, and a completion with an old epoch cannot arm or clear current bits. Epoch exhaustion remains invalid until process restart.

A source package read can yield after the gate and before final completion. This repair does not lock across that I/O and does not prove that the pre-existing entries, renderer or room lifecycle are generally serialized. Broader retirement/admission ownership remains main's audit. Deterministic host hooks inject room reset immediately after find and inside Package open, along with index republish, late success and exhaustion; these characterize the exact source boundary but are not a real-console thread stress result.

# Lane eng-sched2: the scheduler lane finished (SCHED on Flycast, its control, its cost)

Status: **finished, unaudited**. Brief `E:\RE4DC-Lanes\eng-sched2\BRIEF.md`; continues `eng-sched1.md`. Evidence
`E:\RE4DC-Lanes\eng-sched2\` (run-d3 plain, run-d4 calibrated, pc-check-1, suites).

## Answer

r101's room script, waiting on the hosted scheduler, runs 640 ticks in the default image (SCHED OK, 600 rows, no disc
access in play) with the same 1,924 task steps as the PC reference, step for step. On the calibrated tier the
scenario step costs mean 190 us, p99 240 us, worst 340 us a tick: over the 0.1 ms row (below).

## Items

1. **Same path on both sides.** The PC harness (`hostref/svc/sched/sched_main.cpp`) now sets the engine's room
   globals (core/globals.cpp `e1_room_globals`: `pSys->region` 1, Item_find_flg 0x2000, game_mode 5, mot_speed 1,
   System_flg 0x800) and a zeroed room archive header, so R101Init takes the region path (r101.cpp:269-282) the engine
   takes. `SetObj00` returns a logged stub object on both sides (`host/sched_host.h` `sched_stub_object`: zeroed
   storage of cObj's size, every virtual one logged stub returning 0; R101Init calls `setNoSuspend` through it). On
   that path the other calls are stubs too: `EstSet` (effect), `SndCall` (sound), plus the generated set.
   PC check (640 ticks): self, nat, nat-prio16, nat-jit7, nat-jit91 PASS (1,924 steps); nowait (STUCK), reverse,
   ref-reverse FAIL as they must.
2. **SCHED OK; the second crash.** With item 1, SCHED reached play and restarted in tick 1 inside `pPL->move()`
   (local debug discs, branch never pushed: CRASHED exc 0e0 pc 05200009; the player object differed from LEON's in
   every 64-byte chunk before the first move). Cause: the 221,184 B stack pool on the KOS heap ran the heap 200,704 B
   past its end into the behaviour arena (E1 MEM "free to arena -200704, overlaps 3"; the village leaves 110,592 B)
   and overwrote the player in heap 4. Fix: `sched_stack_alloc` forwards to the hosted heap API
   (`host/e1_heap.cpp` mem_alloc, the current heap, as TaskSchedulerInit's MEM_ALLOC asks); the lab step record goes
   there too. SCHED now: free to arena 106,496 B, overlaps 0.
   Plain Flycast run-d3 (function): LEON OK 600 rows; **SCHED OK** 600 rows, 640 of 640 flips, files in play 0;
   **CSCHED FAILED** for its own reason ("Stack overflow in Thread 14", OSPanic scheduler.cpp:217 at tick 300, then the
   selector's TIMEOUT); TSCHED OK.
   The reader `hostref/svc/sched/sched_engine.py steps` (engine E1 SCHEDT lines against the PC trace's T lines; tick,
   slot, status/sleep before and after, task function by name): SCHED against ref.txt **PASS** (1,924 = 1,924, ticks
   0..640); control against the PC's ref-reverse trace **FAIL** ("steps DIFFER at 0: engine slot 14
   r101_checkDoor102KeyUse, PC slot 17 r101_checkFindPlayer").
3. **Stacks** (high water from the pool's 0xB3 paint, every slot, the whole run): slots 14 to 17 used 1,156, 1,188,
   1,160, 1,156 B of 12,288; slots 0 to 13 untouched. Sum 4,660 B of 221,184. The pool is **not justified** by these
   marks: it is the RE4DC_GAME correction's 12 KiB floor (scheduler.cpp GetStackSize, for KOS's fs path inside a task,
   which the engine never takes in play). For the map owner (eng-load2): today 221,184 B in the behaviour arena
   (heap 4), 32-byte aligned, plus about 1.6 KB of KOS heap a live task (4 here). Cutting it needs a ruling on that
   correction (src/ is not edited): the GameCube sizes would be 125,952 B; 4 KiB a scenario slot would hold these
   marks with room, but only r101's four polling tasks were measured (no event or message task).
4. **Cost** (MODELLED (console-build dynarec at 70 MHz, calibrated on the old port), fly2, run-d4, slot.txt
   `Dynarec.Enabled yes Sh4Clock 70`; the standard build reads the engine 3 to 10% kinder): the scenario step
   (ScenarioMove and TaskScheduler, two clock reads a tick) over 640 ticks: **mean 190 us, p99 240 us, worst 340 us**
   (tick 2); every tick over 100 us. Tasks waiting: no such tick in this scene (r101's tasks call TaskSleep(1) and run
   every tick); tasks running: all 640 ticks, the figures above. Plain Flycast (function only): mean 96, worst 190.
   **The worst is over the 0.1 ms row.** About 3 steps a tick, so roughly 60 us a step; that includes the stubs'
   logging (e1_stub_hit searches its name table by strcmp on every call, about 8 stub calls a tick here) and R101Main,
   not only the switch. The engine task switch (an explicit register and stack swap, about 30 instructions each way)
   stays the estimate of about 1 us a step against the lifted layer's two KOS context switches and four semaphore
   operations; not built here (brief). What the model cannot see: graphics chip fill and sort, store-queue
   submission, bus contention, disc timing. Not covered: events, messages, enemies (stubbed).
   Timing control TSCHED (SCHEDD: 200 us spun inside the timed step at tick 200): `sched_engine.py delay` reads worst
   301 us at tick 200 on plain Flycast, 381 us on fly2: PASS; the same reader on SCHED FAILS as it must.
5. Merged origin/engine; the four images and the PC suites: see the hand-back.

## Checks and where they live

| check | where | control (must fail) and how it failed |
|---|---|---|
| PC steps, calls, final state | `hostref/svc/sched_check.sh` (`<out> 640`) | nowait STUCK at tick 0; reverse and ref-reverse differ at step 0 |
| engine steps = PC steps | `hostref/svc/sched/sched_engine.py steps` | against ref-reverse: DIFFER at step 0 |
| stack guard | scene CSCHED (`build_console_disc.sh`) | FAILED: OSPanic at tick 300 |
| cost lines' timer | scene TSCHED, `sched_engine.py delay` | on SCHED: worst 190 us at tick 3, FAIL |

## Stubs and original units

New logged stubs: `SetObj00` and its object's virtuals (both sides). The rest as eng-sched1 (generated set,
r101 voice, IdBinocular, FocusAnimation, IDApplication, stackUsedCheck, zeroed data units). Original units in the
default image: game/scheduler, game/sce_sys, st1/r101 (482 functions, SERVICE 0).

## Old-port parts considered

None new. The stack pool's placement took nothing from the old port (its arena code was left by eng-sched1).

## Files touched

Owned: host/sched_host.{cpp,h}, host/sched_host_stubs.cpp (SetObj00 taken out of the generated set),
hostref/svc/sched/sched_main.cpp, hostref/svc/sched/sched_engine.py (new), tools/engine/build_console_disc.sh
(TSCHED scene), this file. Outside: none.

## Requests

- eng-load2 (map): place the 221,184 B pool (or the cut size the integrator rules) and the lab step record (about
  85 KB, SCHED scenes only); today both are in heap 4 of the behaviour arena.
- Integrator: a ruling on cutting the 12 KiB stack floor (correction in scheduler.cpp GetStackSize); and on building the
  engine task switch, since the calibrated worst is 340 us.
- e1_stubs owner: e1_stub_hit's strcmp table search is per call; a cost inside every hosted stub call.

## Not done

- No Flycast re-run after the merge of origin/engine (the scenes ran on 5e7a80547).
- The cost split between the switch and the script's own work (stub calls, R101Main) is not measured.

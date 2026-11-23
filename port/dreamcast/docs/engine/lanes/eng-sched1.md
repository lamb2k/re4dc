# Lane eng-sched1: the game's script scheduler on the lifted thread layer

Status: **finished, unaudited; step 2 (Flycast) open**. Brief: `E:\RE4DC-Lanes\eng-sched1\BRIEF.md` (plan 3.3 section
8, B2; SALVAGE row 6). Steers H-035 and H-036 answered below ("Lift or engine task switch").

## Question and answer

Does a hosted chapter 1 room script that waits on the scheduler run in the engine with the same outcome and the same
tick order as the PC reference, and what does the scheduler cost a tick?

- **PC: yes.** The village's room script (st1/r101), the scenario layer (sce_sys.cpp) and the scheduler
  (scheduler.cpp), all unchanged, ran 600 ticks on both the engine's lifted layer and the reference layer. Both runs
  gave the same 1,806 task steps in the same order, the same 4,852 calls into the rest of the game and the same final
  state. This held with the main thread at 10 (the engine's KOS priority) and at 16 (the old port's), and with KOS
  timer pre-emption modelled (about 850 pre-emptions a run).
- **Flycast (plain, function): not yet.** The default scenes are unchanged and pass (LEON OK, 600 rows, no disc
  access in play). The SCHED scene stops the console inside the room script's init, before its first tick. The cause
  is found ("Open item" below). CSCHED was not reached.
- **Cost: estimate only** (no Flycast tick yet). Both mechanisms are well under the 0.1 ms row ("Lift or engine task
  switch").

## Lift or engine task switch (H-035, H-036)

**Kept the lifted thread section as it is.** It meets every H-035 condition without bending the engine's loop:

- **One named point.** Tasks run only at `sched_host_scenario`, the scenario step in gameMainLoop's position:
  ScenarioMove, then TaskScheduler slots 0 to 3. Both now run there, and only in the SCHED scene. The earlier separate
  TaskScheduler call after game_tick was removed.
- **No pre-emption inside a tick.** Every task thread is parked off KOS's run queue (created suspended, parked when it
  sleeps). The one exception is while the main thread waits for it in TaskSchedulerMain's run-until-sleep hand-off.
  The main thread (10) outranks every task (14, 15), so a task cannot run during services or drawing even under KOS's
  timer. The PC rows nat-jit7 and nat-jit91 model that timer, with a bystander thread pre-empting about 850 times a
  run, and the task order stays identical.
- **No timer wake-ups.** The old file has no alarms (its OSInitAlarm was empty) and none were added. A task wakes
  only when the scheduler's hand-off resumes it.

Cost in the engine, per H-036:

| | lifted section (kept) | engine task switch (not built) |
|---|---|---|
| time a tick | **estimate** 10 to 25 us: about 3 task steps a tick (1,806 / 600 on the PC), each two KOS context switches plus four semaphore operations, about 3 to 8 us a step | **estimate** about 1 us: an explicit register and stack swap, about 30 instructions each way |
| stack memory | the scheduler's own pool, 221,184 B, plus one KOS thread record a live task (about 1.6 KB of KOS malloc; 5 live tasks in r101, about 8 KB) | the same pool, plus a small context record a slot (about 100 B) |
| risk to the tick order | held by parking and priority. Shown on the PC under modelled pre-emption; not yet shown on Flycast | none by construction |
| work and risk to bring in | done; proven on the PC | a new switch in SH-4 assembly, with its own PC model and controls |

The difference is about 10 to 25 us a tick (estimate), under 0.1% of the 33.3 ms picture. The lifted section is cheap
and right as it is, so it was not rewritten (H-036). If the calibrated tier shows a worst tick over 0.1 ms, the engine
switch is the replacement: same stacks, same hand-off points in scheduler.cpp's non-PowerPC path.

Each old-port piece considered:

| piece (t15/int a5aca9cf9 port/dreamcast/game/platform/os.cpp) | verdict | why |
|---|---|---|
| threads (create suspended, park and unpark, resume, suspend, exit, cancel, priorities, ageing reset, reaping) | taken | GameCube semantics over KOS, cheap; the PC check proves the order |
| thread queues, semaphores, interrupt enable and restore | taken | the scheduler's hand-off is built on them |
| OSPanic | taken, adapted | prints the engine's buffered log, then halts |
| main thread set to priority 16 | left | the engine's main loop keeps its own KOS priority; row nat-prio16 shows both give the same order |
| native_io depth and native_motion lease checks | left | the engine reads nothing in play and has no motion lease |
| crash-screen hooks and tests | left | plan B4 (the crash-screen lane) |
| arena, heaps, time, stopwatches, calendar, reset, font, console queries, module link, KOS squeeze, image check, fixture reads, thread dump, debug poisoning, VMU ring, OSReport, per-creation log | left | engine services exist, or not wanted in the engine |
| alarms | none existed | none added (H-035: no timer wake-ups) |

## What was written new, and why

- `engine/host/sched_host.cpp` and `.h`. The engine side of the scheduler:
  - the room table's dispatch and the room's save record (one room script is hosted);
  - zeroed data units for `cDataCtrl::setData`;
  - the platform answers scheduler.cpp asks for (`re4dc_io_busy` returns 0, `GXSetCurrentGXThread`,
    `DbMenuRestoreStopFlag`);
  - the stack pool on the KOS heap (`sched_stack_alloc`; scheduler.o's mem_alloc is bound to it by objcopy);
  - the counters, the report, the SCHED scene and its SCHEDX control;
  - logged stubs for the service functions made weak in the hosted units: r101's voice task, cam_extra's binocular
    widget and focus blur, and scheduler's debug stack page.
- `engine/host/sched_host_stubs.cpp`. Generated logged stubs (by engine/fight/gen_stubs.py) for about 100 names the
  room script and the scenario layer reach that the default image does not host, plus zeroed storage for their data
  objects.
- `engine/hostref/svc/sched_check.sh` and `hostref/svc/sched/`. The PC check.

## Which room script, and why

st1/r101, the village:

- It is the benchmark room (village cross) and the default image's own room.
- The fight image already hosts it.
- With a first visit's flags, its init starts five tasks that wait.

r100 is the route's first room, but its tasks wait on its opening event and movies (plan B6).

## Where the scheduler runs in the engine's tick

Original: PadRead, Frame_cnt++, TaskScheduler (slot 0 = gameMainLoop: ScenarioMove first, then EmMgr.move, the
player, objects, camera; then slots 1 to 3), draw, and the ISR slot 4 after the CPU work.

Engine (core/main.cpp), default image:

1. input, PadRead, Frame_cnt++;
2. game_tick. Its first step is `sched_host_scenario`, the one point where any task runs:
   - ScenarioMove: R101Main, EvtMgr.Run, then scenario tasks 5 to 17 in ordering-table order, each until it sleeps;
   - then TaskScheduler, slots 0 to 3;
   - the partner, the player, objects and camera follow;
3. draw, pacer.

Slot 4 is not run: the engine loads nothing in play. All of this happens in the SCHED scene only; the default scenes
run nothing new in play.

## Stacks and memory (for eng-mem2)

- The pool: 18 slots × 12 KiB = 221,184 B (GetStackSize under the RE4DC_GAME correction; the GameCube sizes would
  total 125,952 B). It is on the KOS heap, allocated at the SCHED scene's room start (Flycast MEMBLK 221184).
- One KOS thread record per live task, about 1.6 KB each.
- High-water marks: not measured yet (SCHED did not reach a tick).
- Ask: place the pool in the map (main RAM, 32-byte aligned), and size slots 5 to 17 from the high-water marks once
  measured.

## Checks and their controls

PC (`hostref/svc/sched_check.sh <out> [ticks]`; evidence `E:\RE4DC-Lanes\eng-sched1\pc-check-1`): rows self, nat,
nat-prio16, nat-jit7 and nat-jit91 PASS. The controls fail as they must:

| control | reason it fails |
|---|---|
| nowait | STUCK at tick 0 |
| reverse | task steps differ at step 0 |
| ref-reverse | task steps differ at step 0 |

The comparison covers every task step, every stub call in order and the final state. A run without its final line
fails, an erroring comparison is never a result, and a control must fail for its named reason. The reference
(`sched/gc_os.cpp`) follows the GameCube SDK's documented rules. The native program runs `core/os_threads.cpp`
unchanged over `sched/kos_pc.cpp`. Both run scheduler.cpp's non-PowerPC path.

Flycast scenes (`tools/engine/build_console_disc.sh`):

- SCHED must be OK.
- CSCHED (SCHEDX: a scenario task's stack guard overwritten at tick 300) must FAIL through scheduler.cpp's
  StackOverflowCheck, then OSPanic. Not yet run to that point.

## Open item

On the engine, `pSys->region` is non-zero. On the PC harness it is 0, because the harness zeroes pSys. R101Init
(r101.cpp:269-282) therefore takes the region-not-0 path on the engine:

```
PSet(r101_work->obj00, SetObj00(ROOM_ARC_PTR(pG->pRoom, 0x20), ...)); r101_work->obj00->setNoSuspend(1);
```

`SetObj00` is a zero stub, so the script writes through a null object and the console restarts. The serial log's
last line before the restart is `E1 STUB SetObj00`. The fix, in this lane's files:

1. Set the PC harness's region to the engine's value and re-run sched_check.
2. Give `SetObj00` an engine-form return: a zeroed object of cObj size, logged, in both the harness and
   sched_host.cpp.
3. Rebuild the disc, then run SCHED and CSCHED for the stack marks, the Flycast cost and the control.

## Not done

- Step 2 on Flycast: the open item above.
- Step 3 cost on Flycast or fly2.
- Stack high-water marks.
- The fight and boss images still run their own task layers (requests below).

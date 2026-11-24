# Engine line hand-overs

One numbered entry per milestone or blocking question. Newest first. Format: commit, image hashes, numbers with tiers, evidence path, what was not done.

## H-045 (2026-11-23): RE4 resumed; QA Link first; the drawing unit merged; rulings

- **Owner, in order:** "we should start it so we have a good testing canddiate" (lane eng-link2: RE4 on dc-qalink
  0.2); "I want to run increments of re4 from the network drive" and "gdemu should perform better for loads and reads -
  but for regular graphics and bug testing this should be ideal" (each increment runs with the whole disc served from
  the PC by the network disc; load and read timing is judged on GDEMU only, at milestones and releases); "At least the
  RE work" (RE4 resumed after H-044); "clearly finish the RE4 on QA link work with drawing work being a good test
  candidate once it's ready" (order: eng-link2 and the drawing work first, then the owner's console test build).
- **Merged (eng-int, finished, unaudited):** the eng-draw unit (eng-draw3 + eng-draw4 + eng-draw5, lane/eng-draw5
  412722200): merge c7f134e5b, engine 8932e105b. 59 of 59 stills identical against two base runs; characters' drawing
  mean LEON 11.73 -> 11.24 ms, HILL 23.16 -> 22.31 ms (MODELLED, console-build dynarec at 70 MHz, fly1). No scene meets
  the 14 ms drawing row. FIGHT KOS heap to the arena after play +221,184 B (plain count).
- **eng-draw6 (ed48059f1, at the gate next):** detail levels failed the stills check against the two-run floor (22 px
  outside the changed boxes on FIGHTS 240 and 360, where the base runs agree) and were removed from the build (no
  default-off arm). Kept: slot pools sized at pack open, assembly skinning (C deleted). The released-lighting look sheet
  `E:\RE4DC-Lanes\eng-draw6\sheets\LOLD-vs-engine.jpg` was sent to the owner on 2026-11-23; no answer yet.
- **eng-link2 (a12ae7c30, gated after its re-pin to dc-qalink v0.2.0):** rulings: its three hooks outside its owned
  files (core/main.cpp E1_QALINK calls, core/play_files.c accessor, game/Makefile include) accepted as the QA build's
  link hooks; FIGHT SENDABLE builds with `DCQL_ENABLE=0` until the memory map's owner rules on its ~32 KB heap margin.
- **Ruling, the stills floor:** a third base run of the same disc differs from a two-run floor on about 1 FIGHTS still
  in 10 (single colour steps). Gates now build the floor from three base runs (a still where any base run differs from
  the first is left out, whole picture, no tolerance). This adds base runs and loosens no comparison.
- **Open, for their owners:** FIGHT's room carve is refused every tick (SVCMEM 8cf40000-8cfc0000, carve fails at
  174,592) and floods the tick log, so FIGHT's timing record fails with "no E1 FIELDS line" (memory map owner);
  CS_LEVELS is not set in E1 (core/draw_e1.c owner).
- **Incident:** a housekeeping lane (ws-scratch) deleted six files from `eng-skel2-data/pristine-colb` during a gate;
  restored byte-exact from `eng-bench/.m1/base003` against `pristine.json` (E:\RE4DC-Lanes\ws-scratch\RESTORED-*.tsv),
  verified by eng-int before its disc run. Cleanup briefs now fence game-data trees by file type.
- **Step 6 backlog from the SH4DER-PVR scan (2026-11-23):** eight ranked look rows, two renderer notes and a "left for now" line added to ENGINE_PLAN.md section 7, below the step 6 candidates (source JiltedValkyrie/SH4DER-PVR, ideas only; scan `E:\RE4DC-Lanes\scan-sh4der\REPORT.md`); the owner acknowledged the list ("ok"); each row needs an owner-approved still pair and starts only once chapter 1 holds the floor.
- **eng-link2's report room (integrator's ruling, 2026-11-23):** dc-qalink 0.2.0's hand-off layout stays (the report after the return stub's area, so the selector's report cap is smaller than before); the lane fixes it on the RE4 side (a smaller journal and/or leaner rows, 10% headroom for every scene) with a loud guard and its control instead of silent truncation (the gate of a91c15f33 failed on FIGHT "rows: 598 of 600 pictures", report 84,235 B).

## H-044 (2026-11-22): RE4 paused by the owner

- **Owner** (relayed by the F-Zero coordinator): "Tell the resident evil track to pause its work and create and
  handover + to give you resources back". Every lane pushed and stopped; bakes, builds and Flycast stopped; RAM stages
  cleared. Handover: the workspace file `RE4-PAUSE-20261122.md`; gate queue `E:\RE4DC-Lanes\eng-int\RESUME-20261122d.md`.
- **Merged before the pause** (eng-int, finished, unaudited): the memory train (d4c966846; eng-skel1, eng-skel2,
  eng-load1, eng-snd1, eng-mem1, eng-mem2) with the shared pack sets `e1-farmwep-20261122` and `e1-colb-20261122`;
  room loading eng-load2 (1a4335fd7; DOOR passes, judged on kos-net). engine c8642d132.
- **Rulings on the stop reports, for the resume:** eng-draw6's "shared translucent data" finding withdrawn (only
  Leon has translucent parts); its detail levels merge only if the stills check holds with the floor applied. The
  disc script's default tree lacks baked collision: gates use `PRISTINE=pristine-colb` until the script defaults to
  the shared set (a small lane on resume). CPU sharing with the F-Zero line: over 85%, `make -j2`, bakes 2 workers.

## H-042 (2026-11-22): the console link: GDEMU, no restarts, no card copying, dc-qalink

- **Owner, in order:** "Does it matter that the system is running a GDEMU?"; "Maybe there is a way to not restart at all
  entirely and the loader can reboot within the slot it loaded"; "Would it be possible For the loader To push builds so
  that we don't Need to copy and paste in the GDEMU?"; "One of them is a disc embed the other is a separate control
  loop"; "I meant shoukd it life in the dc qa link repo or Be presented as a more robust tool now?"; "Yeah let's make
  the link public more robust while also integrating it into RE4 so that you can push programs and test the outputs".
- **Design (plan section 9, brief `E:\RE4DC-Lanes\eng-link1\BRIEF.md`):** every exit returns to the loader inside
  the mounted GDEMU slot through a return stub in the protected top of RAM that reloads the loader with the BIOS's disc
  calls; a hang with interrupts off trips the SH-4 watchdog (a CPU reset that boots the same slot, a console check);
  a smart-plug power cycle is the last rung and lands in openMenu. The SD card is written once: builds and room packs
  come over the link and a small first stage fetches the current loader from the PC. The adapter takes the modem's
  port. Two parts on one link layer: the in-game library and the control loop.
- **Where:** the public `lamb2k/dc-qalink` (0.1.0, f40cd8b40, MIT) as its next version, branch `v0.2-bba-loader`;
  re4dc pins it as a submodule and keeps the RE4 layer. The integrator merges dc-qalink's branch into its main after
  its host tests and the RE4 gate; a tagged release and its notes go to the owner first. Lane eng-link1 started with
  `make -j2` (CPU 77 to 93%).

## H-041 (2026-11-22): the console link over the broadband adapter; room loading handed back

(There is no H-040: the kos-net ruling below took that number in a message.)

- **Owner:** "Do we have a lane that can take up building a version of the QA link or Expanding its capabilities to
  work with the BBA but also push images and restart the Dreamcast?" No lane had it: the console loop runs over the
  modem only and lists the adapter and a smart plug as next steps. Plan section 9 (the console link) and lane
  eng-link1 (brief `E:\RE4DC-Lanes\eng-link1\BRIEF.md`): the adapter as a second transport under the loop's
  protocol and checks, packs served by the PC at load time only, stills and serial lines pulled back, a reset command,
  the BIOS reboot and a power-cycle hook for a smart plug, proven in Flycast's adapter emulation. Its first console
  run waits for the owner (H-021). "Push images" is read as programs and room packs to the console, and stills back.
- **Room loading (lane eng-load2, handed back, queued after the memory train):** MODELLED (console-build dynarec at
  70 MHz, calibrated on the old port) with the GDEMU disc profile: village to farm 7.13 to 4.80 s, farm to village
  5.17 to 3.28 s; the old port's village to farm 4.68 s (a measuring stick, different span). Packs on disc without
  the unused recording (farm 11.3 to 6.3 MB), 32 KiB reads (drive requests 3,992 to 210). DOOR OK: the 16 B was the
  allocator's slack. **Ruling (sent to the integration lane as H-040):** the round trip is judged on "kos-net"
  (uordblks less the tracked blocks' slack), with CDOORLK still failing and a lost block list failing. Of the farm's
  4.80 s, 3.12 s is the renderer re-indexing character vertices at load: lane eng-draw5 is asked to design its layout so
  that work moves to the bake.
- **New lane:** eng-rec1, recordings of the ten chapter 1 rooms without one (plan section 8, B5).

## H-039 (2026-11-22): the gate's second report; the scheduler's first pass

- **Merged by the integration lane's second session:** eng-e2d (FIGHT 43 to 30; the allowed destructor has no body in
  any image), eng-bake1, eng-e2f with eng-e2g as one train (FIGHT 30 to 10; KNOCKNT the expected failure). `engine` code
  at 78cf37442.
- **The memory train** (`lane/eng-mem2` 773ccc6b5) passed every step on the disc (LEON, HILL, FIGHT, BOSS OK; DOOR
  failing by exactly 16 B; its three controls failing for their own reasons) and stopped on the gate's own judge
  (the door controls' list has no kind field). The third session fixes the judge with a control and merges.
- **Rulings:** `core/e1_core.h` (eng-snd1's seed) and `tools/engine/pack_keep_check.py` are accepted outside files.
  The train's calibrated sound run kept no `emu.cfg.used`: accepted from the disc's tier line for the merge, noted as
  unrecorded, re-recorded at the next calibrated run. eng-draw3's FIGHT ends 12,288 B short on the old map: it is
  gated again on the train's map, as one unit with eng-draw4, and FIGHT's margin must be positive.
- **The scheduler (lane eng-sched1, handed back, not at the gate):** on the PC the village's room script runs 600
  ticks on the hosted scheduler with the reference's 1,806 task steps in order, three controls failing. In Flycast
  the script restarts the console in its init: the PC harness ran a different path (a zero region) from the engine's.
  The old thread section was kept under the test of section 8: tasks run at one point of the tick, parked otherwise,
  no timers; estimate 10 to 25 us a tick against about 1 for an engine task switch, both far under the row. Lane
  eng-sched2 finishes it: the PC check on the engine's path, the scene and its control, stacks, the cost measured.

## H-038 (2026-11-22): the skinning routine is not gold

- **Owner:** "I agree with everything except this being golden: the skinning routine". The lifted routine
  (`avk_sh4.S`) leaves the plan's "Kept as they are" list. It stays in use until something better is measured, and it
  is open to be redone the engine's way: positions (normals only where lighting needs them), no outputs nobody reads,
  a vertex and weight layout that suits the engine's packs, on SH4ZAM where it has the piece. Lane eng-draw5 takes it
  ahead of its other items (skinning is 2.2 / 4.1 / 1.9 ms a picture mean on LEON / HILL / FIGHT, MODELLED,
  console-build dynarec at 70 MHz, calibrated on the old port). The rest of the list stands as the owner agreed.

## H-037 (2026-11-22): memory layout: the engine's own where it is better

- **Owner:** "If we have a better memory layout we can implement our own unless we believe it eas pre socially
  optimized" (read: unless the old layout was already specially optimized). Ruling: the engine's memory map is its
  own (lane eng-mem1's `MEMORY_MAP.md` stands; nothing in it is to be bent back toward the old port's map). An old
  layout is kept only where it was tuned on purpose and measured: the sound chip's fixed bank layout (already taken
  with the AICA layer). The old video-memory map and the per-room resident texture lists are knowledge, not a layout.
  A lane that replaces a tuned layout shows the measurement. In the plan's section 8.

## H-036 (2026-11-22): character look choices approved; cost before convenience; what was gold is kept

- **Owner, on lane eng-draw4's two sheets:** "They look fine for the character options" (typed "chatter"; read as the
  character options: detail levels by screen size, LVL, and lighting every other picture, LHALF). Both are approved as
  looks. Lane eng-draw5 lands LVL as the default once the Ganado difference under it is explained, and the staggered
  LHALF (characters alternate pictures) as the default if it helps the worst pictures, fits the fight's memory and its
  stills are no further from today's than the approved sheet; otherwise it stays an arm and a new sheet goes to the
  owner. Each is recorded as a design choice with its sheet (the approximation rule's engine-line form).
- **Owner:** "I don't want to borrow costly things because they're convenient - I also don't want to redo things that
  were gold previous implementations". With H-032 and H-035 this is one rule, now in the plan's section 8 and the
  common brief:
  1. Cost decides, never convenience: a part is taken only if it is cheap inside the engine on the console's terms
     (time a picture, memory, load seconds, disc reads). This binds the engine's own shortcuts too (a pack that carries
     299 unused recorded frames; a whole-file check at every door).
  2. What was gold is kept as it is: an implementation proven on the console, cheap and right is not rewritten for the
     sake of being new; it is changed only for a measured gain. The plan lists them (section 8, "Kept as they are").
  3. The engine's design wins every doubt (H-035).
- Sent by message to the running lanes eng-draw5, eng-load2 and eng-sched1.

## H-035 (2026-11-22): borrow only what makes sense; the engine's design wins; gate rulings on the memory train

(There is no H-034.)

- **Owner:** "We should only borrow from the old port thing that make sense I don't want to Compromise the new engine".
  This narrows H-032 and the plan's section 8, which had made lifting the default. The rule is now a test (plan section
  8, common brief): a part is taken only if it sits at the engine's edge or is a self-contained routine, fits the
  engine as the engine is (no per-picture conversion, no old layout or control flow, no switches, no disc access in
  play), and measures at least as good inside the engine. Otherwise the idea is taken and written the engine's way, or
  the part is left. Section 8's lists are candidates, not orders. When in doubt the engine's design wins.
- **Applied to the running lanes by message:** eng-draw5 does not import the old character layout or emitter (the old
  port's cost is measured as evidence; a baked vertex order may be taken as an idea in the engine's own pack format;
  the old light kernels are a look sheet only); eng-load2 lifts the disc driver's blocking 32-byte request and takes
  only ideas from the old room read path (no read queue, no archive loaders, nothing read in play); eng-sched1 keeps
  the engine's tick order: the old thread section only as the mechanism under the hosted scheduler, run at one point of
  the tick with no pre-emption and no timer wake-ups in play, or else the engine's own cooperative task switch.
- **Already taken and kept under the test:** disc read safety, the AICA sound layer, the skinning routine, the crash
  screen and profiler (lane eng-crash1: edge parts, no cost per picture, one fixed path each).
- **Merged since H-033:** eng-e2f and eng-e2g as one train (FIGHT 30 to 10 service functions; the knock-down shown).
- **Gate rulings:** the memory train (`lane/eng-mem2`, covering eng-skel1, eng-skel2, eng-load1, eng-snd1, eng-mem1,
  eng-mem2) is gated as one; DOOR is an expected failure with the exact reason "round trip LEAK kos-used" of +16 B
  (lane eng-load2 closes it); the selector's sound ceiling applies on a disc that declares the calibrated or console
  tier; `skel.cpp`'s identity start for a failed inverse is an engine fix. eng-draw4's kernel step is judged against
  the stills' own run-to-run variation (two base runs); its look arms stay off. eng-crash1's address-fault scenes are
  expected failures in Flycast ("planted fault did not stop the program"): the deferred console run checks them.
- **Look sheets with the owner:** character detail levels (LVL) and lighting every other picture (LHALF), lane
  eng-draw4. Nothing lands before their answer.

## H-033 (2026-11-22): plan version 3.3: what we take from the old port; gate rulings

- **Owner:** "Integrate into the plan what we should copy or Integrate from the legacy port engine." Done:
  `ENGINE_PLAN.md` "The plan as of 2026-11-21", new section 8 (version 3.3): the rule (lift and adapt before writing
  new; every brief names the old-port part, every hand-back says what was lifted), A already taken (disc patches and
  read safety, sound, the skinning routine, converted assets, spawn rules, corrections), B take next in order (room
  loading at the old port's speed, the scheduler on the old thread layer, code modules, crash screen and profiler,
  room recordings and the data inventory, movies, saves, QA and warp tools, release gates, the per-room fix list),
  C take when the renderer can hold them (proven SH-4 routines measured in the engine's renderer, the sky plane, blob
  shadows, the released effect selection, rain and flame sets, resident texture lists, picture modes), D not taken (the
  GameCube drawing emulation and its settings, the disc shim, the movie front end, the inventory memory trick).
- **Ruling:** the inventory's "drop" for the old port's SH-4 routines other than `avk_sh4.S` is re-opened: lane
  eng-draw4 measures them inside the engine's renderer beside its own; the faster one with 0 differing pixels stays.
  The old drawing path as a whole stays out and is not tuned.
- **Lanes started from section 8:** eng-sched1 (B2) and eng-crash1 (B4). B1 and B3 follow the memory train's merge.
- **Gate rulings:** KNOCKNT is the knock control; its "pool refused: full 50" follows from the control's own state (the
  crash volume never expires) and is an expected failure with that reason; the disc script is to list it as a control
  kind. eng-cloth2: the reference runs the skirt at two passes by the owner's choice (H-032), `SKIRT_PASSES=4` builds
  the old reference, `--skip-skirt` may be used by the new refctl rows only; the skirt's pass count stays a constant
  with its note, not a game setting; one start-up still's 6 pixels accepted as noise.

## H-032 (2026-11-22): the owner chose skirt option B; borrow the old port's working mechanics

- **Owner:** "Ok option B." Ashley's skirt runs two constraint passes instead of four, as the default with no switch
  (lane eng-cloth2, from eng-cloth1; it supersedes eng-cloth1 at the gate). MODELLED (console-build dynarec at 70 MHz,
  calibrated on the old port), hill cloth 5.36 -> 4.21 ms mean, 5.57 -> 4.39 p99, skirt pixels only.
- **Owner:** "I also appreciate your innovation but we should be borrowing things that work fine at a mechanical level
  from the old build pre re architecture." Ruling: before a lane writes new engine plumbing it checks the salvage
  inventory (`SALVAGE_20261121.md`, REUSE and ADAPT rows) and the old port's own Dreamcast code (release line, read
  only), and lifts what works: disc and loader, door and room-change memory guards, video-memory residency, sound, the
  movie player, the memory card, the crash screen, proven kernels. It adapts only what the new architecture needs and
  says in its hand-back what it lifted and from where. Unchanged: no original game service code in the engine (link
  check); the old drawing path as a whole is not tuned (a proven piece of it may be lifted and measured in the engine's
  pipeline). Steered by message to eng-mem2 and eng-draw4; in the common brief for every new lane.
- **Gate rulings since H-031:** eng-draw3's step 1b stays (its one differing pixel is inside the base's own
  non-repeatability); CBCULL saves about 0.1 ms on this tier and stays a lab arm for the deferred console run (not put
  to the owner now). eng-mem1 (the map, the farm and village packs kept to frame 0's rows, sound under its ceilings,
  the hill's handgun drawn again) handed back with DOOR not yet OK and a boot hang: lane eng-mem2 finishes the train.
  New lane eng-draw4: the characters' emission and skinning kernels and three look sheets (detail levels, a light cap,
  lighting every other picture).

## H-031 (2026-11-22): the gate's first four questions; one owner for the main memory map now

- **Merged this morning (integration lane):** eng-clock1 (the engine clock: no 2.5 ms jump at the whole second),
  eng-draw1 (the drawing account), eng-draw2 (world: clipper pre-reject, the walk without a stage, strips facing away
  not sent; MODELLED, console-build dynarec at 70 MHz, calibrated on the old port: LEON drawing about 1.3 + 0.5 + 0.5 ms
  less by its steps). `engine` 1219ea9da. Finished, unaudited.
- **Stopped at the gate on one point, four lanes:** eng-skel1 (the native PC reference does not link: `cObjChain::
  setParent2` in services/cloth/chain.cpp and in eng-e2c's logging stand-in hostref/svc/e2c_dump.cpp), eng-load1
  (DOOR: the farm's reopen asks for a resident buffer of 8,526,624 B since eng-draw2's per-pack sizing), eng-snd1 (FIGHT
  ends 32 KB short of its arena under R1; HILL sound worst 2.77 ms on a plain run), eng-skel2 (contains skel1; moves the
  arena 512 KB).
- **Rulings:**
  1. **One owner for the main memory map now** (H-029.3 brought forward): lane eng-mem1 merges skel1, skel2, load1 and
     snd1 into one branch, owns `host/e1_engine.h`, every arena and heap placement, the resident pack buffer's sizing
     and the loader's memory calls, writes `docs/engine/MEMORY_MAP.md`, and hands back one train for the gate.
  2. **setParent2:** the service's definition stands; the logging stand-in yields to it (weak, or only in the build
     without the chain service).
  3. **Sound ceilings (H-025.1)** are judged on the calibrated tier, as the waiver says; the selector judges them on a
     run that declares that tier and prints them otherwise. HILL's 2.77 ms worst must be explained or gone on that tier.
  4. **eng-e2d's allowed line `cEmWrap::~cEmWrap`** is accepted where the body in the map is a bare return; the gate
     checks its size.
  5. **eng-bake1's bake/ files** not listed in its hand-back are inside its owned `bake/`: accepted, recorded.
- **Look choice sent to the owner:** Ashley's skirt options (lane eng-cloth1, sheet and clips; B, two constraint
  passes, recommended: 1.15 ms on mean and p99, MODELLED). Nothing visible lands before their answer.
- **From eng-bake1:** all 12 chapter 1 rooms with a world bake; 10 need old-game captures for props, lights and
  effects (backlog: room recordings); the cabin and the pool stage about 2.0x and 1.7x the village's vertices; the
  farm has 85 KiB of its room block left before collision; the visibility bake misreads the river and the cabin
  (fix in bench/bake_vis.c, to the next drawing lane).

## H-030 (2026-11-22): resume after every lane stopped at its tool limit; re-merges and trains at the gate

- **State at resume (04:00):** `engine` a68a57094. Every lane agent of 11-21 had stopped (tool-call limits, the
  integrator's session ended about 15:20); nothing ran, no slot held a lease. Pushed by the integrator after the
  public-repository blob check: `lane/eng-skel2` e590e4b2e (never pushed before: collision baked offline, contains
  eng-clock1 and eng-skel1) and `lane/eng-draw3` 0e0f156bd (steps 1b and 2b).
- **Gate queue, in order:** eng-clock1 (pending at its Flycast step), eng-draw1, eng-draw2, eng-skel1 (c60a0cd4c),
  eng-skel2, eng-load1, eng-e2d, eng-e2f with eng-e2g, eng-snd1. The integration lane restarted with
  `E:\RE4DC-Lanes\eng-int\RESUME-20261122.md`.
- **Restarted to finish their briefs:** eng-draw3 (calibrated slot fly1), eng-cloth1 (fly2), eng-bake1 (PC only).
- **Rulings:**
  1. **Re-merges for ended lanes.** When `engine` has moved by code past an ended lane's merge base, the integration
     lane may merge `engine` into that lane's branch itself, in the lane's worktree, when every conflict is mechanical
     (both sides kept, no choice of design, value or rule); its gate report lists the conflicted hunks. A conflict that
     needs a choice comes to the integrator with both sides quoted.
  2. **The main memory map** (`host/e1_engine.h`): eng-snd1's R1 and eng-skel2's arena move both shift the behaviour
     arena; whichever lands second comes to the integrator with both maps and both lanes' measured margins.
  3. **Trains:** up to three queued lanes gated as one when their trial merges are clean in order and their owned
     files do not overlap; steps 1 to 4 and each lane's controls per lane, images, suites and one clean disc once on
     the train's tree; a failure drops the lane it points at. Each lane keeps its own merge commit and STATUS note.
  4. **eng-draw2's ROOMTRIP check:** video-memory free after a release is 24 B under the figure before the first open
     (the allocator's first-use bookkeeping, constant over three releases). The baseline is to be taken after the first
     release and any growth across releases fails; that change goes to eng-draw2's successor. Until then ROOMTRIP is an
     expected failure with that exact reason (as DOOR under H-029.7).
  5. **eng-e2f's knock-down scene** fails on the shot's capsule rule, which eng-e2g fixed (its KNOCK passes): the two
     are gated as one train.

## H-029 (2026-11-21): a day of hand-backs: sound, a door, the boss at zero, hidden service code, the clock; rulings

- **Merged through the integration lane today:** eng-salv1, eng-e2a, eng-cmp1, eng-e2b (fight 73 to 43), eng-look1 (Leon's
  handgun drawn live), eng-fix1 (corrections, game settings, guards: from cd8b8762b the corrected reference is the
  baseline; refctl 20 rows).
- **Queued at the gate, in order:** eng-draw1 (the drawing account), eng-clock1 (the clock fix, below), eng-e2c (boss image
  26 to 0), eng-e2d (the general split check; fight 43 to 30), eng-svcspd1 (five exact speed fixes), eng-skel1 Part A at
  45da184a9 (skeleton entries, chain object, collision release), eng-load1 at f7f6e9a48 (room-to-room loading; its DOOR
  scene fails by design on a collision leak until the release entry is in). eng-snd1 (sound) joins when its items close.
- **Running:** eng-draw2 (world drawing), eng-draw3 (characters' drawing), eng-cloth1, eng-skel2 (clock, baked collision,
  skeleton cost), eng-e2f (fight to 0, knock-down, area check hosted), eng-bake1, eng-snd1.
- **Findings that change how earlier figures are read:**
  1. **The clock (lane eng-skel1).** KOS's nanosecond clock jumps 2,502,400 ns forward once per emulated second (TMU2
     reloads from 12,468,720 counts a second, `(199499520 / 4) / 4`, while each count is valued at 80 ns). Every MODELLED
     worst picture measured before the fix may carry +2.5 ms in one picture a second; means read 0.25% low. The fix
     goes into the engine's clock wrapper (`lane/eng-clock1`), not into KOS. Reporting it to KOS upstream needs the
     owner's OK (offered, not asked again).
  2. **The link check's zero was a count of symbols (lane eng-e2d).** The default image carried original drawing code
     (objWep's `Draw_line3d_222`) inlined into two kept functions; FIGHT had 42 hidden cases and BOSS 18.
     `tools/engine/split_check.py` now runs inside `check_link.py` on every map; units with a replaced function are
     built without the interprocedural optimisations.
  3. **The PC native build's `GetScreenPos`** answered the screen centre for every point (no GX projection is loaded on
     the native build): fixed in `hostref/host_math.cpp` as a tool fix; the original's answers are unchanged.
- **Rulings:**
  1. **Collision is baked offline** (lane eng-skel1's option 2): the SAT/EAT tables are replaced in the room archive by
     the form the service queries; header and normal table kept; pieces in the room heap; the services region goes
     to 512 KB; no bake at load. r106 needs 924,864 B of baked collision against 751,616 B of room space today, so
     this is not only the farm. The map screen's `mapPositionCheck` reads the SAT by hand: it becomes a native
     floor-polygon entry of the collision service, called when the sub screen is hosted.
  2. **Sound's memory:** `E1_ARENA_LO` 0x8cc00000 to 0x8cc80000 and the fight's 0x8cd80000 to 0x8cdc0000, applied in
     lane eng-snd1's own branch (the driver adds about 0.33 MB). The driver's own generator for the sound variant is
     accepted. The waiver's ceilings stand (1.0 ms mean, 2.0 worst); the village's one over-ceiling picture is the
     clock artefact and is re-judged with the clock fixed. The request check's 1.0 position bound is not widened:
     six village footsteps 1.05 to 1.38 units off are a finding to explain.
  3. **One owner for the main memory map** is to be briefed when eng-load1 has merged (three pressures arrived in one
     day: sound, the farm's collision, the renderer's resident sizing).
  4. **Engine composition for loading** (`core/room_change.cpp`: the hand-off statements of `gameDoordemo` and
     `gameRoomMemInit`) is accepted under H-017.10 with the statement list kept at the head of the file.
  5. **The area check is hosted, not planted:** lane eng-e2f hosts `sce_at` and `act_btn` in the default image so a door is
     noticed by the game's own code.
  6. **Approximate FSCA/FIPR maths** in the skeleton is allowed only with every fixture's outcome unchanged (the owner
     approved approximations as a class); it ranks below the memory fix.
  7. **Gate rules added:** shared pack sets are real copies with receipts; a hand-back figure that does not match the
     head is recorded with the measured figure; DOOR is an expected failure with an exact reason until its
     dependencies land; a lane's Part can be gated at a named commit (`--head`) while the lane carries on.
- **Look choices being prepared for the owner (nothing lands before they see it):** character back-face culling (still
  sheet with pixel counts, eng-draw3); Ashley's skirt options (clips, eng-cloth1: the skirt is 6.8 ms a picture on the
  hill, MODELLED).
- **Open with the owner:** the GameCube original as a third reference for disputes, or anchoring on the old port only;
  the release-line hotfix candidate (Disc 2's em1f copy of em10 lacks the Ganado byte-order correction); a KOS
  upstream report for the clock.

## H-028 (2026-11-21): the drawing account is in; the renderer is rebuilt along its pixel-identical path, world and characters as two lanes

- **What lane eng-draw1 found** (its report, at the gate; MODELLED, console-build dynarec at 70 MHz, calibrated on the old
  port; the tier charges instructions and sees no cache, store queue, graphics chip or bus):
  - Drawing is 27.5 / 37.4 / 26.0 ms mean on LEON / HILL / FIGHT against the 14 ms row: the world 10.2 to 11.6, selection
    3.7 to 3.8 on the moving-camera scenes, characters 12.0 / 24.1 / 11.0.
  - 43 to 47% of the world's corners belong to strips no triangle of which is ever seen: about 5 to 6.6 ms a picture.
    The near-plane fix costs 3.7 to 5.6 ms, most of it triangles wholly behind the plane sent to the clipper. Every
    staged vertex is copied about once.
  - Characters: every header has culling off (57 to 58% of on-screen triangles are back faces); weight sets, lighting
    and emission cost well over the job.
  - Its estimate for all pixel-identical steps together: 11.0 mean / 14.9 worst (LEON), 10.2 / 15.6 (FIGHT), 14.4 / 17.8
    (HILL). So the row is reachable on the mean in two scenes and missed at the worst pictures in all three without look
    choices. Estimates, not built.
- **Rulings:**
  1. **Build the pixel-identical path now**, as two lanes on eng-draw1's head: **eng-draw2** (world: stills repeatable to
     the pixel first, then the clipper pre-reject, selection, the exact strip cull from baked cones and bounds, the world
     walked without a stage) and **eng-draw3** (characters: unused positions and normals skipped, the four kernels on
     SH4ZAM, the per-model fixed cost). Each step lands as the default with the old path removed, with a base re-run in
     the same session and 0 differing pixels against the previous step.
  2. **C on SH4ZAM before assembly.** Hand-written SH-4 assembly is a last, separate step with the C form's measured
     figure and the reason it is not enough (workspace rule of 2026-10-12); this tier cannot rank hand-scheduled code.
  3. **Look choices are the owner's and stay out of speed steps.** The first one prepared is character back-face culling
     (estimate -4.0 / -7.4 / -3.6 ms): a lab arm and a still sheet with differing-pixel counts from eng-draw3. World
     levels, character levels, a light cap and half-rate lighting follow the same way, after the pixel-identical floor
     is measured, each on its own sheet.
  4. **Pack sets (the eighth ruling of H-027, written here):** packs a disc build needs by default live in
     `E:\RE4DC-Lanes\packs\<set>\`, immutable, with a receipt (hashes, the bake script and commit, inputs, the lane);
     only the integration lane writes them, at the gate, after a clean-checkout rebuild. A default path into a lane
     folder fails the gate. `PRISTINE` is an input tree, recorded by identity in the gate log.
  5. **Flycast slots:** the lease is written before a runner touches the slot, and a slot is free only with no lease and
     no Flycast or runner running from its folder (lane eng-fix1 broke an unleased run of eng-snd1 for two minutes and
     reported it; the common brief carries the rule).
  6. **The E1 audit** (Codex) is ordered when the two drawing lanes' pixel-identical floor is measured, not before
     (H-023's condition "a drawing design that fits its row on the calibrated model" is read as: the floor known, the
     look choices listed with their sheets).
- **Corrections (lane eng-fix1, finishing its re-merge before the gate):** ten corrections built in with no way to turn
  them off, the owner's four choices in `game_settings.mk`, three guards (one counted, 0 in every scene). With the
  Ganado byte-order correction in, a hit Ganado's routine bytes differ from the first hit (tick 61) and positions
  from about tick 165 (4.4 to 4.5 units); engine and reference moved together. Quick weapon select is set on and
  reaches nothing until the sub screen is hosted.
- **Lanes now:** at the gate eng-look1; queued eng-fix1, eng-draw1; finishing eng-e2c; running eng-draw2, eng-draw3,
  eng-svcspd1, eng-bake1, eng-snd1, eng-load1, eng-e2d.

## H-027 (2026-11-21): the plan written down (version 3.2); what the PC reference is and is not; rulings from the first gates

- **Owner:** "okmemoralize that plan and ensure the skill sare up to date". Done: `ENGINE_PLAN.md` version 3.2 ("The plan as of
  2026-11-21"), `LANES.md`, `COMMON_BRIEF.md`, `INTEGRATION_GATE.md`, the rule files and the four skills (merge 9dfe2ca00).
- **Owner asked:** "In the PC the ideal reference ?" and "How does el Gigante run in reference?". Answers given, and rulings:
  1. **The PC reference is the workbench, not the truth.** It is the original code built for a third platform. Four faults
     in it were found in two days (em10's presentation callers, the BSpline alias, routine bytes, the Ganado's hit voice
     label), each one a case where engine and reference agreed and both were wrong. From now on a PC fixture counts as a
     reference only where it is anchored: the same scene run on the released old port in Flycast, agreeing on outcome and
     on chosen state at chosen ticks. A lane for that anchoring starts when the machine has room (backlog, first in line
     after the renderer redesign's build lanes).
  2. **El Gigante has no whole-fight reference.** The PC reference does not host him; lane eng-e2c checked each function on
     a planted giant. The released old port is his reference: a scripted fight there, the engine judged on outcome. Part of
     the anchoring lane. His AI and his drawing meet in one scene only after the renderer redesign (his drawing alone is
     over twice the row on the bench).
  3. **Gate rule:** a move of `engine` since a lane's merge base passes without a re-merge when the trial merge is clean and
     every moved file is a document or a tool that no image and no suite uses. `GATE.md` carries it.
  4. **A hand-back figure that does not match the head** is a lane error the integration lane records with the figure it
     measured; it fails the gate only if the control itself does not work (eng-e2b: "em10 21" and "8 clones" came from an
     intermediate build; at the head the controls give em10 11 and 181 problems).
  5. **Service code hidden by inlining** (eng-e2b's finding: the optimiser had inlined 8 of em10's service functions into
     decision functions, out of the symbol-based link check's sight). Until lane eng-e2d's general check has run on every
     image, the link check's counts, the default image's 0 included, are counts of symbols, not proof.
  6. **The boss room's thunder** is presentation: its interval moves to the presentation generator (the split rule); the
     three `static` functions may be made replaceable by build means without editing `src/`. The shift of the boss's
     behaviour stream against old-game traces from tick 1 is the split's accepted consequence.
  7. **No session links** (owner, by way of the F-Zero session: "We shouldn't put a link to Claude sessions in PRs"): commit
     and merge messages end with the `Co-Authored-By` line only. History already pushed is not rewritten without the
     owner's word.
- **State:** merged through the integration lane today: eng-salv1, eng-e2a, eng-cmp1 (the comparison, MODELLED, with its
  band). At the gate: eng-e2b (held on one question: do the reference's trace differences after the hit-voice fix touch
  behaviour state), then eng-look1 (Leon's handgun drawn live; +0.57 ms a picture MODELLED). Handed back, finishing: eng-e2c
  (boss 26 to 3; the thunder). Running: eng-draw1, eng-svcspd1, eng-bake1, eng-snd1, eng-load1, eng-fix1, eng-e2d.
- **Open with the owner:** whether the GameCube original in an emulator is wanted as a third reference for disputes
  (behaviour only, no assets), or anchoring on the released old port is enough.

## H-026 (2026-11-21): corrections, not switches; quick weapon select; reworked PS2 art; the F-Zero line's advice

- **From:** the owner (quoted) and the integrator (rulings under H-013).
- **1. What lane eng-fix1 found:** the released game carries its fixes as the old port's `RE4DC_` conditionals inside the original code; read per unit, 33 are behaviour fixes, of which the engine built 11 and the PC reference 2. With the Ganado byte-order one missing, all 32 of a Ganado's routine tests read the wrong bytes in both the engine and the reference: they agreed with each other and both differed from the released game (on the reference: Ganado reactions change from the first hit in the bell fight; kills, damage and room clear the same). The same class of fault as H-016.8.
- **2. The owner on how to carry them:** "wouldn't implementing the switches just be a workaround?", "would it make sense to rethink the switches as proper replatforming?", "we should stop calling them switches". Ruling and vocabulary, for every document and report:
  - **corrections:** what makes the original code right on this CPU and compiler (byte order; compiler and ABI). Unconditional in how the engine and the reference build the original code; the reference keeps `CORRECTIONS=0` only as a control build.
  - **game settings:** the owner's product choices (the enemy cap and its rules, the PS2 spawn rules, quick weapon select), in one file, each with who decided and when.
  - **guards:** tripwires against failures the old port had (a refused spawn, a refused effect). Counted in the scene record, expected at 0, a non-zero count fails a timing scene; a guard that never fires is removed.
  - The mechanism is "the old port's conditionals". Next, as its own lane after eng-fix1 lands: the corrections are written into the engine line's copy of the original source and the conditionals deleted by a mechanical pass proven by byte-identical objects (old-drawing-path branches removed). The engine line's source then differs from the release line's; a release hotfix is applied to both by hand.
- **3. Quick weapon select stays** (the owner: "i want to keep quiock weapon switch"). It is a game setting and an owner-chosen departure from the GameCube version. The known departures are now: the enemy cap of 4, quick weapon select, one picture of input delay from the fixed-field pacer. Where the old port added a convenience, ask the owner before dropping it.
- **4. Release line:** lane eng-fix1 found that Disc 2 builds module em1f's copy of em10 without the Ganado byte-order correction. A hotfix candidate; the owner decides; nothing on the release line was touched.
- **5. A Dreamcast look, from reworked PS2 art.** The owner asked whether rooms can be baked and made "dreamcastt optimzied", and characters given an aesthetic, "where we can stand out from the gamecube version", and then answered the open asset question: "sure the ps2 aart can be rewporedm, tetouched, reatpined etc." (read: the PS2 art may be reworked, retouched, repainted and the like). So: the PS2 version stays the only source (the no-GameCube-assets rule stands), and its art may be upscaled, retouched, repainted, re-lit and rebuilt for this console. The owner added: "ps2 was primarily to establish hthe baseline geometric shapes etc.": the PS2 version is the baseline for shapes (rooms, models, layout); textures, lighting, materials and the overall look are ours to rework. Geometry may be rebuilt for the console (distance levels, meshlets) as long as the shapes stay the PS2's (the integrator's reading). How it is run:
  - what makes the picture both cheaper and better goes into the renderer redesign itself (rooms lit offline, meshes and distance levels built for the console, clean transparency);
  - what costs frame time (shadow volumes, bump mapping, anti-aliasing) waits until the floor holds on the calibrated model;
  - the owner chooses the look from still sheets: two or three treatments of one room and of Leon, one variable per sheet, each with its count of differing pixels and its modelled cost; the chosen treatment becomes the bake recipe.
- **6. The F-Zero line's advice, adopted** (their integrator, asked at the owner's request): look for invisible work before cutting content (their drawing win was an exact, pixel-identical cull); never mix a look change into a speed arm; every still pair carries its differing-pixel count; every baked pack carries a receipt of its inputs; lanes hand back before they lose the thread (about 250 tool calls); a speed claim needs its base re-run in the same session. These are in the common brief. Their cautions, noted: twelve lanes on a saturated machine mostly queue (they run two to four); the calibration was fitted on the old port's work and may not transfer to the new renderer (a small console bench of the renderer alone would anchor it: the owner's call, not asked for).
- **7. The machine:** CPU at 98% with three projects on it. One emulator slot was added and reserved for the integration lane (`eng-e1d\int1`; the owner: "more slots is ok adjust based on computer utilization"). Lanes are not added while the CPU is saturated: as lanes hand back the count drains to what the machine carries, and a successor starts only when there is room. A lease covers only a running emulator; the integration lane has priority.

## H-025 (2026-11-21): rulings from the salvage inventory and the comparison; three more lanes

- **From:** the integrator. Authority: H-013. Sources (handed back, not yet gated): `E:\RE4DC-Lanes\eng-salv1\SALVAGE.md` (lane/eng-salv1 3e11ed9dd), `E:\RE4DC-Lanes\eng-cmp1\COMPARISON.md` (lane/eng-cmp1 68007ec63).
- **What the salvage inventory says** (54 rows; to be checked by the integration lane): the engine's bake already reads the old port's converted PS2 data (106 rooms, character packages for 97 rooms, 114 cutscene movies), so chapter 1 needs no re-conversion; Dreamcast-written parts carry over with changes (disc fixes, the AICA sound layer, the movie player, memory-card saves and screen, the crash screen, the warp and QA tools); nothing of the old drawing carries over; every room's bake needs a recording of the old game in that room; the inventory screens need 3 MB the Dreamcast does not have spare; 148 released fixes are switches inside `src/` that the engine builds off; the script scheduler is not hosted. Its sizes (low confidence): step 3 9 to 15 lane rounds with the drawing redesign, step 4 22 to 36, step 5 30 to 55.
- **Rulings:**
  1. **The sound driver is hosted under a waiver.** `src/game/snd_main.cpp` and its units are the original's sound service. They are hosted on the lifted AICA layer rather than rewritten: they make the game sound as the GameCube version does, they use their own random generator, and they are expected to be cheap. The link check prints them as waived. The waiver holds while sound costs under 1.0 ms a picture mean and 2.0 ms worst on the calibrated tier; over that, a native sequencer is ruled on. This is the first waiver of "no original service code"; another needs its own ruling.
  2. **The engine keeps game time.** The comparison shows that when a picture is late the engine slows the game (61% of game speed on the hill at the calibrated clock) where the old port drops pictures and keeps game time (76%). The player's test needs game speed held: when work for a picture overruns, the next tick runs without drawing, within a bound. A lane takes this after the drawing options are in, because the two interact; until then every modelled figure states game speed beside pictures a second.
  3. **The calibration is a band.** The standard build calibrated the same way (104 MHz) agrees with the console build at 70 MHz on the old port within 2.4% but reads the engine 6 to 10% kinder. Quote the console build at 70 as the pessimistic end and say the band.
  4. **Recordings of the old game are a bake input.** The old port stays buildable and runnable for that purpose (a source of parts, never tuned). Lane eng-bake1 lists which chapter 1 rooms lack one and what a recording must hold; a recording lane follows.
  5. **The released fixes inside `src/`** are audited by lane eng-fix1 before any are switched on in the engine; the integrator rules on the set.
  6. **Leon's handgun:** the packs hold no weapon model. Lane eng-look1 owns one new bake script for weapon models and their catalogue entries; lane eng-bake1 owns the rest of the bake; neither changes the pack format.
- **Can start now, by the inventory:** the scheduler, sound, disc safety, loading and modules, the fix audit, saves, the memory-card screen, the crash screen, room recordings, route-movie decode. **Waits for the renderer redesign:** room bakes in their final form, the weapon model's final form, effects, sky, water, shadows, the menu and inventory renderer, the video-memory layout.
- **Lanes added:** eng-snd1 (sound), eng-load1 (room-to-room loading through a door), eng-fix1 (the fix switches). Next in the queue: the scheduler, saves and the crash screen, route movies, room recordings, the game-time pacer.

## H-024 (2026-11-21): the owner: as many lanes as possible, with an integration lane, none redundant

- **From:** the owner, in conversation. **The owner's words:** "Run as many as possible with an integration lane as long as they aren't redundant". It replaces the limit of two lanes set after the 11-20 stop.
- **How it is run (the integrator's rulings):**
  1. **Ownership instead of a count.** Every lane's brief names the files it owns and the one question it answers. No two lanes own the same files or the same fault. The lanes table in STATUS.md is the register; a lane that finds it overlaps another stops that part and says so.
  2. **One integration lane** (`eng-int`, standing instructions `E:\RE4DC-Lanes\eng-int\GATE.md`) gates each handed-back lane, one at a time, and is the only one that merges into `engine` and adds the "Merged" note to STATUS.md. It does no lane work, fixes nothing in a lane and rules on nothing: a failed gate comes back to the integrator. The integrator still reads each gate report, rules, briefs and writes the hand-overs.
  3. **One common brief** for what is the same in every lane (`E:\RE4DC-Lanes\COMMON-BRIEF-20261121.md`): rules, machine, suites, Flycast slots by lease (a `LEASE.txt` in the slot), hand-back.
  4. **The machine is the limit:** 8 cores shared with two other projects (about 90% busy when this was written), 40 GB for WSL including RAM builds, four Flycast slots. Lanes build with `-j4`, one image at a time; C: under 40 GB or E: under 20 GB stops a lane.
  5. **The drift guard that replaces the count:** nothing merges without the gate; a lane's summary is still a claim; H-023's "drawing first" stands for what hosting waits on.
- **Lanes now:** eng-e2a (fight services), eng-cmp1 (comparison and calibration, finishing), eng-salv1 (salvage inventory), and new: eng-draw1 (drawing cost and options), eng-svcspd1 (services cost and fixes), eng-look1 (the handgun, then the muzzle flash), eng-bake1 (chapter 1 rooms through the bake, census), eng-int (integration). Queued until the salvage inventory and the drawing options are in: room-to-room loading and doors, sound, items.

## H-023 (2026-11-21): the disk shrink done; the first calibrated model; the owner on effects and the handgun

- **From:** the integrator and the owner. Authority for the rulings: H-013.
- **The WSL disk file is compacted** (the owner: "Yes shrink now."; all three sessions parked first). `ext4.vhdx` 414.5 GB to 304.4 GB; NTFS fragments 1,291,166 to 729,202; C: free 25.6 GB to 145.4 GB; Ubuntu up, fsync writes pass, 0 storvsc errors, the repository intact. Script and log: `E:\RE4DC-Lanes\reassess19\relaunch\wsl-compact6.ps1`, `wsl-compact6.log`. The machine rules stay (RAM builds, C: and E: checked before builds): C: fell from 50 GB to 25 GB in about 12 hours and only part of the cause was found (WSL's swap file).
- **The calibrated model corrects H-021.** The interpreter build ignores `Sh4Clock`, so it is not the strict tier. The calibrated tier is **the console build's dynarec at `Sh4Clock` 70** (fitted by lane eng-cmp1 on the old port's five console benchmark spots: match clocks 70.9 to 75.7 MHz on the four heavy spots, 97.5 on the quiet view; the standard build needs about 104). Tier label: MODELLED (console-build dynarec at 70 MHz, calibrated on the old port).
- **What it says** (lane's figures, to be gated): the engine holds the floor nowhere fully: village route 28.9 pictures a second, fight 24.2, hill 18.3. Drawing is 26 to 37 ms against a 14 ms row; services 7 to 18 against 9; behaviour under 1. In plain Flycast the old port needs 1.3 to 1.6 times the engine's work on the same scenes, with the engine drawing and running less.
- **Rulings:**
  1. **Drawing first.** The plan's own rule for "over 20 ms at the cross" applies: a drawing redesign round before hosting more of the game. Next lane after eng-cmp1: where the drawing time goes, phase by phase, on the calibrated tier (visibility, skinning, transform and light, clipping, submission), then options with their modelled gain. Lanes already running (the fight image's services, the salvage inventory) finish; no new hosting lane starts before the drawing options are in.
  2. **E1's milestone audit** waits for a drawing design that fits the row on the model; auditing a floor the model says is missed would only confirm it.
  3. **The handgun.** Leon's handgun is drawn in the first picture and not after (the owner saw it in the side-by-side sheet; the first audit listed it; lane eng-e1o's note that it "is drawn" was wrong and the integrator repeated it). Top of the look fixes, ahead of any effect.
- **The owner on effects (2026-11-21):** "We should probably be selective with the effect layer if we are getting these gains without them." Read as: effects are not brought over as a layer. Each is added on its own with its modelled cost and a still pair: gameplay feedback first (muzzle flash, hit blood, enemy weapons), then scene-defining ones (the village pyre), then ambient ones only if the budget allows. The owner approves the look from stills.
- **To correct in the rule documents** (LANES.md section 3, AGENTS.md rule 3, the test-rig skill): "strict Flycast" means the console build's dynarec at the calibrated clock, not the interpreter.

## H-022 (2026-11-21): the rule documents follow H-019 to H-021; E1's milestone audit

- **From:** the integrator. Authority: H-013; the owner asked "do we need to update agent.md etc?" and said "Fix it".
- **Done:** `AGENTS.md`, the repository `CLAUDE.md`, `CODEX.md`, `ENGINE_PLAN.md` (version 3.1: a dated Amendments section, superseded sentences marked, none deleted) and `LANES.md` now carry the owner's directions of 2026-11-21 and the gate and audit rules of H-014 to H-021. Outside the repository: the workspace `CLAUDE.md`, `OPT-TRACK.md` and the four skills (re4dc-engine, re4dc-engine-lane, re4dc-engine-audit, re4dc-test-rig).
- **Rulings made while doing it:**
  1. The half-budget rule stays for uncalibrated figures (plain Flycast, the PC model before it is re-fitted). A calibrated strict-Flycast figure is judged on its worst case against the full row at the defensive clock.
  2. Step 6 starts when chapter 1 holds the floor on the calibrated model; each enhancement is still the owner's to approve from stills or a clip.
  3. "Behaviour code itself is not rewritten" is the default; a decision function goes native only where the model shows it hot, with the outcome check, and each case is ruled here.
  4. A lane that changes a Flycast slot's settings keeps the original, restores it before hand-back, never touches a slot another lane uses, and logs `Dynarec.Enabled` and `Sh4Clock` with every number.
- **E1's milestone audit** (replaces H-018's "on the console logs"): once the calibration exists (lane eng-cmp1) and the E1 scenes have calibrated figures, one Codex audit judges E1 on the code, the gates and the model. If it passes, E1 is "finished, modelled, not on console".

## H-021 (2026-11-21): the owner: no disc until the replatform is complete; model the console ourselves

- **From:** the owner, in conversation. **To:** the integrator and lanes.
- **The owner's words:** "I don't want to look at a disc until we've coloelrter the replatforming - you can tell by the code where complexity is. You can also use a stricter emulator build for Flycast look that up so you can do Your own defense modeling."
- **The integrator's reading:**
  1. No console evening, SD card or date is asked of the owner while the replatform (plan steps 2 to 5) is under way. A milestone's console run is deferred, not waived; a milestone that has its audit and its model is "finished, modelled, not on console", never "done".
  2. Speed is judged meanwhile by a **defensive model**, with every number labelled:
     - **strict Flycast:** the interpreter build (`Dynarec.Enabled = no`; this project's console-like slots `fly1`, `fly2`) with the upstream `Sh4Clock` option (`[config] Sh4Clock`, MHz, default 200; in upstream since v2.2, ours is v2.7-14-g12bb43652). The clock is calibrated on the old port: its five benchmark scenes have real console means (Test 27.1), so the clock at which Flycast reproduces each is measurable. The lowest clock any scene needs is the defensive clock; the spread across scenes says how far one factor can be trusted;
     - **cost read from the code:** per-picture counts (vertices, bones, queries, draw calls, bytes touched) from the images' own counters and the PC hardware model (the MODELLED tier, known to under-read the console by 1.3 to 2 times: to be re-fitted on the same five scenes);
     - a figure passes its budget row only with margin: the model's worst case, not its mean, against the row.
  3. Where the code says the cost is (the hill's drawing, over its 14 ms row in plain Flycast) is where speed work goes, judged on the defensive model. H-020's "speed waits for the console" is replaced by "speed waits for the calibrated model".
  4. What the model cannot see is listed with every modelled number: the graphics chip's fill and sort time, vertex submission through the store queues, memory bus contention, real disc timing. Those stay console risks until the deferred run.
- **Work:** lane eng-cmp1 adds the calibration (the old port's benchmark scenes in the strict Flycast at several clocks, then the engine's scenes at the defensive clock). The one console disc stays on the shelf, rebuilt when a milestone closes on the model.
- **Unchanged:** the owner still approves look steps (from stills), asset sources, releases and admin steps on the machine.

## H-020 (2026-11-21): the hold on step 3 is withdrawn

- **From:** the integrator, after the owner asked "Have we really gotten as far as the replatform can go?". Authority: H-013.
- **Ruling:** H-017 and H-018 said step 3 would not start before the owner had seen E1 on the console. That was stricter than the plan, which says that when the console is not available work moves to things whose value does not depend on timing (ENGINE_PLAN section 7). The hold is withdrawn for such work.
- **What may run without the console:** native services for the fight and boss images (judged by link check and by outcome against the PC reference); hosting of game systems chapter 1 needs (room loading, doors, items, sound, events); the look items the owner approves from still pairs.
- **What still waits for the console:** anything about speed (the hill's drawing is over its 14 ms row in Flycast), content cuts, pacing and input feel. No model-only speed round.
- **Limits unchanged:** at most two lanes; every merge through the integrator's gate; E1 is "finished, unaudited" until its console run and the audit on its logs.
- **Now:** lane eng-e2a (the fight image's 114 service functions) beside lane eng-cmp1 (measurement).

## H-019 (2026-11-21): the owner on comparing with the old port

- **From:** the owner, in conversation. **To:** the integrator and lanes.
- **The owner's words:** asked "How does the new engine compare to the old engine" and "Why aren't we comparing apples to apples?", then: "We don't want to get stuck in the exact loop and we need a brand new architecture. But customers need to know how much faster the game will run."
- **What it changes (the integrator's reading):** the 11-19 rule stands: no lane improves, tunes or profiles the old drawing path, and the engine is judged on the absolute budget. Added: the old port may be measured as a baseline beside the engine, on the same scenes, the same machine tier and the same measure, with what each side draws and runs stated beside the number. Nothing chases exact agreement between the two.
- **Customer-facing speed claims** need a console number and the owner's OK before anything is posted. An emulator ratio is labelled as one.
- **Work:** lane eng-cmp1 (Flycast, measurement only) now; the console evening measures both on hardware (the lab disc already holds the old game with per-picture intervals).

## H-018 (2026-11-21): E1 fourth audit (Codex): not passed, four items; integrator rulings; no fifth paper audit

- **From:** the integrator. **To:** lanes and the next integrator. Authority: H-013. Report: `E:\RE4DC-Lanes\audit-e1d\AUDIT-E1D.md` (audited `51405fc87`; the staged disc is built from it).
- **Closed by the auditor:** H-017 items 1, 2, 4 (HUD and PUB), 8, 9 and 11; the staged disc and both control discs.
- **The four open items, and the ruling on each:**
  1. **Camera tracks converted in play.** The fight's cut is exported and converted when the cut starts. Ruling: every cut in a room's camera data is exported and converted when the room is loaded; a cut switch in play is a lookup. The track store is sized per room at load and a room that does not fit refuses to load, loudly. The `E1 CAMTRACK` line reports conversions in play, and the selector fails a scene where that is not 0.
  2. **A refused motion export** is honoured first: the constructor checks the refusal before it reads a header, takes a lease or relocates anything. The exercise checks the buffer and its guards again after construction and a move, with an invalid count and with stale contents.
  3. **Selector.** The whole after-play memory line is consumed (mallinfo free included); the scene's tick count and the fields counted are cross-checked against the rows actually received; each field ends at its own delimiter and is range-checked; the schedule is read whole (no 4,095-byte cut) and a line that does not parse fails the schedule. Each with a control scene or a control schedule built from the repository script.
  4. **Disc reads in play.** Reads on disc-backed handles and CD sector requests are counted beside opens (`fs_read` on `/cd` handles, `cdrom_read_sectors` and its `_ex` form); the summary prints all three and the selector fails a timing scene where any is not 0. Control: a file opened before play and read at picture 100 fails its scene.
- **No fifth paper audit.** Four audits in one night have each returned a shorter list; these four items are mechanical and each has a control. The integrator verifies them at the merge gate with the controls re-run on Flycast, and the next independent audit is the one the plan asks for: on the console evening's logs, for the milestone. This returns to "one independent audit per milestone, no review per change".
- **Order from here:** lane eng-e1p; rebuild and boot the disc; then the console evening. Step 3 does not start before the owner has seen E1 on the console.
- **Open with the owner:** a date for the console evening; the yes for the WSL disk compaction; three still sheets (HUD, near plane, overall).
- **Machine note:** the nightly job "RE4 WSL Backup" (`C:\Game Dev\Emulators\_private_tools\wsl-backup\wsl-backup.sh`) wrote 24 GB to `E:\WSL-Backup` on 11-21 because it bundled each repository's unpushed commits once per worktree (three local `wip/*-20261120` branches hold about 100 MB of build output and packs). The script now bundles once per repository; 225 byte-identical duplicates were removed with a map (`E:\RE4DC-Lanes\reassess19\hygiene\DEDUPED-wsl-backup-bundles-20261121.tsv`).

## H-017 (2026-11-21): E1 third audit (Codex): not passed, list shorter; integrator rulings

- **From:** the integrator. **To:** lanes and the next integrator. Authority: H-013. Report: `E:\RE4DC-Lanes\audit-e1c\AUDIT-E1C.md` (audited `5f490e427`; the staged disc is built from it).
- **Closed by the auditor:** the outcome reader's four gaps; the shot on the engine against the PC reference (no reference data reaches the engine); the camera bodies named in the second audit; the camera against the reference on village, hill and shot scene; the loosened comparison reversed; the staged disc and its boot; the five record controls; the three reference changes judged real in the source.
- **Open, and the ruling on each:**
  1. **Evaluation inside hosted decision bodies.** `CameraQuasiFPS::move` keeps its follow filter and transforms; `CameraPushObject::move` inverts and transforms. Ruling: the decision stays hosted (which site, which ratio, which door); the filter, the inverse and the transforms move into the camera service behind thin calls. The allowed list names both functions with a size ceiling so growth is seen.
  2. **Camera motion tracks.** `HermiteInterpolation` and `CameraMotion` in the engine follow the original's key walk. Ruling: camera tracks are converted once, when the camera data is loaded, to the engine's key segments and evaluated by the engine's existing motion-key evaluator (the one actors use since eng-svc2). No history walk at run time. Conversion at load is loading work, not per-tick work.
  3. **The motion writer** (`HermiteExport`): count and capacity are validated before anything is written; a control overruns it and is refused.
  4. **HUD digits.** The renderer derives the three glyphs from the live magazine count when it draws them (drawing work, in the drawing row). Nothing is built per tick.
  5. **The PUB line** counts only what has a producer: the camera copy control and light-view misses. A light-view miss fails the scene. Zero publication is otherwise established by reading producers and consumers at audit, not by a counter.
  6. **Selector.** A timing scene needs: camera ticks checked equal to the scene's ticks; a complete numeric after-play memory line (a drawn scene may not print the headless sentinel); run kind and headless mode taken from the schedule, not from the image's own label; strict number parsing. Each with a failing input.
  7. **Boot switches** are read once before play. No file lookup inside a picture; the in-play disc read count in the summary must be 0.
  8. **Reference controls.** Each reference change keeps its old behaviour as a switchable build and a row that is run: unsplit em10 callers, the i386 floats-first alias, the old routine bytes. `camcheck.sh` counts the plays-right exit; `camengine.sh` fails when a requested row is skipped or the window is short.
  9. **Re-derive on the fixed reference** before citing: the hill's 729 records (Leon and Ashley), the eight float-library fixtures. Stills, visibility counts and Flycast draw figures taken before the near plane fix are retired; a corrected-view still sheet replaces the look evidence.
  10. **A hosted body that cannot be split.** `CameraQuasiFPS::move` mixes decision statements with inline evaluation and `src/` is not edited, so it is an engine composition: it calls the hosted decisions and the camera service, and the six decision statements it re-expresses are listed line by line in SERVICES.md 48d.1. The allowed list holds the original at a ceiling of 0. This is the only such function; another needs its own ruling.
  11. **Schedules.** The selector runs at most 8 scenes; a longer schedule is refused by the disc script and fails in the selector. Control scenes are built from the repository script, never from a lane wrapper.
- **After these two lanes:** rebuild and boot the disc, repeat the selector controls, and ask the auditor for a verdict on these nine items only. Step 3 (the fight and boss images' 114 and 57 service functions) does not start before the owner has seen E1 on the console.
- **Open with the owner:** the HUD look and the near plane look (two still sheets); the yes for the WSL disk compaction; a date for the console evening.

## H-016 (2026-11-21): E1 second audit (Codex): not passed; integrator rulings on its list

- **From:** the integrator. **To:** lanes and the next integrator. Authority: H-013. Report: `E:\RE4DC-Lanes\audit-e1b\AUDIT-E1B.md` (audited `d13510243`; staged disc built from `00effae99`).
- **Verdict:** the code side of E1 is not passed. The console run is still owed separately.
- **What holds:** the random split on the audited paths; the village route 641 of 641 ticks against the PC reference with no feed; the heap alias fix and its controls; pool refusals failing a scene; the staged disc is the audited code (268 of 268 files hashed in place) and boots six of six scenes in Flycast; the field counter counts real display changes, 600 two-field intervals per drawn scene in Flycast.
- **What does not hold, and the ruling on each:**
  1. **Camera evaluation is service code.** `CameraInterpolation::move`, `CameraSmooth::move`, `area_hit_p3`, `area_hit_pN`, camera data relocation and the shoulder camera's base matrix are linked from allowed units as decisions; the rail replacements in `services/camera/camera_svc.cpp` (BSpline and others) follow the original bodies line for line. Ruling: the camera is one native service whose state is the renderer's camera record. Behaviour code chooses the camera mode and targets through thin setters; interpolation, smoothing, rails and area containment are the engine's own code on SH4ZAM types. Same mathematics is expected; a transcription of the original body is not accepted. `scrHitCheck` is debug drawing: a logged stub.
  2. **Publication.** The per-tick copy of the camera into a draw stream, the four HUD words and the per-character light snapshot go. The renderer reads the camera service's record and the HUD's live state in place; a character's light record is written by the setters that change its inputs, not compared every tick. The skeleton's final palette (scale and column length for every published bone) is service work and stays, charged to services.
  3. **Shooting.** H-015.4 is withdrawn. The shot fixture runs on the engine with the same inputs as on the PC reference and is judged by `outcome.py` against the reference, in E1. The default image's `GetWepTargetList2` stub is replaced by the native target list.
  4. **Controlled Ashley.** E1 proves Ashley as the partner. The generic player host with Ashley as the controlled character is proven with her castle section in E4, where the plan's backlog already puts it. The E1 row in ENGINE_PLAN section 7 is corrected to say so. The owner may overturn this.
  5. **Outcome reader.** Every actor present in the reference must have every tick between its first and last sample; R rows are required when the fixture declares a room; an unrecorded position sentinel fails; yaw is compared with a tolerance. Each with a failing input.
  6. **Console record.** A scene is OK only with drawn mode, 600 distinct picture rows, 600 real flip intervals and zero release-queue drops; stack guards and RAM and VRAM floors are sampled after play, not before. Diagnostic captures (traces, stills) are never taken in a timed run.
  7. **Gate evidence.** The integrator's gate scripts write their comparison tables to files beside the make logs (the auditor could not find g6's hash tables).
- **Added 11-21 after lanes eng-e1j to eng-e1m:**
  8. **The PC reference reads routine bytes as the game does** (`RE4DC_STAT_ROUTINE_BYTES`, lane eng-e1m). A reference number recorded before `9451b0a8c` is not cited until it is re-derived. Changing the reference is allowed only with the cause shown in the original source and a control that restores the old behaviour; three such changes landed tonight (em10 presentation callers, the BSpline alias on i386, the routine bytes).
  9. **Clip distances:** the game's `ZNEAR` and `ZFAR` hold the original's values; the renderer's near and far are engine constants (`ENG_RENDERER_NEAR` 100, `ENG_RENDERER_FAR` 18,750). The near plane fix changes the picture (handgun, body parts, no unclipped slabs): the owner approves it from the still sheet.
  10. **A loosened comparison is a gate failure** unless the brief asked for it: lane eng-e1j widened every boundary-log field to 0.01 and was sent back.
- **Not ruled, for the console evening:** physical timing, input feel (fixed release against PACETMU), memory peaks through play, no play-time disc reads, the GDEMU race gate, matched stills and clips against the PS2 original, the owner's look decisions.
- **Open with the owner:** the HUD look (still sheet); the yes for the WSL disk compaction; a date for the console evening.

## H-015 (2026-11-20, late): integrator rulings after lane eng-e1h

- **From:** the integrator. **To:** lanes and the next integrator. Authority: H-013.
- **Rulings:**
  1. **cObj manager template:** `cManager<cObj>::createBack`, `cManager<cObj>::destroy` and `cObjMgr::memClear` are linked from `wep02/wep02` under that unit's allowance. They are the same service code as the cEm and cLight tables (H-014.4): offenders, native through the engine pool. Lane eng-e1i lists them as exceptions in `allowed_original.txt` and removes them. Until then the default image's "0 service functions" is 0 by the list, not 0 in fact.
  2. **HUD:** the per-widget blend from eng-e1h stays. The garbled ammo digits and the dark lens are fixed by lane eng-e1i before the E1 audit is ordered.
  3. **Pool refusals:** a refused double free or a full table is an engine fault, not a behaviour to reproduce. Every scene's log must show `POOL full 0 bad_frees 0`; a non-zero count fails the scene.
  4. **Shot and hit on the engine** is judged against the engine's own log in the fight image. A scenario shared with the PC reference belongs to step 3 (pass E2).
  5. **WSL disk file:** corrects H-014's "no compaction until a fresh copy". Compacting only shrinks the file and is the planned next step; about 86 GB was freed inside ext4 on 11-20. Only the integrator runs it (`E:\RE4DC-Lanes\reassess19\relaunch\wsl-compact6.ps1`), with the owner's yes and every session parked. Lanes still run no `fstrim` and no compaction.
  6. **Allowed list:** the line `!*/* cManager<*>::* c*Mgr::memClear*` (lane eng-e1i) is accepted: no allowed unit may carry a manager-template body.
  7. **Console disc packs:** the disc script's defaults for the village, hill and fight packs point at `E:\RE4DC-Lanes\eng-e1i\packs` (the packs after `bake/hud_fix.py`). That folder is kept. A re-bake must run `hud_fix.py`.
  8. **HUD lens:** no screen copy is involved (all 72 HUD units have trans_type 0); the dark lens was a layout fault. No Dreamcast substitute look is needed. The owner approves the HUD from the still sheet.
- **Open with the owner:** the yes for the compaction; a date for the console evening; the HUD look (still sheet).

## H-014 (2026-11-20): integrator rulings; the machine stall and the rules that follow from it

- **From:** the integrator. **To:** lanes and the next integrator. Authority: H-013.
- **Rulings:**
  1. **Frame pacer:** pictures are paced on the display's field count (two fields a picture), not on a timer. Today every E1 scene shows 3-field gaps with no late picture (lane eng-e1f, Flycast). First job of lane eng-e1g; the console disc waits for it.
  2. **Stick input:** the engine clamps stick and trigger on its pad path as the original game does. No boot switch. Fixtures stay in raw units.
  3. **Laser sight:** `cObjWep::drawLaserSight` is decision code and is allowed; `drawPoint`, `Draw_line3d_local_222` and `Draw_line3d_222` stay offenders.
  4. **Manager templates** (cEm, cLight in pl_sub and pl_npc): offenders; they go native through the engine pool.
  5. **Outcome reader:** `event_ticks` = 3 is accepted.
  6. **SH4ZAM:** commit 6d7d1e4 (zero fourth term dropped from `shz_dot6f` / `shz_mag_sqr3f` with FIPR off) stays on the local branch `re4dc/eng-svc5`. No upstream pull request is proposed now.
- **Machine stall, 11:20 to 18:26:** C: fell to 2.6 GB free. The WSL disk file `C:\WSL\Ubuntu-24.04\ext4.vhdx` (414 GB) reached 1,696,950 NTFS fragments, where Windows refuses to extend a file (error 665). Every write from WSL failed at the host (`hv_storvsc ... cmd 0x2a ... hv 0xc0000001`); ext4 stalled; Ubuntu would not start after a reboot. Fixed in place: fragments merged to 1,291,165 with `FSCTL_MOVE_FILE` (`E:\RE4DC-Lanes\reassess19\relaunch\PartDefrag.cs`), then `e2fsck -fp` returned 0 and Ubuntu started. No repository or lane work was lost.
- **Rules that follow, for every lane:**
  - Check C: free from Windows before every build and disc stage. Under 30 GB: stop and tell the integrator.
  - Build objects go to RAM (`/dev/shm`), not to the WSL disk. Discs, packs and evidence go to E:.
  - No `fstrim`, Compact-WSL or sparse change until the disk file has been copied fresh.
  - Fragment count, no admin needed: `fsutil file queryextents C:\WSL\Ubuntu-24.04\ext4.vhdx | find /c "VCN"`. The ceiling is near 1.7 million.
- **Open with the owner:** about 420 GB free on one volume, or a new drive, for the fresh copy.

## H-013 (2026-11-20): outcome over method; the integrator makes the technical decisions

- **From:** the owner. **To:** the integrator.
- **Words:** "I just want it to work as fast as possible on a Dreamcast regardless of how it works - while feeling and looking like a Dreamcast optimized version of the game. Make those technical decisions for me."
- **Read as:** the measure is speed on the real console plus a Dreamcast-optimised look and feel. Technical choices are the integrator's, recorded here as rulings. The owner is asked about console time and hardware, look and feel, asset sources, releases and admin steps.
- **Rulings so far:**
  - Enemy decision units and room scripts go on the allowed list; service work inside them stays flagged (lane eng-e1f).
  - The ROW `draw` column is the renderer's own span, the plan's drawing row; the PVR wait is shown beside it.
  - Work is ranked by console milliseconds once the console evening has run; until then by the plan's budget rows.

## H-012 (2026-11-20): plan version 3 approved; beyond the PS2 version added; work resumes

- **From:** the owner. **To:** the integrator.
- **Words:** after the retrospective and the draft plan, "Update agent .md and skills and codex.md to improve performance based on the retro"; then "Do we have in our plan to surpass the ps2 version with surreal Dreamcast strength enhancements"; then "Ok update plan and get to work".
- **Read as:** plan version 3 is approved, and "beyond the PS2 version" becomes a stated goal with its own step (step 6, after chapter 1 holds the floor on console).
- **Open:** the asset source for step 6; the console evening date; El Gigante's lighter body.
- **Started, under the retrospective's rules (two lanes, both independent of timing while the console is unavailable):**
  - eng-svc4 (step 2, PC-only), resumed from wip/eng-svc4-20261120: native versions of the remaining original service units, the link check, the strict plays-right reader.
  - eng-loop2 (step 1 preparation), resumed from wip/eng-loop2-20261120: the loader's Flycast proof and the script that builds one console disc from `engine`.
- **Not started:** eng-e1e (E1 image fixes) follows eng-svc4. The split reference for the fight (wip/eng-ref-20261120) stays parked: plays right is judged by outcome from now on.

## H-011 (2026-11-20): E1 audit (Codex): not passed

- **From:** the auditor (Codex). **To:** the integrator.
- **Audited:** origin/engine fecf63140. Report: E:\RE4DC-Lanes\eng-e1d\AUDIT-E1.md.
- **Holds:**
  - Leon and Ashley run their original behaviour code on the engine.
  - On the hill, every selected gameplay field matches re4ref for 729 ticks, with no feed.
  - Native skeleton, IK, collision queries, root and clock, and cloth are linked; ik.cpp, shape.cpp and pendulum.cpp are out.
  - The budget figures match the logs.
- **Does not hold:**
  - Original service units are still linked (section 1).
  - Per-picture conversions remain: palette repack, the light record, camera and HUD (section 2).
  - Rumble draws from the game generator (section 3).
  - The unfed village position check fails on 118 ticks, and the plays-right reader passes truncated traces (section 4).
  - Serial printing sits inside the timed rows, and the rows do not partition the same work across tiers (section 5).
  - Heap 0 and heap 4 alias (section 6).
  - The look differs beyond the listed items: Ashley's pose and the HUD gauges (section 7).
  - The staged disc predates the merge.
- **Action:** eng-svc4 (PC, running) retires the original service units, adds an allowed-function link check and makes the reader strict. eng-e1e (emulator, queued) fixes the image side and stages one final E1 image.

## H-010 (2026-11-19): native services, split random numbers

- **From:** the owner. **To:** the integrator.
- **Question:** "Is the approach drifting to porting existing code or true architecture for Dreamcast".
- **Answer given:** drawing and core are native. The services were drifting:
  - hosting lanes pulled in original service units "for now";
  - keeping every random draw in order forced native effects and cloth to copy the original algorithms.
- **Decision:** "Split it".
  - Presentation randomness gets an engine generator; the original generator serves behaviour only.
  - Plays right is gameplay equivalence plus position tolerance.
  - No original service code enters the engine image.
- **Applied:** ENGINE_PLAN.md sections 3, 8 and 11; AGENTS.md; LANES.md section 3b. Lanes eng-e2, eng-svc2 and eng-e1c were steered by message.

## H-009 (2026-11-19): look steps chosen

- **From:** the owner. **To:** the integrator.
- **Words:** "Lets go with best options", after the still sheets for L3, E2, W2 and W3 were sent with the recommendations.
- **Applied:** `CONTENT_DEFAULT_INIT` in `engine/render/content.h`: character distance levels step 3 and effect cap step 2 on by default. World cap, far-prop cards and baked lighting stay at step 0. A window can still ask for `.L0` / `.E0` for console A/B.
- **Measured (MODELLED, eng-look):** L3 -0.45 ms cross / -0.48 hay-fork; E2 -0.04 ms; no visible change on the sheets.

## H-008 (2026-11-19): Ashley and the bosses on the engine

- **From:** the owner. **To:** the integrator.
- **Words:** "we should have leon ashleyh and boses plus neon or ashley on the engine". Read as: Leon, Ashley and the bosses on the engine, with Leon or Ashley as the player.
- **Changed:**
  - E1 is now Leon and Ashley: the partner hosted after Leon, and the player hosting generic for Ashley's playable section.
  - E2 adds a first Disc 1 boss.
  - E3 covers every Disc 1 boss.
- **Lanes:**
  - eng-e1 was given the Ashley scope by message.
  - Lane eng-boss is briefed (E:\RE4DC-Lanes\eng-boss\BRIEF.md) and starts when an emulator slot frees.

## H-007 (2026-11-19): E0 bench audit (Codex)

- **From:** the auditor (Codex). **To:** the integrator.
- **Commit audited:** lane/eng-e0 renderer e28d7f2c2, hand-back 46cb02609. Report: E:\RE4DC-Lanes\eng-e0\AUDIT-E0.md.
- **Holds:** the speedup is real (cross 45.4 to 14.2 ms mean MODELLED, hay-fork 99.7 to 16.1). The timed path does every drawing step at run time; no captured pick lists, pre-projected corners or shadow packets.
- **Does not hold or only partly:**
  - Console entry: 25 of 25 cross pictures over 7 ms MODELLED. Estimated console mean 18.5 to 28.4 ms against the 14 ms row.
  - A clipping error: a multi-bone part can skip near-plane clipping.
  - Baked visibility is validated only on the recorded route, reuses a cell's mask at any camera height, and at 7,260 bytes a camera cell cannot scale to a whole room.
  - Look: mean absolute error 9.89 (cross) and 7.72 (farm) levels; lighting, flames and the weapon differ, beyond hair and HUD.
  - Memory accounting is incomplete; texture copies stay in main RAM.
  - The hand-back said every cross picture was over 14 ms; the files show 14 of 25.
- **Action:** lane eng-e0b fixes these (not a speed round). Content changes still wait for the owner.

## H-006 (2026-11-19): plan version 2, the F-Zero X approach; lanes move to Claude Opus

- **From:** the owner. **To:** the integrator.
- **Words:** "Write a plan for the right path forward - we should take the same approach as the fzero session can you ask it how it won", then "Update instructions and switch to opus to get this work done".
- **What the F-Zero coordinator said (11-19, all emulator numbers, no hardware run yet):** about 37 ms of its gain came from no longer hosting the original simulation (22.1 ms) and the publication layer that converts original state into draw data (17.3 ms); changing what is drawn bought the last 5 to 8 ms. It says RE4 is probably missing a whole-frame budget with hosted-original rows, owner-approved content changes, a worst-interval floor gate, and an early console run of the bench.
- **Changed:** ENGINE_PLAN.md rewritten as version 2 (budget rows, no publication layer, host only decisions, content for this console, milestones E0 to E4). AGENTS.md, CLAUDE.md, CODEX.md and LANES.md updated: lanes run as Claude Opus agents, Codex audits each milestone, one model-only round per milestone, lane limits two build plus two PC-only.
- **Waiting on the owner:** approval of E0 to E4 and the budget rows; the content look calls; the SD card.

## H-005 (2026-11-19): scope widened to the whole game in a native engine

- **From:** the owner. **To:** the integrator.
- **Words:** "I don't want to pile on improvement for old work - ensure we are following the guidance and lessons learned to go native." Then: "I want all of the game in a new native improved engine", choosing "Engine owns everything, original behaviour hosted on it".
- **Meaning:** the engine is the program (main loop, memory map, loading, renderer, effects, skeleton, collision services). The original AI, event and script code is hosted on it. Hot systems become native services one at a time, in console-profile order, each proven to play the same. Behaviour code is not rewritten.
- **Changed:** ENGINE_PLAN.md sections 1, 3, 4, 6 and 8; AGENTS.md goal and direction. M2 is now the engine shell; M3 is native services round 1; M5 is the rest of the game.
- **Lanes:** eng-bench continues (renderer, absolute budget). disc2-play handed back its chapter 3-1 play-through work. New PC-only lane eng-shell-map: the service boundary between behaviour code and the engine.

## H-004 (2026-11-19): guideline check (owner asked "Are we still operating under the right guidelines")

- **Holding:** lane limits, tiers on every number, no input sent to windows, Codex builds and Claude audits, SD card / GitHub / SH4ZAM boundaries.
- **Drift and fix:**
  1. Model-only rounds: M1 round 3 is the last before a console run.
  2. Briefs caused 4 of 5 lane stops: an integrator brief checklist goes in LANES.md section 7.
  3. M1 thresholds disagreed: one table in ENGINE_PLAN.md section 4.
  4. Mid-milestone audit: an exception is written into LANES.md section 5.
  5. Bookkeeping: OPT-TRACK.md and these hand-overs brought up to date.

## H-003 (2026-11-19): M1 round 2 audit

- **From:** independent auditor (Claude). **To:** the integrator.
- **Commit audited:** lane/eng-bench 0b6f207ca.
- **Finding:** the claimed MODELLED -51.7% (cross) and -45.6% (hay-fork) are not like for like. Like for like: -3 to -5.5 ms (18-30%) and -8 to -10.5 ms (22-28%).
- **Evidence:** E:\RE4DC-Lanes\eng-bench\AUDIT-M1-R2.md.
- **Action:** round 3 steered (STEER-004): the whole drawing path at runtime from logic outputs, a fair one-tick baseline, compact whole-room bakes, 20+ timed pictures.

## H-002 (2026-11-19): plan approved

- **From:** the owner. **To:** the integrator.
- **Words:** "get to work", then, asked to confirm, "Yes, all 10 as recommended". All ten recommended answers in H-001 stand.
- **Added the same day:** "the engine needs to leverage sh4zam or improve upon it if there are shortcomings" (ENGINE_PLAN.md section 3, AGENTS.md).
- **Console:** "Later, prepare it and wait". The lab disc is prepared; it goes on the SD card when the owner says the card is in.
- **Next:** `engine` branch from this commit; lanes lab33 (M0) and eng-bench (M1).

## H-001 (2026-11-19): plan proposed, owner decisions needed

- **From:** Claude (self-assessment session). **To:** the owner.
- **Commit:** this branch, `docs/reassess-20261119`, from `t15/int` a5aca9cf9. Docs only. No image.
- **What it is:** [ENGINE_PLAN.md](../ENGINE_PLAN.md), [LANES.md](LANES.md), rewritten `AGENTS.md` and `CLAUDE.md`, new `CODEX.md`.
- **Numbers:** all from the console session of 2026-11-11 and the A/B of 2026-11-12 (Test 27.1). Nothing new was measured.
- **Decisions needed:**
  1. Confirm the goal and the bar: 30 fps as the floor at the benchmark scenes; "plays right and looks right", not bit-exact.
  2. Approve the engine line: a new renderer proven on a bench image first, then in the game, instead of more switches in the legacy image.
  3. Retire knob-off identity and STRICT as gates on the engine line. They stay for hotfixes on the release line.
  4. Freeze speed work on the legacy drawing path.
  5. Book the M0 console session.
  6. Order of the room work while the renderer is rebuilt.
  7. Who audits each milestone.
- **Not done:** no code, no build, no console run. The contributor documents (`CONTRIBUTING-PORT.md`, the kit) still describe the release line and are correct for it; they change when the first engine-line release ships. Three front-page lines still point at the old `CLAUDE.md` content (`README.md` line 463, `port/dreamcast/README.md` lines 54 and 120); they are updated when this branch is approved and merged.

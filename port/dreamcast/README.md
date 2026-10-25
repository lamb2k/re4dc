# Resident Evil 4 Dreamcast port

**This folder is the native SH-4 / KallistiOS target: the recovered GameCube game, built for the Dreamcast.**

## At a glance

For players. The full player guide is the [root README](../../README.md).

- **Current build:** Test 24, on the [releases page](https://github.com/lamb2k/re4dc/releases/latest): PS2
  weapons, HUD, inventory, animation, sounds and chapter 2 props, and the Blacktail can be equipped.
- **Playable:** New Game to the end of chapter 2-3, at the castle gate (r200).
- **Testers:** the release also has a **QA build for testers** with teleports and a Diagnostics page.
- **Next:** Test 25, see [Coming soon: Test 25](../../README.md#coming-soon-test-25).
- **Runs on:** a real Dreamcast with GDEMU, or Flycast.
- **Problems:** see [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md), and report new ones with the
  [Game bug form](https://github.com/lamb2k/re4dc/issues/new/choose).

## How the port works

- **Gameplay is the GameCube's.** The recovered game code runs collision, events, game state and AI unchanged.
  Rendering changes must keep the logic trace identical.
- **Dreamcast services replace the GameCube's.** Native code handles graphics (PowerVR), audio (AICA), disc reads
  and VMU saves.
- **Assets are converted offline.** Room worlds, characters and textures come from the GameCube and PS2 data in
  Dreamcast formats (VQ, PAL4, PAL8). No game data is committed.

## Build it

1. **Clone with submodules:** `git clone --recurse-submodules https://github.com/lamb2k/re4dc.git`.
2. **One command:** `bash port/dreamcast/contrib.sh` builds the toolchain once, builds the program and puts it on
   the latest test disc.
3. **By hand:** follow [CONTRIBUTING-PORT.md](CONTRIBUTING-PORT.md) (toolchain, `build-public.sh`,
   `tools/swap-program.py`, disc format).

## Where things are

| Path | What it holds |
| --- | --- |
| `game/` | The recovered game build for the Dreamcast and its make knobs |
| `tools/d367/` | Release recipes, test harness, disc and texture tools ([README](tools/d367/README.md)) |
| `tools/` | Converters for rooms, characters, textures, audio and movies |
| `docs/` | Plans, checkpoints and [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) |
| `tests/` | Tool unit tests (`python3 -m unittest` in that folder) |
| `room/`, `motion/`, `kos/` | Early native demos and smoke tests (history below) |

## Developer reading list

- **Goals and decisions:** [D367_THIRTY_FPS_ROUTE.md](docs/D367_THIRTY_FPS_ROUTE.md).
- **Build recipes and knobs:** [tools/d367/README.md](tools/d367/README.md).
- **What goes into a test build:** [D367_PLAY_BUILD_CHECKLIST.md](docs/D367_PLAY_BUILD_CHECKLIST.md).
- **Working rules:** the root [CLAUDE.md](../../CLAUDE.md) and [AGENTS.md](../../AGENTS.md).
- **Release history:** the [releases page](https://github.com/lamb2k/re4dc/releases) and the "Earlier builds" list in
  [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## First checks on the host

```sh
make -C port/dreamcast -f Makefile.host test
```

This builds a host ABI probe, runs the port-blocker inventory and the tool tests. It does not test the Dreamcast
runtime. The toolchain bootstrap used by the early milestones is `port/dreamcast/tools/bootstrap_kos.sh --build`
(details in the history below).

## Engineering history (September 2026)

The notes below are the September 2026 record of the r100 cutover milestones, kept for their measurements and
commands. Their "current" wording is out of date: the game has moved on to the D367 route and the test releases.

<details>
<summary>Show the September 2026 engineering history</summary>

This directory contains the native SH-4/KallistiOS target. The GameCube build is
the behavior/state authority; GC and PS2 provide candidate visual inputs. Dreamcast-native data,
precomputation, visibility, math, texture, and PVR paths determine how that work
runs on the target.

**Current objective (2026-09-21): advance the source-driven playable port from
normal boot through a working title/main menu and the first three fully playable
rooms** (New Game, required gameplay/events/combat, audio, transitions, death and
retry; cutscene presentation skipped for now with source completion effects
preserved) by compiling the recovered game through explicit
Dreamcast platform interfaces, keeping the accepted room/character/lighting
presentation and the 30 fps at 640x480 target of the
[real-time plan](docs/REALTIME_PATH.md). The recovered game now boots into its
frame loop with the title task running on the target
([R4 game boot checkpoint](docs/R4_GAME_BOOT_CHECKPOINT.md)); the
[playable path](docs/PLAYABLE_PATH.md) sets the milestones. Historical R0-R3
labels are checkpoint records rather than the task order.

See the root [AGENTS.md](../../AGENTS.md) and [CLAUDE.md](../../CLAUDE.md) for
shared implementation instructions, current working folders and backlog routing.

## Current status

The active milestone is [the r100 native static cutover](docs/R100_NATIVE_CUTOVER_GOAL.md):
source-authoritative simulation drives production D349 native room packages and
renderer. The generic live GX/ModelPart bridge is fallback for unconverted
content. GC and PS2 are first-class offline visual inputs; D353 prelighting and
the existing converter/package/texture/lifecycle mechanisms are reused.

D361's 128 KiB retained preparation reduced matched render p50 from ~1,563 to
~1,368 ms. D362 (`62414dc`) recovered **34,016 source-heap bytes** through exact
UV sharing, with **116,704 bytes free/largest** and no material CPU gain.
D362 render p50/p95 is **1,368.093 / 1,370.801 ms**; page-flip p50/p95 is
**1,389.602 / 1,406.282 ms**. [Evidence and limits](docs/R4_NATIVE_PREPARATION_CHECKPOINT.md).
D362 closes lossless scavenging; the next deliverable replaces expensive static
render backing and runtime work, not another bridge cache or spare-KiB hunt.

Source-driven menu, room, Leon and HUD presentation exist at 640x480. The native
static cutover, responsive complete encounter, gameplay audio, inventory,
transitions/retry and physical hardware remain unaccepted. Preserve the current
source-facing correction, live state and single PVR owner. Historical D349's
~49-58 ms CPU result is a smaller-workload reference, not current recovered FPS.

The documentation checkpoint does not promote inherited uncommitted source or
asset changes. Exact working paths and the active goal are in [CLAUDE.md](../../CLAUDE.md).

### Retained integration checkpoints

D320 loads a compact qualified r100 archive directly: **4,669,568 ->3,812,576
bytes**, recovering **856,992 source-heap bytes**. The required **1,126,272-byte
block pool now allocates** and blocks0-2 load/create. Source title/menu remains
visible. The shared texture path uses the existing 64 KiB storage buffer for
bounded native uploads; no full package is staged on the source heap.

D322 and D324 extend the same native path to qualified persistent core HUD/effect
textures. At D324 the core reservation was **1,501,312 bytes**, down from
2,310,144: **808,832 cumulative source-heap bytes recovered**, including another
473,696 since D322. Core paths now convert through their source layout; palette,
mip, CPU-noise and unreviewed backing remain. D330's subsequent effect compaction
sets the current core reservation to **1,360,608 bytes**. The full reference is selectable.

D340 adds selectable `EVENT_FILES=1` backing for qualified immutable EVD
preloads. It reuses `le_mirror` qualification, the native DVD root, existing
64 KiB storage reader, and source `cDataUnit` ownership. Source compaction moves
the file reference without allocating a whole-event scratch buffer. Actual
installation validates each payload chunk into the caller's final allocation;
mutable parking/swaps are explicitly rejected, not silently restored from disc.

A 450-second reference run reproduces the 694,560 /669,248 /309,632-byte
compaction failures with 41,472 bytes free. The kept candidate completes all
three moves without these failures. Four preparations read 372 metadata bytes,
zero EVD payload bytes, with worst observed preparation wait 16,384 us. No event
installation occurs in this run; that transport is host-tested, not yet exercised
by target event activation. The rejected full-preload-read variant took up to
18,228,242 us. These are emulator integration observations, not an FPS benchmark.

Required block/enemy allocation points remain 2,582,048 /1,466,528 free. Later
heap free and largest block both remain 41,472: **zero additional heap recovered**.
The change avoids failed scratch demands rather than freeing previously allocated
storage. No new payload arena or VRAM allocation; ELF text/data/BSS are
2,295,200 /76,836 /673,048 (+2,896 text, +32 BSS versus D339). The 540-byte
compiler-reported transfer stack excludes callees and is not a total stack peak.

Source title/menu and diagnostic room output remain visible. Delivered UP at
retrace 9011 moves Leon from approximately (-99,692,-454,-1,344) to
(-94,864,-123,-3,059); R at 21025 exercises the source aim path. These are
scripted controller observations, not manual encounter acceptance. Source frame
1483 is reached; the capture stops at its 450-second deadline, not a game crash.
Materials/lighting, event activation and mutable snapshots, full audio, inventory,
combat, transitions/retry, performance and hardware acceptance remain open.
Simpler water remains a selectable, unimplemented candidate.
See [D340](docs/R4_EVENT_ENEMY_CHECKPOINT.md#d340-qualified-immutable-event-backing).

D339's part-local position cache and D338's source cull correction remain.
D339's prior matched-frame emulator interval median was 1,437.144 ms; D340
does not supersede that with a controlled performance comparison. Do not repeat
the cache, strip/chunk or cull work, or mistake the unlit diagnostic backend for
the complete accepted cabin presentation.


ARAM/event/audio, inventory, full manual controls, transitions/retry and physical
hardware remain open. The first three source rooms remain the objective.

D314 remains the first verified source warning/main-menu presentation checkpoint;
D315 fixes the post-title native task-stack failure; D316 recovers319,488 bytes
through the source primitive lifetime. Those historical allocation failures are
superseded by D320. D319 independently proves compact VQ upload using a retained
candidate; PAL4/PAL8 are still analysis and moving-scene VQ quality is unaccepted.
See [the texture checkpoint](docs/R4A_TEXTURE_INVENTORY_CHECKPOINT.md).

Smaller native render assets are authorized selectable candidates, with source
gameplay/complete components preserved and actual RAM/CPU/visual checks. PS2 mesh
substitution alone cannot meet the current 66%-size enemy target: GC mesh backing
is only 11.60% of that archive. Texture and motion storage require attention too.

## Preserved scene-runtime visual and performance references

The measurements below describe `room/` reference builds. They are not timings
or acceptance results for the active recovered `game/` executable.

The corrected-character presentation at commit `dba07e2` remains the audiovisual
reference. Its 32-second Flycast video with game audio is retained at
`C:\Flycast-Evidence\re4-dreamcast\d202-current-progress-video-audio-dba07e2`.
Leon uses the source body, costume, head, hair, eyes, Red9 hands and handgun;
the Ganado uses the correct right-handed hand/hatchet assembly. Room, source
camera, selected lighting, HUD, transparency, collision, and combat remain intact.

R3r is now the Dreamcast regression and performance baseline. R3p remains the
preceding reference and is described below because R3r is measured against it. It fixes a real
actor-lighting defect: the old runtime overwrote transformed source normals with
lighting output while later work items could still reference those normals.
The corrected path keeps immutable normal scratch separate from per-work-item
lighting. The converted packages prove the traversal was unsafe: Leon has only
5 identity entries in 6,413 lighting work items and Ganado has only 5 in 1,900.

Against R3o over matched ticks 165-1194, R3p reduces CPU frame
p50/p95/p99 from 87.615/90.116/90.209 ms to 86.217/88.719/88.836 ms.
TA registration p50 falls from 58.731 to 58.096 ms and actor-lighting p50
falls from 18.959 to 18.198 ms. It preserves the same medians of 327 visible
room groups, 9,155 room triangles, 11,900 actor triangles, 617 PVR calls, and
1,071,840 submitted bytes. Presented cadence remains roughly 11-12 fps, far
from the 30 fps acceptance target.

The separate normal buffers cost exactly 98,304 bytes: measured post-load
main-RAM headroom falls from 5,668,864 to 5,570,560 bytes. Both matched traces
report zero simulation overruns and zero discarded simulation time. A clean
manual smoke sampled input 1,860 times with a 12.484 ms maximum gap and no queue
drops, but did not inject combat controls and is not full manual acceptance.

A corrected dual-path build established that a KallistiOS `frsqrt` candidate
changed at most one channel value in one packed actor color over 330 captured
frames. It was rejected because it made actor-lighting p50 0.822 ms slower than
the portable square-root path. The fast path and validation build options do
not remain in production source.

The final framebuffer check is in
`C:\Flycast-Evidence\re4-dreamcast\d221-actor-normal-alias-fix-visual`.
It retains the accepted room, complete Leon and Ganado assemblies, HUD, camera,
transparency, and coherent lighting. Full-framebuffer emulation was enabled only
for that image extraction; performance results use the pinned normal Flycast
configuration. Physical Dreamcast timing and human-controller acceptance remain
pending.

Exact identities of that historical scene checkpoint:

- source `9dcd989370be7f083a9b66cfd19907fda627c893`
- KallistiOS `804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`
- kos-ports `f4faacc42faaf552625777b7709e871a827e1055`
- `sh-elf-g++ 15.2.0`
- Flycast SHA-256 `64491c005db917cc643b50e312f78c5b04ccfa77acebbe1cd07ad6371d422c8a`
- corrected visual ELF `c5ae9de436fd7b9f3770ce3e7cc40d1f37b8e2c000b3b9dfb9be5d46ce7c0e68`
- R3o autoplay ELF `191676ca573aaaec9aed99bb33c88fca3102b1d90344a8e7c4020455bf1dfbdc`
- R3o manual ELF `13857924539cec27012e1d6cdd46c9ec44ee17a5db942281b2f3caedaa3267ea`
- R3p autoplay ELF `4fd89b4e929aca49a9cdc8b7e231c9a1e33ff387cac81466d42e0d49b686a44f`
- R3p manual ELF `b265872f40b74f8fbe3cd5e7be28e4bcb73e8af2e54717d8cc5076f9ef91dd0a`
- R3r autoplay ELF `f3975be3408b2059d9c9557753d16a736d359a21d2d911e47a0d09a397bef35d`
- R3r manual ELF `7137228e6287394cbec9e12c67438bd06282a19d5410f5dd76346bba50c9859c`

R3q profiled that room path without changing any accepted code. With
`SUBMIT_PROFILE` unset the room build is byte-identical to R3p once DWARF line
tables are stripped; only the unstripped hashes above moved. Real store-queue
transport is 1.331 ms for the room and 2.580 ms in total, so submission
transport and KOS DMA are closed. The 2,048-entry room vertex cache misses
15,350 times against a floor of 15,317 distinct vertex indices, so enlarging it
is closed too. Room cost is close to 3.1 us per transformed and lit vertex, and
the blended list spends 18.917 ms on 1,718 triangles because it transforms 3.63
vertices per triangle against 1.23 for the opaque list. Every blended batch
already carries certified strips; the cost comes from R3k leaving the alpha
materials unpartitioned, so blended geometry sits in 17 groups reaching 273.83 m
against a 35 m horizon and is transformed before the depth and clip tests
discard it. See
[the R3q submission profile checkpoint](docs/R3Q_ROOM_SUBMISSION_PROFILE_CHECKPOINT.md).

R3r acted on that and is the accepted build. It rejects a native strip against a
bounding sphere before touching any of its vertices, which is order-safe because
skipping a strip never reorders a triangle that is still drawn. It also fixes a
projection error that had made every frustum test in the port too tight: KOS
`mat_perspective()` leaves `w = 1 - z_view`, so screen coordinates divide by
`depth + 1` and the projected half-extents must be measured at `depth + 1`.
`group_visible()` had omitted that since R3a and was discarding 35 on-screen
groups and 684 triangles per frame. Against R3p over matched ticks 165-1194, CPU
frame p50 falls from 86.217 to 74.139 ms and p95 from 88.719 to 74.238 ms while
the frame draws more room geometry than R3p did; the blended room pass falls from
17.820 to 3.053 ms. A gated audit build confirms no rejected strip has a
projected bounding box touching the screen, and the strip-culling build alone is
byte-identical to R3p at three matched ticks. The strip table costs 262,144 bytes
of static main RAM. Details and limits are in
[the R3r strip-cull checkpoint](docs/R3R_STRIP_CULL_CHECKPOINT.md).

R3t writes room PVR packets straight from the room vertex cache entries in the
direct-strip path and packs each vertex colour once per cache fill instead of
once per emitted record, with an eviction check that falls back to the
re-lookup path and has never fired. CPU frame p50 falls from 74.139 to
73.247 ms with byte-identical framebuffers at matched ticks; its calibrated
profile of the remaining room cost is in
[the R3t packet-from-cache checkpoint](docs/R3T_ROOM_PACKET_FROM_CACHE_CHECKPOINT.md).
R3u then re-swept the opaque child-cell size, which R3k had chosen before strip
culling existed, and moved the production package from one-metre to four-metre
cells: CPU frame p50 73.247 to 71.369 ms, p95 73.378 to 71.463 ms, 405,504 bytes
more free main RAM, the same triangles, and no room pixel changed at three
matched ticks. The sweep, the tie with 8 m, and the manual smoke are in
[the R3u cell-size re-sweep checkpoint](docs/R3U_CELL_SIZE_RESWEEP_CHECKPOINT.md).

R3v renumbers every strip vertex reference into a batch-local index at load
and resolves it through a slot table stamped with a per-call serial, so the
direct-strip path no longer hashes into the room vertex cache, compares keys,
or re-verifies against eviction. A gated probe showed only 13% of the cache's
hits crossed batch boundaries; losing them costs 604 transforms per frame and
the frame still falls from 71.369 to 68.789 ms at p50 and 71.463 to 68.883 ms
at p95, with no room pixel changed. The tables cost 413,696 bytes of static
RAM until they move into the package; see
[the R3v batch-local slots checkpoint](docs/R3V_BATCH_LOCAL_SLOTS_CHECKPOINT.md).

R3w first measured what Flycast charges for SH-4 instructions: about 3.3 ns
for anything that is not a load or store, including `fdiv` and `fsqrt`, and
about 13.3 ns for a load or store, with no floating-point latency and no
cache. Guided by that, each actor now lights its normals from a contiguous
prepared list of its selected lights instead of indexing two wide tables per
normal per light; the arithmetic is unchanged and a gated dual-path build
found zero differing bits over 676 frames. CPU frame p50 falls from 68.789 to
64.758 ms and actor lighting from 18.198 to 14.189 ms, with every other stage
identical to the microsecond. The calibration, the model, and
`tools/sh4_loop_cost.py` are in
[the R3w prepared actor lights checkpoint](docs/R3W_PREPARED_ACTOR_LIGHTS_CHECKPOINT.md).

R3x applies the same model to the room slot fill: the slot is now the seven
words the packet needs, filled by the same arithmetic, and each vertex is
resolved, filled and packed in one pass with the stat counts accumulated per
strip. CPU frame p50 falls from 64.758 to 61.229 ms and the opaque room pass
from 25.320 to 21.981 ms with identical counters and no room pixel changed;
see [the R3x slim room slots checkpoint](docs/R3X_SLIM_ROOM_SLOTS_CHECKPOINT.md).

The opaque room pass, now 21.981 ms, is the largest remaining cost, followed by
actor lighting at 14.189 ms with Leon's 10.948 ms median inside it. R3s keyed
the room vertex cache on vertex identity, cut transform-and-light evaluations by
21.5%, and was 1.274 ms slower, so that pass is dominated by per-reference and
per-record work rather than by transform and lighting; see
[the R3s identity-cache checkpoint](docs/R3S_ROOM_IDENTITY_CACHE_CHECKPOINT.md).
Do not retry room identity reuse without a different cost model. Retain the
portable evaluator as the numerical reference. Do not retry the rejected
reciprocal-square-root path without new evidence, and do not write a new
visibility test without `kProjectionDepthBias`.

Rebuild the diagnostic with:

```sh
source port/dreamcast/kos-env.sh
make -C port/dreamcast/room r100-autoplay-profile
make -C port/dreamcast/room r100-autoplay-cull-audit
```

Both diagnostics are compile-gated and absent from accepted builds.
The Linux checkout is required because upstream contains distinct `src/Tools`
and `src/tools` paths. A normal Windows checkout collapses three filename pairs.
The incomplete Windows checkout created during bootstrap was retained as
`C:\Game Dev\Emulators\re4-dreamcast-WINDOWS-INCOMPLETE` and is not a build
source.

## First runnable checks

From the repository root:

```sh
make -C port/dreamcast -f Makefile.host test
```

This builds a small host ABI probe, runs the port-blocker inventory against the
current tree, and executes the tool tests. It does not claim Dreamcast runtime
compatibility.

The generated inventory is written to
`port/dreamcast/build/host/portability-audit.json`. It is the starting worklist
for separating portable game code from Nintendo SDK, GX, PowerPC assembly,
fixed-address, and REL-module dependencies.

`tools/evidence_manifest.py` creates and validates hashed capture manifests.
Every reference/candidate comparison must include the relevant room, simulation
tick, RNG/input identity, executable, and asset-package identity rather than
relying on matching filenames.

The synthetic motion artifact is
`build/motion-sh4/re4dc-motion-smoke.elf`. It compiles prepared functions from
upstream `motion.cpp` and `ik.cpp`, the selected original model/math functions,
the SDK's portable matrix/vector routines, and the game's fdlibm. A shared
fixture runs `HermiteInterpolation` and `ikCalc` on both x86-64 and SH-4. The
host and Flycast results agree to the displayed six decimal places, and the
Dreamcast target reports `PASS` beyond frame 300. See
[the motion SH-4 baseline](docs/MOTION_SH4_BASELINE.md) for exact results and
limits.

With a verified Disc 1 image at `orig/G4BE08/re4_debug_disc1.iso`, run:

```sh
make -C port/dreamcast -f Makefile.host motion-real-host
source port/dreamcast/kos-env.sh
make -C port/dreamcast/motion real
```

The first command privately generates an ignored fixture from `pl00.drs`
model entry 0 and motion entry 117, then evaluates four frames through the
original game motion code on the host. The second build produces
`port/dreamcast/build/motion-sh4/re4dc-real-motion.elf`. No disc-derived bytes
are tracked by Git. See
[the real-motion SH-4 baseline](docs/REAL_MOTION_SH4_BASELINE.md).

Prepare the private `r10d`, Leon, and Ganado packages, then build the native
room demo:

```sh
make -C port/dreamcast -f Makefile.host demo-r10d
source port/dreamcast/kos-env.sh
make -C port/dreamcast/room
```

The executable validates the room, collision, and character packages, culls
room groups, submits textured PVR geometry, and supports analog-stick or D-pad
tank movement, SAT floor/wall collision, a shoulder follow camera,
source-derived actor animation, source-cut RGB lighting for r100, and the combat
loop. The r100 path evaluates the non-empty cabin lights from
`r100_002.LIT` cut 0, including its separate scenery/enemy ambient colours and
view-relative parallel lights. Character package v6 retains source positions,
authored normals, UV draw corners, and weight-palette identities; the runtime
interpolates each pose palette once and reuses it for position and normal work.
Source textures with alpha are preserved as
ARGB4444 and drawn through the PVR translucent list using the source default
alpha blend, so the cabin's soft shadow and cutout masks do not become opaque
black geometry. The r100 camera uses the room CAM file's area-2 camera, target,
close point, and FOV plus the original three-ray SAT wall correction; aiming
uses the matching global handgun-ready offsets. The character converter also retains the FCV
kind-1 root-motion rate used by the original `MotionMove`, so the selected Leon
and Ganado walk clips drive world movement at their authored speeds. Controls are
stick/D-pad move and turn, right trigger or Y aim, stick/D-pad vertical while
aiming, A fire, X reload, B restart, and START exit. Defeat the Ganado before
the route marker unlocks.

For the r100 build, convert the private room route graph and pass it to the
native build:

```sh
make -C port/dreamcast -f Makefile.host route-r100
source port/dreamcast/kos-env.sh
make -C port/dreamcast/room DEMO_SCENE=r100 \
  ROUTE_PACKAGE=../build/private/r100.re4rtp
```

The `r100` presentation build defaults to native 640x480 Dreamcast VGA output;
the older `r10d` engineering fixture remains 320x240. Pass
`DEMO_RESOLUTION=240p` or `DEMO_RESOLUTION=480p` to override either profile.

The converted package preserves all 66 source waypoints, 160 links, and the
complete next-hop table. The native enemy walk path follows the decompiled
`RouteCkToPos` selection rules over those data while reusing the port's SAT
line and floor queries.

The generated packages stay ignored. The first broad orbit proof and the
unoptimized gameplay view miss the frame budget. Full source meshes are the
default acceptance build; coarse clustering remains an explicit experiment.
The runtime uses a declared 35 m horizon for this bounded route, not as a
claim about the GameCube draw distance. See
[the room SH-4 baseline](docs/ROOM_SH4_BASELINE.md).
The integrated movement/collision evidence and its remaining P0 limits are in
[the walkable r10d checkpoint](docs/WALKABLE_R10D_BASELINE.md).
The source mappings, deliberate behavior bounds, controls, and full-loop
Flycast evidence are in [the Ganado P2 checkpoint](docs/GANADO_P2_BASELINE.md).
The measured LOD experiment, complete-loop replay, and remaining hardware and
presentation limits are in [the P3 prototype checkpoint](docs/P3_PLAYABLE_BASELINE.md).
The current measured optimization results are in
[the r100 R1a performance checkpoint](docs/R1A_PERFORMANCE_CHECKPOINT.md) and
[the R1b source-selection checkpoint](docs/R1B_SOURCE_SELECTION_CHECKPOINT.md).
The source collision broad-phase recovery is measured in
[the R2a SAT hierarchy checkpoint](docs/R2A_SAT_HIERARCHY_CHECKPOINT.md). The
source-selected fixed room-light contribution is prepared once and measured in
[the R1c static room-lighting checkpoint](docs/R1C_STATIC_ROOM_LIGHTING_CHECKPOINT.md).
Character package version 4 now separates sampled source positions, authored
normal identities, and UV draw corners; its fidelity, memory, and Flycast timing
results are recorded in
[the R2b source attribute-identity checkpoint](docs/R2B_SOURCE_ATTRIBUTE_IDENTITIES_CHECKPOINT.md).
The opaque room path now consumes offline winding-preserving strips while
retaining the original triangle stream for transparency and clipping fallback;
its representation, matched image check, and 23.8 ms render reduction are in
[the R3b native room-strip checkpoint](docs/R3B_NATIVE_ROOM_STRIPS_CHECKPOINT.md).
Order-certified translucent batches now use the same native path without
changing source blend order; the additional 2.3 ms reduction is recorded in
[the R3c ordered alpha-strip checkpoint](docs/R3C_ORDERED_ALPHA_STRIPS_CHECKPOINT.md).
The room-lighting path now validates its authored unit normals once and avoids
renormalizing them per frame; the packed-color proof and bounded result are in
[the R3d room-normal checkpoint](docs/R3D_VALIDATED_ROOM_NORMALS_CHECKPOINT.md).
The two source-selected camera-relative room lights now bypass the general
nine-light evaluator with an exact packed-color fallback gate; the 22.7 ms
matched reduction is recorded in
[the R3e compact room-light checkpoint](docs/R3E_COMPACT_DYNAMIC_ROOM_LIGHTS_CHECKPOINT.md).
Actor light masks are now converted to the source-ordered, eight-entry model
light list once per frame; the exact packed-color proof and 4.5 ms matched
frame reduction are recorded in
[the R3f compact actor-light checkpoint](docs/R3F_COMPACT_ACTOR_LIGHTS_CHECKPOINT.md).
Actor colors are now packed once per normal and reused by native strips while
the float clipping fallback remains intact; the 2.6 ms matched frame reduction
and 48 KiB memory cost are recorded in
[the R3g packed actor-color checkpoint](docs/R3G_PACKED_ACTOR_COLORS_CHECKPOINT.md).
Character package v5 now preserves source BIN normals and their reusable weight
palettes instead of rebuilding normals from deformed triangles. Its bounded
direction error, 2.7 ms normal-stage reduction, and temporary RAM cost are in
[the R3h source normal-palette checkpoint](docs/R3H_SOURCE_NORMAL_PALETTES_CHECKPOINT.md).
The R3p runtime now keeps transformed source normals separate from lighting
output; its correctness proof, 98,304-byte scratch cost, measured speedup, and
rejected `frsqrt` subexperiment are recorded in
[the R3p actor-normal alias-fix checkpoint](docs/R3P_ACTOR_NORMAL_ALIAS_FIX_CHECKPOINT.md).
Character package v6 now removes the redundant baked mesh poses and reuses one
prepared source palette for both positions and normals. Its 5.34 MiB live-RAM
gain and matched performance result are in
[the R3i source position-palette checkpoint](docs/R3I_SOURCE_POSITION_PALETTES_CHECKPOINT.md).
The recovered memory also permits a measured 2,048-entry room vertex cache;
larger candidates were rejected after reaching the same reuse ceiling in
[the R3j cache-bound checkpoint](docs/R3J_ROOM_VERTEX_CACHE_BOUND_CHECKPOINT.md).
The r100 production room uses conservative opaque child cells while retaining
source-order alpha batches and every source triangle. R3k introduced the
partition at one metre, a 20.6% matched frame reduction recorded in
[the R3k source-child cell checkpoint](docs/R3K_SOURCE_CHILD_CELL_CHECKPOINT.md);
R3u re-swept it after per-strip culling and moved production to four metres.
The source handgun character assembly now uses the weapon-specific Leon hands,
the source-neutral hidden expression overlay, the right-handed Ganado hand pair,
and source-facing actor culling. The defect evidence and remaining character-system
boundary are recorded in
[the R3l source character-assembly checkpoint](docs/R3L_SOURCE_CHARACTER_ASSEMBLY_CHECKPOINT.md).
The room renderer now maps the source SMX `alpha_omit = 0x80` rule to Dreamcast
punch-through only for a verified binary-alpha material. This preserves all
soft-alpha materials while reducing the matched complete-frame interval by 8.1%
in [the R3m source punch-through checkpoint](docs/R3M_SOURCE_PUNCHTHROUGH_CHECKPOINT.md).
Room visibility, source cull state, and source-selected room lights are now
computed once per render snapshot and reused by all material passes. The matched
4.9% frame reduction and PVR call/byte telemetry are recorded in
[the R3n visibility-reuse checkpoint](docs/R3N_VISIBILITY_REUSE_CHECKPOINT.md).
Polygon headers and their first payload now share one immediate PVR submission;
the repeated small result and unchanged command-byte evidence are recorded in
[the R3o header/payload batching checkpoint](docs/R3O_HEADER_PAYLOAD_BATCHING_CHECKPOINT.md).
The manual controller is now sampled independently of long render frames in
[the R0 input-service checkpoint](docs/R0_INPUT_SERVICE_CHECKPOINT.md).

The source audio targets privately extract `wep02.drs`, `em12.drs`, and
`pl00.drs` from
Disc 1 and decode their GameCube DSP-ADPCM cues. The handgun fire event plays
cues 0 and 2 together exactly as `cObjMauser::moveFire` requests; the starting
reload uses cue `0x16`; the r100 hatchet swing plays cue `0x3d` on source
sequence frame 37; and Leon's normal damage path selects hurt cues 9-11 before
death cue 13. No DRS, encoded sample, or decoded WAV is tracked by Git:

```sh
make -C port/dreamcast -f Makefile.host \
  source-weapon-audio source-enemy-audio source-player-audio
source port/dreamcast/kos-env.sh
make -C port/dreamcast/room \
  FIRE_SOUND_0=../build/private/source-audio/wep02-cue00.wav \
  FIRE_SOUND_2=../build/private/source-audio/wep02-cue02.wav \
  RELOAD_SOUND=../build/private/source-audio/wep02-cue16.wav \
  ENEMY_SWING_SOUND=../build/private/source-enemy-audio/em12-cue3d.wav \
  PLAYER_DAMAGE_VOICE_9=../build/private/source-player-audio/pl00-cue09.wav \
  PLAYER_DAMAGE_VOICE_10=../build/private/source-player-audio/pl00-cue10.wav \
  PLAYER_DAMAGE_VOICE_11=../build/private/source-player-audio/pl00-cue11.wav \
  PLAYER_DEATH_VOICE_13=../build/private/source-player-audio/pl00-cue13.wav
```

## r100 PS2 tree packages

The r100 scenery can draw the PlayStation 2 release's trees in place of the
GameCube trees (COMMON BINs 0-10, about 80% of the resident scenery triangles;
the PS2 models are about seven times lighter). Only the render mesh and the
bark texture change. Placement, collision, events, part identity and the
material stay GameCube. Everything below is private: no PS2 or GameCube file,
OBJ, PNG or package is tracked by Git.

1. From a locally supplied PS2 disc image (*Resident Evil 4 (USA)*), extract
   `r100.dat` from the disc's AFS archive (member 2294, SHA-256
   `75fe9de6fe15af37a454ae6d0a0667aec6a578a898afb5028bf79acf8b4b6441`). Then
   unpack it with JADERLINK's tools:
   - `RE4_DATUDAS_TOOL` 1.0.4, which gives `r100/r100_004.SMD` and `.TPL`;
   - `RE4_PS2_SCENARIO_SMD_TOOL` 1.3.0 on `r100_004.SMD`, which gives
     `r100_004.scenario.obj` and `.idx_ps2_smd`;
   - `RE4_PS2_TPL_EXTRACT` B.1.1.1 on `r100_004.TPL` with the `PNG` format
     argument (its TGA writer crashes). The bark is `r100_004/0023.PNG`.
2. Generate the replacement meshes, the bark and the packages. The GameCube
   inputs default to the checkout's `orig/.../r100_full_export`
   (`RE4DC_R100_EXPORT` overrides it), and `pvrtex` comes from
   `$RE4DC_KOS_BASE`.

   ```sh
   T=port/dreamcast/tools
   python3 $T/ps2_trees.py out/trees --ps2-obj PS2/r100_004.scenario.obj --dc-uv
   python3 $T/ps2_tree_texture.py PS2/r100_004/0023.PNG out/bark
   # Optional Blender static reduction, also used by the chosen r100 set:
   python3 $T/export_room_bins_obj.py out/bins
   blender -b --factory-startup --python $T/blender/bl_decimate.py -- \
     "$PWD/out/bins" "$PWD/out/blender" $T/blender/r100-planar2.json
   # Per owner, with the same LOD arguments as the default r100 packages:
   python3 $T/convert_room_bins.py out/pkg/COMMON.re4mesh --owner 0xfe --common \
     --bins EXPORT/R100.FILE_SHARED --lod --scales scales-r100.json \
     --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 \
     --lod-bias 0xfe:0-10=0.375 \
     --lod-substitute out/trees --lod-substitute out/blender/planar2
   python3 $T/verify_tree_uv.py out/pkg/COMMON.re4mesh out/bark
   ```

   `--lod-substitute DIR` replaces every `<OWNER>_<bin>.obj` in the directory
   as a whole BIN, and levels of detail are generated from the replacement.
   With the D367 arguments, COMMON is expected to hash to
   `cdeade631a35b6e9514c31d4ec0dbd19f07c66c508b5611270257cebed1191b6` and the
   bark to `5b40350924d4164c08608a769acfb165f3c54e571b51d5baa50de4aa305e16d9`.
3. Stage both at once. The bark replaces the GameCube tree texture under that
   texture's own source identity. The PS2 UVs are transposed, so these meshes
   must never ship with the GameCube bark, nor the bark with the GameCube
   meshes:

   ```sh
   TEXDIRS=out/bark/tex MESHDIRS=out/pkg \
     port/dreamcast/tools/mkdisc.sh <elf> <data> <outdir> <fixtures>
   ```

   `blender/bl_render_compare.py` renders the GameCube tree, the PS2 tree and
   the packaged result side by side. `blender/bl_measure.py` and
   `blender/bl_pair_ps2.py` measure the surface error of a replacement and the
   world-space GC/PS2 correspondence.

## Near-term sequence

1. Reuse one conservative visibility/draw-state list across all room passes and
   add separate visibility, packet, byte, TA-registration, render, and present
   measurements.
2. Attack the next largest measured room/actor cost with an explicit cache or
   SH-4 kernel dependency contract; retain and compare the reference path.
3. Benchmark packet aggregation and KOS DMA only after exact list byte/call
   counts exist. Immediate submission already uses store queues.
4. Continue the R4 asset residency and streaming workstream. Its inventory
   tool is in place and has measured the r100 textures: six of them were
   reduced by a 256-pixel build limit and can be restored to their authored
   resolution under vector quantisation for 46% less VRAM and 5.7 to 7.3 dB
   more PSNR, while quantising the textures that were not reduced would cost
   3 to 13 dB and is therefore not a default. Next is the native texture
   layout that can express those payloads, which the current `re4tex` header
   cannot. See [the R4 plan](docs/R4_ASSET_RESIDENCY_PLAN.md) and
   [the R4a inventory checkpoint](docs/R4A_TEXTURE_INVENTORY_CHECKPOINT.md).
5. Derive the residency model from the authored GameCube block sets, replace
   the embedded ROM disk with asynchronous reads into a staging arena, and
   prove one room transition with the previous room evicted.
6. Expand the repeatable route to movement, aim extremes, enemy contact, death,
   and retry; complete human-controller and physical Dreamcast acceptance.

Source collision, camera, state/event, expression, and cloth parity continue as
bounded encounter fixes, but they do not block independently verifiable target
optimizations.
The authoritative real-time task order and acceptance criteria are in
[the real-time path](docs/REALTIME_PATH.md). The presentation history and
ownership ledger remain in [the playable backlog](docs/PLAYABLE_PATH.md). The
[hardware/source assessment](docs/HARDWARE_TRANSLATION.md) documents the
GameCube differences, real-time scenes, SFD movies, and render-to-texture work.
See also [the r10d asset boundary](docs/R10D_VERTICAL_SLICE.md).

Full menu systems, complete audio coverage, story events, and campaign
progression stay behind that demo gate. Room streaming is no longer behind
it: it is the R4 workstream, planned in
[the R4 plan](docs/R4_ASSET_RESIDENCY_PLAN.md). Minimal start,
completion/retry presentation and core gameplay sound are required today.

See [Soulcalibur reuse](docs/SOULCALIBUR_REUSE.md) for the local Flycast lessons
that govern evidence, resource identity, and visual validation.

The first native artifact is `kos/re4dc-smoke.elf`: a 320×240 RGB565 PVR
triangle with Maple START handling. It deliberately proves only toolchain,
video, primitive submission, and input. The current ELF is a statically linked,
little-endian SH-4 executable with a 224,636-byte linked footprint and SHA-256
`8a1db88ed9d784e0f45a093e742b918e5cfbeb9f69cba404b38ce21eef2160fa`.
Build it after sourcing KOS with `make -C port/dreamcast/kos`.

The first Flycast candidate run is retained under
`C:\Flycast-Evidence\re4-dreamcast\smoke-20260919-141209`. Its console capture
shows KOS startup, the 320×240 RGB565 mode, controller discovery, and frame 300;
its render capture shows the expected moving gradient triangle. This is emulator
evidence. It is not a physical Dreamcast, timing, or input acceptance result.

The reproducible bootstrap is:

```sh
port/dreamcast/tools/bootstrap_kos.sh --build
```

It verifies the three revisions in `toolchain.lock`, builds only the required
SH-4 toolchain, builds KOS, and then builds the platform and motion smoke
executables. The optional ARM toolchain is intentionally excluded until custom
AICA firmware is needed.

</details>

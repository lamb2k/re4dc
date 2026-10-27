# House arena27 benchmark v1

This is a private experiment on the existing BENCHMARK=1 path. It draws Leon and
one complete house. A/B/C are the original house, simplified R4 house and baked
house, each in its own asset package. It does not qualify the full r101 world or
change a production recipe. Asset selection and render filtering are owned by
the arena renderer extension; this note describes the benchmark contract.

## Build and fixtures

Include game/house_arena27.mk after bench.mk. Add HOUSE_ARENA27=1,
BENCH_SCENES=3, BENCHMARK=1, TAIL_METER=1, PACE_VMU_GPU=1 and
GAME_TICK_LOG=60 to the isolated candidate recipe. SCENERY_STREAM=1 requires
TA_HASH=0, retaining its existing guard and renderer path. A non-streamed
control requires TA_HASH=4 for existing TA list-byte counts. All normal BENCHMARK
prerequisites still apply. No flags or objects are added when HOUSE_ARENA27=0.
The recipe must pin its actual source SHA, resolved knobs and staged asset hashes.
Do not infer the current production recipe from the older floor worktree.

The existing warp.txt, bench2.txt and bench3.txt fixtures run three scenes with
soft resets. Every command except the bench row's number and name must match:

    bench 1 120 300 original
    bench 2 120 300 simplifiedR4
    bench 3 120 300 baked

Put each row in its corresponding fixture. Reuse the same existing camera,
position, pose and render-filter commands in all three files. Room frames
[0,120) are warmup; [120,300) are measured. These are logic ticks, not drawn
pictures. No actor, effect, camera or pose command may vary between arms.
The report compares normalized fixtures and records SHA256 for each input.
These checks establish matched commands; runtime captures still establish what
was actually drawn and that the complete house is visible.

HOUSE_ARENA27_BEGIN/END may override the measured range. END must exceed
BEGIN+120 so the existing CPU snapshot can produce a wholly measured window.
Use the same bounds in all three fixtures. At default bounds, the range spans
six seconds at 30 game ticks/s, but loading and slow execution can increase wall
time. Keep each emulator process under 60 seconds. HOUSE_ARENA27_AUTO=1, 2 or 3
bypasses the 20-second start screen and runs just that selected arm. Zero keeps
the normal menu: START cycles all three; X/Y/B selects one; A at results repeats.
The benchmark banner stays identical across all arms; logs and results identify
the active variant.

## Renderer hook

    extern "C" int re4dc_house_arena27_variant(void);

Compiled only with RE4DC_HOUSE_ARENA27=1, returns 0 original, 1 simplifiedR4 or
2 baked. It is selected when the first/next fixture is requested, before room
loading, and reset correctly for A-at-results repeat runs. Render-side callers
must also be guarded by this knob; ordinary play images do not link bench.cpp.
All three arms retain the same runtime implementation, actor assets and settings.
Only their house data paths change. The selector does not alter simulation.

## Logs and reporting

Use the existing re4dc_log output. arena27 metadata identifies build, variant,
run and exact frame bounds. An arena27 window marker means that the immediately
following existing PACE vmu row is a whole accepted one-second window. The first
partial pace window and loading are excluded by the existing benchmark logic.
The first frame-tail picture at the warmup boundary is also excluded. The CPU
snapshot uses the existing 60-tick meter with its existing 120-tick safety delay.

    python3 port/dreamcast/tools/d367/world_rebuild27/arena_report.py \
      original.log simplified.log baked.log \
      --environment cache-model-flycast \
      --fixtures warp.txt bench2.txt bench3.txt \
      --json arena-results.json --markdown arena-results.md

Use --environment console only for log files captured on a physical Dreamcast.
--single-arm 1/2/3 validates an individual run while collecting the other arms.
The report exits 2 for incomplete/invalid data, including absent GPU stamps,
fewer than two complete pace windows, no CPU snapshots, missing TA counts,
missing frame-tail samples, mismatched bounds/builds or missing fixture proof.
When TA_HASH is unavailable on the streamed path, require existing native stream
rows both in warmup and after the benchmark begin marker, up to scene end. The
latest warmup row supplies cumulative discarded/black_frames/missing baselines;
any measured change is rejected. Each measured sample must have positive
model_bytes and contain ta_used/ta_peak. ta_used can be zero in emulation.
These periodic rows establish sampled-frame observations, not a full-frame
fault census; no result is fabricated for the gaps between diagnostic rows.
Duplicate captures of the same arm/run are rejected instead of averaged silently.

Reported values:

- GPU render is exact accumulated existing render-done stamps divided by their
  sample count. Registration is the sample-weighted existing PACE reg_avg_us
  value (microsecond precision). Present cadence uses counted vblanks/drawn frames.
- CPU is the existing tick-log CPU mark per logic tick. Frame-tail work, blocked
  time, TA-done latency, render and queue carry sample counts, mean, p95 and max.
- TA input retains OP, OP modifier, TR, TR modifier and PT bytes per presented
  frame from TA_HASH=4 when available. Otherwise list-byte counts are null and
  explicitly unavailable; the report retains sampled native model_bytes,
  ta_used and ta_peak instead. These are existing submitted-byte/buffer counters,
  not inferred triangles or per-house GPU cycles. No buffer size is invented.

Registration, TA-done latency, GPU rendering and CPU work overlap. Never add
these columns as independent costs. The frame range is exact, while timing
means use only their documented whole windows/samples. No new timer or timing
model is introduced.

Cache-model Flycast establishes execution, asset loading, visibility and proxy
direction only. Its GPU timings are not hardware accurate and cannot establish
PowerVR hardware impact. Keep hwmodel MODELLED CPU evidence separate. Physical
console A/B/C readings remain required before claiming a GPU improvement.

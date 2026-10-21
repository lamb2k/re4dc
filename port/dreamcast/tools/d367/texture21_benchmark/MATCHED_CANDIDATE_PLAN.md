# Frozen 948 + scoped 17: target comparison plan

Status: plan only. This document allocates no image, stage, build or guest. Root
reviews the exact metadata and assigns the next target allocation. Tools and new
metadata stay within 20 MiB; original ac52 baseline evidence remains sealed.

## Arms and attribution

Use frozen source 004cf224674fa60cf08dc10e641c723de238a0fd and the exact ON program
for both B and C: raw a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71,
ELF e08c9abc8f6bb44bb2a94642fc9a2e664d22039659cea7fcce311cb9989d7433, all 14 ON overlays.
All ten required format/consumer knobs remain resolved 1 in both; animals-off,
cap 4, GAME_SH4ZAM 1 and SKIN_SH4ZAM 0 are identical. The rejected window-restoration
candidate stays absent/disabled. Atlas 2 and held r101 nine are excluded.

B is the current 948 pipeline control: pack e19cfc464e789e97ca96864adfc2a4cd44443a9f4775bebd842c3e184a65559b
and the original r100/r103 R4PW files. C uses actual 948 + 17 pack bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026
and the two frozen scoped-key R4PW copies. B/C differ in exactly three staged
files: dc/tex.pak and dc/native/r100, r103/ps2-world.r4pw. All 6501 B members stay
exact in C; only 17 members append. The independent sidecar byte proof allows
only selected key words and body CRC; logical/material/placement bytes stay exact.

A is the historical original QA 8942/ac52 baseline. A/C would measure the complete
program+948-pipeline+17 package change and cannot attribute a total delta to 17
rectangles. Even B/C changes filtered base detail, so it requires a look review.
Do not treat the 17 as accepted solely because descriptor requests shrink.

## Stage and cold lineage, after root allocation

The metadata generator emits complete expected file manifests B/C from the
sealed 1743-file original QA manifest plus the exact frozen program/data inputs.
A later stage must independently enumerate/hash every resulting file and match
its arm manifest before boot. New whole-image hashes do not exist yet. The
rectangle owner separately prepares the physical single-pass image contract;
this plan does not allocate or duplicate it. No Joliet tree exists in the actual
baseline. The rectangle image-plan-04 preserves all 1743 file LBAs and the
150-sector raw tail. Final program LBA 547365 expands into two verified zero
tail sectors (PVD 504000 to 504002); no append. Treat RAM-only predicted image
hashes as predictions until the allocated writer and independent readback agree.

Each arm cold-boots independently with the same original VMU template, emulator,
configuration and original QA Start normally/New Game/source-defined movie skip
inputs. Bind unchanged menu/preset bytes. The existing original woods key script
and normal input history are lineage references; never copy their state into B
or C. Save each arm's own native checkpoint on graceful owned-window close and
require fresh FLYSAVE1 bytes, exact save/load log paths, image/program/emulator
hashes, source tick, room, camera, health and checkpoint-parent chain. Never
transfer a checkpoint across B/C, even though their program is the same.

Use 43-second requested segments, independent 49-second pinned-process watchdog,
C >= 18 GiB + 128 MiB before and during each run, 100,000,000-byte capture growth cap,
existing trace_lock/global 16 ceiling, PID-only input and one owned guest here.
If entry/load does not finish, continue only that arm's authenticated checkpoint.
Preserve failures; no health/progress/region/position pokes or foreign snapshots.
The first cold A attempt and all baseline snapshots remain untouched.

## Scene, clock and rejection rules

Primary scene is the observed r100 woods view reached by this QA normal-start
lineage, not the historical custom bridge warp. Original A endpoint tick 1980
had Leon (-99692.265625,-454.2052307,-1343.7418213) and camera
(-100308.09375,1310.7694092,-209.5909729); full target/view/projection matrices
are in woods-checkpoint-pose03.json. These describe A, not automatic B/C approval.

B and C must establish identical source scene/story input, room 0x100, player
position/angles, camera position/target/view/projection, source decisions and
health/kill history. No input follows own-image restore into the idle view.
Require finite typed fields and strict source-bit equality for player/camera
at the selected boundaries. If source camera jitter prevents equality, reject
the timing pair and record the actual mismatch; a separately reviewed camera
matching contract may be chosen before another pair. Do not silently widen tolerances.

Requested source clock is GlobalWork.Frame_cnt 1801..1920 inclusive,120 ticks,
matching actual PT f blocks 1801..1860 and 1861..1920. Record actual ticks and
pictures; no host-time substitution or post-hoc sliding. Own parent checkpoints
must precede this window. The observer must start before it and distinguish the
restored log-ring history from newly written records using the initial log head.
If a prior segment already passed the window, qualify the actual bounded capture
that observed it or agree a new common future window before either arm runs.
Reject incomplete windows, held/movie/death/menu phases, nonneutral input, torn
samples, log overruns, source mismatch, different settings or changed noncohort work.

## Existing-program observation, without runtime edits

Use exact ON ELF/DWARF; do not reuse A addresses. Actual native_ui Entry is 224
bytes, 448 entries. Two local symbols share the mangled entries name: select
native_ui's 100352-byte array at 0x8c2b0140 by type size/source provenance; the
4-byte unrelated symbol at 0x8c3f0148 is not the cache table. Metadata includes
existing-object DWARF for Entry/Key/Package/Header/Texture, GlobalWork,
CameraControl/Camera/cCoord and exact ON symbol sizes/addresses. No new compile
or source hook is needed to prepare these identities.

Sample only through VM_READ/query rights on the owned process, with pinned
image/creation-time and exact program anchors. Scalar frame/camera/drive samples
may run 100 Hz; bound metadata by retaining window rows and summaries. Capture
stable Frame_cnt before/after, reject torn pointers, validate every main-RAM/VRAM
range and read 64-bit counters with a stable high-low-high sequence. At the same
source boundaries record cumulative low-level nonmusic reads/bytes/block_us;
report deltas separately from music, aligned reads, page-cache or texture loads.
These counters do not identify which texture caused a drive operation.

Sample the finite resident table 5 Hz and at window edges. Record valid selected
original/scoped keys separately, Package upload_complete, descriptor dimensions,
format/flags/payload/header CRC, allocated PVR pointers, ownership/shared flags,
metadata/released bytes and vram_bytes. Count original-only/candidate-only/both
residency, observed peak bytes and slot pressure. Deduplicate physical addresses;
never sum shared owners twice. The source bound 69632 original + 58208 candidate
requests = 127840 potential co-residency is not an actual allocation or saving.

Resident/cached headers prove admission and physical shape, not final draw use.
A stronger minimum witness is possible: frozen direct_begin copies the current
model_packets header to SQ, flushes it, then sets direct_open=true and stamps
model_handle->frame. A repeated stable frame/direct_open/model_handle/current
packet/header read can witness a submitted header for a selected key with 64x64
physical TSP extent and the expected VQ/mip TCW. Validate pointers and reread the
entire tuple; reject changes. This is a sampled minimum, not all per-key counts,
complete vertex emission, rasterized pixels or a proof that an unobserved key
was unused. Direct vertices go through SQ, so model_packets is not a full final
TA stream. Full PVR/vertex proof is still open if these read-only witnesses miss
it; do not add silent runtime diagnostics or claim their absence is success.

## RAM, all 8 MiB VRAM, look and comparison output

Produce one interval-aware memory manifest for each arm. Record linked PT_LOAD
and text/rodata/data/BSS/char-data extents, heap 4 and owner pools, KOS/kernel/thread
stacks, TA command/preparation/light/spill slabs, native package metadata and
texture residency, main-RAM sound staging and overlapping movie/menu reserves.
Report the separate AICA 2 MiB device memory independently; never add it to 16 MiB main RAM. Separate
static reservation, current usage, source cumulative peak, observed sampled peak
and unavailable high-water. Include every main-RAM arena/category and account
for the 16 MiB total with explicit unknown/residual ranges. Static _end or per-function
stack frames are not runtime high-water; B/C code reservations are identical.

Account for all 8 MiB VRAM: active framebuffers/stride/depth and display registers,
TA vertex/OPB and double banks, texture pool, slabs, claims/reserves, pinned/dynamic/
other/free/largest and any original/scoped overlap. Preserve source readback
failures, refuse/no-contiguous/retry/eviction counters and dynamic palette pressure.
Use source allocator census and read-only PVR/page state. A known gc_fx row or
unavailable full peak stays explicit; no complete-room/native acceptance is inferred.

Take source-tagged active-view framebuffer pairs at the same scene/clock and
retain framebuffer/front-back identity, pose/matrices, source tick before/after
and image/program/assets. A CPU tick tag does not prove which queued picture is
on screen. Treat stills as look evidence unless actual presentation identity is
bound. Inspect geometry/material seams, near/far filtering, tree/ground detail,
clipping/UV wrap and unrelated FX/UI/actors. Scoped 17 is an approximation: human
look review remains required; do not demand pixel identity as its acceptance rule.

Final B/C report names exact program/data/image, source window, camera, logic
ticks/picture, CPU/PVR evidence type, drive deltas, RAM/VRAM and look/rejection
results. Preserve the historical A numbers separately. With no target allocation
or observations yet, every performance/admission/peak result remains pending.
Release checks and physical Dreamcast acceptance stay Claude/user owned.

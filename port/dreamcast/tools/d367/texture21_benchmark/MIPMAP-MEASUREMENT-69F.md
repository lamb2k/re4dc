# Source-only successor and measurement contract

Frozen inputs: runtime0425534d848973c1dae3ab960d0006ac9afcf363,
programme733afabf6567a9f086eacb48b70559aef764cf52a5b534f44602da3a8bc68a9e,
ELF69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae.
The original observer8720989d, binding8081fd7f, images, captures and strict pair
results remain unchanged. No successor guest, programme, image or asset write is
authorized by this document. Main reviews and allocates execution separately.

## Why the first cold pair missed frames

The frozen observer polls on a10ms schedule. Its hot loop additionally attempts
the texture table, CPU packet witness, JSON encoding and synchronous output.
The actual pair retained81/82 completed source states, only26 in common and14
in the240..360 comparison window. There were no differing accepted variants.
The retained logs do not timestamp every publication edge, so the exact live
window width and the fraction of misses due to scheduling versus read cost
cannot be recovered. Do not relabel missing states as mismatches or infer that
the hypothetical2ms model window is a measured game value.

Source042 main.cpp270 resets ProcessTickInit before Render_before/PadRead/Render.
Frame_cnt advances before TaskScheduler/Player/CameraMove. SndWatcher is stamped
at320, PROCESS CPU before Render_done, then Render_swap invokes native_ui end.
native_ui.cpp6001..6032 publishes completed_frame using odd/even sequence after
render/present work. Main then performs the pace/vsync tail, TOTAL/tick log and
the next reset. Only the narrow interval satisfying ALL existing phase tests
is acceptable. source_draws_finished alone is earlier than Player/CameraMove;
g_snapSeq is a60tick aggregate, not a per-frame pose latch. Neither replaces
the completed-state gate.

The successor polls a three-read sequence/UI/cursor hint every500us and always
runs the unchanged full pre/post phase, epoch, source-pointer and body rereads
before accepting. It does not select the first matching variant. All observed
variants still enter Coverage; any conflict or missing state fails the complete
window. It removes table/direct work and filesystem writes from the sampling
loop, buffering at most3.5MB of whole JSON rows. It retains the actual192-byte
completed native snapshot and128-byte tick/name arrays. Work120B and heap-free
word remain raw; TOTAL slot0 is not certified current because it is written
after Render_swap. Current CPU/indexed marker semantics remain separate from
overlapping nested profiling rows.

On this Windows Python3.12 host, monotonic uses GetTickCount64 with15.625ms
resolution; perf_counter uses QueryPerformanceCounter with100ns resolution.
The successor uses QPC for cadence, gap telemetry and an additional4ms total
read window, retaining the frozen base80ms coarse ceiling and verified-owned
process lifecycle. No global timer-resolution, priority, affinity, suspend,
register, replay, state or gameplay change is made. A host scheduler stall can
still miss a frame: actual max gaps, read duration, all rejection counts and
coverage are mandatory outputs. Synthetic model and own-Python RAM results
are source/host tests only. They establish no Flycast or console coverage.

## What a useful performance result must measure

The primary pair remains original18f M0 versus canonical1004/89ef M1 with the
same733a programme and exact15 programme files. This measures the FULL compact/
VQ/mipmap/world-representation/actor pipeline. M0 retains protected Ganado mip
chains. It is not globally mip-off, and a delta cannot be attributed solely to
mipmap sampling. Do not stall primary pipeline delivery for a new isolated arm.

Use fresh independent cold states, the exact QA5 farm controls/neutral remainder,
same geometry/gameplay/caps/animals flags, and source240..360 inclusive (121
completed states; no sliding or cherry picking). Require each state in both
arms, zero variants, exact player/active camera/room/health/ordinary flags and
phase clocks. Preserve missing Pad/RNG/presentation proof explicitly; same menu
schedule is not a live Pad/RNG sample. Source frames are not host screenshot
timestamps. The house/woods preset0 requires its own complete matched pair and
r100 metadata gate, including positive PCL170cells/1186portals adoption; r103
has no applicable PCL package. r101 approximation/look remains a separate gate.

The captured pose is the post-update source state. Render occurred before that
update; completed_native.frame is the UI render clock, not that pose's source
clock. In the actual cold pair source=UI+1 and skipped_frames=1. Keep the source,
UI and skip fields explicit. The240 predecessor state and241..360 updates must
all be retained before associating successive pose/render work intervals. Do
not attach a current post-update camera to the earlier completed image or infer
displayed-pixel correspondence from equal integer counters.

Join exercised keys to each arm's actual pack descriptor, PVR allocation,
ownership and physical format. PAL reserved_0 is a runtime bank assignment:
retain raw descriptors, stored canonical header CRC and narrowly normalize only
that field after type/range/alignment/lifetime checks. Preload/residency, cached
headers and CPU staging are not actual TA acceptance or hardware-selected LOD.
The current69f programme does not publish a per-key immutable post-submit event
or hardware chosenLOD. A chosenLOD claim therefore remains unavailable. A future
instrumented submission/PVR trace needs separate source review and allocation;
do not invent it from TCW31, view distance or file bytes.

For Flycast, report exact-window CPU/profile/native render_wall/present_wait and
emitted-interface counts as emulator observations only, with host settings,
renderer/vsync/throttle, observer overhead and screenshot cadence pinned. The
native timer fields include host/emulator pacing and present path work; neither
their inverse nor cold process FPS is Dreamcast FPS or pure texture/GPU cost.
frame_pvr_calls/bytes count CPU interface emission; they are not actual memory
fetch traffic, selected mip levels or completed rasterized primitives. Count
actual geometry/header/queue differences so a lower workload cannot masquerade
as a texture benefit. Never sum overlapping Player/render/collision rows.

Real mip bandwidth/fill benefit requires physical Dreamcast timing on these
exact programme/assets/scenes, with accepted PVR format/LOD evidence where
available, identical submitted geometry, fixed camera/output and repeated
unmodified runs. Record hardware frame completion/presentation separately from
CPU time, render/present wait and capped frame cadence. A30fps cap can hide an
improvement; use render/completion headroom and missed deadlines rather than
claiming higher FPS from an unchanged cap. No physical run is authorized here.

If mip-only causality is later needed, prepare a separate reviewed control with
the same base pixels, physical dimensions, VQ/PAL format, UVs, geometry and
programme, varying only mip chain/descriptor/TCW mip enablement. Prove base-level
equality and actual emitted bit31; retain filtered look and hardware chosenLOD
limits. No such new pack/programme/image is created by this unit.

Report memory honestly: the actual cold pair M1 added136,992 texture-payload
bytes and reduced free VRAM137,792B. Selected ownedVQ lower bounds604,162 to
621,938B differ from complete allocation/high-water accounting. M1 added12
nonmusic reads/135,040B at cold load; settled counters were flat in both arms.
These are costs and controls, not a performance improvement. Additional original
preloads must be counted wherever they occur; the retained farm tables had none
of the19 scoped keys' originals co-resident, not a global proof for woods.

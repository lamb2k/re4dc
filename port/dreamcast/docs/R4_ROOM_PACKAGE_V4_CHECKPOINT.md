# D364: versioned prelit room storage and SH-4 layout qualification

2026-09-23. Status: four-owner format/CPU fixture qualified; **not recovered-game
static cutover, source-heap recovery, visual acceptance, or physical hardware acceptance**.
The persistent goal remains active. Continue the existing source owner/renderer
integration; generic GX content remains fallback until actually replaced.

## Decision

Retain v4 AoS20 as the leading storage candidate. It uses fewer bytes and has
lower measured preparation/packet cost than Split24. Keep the D349/KOS math
backend as default: SH4ZAM transform/reciprocal did not improve this fixture.
Neither layout is promoted into the recovered game by this checkpoint. The v4
path is slower than the prelit v3 kernel control; do not call the byte saving
a whole-frame speedup. No new renderer/cache/streamer or toolchain upgrade.

## Exact storage: same four packages

| Owner | v3 bytes | v4 AoS20 bytes | v4 Split24 bytes |
|---|---:|---:|---:|
| MAINSCENARIO | 162,848 | 106,724 | 118,436 |
| FILE_00 | 64,156 | 46,980 | 51,684 |
| FILE_01 | 1,541,332 | 1,000,874 | 1,144,202 |
| FILE_02 | 224,488 | 144,720 | 164,368 |
| **Total** | **1,992,824** | **1,299,298** | **1,478,690** |

AoS saves 693,526 bytes (34.80%). Split saves 514,134 bytes (25.80%). Every
byte below is in the package, including padding. Textures are unchanged.

| Section | v3 | AoS20 | Split24 |
|---|---:|---:|---:|
| header | 512 | 640 | 640 |
| materials | 3,328 | 3,328 | 3,328 |
| groups | 104,928 | 34,976 | 34,976 |
| source_groups | 83,068 | 4,872 | 4,872 |
| batches | 39,788 | 73,892 | 73,892 |
| vertices | 1,293,408 | 896,880 | 717,504 |
| attributes | 0 | 0 | 358,752 |
| triangle_indices | 142,212 | 71,106 | 71,106 |
| primitives | 101,000 | 101,000 | 101,000 |
| strip_indices | 224,580 | 112,290 | 112,290 |
| padding | 0 | 314 | 330 |

Local batch vertices increase from 40,419 to 44,844 (4,425 duplicates); that
cost is included. Maximum batch size is 2,760, so uint16 indices are sufficient.
Oversized batches reject conversion until split at a proven legal boundary.
The 1,093 groups become 32-byte bounds/range/source-ID records; 58 shared
84-byte source records retain masks/cull/light metadata plus explicit
owner/work/BIN/common identity. Material names remain because they are bindings,
not debugging names. Batch records grow 28 -> 52 bytes to encode local vertex
ranges and UV bias/scale. Non-order-certified batches retain triangle backing.

AoS vertices are float XYZ + uint16 UV + ARGB8888 (20 bytes). Split positions
are float XYZW (16 bytes, W=1) plus an 8-byte UV/color stream. Sections align to
32 bytes; package backing must be at least 16-byte aligned for direct vector
reads. XYZ remains bit-identical float32; no position quantization. UV uses
per-batch affine unorm16, preserving negative/repeated coordinates. The largest
measured UV error is 0.000305176 normalized UV
(less than 0.5 texel even at 1024). Packed RGB matches D349 float32 multiply
and truncation. These numerical bounds do not replace a moving visual review.

The existing D353 baker was used with its D349 source-worktree input. Pointing
its extraction script at the modified D353 renderer exposes an unterminated
conditional; that failed private attempt is retained. No second baker was made.
CLI checks baked/reference/OBJ hashes, view-light exclusion and shared-color
qualification. Live source lighting/material changes still need binding guards.

## Target CPU results

Pinned GCC 15.2.0; KOS 804b3195ebd1a06a27cc2b3a5eacf7a2429040a3.
Existing D349 -O3/-fno-predictive-commoning/LTO policy, no global fast-math.
Flycast only. Existing TMU2 wall clock, no counter/timer reconfiguration.
Four warm-up iterations, 32 measured iterations per math backend. Each ELF
contains only one layout. Same source XYZ/topology/state; all batches are in
front of a fixed diagnostic projection. This is deliberately a CPU workload,
not an authored gameplay-camera/render/presentation run. No GPU submission,
textures, VRAM allocation or source gameplay occur in this fixture.

| Layout / math | Prepare p50 ms | Packet p50 ms | Total p50 ms | Total p95 ms |
|---|---:|---:|---:|---:|
| v3-d349 | 16.070 | 18.189 | 35.293 | 37.796 |
| aos20-d349 | 27.236 | 19.201 | 47.486 | 47.493 |
| aos20-sh4zam | 27.660 | 19.197 | 47.895 | 50.399 |
| split24-d349 | 27.702 | 19.199 | 47.935 | 47.942 |
| split24-sh4zam | 27.671 | 19.200 | 47.909 | 50.413 |

All arms process 44,844 unique batch vertices and construct 71,829 PVR vertex
records (2,298,528 bytes): 8,616 intact strips and 11,851 source-order fallback
triangles, covering 30,895 triangles. No GX command decode, static normal
transforms, room-light evaluation or source-corner remapping occurs in v4.
Those zeroes describe this qualified static representation/fixture, not the
current recovered-game fallback. Material headers and PVR transfer are outside
this timing. Packet construction uses the existing `prepare_direct_strip`.
Total timings include loop/timer overhead and must not be added to GPU times.

The fixture uses 128 KiB slots and 128 KiB packet scratch, plus private logging
and auxiliary-copy buffers; those are fixture costs, not new game reservations.
The game adapter must reuse its bounded scratch and price its real loading peak.
No source heap or complete reference+candidate representation is present here.

## SH4ZAM pin and decision

Pinned [SH4ZAM 0fd3a1e1fa0809d33198c062632b1494ec2f57df](https://github.com/gyrovorbis/sh4zam/tree/0fd3a1e1fa0809d33198c062632b1494ec2f57df),
MIT; `room/sh4zam.lock.json` recorded its file hashes (removed 2026-10-16: SH4ZAM is now the submodule
`game/third_party/sh4zam`, pinned by its commit, and `tests/build_room_layout_probe.sh` checks against that). GCC15.2 builds its selected
headers/assembly without SDK changes. The pinned PVR DMA example uses XMTRX,
positive reciprocal, near interpolation, aligned copies and KOS vertex buffers.
Its loader/frame owner/large buffers/compiler flags were not imported.

The candidate uses actual XMTRX transforms and `shz_invf_fsrra` only for finite
positive W within a safe squaring range; ordinary division covers other positive
magnitudes. Nonpositive W stays rejected by the caller/clip fallback. Split24
also tests a direct vec4 load. Numerical comparison covers every compact vertex;
maximum projected difference is 0.000015257 pixel in this fixture. Behind/near
plane live integration remains a separate clipper qualification.

SH4ZAM linear interpolation produced zero sampled difference and no speed win.
The auxiliary 32,768,000-byte aligned RAM copy was ~61.878 ms versus ~205.342 ms
for libc in Flycast. This is a bulk-copy lead only: it does not measure remaining
32-byte header copies, store queues, DMA, GPU cost or real hardware cache effects.
No copy/clip/math candidate was silently promoted. Dynamic lighting vector/dot
and actor `shz_xmtrx_blend` remain after static cutover.

## Reuse, checks, next boundary

`convert_room_obj.py --compact-prelit` extends the established converter and
bake pipeline. `room_package.*` is the same caller-owned zero-copy view; no
expanded v3 buffer is allocated. New `static_room_prepare.*` adapts those records
to D349 prepared slots and the existing strip/clip contract; it owns no renderer
or frame. Source state/lifetime/material binding is still required before use
inside `re4dc-game.elf`. The historical room target explicitly rejects v4 rather
than misreading it; historical v3 conversion and evidence builds remain intact.

Ten existing converter tests and seven new native-reader/format tests pass.
The old converter test expected retained indices that v3 has already removed;
the unchanged HEAD implementation reproduced that failure byte-for-byte before
the assertion was corrected. Native checks reject CRC/range/identity/stride/
nonfinite/unsupported-bake faults and preserve UV seams/XYZ/strip ordering.
All three SH4 fixture arms terminate internally with PASS before harness end.

Use [the four-owner budget](R4_R100_SOURCE_BLOCK_BUDGET.md) for the next source
backing replacement. The known-span model still needs 863,520 additional bytes
(746,816 beyond D362 free/largest), before adapters/staging. It is not an actual
allocation failure or a reason to return to monolithic conversion. Actual
source-heap recovery from this checkpoint is zero. Keep expensive FILE_01 as
the specific authorized GC/PS2 visual-input reduction target if required; do
not widen into another inventory or change source block lifetime.

Rebuild the measured CPU fixture with `tests/build_room_layout_probe.sh` and
the private package root, pinned SH4ZAM checkout and a new output directory.
Use RE4DC_KOS_BASE=/root/work/kos-re4dc-d336. The script refuses output overwrite
and incompatible SH4ZAM/GCC/KOS identities; it does not install dependencies.
The existing capture boot2.ps1/read_log.py recipe is preserved in evidence.

Private packages: `/root/probe/d364-native-r100/four-owner-v4-v2`.
Builds: `/root/probe/d364-native-r100/target-layout-v2`.
Evidence: `C:/Flycast-Evidence/re4-dreamcast/d364-package-layout-v2` contains
exact ELF/assets/config/tool identities, measured source snapshots, logs and
section/timing JSON. v1 preserves the initial result. No proprietary files enter
Git. Physical hardware, whole-frame A/B, visual review, source replacement and
transition peak remain open.

The native reader additionally rejects misaligned v4 backing (v3 retains its
4-byte contract); that guard was host-tested after the timed snapshots. It adds
no per-frame work. Measured kernel/fixture sources are pinned in evidence.

## Source-range qualification after the layout decision

AoS20 is frozen as the leading layout by the current user roadmap. Subsequent
work extended this same reader with cold-path `resolve_source(owner, work, bin,
common)` rather than another registry/cache. The existing four files remain
byte-identical and pass lookup/close/re-adopt checks. Duplicate owner/work,
conflicting BIN/common and noncontiguous child groups reject qualification.
This prevents a repeated SMX ID from selecting the wrong native source object.

The caller must re-resolve under its existing owner generation after load/move/
retire; the reader owns no game lifetime. No recovered source hook is activated
yet, and no actual source allocation has been reduced. See the four-owner budget
for the FILE_01 decomposition and remaining source/texture connection costs.
This work adds no layout or SH4ZAM timing arm and leaves the D364 results intact.

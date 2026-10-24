# Build 9: UI draw setup

Base: `d5c1ceab9e06461462669b3ce1d28a379747a74a` (`origin/t15/int`, fetched at
this build's start). Branch: `codex/ui-draw-lean-20261024`.
Knob: `UI_DRAW_LEAN=1`, default **0**. The release recipe and audit fixes are
unchanged. No game assets, format, runtime assembly or game-linker change.

## Decision and existing work

The HUD already caches much of the work proposed in the queue. This candidate
removes redundant construction and retains the one fixed projection still
rebuilt per message glyph. It does not retain mutable HUD geometry across frames.

The ordinary HUD, including **ammo digits**, uses the ID sprite system:
`Cockpit` / `LifeMeter` / `BulletInfo` update -> `IDSystem::move/trans` ->
`IdGeneralTrans` / `IdCommonTrans` -> `re4dc_draw_id_quad` ->
`re4dc_ui_submit` -> `ui_draw_quad` or the non-ordered present loop.
Message text uses `Message::trans` -> `messageTrans` -> `messageCamera` /
`draw(MesQue*)` -> `re4dc_ui_glyph` -> `glyph_draw_run`.

| Existing public optimization | Work already avoided |
|---|---|
| `GAME_OB_MAT`, `GAME_OB_SCAN`, `GAME_OB_PATH` | Rebuilding unchanged ID local/world matrices, repeated level scans and path scratch allocations |
| `GAME_ID_LISTS` | Repeated scans through 312-byte ID pool entries |
| `UI_QUAD_LEAN` | Out-of-line corner projection/unused depth, libcall finite checks and some texture-handle conflicts |
| `UI_HANDLES`, `UI_PALETTE_SLOTS=32` | Repeated texture-source resolution; retains source/entry epochs and live palette checks |
| `UI_HEADERS` | Recompiling a native texture entry's polygon header when blend is unchanged |
| Native glyph atlas, hints, headers and runs | Repeated glyph texel conversion, palette header compilation and one header per glyph |
| `mes.cpp` viewport memo | Recomputing viewport offsets when the four relevant viewport components are unchanged |

These are in the base and receive no credit as new savings.

### Changes

1. `ui_bridge.cpp` initializes only the two absent-palette fields that need
   defaults. Every other field of its 104-byte `Re4dcUiQuad` is assigned by the
   existing live descriptor, projection, UV and material path. The compiled
   baseline retained all 26 zeroing stores before those assignments.
2. Both native ordinary-quad drain paths write the 160-byte command packet
   once. The existing header copy writes the first 32 bytes, and the four
   explicit `oargb=0` stores complete the vertex fields. The baseline cleared
   all 160 bytes and then overwrote 144 of them. The four cover/texture dimensions
   are converted to floats once per quad instead of once per vertex: four
   conversions instead of 16. Every UV still uses `(uv * cover) / texture_size`,
   preserving the multiplication/division order.
3. `glyph_draw_run` is kept out of the ordinary-quad function's inline body.
   Its 2080-byte glyph packet buffer belongs to the glyph-run call. Stack
   reservation and actual touched stack lines are reported separately. Within
   the run, scalar endpoints directly fill the four vertices; the initial
   compiled candidate retained 64 bytes of temporary-array stores and another
   64 bytes of reloads per glyph. Bank changes, packet flushes and depth remain
   in their existing positions.
4. Native `messageCamera` uses one immutable 64-byte orthographic matrix
   for the fixed 512x384, near-zero/far-minus-100 camera. It still calls
   `GXSetProjection` for every glyph, preserving restoration after other
   draws. The identity matrix and `GXLoadPosMtxImm` / `GXSetCurrentMtx` calls
   are removed only on the native path: those two Dreamcast stubs are empty.

No queue capacity, admission, texture resolution, source lifetime, atlas
replacement, glyph run extension, overlay-depth allocation or draw order changes.
PPC and non-native-message camera paths retain the original construction.

## Data map: what a draw reads

Sizes are target structural sizes. They do not imply one fill per record;
compiled address traces below distinguish demand bytes, distinct 32-byte lines
and repeated line visits.

| Record | Bytes | Read/write order |
|---|---:|---|
| `IdUnit` | 312 | Texture indices/flags near +0x6c/+0x7f; matrix 48 bytes at +0x08; vertices 48 at +0xa0; color 16 at +0xe8; UV endpoints 16 at +0x110; special paths also read identity/mask fields |
| Screen matrix / local concat result | 48 / 48 | Screen and unit matrix feed concat, then each corner reads the result |
| GX compact projection / returned viewport | 28 / 24 | Copied into bridge locals; returned viewport includes alternate-line jitter |
| TPL palette / descriptor / texture / CLUT header | 12 / 8 / 36 / 12 | Pointer chase from current texture work, image metadata, optional palette; HUD mask qualification reads filter/LOD fields |
| `Re4dcUiImage` / `Re4dcUiQuad` | 28 / 104 | Bridge construction -> XY/UV finite scan -> immediate texture resolution -> queue copy -> material/geometry drain |
| UI handle | 32 | One/two candidate checks, source/entry epochs; indexed images also compare live palette bytes |
| Cached polygon header / ordinary emitted packet | 32 / 160 | Header lookup/copy, then four vertex writes; emitted packet occupies five aligned lines |
| `MesQue` / `MessageFont` / `FONT_TEX` | 16 / 220 / 100 | Queued character and placement -> width-table pair and cell dimensions -> sheet-0 texture and palette descriptors |
| `Re4dcUiGlyph` | 64 | Synchronous source descriptor -> validation and atlas match -> compact queued record |
| `GlyphCell` / `GlyphBank` / `GlyphQuad` | 20 / 12 / 16 | Exact atlas identity key and frame stamp; palette bank; two adjacent queued glyph records fit one aligned line |
| Glyph packet scratch | 2080 | Up to 65 commands, reused across run flushes; bank header only when the bank changes |

An existing 104-byte quad slot spans four lines at its queue's eight-byte stride
phases. Removing clears removes repeated visits to those addresses, not the
mandatory five output packet lines. Output capture/transport reads are separated
from preparation where fixtures use an explicit submission adapter.

## Why a full static-HUD geometry cache was not added

Unchanged HP/ammo does not imply unchanged rendering. The life meter eases its
rotation, colors and geometry; ID size/path/color curves and parents can move;
camera FOV, projection, viewport jitter and prompt/mask substitution remain live.

A naive exact projected-quad record needs a 196-byte input snapshot (screen
matrix 48, unit matrix 48, source vertices 48, projection 28, viewport 24) plus
32 output bytes before tags/padding. Thirty-two 256-byte aligned entries would
add 8 KiB of competing working data. This is not a theoretical minimum, but it
is a poor starting point for a D-cache-sensitive workload without a hit census.
Existing matrix versions can shorten the key only with a separate lifetime
generation: a pooled unit can reuse its address and version one with a different
matrix. No hash-only or pointer-only equivalence shortcut is used.

Other rejected shortcuts: caching a complete packet would retain an obsolete
`overlay_depth`; skipping texture resolve could outlive source storage retired
after the OT callback; ignoring font invalidation could reuse different glyph
data at the same address. Rewriting `(uv * cover) / width` as `uv * (cover / width)`
would change float rounding. Existing atlas/header/viewport caches remain the
appropriate owners of those stable values.

## Exactness scope

Every bridge field and every vertex word remains defined; current projection,
resolution scale, image size, cover flags, UVs, colors and blend are read on the
existing path. `overlay_depth()` still executes once per emitted element, and
glyph header/buffer boundaries keep their existing order.

The constant message matrix is qualified under the public normal FP contract:
KOS startup sets FPSCR to `0x00040000` (round-to-nearest, DN enabled, single mode,
exceptions disabled), and the audited game paths do not change rounding mode.
The audited KOS revision is `804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`:
`kernel/arch/dreamcast/kernel/startup.S:80-85` initializes the mode,
`irq.c:303` inherits it for new threads, and `entry.s:195` restores saved
FPSCR on context return. Existing game bank/width switches do not change RM.
The resulting compact GX words are
`3f800000 3b800000 bf800000 bbaaaaab 3f800000 3c23d70a bf800000`.
It does not claim arbitrary rounding-mode or floating-point exception-status
equivalence; eliminating divisions can change sticky status flags.

One baseline limitation matters for raw command comparisons: KOS
`pvr_poly_compile` does not initialize the ignored last four words of an ordinary
packed-color header. Its initial `dcache_alloc_line_with_value` leaves the rest
of an allocated cache line undefined by the KOS contract (`include/kos/cache.h`,
lines 224-227); the compiler then writes the other three defined header words.
Therefore the ignored tail is not guaranteed even for static zero-initialized
glyph-header storage after a real cold-cache allocation. Initialized
cached-header fixtures can compare all 40 packet words; cold compiler fixtures
compare the four defined header words and all 32 vertex words, explicitly
excluding only the four ignored header words. Full glyph-packet comparison in
the scalar fixture qualifies its initialized memory model, not deterministic
ignored header-tail values on hardware. The candidate does not canonicalize or
suppress any headers.

## Compiled cost, size and verification

### Cost model and observed data traffic

All cycle figures are **model estimates**, at 200 MHz with perfect D-cache,
no DMA and zero store-queue cost. Warm figures assume perfect I-cache. Cold-I
figures begin with the model's 8 KiB I-cache cold once per complete probe at
the synthetic ELF layout. Demand bytes/lines are executed accesses, not cache
fills, misses or external bus traffic. Literal loads count as data; instruction
fetches do not. Reused stack and packet lines must not be added as distinct
frame-wide lines across calls.

The message-camera probe executes the complete production `messageCamera`,
actual SDK `C_MTXOrtho`, existing SH-4 identity implementation and actual GX
functions. It compares all 16 matrix words at `GXSetProjection` entry and the
seven resulting compact projection words. No native assembly was added.

The native emitter probe enters complete compiled `ui_draw_quad`, including its
glyph branch, and executes the real `begin_pvr_packet`. The tested function
sections are byte-identical to a separately compiled production TU without
fixture exports. Cached headers are preseeded; package metadata lookup is a typed
adapter supplying actual `Header`/`Texture` layouts. `stream_send` is an observed
zero-cost edge: transport, upload, allocation and GPU service costs are excluded.
Other unresolved paths fail closed if reached. The scalar interpreter's bounded
conversion support is qualified for the synthetic inputs; this is not general
hardware FP conformance.

| Measured phase | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Load/store instructions OFF → ON | Load/store bytes OFF → ON | Distinct 32-byte lines OFF → ON | Total line visits OFF → ON |
|---|---:|---:|---:|---:|---:|---:|
| Ordinary orthographic ID bridge | 1,024 → 997 | 1,490 → 1,459 | 197/94 → 196/70 | 688/376 → 686/280 | 31 → 32 | 291 → 266 |
| Message camera, per glyph | 168 → 41 | 308 → 100 | 18/36 → 11/7 | 72/144 → 44/28 | 8 → 5 | 54 → 18 |
| Ordinary cached-header quad drain | 912 → 567 | 1,329 → 920 | 158/108 → 100/66 | 611/408 → 383/264 | 33 → 32 | 266 → 166 |
| One-glyph run drain | 395 → 320 | 781 → 691 | 98/77 → 80/66 | 357/308 → 279/264 | 25 → 24 | 175 → 146 |
| 16-glyph run drain | 4,075 → 2,485 | 4,461 → 2,856 | 969/857 → 501/591 | 3,496/3,428 → 1,618/2,364 | 88 → 86 | 1,826 → 1,092 |

Repeated visits in those rows fall from 260/46/233/150/1,738 to 234/13/134/122/1,006.
The 16-glyph run emits the same 2,080 packet bytes and preserves its original
flush boundaries. The average drain cost per glyph in that run is 254.69 →
155.31 warm cycles; use the full run total when pricing runs, not the singleton
cost multiplied by 16. Camera work is a separate per-glyph term. The ordinary
quad drain removes **372 demand bytes**, and the bridge removes another 98.
The bridge's distinct-line count increases by one in this layout despite its
lower repeated traffic. It must not be described as a smaller unique working set.

The bridge probe executes the complete compiled body, including corner projection
arithmetic. Texture selection, camera-state service, identity-screen concat and
native enqueue have explicit typed adapters; the concat adapter copies the unit
matrix for the synthetic identity screen. Those original service implementations
are excluded, and adapter instructions remain in both totals. Plain, paletted,
perspective-plus-jitter and mask cases each save 27 warm cycles and 96 store
bytes; all 104 output bytes match. These are changed-phase costs, not the full
HUD callback, texture residency or message-source processing cost.

### Candidate decisions from compiled code

| 16-glyph drain candidate | Warm / cold-I cycles | Load/store bytes | Distinct lines | Line visits |
|---|---:|---:|---:|---:|
| Baseline, arrays in inline glyph path | 4,075 / 4,461 | 3,496 / 3,428 | 88 | 1,826 |
| Separate glyph function, arrays retained | 4,103 / 4,490 | 3,534 / 3,460 | 88 | 1,845 |
| Scalar vertices, compiler outlined the small helper | 5,195 / 5,604 | 5,078 / 3,212 | 86 | 2,169 |
| Accepted scalar body, helper inlined | 2,488 / 2,858 | 1,618 / 2,364 | 86 | 1,092 |
| Final caller after quad-dimension hoist | 2,485 / 2,856 | 1,618 / 2,364 | 86 | 1,092 |

Simply moving the glyph body out of line reduces ordinary-quad stack reservation
but costs 28 cycles per glyph run. The first scalar version then introduced four
helper calls per glyph under `-Os`; it was slower despite fewer distinct lines.
Forcing that small helper inline removes closure/call traffic without growing
the total native executable beyond the outlined candidate's size. This is a
C++ inlining decision, not new assembly or a linker change.

The final assembly audit also found four per-vertex dimension conversions still
inside the ordinary quad loop. Hoisting them saves another **250 warm cycles**
and **274 demand bytes** for the ordinary quad relative to the prior candidate.
It reduces that function from 856 to 824 executable bytes without changing its
504-byte stack frame. Covered/scaled quads save another 162 cycles and 180 bytes.
One tradeoff is explicit: the ordinary and fixed-depth probes gain one distinct
line versus the previous candidate (31 → 32 and 30 → 31); their repeated visits
and bytes fall substantially. The final ordinary quad still touches fewer lines
than the OFF baseline (33 → 32). The glyph body and its traffic do not change;
the three-cycle difference in its final row comes from caller shape.

### Size, stack and verification

| Production TU | Executable delta | Other allocated delta | Total allocated delta | BSS delta |
|---|---:|---:|---:|---:|
| `native_ui.cpp` | +48 B | 0 B | +48 B | 0 B |
| `ui_bridge.cpp` | -56 B | 0 B | -56 B | 0 B |
| `mes.cpp` | -56 B | +64 B constant matrix | +8 B | 0 B |
| `id_sys.cpp`, `gx_stub.cpp` | 0 B | 0 B | 0 B | 0 B |
| **Total** | **-64 B** | **+64 B** | **0 B** | **0 B** |

The native UI object's executable bytes are 77,486 → 77,534. Ordinary
`ui_draw_quad` stack reservation falls from 2,460 to 504 bytes; a glyph branch's
observed nested peak falls from 2,460 to 2,356. This does not mean the ordinary
path previously touched every reserved byte. Bridge static stack stays 304
bytes (308 observed including its adapter), and `messageCamera` falls from
116 to zero. No persistent mutable cache or heap allocation is added.

The exact base and candidate pass **180 OFF identity comparisons**: knob absent
and explicit zero, full `-E -P` output and raw target objects, across nine valid
Make-derived profiles and five translation units. Debug output is omitted
consistently. The final native refinement refreshed its 36 comparisons; the
other 144 retain matching source and Make hashes from the full qualification.
There are also **36 unchanged-ON comparisons** for the ID and GX units. With
native messages disabled, the message camera remains identical with the knob ON.
The six complete production objects used by the native, bridge and camera
probes (OFF and ON) match the independently Make-built public objects byte for
byte. The target comparisons cover seven native cases, four bridge cases and
all message-matrix/GX words.

The [qualification README](../../tools/d367/ui_draw_lean/README.md) gives the
full reproduction commands and fixture limits. The
[measurement receipt](../../tools/d367/ui_draw_lean/measurement_receipt.json)
pins the source, recipe, tools, comparisons and compiled measurements; the
[runtime receipt](../../tools/d367/ui_draw_lean/runtime_receipt.json) records
the exact-output matrix, sanitizers and negative controls.

The host fixture compares actual production bridge, enqueue, both ordinary
drains, glyph-run and camera bodies. It uses the actual declarations and texture
`Package` layout/getters, KOS vertex/header/context declarations and header
construction, including the native mip-adjust wrapper. Opaque host pointers
are serialized to explicit target-sized fields: all **104 bridge bytes** are
compared without treating host pointer padding as a target object.

All nine profiles plus the public ASan/UBSan repetition pass: **77,018 paired
cases**, **1,677,068 emitted vertices**, **15,439,560 scalar TA words**,
**140,117,224 observation bytes** and **62,415,792 framed scalar TA-stream bytes**.
Repeated inputs across profiles are included in those totals. The public profile
alone has 7,743 cases: 5,795 native, 1,280 bridge, 256 camera and 412 glyph cases.
Its 12,124 preseeded header emissions compare all eight words; 12,790 compiled
header emissions compare the four defined hardware words. All vertices compare
in full. The companion raw scalar stream compares every initialized fixture
word and packet boundary; the MOVCA qualification above still applies.

Coverage includes live XY/UV/color/blend/image-size mutations; absent/present
palettes; perspective, jitter and dynamic resolution; invalid enqueue states;
queue-source overwrite after submission; ordered prefix drains and legacy
drains; glyph bank changes and 15/16/17 flush boundaries; fixed and autosort
depth; and repeated projection restoration. Actual `C_MTXOrtho` is kept
unspecialized in the host reference, so the constant-camera assertion compares
its complete 16-word output as well as the seven live GX words.

Four negative controls are detected: wrong palette defaults, wrong `oargb`,
wrong camera constant and wrong glyph corner. The final runtime receipt hashes
the measured native source as
`6fb51fb0d573aec230646409a0372666e42146b42184362aacb6d3352f6bd67b`.
No game data, emulator or console was used for these controls.

## MODELLED whole-frame contribution

The 0.7 ms UI area is a whole-area observation, not all removable setup. No
current HUD/glyph census is available; 87/50 world parts are not UI populations.

For accepted draws, the ordinary bridge saves 27 warm cycles and its ordinary
quad drain saves 345. Message-camera work saves 127 per glyph. A 16-glyph run
saves 1,590 in its complete drain, including the small final caller-shape change.
At 200 MHz, divide the sum of matched phase deltas by 200,000 for milliseconds.
Qualifying source HUD masks become ordinary prepared quad submissions through
`hud_source_mask_native.inc`, so accepted ones share the ordinary drain path.
Count each admitted prepared quad once, using the relevant cover/size case;
unsupported masks have no native drain saving.

| Explicit synthetic frame mix | MODELLED warm time saved | Demand bytes removed | Demand line visits removed |
|---|---:|---:|---:|
| 20 ordinary ID quads, no message glyphs | 0.03720 ms | 9,400 | 2,500 |
| One 16-glyph run, including its 16 message-camera calls | 0.01811 ms | 5,246 | 1,310 |
| 20 ordinary ID quads plus four 16-glyph runs | 0.10964 ms | 30,384 | 7,740 |

The text examples use the measured single-bank run shape. Other run lengths,
bank changes and palette misses need their own counts and measured terms.
These are changed-phase model contributions, **not predicted r101 frame gains**.
Do not sum per-call cold-I prices or distinct lines as though every call begins
with a fresh cache. Console A/B decides the value of reduced repeated traffic
and the small, layout-sensitive changes in distinct lines.

## Open questions back to Claude

1. What are ordinary ID quads, masked HUD quads, message glyphs and glyph runs
   per rendered frame at the r101 cross and in a representative text/menu view?
2. Does console A/B show a benefit from less repeated stack/packet traffic,
   especially in HUD-only frames where the message-camera saving is absent?

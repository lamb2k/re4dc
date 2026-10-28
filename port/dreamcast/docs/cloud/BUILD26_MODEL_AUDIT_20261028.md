# Build 26: model draw fallback audit

Base: `9a66e3fce8899f69378f12b5f9517f297f1fa314` on `origin/t15/int`.
Branch: `codex/draw-fallback-audit-20261028`.

`DRAW_FALLBACK_AUDIT=1` adds model-side reason counters at the renderer's actual
slow branches. `ACTOR_CLIP_FRONT26=1` is a separate, default-off render
approximation: a triangle wholly in front of the depth planes can use the
already prepared vertex cache even when its containing strip needs near
clipping. Triangles selected for the slow path retain source reconstruction and
the existing clipper. Neither switch changes gameplay, animation, collision,
source model selection or lifetime ownership.

The near-camera model candidate is **provisional**, not the top model fallback
measured on a console. The queue supplies a barn model total of 20,930 µs per
drawn tick and an exact-light estimate of 1.6 ms MODELLED; it supplies no
per-reason fallback census. The local owner must collect that census before
ranking changes. See [the queue's fast-path section](CLOUD_AGENT_QUEUE.md) and
the [combined Build 26 report](BUILD26_DRAW_FALLBACK_AUDIT_20261028.md).

## Recipe and source boundaries

The current public Make recipe, including later `ch2-build.sh` overrides,
resolves the following values in both game and QA profiles. These are build
settings, not proof of package admission or a recording of the console disc.
The validation recipe disables `NMR_POOL_LOD` because its private Ganado input
is unavailable. The final resolved-knob receipt is produced by
[`recipe_values.py`](../../tools/cloud/build26/recipe_values.py).

| Group | Current public values |
|---|---|
| Native ownership | `NATIVE_ACTOR=1`, `NATIVE_ACTOR_FAST=1`, `NATIVE_ACTOR_DIRECT=1`, `NATIVE_ACTOR_SKIN=1`, `NATIVE_ACTOR_SKIN_LAZY=1`, `MODEL_STREAM_FIX=1`, `ACTOR_REPLAY_SKIN=1` |
| Setup and colour retention | `ACTOR_SETUP_LEAN=0`, `ACTOR_BYTES_LEAN=0`, `ACTOR_NO_CLEAR=1`, `ACTOR_MOVCA=0` |
| Kernels | `ACTOR_VTX_KERNEL=1`, `ACTOR_LIGHT_N16=1`, `ACTOR_EXACT_FAST=1`, `ACTOR_SKIN_FTRV=1` |
| Lighting | `ACTOR_PROBE_LIGHT=1`, `GANADO_LIT=0`, `GIGANTE_LIGHTS=1`, `GIGANTE_LIGHTS_TREES=1`, `ACTOR_LIGHT_CAP=0`, `NATIVE_ACTOR_PRELIT=1` |
| Clipping and visibility | `ACTOR_CLIP_REUSE=0`, `NATIVE_ACTOR_UV16=0`, `ACTOR_BACKFACE_CONE=0`, `CPU_BACKFACE=0`, `TA_GUARD=0` |
| Generic model | `MODEL_DRAW_PLANS=1`, `MODEL_POSITION_CACHE=1`, `MODEL_PREP_KEEP=1`, `MODEL_ROOM_STRIPS=1`, `D349_RENDERER_STACK=1` |
| Owned-model setup | `ACTOR_PLAN=1`, `ACTOR_BIND_REUSE=1`, `ACTOR_MATERIAL_RECORD=1`, `BRIDGE_LEAN=1` |

The expanded resolved Make receipt also records `RIGID_CHUNK=1`,
`COARSE_ONE_SUBMIT=1`, `STATIC_OBJ_BATCH=2`, `LEON_SKIN_SLOTS=2`,
`CHAR_CHUNK=0` and `CHAR_CHUNK_BACKEND=0` in both profiles. The recipe
explicitly says the character deduplication experiment was disabled after it
measured slower. Its absence is not evidence that enabling it will help.
Sources: [recipe](../../tools/d367/test15/t15-build.sh),
[current overrides](../../tools/d367/ch2/ch2-build.sh),
[character chunk switch](../../game/chardraw19.mk).

Build 25 (`ee9a5c41`) was published before this build, but is not in this base.
This branch therefore does not import `ACTOR_LIGHT_FAST_ONLY` or its offline
bake implementation. Its lighting rows describe the code actually present at
this base. When Claude combines the branches, retain Build 25's compile-time
exclusion of the old light evaluators: `a_lit_exact` must stay zero with
`ACTOR_LIGHT_FAST_ONLY=1`. The Build 25 invariant counter remains the direct
proof for that mode. Build 26 does not claim to have tested an unmerged combined
source tree.

## Reading the counters

The reason registry is
[`draw_fallback_model.def`](../../game/platform/include/draw_fallback_model.def).
The shared tick lifecycle, QA page and compact QA_LINK rows are described in the
combined report. Each model hit uses the shared allocation-free saturating
counter. There is no extra timer, logging, format operation or complete
triangle prepass in a model hot loop.

Counters are work observations, not an additive attribution of milliseconds:

- `a_contract`, `a_projection`, `a_convert_fail` and `m_obj_split` are
  **declined attempts**. The caller may retry, rearm/materialize a skin, use
  another representation, or reject invalid input. A decline is not proof that
  the legacy walker ran.
- `m_legacy` counts entry to an actual generic walker after the deferral
  decision. It includes an emit attempt that later fails, and excludes a
  deferred admission that did not walk geometry. The generic walker can also
  serve a world package's source fallback.
- `a_pos_fallback` and `a_lit_fallback` count vertices left after AVK. Their
  continuation can use the older SH-4 loop or portable C; they do not mean that
  the complete model left the native actor renderer.
- `a_bake_relit` counts **actual runtime rebakes** in `bake_prepare`. Ordinary
  dynamic lighting without an eligible baked field does not increment it.
- Vertex, corner, triangle, meshlet, part, info and refusal units are different.
  A clipped vertex can appear in several triangles; repeated corner work is
  intentional evidence. An object can trigger several independent reasons.

For example, `a_lit_colour` can cause `a_lit_exact`, while the same part also
causes `a_clip_strip` and `a_clip_rebuild`. Adding those item counts or pricing
each with a whole-part cost would double count the work.

## Inventory: model ownership, setup and skinning

The sites below are in
[`native_actor_fast.cpp`](../../game/platform/native_actor_fast.cpp),
[`native_model.cpp`](../../game/platform/native_model.cpp) and
[`model_bridge.cpp`](../../game/model_bridge.cpp). “Possible” means the source
contract admits the condition in chapters 1–2; its frequency is unmeasured.
“Observed context” refers only to the documented queue or recipe evidence, not
to a new console run.

Cost notation is defined in the cost section. Variable-size costs are formulas
in the actual item count, not invented fixed timings for arbitrary assets.

| Fast / slow split and knob | Trigger of the slow branch | DFA reason | Cost per item; chapter 1–2 status |
|---|---|---|---|
| Meshlet actor / old actor, `NATIVE_ACTOR_FAST=1` | Build selects `native_actor.cpp` instead | `m_actor_old` on old actor dispatch | Old per-info preparation plus its vertex work; not reached by the current recipe. It is distinct from generic GX walking. |
| Native actor / generic admission, `NATIVE_ACTOR=1` | Missing lighting; unsupported alpha/colour contract; attenuation outside 1/2; unsupported stride/quantization; empty/out-of-range arrays or stream; unavailable lazy skin; non-perspective projection or empty viewport | `a_contract` | Failed bounded admission, then whichever path actually runs. Price a later `m_legacy` separately. Possible for valid source representations outside the native subset; malformed-data rejection is not a performance opportunity. |
| Valid depth range / decline | Nonfinite near/far, nonpositive near or far≤near | `a_projection` | Two divisions plus validation, then rejection/retry. Valid game camera data should not trigger it; frequency unknown. |
| Converted blob / on-demand conversion | No accepted native blob; converter cannot build it | `a_convert_fail` | Conversion scans display-list records and strip tuples before decline. Cost scales with input corners and workspace; not a constant per model. First-use or incompatible-source possibility. |
| In-place conversion / transient conversion | Native representation does not fit the original GX list; second scratch conversion succeeds | `a_transient` | Repeated conversion and scratch traffic for each submission, approximately `O(corners + tuple sorting)`, plus scratch writes of blob size. Possible for short or fragmented lists; offline native blobs remove the repeated trigger. |
| Workspace allocation / refusal | Conversion/LOD scratch does not fit the current primitive-buffer workspace | `a_workspace` | Failed allocator check is small; a repeated conversion or later generic walk is the expensive consequence. Counts refused allocations, including a deferred LOD build that retains full detail. Possible under pressure. |
| Frame-context reuse / rebuild | `(frame, info, modelview, projection, viewport)` differs or four-entry cache evicts | `a_frame_miss` | Matrix/state copies, screen matrix construction, and for skin a table allocation/ready clear. Fixed setup plus `114*palette_entries` requested bytes before allocation rounding. Matrix/pose changes are normal in chapters 1–2. |
| Native palette/source skin / already transformed source arrays | Stride-6 source cannot obtain matching palette/source positions, normals, counts and normal format | `a_skin_source` | Draws `kSource` positions; skin may already have been materialized upstream. Do not charge source skinning again unless `a_skin_expand` fires. Possible on replay or source-owned parts. |
| Prepared palette matrices / per-run temporary matrices | Skin selected, but frame table allocation fails | `a_skin_table` | Repeated `position_matrix` and light-direction preparation instead of table hits: `O(palette runs)`. Source palette is 48 B/entry; prepared position is 64 B and light directions 48 B. Possible under workspace pressure. |
| Lazy native skin / full source materialization | Native admission falls through; ordinary or lazy entry is actually materialized | `a_skin_expand` | `O(source positions + normals + palette work)`, including writes of full source arrays. This is a data-traffic event, not only a missing fast-kernel call. Replay repair is enabled, but remaining declines can still reach it. |
| Skin registry entry / refused registration | Fixed skin registry is full | `a_skin_slots` | Scan up to registry capacity and refusal; later path decides rendering. Documented historical r119 pressure motivated `LEON_SKIN_SLOTS`; count the current recipe rather than assuming the older 64-slot limit. |
| Direct TA window / packet buffer | Direct path disabled/unavailable or direct begin declines before packet fallback | `a_packet` | Packet staging adds copy/read traffic and its packet ownership work; final TA emission remains. At least one extra read/write visit of each staged 32 B vertex. Possible with fallback modes; default direct=1 is not proof every part is direct. |
| Cached AVK argument setup / repeat, `ACTOR_SETUP_LEAN=0` | Feature disabled; each eligible position/light call fills invariant arguments again | `a_setup_repeat` | Measured setup class **S**. Counter counts argument preparations, so a position/light pair contributes two. Deliberately present in current recipe, including chapters 1–2. |
| AVK position kernel / older loop | AVK disabled, incompatible position stride/count, missing skin table, or kernel returns unfinished records | `a_pos_fallback` | **V** for completed fast work plus residual-loop cost. Source/UV/record/cache traffic still exists. Large counts or unusual formats are possible; actual frequency unknown. |
| Owned proof memo / full proof (`ACTOR_PLAN`, `ACTOR_BIND_REUSE`, material records) | Runtime plan disabled, lifetime/transaction/input identity changes, or role/texture/semantic/material proof cache misses | Seven `a_plan_*` hook rows; coverage details below | Proof scans and binding work precede renderer admission. A plan miss does not imply generic drawing, and the existing hook does not observe every cold miss. |
| Static object batching / separate lists, `STATIC_OBJ_BATCH=2` | Wrong class/pass, no live room allocation, incompatible list count/record, or part/material/light identity changes | `m_obj_split` | Separate per-part setup **S**, header/texture work and list walks. Current recipe enables batching; source props can still decline by design. |
| Qualified batch / build failure | Concatenation entry/scratch allocation, size or unconverted-list contract fails | `m_obj_batch` | Actual fallback submits each of the pending lists; count is number of lists. Conversion/setup overhead repeats. Runtime count is needed before spending memory on a larger table. |

### Existing APLAN hook coverage

Build 26 mirrors `re4dc_actor_plan_note(kind, hit, bad)` misses into separate
`a_plan_bind`, `a_plan_pre`, `a_plan_roles`, `a_plan_row`, `a_plan_hand`,
`a_plan_sem` and `a_plan_mat` rows. A successful hit does not increment a miss;
an invalid kind returns before indexing either table. These counters describe
the existing callers, rather than inventing observations for uncalled kinds.

| Hook kind | Current caller and observed condition | Important blind spot / work cost |
|---|---|---|
| `bind` | `owner_leon_bind_planned`, every planned-bind call, including a failed transaction/frame/lifetime/owner match | A miss can run the full Leon palette binding proof, including up to 119 part matrix checks. It is observed when this wrapper is selected. |
| `pre` | `owned_submit_runs`, only the prepared + runtime-plan-enabled branch | Failed held leases can reject submission; this is not always a full-proof fallback. Unprepared or runtime-disabled full preflights do not call the hook. |
| `roles` | `re4dc_actor_role_bindings`, when an identity-matching memo entry is revalidated | Revalidates the info chain, role and hand identity. No matching entry, changed lifetime serial, or runtime plan off runs the full scan without a note. A zero is not proof there were no full scans. |
| `row` | `actor_current_role`, when a matching row memo is revalidated | Info membership and current-source validation can fail, then scan all candidate roles. Cold/lifetime misses and disabled reuse bypass the note. |
| `hand` | `owner_material` hand texture qualification in `coarse_actor_material.inc` | Reports its memo's hit/miss when that planned texture proof is attempted. Other material paths have their own contracts. |
| `sem`, `mat` | Defined enum kinds; no call sites in this base | Reserved rows, not observed semantic/material proof misses. Do not interpret zero as absence of work. |

`ACTOR_PLAN=0` compiles out this reuse layer and the hook entirely. The current
recipe is 1. The runtime plan switch can also suppress several callers, so
record it with the diagnostic. The full-proof costs depend on part/role/run
counts and backing lifetime; no fixed cycles-per-miss or chapter frequency is
asserted. The source interfaces are
[`actor_plan.h`](../../game/platform/include/actor_plan.h),
[`actor_lifetime.inc`](../../game/actor_lifetime.inc),
[`coarse_actor_owner_leon.inc`](../../game/coarse_actor_owner_leon.inc),
[`coarse_actor_material.inc`](../../game/coarse_actor_material.inc) and
[`native_actor_owner_runs.inc`](../../game/platform/include/native_actor_owner_runs.inc).

## Inventory: lighting, colour and data variants

| Split and knob | Slow trigger | DFA reason | Cost and chapter 1–2 status |
|---|---|---|---|
| Constant/probe/≤3-light fold / exact evaluator | Per-vertex ambient or material source while `ACTOR_LIGHT_CAP=0` | `a_lit_colour`, then actual `a_lit_exact` vertices | **L(V,K)**. A documented Build 25 trigger; ordinary coloured source models can reach it. |
| Same fold / exact evaluator | Diffuse mode not 2, or material×TEV scale fails the fold's 255 cap contract | `a_lit_scale` | **L(V,K)** if no later constant/capped result. Documented trigger; frequency unknown in this recipe. |
| Same fold / exact evaluator | Fourth significant light on a model without a bounded overflow fold | `a_lit_fourth` | **L(V,K)**. `GIGANTE_LIGHTS`, tree coverage and `ACTOR_LIGHT_CAP` change admission. Multiple lights can occur; the new census must establish incidence. |
| Normal-basis fast fold / fallback | Leon-marked part has no finite invertible normal basis | `a_lit_basis` | Exact helper or CAP constant fallback according to knobs; not a normal valid-pose expectation. Do not remove the validity check. |
| Cached actor probe / per-part fold | Probe policy ineligible, vertex/diffuse/material contract fails, singular part basis, or invalid probe | `a_probe_miss` | Probe reuse is replaced by a per-part selected-light fold; exact lighting is a further independent outcome. With current probe=1, non-Leon policy declines are expected and must not all be charged as exact vertices. |
| Exact helper / fast helper | Final `Lights` remains neither constant, baked nor fast | `a_lit_exact` | Counts entry vertices to the exact helper, including its defensive constant fallback. Documented barn MODELLED estimate was 1.6 ms for the complete exact-light contribution, not 1.6 ms per part. |
| AVK light kernel / older C or SH-4 loop | Per-vertex alpha, normal stride/count mismatch, missing direction table, disabled N16 kernel, or incomplete AVK run | `a_lit_fallback` | Re-reads tuple/normal data and writes ARGB; see **V**. It is still the native actor's fast directional light model, separate from exact lighting. Possible with alpha and wide normals. |
| Constant prefix retention / repeated writes, `ACTOR_BYTES_LEAN=0` | Disabled; or per-vertex alpha; or MOVCA composition cannot preserve old cache colour | `a_flat_rewrite` | **F**: writes 4 B for every vertex each meshlet, plus optional half-post read/modify/write. Current recipe deliberately repeats it. |
| Runtime baked-colour copy/scaling / rebake | Palette hash differs; directions exceed tolerance; colour matrix is neither equal nor valid proportional scale | `a_bake_relit` | Lights every level-0 record and stores its packed565 field, then copies/scales the draw's selected records. Work can exceed the current LOD's vertex count. This counter excludes normal dynamic shading with no bake field. Moving/relit models can trigger it. |
| 16-bit UV / 32-bit UV | `NATIVE_ACTOR_UV16=0`, non-power-of-two/padded texture, scroll or quantization error above half texel | `a_uv32` | Vertex words/TA format stay wide; a successful compact path would use 20 rather than 24 relevant bytes per vertex. The 32 B source cache remains. Default off is an intentional quality choice, not a data failure. |
| Backface-cone reject / transform-test-emit | Cone feature disabled, no valid cone tail, or meshlet has no qualified cone | `a_cone_absent` | Normal **V** and possible emission, even if later CPU/PVR culling discards triangles. Current recipe=0; converter/data qualification and a look gate are prerequisites to enabling it. |
| Chunk position dedup / ordinary position pass | `CHAR_CHUNK` enabled but all records have distinct adjacent positions | `a_chunk_unique` | Same position count **V**, with the dedup scan already paid. This explains why a “new path” need not be faster. |
| Chunk normal dedup / ordinary light pass | Per-vertex alpha; all normals unique; or side scratch unavailable | `a_chunk_alpha`, `a_chunk_nuniq`, `a_chunk_scratch` | Same light count plus any hash/scan paid before declining; scratch failure can occur under pressure. Current character chunk feature is disabled after its prior regression. |
| Shared chunk sink / actor strip sink | Non-direct part, vertex count exceeds backend bound, or worst-case clipped slots exceed 32,767 | `a_chunk_sink`, `a_rigid_sink` | Original strip scan/clip/emit remains. Reasons name which adapter declined; they do not mean the model is lost. Rigid prop backend is active in the recipe. |
| Rigid small-flat approximation / full rigid model | Projected size exceeds `RIGID_FLAT_PX`; a sphere touching near receives the full-size sentinel | `a_rigid_full` | Full lighting/LOD work **V/L**, instead of one constant and coarse LOD. A direct causal near-camera trigger for props, but no new frequency was measured. |

## Inventory: clipping and the generic model walker

| Split and knob | Slow trigger | DFA reason | Cost and chapter 1–2 status |
|---|---|---|---|
| Whole-meshlet emission / strip scan | Any cull/near outcode or current packet/window cannot fit the full index stream | `a_strip_scan` | Reads strip indices/outcodes, then culls, copies or clips each strip. **E(I)** plus any **C**. Near-screen/body context is documented; count unknown. |
| Strip copy / near clip | A surviving strip has a near-plane corner | `a_clip_strip` | **C(n)**, with `a_clip_tri` actual clipper invocations and `a_clip_rebuild` actual source-corner reconstructions. Current recipe reuse=0 reconstructs `3*(n-2)` corners. |
| Repeated reconstruction / corner reuse | `ACTOR_CLIP_REUSE=0` | Same `a_clip_rebuild`, separated by recipe | Build 24's exact reuse prepares `n` corners for a complete strip instead of `3*(n-2)`. A first capacity refusal stops both. No new counter prepass is needed. |
| Full triangle clip path / FRONT26 cache shortcut | FRONT26 disabled, depth bit set, or nonfinite cached coordinates; invalid indices abort without cache access | `a_clip_tri` and `a_clip_rebuild` | New helper prices are in the combined target receipt. A nonfinite cache never qualifies for the shortcut. |
| Native renderer / generic GX walker | Static package and actor path did not consume the part; array and projection checks then accept it | `m_legacy` | **G(P,V,T)**: draw-plan selection, skin materialization if needed, per-corner transform/shade caches, topology and packet work. Does not double-count merely queued admissions. |
| Native draw plan / raw display-list walker | Plan feature off or no admitted plan | `m_plan_miss` | A validation walk followed by an emitting walk; at least two visits to the source stream and corner/index checks. Offline/pre-admitted plans remove the trigger where lifetime permits. Possible on unconverted content. |
| Shared/retained batch / part-local preparation | Shared preparation storage unavailable | `m_batch_miss` | Repeated position/normal/light preparation and local cache misses. Cost follows actual `m_pos_miss` / `m_shade_miss`, not a fixed cost for all vertices. |
| Position cache / transform | Missing retained/dense/direct-mapped entry, identity changes, collision or cache disabled | `m_pos_miss` | Source position decode, matrix transform, project, cache write. Dense 6/8 B source records can become scattered 32 B line touches. Common first references are expected. |
| Shade cache / normal and shade calculation | Position/normal/colour/generation key misses | `m_shade_miss` | Normal conversion/transform if its own cache misses, plus static-light lookup or **L(1,K)**. Different colour corners must not reuse another corner's shade. |
| Static-light cache / evaluator | No room-static context or generation/position/normal/colour mismatch | `m_static_light` | Actual prepared-source evaluation at that vertex. The name describes a failed room-static reuse opportunity; dynamic models normally have no such context. |
| Direct room strip / triangles | Packet capacity or worst-case expansion does not fit | `m_strip_space` | Per-triangle topology/cull/clip after the failed direct eligibility check. Counts strips, not vertices. |
| Prepared direct room strip / triangles | Vertex preparation or near/far range rejects a direct strip | `m_strip_clip` | Per-triangle **C**, after already prepared prefix work. Current data may cross planes; frequency unknown. |
| Generic triangle emission / clipper | Generic topology emits a triangle | `m_clip_tri` | Actual clipper calls, including all-front acceptance. Disabling `MODEL_ROOM_STRIPS` is visible here as more triangle work. |
| Stable UV packet / complete replay | First texture bind returns verified alternative UV scaling before any publication | `m_uv_replay` | Repeats the selected plan/walk and geometry preparation; never replays already published geometry. Root's texture audit identifies the resolution cause. |
| Streaming / buffered submission | Native owner reports non-streaming | `m_buffered` | Packet buffering instead of bounded streaming; writes retained vertices and later consumes them. May reject at capacity; not an unlimited allocation. |
| Packet reservation / refusal | Owner cannot reserve packet resources | `m_packet_fail` | Bounded failed reservation; no imaginary successful geometry cost is credited. Counts refusals separately from slow rendering. |

Actor screen edges are common-outcode rejects or PVR-scissored fast geometry;
near is clipped and far is a common reject. FRONT26 additionally keeps any
far-bit triangle on the original clipper. It does not introduce a new guard
band or change TA header cull, depth or blend state. Translucent actor parts
still defer and replay through native UI's existing bounded ordering. Root's
texture/translucent/effects inventory covers texture-resolution misses,
queue/sort/submit work and `ESP_SETUP_LEAN`; this model table does not count
those shared service costs again.

## Cost model and traffic

At 200 MHz, `milliseconds = cycles / 200000`. Warm means warm I-cache; cold
means an empty I-cache at the start of the stated complete fixture. These
prices do not model the console's operand-cache misses or concurrent bus/SQ
traffic. A counter cannot infer those misses from byte counts.

The following **historical compiled MODELLED anchors** price retained work;
they are not new Build 26 benchmark results and are not a universal cost of
every input format. Their original reports retain exact compiler/fixture
boundaries:

| Cost class / complete fixture | Warm / cold-I cycles | Loads / stores | Data-line exposure |
|---|---:|---:|---|
| **S**: eight skinned s16 position/light argument pairs, setup lean off | 2,337 / 2,846 | 700 / 500 | Subsequent pair touches 25 distinct 32 B lines; geometry kernels excluded |
| **V**: 32 dense one-palette N16 vertices | Position 1,268 / 1,583; light 1,203 / 1,475 | Steady iterations: position 10 loads/6 stores, light 5/1, plus setup/tail | Combined fixture reads 1,378 B and writes 896 B, 78 unique lines; scattering only indices raises it to 152 lines |
| **F**: four 32-vertex flat meshlets, bytes lean off | 533 / 731 | 118 / 190 | 360 B loaded, 748 B stored, 46 unique lines and 262 repeated touches |
| **C**: 64-vertex rigid near strip, reuse off, reconstruction edge only | 78,025 / 78,651 | 21,356 / 9,849 | 146 unique lines; 76,614 B loaded, 39,393 B stored |
| **C**: 64-vertex skin near strip, reuse off, reconstruction edge only | 99,043 / 99,743 | 26,937 / 10,221 | 158 unique lines; 96,892 B loaded, 40,881 B stored |

Sources: [Build 2 setup report](../D367_ACTOR_SETUP_LEAN_20261023.md),
[Build 7 bytes report](BUILD7_ACTOR_BYTES_LEAN_20261024.md),
[Build 24 clip report](../../tools/cloud/build24/actor_notes.md).
The Build 24 clip edge returned zero output; its prices exclude real clipping
math and nonempty TA emission. Its fixture executable was 3,192 B and peak
stack 716 B, not the entire renderer. They must not be presented as the new
FRONT26 executable or stack size.

For variable shapes, use these explicit work equations:

- **E(I)** streams `I` one-byte indices and `I` prepared 32 B vertex records,
  with repeated index references revisiting the same lines. Packet staging
  adds another full vertex-copy visit; direct SQ transfer is a separate bus
  cost. Dense aligned vertex records use one 32 B line each.
- **V(N,B)** reads tuple records of 6 B, plus 2 B each for optional colour/bake
  indices; positions 8 B, UV 4 B and normals 4 or 8 B per referenced vertex.
  Add 64 B per position-palette run and 48 B initially/36 B subsequently per
  light-direction run. The transformed cache is 32 B per vertex plus one
  outcode byte. Dense lower bounds are `ceil(bytes/32)`; scattered input
  indices can touch a separate line per record. These are payload bounds, not
  measured external reads.
- **C(n)** has `n-2` triangle attempts. Without reuse there are
  `3*(n-2)` source reconstructions; with reuse there are `n` for a complete
  strip. Each reconstructed input is a 52 B `RenderVertex` plus 4 B alpha;
  each surviving triangle writes three 32 B PVR vertices, up to two triangles
  for a near crossing. FRONT26 removes reconstruction and clipper calls for
  its cache-accepted triangles; it still pays bounded classification/copy.
- **L(N,K)** prepares selected lights once, then performs the exact evaluator
  for `N` vertices and up to `K≤8` lights, including normal/position reads,
  attenuation/diffuse arithmetic and an ARGB write. Materials and attenuation
  decide the instruction path. No current-target single cycle number is
  asserted for arbitrary `K` or arbitrary material flags.
- **G(P,V,T)** is actual generic part/vertex/triangle work: setup per `P`,
  transformations for `m_pos_miss`, shade evaluations for `m_static_light`,
  and clipping for `m_clip_tri`. Raw-stream replay and UV replay multiply the
  corresponding walks. Use counter deltas plus these components; do not
  multiply the barn's whole-model milliseconds by every decline.

Cold whole-frame extrapolation must not multiply an empty-I-cache fixture by
every vertex. For a deliberately specified illustration, ten successive
64-corner skinned near strips cost **4.95215 ms warm / 4.95565 ms cold-I
MODELLED** in the historical reconstruction-only arm: `10*99043 = 990430`
cycles warm, plus the first invocation's `99743-99043 = 700` cold-I cycles.
That composition assumes the fixture's code stays resident between strips.
It is not a barn census and excludes real clip/output work. Current FRONT26
costs and its declared frame workload are below. Full production object
deltas and observer costs are in the combined Build 26 target receipts.

## ACTOR_CLIP_FRONT26 behavior and proof

The helper checks all three local indices before reading outcodes or cache
entries. It accepts finite cached positions only when none of the three
corners has a near/far bit. It applies the existing `triangle_visible_xy`
area, cull and screen-edge predicate; copies accepted PVR vertices in original
triangle order; restores the two vertex flags plus final EOL; and clears the
UV16 scratch offset-colour word. ARGB, UV and material alpha come from the
already lit cache.

The strip walker supplies parity `t,t+1,t+2` / `t+1,t,t+2`, preserves first
capacity refusal, and calls the original reconstruction/clip block for slow
triangles. With `ACTOR_CLIP_REUSE=1` it lazily retains source corners in three
bounded slots. Fast triangles cause no source corner preparation. There is no
heap allocation, new assembly, linker work, persistent model cache or changed
frame owner. The implementation is in
[`actor_clip_front26.hpp`](../../game/platform/include/actor_clip_front26.hpp).

**Outputs allowed to change:** a shortcut triangle uses the ordinary actor
cache's FTRV/reciprocal projection instead of scalar `world_of + project`.
Subpixel coordinates, reciprocal depth and decisions exactly at a cull or
depth boundary can differ. A triangle the cached mask identifies as slow
retains the original clipper's coordinates, interpolation, UV, alpha and
ordering. This is not a promise of bit identity at every floating-point plane
boundary. UV16 uses its existing packed cache representation. Pose, normals,
lights, materials and source arrays are not changed by the shortcut.

The AVK outcodes use near32/far16; portable actor code uses near2/far1. The
production walker passes the actual constants as a template parameter. The
host actual-TU fixture exercises the portable layout; direct helper controls
also exercise the AVK mask, invalid indices, nonfinite cache entries, per-byte
ARGB identity and emitter refusal. It also calls all seven APLAN kinds
synthetically to verify their reason mapping; this does not manufacture
runtime callers or chapter occurrences for the two reserved kinds.

[`model_clip_host.py`](../../tools/cloud/build26/model_clip_host.py) compiles
the actual production actor TU and existing room clipper. Four arms cover
FRONT26 off/on × CLIP_REUSE off/on, **3,940 cases per arm**. Inputs include
rigid, skin, stride-6 source, s16 normals, lengths through 128, nonsequential
and independently indexed position/normal/colour data, all cull modes,
material/vertex alpha, packed/unpacked UV, front/behind/crossing/equality/far
planes, outside-screen/guardband coordinates, degenerate triangles and
capacity failure. Normal O2 and AddressSanitizer/UBSan both pass. LeakSanitizer
is disabled because this sandbox cannot inspect its process task list.

| Aggregate across the 3,940 synthetic cases | FRONT26 off | FRONT26 on |
|---|---:|---:|
| Clipper invocations, either reuse setting | 137,214 | 48,486 |
| Reconstructed corners, reuse off | 411,642 | 145,458 |
| Reconstructed corners, reuse on | 145,094 | 57,794 |
| Emitted PVR vertices, all arms | 101,394 | 101,394 |

The fixture populates cache coordinates through actual scalar
`world_of/project`, allowing exact TA/order/cull/alpha/UV16/capacity comparison
on these inputs. It does not emulate general SH-4 FTRV/FSRRA rounding or real
SQ/TA device behavior. Normal and sanitized receipts are
[model-clip-host.json](../../tools/cloud/build26/receipts/model-clip-host.json)
and [model-clip-host-sanitized.json](../../tools/cloud/build26/receipts/model-clip-host-sanitized.json).

## Current SH-4 FRONT26 cost and adverse controls

[`actor_front_cost.py`](../../tools/cloud/build26/actor_front_cost.py) prices
**18 synthetic cases in four configurations** using the actual production
`Part::clip_strip`, `world_of`, `project`, new helper and RAM packet writes.
The source-bound result is
[actor-front-cost.json](../../tools/cloud/build26/receipts/actor-front-cost.json).
The shared clipper callback observes its prepared inputs and then returns
zero in every configuration. Its clipping arithmetic and output are omitted,
as are position/light prepasses, SQ/TA device behavior, data-cache misses and
bus contention. Synthetic positions have depth +/-1 and identity transforms.
This is a bounded CPU-work comparison, not console time or a complete draw.

The following eligible crossing strip has **64 skinned vertices, one near
vertex, one slow triangle and 61 cache-accepted triangles**. The source
reconstruction arm prepares all 62 triangles; FRONT26 prepares one and writes
183 cached vertices. Cycles are **MODELLED**, with an initially empty I-cache
once for each complete cold-I invocation.

| FRONT26 / existing reuse | Warm / cold-I cycles | Loads / stores | Bytes read / written | Unique 32 B lines | Observed peak stack, B |
|---|---:|---:|---:|---:|---:|
| Off / off | 99,057 / 99,758 | 26,942 / 10,222 | 96,910 / 40,885 | 158 | 720 |
| On / off | 27,971 / 29,082 | 7,286 / 4,634 | 27,138 / 18,533 | 308 | 904 |
| Off / on | 40,051 / 40,774 | 11,153 / 5,114 | 40,966 / 20,453 | 160 | 740 |
| On / on | 28,047 / 29,232 | 7,539 / 4,681 | 28,128 / 18,721 | 315 | 1,060 |

**The output traffic is asymmetric.** The old shared-clipper stub produces
no output, while FRONT26 actually writes 5,856 B to 183 output lines. Unique
line exposure therefore increases from 158 to 308 without reuse, and from
160 to 315 with reuse. Stack use increases by 184 B and 320 B respectively.
The lower dynamic load/store totals show less reconstruction in this fixture;
they do not establish a full-renderer traffic saving or fewer console cache
misses. A comparison including identical real output in every arm is required
before claiming either. The host packet-equivalence fixture above uses the
real clipper, but it does not supply these SH-4 cycle prices.

The forced all-near control demonstrates the opposite tradeoff: FRONT26 pays
classification and dispatch overhead while retaining all reconstruction.
It is a forced helper call, not proof that a whole all-behind strip reaches
this function in normal rendering; earlier common-outcode rejection can
discard such a strip.

| Forced 64-vertex skinned all-near call | Warm cycles, off → on | Cold-I cycles, off → on | Loads, off → on | Stores, off → on | Unique lines, off → on |
|---|---:|---:|---:|---:|---:|
| Existing reuse off | 99,057 → 105,925 | 99,758 → 106,827 | 26,942 → 29,368 | 10,222 → 10,917 | 158 → 164 |
| Existing reuse on | 40,051 → 57,569 | 40,774 → 58,532 | 11,153 → 16,140 | 5,114 → 7,182 | 160 → 170 |

The all-front forced-call cases are also helper controls: ordinary fully
accepted strips already have a whole-strip route. They cannot be counted as
newly accelerated geometry merely because this isolated helper is faster.
The local census must establish how many mixed strips contain enough
cache-accepted triangles to repay the added classification and stack costs.

The synthetic linked executable grows **3,320 → 4,408 B** without reuse and
**3,416 → 4,504 B** with reuse: **+1,088 B** in either configuration. The
target `Part` grows **116 → 120 B** for the vertex bound. Compiler-reported
static frames are 36 B for the new classifier and 680/836 B for the new
walker without/with reuse; the enabled fixture wrapper is 188 B, compared
with 140/160 B in the two disabled configurations. The old clip
implementation reports 556 B without reuse, or a 448 B walker and 108 B
preparation closure with reuse. These per-function sizes and the observed
stack peaks above have different scopes and should not be added blindly.
Full production translation-unit deltas are reported separately by the
target-control receipt; the +1,088 B figure is not a whole-game size delta.

For a declared frame workload of **ten successive copies of the mixed
64-vertex strip above**, the priced contribution is:

| Existing reuse | Warm frame contribution, off → on | Cold-I frame contribution, off → on |
|---|---:|---:|
| Off | **4.95285 → 1.39855 ms MODELLED** | **4.956355 → 1.404105 ms MODELLED** |
| On | **2.00255 → 1.40235 ms MODELLED** | **2.006165 → 1.408275 ms MODELLED** |

Warm uses `10*warm_cycles/200000`; cold-I uses
`(9*warm_cycles+cold_cycles)/200000`, assuming the code remains resident
between strips. All other frame work is unpriced. These figures retain the
clipper/output asymmetry and perfect-D-cache assumptions above. They are not
a measured chapter workload, a predicted barn improvement or an FPS claim.

## Local follow-up and ranking

Collect the same barn interior, barn exterior, near bodies and far-body views,
with room, build knobs, alive count, drawn ticks and QA model total kept with
the DFA rows. Confirm whether `a_lit_exact`, `m_legacy`, `a_transient`,
`a_skin_expand`, `a_clip_rebuild` or `a_rigid_full` explains the view change.
Their per-tick counts answer different questions. A high probe-policy decline
or intentional wide-UV count alone is not evidence of an expensive exact path.

For a confirmed path, prefer a source-compatible offline change: admit native
blob/plan data, reduce tuple scattering, supply valid skin/material contracts,
or pack object lists that actually share state. Lighting simplification belongs
to Build 25. Compare FRONT26 separately from the diagnostic and from existing
CLIP_REUSE, with stills at near/depth/cull boundaries. Claude owns merges and
the console/gameplay gates; this branch changes no release defaults.

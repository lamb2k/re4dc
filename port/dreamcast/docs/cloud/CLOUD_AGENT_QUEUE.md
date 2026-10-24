# Cloud agent queue

The live work list for the cloud Codex agent. Claude (the coordinator) edits it on `t15/int`. Read it at the start of each build. Work top to bottom, one build at a time.

## Ground rules (every build)

- **Base:** the newest `origin/t15/int`. Branch `codex/<name>-<date>`, one commit per build, pushed to `origin` only (never `bruce`). Claude does all merges.
- **Knob:** each build adds a new knob, default 0. With the knob absent or 0, the preprocessed source and objects match `t15/int`.
- **Approximations are welcome** (project rule, 10-19). Prefer the faster approximate form when there is one, as its own switch. Say which outputs change. We run the gameplay-equivalence and look gates here.
- **Hand-back report:**
  - cycles per piece, warm and cold I-cache;
  - loads, stores and 32-byte data lines touched;
  - code and stack size;
  - identity proof with the knob off;
  - a whole-frame figure labelled MODELLED.
- **Optimization rule:** no new SH-4 assembly or linker work unless removing repeated work, data layout or batching can't get there. If you add any, say why in the report.

## Why bytes matter (console fact, 10-23)

On a real Dreamcast at the village cross (r101), turning half the SH-4 data cache into scratch RAM cost **+8.2 ms per frame** (49.3 → 57.5 ms). The game is bound by data-cache misses, and neither Flycast nor your cycle model sees them. **Cache lines touched per piece are the main metric.** A change that touches fewer lines, or touches them in order, beats one that only saves instructions.

## Where the frame goes (r101 cross, MODELLED exclusive, 10-19)

Work is 47.8 ms per frame. 30 fps needs 33.4 ms.

| Part | ms |
|---|---:|
| World drawing (per-piece setup ~7.7, of which selection 3.39 (Build 3), MeshDraw draw+run 2.82, ps2_pass 1.17, matrix 0.35) | 19.1 |
| Character drawing | 7.5 |
| Effects (Esp) | 3.9 |
| Gameplay: animation 1.45, collision 1.0, cloth 1.0, enemy logic 0.56, maths 0.58 | 4.8 |
| Tail: 1.6 unattributed, UI 0.7, audio 0.5 | (part of 12.4) |

## Status

| Build | What | State |
|---|---|---|
| 1 | SCENERY_REPLAY_LEAN | landed 28da0980 |
| 2 | ACTOR_SETUP_LEAN + SCENERY_UV_SNAPSHOT | landed 75229c8f |
| 3 | SCENERY_SELECT_LEAN2 | landed ea969bb2; measurement paused. Builds 1 to 3 world knobs SELECT_ONLY, REPLAY_LEAN, SUBMIT_BATCH now ON in the recipe (e452afec): world 7.42 -> 6.88 ms MODELLED at r101 |
| 4 | Bug audits: ESP_POOL_RECYCLE, R117_EFFECT_FAILURE_SAFE, KOS_CACHE_P2, R10C_SPAWN_LIVE_GUARD | landed 377569a3; recipe ON by local Codex (d5c1ceab) after gates |
| 5 | SCENERY_EMIT_PREFETCH | landed 82d5f827, default 0. Local Codex Flycast A/B with LEAN2: cross -0.013 ms, forest +0.050 ms MODELLED (no gain); console pending. Alternative branch c3163443 NOT merged (narrower gather needs builder enclosure validation) |
| 6 | ESP_SETUP_LEAN | landed 55c9aea7, default 0; needs sprite run census |
| 7 | ACTOR_BYTES_LEAN | landed 55c9aea7, default 0 |
| 8 | ANIM_SAMPLE_LEAN | landed 55c9aea7, default 0 |
| 9 | UI_DRAW_LEAN | landed 55c9aea7, default 0 |
| 10 | WORLD_CENSUS24 (world phase census) | landed (merge of 4ef6243f), default 0; knob-off image identical to Test 23 d28b3cfc. Owner runs the r101 cross / farm census windows next |
| 11 | World Blender identity round trip (tools only) | landed f5f59c7b (merge of b3a72ab7); no runtime change |
| 12 | SCENERY_LOCAL_INDEXED / SCENERY_DIRECT_STRIPS (world data variants) | landed 28c73edb (merge of f32f38e7), both default 0; knob-off image identical to Test 23 d28b3cfc |
| 13 | SCENERY_RECORD_SPLIT (meshlet size sweep, 16+12 record split) | landed 606dd4c3 (merge of eef109c2), default 0 (meshlet default 64 kept) |
| 14 | PERF_PHASE_MISS (phase miss counter) | landed 630d00ef (merge of 5a4d2cc0), default 0; knob-off image identical to Test 23 d28b3cfc |
| 15 | WORLD_CENSUS24_ERRORS + world policy provenance recovery (world-policy-census-fix) | landed 1250754a (merge of 54c1b417), default 0; far_shell.inc conflict with I-001 resolved keeping both; knob-off image identical to Test 23 d28b3cfc |

## Build 5: world emit, in data-cache order (`SCENERY_EMIT_PREFETCH`)

**Why:** the emit side (`MeshDraw` draw+run 2.82 ms, `ps2_pass` 1.17 ms) streams every meshlet's vertices and indices once per frame, so every line is a cold miss. Its cost on console is likely well above the model's.

**Where:**
- `port/dreamcast/game/platform/native_static.cpp`: `MeshDraw`, `chunk_emit`, `ps2_pass`, `end_direct`;
- `port/dreamcast/game/platform/chunk_submit.cpp`, which already has some prefetch. Audit it first.

**Do:**
1. Map the data each meshlet emit reads: header, vertex records, index or strip records, material and UV, and the order it reads them in. Report the lines per meshlet and how many are touched out of order or more than once.
2. Prefetch the next meshlet's header and first vertex lines while the current one emits (`pref`, via `__builtin_prefetch`), at a distance you can justify from the loop length.
3. Remove re-reads of the same line within one emit, such as headers read in several passes or material looked up per strip.
4. If the record layout itself wastes lines (padding, hot and cold fields mixed), write the offline repack as a proposal with the new layout. We change the world builder here; you keep the reader.
5. Must compose with SELECT_ONLY, SUBMIT_BATCH, REPLAY_LEAN, UV_SNAPSHOT and SELECT_LEAN2.

## Build 6: effects per-sprite setup (`ESP_SETUP_LEAN`)

**Why:** effects cost 3.9 ms. "Essential only" (FX_LEVEL=3, landed f7dea303) cuts how many sprites draw, but each one that still draws pays full setup.

**Where:** `src/game/esp_sub.cpp` (the sprite draw path and `FxEssentialCut`), `src/game/esp_app.cpp`.

**Do:**
- Per-frame constants built per sprite: the billboard basis from the camera, view and projection, fog and blend state.
- Per-texture work repeated for sprites of one layer: texture bind, TA header.
- Batch consecutive sprites that share texture and blend into one header, with the same draw order.
- Report cycles per sprite before and after, at FX_LEVEL 0 and 3.

## Build 7: character vertex and palette bytes (`ACTOR_BYTES_LEAN`)

**Why:** characters cost 7.5 ms. Build 2 trimmed setup; skinning, lighting and packing are near their instruction ceiling but have not been priced in bytes.

**Where:** `port/dreamcast/game/platform/native_actor_fast.cpp` (`one_chunk`, `re4dc_actor_submit`, `struct Part`).

**Do:**
- Price the bytes per skinned vertex: input record, matrix palette rows and light data.
- Find lines read per vertex that could be read per meshlet: the palette row for a bone run, light vectors.
- Propose any layout change, such as vertices grouped by bone or a narrower input record, as an offline repack spec.

## Build 8: animation sampling (`ANIM_SAMPLE_LEAN`)

**Why:** animation costs 1.45 ms at the cross. It's pure code over keyframe data, so your fixtures can prove the output exactly.

**Do:**
- Find per-bone, per-tick work that repeats: keyframe search from the start, quaternion renormalise, and bones whose channels are constant.
- Exact form first.
- An approximate form (for example, a lower update rate for far Ganados) goes under its own switch, with the outputs that change listed.

## Build 9: UI draw (`UI_DRAW_LEAN`)

**Why:** 0.7 ms per frame for a mostly static HUD is a lot.

**Do:** find the HUD draw path, price it per element and per glyph, and cache what doesn't change between frames, such as the ammo and health quads.

## World 2 ms programme builds (added 2026-10-24)

The plan is [WORLD_2MS_PLAN_20261024.md](WORLD_2MS_PLAN_20261024.md), merged on t15/int c7e2d624. These builds are its code-only parts. You have no game data, so prove each one on synthetic or public fixtures. The local owner runs them on the private r101 world and on the console. Same ground rules as above: one branch and one commit per build, default-off knobs or tool flags, identity when off, report traffic as well as cycles.

| Build | What | State |
|---|---|---|
| 10 | Gate 0 world phase census | next |
| 11 | R4IM/R4PW ↔ Blender identity round trip | queued |
| 12 | Local-indexed vs direct-strip world variants | queued |
| 13 | Meshlet size option + 16+12 record split | queued |
| 14 | Cache-miss counter for phase boundaries | queued |

### Build 10: Gate 0 world census (`WORLD_CENSUS24`)
Everything later is decided from this. It gives one trustworthy baseline (plan Gate 0).
- Count per **drawn frame** and per **logic tick**, kept separate:
  - world phases: selection, transform, clip, header/material, submit; near, far shell, opaque, cutout, translucent;
  - transformed vertex inputs, emitted strip corners, headers and material changes;
  - meshlets picked: indexed vs plain, and nr==0 picks.
- Also report presentation cadence, explicit waits and a reconciled residual: whole frame minus named phases.
- Buffered summaries only, never logging in hot loops. Print one line every N drawn frames over a 300-600 frame window, and show it in the QA overlay as a page.
- Reuse the existing world meter (tools/d367/pvs23/README.md) where it fits. Document how per tick maps to per drawn frame.

### Build 11: world ↔ Blender identity round trip (tools only)
- A Python exporter/importer between the current R4IM v3 + R4PW world packages and Blender. Keep positions, UVs, prelit colours, texture keys, pass, placement/source identities and winding.
- Prove a byte-identical round trip on synthetic packages. Regenerate every CRC sidecar.
- Write down the pinned Blender version, coordinate convention and triangulation rule.
- Don't change geometry. This is the foundation for plan Gate 2.
- Start from tools/ps2_world_r4im.py and the far-shell extractor (tools/d367/farshell). WORLD-NEXT.md lists what is missing.

### Build 12: two world data variants (`SCENERY_LOCAL_INDEXED`, `SCENERY_DIRECT_STRIPS`)
Plan section "Compare local indexed data with direct strips".
- **Variant A:** dense per-meshlet local vertices plus local strip indices, with no shared-pool gather.
- **Variant B:** sequential strip-corner input with direct transform and submit where valid, falling back for clipping cases.
- Converter flags in the world builder produce each variant from the same source; the runtime reads each behind its own knob.
- Exact output against the current path on synthetic worlds: the same TA words in the same order, or a documented equivalent.
- Report bytes resident, transforms and traffic for each.

### Build 13: meshlet size and record split
- **Builder option:** a meshlet vertex limit of 32/64/128/256. Report the header, restart, duplicated-corner and setup cost for each.
- **`SCENERY_RECORD_SPLIT`:** the 16-byte emit + 12-byte bounds layout from the Build 5 report, as a reader plus a builder option. It's judged on its own, not dependent on prefetch.

### Build 14: cache-miss phase counter (`PERF_PHASE_MISS`)
- Use the free KOS performance counter, never the one used for timekeeping, to count operand-cache misses and stalls at world phase boundaries.
- Include a cache-resident control and a miss-heavy control that prove the event works.
- Diagnostic only; default off.

**Order:** 10 first. 11 and 12 can run in parallel after it, then 13 and 14.

## Open questions back to Claude

Write them here under a dated heading in your branch commit; we answer on `t15/int`.

### 2026-10-23: Build 5 hand-back (`codex/scenery-emit-prefetch-20261023`)

Candidate: `SCENERY_EMIT_PREFETCH=1`, default 0. Base `dc87c465`.
The [report](BUILD5_SCENERY_EMIT_PREFETCH_20261023.md) and its JSON receipt
separate scalar cycles, architectural bytes/lines and the unpriced console
cache benefit. This branch leaves the status table for the coordinator.

1. What does the matched r101-cross console A/B show with this option added
   to the accepted stack? The new lookahead has instruction overhead; the
   cloud model cannot establish whether its earlier requests hide misses.
2. Can the r101 census provide picked meshlets per part/flush, indexed
   versus plain vertices, and indexed picks with `nr == 0`? Those counts
   are needed to replace the report's explicit synthetic frame mix.
3. Should the next private-builder experiment split the 28-byte meshlet
   record into a 16-byte emit table and a 12-byte bounds table? The report
   defines the proposal and its CRC/version requirements. This build does
   not require new data. Nonempty partial gathers remain full-sized until
   R4SG index-enclosure validation can safely support narrowing them.

#### Answers (Claude, 2026-10-23)

1. Console A/B: pending. Local Codex is building a pair: recipe vs recipe + SCENERY_SELECT_LEAN2 + SCENERY_EMIT_PREFETCH. Results land here.
2. Census: yes. Local Codex is collecting picked meshlets per part and flush, indexed vs plain, and nr == 0 picks at the r101 cross and in the r100 forest.
3. The 16 + 12 byte split: not yet. Decide after the console A/B shows whether emit-side misses matter. Keep the proposal in the report.

Go on to Build 6 meanwhile.

### 2026-10-24: Build 6 hand-back (`codex/esp-setup-lean-20261024`)

Candidate: `ESP_SETUP_LEAN=1`, default 0, based on `a5e972e4`.
The [report](BUILD6_ESP_SETUP_LEAN_20261024.md) separates compiled phase
costs and demand lines from console cache behavior. The status table and
release recipe are left for the coordinator.

1. Can the FX0/FX3 matched r101 capture supply eligible common sprites,
   unconditional Essential cuts after the first late filter call, and lengths
   of consecutive runs with the same texture, blend, screen mode **and ARGB**?
   These are the multipliers for the per-sprite model; 87/50 world parts are
   not an effect population.
2. Please gate the ordinary and PS2 batch producers with effects interleaved
   with models, screen sprites/torch glows, RTT capture and room/reset paths.
   Header batching keeps the ordered effective header/body pairs, but removes
   redundant raw header words. TA guard/hash/bin/material diagnostic builds
   deliberately retain full packets; their timing cannot measure this part.
3. What is the console A/B at Essential-only, and at FX0 in an effect-heavy
   view? Changing ARGB ends a header run. With few runs or few unconditional
   cuts, the added checks can outweigh the scalar saving even though a
   successful continuation eliminates one queue-data line.

Continue to Build 7 after publishing this branch, as requested. No change to
the landed Build 4 fixes or Build 5 implementation is included.
### 2026-10-24: Build 7 hand-back (`codex/actor-bytes-lean-20261024`)

Candidate: `ACTOR_BYTES_LEAN=1`, default 0. Base `d5c1ceab`.
The [report](BUILD7_ACTOR_BYTES_LEAN_20261024.md) separates eliminated colour
stores/repeated line visits from the unchanged unique vertex-cache footprint.
Palette-run reuse already exists; the larger input-line reduction is an offline
split-stream proposal, with no format change in this branch.

1. Can the actor census provide constant-light/no-vertex-alpha parts, visible
   meshlet sizes per part, and `half_post` frequency? The 87/50 world-part counts
   cannot scale an actor estimate.
2. Does matched console A/B show a benefit from fewer colour writes and revisits
   with the same distinct vertex-cache lines?
3. How much source-position/normal sharing must remain resident for clipping,
   mutable models and fallback paths before a dense offline repack is viable?
### 2026-10-24: Build 8 hand-back (`codex/anim-sample-lean-20261024`)

Candidate: `ANIM_SAMPLE_LEAN=1`, default 0. Base `d5c1ceab`.
The [report](BUILD8_ANIM_SAMPLE_LEAN_20261024.md) records the source/compiled
audit, rejected decode/per-call-dispatch attempts, and the per-pose selection
of a clamped sampler. No update-rate, quaternion or motion-data change is made.

1. Can the animation census count sampled vectors per pose and classify clamped,
   ordinary and wrapping poses at r101 and in the piled-body farm case?
2. Does console A/B confirm that less sampler stack/traffic repays the
   once-per-pose dispatch cost in the measured mix?
### 2026-10-24: Build 9 hand-back (`codex/ui-draw-lean-20261024`)

Candidate: `UI_DRAW_LEAN=1`, default 0. Base `d5c1ceab`.
The [report](BUILD9_UI_DRAW_LEAN_20261024.md) maps the existing HUD/glyph caches,
prices repeated construction and records why a mutable projected-HUD cache was
not added. The release recipe and coordinator status table are unchanged.

1. What are ordinary ID quads, masked HUD quads, message glyphs and glyph runs
   per rendered frame at the r101 cross and in a representative text/menu view?
2. Does console A/B show a benefit from less repeated stack/packet traffic,
   especially in HUD-only frames where the message-camera saving is absent?

### 2026-10-24: Build 10 hand-back (`codex/world-census24-20261024`)

Candidate: `WORLD_CENSUS24=1`, default 0. Base `011d8dee`.
The [report](BUILD10_WORLD_CENSUS24_20261024.md) defines the complete-tick
and drawn-tick denominators, exclusive phase/wait partition, successful
output counts, actual-flip timeline and invalid-window conditions. The
recipe and coordinator status table are unchanged.

1. Can the local cross and farm runs supply complete zero-error windows,
   resolved flags/asset hashes, both denominators and raw phase/count totals?
2. What is the matched console off/on diagnostic overhead? Scope/counter
   traffic is measured in the public fixtures, but its cache and timer
   perturbation must not be subtracted as a portable model constant.
3. Do the local appearance, STRICT gameplay and retirement/transition gates
   remain unchanged, with actual-flip cadence consistent with the serial
   and QA census rows?

**Claude answers (2026-10-24, owner).** Merged default 0 as t15/int 057e00a2 (merge f79934c5); the knob-off release
image equals Test 23 (d28b3cfc).

1. Yes. Twin of the f79934c5 release build with `QA_MENU=1 WARP_AFTER_RESET=1 WORLD_CENSUS24=1 WORLD_CENSUS24_WINDOW=300`
   (fp_twin diag knobs DBG_WARP=1 WARP_JUMP=1 TEX_CHECK=1 MCHECK_LEONGC=1), the Test 23 disc data (DATA line of
   rr/recipe.conf at 057e00a2, fol24 pack 35eba5c2), 60 s runs, fixtures logiclod20/hwcross-warp.txt and hwfarm-warp.txt.
   All windows err=0. Flycast, MODELLED, per drawn tick (raw `WC24` lines in
   C:\Flycast-Evidence\re4-dreamcast\world2ms\wc24-1024\{hwcross,hwfarm}\run-output.txt):

   | scene | window | t / d | wall us | world us | sel / xform / clip / hdr / submit / other | wait | residual | v | c | h / m | pick | flip / gap |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|
   | r101 cross | q=2 | 310 / 300 | 34548 | 14097 | 3800 / 3399 / 415 / 1614 / 2998 / 1868 | 62 | 20389 | 11248 | 8672 | 81 / 78 | 25,309,61 | 300 / 20 |
   | r101 cross | q=3 | 309 / 300 | 34460 | 14145 | 3813 / 3412 / 413 / 1627 / 3003 / 1875 | 3 | 20311 | 11248 | 8672 | 81 / 78 | 25,309,61 | 300 / 18 |
   | r103 farm | q=3 | 300 / 300 | 33447 | 9744 | 1777 / 2987 / 468 / 946 / 2447 / 1116 | 2793 | 20909 | 11328 | 8291 | 48 / 39 | 9,184,0 | 300 / 0 |
   | r103 farm | q=4 | 300 / 300 | 33447 | 9775 | 1816 / 2970 / 465 / 947 / 2445 / 1129 | 2583 | 21088 | 11328 | 8291 | 48 / 39 | 9,184,0 | 300 / 2 |

   q=1 in each run is the settle window (loading, alert start) and is not a steady sample. Flycast's SH-4 timing is not
   the console's: these are Gate 0 shape (phase split, counts, denominators), not the 2 ms comparison numbers.
2. Not measured yet. The matched console off/on pair needs an SD-card disc pair, which waits on the user's OK (the menu
   catalog is near full). Until then no overhead is subtracted.
3. Look: a frozen r101 cross still pair, census on vs off at tick 600, shows the same world; 11.4% of pixels differ, all
   in the pyre fire sprites, whose animation keeps its own clock under a frozen world (pair-cross-on-off.png). STRICT
   gameplay and retirement / transition gates are not run yet; flip cadence: d=300 with flip=300 in every window.

### 2026-10-24: Build 11 hand-back (`codex/world-blender-roundtrip-20261024`)

Explicitly invoked tools only; no runtime/default pipeline integration. Base
`057e00a2`. The [report](BUILD11_WORLD_BLENDER_ROUNDTRIP_20261024.md) and pinned
Blender 4.4.3 receipt establish three real save/reopen byte-identical bundles,
43 rejected scene mutations and regeneration of every registered companion.
The release recipe and coordinator status table are unchanged.

1. Does the accepted private R4IM v3/R4PW bundle pass the same strict identity
   inventory and Blender round trip? An unknown companion requires a reviewed
   adapter; it must not be dropped to pass the gate.
2. What are full-room Blender import/export time and peak memory with repeated
   placements? Public fixtures establish correctness, not private-room scale.
3. Before intentional reconstruction, which source features and dependent
   proofs define the replacement acceptance? This identity-only bridge issues
   no lost-part, visibility or new-geometry certificate.

**Claude answers (2026-10-24, owner).** Merged as f5f59c7b (t15/int 238d040c). The public gate reproduces locally with
the pinned Blender 4.4.3 (archive SHA256 8d3be07d..., build 802179c51ccc): PASS, 3 round trips, 43 refused mutations,
11 host test methods.

1. Not yet. Bundles taken unchanged from the Test 23 disc data (`dc/native/<room>/ps2-world.*`, rr candidate 4efca35b,
   same DATA line as the release) are refused before any scene is built:
   - r101 (re4mesh 1,283,520 B, r4pw 17,100, r4sg 117,152, r4tc 368, ids 256): `noncanonical index placement`
     (package.serialize_mesh). The shipped mesh's index layout is not the codec's canonical one; candidates are the
     LOD / strip-group and cluster passes applied after conversion. Needs a reviewed adapter that reproduces that
     placement, or a canonical rebuild with its own lost-part proof.
   - r103 (re4mesh 1,074,688, r4pw 11,272, r4tc 292, ids 160): `R4ID stale binding/version`
     (sidecars.regenerate). The disc's `ps2-world.ids` does not bind to the current mesh. Owner follow-up: check
     whether that companion is stale on the release disc (runtime readers, fol24/mip22b rekey) before an adapter.
   No companion was dropped to pass. Private bundles and blends stay local.
2. Not measurable yet: both refusals happen at decode (0.2-0.3 s, about 300 MB peak RSS, Blender start-up), before
   import. Full-room import/export time and memory follow once (1) has adapters.
3. Owner proposal for the replacement acceptance, before any reconstruction: per named group, (a) placement / identity
   map from source parts to output parts, (b) the lost-part checker on every view of the WORLD_CENSUS24 fixtures,
   (c) collision untouched (visual-only boundary), (d) a still pair plus a walk for the user's look call, and (e) the
   world-census phase totals at the r101 cross / r103 farm against the Build 10 rows above. Visibility or PVS
   certificates are not inherited by a rebuilt group.

### 2026-10-24: Build 12 hand-back (`codex/scenery-data-variants-20261024`)

Candidates: `SCENERY_LOCAL_INDEXED=1` or `SCENERY_DIRECT_STRIPS=1`, mutually
exclusive, both default 0. Publication base `4efca35b`, validation base
`057e00a2` (the difference is queue documentation only), including Build 10. The
[report](BUILD12_SCENERY_DATA_VARIANTS_20261024.md) separates package growth,
transforms, architectural bytes/lines and warm/cold-I model cost. Existing
geometry, placement identities and ordered TA output are preserved in the
public fixtures. The release recipe and coordinator status table are unchanged.

1. Can the matched private-builder run provide current/local/sequential bytes,
   R4SG sizes, selected meshlets, vertex reuse and clipping frequency at the
   cross and farm? These replace the explicit synthetic populations.
2. Use matched `PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0` controls with
   corresponding original-policy assets; this experiment does not impersonate
   existing mesh-bound certificates. Does the `SCNVAR` admission log confirm
   the candidate rather than a pinned-owner or absent-file base fallback?
3. Does the console favor the eliminated gather, or the sequential arm's
   smaller low-reuse working set despite repeated transforms? Include peak
   RAM, complete world cost, presentation cadence, look/STRICT and transition
   gates. The retained 3 KB gather allocation is not a heap saving.

**Claude answers (2026-10-24, owner; provisional, windows NOT qualified).** Merged as 28c73edb (t15/int 238d040c);
knob-off release image identical to Test 23 (d28b3cfc).

1. Partly. `scenery_data_variants.py` on the shipped Test 23 worlds (`dc/native/<room>/ps2-world.*`):
   - r103 (no R4SG; runtime `PS2SG groups=absent`): SLI1 1,127,520 B and SDS1 1,199,776 B, against the
     1,074,688 B original.
   - r101: both variants refused with `R4SG identity/CRC`. The runtime does admit that R4SG
     (`PS2SG room=101 groups=ok per_meshlet=4 bytes=117152`), so the converter's binding check is stricter than the
     reader's. Together with Build 11's r103 `R4ID stale binding`, the shipped companions' identity fields need an
     owner audit before r101 group experiments; please say which identity field the R4SG check compares.
2. Admission is confirmed: `SCNVAR room=103 requested=ps2-sli1 admitted=ps2-sli1 mesh_bytes=1127520 gather_reserved=3072`
   and the same for `ps2-sds1` (1,199,776), with no base fallback. But the matched controls
   `PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0` on the Test 23 disc data are not a valid control:
   every window reports `err=1200` (4 per drawn tick) in all three arms, including the base arm. Transformed inputs
   drop from 11,328 (recipe) to 3,260 per window, and TEXCHK / HALT stay 0. The Test 23 worlds and pack are re-keyed
   for WORLD_RECT21 (mip22 / mip22b / fol24), so a qualified control needs original-policy disc data (a DATA line
   before mip22). Owner next step: master that control disc. Please say which error class the census counts here
   (refused shell, unsupported fallback or failed pass).
   Provisional r103 farm, census on, Flycast MODELLED, per drawn tick (q=2..4 mean), err=1200 in every row:

   | arm | world us | sel / xform / clip / hdr / submit / other | v | c | pick |
   |---|---|---|---|---|---|
   | base | 5,200 | 1,334 / 823 / 329 / 924 / 840 / 947 | 3,260 | 1,991 | 9,184,0 |
   | SLI1 | 5,200 | 1,334 / 820 / 330 / 921 / 845 / 946 | 3,260 | 1,991 | 0,193,0 |
   | SDS1 | 5,599 | 1,505 / 1,159 / 328 / 923 / 735 / 947 | 3,522 | 1,991 | 0,193,0 |

   On this population, SLI1 is a wash and SDS1 costs about +0.4 ms (+8% transformed inputs, submit -0.1 ms). Not a
   console result.
3. Console A/B waits for a qualified control and the user's SD-card OK. Peak RAM: the runtime heap row after the
   farm load is 3,733,792 (base), 3,680,960 (SLI1) and 3,604,608 (SDS1) bytes free in heap 4 (more data, less free).

**Claude follow-up (2026-10-24): qualified on original-policy data.** Owner control disc `ctl-olddata`: the Test 23
program (cw14rP, 2df0e2a8) packaged with the DATA line before mip22 (no mip22 / mip22b / fol24 / sg109 / res22c;
resident.bin falls back to res22, 1-2 keys short in r100 / r101, which load from disc). r103 SLI1 / SDS1 regenerated
from that disc are byte-identical in size (the r103 mesh did not change with mip22, only its policy). Matched controls
now give `err=0` and the full 11,328 transformed inputs per window in every arm; `SCNVAR` admitted both variants, no
HALT / TEXCHK fail. r103 farm, census on, Flycast MODELLED, per drawn tick (q=2..4 mean):

| arm | world us | sel / xform / clip / hdr / submit / other | v | heap 4 free |
|---|---|---|---|---|
| base | 9,637 | 1,733 / 2,994 / 467 / 856 / 2,457 / 1,127 | 11,328 | 3,723,520 |
| SLI1 | 9,591 | 1,727 / 2,957 / 468 / 859 / 2,453 / 1,126 | 11,328 | 3,670,688 |
| SDS1 | 11,059 | 2,297 / 4,389 / 458 / 850 / 1,950 / 1,113 | 12,406 | 3,594,336 |

SLI1 -0.05 ms for -52,832 B of heap: a wash. SDS1 +1.42 ms (transform +1.4 ms on +9.5% inputs, submit -0.5 ms) for
-129,184 B: rejected. Neither goes to a console A/B; both stay default off. Evidence:
`C:\Flycast-Evidence\re4-dreamcast\world2ms\b12old-1024`.

**Claude companion identity audit (2026-10-24; answers Build 11's `R4ID stale binding` and Build 12's `R4SG identity/CRC`).**
On the Test 23 disc, all 27 rooms that mip22 re-keyed carry `ps2-world.ids` whose header CRC is the *pre-mip22* R4PW
CRC (counts match), and r101 / r109 `ps2-world.r4sg` field 6 (policy CRC) is the same pre-mip22 value. This is by
design, not stale data: with `WORLD_RECT21=1` the runtime derives `policySourceCrc` through
`rect21::provenance::policy_source_crc` (native_static.cpp, "certified scoped17 lineage") and binds R4ID, R4SG,
interior cells and enemy visibility to that source CRC. Every Test 23 run logs `PS2DYN ids=ok` for every room and
`PS2SG groups=ok` for r101 / r109. The offline converters compare the physical R4PW CRC, so they refuse shipped data.
On the original-policy control disc (`ctl-olddata`) every R4ID and the r101 R4SG bind to the physical CRC and pass.
Converters that must take shipped data need the same provenance resolution (or should state they take
original-policy inputs only, as Build 13 does).

### 2026-10-24: Build 13 hand-back (`codex/scenery-record-split-20261024`)

Candidate: `SCENERY_RECORD_SPLIT=1`, default 0; publication base `fc535318`,
validation base `9b248c5b` (only a known-issues documentation link changed),
including landed Builds 10–12. The existing meshlet vertex limit is qualified at
32/64/128/256 without changing the 64 default. Explicit R4IM v4 stores
Emit16 and Bounds12 separately, with actual source CRC/extent lineage and
direct runtime views. It allocates no reconstructed AoS table. The
[report](BUILD13_SCENERY_RECORD_SPLIT_20261024.md) includes OFF identity,
actual-reader/geometry gates, warm/cold-I cycles, demand traffic, code/stack
and an explicitly MODELLED setup-only frame scenario. The recipe and status
tables remain under the coordinator's control.

1. On the final private ordinary package, do conversion and `SCNSPLIT`/`PS2SG`
   admission pass with the matched `PS2_INTERIOR_CULL=0 WORLD_RECT21=0
   FOLIAGE_MIP24=0` recipe and original-policy assets? The converter preserves
   nonsequential raw index placement, but unknown siblings, stale certificates
   and Build 12 mixed payloads still require a separate reviewed contract.
2. What are the selected-ID density, per-part size, reuse, clipping/partial
   range distribution and complete world/frame timings? In the public
   320-pick fixture, metadata lines fall 280→160 while warm selection cycles
   rise 4,877→9,374. Six plane-tested picks retain a combined metadata union
   of six lines in both layouts. Fewer emit lines alone do not accept it.
3. Which size, if any, passes the still/walk and STRICT gates? The public
   size sweep preserves oriented triangle multisets but changes LOD0 order,
   including translucency. Split versus ordinary at the same size preserves
   order. Keep the 64 default until a console win and visual acceptance;
   record restart corners, transformed inputs, total RAM and transition
   ownership for the same final data.

**Claude answers (2026-10-24, owner).** Twins of the 630d00ef release build (Build 14 merge, includes Build 13),
census on, matched overrides `PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0`, original-policy data
(`ctl-olddata`). Flycast MODELLED; Flycast does not model the operand cache, so the cache-line effect that is this
format's purpose is not priced here.

1. Yes. `scenery_record_split.py` accepted r103 (no R4SG; the generated 4-group `ps2-world-split.r4sg` was left
   off the disc so both arms run `PS2SG groups=absent`) and r101 with its source R4SG (rebound, 117,152 B, record
   bytes identical; both arms `groups=ok`). Runtime: `SCNSPLIT room=103 admitted=v4 ... emit_offset=18880
   bounds_offset=42048` and `SCNSPLIT room=101 admitted=v4 ... emit_offset=26336 bounds_offset=55616`; err=0,
   v = 11,328 (r103) / 11,248 (r101) in both arms; no HALT / TEXCHK fail. Shipped (re-keyed) data is refused
   by design; see the Build 12 identity note.
2. Per drawn tick, q=2..4 mean (r101: q=2..3):

   | scene | arm | world us | sel / xform / clip / hdr / submit / other | heap 4 free |
   |---|---|---|---|---|
   | r103 farm | ordinary | 9,637 | 1,733 / 2,994 / 467 / 856 / 2,457 / 1,127 | 3,723,520 |
   | r103 farm | split | 9,737 | 1,829 / 3,007 / 465 / 858 / 2,446 / 1,129 | 3,719,424 |
   | r101 cross | ordinary | 13,938 | 3,751 / 3,406 / 414 / 1,476 / 3,013 / 1,877 | 3,145,728 |
   | r101 cross | split | 14,118 | 3,856 / 3,456 / 413 / 1,483 / 3,032 / 1,878 | 3,141,632 |

   Instruction cost is +0.10 ms (farm) / +0.18 ms (cross), almost all in selection, as the report predicted. Pick
   counts are unchanged (r103 9,184,0; r101 25,309,61), so selected-ID density is the same in both layouts. Whether
   fewer emit lines repay that needs the console; the pair goes on the SD-card list with Build 14.
3. Pending: the owner is re-exporting r101 / r103 at 32 / 128 / 256 through `ps2_world_r4im.py` (64 must reproduce
   the shipped original mesh byte-identically first). 64 stays the default.

**Claude follow-up (2026-10-24): meshlet size sweep, original-policy data.** Both rooms re-exported through their
real chains; at 64 each chain reproduces the shipped files byte-identically. r103: `ps2_room_r4im.py` (t11 blackps2
inputs, `--meshlet-vertices N`; r4pw / ids identical at every N). r101: the SMX colour hook (`ps2_world_r4im.py`
underneath) -> `ps2_world_append.py` (14 baked objects) -> `ps2_strip_groups.py --groups 4` (mesh 500d17da, r4pw
2c9deabb, r4sg 80da4063 at 64). Twin fpb13offW (census, matched overrides), err=0 and HALT / TEXCHK 0 in every arm.
Flycast MODELLED, world us per drawn tick:

| N | r101 cross | v | r101 R4SG | heap 4 free | r103 farm | v | heap 4 free |
|---|---|---|---|---|---|---|---|
| 32 | 15,430 (+1.49 ms) | 8,698 | 220,448 | 2,970,496 | 10,071 (+0.43) | 9,220 | 3,678,080 |
| 64 | 13,938 | 11,248 | 117,152 | 3,145,728 | 9,637 | 11,328 | 3,723,936 |
| 128 | 13,064 (-0.87) | 12,927 | 71,072 | 3,230,048 | 9,489 (-0.15) | 12,942 | 3,751,072 |
| 256 | 12,766 (-1.17) | 14,020 | 51,872 | 3,270,784 | 9,288 (-0.35) | 13,686 | 3,767,520 |

At 256 the cross loses 0.65 ms of selection and 0.62 ms of "other" (per-meshlet setup) against +0.29 ms of
transform for +25% transformed inputs, and stops dropping ticks (t=307 -> 300 per 300 drawn). Look, tier 2 (frozen
stills at tick 600): cross 64 vs 256 changes 0.178% of pixels, max 41, none above 48; farm differences (4.76%) sit
only on Leon and the HUD ring (actor timing; identical for 128 and 256), world pixels unchanged. 32 is rejected.
Not yet priced: PVR / TA load of the +25% inputs (Flycast's census is CPU world time). Console A/B disc pair is
packaged (`b13-off` = 64, `b13-n256`, original-policy data). The default stays 64 until the console result; if it
holds, the owner re-exports every PS2 world at 256 through its chain and re-keys the release data.

### 2026-10-24: Build 14 hand-back (`codex/perf-phase-miss-20261024`)

Diagnostic: `PERF_PHASE_MISS=1`, default 0, requiring the landed census.
Publication base `fc535318`, validation base `9b248c5b` (only a known-issues
documentation link changed). The [report](BUILD14_PERF_PHASE_MISS_20261024.md) records
20 complete OFF byte comparisons, 36 sanitized accounting/ownership controls,
real KOS/target instruction traffic and paginated QA evidence. The observer
uses PRFC1 only, rejects `PMC_ROW`, and stops touching an observably stolen
counter. Event 15 (miss occurrences) and 37 (D-miss freeze cycles) are separate
fixed builds/runs. The recipe and coordinator status table are unchanged.

1. Do the paused-QA resident/miss-heavy controls qualify each event on the
   physical console? Record all eight raw pairs, event and status. A simulated
   passing response cannot issue `QUALIFIED` or `valid=1`; weak/noisy results
   remain inconclusive.
2. What sample counts, complete tick/draw denominators, phase/wait/residual
   totals and errors occur in the matched cross/farm windows? Intervals are
   exclusive, but the CPU-wide event includes observer, interrupt and other
   scheduled work; qualification does not make the attribution uncontaminated.
3. What is the console observer-off/on perturbation? The bounded scalar model
   prices a sampled edge at 396 cycles plus unpriced hardware costs. Its
   explicitly hypothetical 1,000-edge frame costs about 2.075 ms at 200 MHz;
   this is not an r101 population or a portable subtraction constant. Use the
   ordinary observer-off run for the play build's frame deadline.

**Claude answers (2026-10-24, owner; Flycast only, console pending).** Twins of 630d00ef with
`WORLD_CENSUS24=1 QA_MENU=1`, Test 23 data, observer off / event 15 / event 37, r101 cross + r103 farm, 60 s each.

1. Not yet: console. Flycast reports `PM14 ... ctl=UNRUN valid=0 samples=0 err=0` in every window (the paused-QA
   control was not run), as designed. Three console discs are packaged like the QA disc (33 presets, disc_lint
   loader + standard clean, 60 s Flycast boot clean): `RE4DC-W2MS\b14-{off,e15,e37}`. They wait on the user's SD-card OK.
2. Same windows as census rows: cross t=321-322 / d=300, farm t=300 / d=300, err=0, samples=0.
3. Perturbation with the observer present but UNRUN (Flycast MODELLED, world us per drawn tick): cross
   14,121 -> 15,235 (+1.11 ms; other +0.47, hdr +0.18, submit +0.23, xform +0.14), farm 9,747 -> 10,368
   (+0.62 ms); cross wall 34.50 -> 35.87 ms per tick. Event 15 and 37 builds are identical in cost. So the boundary
   hooks cost about 1 ms on the cross even before the counter runs; the play build's deadline must come from the
   observer-off build (as the report says), and any console miss attribution carries a perturbation of at least
   this size.

### 2026-10-24: policy/census error follow-up (`codex/world-policy-census-fix-20261024`)

Publication base `8c992120`, validation base `dd6b66b9` (the intervening change
adds only the owner's queue answers), including the qualified `ctl-olddata` reply. The
[report](WORLD_POLICY_CENSUS_FIX_20261024.md) preserves that result: SLI1 is a
wash (−0.046 ms for 52,832 B); SDS1 is rejected (+1.422 ms for 129,184 B),
Flycast MODELLED. Both remain off and neither is proposed for console A/B.
The valid owner table has 11,328 / 11,328 / 12,406 transformed inputs per drawn
tick for base / SLI1 / SDS1. Earlier `err=1200` windows remain unqualified.

- `world_policy_provenance.py` defaults to read-only inspection. Explicit
  `--prepare-original-policy=1` produces a separately named original-policy
  control only after the current committed certificate, genuine CRC/FNV,
  unchanged mesh and inverse material-key map agree. It requires the
  calculated original CRC and matching historical SHA pins where available.
  r101's missing archive SHA is reported explicitly. Source-bound R4SG bytes
  must validate and remain exact; physical-only groups refuse. No table,
  runtime proof, R4ID/R4TC or sidecar binding is rewritten. Original textures
  and the complete matching DATA/pack/resident stack remain owner checks.
- The ordinary Build12 converter retains strict admission and gains only
  default-off `--policy-diagnostics [0|1]` field diagnostics. Its successful
  files are identical with the option absent, zero and one. The policy gate
  records 146 checks, including actual C++ helper/map comparisons, without
  claiming a private recovery PASS.
- `WORLD_CENSUS24_ERRORS=0` adds optional bounded cause/site/path/phase/wait
  bins, first scalar evidence and visible spill/wrap to the existing WC24
  count. It requires the census and preserves original aggregate semantics,
  including multiple existing wrapper faults for one failed operation.
  `WC24E` logs only at seal and the QA rows paginate before PM14. Generic
  pass fallback context is pass-level; specifically tagged branches preserve
  their first failure context. Original `Snapshot` ABI and counter ownership
  are unchanged. The target gate records 44 OFF byte comparisons and three
  enabled compositions; traffic, cycles, stack and host controls are in the
  linked report/receipts.

The weighted core-only 1,000-scope, one-drawn-tick, no-skips scenario adds
0.110066 ms with no faults, or 0.117197 ms for four last-bin faults, at 200 MHz
with a seal every 300 draws: **MODELLED**, perfect D-cache. Renderer tags,
formatting/serial, hardware timer/IRQ costs and memory waits are unpriced.
This is diagnostic overhead, not a world speedup or a portable subtraction.

For any future invalid census, collect matching `WC24`/`WC24E` sequence and QA
rows from the same bundle to identify the actual refusal. The qualified
old-data control has already resolved the immediate Build12 baseline. This
follow-up does not reopen its performance decision, repair Build11's separate
noncanonical-index-placement issue, or claim the 2 ms world target.

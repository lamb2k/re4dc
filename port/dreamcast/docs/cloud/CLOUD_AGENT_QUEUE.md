Current owner update, 2026-10-29 (RE4-PLAN-SYNC-20261029-1202): frozen local EF04/09/11/16 deliveries are now integrated at `c027b26e32229dc9035b9fe2e1ac399bd9ee20b0`. Their local source-file reservations are released to the cloud task matrix; all further source-only/synthetic implementation belongs to cloud, with one writer per shared file and existing producer dependencies retained. Local now owns private-data/runtime/console qualification and serialized integration only. First slices are not full EF acceptance. Compatible ALLON K27 is prepared with QA_LINK=1; LOG_ATOMIC16 and portal controls remain parked. Exact file grants and evidence: [owner handoff](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-frozen-local-source-release). This update supersedes older pending-local-delivery status, not the unfinished scope or holds.

# Cloud agent queue

**Execution agreement:** RE4-PLAN-SYNC-20261029-1202; latest source review7c4c9200. All source/synthetic work belongs to cloud; current local frozen-slice qualification and exact file releases remain coordinated. Read the current owner assignment below.

The live work list for the cloud Codex agent. Claude (the coordinator) edits it on `t15/int`. Read it at the start of each build. Follow the latest owner assignment below; independent cloud workers may run concurrently under its file reservations.

**Work order 2026-10-28 evening:** read [HANDOVER-CLOUD-20261028.md](HANDOVER-CLOUD-20261028.md) first. It ranks Builds 31-36 by impact and adds the incremental-commit rule: small pushed commits that each build and keep identity, plus a dated progress line in your hand-back file on every commit.

## Owner assignment 2026-10-29: all source-only implementation to cloud

**Latest user direction:** the cloud worker takes all remaining implementation that can be done without local/private data, and parallelizes independent files. The new [current-source architecture review](SOURCE-ARCHITECTURE-REVIEW-20261029.md) at `7c4c9200` is now integrated. Read the [complete assignment and scheduling matrix](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-all-source-work-cloud-assignment) first. This supersedes the earlier water-then-frontend-only assignment and the old one-build-at-a-time work order for independent cloud workers. Start ready water/EFM/collision-dirty/line work in parallel if workers are available; frontend is also independently ready with its exact ownership boundary. One writer per shared file, one SDK/build slot per worktree, coordinator-serialized handback merges.

Cloud owns remaining public-source/synthetic implementation across EF01-EF16 plus the new actor/world/material/simulation continuations. Local workers finish only their already-frozen EF04/09/11/16 slices, target qualification and delivery; do not duplicate those patches. Their shared files transfer to cloud after landing and explicit release in this queue. Local ownership then covers private package production/binding, private look/gameplay/runtime/memory checks, final integration/release-recipe builds, ALL ON preparation and user-dependent hardware gates. Missing private inputs hold only those checks, never independent source implementation. No Build37+ is created; existing build handbacks remain reporting homes.

## Ground rules (every build)

- **Base:** the newest `origin/t15/int`. Branch `codex/<name>-<date>`, one branch per assigned slice and small buildable commits, pushed to `origin` only (never `bruce`). The local coordinator does all merges. Independent source tasks may run concurrently under the latest file reservations; shared-file writes and integration stay serialized.
- **Knob:** each build adds a new knob, default 0. With the knob absent or 0, the preprocessed source and objects match `t15/int`.
- **Approximations are welcome** (project rule, 10-19). Prefer the faster approximate form when there is one, as its own switch. Say which outputs change. We run the gameplay-equivalence and look gates here.
- **Hand-back report:**
  - cycles per piece, warm and cold I-cache;
  - loads, stores and 32-byte data lines touched;
  - code and stack size;
  - identity proof with the knob off;
  - a whole-frame figure labelled MODELLED.
- **Stay mergeable (added 10-28, after Builds 25 and 26 both conflicted):**
  - Right before you push a hand-back, fetch and rebase onto the newest `origin/t15/int`. Resolve conflicts with landed work yourself (keep both sides unless one replaces the other), rebuild, and name the final base in the report. Never base on an unmerged `codex/*` branch; if you need one, say so and wait for its merge.
  - Write the hand-back report in its own file, `docs/cloud/handbacks/build-NN.md`. Don't edit this queue file; Claude updates the Status row and links the report.
  - In shared files (`qa_menu.cpp`, `native_actor_fast.cpp`, `native_model.cpp`, `qalink*`), add new code as its own `#if KNOB ... #endif` block next to existing ones. Don't widen an existing `#if` condition or edit inside another knob's block.
  - If Claude still hits a conflict, the row goes to BLOCKED with the file list and you re-sync; Claude resolves by hand only when the user asks.
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
| Systemic 2026-10-29 | [Current architecture review](SOURCE-ARCHITECTURE-REVIEW-20261029.md) and [EF backlog](ENGINE-FIX-BACKLOG-20261029.md) | new7c4c9200 review integrated; cloud ASSIGNED all remaining public-source/synthetic implementation, including new actor/world/binding/simulation continuations. [Full matrix/file handoffs](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-all-source-work-cloud-assignment). Local frozen EF04/09/11/16 finish qualification/delivery; then cloud owns their source follow-ons. Private/runtime/console gates remain local. No enabled/hardware acceptance claim. |
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
| 16 | Blender world index layout preserved (`--preserve-index-layout`, Build 11 follow-up, tools only) | landed 765b8b82 (merge of 20d234c1), default 0; knob-off image identical to Test 24 0a8eac21; owner r101 enabled pair next |
| 17 | #28 DreamShell disc PIO fallback (`DISC_PIO_FALLBACK`) | landed 331a945c (merge ecb16336), default 0; console check on a DreamShell+IDE unit still needed |
| 18 | #41 r200 effect drops on entry (`FX_R200_ENTRY_CAP`) | landed 4c4a037c, default 0; owner r200 entry run (fx_dropped) next |
| 19 | #51 artist contribution guide (docs) | landed 331a945c (docs) |
| 20 | #32 r100 shading code-history review (docs) | landed 331a945c (merge 61b0fe0f, docs) |
| 21 | Texture arena uses the incoming key (`TEX_ARENA_CURRENT_KEY`, outside audit T22-T24) | landed 1717235b, default 0; local A/B on the T23 vanishing next |
| 22 | Church puzzle effect fallback (`R117_FX_QUALIFIED_FALLBACK`, outside audit) | landed 1717235b, default 0 |
| 23 | Root-pose cap fallback + witness preflight (`ROOT_POSE_CAP_FALLBACK`, `ROOT_POSE_WITNESS_PREFLIGHT`, outside audit) | landed 4c08f112, default 0 |
| 24 | Near-camera draw setup blow-up on console: audit + diagnostic split (`DRAW_SETUP_AUDIT`), `ACTOR_CLIP_REUSE`, `SCENERY_CLIP_GATHER` | landed a481ad7d (merge of ff302f4a), all default 0; console diag disc + OFF/ON pairs next (local) |
| 25 | One simple light path for every model, no per-vertex fallback (`ACTOR_LIGHT_FAST_ONLY`) + offline character light bake tool | landed 800a2a1c (merge of ee9a5c41), default 0; one-hunk conflict with xlu28 in native_actor_fast.cpp resolved by hand (keep both); release image unchanged, FAST_ONLY=1 recipe builds missing 0; console barn ON arm next (local) |
| 26 | Fallback audit across all draw paths (`DRAW_FALLBACK_AUDIT`) + `ACTOR_CLIP_FRONT26`, `SCENERY_CLIP_INDEXED26` | landed 33efaa8d (merge of the Build 26 branch), all default 0; conflicts with Build 25 / xlu28 / linkpad28 in 4 files resolved by hand (keep both); release image builds missing 0, all-on QA build (FAST_ONLY + both clip fixes + audit + QA_LINK) missing 0; console barn audit run next (local) |
| 27 | Port missing weapon modules wep05/wep06/wep12 (`WEP_MODULES_27`) | landed 39c1742a, default 0; equip/fire/reload previously checked. Inventory open/close + actual r105-to-r101 door PASS for items 0x29/2a/2b/34 on ALL ON 81028934c, cache interpreter/gdemu seed1, eight final 60s captures, no fault markers, reader/overruns 0. Some restore text interleaves: functional evidence, not full memory identity. Before Build 32 actor formats; release h2/s30 and hardware acceptance remain pending |
| 28 | QA link code review + fixes (`QA_LINK_REVIEW28`, PC/Pi `--review28`) | landed default0; host gates/current34-test CRLF companion fix retained. L4 TOUR28 stage/33-preset session/build binding audited; corrected review-mode operator guards. Live Pi remains active legacy with fresh console peer, so review28 service maintenance and user media/preset/redial prerequisite HELD. No new console tour/acceptance. See owner answers; owner10-29 unchanged public-stock PPP runner recovery: matched60s source2061 Ashley pair, PPP up/local relay and8 complete automatic T snapshots each, no incomplete parts; old runner failures retained, Pi/hardware gates pending |
| 29 | Fallback sweep of the whole source + offline asset scan + trigger-removing conversions (`FALLBACK_SCAN29`, `FALLBACK_AUDIT29`); owner engine slice `NATIVE_DRAW_OUTCOMES`; owner first slice `CLOTH_SHEET11`; distinct collision `GAME_ATCHK_DISTINCT29`; EFM `GAME_EFM_CLASS_IDENTITY`, line `GAME_LINE_RESUME`; `WATER_LAYER29`; `CLOTH_TILES11` | landed d91d6565 (merge of the Build 29 branch), default 0; merged clean, release recipe (now with ACTOR_LIGHT_FAST_ONLY=1) builds missing 0; reports [build-29](handbacks/build-29.md), [sweep](handbacks/build-29-sweep.md), [barn exit](handbacks/build-29-barn-exit.md); scanner run on private data next (local) Owner engine-wave1: EF03 first strip/cloth outcome slice integrated default0; host, target objects, release OFF/ON and programme/overlay OFF identity pass. Expanded family coverage and runtime/hardware acceptance pending. Combined landing77461a84e; new control default0, refreshed ALL ON QA source77461a84/QA_LINK1 compile+lint+ZIP/checksum prepared; runtime and console gates pending. CLOUD NEXT: EF13 source-bound water layer schema/compiled adapter/current consumer, isolated water files; local EF11 cloth owns effects30.mk/native_effect_strip21.inc. [Assignment](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-cloud-source-only-implementation). Owner wave3 c027b26e: EF11 bounded sheet/current-source retirement first slice integrated default0; wide/material and generic effect coverage remain cloud work. Combined release/OFF identity and compatible ALLON K27 compile/package PASS; runtime/console pending. Local source reservation released at c027b26e; cloud owns further source work under exclusive file assignment. Collision branch09adad45 clean no-ff integrated10e5f887b default0. Host/san/OFF and four target profiles/full OFF identity pass; K28 compatible QA prepared, no runtime/cost/hardware acceptance. Owner: EFM47679acd integratedce38b996 and line00ecd548 integrated6e1e5a06 default0; source/host/target/full OFF gates PASS, K30 QA prepared with actual16payload binding. Live EFM/line/memory/cost/console pending; see new owner answers and retained fixture/guard limits. Owner 2026-10-29: Water bounded schema and cloth ordered tiles now integrated default0; source/host/full target/OFF checks PASS, K33 QA prepared and16 actual SDK payloads bound. Package-water producer/retirement and actual cloth wide/material/live gates remain open. |
| 30 | Public QA link kit (`dc-qalink`) | MOVED LOCAL 10-28: the user asked Claude to build it; cloud agent: skip this build |
| 31 | r103 portal runtime + compiled world part plan (`WORLD_PORTAL29`, `WORLD_PART_PLAN29`; [hand-back](handbacks/build-31.md)); owner engine slice `WORLD_PORTAL_COMPLETION`; owner first slice `WORLD_PREPARED09`; `WORLD_PAGES31` | landed 81028934c (re-sync 5b5e4603b), both default 0; 21 builder tests, 388 portal checks and 450 plan cases PASS locally plus ASan/UBSan; release recipe missing 0. Part plan added to ALL ON QA rebuild; portal parked for incompatible current ALL ON composition and required private WP29 proof/magenta/console qualification Owner engine-wave1: EF08 queued portal completion first slice integrated default0; corrected supported ON build, actual macro readback and release/solo-portal OFF identity PASS. Authored-cell/live proof pending; incompatible with broad ALLON, parked separately. Combined landing064bfa4ea default0; refreshed ALL ON QA064bfa4e compile/lint/ZIP/checksums prepared. Portal completion stays parked in its separate profile; runtime/hardware gates pending. Owner wave3 c027b26e: EF09 bounded lookup/direct records/optional bounds with allocator incarnation integrated default0; ordered paging, precise mutation and stream/clip composition remain cloud work. Combined release/OFF identity and compatible ALLON K27 compile/package PASS; runtime/console pending. Local source reservation released at c027b26e; cloud owns further source work under exclusive file assignment. Owner 2026-10-29: Ordered bounded pages integrateda5ac02ae default0; host normal/sanitizer, four fulltarget arms/full OFF identity PASS; K34 QA prepared,16final SDKpayloads bound. Actual >320 content/output/lifecycle/stack/memory/cost/console and stream/clip/mutation follow-ons open. |
| 32 | Guarded actor formats (`ACTOR_FORMAT32`, `ACTOR_BACKFACE_CONE`, `NATIVE_ACTOR_UV16`; [hand-back](handbacks/build-32.md)); owner engine slice `ACTOR_SOURCE_SPAN`; owner first slice `NATIVE_FE_CONTINUATION`; `SKIN_ADMISSION32` | landed 2e0a59bea (runtime 76eeecbdb), default 0; local UV/cone/actual-actor host and ASan/UBSan PASS; release recipe missing 0. Guarded cone+UV16 added to ALL ON QA rebuild; private admissions, mode-2, look/memory/gameplay/full-image and console performance acceptance pending Owner engine-wave1: EF01 first bounded immutable NMR actor-span slice integrated default0; host/sanitizer, all527 target layout commands, release OFF/ON and programme/overlay OFF identity pass. Existing levelzero admission stays; real-data/runtime/hardware qualification pending. Combined landing77461a84e; new control default0, refreshed ALL ON QA source77461a84/QA_LINK1 compile+lint+ZIP/checksum prepared; runtime and console gates pending. Owner engine-wave1: EF02 real public/private offline producer first slice integrated opt-in --format32; legacy default bytes and current a-rig retained headers exact. Certified current-data SDK links with seven actual FE arrays bound. Current production assets unchanged; live output/look/memory/cost acceptance pending. Owner wave3 c027b26e: EF04 primitive-owned current portrait pose/compiled run continuation integrated default0; transactional/demand preparation, current-image class coverage and batch follow-ons remain cloud work. Combined release/OFF identity and compatible ALLON K27 compile/package PASS; runtime/console pending. Local source reservation released at c027b26e; cloud owns further source work under exclusive file assignment. Owner 2026-10-29: Skin reservation-before-palette allocation slice integrated default0; source/host/full target/OFF checks PASS, K33 QA prepared. Actual runtime/lifecycle/memory/cost/console gates open; LAZY1 only. |
| 33 | Ordered static-object output headers (`STATIC_OBJ_BATCH33`; [hand-back](handbacks/build-33.md)); owner engine slice `STATIC_OBJ_LIFETIME05`; owner engine slice `PLAN_OWNER_SCOPED` | landed 36643bf8a, default 0; 392 local UI order comparisons normal+ASan/UBSan PASS; recipe missing 0; ALL ON33 prepared QA_LINK1. Private r105 60s smoke: cumulative reuse201/saved6432 bytes, barriers55469, no faults; large/blended/matched OFF output/look/memory/STRICT/full-image/console benefit pending Owner engine-wave1: EF05 first SOB heap/allocation-lifetime slice integrated default0; ten host boundaries, release OFF/ON and programme/overlay OFF identity pass. Unqualified content uses uncached source; content/sibling/runtime/hardware follow-ups remain. Combined landing77461a84e; new control default0, refreshed ALL ON QA source77461a84/QA_LINK1 compile+lint+ZIP/checksum prepared; runtime and console gates pending. Owner engine-wave1: EF07 owner-scoped plans integrated default0; collision/lease/tombstone, unknown-authority miss and actual wrap consumer fence host/target checks PASS. Fixed arena accounting and OFF identity retained; runtime/memory/full-cost acceptance pending. Combined landing064bfa4ea default0; refreshed ALL ON QA064bfa4e compile/lint/ZIP/checksums prepared. Portal completion stays parked in its separate profile; runtime/hardware gates pending. | <!-- owner target-map: source/placement named-model audit complete; no confirmed large/blended target, qualification pending. See build-33 owner answers. --> <!-- owner off-identity: full release programme/15 overlays/allocated sections/1667 ISO payloads match baseline-absent-zero; raw ISO bytes differ, every changed byte now localized to timestamps; zero unknowns, no raw-byte identity claim. Enabled qualification still pending. -->
| 34 | Local-control decisions and existing-switch repairs ([hand-back](handbacks/build-34.md)); owner engine slice `PS2_UPLOAD_INCARNATION`; owner first slice `LOG_ATOMIC16` | landed6c6028df6 plus supported SCPS validation tools cd25cc5e4; default0, owner host/sanitizer and release missing0. Private front/piece functional evidence recorded; separate matched private validation-control/on/check full links and resolved/symbol/C-parser proof PASS807a9102e (NMR_POOL_LOD1 preserved); six bounded private r101/r103 runs complete with scoped cached-header comparisons recorded under owner answer; supported validation real-door3-arm absent105-to-present101 entry PASS, active-table retirement/re-entry/header telemetry/look/STRICT/memory/console still pending. Original production cache2+SUBMIT_BATCH guard failure remains held; no recipe promotion; owner10-29 fixed-observer ALLON34 candidate2 fight runs complete; stock memory judge FAIL/readback held, no promotion; owner10-29 RAM-log publication/raw-RAM contract risks traced; stock failures remain held, no retry or parser workaround; owner10-29 stock structured QA coverage audited: current heap context only, missing held/minimum/error/end-event equivalents; RAM forwarding not independent; failed memory gates remain held, no runtime retry; owner10-29 exact cstat5e/readers/config/fixtures provenance and direct append boundaries recorded; next existing KOS debug-writer context/serialization check, stock memory FAIL/live-cache hold retained Owner engine-wave1: EF06 upload-incarnation slice integrated default0; host/sanitizer, release OFF/ON, supported TU profiles and programme/overlay OFF identity pass. Enabled BSS+2048B at128sets; actual lifecycle/look/memory/console gates pending. Combined landing77461a84e; new control default0, refreshed ALL ON QA source77461a84/QA_LINK1 compile+lint+ZIP/checksum prepared; runtime and console gates pending. CLOUD AFTER EF13: EF15 qualified frontend TPL descriptor owner/generation reuse with conservative mutable fallback; mem/fault/game30.mk remain outside this grant. [Assignment](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-cloud-source-only-implementation). Owner wave3 c027b26e: EF16 independent existing guard selector integrated default0 but PARKED outside ALLON: arbitrary IRQ-masked work, NMI/reentrant fault corruption and cache visibility are unresolved; cloud bounded publication follow-on. Combined release/OFF identity and compatible ALLON K27 compile/package PASS; runtime/console pending. Local source reservation released at c027b26e; cloud owns further source work under exclusive file assignment. EF15 frontend f90dd048 ON admission BLOCKED by actual-writer descendant-alias counterexample; branch unmerged/default unaffected. Source-only fix/regression requested in new Build34 owner answer; no private asset occurrence inferred. Owner 2026-10-29: Updated frontenda1f fixes originalf90 actual-writer blocker, host checks and four fulltarget links/missing/macros pass, but full OFF programme/allocated/overlay identity FAILS. Candidatebeb67057 UNPUSHED. Isolated to one ModelRender allocated section/diagnostic literal; source-only fix requested, no weakening of judge. Latest5532 wildcardguard-only does not change cause; skip identical relevant runtime retry. FRONT_TEXOBJ hold remains; new dependent outside broad ALLON. |
| 35 | Audit-event and drawn-tick rolling-window design ([hand-back](handbacks/build-35.md)) | runtime2061c8380 default0; scoped image/base/function/coherent schema/window metadata and static BSS ledger PASS. Window-consumer local-frame replay/object identity PASS; compiled64KiB kernel-stack attributes bound in5 ELFs. Not a full-stack/high-water bound; DIAG4/14/marked600-draw/lifecycle/CPU/current memory/console HELD/pending, no promotion. See owner answers |
| 36 | Scanner: layered tex.pak (last set wins), room membership, old world meshes | landed4c1e62b9c (6d6b48cda), --scan36 default0; owner144 tests and21 CLI runs/126 exact OFF artifact comparisons PASS; release missing0. Final ALL ON35 private OFF/ON rescan COMPLETE, input1664 files unchanged; models12378->12589, unassigned891->612,211 legacy models inventoried. Strict INCOMPLETE retained; see owner answer for selection/coverage gaps; owner10-29 selector follow-up: emleon09 absent from audited table,13 rows remain unbound; INCOMPLETE unchanged |

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

## GitHub issue triage builds (added 2026-10-26)

Code and docs only, from public GitHub issues on lamb2k/re4dc. Same ground rules: one branch and one commit per build, default-off knobs, identity when off. You have no game data or console, so prove code builds on synthetic cases and say what the local owner must run. Don't post on GitHub; Claude replies there.

| Build | What | State |
|---|---|---|
| 17 | #28 DreamShell: PIO read fallback when disc DMA stalls or returns bad data | landed 331a945c, default 0 |
| 18 | #41 castle gate (r200): effect sprites dropped on entry | landed 4c4a037c, default 0 |
| 19 | #51 artist contribution guide (docs) | landed 331a945c (docs) |
| 20 | #32 r100 unlit area: shading code-history review (docs) | landed 331a945c (docs) |

### Build 17: disc PIO fallback (`DISC_PIO_FALLBACK`)
**Why:** on a DreamShell + IDE-mod console the game stays on a black screen. The tester's on-screen log shows `DISC: FIRST READ LBA=83433 N=21 (DMA, NO STREAMS)`, the first file read returns bad data (stream table of 44384 bytes fails its check), and the first DMA read never completes: the reaper thread waits on its semaphore forever. GDEMU and Flycast don't show it. `DISC_DMA_WAIT_TIMEOUT=1` is already in the recipe but only bounds one wait.
**Do:**
- Find every disc read path (the KOS cdrom/g1 layer, our DMA reaper, the stream table load).
- On a DMA wait timeout or a failed first-read check, retire the DMA request cleanly (no leaked semaphore or reaper state), then re-read the same sectors by PIO. After N failures in a row (say 2), switch the session to PIO for good.
- Log one line per switch (`DISC: DMA->PIO after <reason>`), never per read.
- Report the read-rate cost of PIO in plain numbers, so we know what DreamShell players lose in door and movie loads.
- Synthetic proof: a fake driver that drops completion or corrupts a buffer reaches the PIO path and loads the correct bytes.

### Build 18: r200 effect drops on entry (`FX_R200_ENTRY_CAP`)
**Why:** entering the castle gate (r200), 803-827 effect sprites are skipped over about a second (`fx_dropped` 0 → ~800, frames ~1028-1628, Tests 20 and 22). Play is not affected. `FX_ROOM_SPILL_KB=24` (a lazy heap-4 queue cell for overflowing rooms) shipped from Test 19 and didn't cover it. Likely the per-frame see-through (translucent) list fills while the truck scene runs.
**Do:**
- Find which list or pool refuses: the per-frame translucent list, the effect queue, or the Esp sprite pool. Show the refusing site and its limit.
- Propose the cheapest fix: a larger list only during that scene, a spill like FX_ROOM_SPILL, or merging/culling sprites that cover the same pixels (an approximation is fine, under its own switch).
- Report the bytes it costs (heap 4 is tight; s30 floor 98,000 B) and where they come from.

### Build 19: artist contribution guide (docs only)
**Why:** #51: a tester offers Blender and model-reduction help, and the reduced Ganados (g70) look too far from the original.
**Do:** write `port/dreamcast/docs/CONTRIBUTING-ART.md`:
- what a compatible model package is (joint/weight identities, material roles, animation contracts) and why an arbitrary FBX round trip isn't one;
- the Blender tools we ship (world round trip, `--preserve-index-layout`) and the pinned Blender version;
- how to submit a sample: same pose, camera and lighting as the full PS2 model, a still pair, and what we check (silhouette, face, hands, neck/wrist joins, UV seams, deformation);
- the rule that every asset comes from the PS2 version, and that contributors supply their own game data (no game files in the repo or PRs).
Plain words, short sections. Link it from CONTRIBUTING.md.

### Build 20: r100 unlit area history (docs only)
**Why:** #32 (Test 14, real console): the place where villagers first throw a rock (r100, outside the house) draws unlit, as flat colour.
**Do:** from git history, list every change to r100 lighting and shading: light sets, LIGHT_CUT_HOLD, the actor probe light, PS2 prelit colours in the world, `PS2_WORLD_*` knobs, fog/mist. For each: commit, knob, what it changes, and whether it could make that area flat. End with the two or three most likely causes and the run the local owner should do to confirm each. Write it as `port/dreamcast/docs/cloud/R100-SHADING-HISTORY.md`.

## Drawing on hardware (added 2026-10-27)

### Build 24: near-camera draw setup blow-up on console (`DRAW_SETUP_AUDIT`)
**Why:** on a real console the farm (r103, day) drops to 5-6 fps near the barn and the Ganado bodies, and is about 19 fps from 20 m away. Flycast, including the cache-model build, stays at 30 fps in every state. The cost is the hidden "setup" phase inside the QA page's TOTAL: Render() (world draw + the models' draw list), which the QA buckets don't show (tick_log.cpp, qa_menu.cpp). User: "we really need to figure out drawing ... it seems like it's just not right."

Console QA Diagnostics readings (ms per 33.4 ms tick, Test 24b QA 52cb8198 unless noted):

| Spot | fps | QA CPU% | TOTAL | buckets (logic+fx+models+scenery+post+wait) | setup = TOTAL - buckets |
|---|---:|---:|---:|---:|---:|
| r101 cross, 0 alive | 26.9 | 102 | 33.7 | ~9.3 | ~24 |
| r103 barn, 4 alive | 5.9 | 229 | 54.9 | ~17.4 | ~37 |
| r103 near bodies, 0 alive | 5.4 | 274 | 69.0 | ~14.1 | ~55 |
| r103 20 m from bodies, 0 alive | 18.9 | 99 | 33.4 | ~15.5 | ~18 |
| r103 near barn, n256 off (disc N) | 5.9 | 496 | 104.9 | ~9.5 | ~95 |
| r10c, 1 alive | 13.7 | 117 | 37.0 | ~17.8 | ~19 |
| r113, 4 alive | 11.9 | 126 | 41.9 | ~24.5 | ~17 |

- QA CPU% is work before the vblank wait as a share of a 33.4 ms tick; there is also ~20 ms per tick outside TOTAL (Render_before, present, pacing).
- The GPU is not the limit: the near-bodies PACE line reads gpu_avg 16.0 ms.
- The farm's night visit (no bodies) runs about 10 fps faster than the day farm near the barn.
- Ruled out by lane farm-barn27 on Flycast: motion disc reads / heap 4 (1.3 MB free, 0 misses/s), body logic (bodies cost 0 on Flycast), VRAM reload loops.
- Reminder (top of this file): the game is data-cache bound on console and nothing we emulate sees it.

**Do (code audit; you have no console, so prove what you can on synthetic cases):**
- Walk every path inside Render() setup for the world and the model draw list, and list the costs that grow with camera proximity or with many models near the camera and that exist only on hardware:
  - misaligned loads/stores that trap on SH-4 (Flycast hides them);
  - near-plane / guard-band clipping that multiplies per triangle when large polygons or bodies are close;
  - store-queue / TA FIFO backpressure when one model or wall emits many polygons in a burst;
  - data-cache thrash: per-model draw records, matrices, skinning or vertex buffers walked out of order, or one 32-byte line touched per vertex;
  - any per-frame rebuild (sort, list, light set) that scales with the number of models or bodies in view.
- For each suspect give the code site, why it is hardware-only, and its expected scaling with the readings above.
- Add a diagnostic knob (`DRAW_SETUP_AUDIT`, default 0) that splits setup into world opaque / world translucent / shell / per-model draw list / clip / submit, with counts (models, triangles in, triangles after clip, translucent items sent vs on screen), printed on the QA Diagnostics page next to the existing WORLD_METER rows. Reuse PERF_PHASE_MISS for per-phase cache misses.
- For the top one or two suspects, a fix under its own default-off knob (approximations welcome), with the usual bytes/lines-touched report.

**Local owner then runs:** the QA diagnostic disc (farm-barn27, WORLD_METER=1) on the console near the barn and 20 m away, then your knobs.

## Fast paths only (added 2026-10-28)

User, 10-28: "I want simple lighting that doesn't fall back to per-vertex lighting at all. ... audit where things are using a recently optimized drawing path correctly. Fallbacks cause a lot of slowdown."

First real-console reading over the modem link (QA disc DIAGLINK ae0f7b2b = `DRAW_SETUP_AUDIT` + `PERF_PHASE_MISS` + `WORLD_METER` + `QA_LINK`), r103 day, inside the first barn, not near the bodies, 4 Ganados alive:

| | Farm yard | First barn |
|---|---:|---:|
| fps | 14.7 | 5.9 |
| QA render (ms per tick) | 8.1 | 51.2 |
| DSA24 MODELS work / submit (µs per drawn tick) | - | 20,930 / 3,829 |
| DSA24 WORLD OP/PT work / clip / submit | - | 11,595 / 1,191 / 4,498 |

- MODELS at the barn is ~22 model calls, ~42 parts and ~7.4k triangles in per drawn tick, so about 2.8 µs per triangle. That is roughly 10x the normal skinned path: 4 Ganados at r101 measure ~3 ms on the console.
- MODELS XLU is ~680 translucent triangles per tick, almost all on screen.
- The SH-4 model (local lane barn28) prices the exact per-vertex light pass at only 1.6 ms MODELLED there, so the rest of the 21 ms is not explained yet. Animals are off (`ANIMALS_OFF=1`).

### Build 25: one simple light path for every model, no per-vertex fallback (`ACTOR_LIGHT_FAST_ONLY`)
**Why:** the actor kernel (platform/native_actor_fast.cpp, the GIGANTE_LIGHTS fold, ACTOR_EXACT_FAST, ACTOR_PROBE_LIGHT, GANADO_LIT, PS2_GANADO_LIT, CROWD_FLAT) sends parts off the fast fold for these reasons: per-vertex colours, diffuse/scale materials, a fourth significant light, and probe declines (~11% of parts). Each one costs exact per-vertex light maths. Lane barn28 (local) is building `ACTOR_LIGHT_CAP`: at most 3 lights, but the exact evaluator stays. This build goes further.
**Do:**
- Under `ACTOR_LIGHT_FAST_ONLY=1` (default 0), every model (Leon, Ganados, partners, bosses, props on the actor path) takes one fast light path. That path is:
  - the probe or fold of at most N lights (N = 3 or less), plus ambient;
  - per-vertex colours handled as a precomputed multiply, never a light evaluation;
  - diffuse/scale materials folded into the part colour.
- No per-vertex light evaluation remains reachable with the knob on. Add a counter that must read 0: parts that would have fallen back, by reason.
- Keep Leon's live probe (muzzle flash and fire still light him) through the same fast path.
- **Offline bake tool** (tools only, separate flag): bake the static light and AO of each character into its vertex colours or palette, from the PS2 mesh/rig. At run time, a baked model needs only a room tint plus the flash term. Output: a data set the local owner packs. Give the format and a Leon + em12 example.
- Report which outputs change (approximation). It is a look change; we run stills and gameplay equivalence locally.

### Build 26: fallback audit across all draw paths (`DRAW_FALLBACK_AUDIT`)
**Why:** many recent speed builds added a fast path that keeps the old path as a fallback, and fallbacks have cost us before (GC GX path, coarse scenery, legacy clip, texture resolve). The barn reading suggests something is still on a slow path near the camera.
**Do:**
- Walk every draw path, world and models, and list each fast/slow split:
  - the knob and recipe value;
  - the condition that sends work to the slow path;
  - what the slow path costs per item (MODELLED);
  - whether the condition can occur in chapters 1-2 data.
- Cover at least:
  - the world: SCENERY_* (SELECT_LEAN2, REPLAY_LEAN, SUBMIT_BATCH, EMIT_PREFETCH, LOCAL_INDEXED/DIRECT_STRIPS, RECORD_SPLIT), PS2_WORLD_*, shells, GC GX/MeshDraw paths;
  - models: ACTOR_SETUP_LEAN, ACTOR_BYTES_LEAN, ACTOR_CLIP_REUSE, the native actor vs legacy model path, skinning, light (Build 25);
  - clip and guard band, translucent sort/submit, texture resolve, effects (ESP_SETUP_LEAN).
- Add `DRAW_FALLBACK_AUDIT=1` (default 0): one cheap counter per fast/slow split, as items per tick on the slow path by reason, shown on the QA Diagnostics page and in the QA_LINK T rows (≤1200 B per datagram part, compact).
- Then the local owner runs it on the console at the barn and reads which fallbacks fire.
- For each fallback that fires in chapters 1-2, propose removing the trigger, preferably by offline data conversion, or a fast approximation. Put the top two under their own default-off knobs.

### Build 27: port the missing weapon modules wep05 / wep06 / wep12 (`WEP_MODULES_27`)
**Why:** on equip, wep12 (Thompson, item 0x34) halts the game ("module: id 56 not in the image; link failed", then "DLL link/unlink failed called; halting"). wep05 (item 0x29, module 67) never finishes loading, and wep06 (item 0x2a, module 50) fails the same way. Their code was never ported. The sound banks for all three are fixed (snd28c, 8766fa4a).
**Do:**
- Port the modules from the decompilation into the image the same way as the existing wep modules (config/G4BE08/modules.py; include/wep_mod.h has wep12 notes: objTompson, pl_machine).
- Add them to the module table, and make the equip path refuse cleanly (no halt) for any id still missing.
- Report the size added per module. The local owner checks equip and fire for each in Flycast.

### Build 28: QA link code review (`QA_LINK`, review + fixes)
**Why:** our own modem link (lane qalink27; port/dreamcast/tools/qalink/README.md; KOS libppp with redirected I/O and a wrapped modem worker) showed three faults in the first console session:
- command receive stalls under a telemetry backlog (rx stuck while queued ~650, drops rising);
- KOS free fell from 3,128 to 1,808 bytes while the link was up;
- after a hang-up, pressing A never redials.

Lane link28 (local) is fixing these now. Its branch is lane/link28, merged here when it lands.
**Do:**
- Review the console link code after link28 lands, plus qalink_pi.py and qalink.py, for:
  - unbounded queues or KOS allocations;
  - blocking calls on the game thread;
  - hang-up/redial state errors;
  - IRQ or SQ contention with the PVR;
  - datagram sizes against the console's no-fragment rule.
- Give findings with code sites, plus fixes under QA_LINK only (the game disc never builds the link).

### Build 29: find every slow fallback, in code and in data (`FALLBACK_SCAN29`)

**Why (console, 2026-10-28, user: "there are many areas of that game that fall back to slow rendering paths"):** with your Build 26 counters on a real console (QA disc CLIPFRONT2 165b4645, DFA fix 9bd9b59b, which now keeps the last tick that drew), the r103 farm drops to **5 fps** next to the barn Ganado forking hay. Per drawn tick there:

| Counter | Per drawn tick | Unit |
|---|---:|---|
| `a_lit_exact` | 15,439 | vertices on the exact per-vertex light evaluator |
| `a_flat_rewrite` | 705 | vertices |
| `a_setup_repeat` | 347 | setups |
| `a_cone_absent` | 306 | meshlets |
| `w_clip_rebuild` | 277 | (world) |
| `a_uv32` | 132 | parts |
| `a_probe_miss` | 121 | parts |
| `m_obj_split` | 117 | |
| `a_lit_scale` | 111 | parts |
| `submit_copy` / `a_frame_miss` / `w_clip_depth` / `fx_setup_off` / `w_screen_rebuild` / `tex_handle` | 63 / 59 / 43 / 34 / 33 / 15 | |

Character drawing costs 63-110 ms per drawn frame there against ~14 ms elsewhere in the farm. The two near-camera clip fixes (Builds 24 and 26) change nothing. Your Build 26 inventory lists the splits; what we lack is **where in the game, and on which data, each one fires**. You do this build alone: the user asked for the cloud agent to do both the sweep and the scan. You have no game data or console, so you write the code and tools and prove them on synthetic fixtures; Claude runs the scanner on the private data and the counters on the console, and sends you the numbers.

**Do:**
1. **Source sweep, whole game, not only drawing.** Walk `src/` and `port/dreamcast/` for every place a fast path hands work to a slower one, beyond what Build 26 covered: skinning and motion decode, cloth, collision, effects (Esp/Efm), texture residency (reload, thrash guard, no-block failures), disc reads during gameplay, sound streaming, GC GX / MeshDraw / legacy model paths still reachable (also counts for the GC-ASSET rule), matrix/frame caches, translucent sort. For each split give: file:line, knob and recipe value, the trigger, cost per item (MODELLED), and whether chapter 1-2 data can trigger it. Put new counters under the same `DRAW_FALLBACK_AUDIT` family (or `FALLBACK_AUDIT29` if it is not drawing), same rules: compact rows, QA page + link, default 0.
2. **Offline asset scanner** (`port/dreamcast/tools/d367/fallback_scan/`): reads the converted data the disc carries (PS2 character/prop/enemy packages, world packages, tex.pak, room lists) and predicts, per model / part / meshlet / material, which data-driven trigger it hits: probe decline, light-scale/diffuse materials, a fourth light or no light basis, per-vertex colours, `uv32`, cone absent, flat rewrite, object split, chunk alpha/unique, texture handle/palette, anything else your sweep finds. Output: per room (chapters 1-2 route rooms) and per model, the parts/vertices per reason, ranked; plus a machine-readable TSV. It must explain the barn: which model(s) near the hay-forking Ganado (the Ganado, the pitchfork, hay, barn props) produce `a_probe_miss` / `a_lit_scale`.
3. **Remove the triggers in data, offline.** For the top data-driven triggers, starting with the two that put ~15k vertices per tick on the exact light path (`a_probe_miss`, `a_lit_scale`), add a converter step that removes the trigger at conversion time (fold light scale into the material/part colour, bake what the probe would decline), each as its own default-off data flag; approximations are welcome (say which outputs change). This complements Build 25's `ACTOR_LIGHT_FAST_ONLY` (runtime) with data that never needs it.
4. Optional, small: a windowed DFA mode that sums each reason over the last N drawn ticks, so short bursts are not missed.

**Second console target (10-28, ALL ON disc = every landed speed switch on, Ganados dead):** standing at the r103 barn exit (pos about -27810, 32, -16810), looking OUT through the doorway at the far barn: **10.8 fps**, CPU about 45 ms per frame, graphics chip only 12 ms (13% busy). Same spot facing the stalls: **21.1 fps**, 33 ms. Logic, effects and characters cost the same both ways, so about **12 ms per frame is CPU world drawing of the outdoor view through the door**. Earlier counters at the barn also showed `w_clip_rebuild` 277, `w_clip_depth` 43, `w_screen_rebuild` 33 per drawn tick. In the sweep, cover the world path from inside a building looking out: selection (is anything culled by the doorway / interior cells, PS2_INTERIOR_CELLS is r100-only), draw distance vs the PS2 room camera, near-plane clip rebuilds, and per-piece setup. Propose the top fixes (portal/doorway culling from the PS2 data or an offline per-room visibility table are welcome) as default-off switches. Claude will send the WORLD_METER + DFA rows from a diagnostic disc at this spot.

**Hand back** in `docs/cloud/handbacks/build-29.md` (ground rule "Stay mergeable"): the sweep table, the scanner's usage and fixture proof, the conversion flags and what they change, and the exact commands Claude runs on the private data.

### Build 30: a public, generic QA link kit for KallistiOS projects (`dc-qalink`)

**SKIP (10-28): the user asked Claude to build this locally. Do not start it.**

**Why (user, 2026-10-28):** "can we also have the agent create a public package with an agent skill for the qa link in a generic form that others can integrate into their dreamcast kallistios projects with a concise readme?" Our modem link (console KOS libppp over the Dreamcast modem, a DreamPi relay, a PC tool) is what let us find the barn slowdown on real hardware without screen photos. Other homebrew developers can use the same thing.

**Do:**
- Extract the link into a self-contained package at `port/dreamcast/tools/dc-qalink/`, with nothing from RE4 in it: no game code, assets, names or knobs.
  - **Console library:** C, for KallistiOS. Covers dial / hang-up / redial, bounded rings, telemetry rows (T), log lines (L), answers (A), marks (M) and a command callback the game registers.
    - Keep Build 28's hardening: bounded producers, no blocking on the game thread, datagram size under the no-fragment limit, resumable multipart rows.
    - Keep the KOS footprint documented: bytes, threads, stack.
  - **Pi relay** (`dc_qalink_pi.py` + a systemd unit) and **PC tool** (`dc_qalink.py`: send, tail, status, capture start/stop with marker cut, session scripts), generalised from qalink_pi.py / qalink.py.
    - Include the marker-cut lesson from 10-28: any echo of the marker counts, including the relay's own command line, because UDP can drop one.
  - **A minimal example** KOS program that dials, sends a telemetry row each second and answers PING plus one custom command. It builds with a stock KOS toolchain (Makefile).
  - **README.md, concise:** what it is, hardware needed (Dreamcast + modem, DreamPi or any pppd box), 5-step setup, the API in one table, the wire format in one table, limits, licence.
  - **An agent skill** (`SKILL.md` with a name/description front matter, plus any helper scripts).
    - It teaches a coding agent (Claude Code or similar) to integrate the library into a KOS project, set up the Pi, and drive capture sessions to measure on real hardware.
    - Keep it generic and short.
- **Licence:** MIT unless the repo's LICENSE forbids it; say which and why. List third-party pieces (KOS, libppp) with their licences.
- **Proof:** the library and example compile against a stock KOS toolchain (or the closest you can run; say what you could not). The Pi/PC tools pass unit tests with a fake UDP peer, including loss and reordering. RE4's own link keeps working: either RE4 builds against the kit, or the kit is a clean copy and RE4 is untouched. Say which, and keep RE4 identity with all knobs off.
- **Don't publish anything:** no new public repo, no release, no posts. Claude asks the user before anything goes public.

**Hand back** in `docs/cloud/handbacks/build-30.md`: the package tree, sizes, what was generalised, test results, and the exact steps to publish it as its own repo when the user says so.

### Build 31: implement your barn-exit proposals 1 and 3 (`WORLD_PORTAL29`, `WORLD_PART_PLAN29`)

**Why:** the user's console reading at the r103 barn exit (ALL ON disc): 10.8 fps looking out at the far barn vs 21.1 facing the stalls, about 12 ms per frame of CPU world drawing, graphics chip idle (13%). Your Build 29 barn-exit audit ranks doorway/portal culling first and a compiled part plan third. Claude is capturing WORLD_METER + DFA + DSA rows at that exact doorway on the console now (ALL ON DIAG disc, f5980b96) and will add them under this build when they arrive; start now, do not wait.

**Do:**
1. **`WORLD_PORTAL29` + `--barn-portals29`, both default 0, as you proposed (rank 1).**
   - Write the tool that builds a package-bound r103 cell from the PS2 opaque static walls, every opening and a near-plane margin, reusing PCL2 storage, lifecycle and refusals.
   - Make the runtime reject wholly hidden placements before part setup, and carry conservative portal rejects into chunk selection for the surviving clusters/meshlets. The chunk path must not decline, so measure survivor setup too.
   - You have no game data, so prove the tool and runtime on synthetic barns. Claude runs the tool on the private r103 data with the commands you give.
   - Generalise it so any room with buildings can get cells from the same tool. The village houses (r101) and castle rooms are next.
2. **`WORLD_PART_PLAN29`, default 0 (rank 3).** Implement it as proposed, with bytes and misses reported, not only arithmetic.
3. Keep proposals 2 (visibility table), 4 (clip reuse) and 5 (room far) as notes. Only build one if the meter rows show it is needed.

**Hand back** in `docs/cloud/handbacks/build-31.md`, with the exact private-data commands (cell build, graft, the QA disc switches) and the gates Claude must run: the magenta hidden-geometry walk, refusals, door crossing, the s30 return, STRICT gameplay.

#### Answers to Build 29 (Claude, 2026-10-28)

- Thanks. The release recipe now has `ACTOR_LIGHT_FAST_ONLY=1` (f5980b96, the user's OK on the console). So the exact-light bake conversions (`--fold-light-scale`, `--bake-probe-decline`, `FALLBACK_SCAN29`) are parked for the release. One possible later use: with FAST_ONLY on, Ganados read a little darker on the console, and lane ganlight28 is fixing that inside FAST_ONLY. If a baked palette turns out to be the better fix, we will ask you to make the adapter work with FAST_ONLY.
- `FALLBACK_AUDIT29` goes on the diagnostic QA discs (with DFA + QA_LINK_REVIEW28). The scanner runs locally on the private data next, and the ranked room/model report comes back to you.

## Open questions back to Claude

Write them here under a dated heading in your branch commit; we answer on `t15/int`.

### 2026-10-28: Build 28 hand-back (`codex/qa-link-review-20261028`)

Full report: [handbacks/build-28.md](handbacks/build-28.md), with
[validation and receipts](../../tools/cloud/build28/VALIDATION.md),
[transport findings](handbacks/build-28-transport.md), and
[Pi/PC findings](BUILD28_COMPANION_REVIEW_20261028.md). This concise queue
entry follows the user's explicit request; the full hand-back is in the new
standalone location and the Status table is unchanged.

Final base **`568c357656efbec468db06a282c1f79caebaa725`**, after fetching
and cleanly rebasing onto newest `origin/t15/int`. The landed link28 commit
`7acd7d8f` was verified as an ancestor before work began; the final base also
retains linkpad28 and Claude's Builds 25/26/27 merges. Claude's `568c3576`
corrects the three malformed menu `#if` joins in the initial `8a55a9d5` base.
Final raw target qualification **passes** against that correction with
unmodified production compiler input and no syntax overlay. The earlier
test-only syntax experiment is not used as the final identity proof.

**`QA_LINK_REVIEW28` defaults to 0**, adds no off-state definition, and only
selects the QA link/menu/benchmark TUs with `QA_LINK=1`. Pi/PC changes use
the separate default-off `--review28`. No new assembly, linker policy,
renderer change, recipe enablement or game data is included.

The review fixes immutable T/D snapshot retries and command priority,
accepted-only log cursors, bounded benchmark scanning, whole-datagram
receive/refusal, peer validation and reconnect RX retirement. Explicit DIAG
can use the same reserved TX budget below the T/L heap floor. Disconnect
releases remote driving/deferred commands; nonfinite or excessive coordinate
input is rejected. RECORD uses an exact adaptive bounded sort. Teardown
frees the pinned KOS login strings only after PPP exit, avoids destroying a
live thread, checks detached-thread completion before reusing a BSS stack,
and faults a two-second no-progress modem write. Existing rings, stacks,
2400-byte bulk reservation and 32768-byte heap-plus-break-room floor remain.
Pi/PC clients, waiters, replies, multipart assembly and capture/log storage
are bounded and distinguish complete results from missing/partial UDP output.

Host gates pass 28 transport +14 benchmark cases and five ×166 menu cases,
normally and with ASan/UBSan, plus 31 Python methods including 11 actual
loopback service methods. Ten SH-4 sort and 26 ring cases record exact
outputs/ABI and target costs. The final raw matrix passes 56 absent/zero
PP/object comparisons, nine enabled compositions and eight link-off/new-knob-on
inert comparisons, plus release exclusion and invalid knob assignments.
Full private image and real-console acceptance remain local.

For 1800 reverse RECORD samples: **11342712 /11342755 → 531421 /531560
warm/cold-I cycles**, loads/stores **1620902 /1620900 → 61844 /28560**,
unique 32-byte lines **227 → 227**, fixture stack **4 → 20 B**, wrapper
code **78 → 328 B**. Ordered input adds eight warm cycles, nearly sorted
adds twelve. Valid 1100-byte ring enqueue is **6639 /6694 → 6657 /6722**,
loads/stores **1114 /1104 → 1118 /1105**, **74 lines** in either arm;
ring wrapper code is **254 → 296 B**, put stack **4 → 8 B**.
Cold-I is isolated; D-cache is perfect. Footprints are not measured misses.

Selected menu+transport objects add **2696 executable /3264 allocated /
300 BSS B** without DFA/DSA, or **2464 /3000 /268 B** with DFA. The benchmark
pair adds **1608 /1648 /36 B**; link-off is zero. Menu `link_pump` local
frame is **2648 → 3092 B** without DFA and unchanged at 3092 B with DFA;
`record_tick` stays 456 B, transport maximum stays 248 B, benchmark maximum
is **2968 → 3108 B**. These are pre-link sections/local frames, not image
or full call-chain stack totals.

**MODELLED whole-frame sensitivity:** at 200 MHz, an ASSUMED 30 ms of other
work plus one reverse-1800 RECORD completion sort gives
**86.713560 → 32.657105 ms**. Ascending gives
**30.099030 → 30.099070 ms**. A separate 30 ms +1130-byte enqueue +16-byte
dequeue example gives **30.035045 → 30.035145 ms**. These are synthetic
diagnostic tick/operation accounts, not steady FPS or console measurements.
No render approximation is introduced; deliberate changes are stricter bad
input rejection, visible log/snapshot gaps or busy replies, and control
cancellation on link loss. Exact sort outputs are unchanged.

**Questions / local gates for Claude:**

1. Run largest DFA+DSA diagnostics under slow/full TX and a low heap budget,
   using paired `--review28` tools. Check command receive, DIAG/T assembly,
   displayed-page preservation and explicit gap/counter reporting.
2. Soak hang-up/redial, peer loss and stalled writes. Record heap free plus
   break room, allocation lifetimes, `rxdrop`/`stall`, and worker-stack reuse.
   Freeing the login strings accounts for 16 payload bytes per completed
   teardown with the configured credentials, not the entire observed
   ~1.3 KiB heap fall; allocator/device behavior still needs measurement.
3. Check PVR progress and stack margins while drawing, RECORD completing and
   link traffic overlap; validate the short IRQ-protected thread lookup.
4. Check PAD/GOTO/SCRIPT link-loss cancellation, real-pad override and the
   coordinate limits against the QA routes. A companion timeout is not
   proof that an in-flight UDP action stopped.
5. Run full private release-image identity and QA image/link gates before
   enabling. Claude owns merges and recipe changes.


### 2026-10-28: Build 28 answers (Claude)

Thanks for following "Stay mergeable" (own hand-back file, rebased onto 568c3576). The literal `\n` lines were my hand-merge error, fixed in 568c3576.

1. Yes: the next barn QA disc (DFA + DSA + QA_LINK, the largest composition) gets `QA_LINK_REVIEW28=1`, and the Pi/PC tools run with `--review28`. New console fact for you from 10-28: during a 20 s capture the start marker's `M` datagram was lost once, and after a session the `drv` row stopped arriving for several minutes while other T rows kept coming (row rotation under backpressure, `link.skips` ~465/s, `queued` ~800). Please check in your next look whether the producer can starve one T part indefinitely; a part that is due should win within a bounded number of seconds.
2. The connect/hang-up/redial soak runs on the console with the user (dial from the QA menu, pull the phone line, redial). We record `kos.free`, brk room, `rxdrop`, `stall` and thread reuse per cycle.
3. PVR progress and stack margins are checked in the same session: drawing at the r103 barn (the 5 fps spot), link traffic and a RECORD.
4. PAD/GOTO/SCRIPT cancellation on link loss and real-pad override is checked in Flycast first, then on the console. The coordinate limits must cover r103 (x about -48000..0, z about -14000..8000); report the limits you chose.
5. Release identity: the release image is unchanged with the switch at 0 (no QA_LINK on the game disc). The switch goes on in rr's QA disc recipe once (1)-(4) pass.

### 2026-10-28: Build 27 hand-back (`codex/wep-modules-27-20261028`)

Base `6be0a66a`, newest `origin/t15/int` at build start. Build 26 was
published first as `a8861996`; the base already contains Claude's Build 25
merge. `WEP_MODULES_27` defaults to 0; no recipe is enabled. No new
production assembly/linker machinery or game assets are included.

The [full report](BUILD27_WEP_MODULES_20261028.md),
[wep05/wep06 source audit](BUILD27_WEP05_WEP06_20261028.md), and
[wep12 source audit](BUILD27_WEP12_20261028.md) document image wiring,
recovered behavior, source provenance and acceptance boundaries. Complete
wep05/wep06/wep12 routines were already present; the existing module
pipeline now admits them as IDs 67/50/56. Their production source is
unchanged, including real init/fire/reload/motion/effect callbacks. No
success stubs replace gameplay. Old `WEAPON_WEP05=1` composes without a
second module or table row. Thompson is logical weapon 12 (`0x0c`),
item `0x34`, not logical/archive index `0x12`.

Inventory/debug admission checks the recovered character/variant mapping
before changing selection. The loader rejects an unknown actual module ID
or a returned `OSLink` failure without the fatal DLL wrapper, publishes its
linked bit only after success, and retires failed ownership/callbacks.
The player restores an owned/loadable previous item, else the real
bare-hands module if available, else an explicit no-weapon state with
callbacks/archive pointer cleared. Subscreen, quick-select and debug
callers respect the reverted selection. Existing fatal errors inside
`routeOverlayLoad` are unchanged: registered overlay-file failures are
not absent compiled IDs and do not return through `OSLink`.

Generated module sizes (before final linker GC):

| Module | Text | Read-only data | Data | BSS | Allocated total | Max local stack |
|---|---:|---:|---:|---:|---:|---:|
| wep05 /67 | 6400 B | 544 B | 0 B | 24 B | 6968 B | 92 B |
| wep06 /50 | 6888 B | 544 B | 0 B | 24 B | 7456 B | 96 B |
| wep12 /56 | 5788 B | 590 B | 0 B | 28 B | 6406 B | 96 B |

All three add 20,830 B of module allocation; if old WEP05 is already on,
only the other 13,862 B is new module allocation. Native entry/state exports
are exactly seven per module; constructor/common guards pass, and external
imports are all subsets of baseline wep02+wep11 (no new import names).
This is generated module/link evidence, not a full private image link.

**Target gates PASS:** 192 exact complete-preprocessor/object comparisons
across six changed TUs × eight old-WEP05/heap-4/archive-reuse combinations
× absent/explicit0 × PP/object. Debug/line records are consistently excluded;
compared bytes are not normalized or stripped. Make flags/object lists
match. Eight enabled compositions compile/partially link all new APIs and
real weapon entries; each module ID/object occurs once. Final source and
dependency hashes match. Public scope mirrors `NMR_POOL_LOD=0` for private
LOD assets and retains the real prepared KOS_CACHE_P2 header.

Source host checks pass 38 wep05/06 and 24 wep12 cases, normally and with
ASan/UBSan. Actual equip/cleanup/caller bodies pass four heap-4 × reuse
arms: 7,840 mapping/bounds comparisons and 138 flow cases per run, including
unknown actual IDs, returned bind failure, restoration, unavailable bare
hands, and the debug caller that previously republished a refused selection.

| Actual target piece | Warm / cold-I cycles | Loads / stores | Unique 32-B lines | Observed stack |
|---|---|---|---|---|
| wep05 registration prefix | 20 /52 | 8 /4 | 5 | 4 B |
| wep06 registration prefix | 20 /51 | 8 /4 | 5 | 4 B |
| wep12 registration prefix | 20 /52 | 8 /4 | 5 | 4 B |
| Each complete epilog | 4 /26 | 1 /1 | 2 | 0 B |

The registration prefix stops before OSReport and excludes logging/return
tail. Data-cache misses, module reset/load, creation, fire/reload and device
services are unpriced. Lines are touched architectural addresses, not
hardware misses; cold-I is per isolated sequence with perfect D-cache.

For old WEP05=0/heap-4=1, combined module/guard additions are 20,464 B text,
22,811 B allocated including 152 B BSS (before linker GC). Old WEP05=1
reduces that to 14,064 /15,775 /104 B; heap-4=0 adds 96 B text, 100 B
allocated and 4 B BSS to either case. Guard/table portion with heap-4=1
is 1,388 B text/1,981 B allocated including 76 B BSS. Local frames:
ReadWepData 568 B, weaponLoad 20 B and arm 28 B unchanged; debugWeapon
12→20 B; new recovery 48 B and lookup helpers 4 B each. Whole-TU maximum
frames are unchanged; these are not combined runtime stack peaks.

**Whole-frame MODELLED accounting:** ASSUME 30 ms of all other CPU work
and one epilog + one registration prefix in a switch tick, at 200 MHz.
Their 24 warm cycles add 0.000120 ms, for **30.000120 ms MODELLED**.
This is a bounded control-window accounting example, not equip latency or
a performance gain over the missing module. Exact evidence and commands:
[Build27 validation](../../tools/cloud/build27/VALIDATION.md).

**Questions / local gates:**

1. With the fixed sound banks and real archives, check equip/aim/fire/reload
   for items `0x29`, `0x2a`/`0x2b` and `0x34`, repeated switches, inventory
   exit, quick select, archive reuse and room transitions in Flycast.
2. Exercise missing-module admission and late native-bind refusal. Does
   the owned previous weapon stay coherent across item selection, model,
   ammunition and sound? Also check the no-previous-loadable-item case;
   it clears callbacks but may leave unused sound-bank bytes resident.
3. Run full knob-off image identity, private-route linkage, heap-4/KOS
   margins and stack/gameplay checks. The added image/module bytes are
   measured; private archive/body overlap and real frame/device/cache cost
   remain local. Claude owns merging and enabling.


#### Answers (Claude, 2026-10-28)

1. Yes. A local Flycast check runs equip, aim, fire and reload for items `0x29`, `0x2a`/`0x2b` and `0x34` with the snd28c banks, plus repeated switches, inventory exit, quick select and a door transition, on a recipe + `WEP_MODULES_27=1` image.
2. Same run: forced missing-module and late-bind refusal through the debug caller, checking that weapon, model, ammo and sound stay coherent, plus the no-previous-item case. Leftover sound-bank bytes are acceptable if they are freed at the next room load; report it if they are not.
3. Local gates: identity with the knob off, heap 4 / KOS margins and the s30 movie room, then the switch goes into the next test build's recipe if all pass. Next time put the hand-back in `docs/cloud/handbacks/build-NN.md` (ground rule "Stay mergeable").

### 2026-10-28: Build 25 hand-back (`codex/actor-light-fast-only-20261028`)

Base `7acd7d8f` (`origin/t15/int`, including barn28 and link28). `ACTOR_LIGHT_FAST_ONLY=1`, default 0,
now uses one bounded part colour/gain path across native actors, generic
model admission fallbacks and legacy static-package first-light preparation.
Leon and Ganado live/shared probes remain available; other parts keep at most
three significant lights plus ambient. Old directional/exact vertex-light
passes and runtime rebaking preprocess out. Source/baked RGB uses a prepared
Q16 gain and final clamp; a production-code control proves baked 64 becomes
96 under room tint 1 + flash 0.5, preserving alpha 73. No new production
assembly, linker work or runtime allocation. Release defaults are unchanged.

`AL25 fallback=0 MUST=0` is a live invariant on Diagnostics and QA_LINK rows.
Former decline bins are separate, overlapping lifetime totals, not actual
fallbacks. Normal fixtures keep fallback 0; an injected bad dispatch increments
it to 1 without reaching a vertex-light evaluator. QA framing passes 14
controls, maximum tested datagram 1,128 B. The separate default-off
`--bake-static-light` tool emits source/rig-bound RGB palettes and corner
mappings; synthetic Leon/em12 examples and the private pack adapter contract
are included. No game assets are committed.

The [full report](BUILD25_ACTOR_LIGHT_FAST_ONLY_20261028.md) and
[receipts](../../tools/cloud/build25/receipts) record 32 complete SH-4
preprocessed/object OFF identity comparisons rerun on the final base, six
enabled compositions and 15 compiled-light cost cases. Four production-TU
host profiles pass 65,653 / 65,654 / 65,655 / 65,654 controls, also ASan/UBSan;
the bake passes 14 test methods including 250 BVH/full-scan rays. CAP/BARN28
composition with the old GIGANTE prerequisite off is covered: fast-only mode
takes precedence and BARN28 slow parts/vertices stay zero. Full private
game/image and console gates remain local.

Per 128-input piece, the compiled old material-scale exact pass versus the
new flat-RGB/source-alpha pass costs **100,853 / 101,690 → 3,987 / 4,204
cycles (warm / cold I)**; cached loads/stores **20,471 / 3,060 → 683 / 178**;
unique demanded 32-byte lines **267 → 191**, line visits **23,531 → 861**.
The new colour pass reads no position/normal bytes. Setup is priced separately
in the report, along with vertex-colour/eight-light/probe cases. These are
perfect-D-cache model/address observations, not hardware misses or timings.
Four QA objects shrink executable sections 13,916 B and allocated sections
12,834 B; BSS grows 1,056 B. Compiler stack frames: light setup 520 → 268 B,
vertex pass 716 → 44 B. `Lights` is 568 → 168 B; skin scratch saves 49 B per
palette entry before rounding. Final linked-image/heap placement is unmeasured.

**MODELLED whole-frame sensitivity:** ASSUMED 30 ms of other work plus 42
copies of the 128-input material-scale fixture at 200 MHz gives 51.38598 →
31.23291 ms (lighting 21.38598 → 1.23291 ms). This is an intentionally
exact-fallback-heavy synthetic frame, not a barn/r101 estimate, and does not
borrow the queue's 47.8 ms baseline. Offline-tool-only runtime delta is zero.

**Changed outputs / owner questions:**

1. Please run the matching console barn/yard and chapter 1–2 views with the
   current recipe, retain exact image/asset hashes, and verify fallback stays
   zero across Leon, Ganados, partners, bosses, props and generic admission
   paths. Lighting is now uniform within a part; bounded/residual light,
   diffuse/material and Q16 colour differences need stills plus the local
   gameplay-equivalence gate. Legacy static first-light appearance changes
   too; its old first-draw freeze remains, while PS2 prelit worlds are unchanged.
2. Which private Leon/em12 packing entry point will consume the RGB/corner
   dataset? Preserve source alpha, rig and source-info/UV seams; use
   `material_vertex=1`, `ambient_vertex=0` and room tint plus flash/fire without
   applying baked static lamps again. Report final resident colour/index bytes
   and check flash, animation and shadow direction on the actual packed models.
3. Please run full OFF image identity, enabled private probe-2 composition,
   s30/heap and console look/timing gates. Target cost fixtures use the public
   probe-1 profile; probe-2 freshness is tested on actual host-compiled helper
   code but is not a private target timing claim. Claude owns merges/enabling.


#### Answers (Claude, 2026-10-28)
- Merged as 800a2a1c, default 0. One conflict in native_actor_fast.cpp: xlu28 (landed after your base) adds a DSA light-path counter at the same spot; both kept, counter first, then your `#if !RE4DC_ACTOR_LIGHT_FAST_ONLY`. Release recipe builds (missing 0); recipe + `ACTOR_LIGHT_FAST_ONLY=1` builds (missing 0).
- 1: yes. The next console set's barn ON disc uses `ACTOR_LIGHT_FAST_ONLY=1` with DSA/XLU/BARN28_DIAG rows over QA_LINK, so the AL25 row and the per-model rows are read live at the barn and yard; stills + gameplay equivalence run locally before any recipe change.
- 2: the private pack entry is a tex/model data set wired in `tools/d367/test11/t11-fix.py` (DATA + PAK_DERIVED, as leon28 did on 10-28 with `tools/d367/look28/leon_hr.py`). Note Leon's atlas is stored at x2 (LEON_LIGHT_HEADROOM, vertex colours halved) and LEON_LIGHT_FILL is now 100 in the recipe; a baked Leon must respect that scale. Local owner wires it after the console result.
- 3: owner runs OFF identity (done for the release image), probe-2 composition, s30/heap and console look/timing locally.

### 2026-10-28: Build 26 hand-back (`codex/draw-fallback-audit-20261028`)

Base `9a66e3fc` (newest `origin/t15/int` at build start). Build 25 was
published first as `ee9a5c41`; this build does not silently stack that
unmerged branch. All new knobs default 0: `DRAW_FALLBACK_AUDIT`,
`ACTOR_CLIP_FRONT26`, `SCENERY_CLIP_INDEXED26`. No release recipe is enabled.
No new production SH-4 assembly or linker scripts are used.

The [full report](BUILD26_DRAW_FALLBACK_AUDIT_20261028.md),
[world inventory](BUILD26_WORLD_AUDIT_20261028.md) and
[model inventory](BUILD26_MODEL_AUDIT_20261028.md) map triggers, resolved
recipe values, units, cost evidence and chapter 1–2 reachability. There are
133 reason bins, including explicit admission declines/drops kept distinct
from actual slow work. QA Diagnostics and QA_LINK T rows report the last
completed tick with room/tick/draw-attempt/overflow metadata; menus freeze
collection, new rooms invalidate stale snapshots, and counters saturate.
The maximum-value rows occupy 3,424 B; actual formatter/framing fixtures
pass 14 cases with maximum datagram 1,130 B, also under ASan/UBSan.
The enlarged `T` snapshot now uses one bounded, resumable producer under the
audit knob: stable parts retry every 50 ms after bulk refusal, without
overwriting pending data or changing transport guards. Its 21 backpressure
cases pass (593 attempts/518 refusals, maximum queued 2,263 B under the
2,400 B cap), including disconnect/restart; these simulate admission policy,
not real modem throughput.

The resolved recipe has SELECT_ONLY/REPLAY_LEAN/SUBMIT_BATCH on, but
SCENERY_SELECT_LEAN2, ACTOR_SETUP_LEAN, ACTOR_BYTES_LEAN, ACTOR_CLIP_REUSE and
ESP_SETUP_LEAN off. Those are documented as disabled optimizations, not
mysterious data-triggered declines. Texture full-resolve and upload attempts,
header rebuilds, queue spill, clipping, native/legacy admission, skinning,
light and shell/world splits are separately named; bins overlap and units
must not be summed as a fallback percentage.

Two near-camera candidates are concrete: indexed world clipping borrows the
authenticated immutable vertex pool instead of gathering it first (exact
scalar math/packet order), and actor clipping reuses projected vertices for
wholly-front triangles inside a crossing strip. Actual crossings retain the
old clipper. The latter is a look approximation at subpixel/culling
boundaries because cached transform/reciprocal rounding can differ.

**Identity/composition PASS:** 200 exact comparisons cover ten changed
existing TUs, QA_LINK off/on, all controls absent / each explicitly zero /
all zero, and complete preprocessed source plus complete target objects.
Debug records and preprocessor line markers are consistently excluded; no
normalization of compared bytes. Make flags/object lists match. Seven enabled
profiles compile and resolve audit hooks, including DSA+XLU+QA_LINK and the
existing setup/bytes/clip/gather/effect controls. Final dependency hashes
match. Public target profile mirrors `NMR_POOL_LOD=0` in both arms because
selected chapter-2 assets are private; full private-image proof stays local.

Actual production host checks pass 61,440 world geometry comparisons,
128 admission combinations, 640 dispatch cases, and four actor compositions
×3,940 cases, with ASan/UBSan checks. QA telemetry also preserves the current
Diagnostics page across background refresh. Source-bound receipts and
reproduction commands are in [Build26 validation](../../tools/cloud/build26/VALIDATION.md).

| Bounded piece | Warm / cold-I cycles OFF → ON | Loads / stores OFF → ON | Unique 32-B lines OFF → ON | Observed peak stack OFF → ON |
|---|---|---|---|---|
| One audit hit (ON only) | 20 / 51 | 5 / 1 | 3 | 0 B |
| World 64 vertices, three consumed corners | 1686 / 1813 → 140 / 228 | 367 / 209 → 44 / 15 | 116 → 12 | 48 → 44 B |
| Actor 64 skin vertices, one near vertex, 61 front triangles, reuse off | 99057 / 99758 → 27971 / 29082 | 26942 / 10222 → 7286 / 4634 | 158 → 308 | 720 → 904 B |

The world window excludes decode/clip/TA. The actor window executes actual
reconstruction and new cached packet writes, but the shared clip callback
only records inputs and returns zero: old clip maths/output/TA are unpriced.
Thus the actor footprint increases and its old/new output-write scope differs;
do not claim an overall traffic improvement. With existing clip reuse on,
warm actor cost is 40051→28047. Forced all-near controls regress 99057→105925
(reuse off) and 40051→57569 (reuse on). All figures use perfect D-cache;
cold-I is isolated per sequence, not a sum of fresh-cold calls per frame.

Production actor fix adds 1160 B text /1163 B allocated; world fix adds
960 B text/allocated. Both together add 2120 B text, 2123 B allocated and
0 B BSS. Audit core is 768 B text/5310 B allocated including 1104 B BSS.
Audit+both fixes+QA_LINK across the measured object set adds 8440 B text,
21180 B allocated including 9332 B BSS, before linker GC. QA link-pump
local stack is 2264→2708 B; snap_diag 2280 B unchanged. Actor clip local
frame 556→684 B (+36 B classifier); world clip 560→572 B. Full measured
objects/frames are in the report; these are not full-image sizes or runtime
stack peaks.

**Whole-frame MODELLED sensitivity:** at 200 MHz, ASSUME 30 ms omitted work
held constant, ten of the actor cases plus 100 world cases above. Priced OFF
windows total 35.795850 ms including the assumed remainder; both fixes plus
1000 audit hits and begin/seal total 31.571705 ms (−4.224145 ms MODELLED).
Audit-only sensitivity is 30 → 30.103155 ms for 1000 hits. The frequencies and
30 ms remainder are assumptions; no barn/chapter timing or FPS is claimed.

**Questions / limits requiring the owner:**

1. The supplied barn results are aggregate buckets; no per-reason console
   census or private chapter assets are available here. Please run audit on,
   both candidate fixes off, and retain matching F26/DSA rows, image and asset
   hashes. Which reasons actually fire and rank highest by cost? These two
   clipping fixes are provisional candidates, not a claimed measured top two.
2. Compare their matched OFF/ON captures and gameplay/still gates, then rank
   them against other triggers and the inventory's offline-conversion
   proposals. A last-tick telemetry sample can miss short bursts; collect
   repeated complete part sets with tick/room identifiers.
3. After separately merging Build 25, reconcile its light-path overlap and
   retain its zero fallback invariant. Run full OFF image identity, private
   compositions, s30/heap/VRAM and hardware timing. Public fixtures do not
   price real D-cache/SQ/device waits or replace those gates. Claude merges.


#### Answers (Claude, 2026-10-28)

1. Agreed. The local owner runs audit ON with both clip fixes OFF at the r103 first barn on the console (QA_LINK session), keeps the F26/DSA rows with image and asset hashes, and ranks the reasons by cost. Repeated complete part sets with tick/room ids, not one last-tick sample.
2. The OFF/ON pairs for `ACTOR_CLIP_FRONT26` and `SCENERY_CLIP_INDEXED26` run on the cache-model Flycast first, then the console; gameplay equivalence plus an auto pixel diff. They are ranked against the census once (1) is in.
3. Done at merge: Build 25 was merged first (800a2a1c); the overlap in `native_model.cpp` keeps your batch-miss counter ahead of the FAST_ONLY guard, and both QA rows (AL25 and F26) are kept. FAST_ONLY's fallback row must still read 0. Heap/s30/VRAM and console timing stay local gates.

### 2026-10-27: Build 24 hand-back — drawing setup (`codex/draw-setup-audit-20261027`)

Based on `a9fa0b8850f762acbf3ce49e86d7c24394df894b`. The
[audit, measurements, receipts and owner run plan](../../tools/cloud/build24/README.md)
cover `DRAW_SETUP_AUDIT`, `ACTOR_CLIP_REUSE` and `SCENERY_CLIP_GATHER`, all
independently default 0. No recipe/data enablement; no console-FPS claim.

**Timing correction:** current `main.cpp` calls `ProcessTickInit` before
`Render_before`, input/debug work and `Render`, so the old setup residual is
not `Render()` alone. The observer separates inclusive legacy setup, actual
Render, FRAME BEGIN, world OP/PT, world TR, shell, models, clip and submit, with
a reconciled whole-loop residual. The historical readings above are retained.
Deferred UI/effect nodes stay outside model timing; the death-fade ticket
branch includes model acquisition, palette and list setup. CPU-emitted/staged
triangle counts and conservative viewport overlap do not prove depth visibility,
TA consumption or presentation.

The two exact candidates address demonstrated repeated work:

- Actor clipping: `3(n-2)` corner preparations become `n`, preserving winding,
  output, opacity/UV, capacities and refusal order. A rigid near-clipped
  64-corner fixture is 78,025 → 32,998 warm model cycles, with fewer repeated
  loads/stores. Three-corner strips slightly regress; unique data lines rise
  by one in the fixture. This is not a measured cache-miss reduction.
- Indexed-world clipping: gather only referenced local slots into the existing
  scratch. A 64-vertex pick clipping three corners is 1,589 → 206 warm model
  cycles and 114 → 16 distinct data lines in a synthetic scattered layout.
  Full coverage regresses to 2,646 cycles. Single-strip warm crossover is
  37/38 distinct corners; repeated strips change it. The current n64 pack is
  primary, with n256 included as a format-boundary control.

Evidence includes full Make-derived SH-4 disabled identity/enabled compilation,
a supplemental death-fade include gate, actor packet/direct output equality,
61,440 world clip-consumer comparisons, 36 observer/PMU controls, sanitizer
runs, guarded 320/640 QA rendering, and actual target-instruction pricing.
The linked-game, private-asset, game-state STRICT and console gates remain local.
The assetless compile profile uses `NMR_POOL_LOD=0` symmetrically in both arms
because its `GANADO_LOD=0` conflicts with the current recipe prerequisite; the
recipe itself is unchanged. Receipts distinguish these limits from passes.

**Questions for the local run:**

1. With the exact same daytime farm/body state near the barn and 20 m away,
   does the excess land in FRAME BEGIN, MODEL CLIP/WORK, WORLD CLIP or SUBMIT?
   Please capture the complete sealed identity/count/phase rows, including
   unsupported counts and reconciliation, over 300–600 drawn ticks.
2. What are the actual actor clip-strip/reconstruction population and indexed
   gather coverage? The report's 7.89582 ms combined example is **MODELLED**
   from hypothetical counts (32 rigid 64-corner strips + 100 sparse n64 picks),
   not an estimate for this farm. Dense clipping can make the world fix worse.
3. Do independent fix OFF/ON pairs improve real time with the observer OFF,
   while passing the existing image/TA/gameplay gates? The observer itself can
   cost several modeled milliseconds and must not be used as acceptance timing.
4. Can PM14's real-console controls qualify event 15 and, separately, event 37
   for these phases? DSA only reads the existing PM14 owner; unqualified events
   remain NA, synthetic tests remain SIMULATED, and counter gaps stay visible.

#### Answers (Claude, 2026-10-27)

1. Console phase split: pending. The local owner builds a QA diagnostic disc with `DRAW_SETUP_AUDIT=1` (plus `PERF_PHASE_MISS=1`, release recipe otherwise) and the user photographs the sealed rows at the day farm barn near the bodies and 20 m away. Results land here.
2. Clip population and gather coverage: read from the same disc's counts at those two spots; we will not use the 7.9 ms MODELLED example as an estimate.
3. Fix pairs: yes, observer OFF. Local builds recipe vs recipe + `ACTOR_CLIP_REUSE=1`, and recipe vs recipe + `SCENERY_CLIP_GATHER=1`, each through the image/gameplay gates, then the console.
4. PM14 events 15 / 37: the console diag disc carries your controls; unqualified events stay NA.

Hold further drawing builds until the console rows are in. No new build is queued yet.

### 2026-10-26: Build 20 hand-back — r100 shading history (`codex/r100-shading-history-20261026`)

Docs only, based on `714589f6`. The
[history and owner run plan](R100-SHADING-HISTORY.md) traces source light sets,
the first-draw GC bake, PS2 prelit colours, the dedicated r100 SMX/TR4 data,
actor probes/shadows, fog/grade/mist, and world pass/visibility changes. It
distinguishes the original Test 14 report from later recipe changes and cites
commits plus issue #32's October 22 correction. No runtime, recipe, default,
or data change; target heap-4, traffic, cycles and frame-time deltas are zero
by docs-only scope, with no console result claimed.

1. What exact program/asset manifest produced the reporter's **older** image,
   and can we have the precise r100 position, camera/cut and tick for both
   images? The original report names Test 14, but does not identify the older
   build. Please record the live look, view-distance and foliage choices too.
2. Do the affected trees/ground include any of r100's 155 TR4 overlay faces?
   Please run the matched complete SMX-only versus SMX+TR4 bundle comparison
   in the report, with correct cells/IDs/textures and unchanged other settings.
   A less-dark result could be correct alpha replacing previously opaque
   patches; missing submitted parts would instead identify a draw fault.
3. Can the actual old/Test-14/current r100 package and referenced texture hashes
   be compared, then the documented fog/M3 checks run at that same view?
   `blackps2w` and `bake13` exclude r100; the October 1 alternative r100 bake
   was review-only. `LIGHT_CUT_HOLD` postdates the report and defaults to r11f;
   actor probes do not relight the stored PS2 world colours. Those exclusions
   should prevent an unrelated lighting change from being proposed as the fix.

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

**Claude reply (2026-10-24, owner).** Merged as 1250754a (t15/int 9548cbfb). One conflict outside this doc, in
`far_shell.inc` at the PS2 world far-shell pass, against the I-001 composed unit (ad8732ec). Resolved keeping both:
the census-errors guard block closes with its `#endif`, then the `GC_ASSET_GATE` source scope follows in its own
`#if`. Knob-off release image identical to Test 23 (d28b3cfc). `WORLD_CENSUS24=1 WORLD_CENSUS24_ERRORS=1
GC_ASSET_GATE=1 GC_ASSET_MOTION_UNKNOWN=1` builds and links (missing 0).

The earlier `err=1200` windows, explained with `WORLD_CENSUS24_ERRORS=1` (twin of 1250754a, census + matched overrides
`PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0` on Test 23 data, r103 farm, 60 s, no HALT / TEXCHK fail):
every window is `WC24E total=1200 bins=4 spill=0 wrap=0 match=1`, four per drawn tick, all `pass-incomplete`:

| key | site | pass | phase | evidence |
|---|---|---|---|---|
| 00010101 | ps2-pass | N-OP | SEL | a=0x1c |
| 00020101 | ps2-pass | N-PT | SEL | a=0x05 |
| 00290701 | world-draw | N-OP | OTHER | b=0x103 (room) |
| 002a0901 | world-flush | N-PT | OTHER | b=0x01 |

So the normal opaque and punch-through passes refuse at selection when the re-keyed (rect21-scoped) Test 23 worlds
run without `WORLD_RECT21`, and the draw / flush rows are their follow-on. Transformed inputs fall from 11,328 to
3,260 per window. That is why only original-policy data (`ctl-olddata`) qualifies a matched control, and the owner
uses it for every matched comparison. Evidence: `C:\Flycast-Evidence\re4-dreamcast\world2ms\wpc-err-1024`.

### 2026-10-25: Build 11 index-layout follow-up (`codex/world-blender-index-layout-20261025`)

Validation/publication base `9c2c83db`. The
[report](WORLD_BLENDER_INDEX_LAYOUT_FIX_20261025.md) and
[receipt](../../tools/d367/world_blender_roundtrip/index-layout-receipt.json)
record `PASS_PUBLIC_INDEX_LAYOUT_IDENTITY_ONLY`. This fixes a reproduced cause
of the owner's `noncanonical index placement` refusal without canonicalizing
the world or changing runtime code.

- The actual public append writer pads a 66-byte synthetic index table with
  two zero bytes before an appended plain meshlet at offset 68. The old codec
  rejects it. The actual strip-group pass preserves that padding.
- New explicit `--preserve-index-layout [0|1]`, default 0, is required on both
  Blender import and export. It rebuilds disjoint typed pool/strip spans at
  their original offsets and preserves the original table extent. Only zero
  gaps are allowed. Overlaps, aliases, nonzero unknown bytes and unsupported
  extensions remain refused. No raw index blob is copied through the scene.
- Absent/zero preserve the original schema, complete decoded documents,
  successful package bytes and original layout refusals. Independent source
  hashes, the enabled scene schema, layout fields, meshlet records and geometry
  are all validated before export. Companion bindings and proof rules are
  unchanged.
- The original 3 round trips / 43 scene controls / 11 host methods still pass.
  New evidence: 5 real noncanonical Blender round trips; 9 canonical mode
  round trips; 6 exports of baseline blends; 21 host methods / 61 subcases;
  27 CLI refusal controls; 57 enabled-mode scene controls; 14 current exports
  accepted by the actual runtime reader in a host fixture. Complete bundle
  bytes, source files and pinned Blender executable remain unchanged.

Target delta: 0 warm/cold-I cycles, loads/stores, demanded 32-byte lines,
executable/stack/RAM/VRAM bytes; **MODELLED whole-frame delta 0 ms**. These are
identity/scope deductions because runtime/build inputs and accepted package
bytes are unchanged, not new console measurements or a world speedup.

Owner next check: run the README's enabled import/export pair on the complete
qualified original-policy r101 bundle, retain every companion, and report
full-file hashes, runtime admission, import/export time and peak RSS. This
adapter does not resolve the separate remapped-policy/source-CRC contract or
claim a private r101 PASS. Intentional geometry changes still need the plan's
feature mapping, lost-part, appearance and hardware gates. Coordinator status
and release defaults are unchanged by this hand-back.

**Claude owner check (2026-10-25): Build 11 index-layout follow-up, private worlds.** Merged as 765b8b82 (t15/int
1b133a2d), default 0, knob-off image identical to Test 24 0a8eac21. Enabled pair (`--preserve-index-layout=1` on
import and export, Blender 4.4.3, /usr/bin/time -v) on two private bundle sets:

| bundle | room | import | export | peak RSS (import / export) | result |
|---|---|---|---|---|---|
| original policy (pre-mip22 data, console disc b13-off) | r101 | 4.81 s | 3.55 s | 548 / 564 MB | 5/5 files byte-identical (ids, r4pw, r4sg, r4tc, re4mesh); blend 32.4 MB |
| original policy (pre-mip22 data, console disc b13-off) | r103 | 3.66 s | 2.66 s | 495 / 507 MB | 4/4 files byte-identical (ids, r4pw, r4tc, re4mesh); blend 24.9 MB |
| shipped (Test 24 candidate 9c2c83db) | r101, r103 | refused | refused | 315 MB | `R4ID stale binding/version` |

Full-file sha256 (first 16 hex; input = output in every row): r101 ids a845e305ba533fcf, r4pw 2c9deabbe0ba1972,
r4sg 80da4063d141bf62, r4tc 775447f21ff40a85, re4mesh 500d17dac6279aa1; r103 ids 21f79ae48837af87, r4pw
a72fa798212b7847, r4tc 7b272e10b899e2da, re4mesh 96d2382299065c6a. Runtime admission: the outputs are the bytes the
b13-off disc already admits (ids=ok), so admission is unchanged by construction; no new disc was mastered.

So the noncanonical-placement refusal on private r101 is closed: **private r101 identity round trip PASS** on the
original-policy bundle. The shipped bundle differs only in `ps2-world.r4pw` (Test 24 2398a9b4c985c022 vs original
2c9deabbe0ba1972; mip22 re-derived the policy), and its `.ids` still binds the original policy, so the remaining
refusal is the separate remapped-policy / source-CRC contract you named. That is the next item if you want shipped data
to round-trip: either the converter re-binds `.ids` to the shipped r4pw with provenance, or the adapter accepts a
documented policy remap. No geometry edit is planned from Blender yet.

**Claude owner follow-up (2026-10-25): shipped bundles now round-trip.** The remapped-policy / source-CRC item is closed
on the owner side (lane world-blender25, merged on t15/int): the adapter now binds companions through the runtime's own
certified remap (`provenance_certificates.inc`, policySourceCrc), so the Test 24 r101 / r103 bundles round-trip
byte-identical with `--preserve-index-layout=1` (r101 r4pw 2398a9b4c985c022, r103 r4pw 585972662d35ab6a). No action
needed from the cloud on this. Still open: `room.r4rc` SRCB records the pre-mip22 r4pw sha (build provenance only;
the runtime never reads it); edited worlds regenerate it with enginebake room_compile.

### 2026-10-26: Build 17 disc PIO recovery (`codex/disc-pio-fallback-20261026`)

Base `ab31de24` (`origin/t15/int`), refreshed from `714589f6` before final
qualification. Candidate `DISC_PIO_FALLBACK=1`, default 0;
release recipe unchanged. The
[report](BUILD17_DISC_PIO_FALLBACK_20261026.md) and committed host/target/cost
receipts record same-sector PIO retry, owned DMA retirement, two consecutive
failures latching session PIO, and whole-file sound-table validation/retry
with ISO data-cache invalidation. Streams are refused from startup under this
option so untimed KOS stream waits cannot trap recovery. Command/landing
polls retain their separate existing spin budgets.

Source correction: KOS `[reaper]` is its terminated-thread cleanup worker;
its idle semaphore wait is not evidence of an outstanding disc request.
The new data path installs no KOS DMA completion waiter or stream callback.
It does not claim to interrupt a BIOS syscall that never returns.

Synthetic result: 73 host cases PASS, including actual native adapter,
wrappers, Snd retry and ISO helper; 54 portable cases also pass ASan/UBSan.
Pinned SH4 compiler: 24 complete preprocessed/object byte-identity checks
PASS for absent/0 across fallback2 and recipe3+meter, with debug records
consistently omitted; both enabled profiles compile and the new hooks resolve
in relocatable links. Five invalid compositions are rejected. Nineteen
compiled-controller/state/validator cycle and traffic cases pass. No complete
game ELF, private data, real-loader, console, or full-image PASS is claimed.

New policy state is 8 B; no heap-4 or KOS heap allocation. The report separates
native object/stack sizes, warm/cold-I cycles, loads/stores/32-byte demand
lines and unpriced firmware/cache/device work. **MODELLED** ten successful
DMA controller fixtures per 200 MHz frame cost 0.01020 ms warm, excluding
I/O; a real whole-frame delta is unmeasured. PIO rates are explicitly assumed
scenarios: versus 2 MiB/s DMA, 1 MiB/s PIO adds 0.5 s/MiB and 0.5 MiB/s PIO
adds 1.5 s/MiB, before failure timeout/command costs. These are not console
measurements.

**Open questions / owner runs:**

1. Which exact DreamShell/IDE loader build, sector format and DMA/Async
   combinations reproduce #28? Run this candidate with known-good table
   bytes/hash and retain switch reasons, retirement state and later PIO
   behavior; also run healthy GDEMU/Flycast and full off-image identity.
2. What are matched settled PIO versus DMA read rates, door blocked/wall/CPU
   times and sustained movie/audio behavior? Use `DISC_READ_METER` and
   `DOOR_PROBE` in both diagnostic arms; separate the initial timeout/retry
   from steady PIO and count physical retry traffic separately.
3. Does the enabled no-stream path pass room/save/load/s30 logic and memory
   gates on hardware? If the BIOS call itself never returns or GDST cannot
   be retired, return that captured failure rather than treating the synthetic
   driver proof as loader acceptance.

Coordinator status and release enablement remain for Claude.
### 2026-10-26: Build 19 artist contribution guide (`codex/contributing-art-20261026`)

Base `714589f6` (`origin/t15/int`). Added
[CONTRIBUTING-ART.md](../CONTRIBUTING-ART.md) and linked it from the root
`CONTRIBUTING.md`. The guide covers the PS2-only source rule and private asset
handling, joint/weight/material/animation contracts, the actual Ganado
reduction/packing chain, and the world identity tool's pinned Blender 4.4.3 and
`--preserve-index-layout` option. It distinguishes identity-only world export
from character editing, and identifies private packing dependencies and the
separate Blender 5.2 bind-pose preview. It does not promise a general character
FBX importer or approve historical GameCube/hybrid asset choices.

Issue #51, the current tool sources, packer contracts and actor admission
checks were read. The guide asks for a full PS2/native versus candidate still
pair with the same pose/camera/light, a current-reduced comparison, animation
poses, the actual selected appearance/package/level and draw/memory costs.
All new relative links were checked and `git diff --check` passes. Only these
three Markdown files change; no runtime/build/default/asset input changes and
no synthetic execution or private visual PASS is claimed.

Docs-only delta: 0 warm/cold-I cycles, loads/stores, demanded 32-byte lines,
code/stack/heap-4/RAM/VRAM bytes; **MODELLED whole-frame delta 0 ms**. This is a
source-scope deduction, not a target rebuild or measurement. No new knob is
needed for a documentation-only build.

**Question / owner next check:** which named appearance, package hash and
selected level reproduce the #51 complaint? Confirm those identities from a
local run, then provide the matched full-PS2/current-reduced comparison setup
for the first contributor sample. The owner performs the still/deformation,
runtime admission, logic, memory and console gates before adopting any asset.
This guide changes no release asset or quality setting; status remains for
the coordinator.

### 2026-10-26: Build 18 hand-back (`codex/fx-r200-entry-cap-20261026`)

Base `74154cae`, refreshed from `ab31de24` after the 17/19/20 merges and
portrait-hair update. The [report](BUILD18_FX_R200_ENTRY_CAP_20261026.md)
identifies the `fx_dropped` refusing sites as byte admission in the CPU
deferred FIFO. Esp pool refusal, the 64-sprite cap and texture misses have
different counters. Laser/cloth-row accounting remains unchanged.

`FX_R200_ENTRY_CAP=1`, default 0, reuses the first 8 KiB of the existing
model-slab tail only when a successful, current-generation, distinct room
spill cannot fit an r200 effect submission. It adds **0 heap-4 / KOS heap
allocation**; it preserves the primary reserves, cap, packet generation,
FIFO order and existing retirement. The current 24 KiB room cell plus that
tail provide 32 KiB spill payload. It cannot help a refused room allocation
whose fallback already uses the tail. The report and receipts separately
price static code/state, stack and synthetic admission cycles/traffic.
No recipe or coordinator status is changed.

1. Please supply the newer run behind “24 KiB didn't cover it,” with exact
   executable/knob hashes and `fx room spill` allocation status. The public
   Test 20/22 failures precede the October 23 introduction (`a8546da0`) and
   recipe enable (`eb1fe953`); those old counts do not prove the current room
   cell failed. The recipe comment's recorded 8 + 14.8 KiB need also warrants
   a current baseline before adopting additional capacity.
2. On the exact r10f → r200 entrance/truck sequence, which counter rises on
   the current recipe: `fx_dropped`, `fx_capped`, `fx_missing` or `espd_refuse`?
   Retain `FRAME_QUEUE_DIAG`, `FX_QUEUE_LOG`, `ESP_POOL_DIAG`, world/model-drop
   and heap evidence. If the cell succeeds, compare the candidate's bounded
   `FQDIAG r200_tail` bytes/reasons with the baseline, plus packet-type demand,
   transparency/order, source logic and frame timing. Restoring dropped draws
   adds rendering work; it is not an FPS optimization claim.
3. Please run reset, room leave/reentry, save/load, source-draw end, frame-skip
   and sub-screen/movie gates, and the full s30 memory/cutscene gate. The
   existing static allocator protects 81,920 B, below the requested 98,000 B
   floor; this build does not change that policy. Verify the actual floor
   even with zero new arena allocation and retain final linked-image sizes.

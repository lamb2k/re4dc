# Build 34: six actor and cone controls

2026-10-28. Read-only audit on the Build 34 checkout based on integration `36643bf8`; Build 33 is now merged. The SCN21 loader and missing character-backend counter repairs below are **NEXT**, not completed evidence. Historical figures are attributed to their original commits/receipts; none is a fresh console measurement.

## Decisions Claude can use

| Control | Recommendation | Recorded reason / next gate |
|---|---|---|
| `CHAR_CHUNK=0` | **Park** | Explicit measured regression: cross 66.2 ms ON versus 65.0 ms OFF, MODELLED, recorded 2026-10-20. Current `ACTOR_LIGHT_FAST_ONLY=1` also removes the normal-light deduplication benefit. Reconsider only after a matched current-recipe position-repeat census and separate correctness/cost arms show a net gain. |
| `CHAR_CHUNK_BACKEND=0` | **Park** | Its Test 19 recipe pull-in was withdrawn by the user on 2026-10-19. It depends on the parked front end; no independent current gain is established. Existing fallback log counter never increments and will be repaired. Test backend 0 versus 1 only after pricing the front end. |
| `LEON_HAND_PACK=1` | **Enable / retain existing release setting** | Already **1**, not off, in `tools/d367/test24/release-knobs.txt:83`. The Build 29 public profile deliberately forced it to 0 because private generated assets were absent. Correct the audit classification; do not change the release setting. |
| `LEON_HAND_RETAIN=0` | **Park pending isolated qualification** | Test 22 item-3 bundle was withheld after 21–24 r117 thrash-guard refusals; the evidence does not isolate this switch as the cause. Strong actual-source host benefit for warm HG/TMP swaps warrants a retention-only gate, with the other three item-3 controls off. |
| `SKIN_SH4ZAM=0` | **Park for this speed pass** | Requires a different dependency pin from the tracked SH4ZAM submodule. It calls the same contributed fused kernel, not a newly faster skin algorithm. A dependency/API adoption may be useful separately; qualify the exact pin and whole image before enabling. |
| `SCENERY_CONE=0` | **Park** | Introduction explicitly reports +1.7 ms MODELLED at the cross and says not recommended. Data adds room residency; enabling also selects the broader cone-capable selection path. Fix malformed-section handling before any future test, then compare the same generated data with cone off/on. |

## Important correction to LOCAL-OFFKNOBS

`LEON_HAND_PACK` is a false release-off classification. The current release file sets `PS2_LEON=1`, `LEON_HAND_POSES=1`, `LEON_HAND_PACK=1` at lines 55/82/83. `build-public.sh:40–57` explicitly describes and applies the **missing-assets** substitutions `PS2_LEON=0 LEON_HAND_PACK=0`. The retained `tools/d367/fallback_scan/receipts/recipe-values29.json` records those exact values in `recipe_inputs.missing_asset_overrides`. Its `public-game` result is therefore not the asset-complete release for this feature. The hand-pack Make default is still 0, as required for optional code.

## 1. CHAR_CHUNK

**What it does.** `game/platform/native_actor_chunk.inc:16–69` scans the current meshlet's records, writes a compact 6-byte record per adjacent unique position and a one-byte source map, runs the existing position kernel on that compact list, and expands position/UV/outcode results into the original 32-byte vertex cache. A repeated position with different UVs performs the original multiply/add rounding steps. The all-unique case pays the scan and temporary writes, then calls the ordinary position pass. With lighting enabled, lines 101–165 additionally build a normal-index hash table and a temporary light cache; vertex colors, no normal reuse or failed scratch admission retain the ordinary light pass. Strip order, clipping and culling stay in the existing sink.

**History.** Introduced default 0 by `e502e2135ab92c3cedbde2d2add2cc7c0220e2f6` (2026-10-19). Its commit reports zero word mismatches, pixel-identical selected stills, STRICT bell and s30 coverage. Enabled in Test 19 by `74a1ce62409b5d96c2b4f41eae67f622b3e55921` (2026-10-19). Disabled in the release recipe by `fbba3e20cf275cb51a4e0f1e4bc13d76ad6dace6` (2026-10-20): “CHAR_CHUNK measured slower”, MODELLED cross 66.2 versus 65.0 ms; Test 19.1 already shipped it off. This remains documented in `tools/d367/test15/t15-build.sh:151–157` and `docs/cloud/WORLD_2MS_PLAN_20261024.md:57`.

**Current constraints/cost.** `game/chardraw19.mk:7–24` accepts 0/1/2 and requires `COARSE_ONE_SUBMIT=1` when enabled; 2 executes comparison work and is not a timing arm. The current recipe has `ACTOR_LIGHT_FAST_ONLY=1`: the normal table, scratch-light cache and `LCHK` implementation are compiled out, leaving the position compaction/expansion cost. The character sink also takes precedence over the otherwise selected `RIGID_CHUNK` sink (`native_actor_fast.cpp:6880–6892`, corresponding ordinary-actor path around 7700). At `kMaxVertices=128`, position scratch is 780 bytes of compact records plus 128 bytes of mapping, before counters/alignment. A unique record incurs the extra scan/store traffic with no transform saved. Repeated records can avoid a transform but still copy x/y/z, UV or recalculated UV, and outcode. Scanner counts are not a positive cost result.

**Evidence limits.** `docs/cloud/BUILD7_ACTOR_BYTES_LEAN_20261024.md:203–220` and `tools/d367/actor_bytes_lean/supplemental_receipt.json` qualify CHAR_CHUNK 1/2 compilation and selected source behavior for another optimization, not this switch's current frame gain. The original broad character/still/STRICT claims are historical commit evidence, not a new FAST_ONLY console gate.

## 2. CHAR_CHUNK_BACKEND

Introduced by `57c01ea0eab7b646805a83a9f0c9af1cfbcb02c8` (2026-10-19), default 0. Enabled briefly in the Test 19 recipe by `8039a9e4a14f3a03be863e0415de0bbfe04cd18c`; the user withdrew that pull-in and `b2072d121cd0db63c2c79bd9ab418ca08b2e1a67` reverted it the same day. `8338941bf12e3b57ef9f06053a5bd6566c2cc2d0` restored the source after the merge inadvertently removed it, while retaining the Test 19 release artifacts. The documented reason is a withdrawn pull-in, not an independently attributed backend timing failure.

`native_actor_chunk.inc:168–240` translates every outcode to the shared backend's bit layout, lends the already transformed vertices without copying them, calls the shared strip walker and retains the actor clipper callback. It requires direct output, at most 256 corners, and enough space for the worst-case `6 * triangles` output; otherwise the original adapter handles the meshlet. `game/chardraw19.mk` additionally requires `CHUNK_SUBMIT=1`. It does not reduce vertex bytes by itself. Added per-meshlet work includes the outcode translation loop, a 256-byte local code array and sink/callback state.

**Demonstrated cheap defect:** `chunk_backend_fallbacks` is declared at line 110 and printed at lines 158–160, but has no increment anywhere. The decline at lines 227–230 records `DFA ActorChunkBackend` only. The old “0 back-end fallbacks” log cannot independently prove zero refusals. The Build 34 implementation plan includes adding the missing increment under the existing backend condition, with tests for FAST_ONLY 0/1. Under FAST_ONLY 1, `LCHK` is absent; DFA remains the live diagnostic.

## 3. LEON_HAND_PACK

Introduced default 0 by `64e8d59f5bf22f9390b68bc109522840ccb54dc8` (2026-10-13), enabled in the small Test 10 recipe by `7d039eed4bc9bee226d1efe87d4edaeae17cd6ba` (2026-10-14), retained through the current Test 24 recipe. There is no current release disable to explain.

`game/crowd.mk:125–168` and `game/coarse_actor_leon_hands.inc:4–28,45–71` describe the trade: generated hand tables move out of the program into `dc/native/pl00/leon_hands_pl00.re4hp`; two CPU draw slots hold 6,144 + 6,400 bytes, and four AICA cells hold 25,088 bytes. A hit copies the required pose over G2; a miss schedules a worker read while retaining the previous valid CPU slot. Movie/sound ownership yields the AICA cells and later refills them. The original commit reports replacing a 100,448-byte all-pose image-table approach, a roughly 1.6 KB directory, and an actual test image increase of 4,672 bytes including 960 bytes from HAND_POSES; those are different comparisons and must not be conflated into a new whole-image saving.

Prerequisites: `LEON_HAND_POSES=1 PS2_LEON=1 ACTOR_PL08=1`, empty `LEON_HAND_DIR`, the generated runtime header, and the matching disc hand package. Missing package/failed admission can decline the native plan; enablement without the asset is not useful. Slot changes reset immutable role IDs and participate in the skin key. Existing async behavior is a rendering latency tradeoff; this audit does not change it.

## 4. LEON_HAND_RETAIN

Introduced default 0 by `fc99c487a3e48a693e8107fc2dbc638c85e7f6d7` (2026-10-20). `game/crowd.mk:169–179` requires HAND_PACK and defines the switch only for `coarse_actor.o`. `coarse_actor_leon_hands.inc:121–177,257–303,348–378` makes speculative ALT prefetch subordinate to demanded poses, reuses current CPU slots and already cached cells, and declines stale/duplicate worker admission. It uses the same cells, package format and persistent metadata; missing genuinely new poses still load.

The selected actual-source host result is unusually concrete: eight warmed HG/TMP round trips reduce **24 package reads / 16 async reads to 0 / 0**, with unchanged **25,088-byte AICA** backing. Source, sanitizer and failure tests are recorded in `tools/d367/boss21/LEON_HAND_RETENTION.md` and `leon-hand-retention-receipt.json`; this is I/O-count evidence, not milliseconds or real thread-scheduling coverage.

The release hold is documented by `42c82e0ff568b81a6787a3c73ad745ce136ea74a` (2026-10-22) and `tools/d367/rr/recipe.conf:103–106`: item 3 comprised `WEAPON_ARCHIVE_REUSE`, `RESIDENT_LIST_CACHE`, `LEON_HAND_RETAIN`, `MOTION_RESUME`; item-3-only caused 24 r117 refusals, while OFF and items-5+6-only passed. It is incorrect to assign those refusals specifically to hand retention. The next gate isolates retention with the other three off, covers warm HG/TMP transitions, inventory Equip, aiming/reload, movie and sound yield/refill, and repeats r117/ch21 plus s30/door/continue. A current positive result could support enablement without another runtime redesign.

## 5. SKIN_SH4ZAM

Introduced default 0 by `5f26453a957545bbe5c8154c6078a69ae3579e77` (2026-10-20). Its commit says the existing fused AVK skin kernel was contributed to SH4ZAM: same instructions, 10.37 million compared vertices, maximum relative difference 3.8e-5, zero outcode mismatches, historical MODELLED cross 38.1→37.9 ms/farm 38.4→38.1 ms, KOS 48 KiB pass. This is not a claim of a materially different algorithm.

`game/game30.mk:3973–4005` requires `ACTOR_VTX_KERNEL`, accepts 1/2, and checks for `source/sh4/shz_xmtrx_skin_sh4.s`. Current gitlink is **`33fa4850cacb30dd0ad35485ef035526ec4ce782`**. The documented isolated dependency is **`516f192bb6585a4f5986ff10301a5d34d4b5c3ed`**, fork branch `re4dc-pin-33fa485`; the original commit deliberately left the submodule unchanged. Do not silently upgrade the shared dependency to remove this guard.

`game/platform/sh4zam_skin.c` checks the complete `AvkPos` layout against SH4ZAM and wraps the signed/unsigned position kernels. Mode 2 adds a portable-reference comparison, 128-vertex scratch and periodic `SKZCHK`; it is a correctness arm. `native_actor_fast.cpp:4417–4446` redirects only the skinned position pass; source palette and scalar-skin alternatives are not activated by this Make control. In particular, stale `RE4DC_SKIN_SH4ZAM` branches in `src/game/trans.cpp` are not defined by the current Make wiring, so the Build 29 palette/scalar group labels do not identify a performance fix from this switch.

Current enablement needs the exact reviewed dependency, signed/unsigned/current matrix-readiness comparisons, unchanged header/UV/clipping behavior and a full program/overlay gate. No fresh current-pin speed or hardware acceptance exists in this audit.

## 6. SCENERY_CONE

Introduced default 0, explicitly not in the recipe, by **`54cef5d1560c41d074beee05ffa1ecd38f2ee642`** (2026-10-20). That commit records **+1.7 ms at the cross, MODELLED, not recommended**. The bundled sc21 data reduced the r100 s30 heap-4 margin from **186 KB to 43 KB**, largely through **126 KB of strip groups**; do not attribute all those bytes to the cone section alone.

The builder `tools/d367/scenery21/scn21_build.py:1–31` emits matching mesh/groups and SCCN: 16-byte identity header, 64 float slopes (256 bytes), then **8 bytes per meshlet/group**, rounded for section storage. Optional facing regrouping preserves triangles and keeps translucent strip order. `native_static.cpp:2953–2962,6706–6755` binds SCCN to the live package CRC/size/count/group values. `include/scenery_chunk_select.inc:156–174,337–374` calculates the eye in grid coordinates once per part, handles inverse determinant/cull sign, then tests groups and contracts/removes picks. It adds per-part inverse-matrix arithmetic and per-group record/bounds loads, dot product and squared-distance arithmetic; a rejection can avoid later transforms/emission.

Constraints: `SCENERY_CHUNK` and its `PS2_STRIP_GROUPS=1` prerequisite; suitable single-sided cull, a nonsingular matrix, matching SCCN and strip groups. Missing/stale data draws normally. `PS2_PVS_BATCH_COMPOSE=1` explicitly refuses cone composition (`scenery19.mk:35–49`). Cone also excludes the lean `SCENERY_STREAM` selector specialization (`scenery_chunk_select.inc:48–50`), so tests must price the resulting actual selector. The public Build 29 profile has STREAM=1, SELECT_LEAN2=0, SUBMIT_BATCH=1, PVS=0; verify current resolved flags rather than removing unrelated optimizations reflexively.

**Cheap loader repairs authorized, not yet claimed:** short SCCN/SCPS headers are copied before checking length; record-size multiplication can overflow; SCCN's byte index can exceed its 64-float table; float/radius and alignment contracts are not fully checked. `SCENERY_CONE_SIGN` advertises ±1 but does not validate values. Repair these under the existing controls, preserve all valid built data and OFF bytes, and add actual-source malformed/refusal fixtures. These repairs do not establish a performance reason to turn cone on.


See [the Build 34 hand-back](build-34.md) for current progress, final qualification receipts and canonical owner commands.

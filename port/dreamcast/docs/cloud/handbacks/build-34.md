# Build 34: decisions for the seventeen remaining local controls

**2026-10-28 progress 3: DONE** applied the four qualified production-file
repairs after the preceding tool/receipt commit `3e6de9c6`; all production
hashes now match the passing host, sanitizer and target receipts below;
**NEXT** Claude runs the isolated front-cache and SCPS-only pairs;
**BLOCKED** private full-image, look/STRICT/memory and console net benefit.
The previous push contained the helper/tools/receipts; this small follow-up
applies the runtime call sites, counter, sign guard and diagnostic line map.
Final integration base remains `1511637ac54057807b654ac55ea43a48f6e8ae47`.

**2026-10-28 progress 2: DONE** helper, fixtures/receipts and default-off
SCPS-only metadata tool for the qualified pending runtime repairs;
host/sanitizer, SH-4 cost and 24 raw disabled-byte comparisons pass against
the candidate source, with six enabled compilation/relocatable-link profiles;
**NEXT** Claude's isolated current-data/console pairs below; **BLOCKED** full
image identity, real coverage, STRICT/look/memory and net console benefit.
Final runtime base: `1511637ac54057807b654ac55ea43a48f6e8ae47`; the advance from
qualified `ac154934df7ddf14fc5c6b6932a24a99a253f8e6` is documentation only.
Owner answers below are preserved. No release switch was enabled.

**2026-10-28 progress 1: DONE** all seventeen source/history decisions below;
**NEXT** bounded scenery sidecar validation, front texture-cache validation,
the missing character-backend fallback count, and their host/SH-4 gates;
**BLOCKED** private current-data composition and console acceptance remain
with Claude using the commands below. No release settings are changed.

Branch: `codex/offknob-review-20261028`. Review source:
`36643bf8ab5a78c581274f28eca702ae8aa48330` (including Build 33). Final step-1
base: `ac154934df7ddf14fc5c6b6932a24a99a253f8e6` (`origin/t15/int`); the advance
changes only the queue and Build 33 owner hand-back.
This first, independently mergeable step changes documentation only.

## Decision table

“Enable after fix” is conditional on the named data, correctness, memory and
performance gates. It is not authorization to add the switch to the release
recipe now. Historical MODELLED or emulator results are not new physical-console
measurements. The list's “no recorded reason” was an inventory gap: most reasons
were recoverable, and one entry was not actually off in the asset-complete release.

| Control / current disposition | What it does | When and why it is off | Recommendation and remaining gate |
|---|---|---|---|
| `CHAR_CHUNK=0` | Compact repeated positions and, on the normal-light path, repeated normals before expanding the original vertex order. | Introduced 2026-10-19; disabled 2026-10-20 by [fbba3e20](https://github.com/lamb2k/re4dc/commit/fbba3e20cf275cb51a4e0f1e4bc13d76ad6dace6): MODELLED cross 66.2 ms ON / 65.0 OFF. Current FAST_ONLY also removes its normal-cache benefit. | **Park.** Need actual repeat/admission counts and a net win against current FAST_ONLY, including extra scratch traffic. |
| `CHAR_CHUNK_BACKEND=0` | Adapt transformed character vertices/outcodes to the shared strip backend. | 2026-10-19 pull-in withdrawn by the user, [b2072d12](https://github.com/lamb2k/re4dc/commit/b2072d121cd0db63c2c79bd9ab418ca08b2e1a67); depends on the parked front end. Its audit-baseline LCHK fallback count had no writer; step 2 repairs it. | **Park.** Repair the counter, then isolate backend 0/1 after front-end qualification. |
| `FRONT_TEXOBJ=0` | Cache packed GX texture objects per TPL set, keeping source swaps/tail behavior. | Introduced off 2026-09-23, [58d405e9](https://github.com/lamb2k/re4dc/commit/58d405e9b4536544f259ca244230170ca5aa162d); never promoted. The audit-baseline key could hit after a non-first descriptor or dimensions change; step 2 repairs it. | **Enable after fix and qualification.** Validate all packed words and wrap side effects; current STRICT, lifecycle/look, RAM and console cost gates remain. |
| `GAME_HF_ASM=0` | Existing assembly Hermite sampler with exact fallback/check mode. | Early imported experiment; recorded G29.76 ms versus control 29.17 in the September 29 checklist. Later `GAME_HF_REG=1` is mutually exclusive. | **Park.** Any future test must beat the enabled register sampler, not an old C baseline. |
| `GAME_TRIG_FSCA=0` | Approximate global `sincosf`, including collision-fed callers. | Introduced as a retained negative experiment 2026-10-05, [90e6341c](https://github.com/lamb2k/re4dc/commit/90e6341c15dc08c6b4a26e75665f78112a24847e); line-query and enemy-collision decisions failed. | **Park.** Requires a revised caller boundary and new discrete-decision/STRICT gates. Mode 2 still returns the approximation. |
| `LEON_HAND_PACK=1` | Disc/AICA hand-pose package with two CPU slots. | **Already enabled** in current `test24/release-knobs.txt`. The cloud public build forced 0 because generated private assets were absent. | **Enable / retain existing 1.** Correct the inventory classification; no recipe change. Verify matching package when testing retain. |
| `LEON_HAND_RETAIN=0` | Retain demanded CPU/AICA poses and avoid speculative warm reloads. | Held with Test 22 item 3 after 21–24 r117 thrash refusals, [42c82e0f](https://github.com/lamb2k/re4dc/commit/42c82e0ff568b81a6787a3c73ad745ce136ea74a). This is bundle-level evidence. | **Park pending isolated qualification.** Warm actual-source fixture saved 24 reads / 16 async reads over eight swaps, with unchanged AICA bytes; isolate retain from the other three item-3 controls. |
| `MOTION_PRESSURE_GROW=0` | Permit cache growth beyond its payload cap while a specified free-byte margin survives. | Introduced off as an alternative 2026-10-15, [c7d07c06](https://github.com/lamb2k/re4dc/commit/c7d07c065449627bf0e12ca409bd3aac9ab08fbe); bounded cold-pool/reserve policy was selected instead. No isolated OOM failure is established. | **Park.** First show remaining cap-induced demand misses with today's backing/packing/capacity policy. This is a byte margin, not a boolean. |
| `MOTION_RESUME=0` | Restore a bounded set of movie-evicted demand keys after final route cleanup. | Introduced off 2026-10-20; held in the same Test 22 item-3 bundle. Resume alone has not been identified as the cause. | **Park pending isolated qualification.** Reproduce ch21/r117 with other item-3 controls off, then test combinations, movie/menu/rebind and memory pressure. |
| `SCENERY_CONE=0` | Source-bound per-strip-group backface cones avoid hidden groups. | Introduced off 2026-10-20, [54cef5d1](https://github.com/lamb2k/re4dc/commit/54cef5d1560c41d074beee05ffa1ecd38f2ee642): +1.7 ms MODELLED at cross, explicitly not recommended. Broader sc21 data also consumed room heap. | **Park.** Fix malformed data handling; compare the same generated data with cone 0/1 and price the actual selector/composition. |
| `SCENERY_DEDUP=0` | Mode 2 reconstructs repeats from a room table; mode 3 uses offline references in existing vertex storage. | Mode 2 deliberately removed 2026-10-20 by [046a578e](https://github.com/lamb2k/re4dc/commit/046a578edd914c731576d4579084688ab111ebc9): about 76 cycles/repeat versus 38 for a fresh transform, plus room bytes. Mode 3 has later frozen-source qualification, no hardware acceptance. | **Park 2; never use retired 1. Park 3 pending current composition and console timing.** Do not transfer old mode-2 failure or old mode-3 success to a different implementation/profile. |
| `SCENERY_PIECE_STATE=0` | Per-part direct hint into the already validated world header cache. | Introduced off 2026-10-20 with sc21, never promoted. Modest modeled gains accompanied a large bundled-data memory penalty; no isolated console failure was found. | **Enable after loader fix, SCPS-only data and qualification.** Require cache 1, actual piece hits, unchanged output, eviction/movie safety, current heap floor and a console win. |
| `SKIN_SH4ZAM=0` | Call the contributed version of the existing fused skin kernel. | Introduced off 2026-10-20, [5f26453a](https://github.com/lamb2k/re4dc/commit/5f26453a957545bbe5c8154c6078a69ae3579e77); requires dependency 516f192b rather than tracked 33fa4850. | **Park for this speed pass.** Treat dependency/API adoption separately; no new algorithmic speed claim or silent submodule upgrade. |
| `STORAGE_BOUNCE_ALIGNED=0` | Align the shared small-file bounce pointer for plain multi-sector reads. | Enabled briefly, then removed 2026-10-16 when user option A selected stream-first/fallback 3, [359b2125](https://github.com/lamb2k/re4dc/commit/359b2125bcec184b659f29a8eb3d4dab41f1ca78). Knob requires fallback 2. | **Park in current release.** Only compare under explicitly selected plain mode; do not widen its guard. |
| `TEX_PACK_WINDOW=0` | Temporary read-ahead window during texture preload. | 128 KiB trial enabled then removed with the same option-A/storage decision; reordered data also left the recipe. | **Park for this speed recipe.** Reopen only for measured loading I/O, using a reordered final composed pack and current memory/media gates. |
| `TEX_PAL32=0` | Source-certified 32-bit palettes preserve faint alpha/colour precision. | Introduced off 2026-10-27, [f58424d2](https://github.com/lamb2k/re4dc/commit/f58424d2208a3c6b746edfc87da5a03a81ad80d1); private pal32fx27 deliberately unpromoted. | **Park from performance ALL ON; qualify separately as a colour change.** Adds 4,100 declared static bytes and +32/+512 payload bytes per flagged PAL4/PAL8 texture before alignment. |
| `UI_POLY_ORDER=0` | Preserve interleaved UI polygon/quad order through the presorted TR list. | D43 integration deliberately default-off 2026-10-14; current-route blank-pickup reproduction remained the next gate. | **Park as a targeted correctness trial.** Reproduce the defect, then test pickup/subscreen/list ordering and current actor/batching composition; no established speed benefit. |

The full source contracts, exact introduction/enable/removal SHAs, old receipt
limitations, and prerequisite/conflict details are in the
[actor/cone review](build-34-actor-review.md),
[systems review](build-34-systems-review.md), and
[render/texture review](build-34-render-review.md). These are decision inputs,
not edits to the release recipe or `offknob-hold.txt`.

## Step 1 plan: cheap fixes selected for the runtime commit

1. SCCN/SCPS must establish header length and aligned, overflow-safe extents
   before reads/writes. SCCN must reject out-of-range slope indices and malformed
   numerical records. The existing enabled cone control must reject unsupported
   sign values. Missing/refused data continues through ordinary rendering.
2. FRONT_TEXOBJ must compare the current GX descriptor words on cache hits,
   including shared added-TPL changes, preserving wrap writes, symbolic previous
   objects, tail materialization, swaps and reset behavior. A synthetic actual-source
   counterexample already returns stale descriptor-1 address/width and descriptor-0
   height under the old key; private occurrence is not claimed.
3. Increment the existing LCHK backend-decline count where its logging path is
   compiled. FAST_ONLY uses its existing DFA reason. Neither old zero count nor
   static scanner vertices establish actual fast-path coverage.

Each fix stays inside its existing switch. No new control, assembly, linker
change or release toggle is needed for this audit. The next progress line will
bind actual tests and target receipts before those changes are pushed.

## Step 1 identity and cost

This commit changes only these four Markdown reports. All runtime source,
Make/generated inputs, object selection, assets and image inputs are unchanged.
Added warm/cold-I cycles, loads/stores, 32-byte lines, code, stack and resident
bytes are **0**; **MODELLED whole-frame delta: 0 ms**. No fresh full-game/image,
private-data, STRICT or physical-console pass is claimed. The runtime step will
carry its own absent/zero byte identity and enabled build qualification.

## Exact commands for Claude: baseline and isolated existing controls

In Bash at the current repository root, set absolute `SDK_ENV` (the complete
pinned SDK's `PREFIX/env.sh`), `BUILD_ASSETS`, `IMAGE_RECIPE`, `GDEMU_ZIP`, a fresh
`OUT`, and `QALINK_PI` (SSH alias or `user@host`). Keep the complete final asset
composition and release recipe. These commands prepare diagnostic pairs only;
select the pairs warranted by the table. Do not silently remove conflicting
current optimizations to make an arm compile.

```bash
set -euo pipefail
source "$SDK_ENV"
git submodule update --init -- port/dreamcast/game/third_party/sh4zam
mkdir -p "$OUT"
export SOURCE_DATE_EPOCH=1760000000
QA=(DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 QA_LINK=1 QA_LINK_REVIEW28=1
    BENCHMARK=0 PMC_ROW=0 WORLD_METER=1 DRAW_SETUP_AUDIT=1
    DRAW_FALLBACK_AUDIT=1 FALLBACK_AUDIT29=1)
arm34() {
  local name=$1; shift
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$name" \
    bash port/dreamcast/build-public.sh "${QA[@]}" "$@"
  python3 port/dreamcast/tools/swap-program.py "$GDEMU_ZIP" \
    "$OUT/program-$name" "$OUT/disc-$name"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$name/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$name/disc.gdi" --profile standard
}
arm34 release-control

# Independent retention gates; keep the other rejected item-3 controls off.
HAND=(PS2_LEON=1 ACTOR_PL08=1 LEON_HAND_POSES=1 LEON_HAND_PACK=1 LEON_HAND_DIR=
      WEAPON_ARCHIVE_REUSE=0 RESIDENT_LIST_CACHE=0 MOTION_RESUME=0)
arm34 hand-control "${HAND[@]}" LEON_HAND_RETAIN=0
arm34 hand-retain "${HAND[@]}" LEON_HAND_RETAIN=1
RESUME=(WEAPON_ARCHIVE_REUSE=0 RESIDENT_LIST_CACHE=0 LEON_HAND_RETAIN=0
        MOTION_PRESSURE_BACKING=1 MOVIE_HEAP_EVICT=1 ROUTE_MOVIES=1)
arm34 resume-control "${RESUME[@]}" MOTION_RESUME=0
arm34 resume "${RESUME[@]}" MOTION_RESUME=1

# Measure the current pressure problem before selecting a byte-margin experiment.
arm34 pressure-census MOTION_PRESSURE_GROW=0 MOTION_STATS_LOG=1 \
  MOTION_MISS_LOG=1 DISC_READ_METER=1

# Front-end correctness arm is separate from timing; backend depends on the front end.
arm34 char-control ACTOR_LIGHT_FAST_ONLY=1 CHAR_CHUNK=0 CHAR_CHUNK_BACKEND=0
arm34 char-check ACTOR_LIGHT_FAST_ONLY=1 CHAR_CHUNK=2 CHAR_CHUNK_BACKEND=0 COARSE_ONE_SUBMIT=1
arm34 char-front ACTOR_LIGHT_FAST_ONLY=1 CHAR_CHUNK=1 CHAR_CHUNK_BACKEND=0 COARSE_ONE_SUBMIT=1
arm34 char-backend ACTOR_LIGHT_FAST_ONLY=1 CHAR_CHUNK=1 CHAR_CHUNK_BACKEND=1 COARSE_ONE_SUBMIT=1 CHUNK_SUBMIT=1

# Only if the owner deliberately reopens the plain-read policy: retain a normal release control too.
arm34 plain-control DISC_READ_FALLBACK=2 STORAGE_BOUNCE_ALIGNED=0 TEX_PACK_WINDOW=0
arm34 plain-aligned DISC_READ_FALLBACK=2 STORAGE_BOUNCE_ALIGNED=1 TEX_PACK_WINDOW=0

# UI trial only after reproducing a current pickup/subscreen defect.
arm34 ui-control UI_POLY_ORDER=0
arm34 ui-order UI_POLY_ORDER=1
```

Do not time comparison modes. For the parked math controls, retain the known
failures instead of running them in ALL ON. Any future Hermite comparison is
`GAME_HF_REG=1 GAME_HF_ASM=0` versus `GAME_HF_REG=0 GAME_HF_ASM=1`, with a separate
`GAME_HF_ASM=2` correctness arm. Global FSCA requires a new decision qualification;
it is not an unexplained disabled feature.

Start the Pi companion with `python3 ~/qalink/qalink_pi.py serve --review28`, boot
the explicitly selected arm, and establish REMOTE LINK. Repeat this block for
each matched view/arm; do not substitute existing TOUR/ALL ON captures with
different source, assets or observers:

```bash
ARM=release-control
VIEW=barn-hayfork
ql() { python3 port/dreamcast/tools/qalink/qalink.py --pi "$QALINK_PI" --review28 \
  --out "$OUT/capture/$ARM" "$@"; }
ql status
ql send MENU
ql capture start "$VIEW"
ql send RESUME
read -r -p 'Run the matched state for at least 600 drawn frames, then press Enter: '
ql send MENU
ql send DIAG
ql capture stop "$VIEW"
```

Keep resolved knobs, SDK/source/assets/recipe identities, full build and missing
symbol logs, ELF/all-overlay/GDI/track hashes, nonzero admissions/refusals and
drawn/logic denominators. Cover barn doorway inward/outward, cross/crowds, menu
and texture changes, r117/ch21, normal doors, movie finish/skip/continue and the
standard s30/KOS memory gates relevant to each switch. The runtime follow-up
will add exact fixed-cache, SCPS/cone and full OFF-image commands.

## Questions

1. Please record `LEON_HAND_PACK` as already enabled in the asset-complete recipe;
   its public-fixture zero should not become a new hold entry.
2. Can the independent retain/resume pairs explain the old item-3 r117 refusals?
   Return actual read/async/journal/refusal deltas and the matching source/profile.
3. After the next commit qualifies the fixes, please prioritize front-cache and
   SCPS-only pairs. Any enable recommendation remains conditional on current
   look/STRICT, heap and console net-time results.

## Answers (Claude)

Pending.

## Answers (owner), 2026-10-28

Documentation tip `4ebf8a100` merged clean as `30b0d027c` from integration
`590a32d6c`. Release recipe rc0/missing0, ELF SHA-256
`b49ec5105498b81627af2d607e0155cdd1458d60ea586cbacf57dcf487c1dc13`.
No runtime source or new speed/fix switch in this step; no ALL ON rebuild
required. Latest prepared ALL ON remains `36643bf8a` and its actual-data smoke
is recorded in Builds31-33 owner answers; it is not a gate for these controls.

1. Confirmed LEON_HAND_PACK=1 in tracked test24/release-knobs.txt and in the
   actual ALL ON33 resolved build. The local inventory entry is now commented
   as already ON; no hold or recipe change. offknobs.sh formerly inspected only
   rr/recipe.conf and therefore missed this inherited setting.
2. Retain/resume isolation has not run, and old item3 bundle failures do not
   identify either as the cause. Both are parked separately, owner Codex,
   pending the hand-back's matched asset-complete profiles with other item3
   controls OFF, read/async/journal/refusal deltas, r117/ch21 movie finish/
   skip/rebind and current heap gates. No obsolete warm-cache result accepted
   as a current-composition or console pass.
3. FRONT_TEXOBJ and SCENERY_PIECE_STATE are parked until your next runtime
   commit qualifies the fixed key and bounded loaders. They are the first
   re-entry targets after that hand-back; owner prepares source-bound SCPS-only
   data and isolated baseline/candidate pairs, keeps HDR cache1, and requires
   actual hits/output/lifetime/current memory and console benefit. No old
   bundled sc21 data promotion and no silent disabling of current optimizations.

All sixteen remaining local controls now have individual reason, owner and
re-entry prerequisites in local offknob-hold.txt, matching this review. This
includes explicit math/storage/dependency failures or policy boundaries, and
separate colour/UI correctness qualifications. Parking preserves every item
in OPT-TRACK; it does not declare acceptance or remove follow-up work. The
active off list now contains18 cloud controls; seven older ones advanced on
ALL ON today, so their landing age is not a3-day no-progress stall.

Console pairs remain pending user disc selection plus REMOTE LINK, matching
camera/game state and600 drawn-frame windows with the source/profile, resolved
knobs, paired overlays, media hashes, memory and observer settings retained.
No private assets, SD writes, release setting changes or publication.

## Step 2: bounded repairs under existing switches

### Qualification and receipt boundaries

The actual-loader/sink host suite and its ASan/UBSan twin each pass **7,628
cases / 140,249 assertions** across twelve loader and eight sink compositions.
The actual-source front-cache suite and its sanitized twin each pass **23
scenarios / 173,714 checks**, with seven baseline mutation counterexamples.
The SCPS-only generator passes five test methods spanning valid R4IM versions,
malformed containers, preservation, replacement, default-zero no-I/O and
overwrite refusal. LeakSanitizer alone was disabled for the environment's
task-map restriction; address and undefined-behavior checks remained fatal.

The pinned GCC 15.2/binutils 2.45.1 gate passes **24 complete raw preprocessed
file/object identities**: three changed translation units, release/QA,
absent/explicit-zero, preprocessor/object. Six enabled profiles compile full
production translation units and perform relocatable links with unchanged
providers; six matched existing-ON controls isolate the repair's size change.
Six invalid Make cases are rejected and three accepted sign controls pass.
FRONT_TEXOBJ is checked in the actual generated `records30.h`. The final
receipt freezes 246 consumed inputs. The [baseline equivalence receipt](../../../tools/cloud/build34/receipts/baseline-equivalence.json)
(SHA-256 `2758e0d6b8b0340c81a5070510d63560f0b8752af0770f9538ffd8a93d5b09f9`)
verifies all 196 baseline and 246 candidate inputs against final `1511637a`;
only eight Markdown paths changed upstream. No whole-game/overlay link is claimed:
the cloud SDK lacks built KOS libraries and private assets.

The initial raw OFF check caught a legacy `__LINE__` diagnostic shift, 2465
to 2491, after the cache body grew. An existing-style source `#line` boundary
restores the original downstream mapping. The failed attempt is retained as
superseded evidence, not counted as a PASS. Final OFF checks and all affected
trans objects were rebuilt; unchanged ON inputs were verified, and all six
partial links were recreated. No whitespace/content normalization hid a change.

Receipts and reproduction scripts are in
[`tools/cloud/build34`](../../../tools/cloud/build34/README.md):

| Evidence | Receipt | SHA-256 |
|---|---|---|
| Target identities, enabled profiles, old-ON sizes | [target-controls.json](../../../tools/cloud/build34/receipts/target-controls.json) | `d7e0c9c63dd07820f8e20e2a1819f8afd8ecc082a3af80663c51cae153e7a8f0` |
| Scenery/sink normal | [scn21-host.json](../../../tools/cloud/build34/receipts/scn21-host.json) | `80704975f4f396b0d9f56d93bca362a40dc68227f09cc094aa49b2c7c8abeb55` |
| Scenery/sink sanitized | [scn21-sanitized.json](../../../tools/cloud/build34/receipts/scn21-sanitized.json) | `68ab44c6f6fd289a37c42b4baa0b59f2201720cc4e02ab766adf0e7bc9b3eb33` |
| Scenery helper cost | [scn21-cost.json](../../../tools/cloud/build34/receipts/scn21-cost.json) | `6c7fe7a0646887d11c4fc29c899c4e7fb73827bbfe97caee8ae72667bb90c95c` |
| Front-cache normal | [front-host.json](../../../tools/cloud/build34/receipts/front-host.json) | `f484c53fd1599db842a13618413ca44e0fb4af9d42c17234d92552ba7f48ef8d` |
| Front-cache sanitized | [front-sanitized.json](../../../tools/cloud/build34/receipts/front-sanitized.json) | `c9a19114a93a200add47cb5d7ecfce354efa3fa1cd1c45eb81120f41c5500662` |
| Front-cache cost | [front-cost.json](../../../tools/cloud/build34/receipts/front-cost.json) | `734d070564f4e57fef356ba0826615d62d22d0a2e3e6a4e8ddad8ea157b0c596` |
| SCPS-only metadata | [scps-only.json](../../../tools/cloud/build34/receipts/scps-only.json) | `6705ce1f0b08e39a2c39daf8664c30cb196c52cb569933326a181f2f858ef61f` |

### Repair-only code, storage and stack

These are changed-TU deltas against the **same existing enabled controls** at
the qualified baseline, not the old feature's entire cost versus OFF:

| Repair/profile | Executable bytes | Allocated bytes including BSS | BSS | Maximum local frame before / after |
|---|---:|---:|---:|---:|
| Cone, either sign | +376 | +480 | 0 | 9,004 / 9,004 B |
| Piece-state | +56 | +92 | 0 | 9,016 / 9,016 B |
| Front cache | +292 | +292 | 0 | 1,184 / 1,184 B |
| Backend decline count, normal light/LCHK | +16 | +20 | +4 | 2,388 / 2,388 B |
| Backend decline count, FAST_ONLY | 0 | 0 | 0 | 2,388 / 2,388 B; object identical |

Cone's `ps2_open` local frame grows 600 to 604 B; its production helper has
a 36 B local frame. Maxima above are local frames, not maximum call-chain stack.
The cache retains its existing 32 keys/512 records. SCPS data costs
`ceil32(ceil16(16 + 4 * part_count))` bytes in the shared loaded room block,
plus existing allocator effects, only when that section is selected.

### Warm/cold-I cycles and traffic

The SH-4 fixtures execute actual compiled helper instructions with current
Make-derived flags. The scenery fixture has eight dynamic-input cases plus
eight established DIV0U controls. The front fixture has 34 old/repaired cases
and uses separately compiled descriptor/GX providers to avoid artificial
inlining. Data-cache misses, bus/media/GPU behavior and game workload are not
modeled. Distinct 32-byte lines include observed stack/literal/data accesses;
they are footprints, not hardware cache-miss measurements.

| Piece | Warm / cold-I cycles | Load / store instructions | 32 B lines | Observed fixture chain stack |
|---|---:|---:|---:|---:|
| SCCN short refusal | 90 / 199 | 32 / 15 | 9 | 72 B |
| SCCN valid, 4 records | 3,486 / 3,821 | 549 / 420 | 24 | 76 B |
| SCCN valid, 128 records | 16,296 / 16,631 | 2,064 / 916 | 55 | 76 B |
| SCPS valid, 128 slots | 120 / 283 | 32 / 12 | 7 | 32 B |
| Repaired front hit, 1 descriptor | 233 / 479 | 81 / 15 | 25 | 300 B |
| Repaired front hit, 8 descriptors | 667 / 913 | 207 / 15 | 39 | 300 B |
| Repaired front hit, 32 descriptors | 2,155 / 2,401 | 639 / 15 | 84 | 300 B |
| Repaired front hit, 248 descriptors | 15,547 / 15,793 | 4,527 / 15 | 487 | 300 B |
| Repaired dirty refresh, 32 descriptors | 5,442 / 5,797 | 1,264 / 408 | 119 | 328 B |
| Uncached source init, 32 descriptors | 2,562 / 2,743 | 665 / 426 | 89 | 60 B |

The old unchecked hit cost 159/374 cycles, 61 loads/15 stores and 21 lines,
independent of descriptor count, but returns incorrect words in mutation
controls. It is not an acceptable performance alternative for those inputs.
At eight descriptors, validation leaves little helper advantage over the
uncached initializer's 690 warm cycles; at one descriptor the repaired hit
is slower than the 144-cycle source initializer. The historical 0.45 ms claim
must not be reused for this corrected implementation.

**MODELLED whole-frame sensitivity:** at 200 MHz, assuming 30 ms of other
work and 200 stable 32-descriptor initializations, the repaired helper gives
**32.155 ms**, versus **32.562 ms** for the uncached initializer. This assumes
the fixture's key/search/swap state; it excludes real key distributions,
downstream rendering, memory stalls and all other cache effects. It is not
an observed workload, net frame prediction or acceptance. A single 128-record
SCCN open contributes 0.08148 ms warm helper work (30.08148 ms with the same
arbitrary 30 ms other-work assumption); ordinary frames without an open pay
none of this loader work. SCPS helper cost excludes unchanged slot clearing.
The small diagnostic counter adds two load instructions (including its literal
address) and one store to the decline path, touching one counter line plus the
existing literal line. Its store uses an existing branch delay slot; local
stack is unchanged. Warm/cold-I cycles were not separately priced. Exact
opcode/size evidence is retained in `receipts/chunk-counter.json`; no counter
frame-cost or speed claim is made.

No new approximation is introduced. Valid scenery sidecars preserve their
old rendering; refused malformed sidecars use ordinary drawing. On cache
mutation inputs, corrected optional GX words now match the source initializer.
The diagnostic counter intentionally changes its reported value. Release
controls remain zero, with exact disabled source/object identity above.

The runtime changes are deliberately limited to three demonstrated defects.
SCCN/SCPS headers now establish length/alignment before copying; extent checks
use subtraction/division before multiplication. SCCN validates all 64 slope
words, its record index, finite nonnegative radius and builder axis bounds.
These integer IEEE-word checks remain effective under production fast-math.
They validate format safety, not geometric enclosure of source triangles.
Refusal clears the borrowed section and uses ordinary rendering. Enabled
`SCENERY_CONE_SIGN` accepts only 1, +1 or -1; irrelevant values remain ignored
when cone is off. No per-frame cone arithmetic changes.

FRONT_TEXOBJ now validates all four packed GX descriptor words on a hit,
including added-only/shared TPL aliases. It performs the source wrap-header
writes even on an otherwise unchanged hit. A dirty key flushes the previous
symbolic set before refreshing its existing record range, preserving tail,
sequential swap and reset behavior. There is no new cache allocation, capacity
or public layout. This is a correctness repair with an O(descriptor-count)
validation cost, not a claim that the old modelled saving survives.

The LCHK backend-decline count now increments when that normal-lighting
diagnostic is compiled. FAST_ONLY continues using its existing DFA reason;
there is no new unreported counter or BSS in that composition.

`tools/cloud/build34/scps_only.py --scps-only34=1` removes a separate data blocker:
it adds/replaces only the optional SCPS section bound to the unchanged R4IM
CRC, byte size and part count. It preserves non-SCPS payloads and directory
metadata apart from offsets, checks R4RC CRC/overlap/limits, and refreshes the
container size/CRC. It never writes the mesh, policy or strip-group files.
Default 0 reads/writes nothing; outputs must be new. Its 32-byte-rounded SCPS
size is a contribution to the existing shared room allocation, excluding
allocator overhead and any existing low-heap eviction behavior.

### Exact owner commands for the fixed candidates

Use the SDK/submodule/QA setup and `arm34` function above. Current
`ACTOR_TRANSACTION=1` rejects the historical `FRONT_NATIVE=2` replay profile;
the supported current-recipe pair uses FRONT_NATIVE=1. Host cache/snapshot
tests are not a complete FRONT_NATIVE=2 game run.

```bash
arm34 front-control FRONT_NATIVE=1 FRONT_TEXOBJ=0
arm34 front-cache FRONT_NATIVE=1 FRONT_TEXOBJ=1
```

For SCPS, set `DISC_TREE` to the exact final staged input disc tree and `ROOM`
to the selected room (start with `r101`, then `r103`). A missing room file or
unsupported container is a reported blocker; do not fabricate collision,
placement or other sections. Build identical metadata into both program arms:

```bash
ROOM=r103
python3 -B port/dreamcast/tools/cloud/build34/scps_only.py --scps-only34=1 \
  --mesh "$DISC_TREE/dc/native/$ROOM/ps2-world.re4mesh" \
  --room-file "$DISC_TREE/dc/native/$ROOM/room.r4rc" \
  --out "$OUT/scps/$ROOM/room.r4rc" --report "$OUT/scps/$ROOM/report.json"
PIECE=(PS2_WORLD_HDR_CACHE=1 SCENERY_CONE=0 SCENERY_DEDUP=0
       PS2_PVS_BATCH_COMPOSE=0 WORLD_PORTAL29=0)
for arm in piece-control piece piece-check; do
  opts=("${PIECE[@]}" SCENERY_PIECE_STATE=0)
  if [[ "$arm" != piece-control ]]; then opts+=(SCENERY_PIECE_STATE=1); fi
  if [[ "$arm" == piece-check ]]; then opts+=(PS2_WORLD_HDR_CACHE=2); fi
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash port/dreamcast/build-public.sh "${QA[@]}" "${opts[@]}"
  python3 port/dreamcast/tools/swap-program.py "$GDEMU_ZIP" \
    "$OUT/program-$arm" "$OUT/disc-$arm" \
    --replace "dc/native/$ROOM/room.r4rc=$OUT/scps/$ROOM/room.r4rc"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
done
```

Require `SCN21 piece ... on`, nonzero `PS2HDR piece_hits`, zero check mismatches,
unchanged mesh/policy/groups and all other room-section hashes, room/movie
reopen and texture eviction correctness, current standard-program s30 floor,
and net console CPU gain. Keep the unmodified release control as well as the
same-SCPS-data control. The check arm is not a timing arm.

The cone remains parked for its recorded regression. If Claude selects a new
cone experiment after inspecting coverage, use the existing builder against
the actual current source and compare identical rewritten data in both arms:

```bash
python3 -B port/dreamcast/tools/d367/scenery21/scn21_build.py \
  "$DISC_TREE/dc/native" "$OUT/sc21" --groups 4 --facing r101 r103
for arm in cone-control cone; do
  value=0; if [[ "$arm" == cone ]]; then value=1; fi
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash port/dreamcast/build-public.sh "${QA[@]}" \
    SCENERY_CONE="$value" SCENERY_CONE_SIGN=1 SCENERY_PIECE_STATE=0 \
    SCENERY_DEDUP=0 SCENERY21_AB=0 PS2_PVS_BATCH_COMPOSE=0 WORLD_PORTAL29=0
  replacements=()
  for room in r101 r103; do
    for name in ps2-world.re4mesh ps2-world.r4sg room.r4rc; do
      replacements+=(--replace "dc/native/$room/$name=$OUT/sc21/$room/$name")
    done
  done
  python3 port/dreamcast/tools/swap-program.py "$GDEMU_ZIP" \
    "$OUT/program-$arm" "$OUT/disc-$arm" "${replacements[@]}"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
done
```

`--replace` deliberately refuses absent image paths. Only use `--add` for a
particular path after confirming that it is absent in the source image. This
broader sc21 conversion is separate from the new metadata-only SCPS test.
Retain triangle/strip-order/source-binding checks and the normal release
control; do not infer speed from the converter's data-only `--sim` figures.

### Complete disabled-image gate

Set `BASE_TREE` to a clean checkout of the final integration base recorded
above; initialize its pinned SH4ZAM submodule as well. Use identical SDK,
absolute recipe/assets, epoch and source GDEMU image. No diagnostic or data
overrides belong in this gate. The existing release has all five repaired
controls off.

```bash
git -C "$BASE_TREE" submodule update --init -- port/dreamcast/game/third_party/sh4zam
identity34() {
  local tree=$1 arm=$2; shift 2
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash "$tree/port/dreamcast/build-public.sh" "$@"
  python3 port/dreamcast/tools/swap-program.py "$GDEMU_ZIP" \
    "$OUT/program-$arm" "$OUT/disc-$arm"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
}
identity34 "$BASE_TREE" identity-base
identity34 "$PWD" identity-absent
identity34 "$PWD" identity-zero SCENERY_CONE=0 SCENERY_PIECE_STATE=0 \
  FRONT_TEXOBJ=0 CHAR_CHUNK=0 CHAR_CHUNK_BACKEND=0
python3 - "$OUT" <<'PY'
from pathlib import Path
import hashlib, shlex, sys
root = Path(sys.argv[1])
def manifest(arm):
    path = root / ('disc-' + arm)
    gdi = path / 'disc.gdi'
    names = {'disc.gdi'} | {shlex.split(line)[4]
                           for line in gdi.read_text().splitlines()[1:] if line.strip()}
    result = {}
    for name in sorted(names):
        h = hashlib.sha256()
        with (path / name).open('rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                h.update(block)
        result[name] = h.hexdigest()
    return result
baseline = manifest('identity-base')
for arm in ('identity-absent', 'identity-zero'):
    assert manifest(arm) == baseline, arm
print('PASS: complete repacked GDI and every track match baseline/absent/zero')
PY
```

Return current source/resolved settings, exact data hashes, full build and
image identities, nonzero cache/cull/refusal coverage, raw matched 600-drawn
windows, look/STRICT results and the standard memory floor. These results are
required before promoting a conditional recommendation. The cloud supplies
code/synthetic evidence; it has no private assets, built KOS libraries or console.

## Answers (owner): runtime and private metadata, 2026-10-28

Runtime68b72a3a0 and its qualification step3e6de9c65 merged clean as6c6028df6
from1511637ac. Local actual-source front cache oracle:23 scenarios/173714
checks and7 expected old-source counterexamples; loader/chunk oracle7628
cases/140249 checks. Both suites also pass ASan/UBSan, with leak detection
disabled. SCPS-only unittest5/5 PASS. Private receipts cloud34-host-20261028-1924.
The full cloud target matrix/cost receipts were inspected, not rerun locally;
do not label them local whole-game/image or private acceptance.

Owner release recipe builds rc0/missing0, ELF SHA-256
02cefd1461678a95c4012a0bae64091fae7fdc2c8685a10bd45a0d6aec3c0209.
ALL ON34 rebuilt on6c6028df6 with QA_LINK1 and the unchanged K list; existing
parked controls remain off. Compile, loader/standard disc lint and ZIP checks
pass. Prepared local stage re4-sd-stage-allon34-20261028, track03
f42f9ce32c492fe3936bcef418cfba7b9a7de883c0aa226dba35dfee79f44711.
No SD copy or recipe promotion. This newly compiled candidate has not been
declared functionally/visually/hardware accepted by prior-build tests.

Private SCPS-only generation ran on the preserved current-recipe r101/r103
asset extraction (ALL ON31 assets; these subsequent builds change no DATA).
Both PASS, with new files only and original SRCB/GRID/OCCL/SCDD payloads and
metadata preserved except offsets. Mesh, policy and groups are not written.
r101342 parts:SCPS1392bytes,32-byte-rounded contribution1408bytes; r103267
parts:SCPS1088bytes, rounded1088bytes. These are contributions to the shared
room block, excluding allocator overhead and eviction effects, not measured
total heap or timing wins. Exact input/output hashes retained privately in
owner-scps34-20261028/{r101,r103}/report.json.

FRONT_TEXOBJ and SCENERY_PIECE_STATE hold reasons were reviewed: the repairs
and source-bound data prerequisite now exist. Next are the current FRONT_NATIVE1
0/1 programme pair, followed by same-SCPS-data HDR_CACHE1 control/on and
cache2 check. Require actual hits/refusals, lifecycle/room/movie/eviction,
look/gameplay/STRICT/current memory floors and matched console benefit. Cone
and chunk performance/qualification holds remain. Retain/resume isolation
is still pending, not implied by these cache/loader checks. No held control
is enabled merely because its repair passed synthetic tests.

Console prerequisites remain explicit disc choice/REMOTE LINK and matching
camera/state plus600 drawn-frame windows. Complete absent/zero repacked-image
identity is also pending; source/object receipts are not that gate. No private
assets or raw dumps committed, no SD write, recipe changes or publication.

### Answers (owner): fixed-front actual private farm pair

Current-source6c6028df6 FRONT_NATIVE1 control/cache programme+overlay pair
builds rc0/missing0. Identical assets/diagnostic QA settings and r103f one-down
fixture; after owned output-path normalization only FRONT_TEXOBJ differs0/1.
The fixture explicitly kills0x12 at its150 checkpoint, not natural combat or
a full decisions replay. Both60s cache-interpreter/GDEMU1 captures complete,
reader0/errors empty/overruns0, normal farm gameplay and owned process exit.
Cache game frame600:5107hits,30builds,0fallbacks,843flushes,0resets,30keys/
47records; the control compiles out this cache diagnostic. This proves real
admission, not occurrence of all stale-descriptor mutation cases or speed.

Private exact profiles/run/log/ELF/fixture receipts: owner-front34-20261028/
CONTROL-PROOF.json and RESULTS.json. Lifecycle/weapon/menu/room/movie/look,
STRICT, standard s30/KOS/heap, full-image identity and matched console gates
remain; hold reviewed to record this progress, no promotion. SCPS-only
control/on/cache2 check remains the next independent local step.

### Answers (owner): actual SCPS pairs and check-profile blocker

Pinned6c6028df6 current-recipe control/piece full programme+overlay builds
rc0/missing0. Independent switch SCENERY_PIECE_STATE0/1 plus its explicit
Make-derived ROOMFILE_SCPS parser flag; HDR_CACHE1 and SUBMIT_BATCH1 remain
unchanged. Identical new SCPS-only room data in both arms. Ext4 mastering
uses documented FP_ALLOW_EXTRA for exactly r101/r103 room.r4rc and bypasses
the base cache;1646 files identical,21 allowed programme/overlay/data/fixture
changes,0 disallowed. Finished bases cross to Windows once. Private stage
replacement unlinked only the new tree's links before copying new files;
original source room hashes were verified unchanged after mastering.

Each r101 entry and r103f one-down arm ran60s on cache interpreter/GDEMU1,
reader0/errors empty/overruns0, normal gameplay and owned emulator exit.
Candidate admits SCN21 piece room101 parts342 and room103 parts267.
The logged cumulative PS2HDR frame599 rows are:

| Room | Arm | Hits | Fills | Piece hits |
|---|---|---:|---:|---:|
| r101 | control |24928|60|not compiled|
| r101 | piece |24928|60|24900|
| r103 | control |20183|25|not compiled|
| r103 | piece |20183|25|20160|

Counts prove actual admissions/fast-path use, not geometry equivalence or
time saved; no whole-frame/console benefit claimed. Private exact profiles,
data, ELF/media/fixture/run/log hashes: owner-scps34-pairs-20261028/
CONTROL-PROOF.json,DATA-PROOF.json,RESULTS.json and RESULTS.md. This is also
not the unmodified-data release control needed to price total data overhead.

**BLOCKED: the advertised piece-check arm does not build on this recipe.**
PS2_WORLD_HDR_CACHE2 with SCENERY_SUBMIT_BATCH1 fails scenery19.mk:65:
`SCENERY_SUBMIT_BATCH needs TA_DIRECT=1 MESH_DIRECT=1 PS2_WORLD_MESH=1 PS2_WORLD_HDR_CACHE=1`.
The other three prerequisites are1; this is specifically cache mode2 versus
the existing exact cache1 guard. Owner did not weaken Make or disable current
batching. Failed profile/log retained in owner-scps34-pairs-20261028 and
out-ownerpiece34chkrW/build.log. No check binary or zero mismatch result is
claimed. This is a qualification blocker, not a failed default-off release
merge. Do not repeat it unchanged at6c6028df6/current source guards.

Cloud follow-up required: supply and qualify a supported current-composition
check route (or clearly document a separately scoped validation profile and
its limits); correct the owner command accordingly. Until that and current
look/lifecycle/movie/texture-eviction/gameplay/STRICT/standard s30/KOS/heap,
full-image and matched console gates pass, SCENERY_PIECE_STATE stays parked.
Original sources, prior stages and private assets remain; no SD, recipe or
publication change. Owner can continue independent lifecycle work while this
profile blocker is open.

### Answers (owner): SCPS absent-to-present actual door entry

The valid current-source control/piece arms each complete a60s cache-
interpreter/GDEMU1 default-weapon r105->r101 source-button door case.
Reader0/errors empty/overruns0; hold ends at411 and normal r101 gameplay
continues at419/480; owned emulators exit. No forced room jump or host keys.
Candidate reports SCN21 piece r105 no section, then r101 on/parts342.
At door capture both logs report free812704; that is one observed point,
not a standard heap/KOS/s30 minimum, leak result or full memory gate.

This establishes absent-to-present entry, NOT retirement/re-entry of an
already-active SCPS table, movie/texture eviction or check-mode equivalence.
The cache2 build blocker remains unchanged; no same-input retry, workaround
or zero mismatch claim. Private run/log/fixture receipts are retained in
owner-scps34-pairs-20261028/DOOR-RESULTS.json and DOOR-RESULTS.md.
Next independent local work is fixed-front cache room/material lifetime,
while awaiting a supported current-composition SCPS check route. All held
controls stay off; console prerequisites and broader gates remain unchanged.
No SD/recipe/publication.

### Answers (owner): fixed-front actual door/material lifetime

Pinned6c6028df6 FRONT_NATIVE1 control/cache default-weapon source-button
r105->r101 cases both finish60s cache-interpreter/GDEMU1, reader0/errors
empty/overruns0, normal r101 gameplay and owned process exit. Same assets/
profile except FRONT_TEXOBJ0/1, no host input or forced room jump.
Candidate frame600:1011hits/42builds/0fallbacks/520flushes/0resets,
19keys/175records. Source ftLookup clears room key/record counts on a room
change; ft_resets increments only on capacity exhaustion. The logged zero
resets therefore must not be interpreted as no room reset or as complete
room-lifetime qualification. Preserve that distinction in Build35 counters.

Private hashes/profiles/results: owner-front34-20261028/DOOR-RESULTS.json
and DOOR-RESULTS.md. Broader aliases/material changes/menu/movie/re-entry/
texture eviction, look/STRICT/standard-memory and matched console remain.
Next independent menu/material fixtures are prepared; stock KOS fight/call/
leave60s checks require dedicated squeeze/watch twins. Its door75s and
stock h2_300s are not authorized by the current60s limit. No gate waived,
held control enabled, SD/recipe change or publication.

### Answers (owner): fixed-front default inventory/material pair

Same6c6028df6 FRONT_NATIVE1/cache0-or1 programme pair and identical default
r105 menu fixture. Each60s cache-interpreter/GDEMU1 capture completes with
reader0/errors empty/overruns0, inventory closes and gameplay continues;
owned processes exit, no host input/state-out. SSCERT restored1 with
archives2/2,assets5/5,infos19/19; backing restored2903552bytes, own hashOK,
pool_free475808 both. Hashes differ between programmes; these are within-arm
restore checks, not cross-arm byte identity or a full memory oracle.

The bounded cache case logs its initial frame178 cache row, not a post-menu
frame600 checkpoint. Do not infer zero hits or completed mutation coverage.
Prior farm/door admission counts remain separate evidence. Private exact
receipts: owner-front34-20261028/INVENTORY-RESULTS.json and RESULTS.md.

Next independent memory work uses existing standard-recipe KOS watch/
squeeze/W11 twins and supported60s scenes, with source replay identity and
the fixed-front control/cache delta. These private game-memory twins use
normal QA_MENU0/QA_LINK0 composition, separate from link-enabled public QA/
ALL ON discs; no timing or full standard-floor result exists yet. Stock75s
door/300s h2 are not launched under the current60s rule. No source guard,
SCPS cache2 blocker, held control or release recipe is changed; no SD or
publication. Broader look/lifecycle/STRICT/memory/console gates remain.

### Answers (owner): fixed-front standard-game KOS fight squeeze

Pinned6c6028df6, FRONT_NATIVE1/cache0-or1 normal-game QA_MENU0/QA_LINK0
KOS_WATCH/SQUEEZE/W11/census twins; independent resolved delta only cache.
Both source-replay raw programmes equal release baseline SHA256
fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1.
This is not whole-ELF/overlay/image identity. Public QA stays link-enabled.

Four60s cache-interpreter/GDEMU1 fight captures complete reader0/errors
empty/overruns0, actual held49152 as one block or12 pieces, scene alert
marker reached, no Out of memory/MISSING/HALT. Unchanged kos_squeeze.sh
EVAL_ONLY candidate PASS both levels: minimum headroom7368/7280B and largest
block5152/4288B. Control FAIL: damaged/interleaved kos-watch rows survive its
sed parser and produce integer-expected. Intact numeric rows show minimum
headroom9960/9872B and top7744/6880B; these are observations, not an override
of the failed authoritative control judge or proof of an allocation failure.

Overall matched multi-scene floor remains INCOMPLETE; FRONT_TEXOBJ held.
Do not change source guards or quietly filter away failed records to claim
PASS. Private exact receipts: owner-front34-kos-20261028/RESULTS.json+md,
CONTROL-PROOF.json and each arm/stock-eval.txt. Existing supported60s
call/leave cases can progress independently; stock75s door/300s h2 remain
unrun. No timing/hardware/full look/STRICT/lifetime acceptance, promotion,
SD copy or publication. Existing SCPS cache2 composition blocker unchanged.

### Answers (owner): fixed-front bounded radio-call squeeze

Same6c6028df6 normal-game profiles, source replay identity and cache0/1
delta as the fight qualification above. Four60s cache-interpreter/GDEMU1
radio-call captures complete reader0/errors empty/overruns0/process exited.
Actual49152B held, sub-screen open marker reached, no OOM/MISSING/HALT.
Unmodified EVAL_ONLY judge results (intact-row minima are observations):

- control-0: FAIL - inspect unmodified judge output; numerical headroom minimum34360B, top29824B.
- control-1: FAIL - inspect unmodified judge output; numerical headroom minimum34272B, top29024B.
- cache-0: FAIL - inspect unmodified judge output; numerical headroom minimum33088B, top27232B.
- cache-1: FAIL - inspect unmodified judge output; numerical headroom minimum31680B, top26432B.

Raw damaged rows and failed judge outcomes remain preserved; no filtering
or source/parser change to manufacture a pass. Radio-open coverage does
not establish close/restoration/long-soak acceptance. Overall matched
multi-scene floor remains INCOMPLETE due fight control logging failures
and pending scenes. FRONT_TEXOBJ held; no timing/hardware/full lifetime/
look/STRICT acceptance. Private receipts owner-front34-kos-20261028/
CALL-RESULTS.json+md and each arm/stock-eval-call.txt. Existing supported
60s leave100/leave103 scenes are the next independent bounded step;
75s door/300s h2 remain unrun. No SD, recipe change or publication.

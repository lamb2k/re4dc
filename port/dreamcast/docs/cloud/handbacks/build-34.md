# Build 34: decisions for the seventeen remaining local controls

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
| `CHAR_CHUNK_BACKEND=0` | Adapt transformed character vertices/outcodes to the shared strip backend. | 2026-10-19 pull-in withdrawn by the user, [b2072d12](https://github.com/lamb2k/re4dc/commit/b2072d121cd0db63c2c79bd9ab418ca08b2e1a67); depends on the parked front end. Its old LCHK fallback count has no writer. | **Park.** Repair the counter, then isolate backend 0/1 after front-end qualification. |
| `FRONT_TEXOBJ=0` | Cache packed GX texture objects per TPL set, keeping source swaps/tail behavior. | Introduced off 2026-09-23, [58d405e9](https://github.com/lamb2k/re4dc/commit/58d405e9b4536544f259ca244230170ca5aa162d); never promoted. The current key can hit after a non-first descriptor or dimensions change. | **Enable after fix and qualification.** Validate all packed words and wrap side effects; current STRICT, lifecycle/look, RAM and console cost gates remain. |
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

## Cheap fixes selected for the next commit

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

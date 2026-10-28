# Build 35: missing audit events and rolling drawn-tick windows

**2026-10-28 progress 1: DONE** source-gap mapping and the bounded collector
contract below; **NEXT** default-off instrumentation, exact ring/lifecycle
fixtures, target disabled identity and enabled build/cost qualification;
**BLOCKED** actual tour coverage and observer overhead require Claude's
asset-complete image and console commands below. This first commit is docs only.

Branch: `codex/audit-windows-20261028`. Review source: `6c6028df6ef31fd1963740e510a460da3568aa96`, including all
Build 34 repairs. Final step-1 base: `bd1e1f3cdc98f5befb9f69191bea4a6782fc554a`
(`origin/t15/int`); its advance changes only queue and owner hand-backs. No release recipe or queue edits.

## Events to close the six named gaps

The new `FALLBACK_AUDIT35=0` boolean extends the existing FA29 reason registry
under its own guard. A small `fa35::hit` adapter uses the existing IRQ-safe
FA29 collector, room totals, tick lifecycle and QA transport. Every existing
FA29 header consumer receives the same extension definition, so reason-array
and Snapshot layouts agree. This does not require `SKIN_CENSUS=1`.

| Gap | Source locations | Intended event units and distinctions |
|---|---|---|
| Cloth simulation | `src/game/cloth.cpp`, common player/enemy chain routines in `pendulum.cpp` | Spring fast/source calls, grid points, chain calls/links and skipped chains. Simulation remains required; a scalar algorithm is not a rendering fallback. |
| Front texture objects | `src/game/trans.cpp` | Cache hit/build/refusal/source calls, flushed textures, resets; include Build 34's refreshed descriptor path. Do not infer net benefit from hit count. |
| Espgen / EspDelete scans | `src/game/espgen.cpp`, `est.cpp` | Scalar slots visited separately for move/transform/delete; distinguish mapped calls, unavailable maps, generation changes, compile-off paths, zero-owner query and empty results. No effects are skipped by the observer. |
| Collision body-list overflow | `src/game/at_mod.cpp` | Alive-list builds, alive/cached/candidate/dirty overflow refusals, source collection calls and actual source/fast list passes. Counts do not mean unique entities or dropped collision candidates. |
| Motion index | `platform/native_motion.cpp` | Binary versus linear searches, records probed, found/missing/unbound calls. `MOTION_INDEX=0` selects linear search; a failed binary search is not a runtime linear fallback. |
| Skin census-only paths | `src/game/trans.cpp` | Deferred/failure/CPU/morph infos and their vertices, ordinary/extended palette matrices. A source-skin pass and an admission failure remain distinct; no source output changes. |

The initial registry has 58 named events with explicit units, appended after
the 33 stable Build 29 reasons. The 133 DFA reasons retain their existing
order. Instrumentation batches event totals where practical rather than
calling the shared collector for every vertex or scanned record. The runtime
step will bind the exact final registry and actual-source event tests.

## Exact rolling-window contract

`FALLBACK_WINDOW35=0` is independent of the new-gap boolean. Nonzero values
select **N = 1..64**, with **32 recommended for the first owner tour**. Either
new control requires the existing `QA_MENU=1 DRAW_FALLBACK_AUDIT=1
FALLBACK_AUDIT29=1` composition; link builds retain REVIEW28's complete DIAG
delivery prerequisite. Unsupported values or missing prerequisites fail Make.

The window stores the last N **completed ticks whose pacing decision attempts
a draw**, then maintains 64-bit sums of each reason's 32-bit tick count.
An attempted draw is not proof of GPU presentation. Skipped logic ticks never
enter the drawn-reason sums; completed/skipped/incomplete and outside-tick
activity have separate denominators/metadata. Existing FA29 room totals
continue covering all logic/async work and remain explicitly not per draw.
Counts with different units overlap and must not be added as a total workload.

The ring uses fixed storage for its configured N, no allocation and no borrowed
room-memory lifetime. With all new reasons enabled the planned payload is
896*N bytes plus 16*N metadata and about 1.8 KiB of 64-bit sums; the target
receipt will report actual object/BSS sizes. It never silently shortens N.
Room/restart resets and a new capture interval invalidate old entries; pause
freezes the snapshot. A saturated tick marks that window incomplete until the
affected entry expires, independently of the older sticky room-total flag.
No wrapped or saturated number is advertised as an exact sum.

Window mode replaces the previous single-drawn-tick display rows with F26W
and FA29W sums, retaining FA29T room totals and the legacy Snapshot APIs.
The existing QA snapshot/192-byte rows will be tested at maximum values;
there is no planned duplicate full dump or unbounded log in a hot loop.
The ring's merge/reset work runs after restoring interrupts. All old bodies
remain literal under the new control's disabled branch for byte identity.

## Step 1 identity and cost

This commit changes only this report. Runtime/Make/image inputs are unchanged;
added warm/cold-I cycles, loads/stores, 32-byte lines, code, stack and resident
bytes are **0**. **MODELLED whole-frame delta: 0 ms**. Runtime overhead, enabled
memory and full-image acceptance are not inferred from the plan. The following
commands start with an existing-collector baseline; candidate commands become
usable only after the qualified runtime follow-up lands.

## Exact commands for Claude

At the repository root in Bash, set absolute `SDK_ENV` to the built pinned
SDK's environment file, `IMAGE_RECIPE`, complete `BUILD_ASSETS`, matching
`GDEMU_ZIP`, a fresh `OUT`, and `QALINK_PI` (SSH alias or `user@host`).

```bash
set -euo pipefail
source "$SDK_ENV"
git submodule update --init -- port/dreamcast/game/third_party/sh4zam
mkdir -p "$OUT"
export SOURCE_DATE_EPOCH=1760000000
QA=(DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 QA_LINK=1 QA_LINK_REVIEW28=1
    BENCHMARK=0 PMC_ROW=0 WORLD_METER=1 DRAW_SETUP_AUDIT=1
    DRAW_FALLBACK_AUDIT=1 FALLBACK_AUDIT29=1)
arm35() {
  local name=$1; shift
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$name" \
    bash port/dreamcast/build-public.sh "${QA[@]}" "$@"
  python3 port/dreamcast/tools/swap-program.py "$GDEMU_ZIP" \
    "$OUT/program-$name" "$OUT/disc-$name"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$name/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$name/disc.gdi" --profile standard
}
arm35 existing-audit

# After the runtime follow-up lands; preserve all other knobs/data in both arms.
arm35 gaps FALLBACK_AUDIT35=1 FALLBACK_WINDOW35=0
arm35 window32 FALLBACK_AUDIT35=1 FALLBACK_WINDOW35=32
```

Run `python3 ~/qalink/qalink_pi.py serve --review28` on the Pi, boot the
explicitly selected arm and establish REMOTE LINK. Record existing-audit,
gaps and window32 at identical game state/camera, with at least 600 drawn
ticks per view; the last 32 are the rolling sample, not a 600-tick total.

```bash
ARM=window32
VIEW=barn-hayfork
ql() { python3 port/dreamcast/tools/qalink/qalink.py --pi "$QALINK_PI" --review28 \
  --out "$OUT/capture/$ARM" "$@"; }
ql status
ql send MENU
ql capture start "$VIEW"
ql send RESUME
read -r -p 'Run the matched state for at least 600 drawn ticks, then press Enter: '
ql send MENU
ql send DIAG
ql capture stop "$VIEW"
```

Tour the barn/cross with crowds and cloth, front-cache material/weapon/menu
changes, effects with owner deletion/reuse, collision-heavy views and motion
archive/key transitions. Retain all rows, explicit N/used/overflow/reset and
denominator metadata, source/resolved definitions, SDK/assets/recipe identity,
ELF/all-overlays/GDI/tracks, and complete build/missing-symbol logs. Compare
observer CPU/heap cost separately from the optimizations being observed.
The runtime follow-up will add exact host, target and full absent/zero image
commands before this build moves on to scanner work.

## Questions

1. Which of the six event groups remain zero after the relevant tour scenes?
   Return the rows and resolved feature modes; zero may mean an unreachable
   path in that composition, not a proof the group is fully optimized.
2. For window32, return a full and a partially filled interval with complete
   metadata, plus a low-FPS view with skipped logic ticks. This checks that
   drawn-only frequency is interpreted separately from FA29 room totals.
3. Please retain normal release and existing-audit controls for observer
   overhead/memory. No speed-switch promotion is requested by this diagnostic.

## Answers (Claude)

Pending.

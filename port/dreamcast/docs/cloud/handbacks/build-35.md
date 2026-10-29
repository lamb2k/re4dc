# Build 35: missing audit events and rolling drawn-tick windows

**2026-10-29 progress 2: DONE** default-off six-gap instrumentation, independent
exact N=1..64 drawn-attempt windows, bounded complete QA transport and the
source-bound host/target qualification below; **NEXT** Claude's matched-state
coverage/observer-cost tour, then cloud Build 36; **BLOCKED** asset-complete
image identity, full-game memory/STRICT/look and console overhead need the
exact owner commands in this hand-back. Release recipes remain unchanged.

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
| Collision body-list overflow | `src/game/at_mod.cpp` | Alive-list builds, alive/cached/candidate/dirty overflow refusals, source collection calls and source/fast list runs (one invocation of a three-phase list pipeline). Counts do not mean unique entities or dropped collision candidates. |
| Motion index | `platform/native_motion.cpp` | Binary versus linear searches, records probed, found/missing/unbound calls. `MOTION_INDEX=0` selects linear search; a failed binary search is not a runtime linear fallback. |
| Skin census-only paths | `src/game/trans.cpp` | Deferred/failure/CPU/morph infos and their vertices, ordinary/extended palette matrices. A source-skin pass and an admission failure remain distinct; no source output changes. |

The initial registry has 58 named events with explicit units, appended after
the 33 stable Build 29 reasons. The 133 DFA reasons retain their existing
order. Instrumentation batches event totals where practical rather than
calling the shared collector for every vertex or scanned record. The runtime
qualification below binds the final registry and actual-source event tests.

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
The existing QA snapshot/192-byte rows are tested at maximum values. The
qualified runtime follow-up below records the required bounded capacity
increase; there is no duplicate full dump or unbounded log in a hot loop.
The ring's merge/reset work runs after restoring interrupts. All old bodies
remain literal under the new control's disabled branch for byte identity.

## Historical step 1 identity and cost (docs-only commit)

The first commit changed only this report. Its runtime/Make/image inputs were unchanged;
added warm/cold-I cycles, loads/stores, 32-byte lines, code, stack and resident
bytes were **0**. **MODELLED whole-frame delta for that commit: 0 ms**. These
historical figures do not describe the runtime follow-up. Its overhead,
enabled memory and acceptance limits are recorded next.

## Runtime qualification (step 2)

Tested target baseline: `b7c321300a12de206c692793d4b3e41ffec03d27`
(including the first design hand-back). Final rebased integration base:
`4f9d44437febb2616fc88d530633140eb0f9dfd0`. Its only changes are the queue and
owner Answers in Build 33/34/35 Markdown, all preserved here. The final
baseline-equivalence receipt verifies all 178 consumed baseline inputs and
192 candidate inputs unchanged; SHA256
`55289419b8678bc19d573758044c4906fe1743af09d62398e1c93d0d5eafd862`.
Both controls remain
default 0. There is no new production assembly, linker-script change or allocation.
The collector uses the existing IRQ-safe FA29 hit path and stable reason IDs;
all header consumers receive the same appended registry definition.

The final gap registry has 58 reasons. The positive face-skin deferral was a
real missing path found during review and is now included in deferred infos
and vertices. Failed allocations/pointer checks do not count CPU skinning
that never happened. `skin_trans_morph` is a subset of executed CPU work.
Front resets mean capacity recycling; room changes have the existing reset
behavior. Effect stale events require an actual scalar slot after generation
change. `mot_probes` includes the binary equality probe. These are observation
changes only; no simulation or rendering algorithm is replaced.

### Source-bound evidence

| Gate | Result and scope |
|---|---|
| Motion/cloth/collision/effect events | 20 legacy configurations, 477 cases / 92,179 assertions per normal/sanitized run; all 42 non-trans reasons exercised. Actual OFF/ON action results/order/state match. Chain moves execute admission prefixes; skip-tick, spring, search, list/cache/pipeline and effect walks use actual bodies with controlled external edges. |
| Texture/skin events | 10 profiles, 105 cases / 689 assertions each in normal and ASan/UBSan runs. Complete `commonScreenMatSub`, all three native texture-init blocks and actual cache helpers; palette admission/event prefixes only, with arithmetic and external allocation/defer/skin edges explicitly doubled. |
| Ring and actual collectors | 6 profiles, 366,954 assertions per normal/sanitized run. Every DFA/FA29/FA35 reason, N=1/3/32/64, exact oracle sums, skip/incomplete/outside work, worker serialization, tick wrap, pause/resume/room/restart and saturation expiry. |
| Complete QA capacity/delivery | 5 profiles and 45 complete transport reassemblies per normal/sanitized run, including backpressure/refusal. Actual formatting/paging/snapshot bodies, actor/DSA/XLU/OCC rows at maximum values and all new reasons. |
| SH-4 disabled identity | **136 byte-identical comparisons**, raw complete preprocessor output and objects, absent/explicit-zero, across release, QA with old auditors off, DFA-only and DFA+FA29. Disabled Make definitions/object/link selection also match. |
| SH-4 enabled profiles | **6 compile/relocatable-link profiles**: current gaps, scalar alternatives, comparison/census/front cache, independent window N=1, combined N=32, maximum N=64. New hook references resolve. |
| Registry/ABI definitions | All 22 direct FA29/FA35 C++ header consumers are covered. Make-expanded flags across 24 affected/legacy targets carry the gap definition exactly once; the window definition is limited to its 4 collector/QA targets. |
| Invalid compositions | **16 Make rejections**: empty/multiple/invalid values, N outside 1..64, missing old collectors and unsupported reviewed-link composition. |

The current/census/scalar target alternatives keep pre-existing composition
constraints: palette-off profiles also set `LEON_FACE_LAZY=0 PROP_GATE=0`;
the existing actor-skin-lazy mode stays on because the current coarse actor
composition requires it. Host event tests separately cover eager and disabled
native skin. These are fixture overrides, not recipe changes.

The target receipt binds 192 source/build inputs to GCC 15.2, binutils 2.45.1,
KOS `804b3195` and SH4ZAM `33fa4850`. Its SHA256 is
`0b2e17ec1583a668283272a1a1ea5828d81bb2d326c0f4ad6d42cd0c549e5c3f`.
Raw commands, preprocessor files, objects, dependency closures and local-frame
records are referenced by the compact committed receipt in
`tools/cloud/build35/receipts/target-controls.json`. Debug records and
preprocessor line markers are consistently omitted; source whitespace and
legacy diagnostic `__LINE__` expansions are not normalized away.
The independent `registry-propagation.json` receipt binds that target result
and all affected Make targets; SHA256
`2a47ebb62bc4cde15e61a440c6e340e6b7d43de713f2ce31d341fde854442f9a`.

No complete game/KOS-library/overlay link was available in cloud. The public
fixture uses `NMR_POOL_LOD=0` equally in control and candidate because the
generated private asset is unavailable. Sanitizers do not test console
timing; leak inspection is disabled for unavailable sandbox `/proc` traversal.
The two event suites together cover all 58 new reasons in 582 cases / 92,868
assertions per normal/sanitized run. Exact event semantics and commands are in
`tools/cloud/build35/HOOKS.md` and `README.md`.

### Code, stack and bounded resident storage

These are compiled object deltas against matching old QA+DFA+FA29 inputs.
Allocated sections include code, data and BSS; they are not independent
quantities to add. Local compiler stack frames are not whole call-chain peaks.

| Profile / compiled scope | Executable bytes added | Allocated-section bytes added | BSS bytes added |
|---|---:|---:|---:|
| Gap counters, 10 TUs | 1,172 | 19,867 | 17,312 |
| Window only, 166 reasons / N=1, 4 collector/QA TUs | 1,956 | 20,689 | 18,468 |
| Combined, 224 reasons / N=32, all 11 changed/new TUs | 3,092 | 53,104 | 48,364 |
| Combined N=64, 4 collector/QA TUs only | 1,944 | 81,140 | 77,548 |

The N=64 row excludes the seven gap TUs from its text total. The seven gap
objects are byte-identical between the complete gaps-only and combined N=32
arms, and add no BSS. Their normal-recipe text deltas are cloth +28, pendulum
+88, trans +232, espgen +272, est +136, collision +288 and motion +104 bytes.
The only TU maximum-frame increase among them is collision 408→412 bytes;
some smaller hot functions grow while the TU maximum stays unchanged:
ordinary weight palette 0→16, effect move 56→68, transform 44→52, controller
delete 56→64, effect delete 44→56 and motion acquire 60→68 bytes. The new window
TU maximum local frame is 64 bytes, ring seal 40; FA29 end-tick grows 8→20 and
its formatter 60→64. QA's maximum local frame stays 3,092 bytes.

Actual ring-object BSS is **2,080 B** for 166 reasons/N=1, **31,048 B** for
224/N=32 and **60,232 B** for 224/N=64. The gap registry adds 928 B of collector
arrays; the window adds a 4-byte per-tick overflow flag. No heap-4 or KOS heap
allocation is introduced. These static bytes still consume console RAM and
must pass the owner's full-image memory-floor check.

Capacity testing found the old 24,576-byte QA snapshot insufficient even with
gaps-only. Either new control now independently selects **32,768 bytes**.
The largest actual generated snapshot is 27,774 B. Reserving all 3,071 bytes
of the existing non-audit formatter and checking a tail sentinel yields a
27,927-byte conservative content bound; with the NUL terminator, 4,840 B
remain. Every new/old DFA/FA29 row fits its 192-byte scratch. A pre-existing
196-byte actor/DSA row uses its separate larger scratch. The selected snapshot
grows 8,192 B and the enabled link's immutable transport copy grows another
8,192 B: **16,384 B total**, already included in the BSS table. This bounded
increase prevents silent truncation; no second full diagnostic dump is added.

### Compiled cycles and traffic

The source-bound SH-4 cost gate passes **118 cases across five arms**. Actual
production executable sections match the address-metadata fixtures before
execution. It uses the real KOS status-register IRQ instructions and linked
copy/clear routines; no new model opcode qualification or production assembly
was needed. Every observed ring update runs after IRQ restoration.
The compact `receipts/window-cost.json` retains all numeric cases/IRQ segments,
source bindings and shared command/flag tables; SHA256
`5e926d82bd2eafc680f5e205e794b33a71bf12dc80ba64c554a268cc9b738716`.

All figures here are **MODELLED**, with perfect data cache. Cold-I means one
initially cold 8 KiB instruction cache in the synthetic ELF layout. Loads and
stores are retired memory instructions, including literals/stack; 32-byte
lines are distinct operand addresses, not measured fills. Scope is callee
entry to return, excluding caller argument setup/call instructions, local
scan/probe accumulators, formatting/transport and the optional actor-reset
callback. Complete methodology and all paths are in `tools/cloud/build35/WINDOW.md`.

| Case | Warm / cold-I cycles | Loads / stores | Distinct 32-byte lines | Observed stack |
|---|---:|---:|---:|---:|
| Existing 33-reason active hit | 88 / 153 | 19 / 6 | 6 | 16 B |
| New 91-reason active hit, window 0 | 90 / 154 | 20 / 6 | 6 | 16 B |
| Combined N32 active hit | 106 / 184 | 27 / 6 | 6 | 16 B |
| Combined N32 same-room begin | 295 / 473 | 36 / 108 | 22 | 24 B |
| Combined N32 full drawn seal, including ring | 5,398 / 5,706 | 1,620 / 1,345 | 162 | 60 B nested |
| Ring replacement alone, after IRQ restore | 4,877 / 5,064 | 1,396 / 1,144 | 123 | 40 B |
| Ring completed skipped tick | 56 / 137 | 17 / 12 | 7 | 40 B |
| Ring reset of sums/metadata | 928 / 973 | 4 / 469 | 61 | 0 B |

One replacement reads 5,564 and writes 4,573 bytes through actual memory
instructions. Ring reset writes 1,864 bytes independent of N. N64 has the
same bounded per-admission/reset instruction/traffic results, with the larger
static footprint above; physical cache placement can still differ. The
combined seal's IRQ-protected portion reads 830 and writes 778 bytes and
models 468 warm cycles, versus old33's 366/314 bytes and 236 cycles. These
isolated protected-segment models do not predict interrupt latency.

For an explicit sensitivity example, assume **1,000 active hit invocations**,
one same-room begin and one full drawn seal per frame at 200 MHz. The combined
collector/window pieces model **0.558465 ms**. With an assumed **30 ms of other
work**, the **MODELLED whole frame is 30.558465 ms**. The old33 observer at the
same assumed call count models 0.442035 ms, giving an equal-frequency delta of
0.116430 ms. Ten thousand assumed calls give 5.328465 ms of combined observer
work. This is not an estimate of actual added hook frequency, full observer
cost or console frame time. Do not sum cold-I cases as a frame prediction.

### Approximation and remaining gates

Window sums use exact 64-bit integer arithmetic; no statistical sampling or
numeric approximation is introduced. Input saturation, incomplete ticks and
unobserved GPU presentation are labeled rather than treated as exact work.
The observer adds CPU and resident-memory cost. Counter amounts have different
units, overlap and often batch many items into one `hit` invocation; summing
their values cannot estimate collector calls or milliseconds.

The host/target gates do not establish private-scene coverage, look/STRICT,
full absent/zero images or a console performance gain. Use release,
existing-audit, gaps and window32 controls at matched state/camera; return
resolved switches, all raw rows and full memory figures. Keep N=64 as a
capacity test until its static RAM cost is accepted. The exact owner commands
below are the next step; no optimization promotion is requested.

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

# Preserve all other knobs/data in each matched pair.
arm35 gaps FALLBACK_AUDIT35=1 FALLBACK_WINDOW35=0
arm35 window32 FALLBACK_AUDIT35=1 FALLBACK_WINDOW35=32

# The main recipe has FRONT_TEXOBJ=0: cache-specific reasons stay zero there.
# This separate pair exercises the Build 34 cache with identical cache settings.
arm35 front-existing FRONT_NATIVE=1 FRONT_TEXOBJ=1
arm35 front-gaps FRONT_NATIVE=1 FRONT_TEXOBJ=1 FALLBACK_AUDIT35=1 FALLBACK_WINDOW35=0
```

Run `python3 ~/qalink/qalink_pi.py serve --review28` on the Pi, boot the
explicitly selected arm and establish REMOTE LINK. Record existing-audit,
gaps and window32 at identical game state/camera, with at least 600 completed
draw-attempt ticks per view; the last 32 are the rolling sample, not a
600-tick total. Repeat the front-cache pair for its additional reachable
reasons; other compile-time alternatives can legitimately remain zero.

```bash
ARM=window32
VIEW=barn-hayfork
ql() { python3 port/dreamcast/tools/qalink/qalink.py --pi "$QALINK_PI" --review28 \
  --out "$OUT/capture/$ARM" "$@"; }
ql status
ql send MENU
ql capture start "$VIEW"
ql send RESUME
read -r -p 'Run at least 600 completed draw-attempt ticks in the matched state, then press Enter: '
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
Host and target commands are in `tools/cloud/build35/README.md`. The complete
absent/zero image gate below remains an owner action with the built SDK/assets.

### Complete disabled-image identity

Set `BASE_TREE` to a clean checkout of the final integration base recorded
with the runtime qualification above, and initialize its pinned submodule.
Use identical absolute SDK, recipe/assets, source GDEMU image and epoch in
all three arms. This gate uses the unchanged release composition rather than
the diagnostic `QA` array above.

```bash
git -C "$BASE_TREE" submodule update --init -- port/dreamcast/game/third_party/sh4zam
identity35() {
  local tree=$1 arm=$2; shift 2
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash "$tree/port/dreamcast/build-public.sh" "$@"
  python3 port/dreamcast/tools/swap-program.py "$GDEMU_ZIP" \
    "$OUT/program-$arm" "$OUT/disc-$arm"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
}
identity35 "$BASE_TREE" identity-base
identity35 "$PWD" identity-absent
identity35 "$PWD" identity-zero FALLBACK_AUDIT35=0 FALLBACK_WINDOW35=0
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

Retain all ELF/overlay hashes and missing-symbol logs as well as this complete
image identity. Source/object equality in cloud is not a claim that the
asset-complete game or image was linked there.

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

## Answers (owner), 2026-10-28

Docs956e83f06 merged clean asb7c321300 onbd1e1f3cd. Full owner release recipe
rc0/missing0, ELF SHA-256
1e93c0fa71ba1af779ca607beb49403b07cc0aa88d9b2553b02bfc98d2c55c19.
No runtime controls in this step; no new ALL ON build required. Prior ALL ON34
and audit-only room-tour stages remain preserved. They are different source/
observer compositions and cannot substitute for matched Build35 arms.

1. Six-group current tour results are pending the runtime. No new group is
   declared zero, absent or optimized from old counters. The fixed FRONT34
   farm pair now proves actual front-cache admission5107hits/30builds/
   0fallbacks at game frame600, but this is not a FA35 six-group capture.
2. Full/partial window32, skipped/incomplete/outside-tick, reset, pause and
   saturation-expiry checks remain pending runtime and its host lifecycle
   oracle. Owner will retain N/used/overflow/reset metadata and separate
   completed draw-attempt ticks from actual presented scenes and room totals;
   different units will not be summed as one workload. No speculative ring
   memory figure is treated as actual BSS or heap acceptance.
3. Confirmed: retain normal release, existing-audit, gaps and window32 as
   separate same-source/assets/profile arms after runtime lands. Measure
   observer CPU, local/total stack and current standard memory floors rather
   than assigning the observer's cost to an optimization. Keep new diagnostics
   out of the release recipe; no speed-switch promotion requested or made.

Console prerequisite: user selects the explicit arm and enables REMOTE LINK;
matching camera/game state and600 drawn ticks per view, complete build/media/
assets identities, raw rows and final32-entry semantics are required. Current
live HouseWhole benchmark is not this tour and has not been driven or repurposed.
Independent private work continues on Build34 SCPS-only control/on/check and
current cache lifecycles while awaiting the runtime. No private assets, SD
writes, recipe promotion, release or new lane launch.

### Answers (owner): runtime landing and local source/host qualification

842d51676 merged clean as2061c8380 after source/guard review. Both new
controls remain default0. Locally reran actual-source gap_host, trans_events,
window_host and window_qa normally and with ASan/UBSan (leaks disabled):
477 gap cases/92179 checks;105 trans scenarios/689 assertions;6 lifecycle
profiles/366954 checks;5 QA compositions/45 complete reassemblies with
maximum-value capacity/transport checks. The4840-byte spare is QA snapshot
buffer capacity, NOT KOS/whole-game free memory. Exact own logs/artifacts:
cloud35-host-20261028-2210. Cloud target136 comparisons/6 enabled links/
16 Make rejects were inspected, not rerun or treated as full game images.

Full owner default-off release recipe rc0/missing0, ELF
fdf2651068ca318cca5ad89904f53ea09241401b80719efc4659556f028d0f10;
origin integration base re-fetched/CAS checked before pushing origin only.
ALL ON QA refresh at source2061c8380 is running with QA_LINK1 and unchanged
K19. These new controls are observers requiring dedicated audit profiles,
so they stay0 in performance K/release; normal release/existing-audit/gaps/
window32 arms remain separate. Old candidates/evidence retained, no SD copy.

1. Six-group actual-game tour is PENDING; no old counters or host fixture
   zero is transferred into current FA35 event coverage. Capture material/
   weapon/menu, cloth, effect owner reuse, collision overflow and motion
   transitions with exact resolved modes and pinned assets/programme.
2. Partial/full/skipped/incomplete/outside/reset/pause/saturation lifecycle
   host/QA tests PASS; actual game/link windows remain pending. Draw attempts
   are not observed GPU presentation, different units are not summed.
3. Normal-release/existing-audit/gaps/window32 private image, full disabled
   repacked GDI/track identity and actual linked BSS/stack/observer CPU costs
   remain owner steps, not inferred from target objects or the earlier plan.
   Warp/QA keeps64KiB log ring versus16KiB production; keep that framework
   footprint separate from incremental gaps/window cost. Never shrink it
   to force a memory pass or silently lower N32.

Console prerequisite: user chooses each explicit arm, establishes REMOTE
LINK after swaps, holds the matched camera/state for600 completed draw-
attempt ticks/view and retains full metadata (32 used entries are not a
600-tick sum). Current HouseWhole session is not that tour; no inputs sent.
No recipe promotion, SD write or release publication.

### Answers (owner): ALL ON refresh complete, 2026-10-28 22:34 EDT

Source2061c8380 ALL ON QA compile/missing0, loader/standard lint0 violations,
ZIP validation PASS. QA_LINK1, K19 unchanged; both new audit35 controls0.
Final track03 SHA256
7d8084996ce2861f54d9cf5313ed601e5316eb4620e1a227e29ef608c6821e91.
Stage source/knobs/all6 SHA256SUMS entries read back and checked before the
independent offline scanner extraction. Prepared only; no new game/link/
hardware acceptance, release promotion, SD copy or publish.

### Answers (owner): full owner release OFF/repacked-image identity, 2026-10-28 23:22 EDT

Before-runtime basecd25cc5e4 and absent-runtime2061c8380 are preserved full
normal-release owner builds (QA0/link0/warp0, missing0). A NEW explicit0/0
2061c8380 full release recipe built49s/rc0/missing0. Recipe/private inputs,
SDK and epoch retained; absent/zero complete resolved-definition delta0 after
normalizing ONLY exact owned source/output prefixes. Compared every allocated
ELF section address/size/type/flags/payload, full nonempty raw programme and
complete15-overlay sets across all3 arms: exactly equal. New Make metadata
for base->absent is only FA35/FW35 empty object variables, their zero controls
and allowed window-value list. No enabled observer or public-data fallback.

Programme3372036B SHA256
fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1.
Whole ELF/debug bytes DIFFER; no full ELF byte-identity claim.

Three INDEPENDENT unchanged swap-program.py CLI runs then replaced the raw
programme plus all15 matching own overlays into one fixed final prepared
ALL ON35 asset GDI template (source2061c8380, original track03 SHA7d808499).
The replacements are NORMAL-RELEASE QA0/warp0 programmes, not ALL ON or an
enabled audit profile. This uses the full owner ch2-build rP recipe/SDK;
it is not a build-public clean contributor-kit check or fresh release master.
No original GDI/template bytes were changed. No fixture/asset patch, cache
hit, timestamp normalization, mask, borrowed replacement image or reused
finished output was used to obtain identity. New independent copies only.

Each swap read back all16 replaced files and checked layout/overlaps; each
finished image passes loader AND standard lint, rc0. GDI plus all3 track
lengths and SHA256 are EXACTLY equal base/absent/zero:

| File | Bytes | SHA256 |
|---|---:|---|
|disc.gdi|87|025516557d49e1835e7eb8571e09244b64db190cf3981ead555c54b1924ca19f|
|track01.bin|1058400|058298a2bd8a0ade4637efaf67cb2c71a2f4c924b1e7d59c2c5989ac550fe8e9|
|track02.raw|1237152|15453e38e9c8e03d6e7854c2414f93e944b6059b4933847ebf735834407cec48|
|track03.bin|1185760800|4b42bf067f4ba84cf1d82284c57080628d5128202e48f0c17b657bbdb92b3b1e|

Read ALL1664 final file payloads from the base repack: its programme and15
overlays match the own compiled output, all1648 other payloads exactly match
the fixed source image manifest. Since the other2 GDI/track sets are raw-byte
identical, that payload result also holds for both. Source manifest SHA
1b9c8f14e97423e12959eec202cda807b15bd761bd0e440b14db2621b29629f4;
source image hashes checked unchanged after all3 swaps.

Evidence: owner-audit35-offid-20261028/OFF-EXECUTABLES.json, OFF-IMAGES.json,
FINAL-PAYLOAD-BINDING.json, full own logs/lint/commands/programmes/GDIs;
WSL root with the same name retains build/precheck/zero input receipts.
This closes the scoped normal-release disabled executable/repacked-image
identity gate on this fixed composed data template. It does not certify the
QA template's content, contributor kit, public release, route, enabled game/
link windows, observer CPU/stack/heap, memory floor or hardware acceptance.

NEXT: same-source normal-release/existing-audit/gaps/window32 private enabled
profiles and actual cost/game/link evidence, retaining normal and existing-
audit controls separately. No N32 reduction, production log-ring change,
recipe promotion, SD copy, release publication or console input.

#### Post-gate storage disposition (owner, 2026-10-28 23:33 EDT)

AFTER all3 independent swaps/lints/raw-image comparisons and finished-payload
proof passed, the two owned redundant absent/zero high tracks were replaced
with hard links to the equal base track. All logical paths/lengths/hashes
remain readable and were rechecked. Pre-dedup independent CLI commands,
logs and manifests remain; links were NOT used to obtain an identity PASS.
POST-GATE-DEDUP.json records this space-only disposition. Original source
template/private assets/unrelated evidence were untouched.

C free18.17GiB at2026-10-28T23:33:02.4609833-04:00; further heavy builds and
multi-GB enabled-profile staging are HELD pending sufficient headroom above
the workspace reserve. Owner Codex, five-minute read-only cloud checks
continue. Source/profile planning can continue without large allocation.
No broad Windows prune, unrelated app restart or private-asset deletion.
Root fstrim reports Linux trim only; no Windows recovery is inferred.

### Answers (owner): private audit links and actual linked static cost, 2026-10-28

Recovered limited space using transparent NTFS compression on owned proof
tracks and prepared ALL ON31..35 QA copies, each checked against its existing
manifest before/after. Logical file bytes/hashes/paths and original assets
are preserved; no captures or gates were repeated to claim a new PASS.
This is filesystem storage disposition AFTER the recorded qualification;
future host-I/O context should include compression, no timing gain inferred.

Full private existing-audit and gaps links each42s/rc0/missing0, source2061c8380,
normal full recipe plus the common documented QA/observer framework. Private
NMR_POOL_LOD1 retained. Complete resolved comparison normalizes ONLY the exact
owned output prefix: FALLBACK_AUDIT35 changes0->1 and the Make-derived object
lists select cloth/pendulum/trans/espgen/est/at_mod plus native_motion.
All other resolved fields match; window0, QA/link/review28/DFA/FA29 remain1.
The separately retained normal release is QA0/link0/warp0 and cannot stand in
for the existing-audit incremental observer control.

Actual final linked GNU size categories and symbols (bytes):

| Profile | text + rodata | initialized data | BSS category | log ring | FA29 state | QA diagnostic buffer |
|---|---:|---:|---:|---:|---:|---:|
|normal-release|2694964|675972|851124|16384|-|-|
|existing-audit|2847376|677120|1053888|65536|600|24576|
|gaps|2849688|677120|1071200|65536|1528|32768|

Gaps minus existing-audit: +2312 code/constant bytes, +0 initialized data,
+17312 linked BSS-category bytes. FA29 state600->1528 and QA buffer24->32KiB
are actual linked symbols. Both QA arms use64KiB logs; the normal release's
16KiB log is separate framework overhead. No heap/KOS minimum, local/total
stack maximum, observer CPU time, frame speed or hardware acceptance follows
from these static sizes. Full symbol/size/definition/ELF receipts retained in
owner-audit35-enabled-20261028/LINKED-PAIR-PROOF.json and original outputs.

The18GiB reserve guard stopped the batch after the successful gaps link.
window32 was NOT launched; completed arms are retained and must not be
rebuilt merely to resume. Source tree2061 remains clean and retained; exact
window32 options/N32 and normal-release control remain fixed. Resume ONLY
the remaining link through codex-lanes/cloud-watch-timer/resume-audit35-window.sh
after measured C headroom supports its1GiB allocation budget above reserve.
Then verify all3 complete profile/object/linked-size deltas. Multi-GB image
staging remains held. No window32 image, enabled game/link/tour/cost run or
reduced-N result is accepted. No recipe promotion, SD copy or publication.

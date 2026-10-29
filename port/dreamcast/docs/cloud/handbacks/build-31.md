# Build 31: portal culling and world part plan

**2026-10-28 progress 3: DONE** runtime follow-up re-synced onto `f4c1af9a1c861de58d56e71fb18d0f4e4e313217`, preserving landed tools and Answers (owner); runtime source is unchanged from the previous qualified follow-up; all 48 OFF comparisons, four enabled compile/link arms and ten rejection probes pass again on the refreshed base; **NEXT** Claude runs the private-image/console commands below; **BLOCKED** private room geometry, full SDK/image identity and hardware acceptance.

Branch: `codex/world-portal-part-plan-20261028`. Current integration base:
`f4c1af9a1c861de58d56e71fb18d0f4e4e313217` (`origin/t15/int`). The tool-only
step is already integrated as `ebb7668d`. This follow-up adds the separately
qualified runtime, build controls and evidence described in step 2. It retains
the owner's integration and qualification notes. The queue and release recipe
are unchanged by this follow-up.

## Step 1: candidate cells, no runtime enablement

**2026-10-28 progress 1: DONE** conservative portal builder, fixture graft and 21 synthetic tests; **NEXT** qualify `WORLD_PORTAL29` runtime and `WORLD_PART_PLAN29`; **BLOCKED** private room geometry and console acceptance are Claude's runs below.

The default-off `--barn-portals29=1` builder accepts a hash-bound R4IM v3,
R4PW and R4ID package and explicit geometry-authored building/eye boxes.
It starts every face open, subtracts only exactly coplanar opaque static
wall triangles, and intersects coverage across every stored LOD. Exact
rational polygon complements preserve cracks; unsupported or uncertain
surfaces remain openings. Apertures expand by at least 64 mm and round
outward. Complex faces become wholly open instead of exceeding the runtime
portal budget. This supports multiple buildings in any explicitly named room.

The output retains PCL2 storage and adds a CRC-bound `WP29` witness trailer.
Legacy loaders reject its extended size. The upcoming runtime must verify
current-view opaque submission and source state; merely having wall data in
a package grants no hiding permission. The graft tool verifies matching
staged mesh/policy identities and adds only the candidate cell reference to a
new fixture. Neither tool reads inputs or writes output with its flag absent
or zero.

Proof and exact schema: [PORTALS29.md](../../../tools/d367/ps2world/interior/PORTALS29.md).
The 21 tests pass on actual synthetic package serialization: door/window,
0.125 mm crack, LOD openings, dynamic/cutout/wrong-facing walls, multiple
houses/rooms, safe-eye/near refusal, CRC/hash/malformed inputs, legacy loader
exclusion, fixture identity and disabled no-output behavior. No game assets
are included.

```sh
python3 -B port/dreamcast/tools/d367/ps2world/interior/test_barn_portals29.py -v
```

Tool-only release identity follows directly from the changed-file scope:
no runtime, build recipe, header or generated asset changes are committed
in this step. Warm/cold-I cycles, loads/stores, 32-byte data lines, runtime
code/stack and resident bytes added by this step are all **0**.
**MODELLED whole-frame delta: 0 ms.** Cell file size is reported by the tool;
runtime costs and benefit remain separate evidence.

## Exact private-data commands for Claude

From the repository root, set `PKG` to the actual staged room-package
directory, `CFG` to the geometry-authored config described in PORTALS29.md,
`BASE_FIXTURE` to a fixture explicitly staging that mesh and policy, and
`OUT` to a fresh private result directory. Do not use the explanatory
coordinates in the schema as r103 geometry.

```sh
sha256sum "$PKG/ps2-world.re4mesh" "$PKG/ps2-world.r4pw" "$PKG/ps2-world.ids"
python3 port/dreamcast/tools/d367/ps2world/interior/barn_portals29.py \
  --barn-portals29=1 --config "$CFG" --package "$PKG" \
  --out "$OUT/interior.cell" --report "$OUT/portal-proof.json"
python3 port/dreamcast/tools/d367/ps2world/interior/graft_portals29.py \
  --barn-portals29=1 --fixture "$BASE_FIXTURE" --cell "$OUT/interior.cell" \
  --out "$OUT/fixture-portals29.json"
```

Retain package/config hashes, face coverage/openings, witness identities,
refusal output and candidate bytes. Runtime build/QA commands follow in the
next qualified step. Do not enable an old PCL2 runtime against this candidate.

## Questions

1. Please author safe eye/hull boxes from the actual r103 opaque PS2 walls,
   then return the generated proof report (or exact refusal). Which witness
   parts occur before the outdoor targets in submission order?
2. Return the outward/inward barn `WORLD_METER`, DFA and DSA windows with
   matched image/package hashes. Proposals 2, 4 and 5 remain notes pending
   those measurements.
3. On the runtime candidate, Claude must run the magenta hidden-geometry
   walk, missing/stale/heap refusal cases, doors and near-plane crossings,
   leave/reentry, s30 loan/return, full disabled image identity and STRICT
   gameplay. No private or console PASS is claimed here.

## Answers (Claude)

Pending.

## Answers (owner)


2026-10-28 Codex owner: tool-only step merged as `ebb7668d` onto
`origin/t15/int`. The 21 committed synthetic tests pass locally. The current
release recipe builds with `rc=0`, `missing=0`; ELF SHA-256
`6468e3e08405f99474f8161ee0c6ab965ff8e11b8b97debf4e11117010f31446`.
No runtime/build/recipe inputs changed, so this step adds no enabled switch
or console speed claim. Runtime work remains open; continue qualified small
commits rebased onto the latest integration branch.

1. Safe eye/hull boxes and witness submission order remain an owner private
   geometry task. No geometry-authored config or proof report is available
   in this hand-back; explanatory schema coordinates will not be used as
   r103 data. The exact builder/graft commands above remain pending those
   pinned private inputs, rather than receiving a synthetic private PASS.
2. Matched outward/inward console windows remain pending the user's slot
   154 ALL ON DIAG / slot 151 baseline session at the same teleported spots,
   with the console dialled onto the Pi link. Existing handover readings
   are historical and do not satisfy this matched package/image request.
3. Runtime, magenta walk, refusal, near/door crossing, reentry, s30, disabled
   image identity and gameplay gates remain pending the runtime candidate.
   This tools-only step cannot qualify or enable the legacy PCL2 runtime.

Watcher cadence is now every five minutes per the user's latest instruction.

2026-10-28 18:06 EDT follow-up: `92f7cf811` arrived while the first tool
landing was being recorded, with the original tools rebased as `0efd3ee31`.
The fresh integration merge conflicts (add/add) only in this hand-back file.
The merge was aborted; no follow-up runtime code was landed or enabled.
Please rebase/re-sync onto current `origin/t15/int`, retain the landed tools
and Answers (owner), qualify again, and push. The owner will retry on the
five-minute watch; no manual conflict resolution is authorized.

## Step 2: guarded portal runtime and compiled part plan

**2026-10-28 progress 2: DONE** default-off portal/runtime and part-plan implementation, 21 builder tests, 388 portal host checks, 450 ordered part-plan cases, sanitizer runs, 48 complete disabled target-byte comparisons, four enabled compile/relocatable-link arms and bounded SH-4 cost receipts; **NEXT** Claude's matched private-image/console gates; **BLOCKED** real room geometry, full linked game/image identity and hardware acceptance require the private inputs and built KOS described below. No console or whole-frame improvement is claimed.

This step remains on `codex/world-portal-part-plan-20261028`, rebased onto the integration commit above. Both `WORLD_PORTAL29` and `WORLD_PART_PLAN29` default to 0. The release recipe is unchanged. Visibility-table, clip-reuse and room-far proposals remain notes pending the actual meter rows.

### What the runtime changes

`WORLD_PORTAL29=1` loads the step-1 PCL2/WP29 cell through the existing interior-cell room/movie lifecycle. It validates the physical mesh CRC/length, physical policy CRC, room, complete-file and witness checksums, counts, finite bounds, hull-plane aperture placement, safe-eye inset and sorted source witnesses. Legacy PCL1/PCL2 files do not provide WP29 authority. Missing, stale, malformed or unaffordable cells leave ordinary drawing active and log their refusal.

A loaded cell is only a candidate. All named immutable opaque source parts must finish successfully in the same scene, view, projection, viewport and room generation before it may hide anything. Live source/gate and opaque-material checks remain required; changed images and frame/pass resets invalidate receipts. Parts omitted or failing before their completion never grant permission. Source drawing order is preserved, so outdoor targets submitted before the complete witness set remain drawn. Actor/Trans and source-owner visibility consumers receive no portal reject.

After activation, a wholly hidden placement is rejected before part setup. Surviving placements retain the chunk path, with conservative portal tests on clusters and meshlets; portal activity itself no longer forces chunk-selection decline. View/near-plane numeric guards and the 64 mm uncertainty margin remain mandatory. The proof declines unsupported source-removing cone/piece-state/dedup/backface compositions. The builder's restricted exact planar-wall coverage is useful only where the real package supports it; unsupported geometry remains open. Magenta hardware validation is still required for seams and rasterization.

`WORLD_PART_PLAN29=1` compiles ordered per-mesh/per-pass spans once on room load. Each aligned 32-byte record holds immutable part metadata, texture key and meshlet count. The spans cover every eligible live foliage/transparency policy migration while preserving source part order. Live material decisions, UV animation, camera transforms, texture resolution and submission remain in the draw path. A source binding/capacity/allocation failure uses the original scan. Room retirement and movie lending free the plan; return recompiles it.

Both optional allocations use the high room allocator with a checked **96 KiB free-heap floor** before and after allocation. They never enter the low allocator's shell/motion eviction path. Both switches require `NATIVE_PKG_HIGH=1`. The plan is capped at 64 KiB plus 31 alignment bytes; each mesh has three 8-byte spans, and records are 32-byte aligned. Portal storage is the cell file plus 5,184 bytes for two arrays of 24 108-byte frusta; portable receipt state is 156 bytes and each geometry state is 72 bytes. This is additional optional room memory, not free cache storage.

### Validation and final target receipt

The Python builder suite passes **21 tests**. The host harness compiles the actual portal loader/runtime and the literal production geometry core: **388 checks pass**, including missing/stale/corrupt layouts, bounds/NaNs, source and scene changes, incomplete receipts, camera/near crossing, actor refusal, and cluster/meshlet survivor behavior. The production plan compiler passes **450 ordered live-policy cases**, plus bounds, alignment, capacity and source-identity checks. Both C++ suites pass AddressSanitizer and UndefinedBehaviorSanitizer with `ASAN_OPTIONS=detect_leaks=0`; LeakSanitizer cannot inspect processes in this environment because of `/proc`/ptrace restrictions. LeakSanitizer was not run successfully.

```sh
python3 -B port/dreamcast/tools/d367/ps2world/interior/test_barn_portals29.py -v
python3 -B port/dreamcast/tools/cloud/build31/portal_runtime_host.py
ASAN_OPTIONS=detect_leaks=0 python3 -B \
  port/dreamcast/tools/cloud/build31/portal_runtime_host.py --sanitize
c++ -std=c++17 -O2 -Wall -Wextra \
  port/dreamcast/tools/cloud/build31/part_plan_host.cpp -o "$OUT/part-plan-host"
"$OUT/part-plan-host"
c++ -std=c++17 -O2 -Wall -Wextra -fsanitize=address,undefined \
  -fno-omit-frame-pointer port/dreamcast/tools/cloud/build31/part_plan_host.cpp \
  -o "$OUT/part-plan-host-san"
ASAN_OPTIONS=detect_leaks=0 "$OUT/part-plan-host-san"
```

The Make-derived target gate checks complete preprocessed source and complete SH-4 objects for `native_static`, `native_ui` and `ui_bridge`. It compares the exact integration baseline with controls absent and explicitly zero in release, QA, supported portal and magenta profiles. Debug records and preprocessor line markers are consistently disabled in all arms; the resulting files are compared without further normalization. Enabled portal, plan, combined and magenta arms compile and undergo a relocatable link requiring the new hooks to resolve.

| Final gate against `f4c1af9a` | Result |
|---|---|
| 48 complete OFF byte comparisons: 4 profiles × 3 TUs × 2 forms × 2 control modes | PASS |
| Four ON compile/relocatable-link arms | PASS |
| Invalid values/compositions rejected | 10 / 10 |
| Frozen consumed source/build input hashes | 223 |
| Portal: executable / allocated / BSS delta | +4,482 / +5,101 / +278 B |
| Part plan: executable / allocated / BSS delta | +1,628 / +1,901 / +44 B |
| Combined: executable / allocated / BSS delta | +6,126 / +7,018 / +322 B |
| Magenta: executable / allocated / BSS delta | +5,890 / +6,782 / +322 B |
| Maximum local static stack frame, portal / plan | 9,272 → 9,476 / 9,008 → 9,012 B |
| Maximum local static stack frame, combined / magenta | 9,272 → 9,496 / 10,112 → 10,340 B |

The section deltas are against each enabled arm's matched OFF profile, not the normal release. Stack figures are compiler-reported local frames, not a measured call-chain maximum. The new optional allocator helpers each use 8 B; plan open uses 116 B and portal finish uses 16 B. The compact [target-controls.json](../../../tools/cloud/build31/receipts/target-controls.json) receipt has SHA-256 `3259f9706dd47e3d0324c845445564085ce2bfae276f28bd038f75fceef668a4`.

Reproduction and toolchain arguments are in [the target-gate README](../../../tools/cloud/build31/README.md). The cloud KOS `lib/dreamcast` directory is empty: no full ELF/game link, overlay link or full-image equivalence PASS is claimed here. Claude must build those with the complete SDK and matching private Build-Assets. An older PVS/batch composition is accepted by Make but rejected by existing source guards; its expected-failure reproduction is retained in that README. The qualified portal profile disables stream and submit batching on **both** arms; this cost must be compared with the normal release as well as the matched control.

### Bounded SH-4 costs

These are **MODELLED** synthetic kernel results from [portal-cost.json](../../../tools/cloud/build31/receipts/portal-cost.json) and [part-plan-cost.json](../../../tools/cloud/build31/receipts/part-plan-cost.json). Warm runs assume perfect D-cache. Cold-I means one isolated initially cold 8 KiB instruction cache. The 32-byte line column is address footprint, **not measured cache misses**. Cold costs cannot be summed into a frame estimate.

| Portal kernel | Warm / cold-I cycles | Loads / stores | 32-byte lines | Observed stack |
|---|---:|---:|---:|---:|
| One portal, visible target | 443 / 668 | 118 / 35 | 18 | 120 B |
| One portal, hidden target | 369 / 578 | 95 / 33 | 17 | 120 B |
| 24 portals, hidden target | 2,531 / 2,740 | 601 / 102 | 95 | 120 B |
| Target intersects house: keep | 281 / 446 | 71 / 30 | 14 | 120 B |
| First witness commit | 36 / 97 | 8 / 4 | 4 | 8 B |
| Last of 256 witness commits | 36 / 97 | 8 / 4 | 5 | 8 B |
| Repeated witness commit | 32 / 93 | 7 / 2 | 5 | 8 B |
| Receipt sync, same image | 342 / 472 | 72 / 10 | 16 | 40 B |
| Receipt sync, new image | 245 / 436 | 45 / 58 | 16 | 40 B |

This omits loader/I/O, current source/material scans, begin/numeric setup, geometry savings and GPU work. `sources()` scans up to 256 witnesses and is revisited before activation/receipt completion; survivor setup must be measured on the real room. Portal fixture text is 1,744 B with 4,868 B allocated, including 2,796 B BSS. Those are the standalone fixture's sections, not production image growth.

| Source parts (selected) | Warm cycles before → after | Cold-I cycles before → after | Loads before → after | Stores before → after | 32-byte lines before → after |
|---|---:|---:|---:|---:|---:|
| 1 (1) | 101 → 91 | 217 → 193 | 24 → 21 | 20 → 13 | 7 → 7 |
| 16 (6) | 596 → 421 | 712 → 523 | 99 → 66 | 85 → 48 | 24 → 17 |
| 64 (22) | 2,180 → 1,477 | 2,296 → 1,579 | 339 → 210 | 293 → 160 | 78 → 47 |
| 128 (43) | 4,270 → 2,863 | 4,386 → 2,965 | 655 → 399 | 566 → 307 | 149 → 86 |

The plan fixture compares ordered metadata/key preparation with prepared spans, excluding allocation/build-once work, other live predicates, vertices and submission. The helper changes from 140 B code / 52 B stack to 96 B / 24 B. Fixture sections are 932 B executable, 27,600 B allocated and 26,656 B BSS; these include synthetic arrays and are not runtime image growth.

For scale only, assume 200 MHz and 30 ms of unrelated work. Adding 100 hidden grid tests yields 30.1845 ms with one portal or 31.2655 ms with 24 portals, before the omitted guards and any saved work. Twenty 64-part metadata scans yield 30.2180 ms before versus 30.1477 ms after. These are arithmetic sensitivities to stated synthetic counts. They do not predict r103 FPS, D-cache savings or a full runtime gain.

### Exact private build and image commands for Claude

First run the step-1 cell build/graft commands above against the actual r103 package. Set `IMAGE_RECIPE` to the release recipe for the source image, `BUILD_ASSETS` to its complete unpacked Build-Assets directory, `GDEMU_ZIP` to that image, and `OUT` to an absolute private output directory. Source the built toolchain environment. The GDEMU image's `ps2-world.re4mesh`, `ps2-world.r4pw` and `ps2-world.ids` must be the package used for the cell proof; retain their hashes with `portal-proof.json`. A fixture graft does not replace mismatched disc packages.

Run the following in Bash from the candidate repository root. Private builds retain the recipe's `NMR_POOL_LOD`; the cloud-only matrix sets it to 0 because its generated private header is unavailable.

```sh
mkdir -p "$OUT"
export SOURCE_DATE_EPOCH=1760000000
QA=(DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 BENCHMARK=0 PMC_ROW=0
    WORLD_METER=1 QA_LINK=1 QA_LINK_REVIEW28=1)
PORTAL=(NATIVE_PKG_HIGH=1 MESH_FASTPATH=1 MESH_DIRECT=1 MESH_VP_SCHED=1
        HW_LEAN=1 SCENERY_CHUNK=1 PS2_WORLD_DYNAMIC=1 PS2_WORLD_MESH=1
        PS2_WORLD_ROOMS=2 MESH_LOD=1 PS2_PVS=1 PS2_INTERIOR_CULL=1
        PS2_PVS_BATCH_COMPOSE=0 SCENERY_SUBMIT_BATCH=0 SCENERY_STREAM=0
        SCENERY_CLIP_GATHER=0 SCENERY_CLIP_INDEXED26=0
        SCENERY_CONE=0 SCENERY_PIECE_STATE=0 SCENERY_DEDUP=0 CPU_BACKFACE=0)
build_arm() {
  local arm=$1
  shift
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash port/dreamcast/build-public.sh "${QA[@]}" "$@"
}
build_arm normal-off WORLD_PORTAL29=0 WORLD_PART_PLAN29=0
build_arm plan-on NATIVE_PKG_HIGH=1 PS2_WORLD_MESH=1 \
  WORLD_PORTAL29=0 WORLD_PART_PLAN29=1
build_arm portal-off "${PORTAL[@]}" WORLD_PORTAL29=0 WORLD_PART_PLAN29=0
build_arm portal-on "${PORTAL[@]}" WORLD_PORTAL29=1 WORLD_PART_PLAN29=0
build_arm combined "${PORTAL[@]}" WORLD_PORTAL29=1 WORLD_PART_PLAN29=1
build_arm magenta "${PORTAL[@]}" PS2_INTERIOR_CULL=2 \
  WORLD_PORTAL29=1 WORLD_PART_PLAN29=1
```

The normal-off/plan-on pair retains the normal recipe's drawing composition; the four portal-profile arms share the slow prerequisites. Keep `resolved-knobs.txt`, `build.log`, the missing-symbol report (must be empty), ELF/overlay hashes and the recipe/assets identity from every arm. Enable DFA/DSA and `FALLBACK_AUDIT29` on a separately matched diagnostic pair if the image recipe does not already include them; keep those observer settings identical between that pair and report the changed composition.

Choose `CELL_MODE=--add` only if `dc/native/r103/interior.cell` is absent in the source image. Use `CELL_MODE=--replace` if it already exists. `--add` rejects an existing file, and `--replace` rejects a missing file; do not pass both. Use the same cell in both comparison arms. Every output disc directory must be fresh or empty.

```sh
CELL_MODE=--add  # Change to --replace when the source image already has this file.
for arm in normal-off plan-on portal-off portal-on combined magenta; do
  python3 port/dreamcast/tools/swap-program.py \
    "$GDEMU_ZIP" "$OUT/program-$arm" "$OUT/disc-$arm" \
    "$CELL_MODE" "dc/native/r103/interior.cell=$OUT/interior.cell"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
done
```

For the full disabled-image gate, `BASE_TREE` must be a clean checkout of `f4c1af9a1c861de58d56e71fb18d0f4e4e313217`; the current checkout is the candidate. Use the same absolute recipe/assets paths, SDK and epoch for all three builds, with no QA overrides, then repack the same source image without asset changes:

```sh
identity_build() {
  local tree=$1 arm=$2
  shift 2
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash "$tree/port/dreamcast/build-public.sh" "$@"
  python3 port/dreamcast/tools/swap-program.py \
    "$GDEMU_ZIP" "$OUT/program-$arm" "$OUT/disc-$arm"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
}
identity_build "$BASE_TREE" identity-base
identity_build "$PWD" identity-absent
identity_build "$PWD" identity-zero WORLD_PORTAL29=0 WORLD_PART_PLAN29=0
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
base = manifest('identity-base')
assert base and any(name.endswith('.gdi') for name in base), base
for arm in ('identity-absent', 'identity-zero'):
    candidate = manifest(arm)
    assert candidate == base, (arm, base, candidate)
print('PASS complete repacked GDI/track identity: baseline = absent = zero')
PY
```

### Console gates and returned evidence

Use the established barn position/save and identical day/enemy/body state for every arm. Capture three views: barn exit looking outside toward the far barn, the same position facing stalls, and the near hay-forking Ganado case. The approximate player coordinates in the queue are a navigation aid, not wall geometry. For each view/arm, hold long enough to collect repeated complete windows, with at least 300 drawn frames; retain raw windows and their tick/frame denominators rather than averaging incomplete rotations.

Use the updated Pi companion files and start the Pi service with the matching protocol: on the Pi run `python3 ~/qalink/qalink_pi.py serve --review28` (or set the existing service ExecStart to the same option before starting it).

```sh
ARM=portal-on  # Repeat for normal-off, plan-on, portal-off and combined.
VIEW=barn-out # Repeat at the matched barn-stalls and near-hayfork views.
ql() {
  python3 port/dreamcast/tools/qalink/qalink.py --pi "$QALINK_PI" --review28 \
    --out "$OUT/capture/$ARM" "$@"
}
# Boot this arm and connect REMOTE LINK in the QA menu first.
ql status
ql send MENU
ql send QA WOPQ GAME
ql send QA WXLU GAME
ql send QA WSHELL GAME
ql capture start "$VIEW"
ql send RESUME
# Hold the already established matched view for the complete draw windows.
ql send MENU
ql send DIAG
ql capture stop "$VIEW"
```

Return image/program/package/config hashes, all resolved knobs, stills, raw QA logs and `WORLD_METER`/DFA/DSA windows. Include `WP29` loaded/candidate/active/witness/committed/decline/wait counters, `PCCULL` placement/cluster/meshlet rejects, `WPLAN29` bytes/planned/legacy/declines, heap, actual CPU/frame/GPU timings and survivor setup. Compare portal-on to both portal-off and normal-off; compare plan-on to normal-off. A synthetic kernel saving alone does not accept either switch.

1. **Magenta walk:** use the magenta arm above. First show real loaded cells, complete witness receipts and nonzero portal tests/rejects; zero visible magenta with zero activation proves nothing. Walk all openings, thin cracks, wall/floor/roof joins, oblique views and near corners. Check the outside view and inward view, different near/FOV settings, and positions outside every safe eye box.
2. **Door/source crossing:** approach and cross each doorway in both directions, open/break/move applicable objects, change source gates, leave/re-enter and reset/reload the room. Permission must disappear whenever source evidence or the current image changes. Dynamic/breakable surfaces must not become fixed occluders. Record any fail-open result or evidence that ordinary drawing was lost.
3. **Refusals and memory:** test missing, truncated/malformed, stale package-bound and checksum-damaged cells plus insufficient optional-allocation headroom. Require the stated refusal, ordinary drawing, zero new portal rejects, and preserved shell/motion backing. A room whose current ID/source mapping cannot establish static witnesses is a refusal, not a forced activation. Check the plan's separate allocation/capacity refusal and original-scan behavior.
4. **s30 loan/return:** record cell/plan retirement, movie playback, heap and post-movie room reload; the return must reload/recompile with fresh generation and empty current-view receipts. Verify no stale pointers, missing world, allocation eviction or gameplay change.
5. **STRICT gameplay and image:** finish the r100/r101/r103 route and relevant doors/events/combat with the same collision, AI and state outcomes, including combined and magenta diagnostics. Run the full absent/zero image identity commands above. Report hardware PASS only with the actual captures; cloud results do not substitute for these gates.

**Questions for Claude (2026-10-28):** Does the real r103 package provide sufficient exact static wall coverage, and do its witness parts complete before enough outdoor targets to help? Please return either the proof/refusal and activated captures or the exact failing gate. Which part of survivor setup remains dominant after the matched comparison? No release-recipe promotion is requested by this hand-back.

**Answers (Claude):** Pending.

## Owner runtime landing, 2026-10-28

Re-synced `5b5e4603b` merged clean as `81028934c`, both switches default 0.
The prior report conflict is cleared. Local checks: 21 builder tests, 388
production portal checks and 450 ordered part-plan cases PASS; both C++
suites also pass ASan/UBSan with leak detection disabled, matching the
disclosed sanitizer boundary. Logs: owner private `cloud31-host-20261028-1816`.
Release recipe builds rc=0/missing=0; ELF SHA-256
`fb2cf4a93361da7512c99368c32bcfbb7ba27d5dd6fb987226901f4497abc1a8`.
The cloud's target-byte matrix was not rerun locally, and full repacked
absent/zero image identity remains a separate pending gate.

`WORLD_PART_PLAN29=1` is added to the ALL ON QA K list; rebuilding on this
runtime integration with QA_LINK=1. No recipe enablement or SD write.
`WORLD_PORTAL29` is explicitly parked with local owner/reason: the qualified
profile requires stream/submit and clip gather/indexed off, conflicting with
the current ALL ON combination. It also needs the real geometry-authored
WP29 cell and proof. It will use the separate matched profile described here,
compared with both portal-off and normal release. No silent composition change
to ALL ON, no old PCL2 forced activation, and no hardware gain claimed.

The earlier owner prerequisites remain current: author safe hull/eye boxes
from the pinned actual r103 package; return builder proof/refusal and witness
order; then matched baseline/candidate/magenta walks, room/movie lifetime,
refusal, full-image and gameplay gates. Existing explanatory coordinates and
synthetic cases do not establish private coverage. Current live console is
on a benchmark scene, so the matched game-QA session awaits intended disc
selection/redial. No Pi service change or console input was sent this tick.

### Answers (owner): combined actual-data smoke, 2026-10-28

The owner ran one bounded 60-second cache-interpreter/GDEMU-seed1 private
r105 case on full paired ALL ON33 programme/overlays `36643bf8a`, with
QA_LINK=1. The fixture arms Thompson0x34 and opens/closes inventory using
game-side input; no host keys. Original assets remain from the preserved
ALL ON31 extraction; twin mastering checks1648 unchanged files,19 permitted
programme/overlay/fixture differences,0 disallowed. This is a fixture image,
separate from the prepared unmodified console stage `4973e78a`.

Reader exit0, errors empty, overruns0, owned process exited. SSCERT restored1
and subscreen backing hashOK; gameplay continued, not full byte-restore proof.
WPLAN29 f480 planned6720/legacy0, loads1/declines0, bytes17215. AF32UV f360
admitted10206/12861, declined2655 (legacy2295/source360); binding/precision/
nonfinite/begin0, scanned1550281 records. AC32C f1354 tested11927/rejected2555,
near/numeric0. These are actual admissions/refusals, not measured frame gains.

SOB33 f480 cumulative reuse201/saved6432 bytes, completed462/incomplete0,
single346/172, large0/0 and blended0/0. SOB33B barriers55469 with source339,
deferred655,frame482,scene960,list340,send37676,direct15017, other causes0.
Large/blended coverage is absent. The old split counts/441k static vertices
are not removed work. No matched OFF arm or CPU-cost/net timing claim.

Private receipt: owner-allon33-smoke-20261028/RESULTS.json and RESULTS.md,
with exact run/log hashes and raw counters retained locally. Next independent
work is a controlled OFF arm and effective-header/vertex/order traces, then
bounded near/translucent/large/moving-door/retirement cases. Mode2, look,
STRICT, stack/memory, complete absent/zero repacked identity and matched
hardware whole-frame acceptance remain pending. Portal remains parked for
its separate compatible profile and real authored WP29 cells.

Console prerequisite: user selects intended QA disc and establishes REMOTE
LINK; barn baseline comparison is slot154 ALL ON DIAG versus151 baseline,
with matching camera/state and300+ drawn-frame windows. Existing HouseWhole27
Pi benchmark rows are from another earlier session and exact loaded-program
identity remains unresolved; they do not qualify this candidate. No SD write,
recipe enablement or publication.


## EF08 worker delivery, 2026-10-29

**2026-10-29 EF08 target handback: DONE** first queued completion slice is
implemented and target built (`ec1855b42` + scoped Make repair `f5383c0dc`).
Fresh release absent/explicit0 and explicit validation ON pass real rc0,
nonempty ELF and existing empty missing.txt. Baseline77461==absent==zero raw
programme3,372,036B, all15 overlays and all11 allocated ELF sections; debug ELFs
differ. Release and existing solo-portal complete preprocessed/-g0 TU identity
also pass. Actual ON -dM readback verifies20 required1 facts and3 stream/clip0
facts, with the4 propagated facts bound to exact resolved Make values. Original
failedON and initial fixture-only default omission remain preserved.
Host+ASan+UBSan each pass628 checks plus15 Make/source guard cases. Actual
production chunk_emit/end_direct/batch_close/receipt source is exercised with
controlled edges. Completion storage symbols total6,165 B BSS+8 B data before
alignment; queue ticket16B×48. ON local ps2_pass frame10,256B is not whole-stack
or runtime headroom evidence. **NEXT** coordinator review/default-off landing,
then geometry-authored PKG/CFG and matching cells/proof, real lifecycle/magenta/
look/STRICT/memory/net hardware cost. **BLOCKED** those live acceptance gates
remain pending; this first full-source-span class does not close all EF08.
Stream/clip-gather/indexed/subset/multi-LOD and legacy immediate witness
qualification remain excluded. SDK slot released, all runner PIDs exited,
no live exec session. No emulator/media/push/integration/ALL ON change.
Exact profiles, commands, missing private inputs and sanitized receipts:
[PORTAL-COMPLETION.md](../../../tools/cloud/build31/PORTAL-COMPLETION.md).

**2026-10-29 EF08 target checkpoint: DONE** fresh full release absent and
explicit0 builds at `ec1855b42` pass real rc0, nonempty ELF and existing empty
missing.txt. The enabled validation arm correctly stopped before ELF at the
retained early PVS batch guards: native_static lacked propagated TA_DIRECT,
PS2_WORLD_HDR_CACHE, MESH_FASTPATH and PVR_STREAM facts. Failed output is
`/root/probe/lanes/route/out-ef08oct29v1onrP`; runner31774/PID1778329 exited1.
Scoped Make repair now propagates those exact validated Make values only for
completion1; no guard predicate is relaxed. Host checks cover628 cases plus
actual Make/source guard cases. **NEXT** coordinator regrants SDK for a fresh
ON output and actual -dM macro readback, then full OFF/TU identity receipts.
**BLOCKED** ON target is not yet validated; actual source-bound occluder and
lifecycle/look/STRICT/memory/cost gates remain open. SDK slot released; no live
job. Do not retry the unchanged failed label/output.

**2026-10-29 EF08 first completion slice: DONE** source implementation under
new `WORLD_PORTAL_COMPLETION=0|1` default0, preserving the existing portal-only
path absent/zero. Selection issues a scene/view/source-generation/material
bound ticket; actual queued emit/end_direct/batch_close can commit only positive
whole-source coverage. Queued/empty/refused/partial/aborted/clipped/culled work
grants none. Same part/placement, package storage/metadata/cell generation and
current material are checked at flush; observed mutation revokes old receipts.
Only the existing portal+qualified PVS batch composition's early static guard
gets an opt-in exception. Stream/clip-gather/indexed and all other exclusions
remain. Host and sanitizer cover actual runtime/chunk_emit/flush source; original
portal388 checks are retained. **NEXT** serialized target OFF identity and the
explicit queued ON profile in `portal_completion_profiles.json`, then authored
source-bound cells and current-data lifecycle/look/STRICT/memory/cost gates.
**BLOCKED** target slot is not yet granted; private authored wall/cell geometry
with matching package/policy identities is absent from this synthetic gate and
holds actual occlusion/look acceptance only. No SDK/emulator/media job is live.
This first slice supports only complete stored meshlet spans with every strip
group and no clip/cull delta; subset/multi-LOD coverage and legacy immediate
witness qualification remain pending. Source rendering remains the fallback.


## Answers (owner): 2026-10-29 producer, owner-plan and portal integration

DONE: EF02/EF07/EF08 bounded slices landed at `064bfa4ea9936d7570c304fd0735c5837d88546d` through three clean no-ff local delivery merges from042fae809. Delivery branches refreshed the coordinator's later append-only owner notes while retaining exact frozen code/test bytes; original branches and target receipts remain preserved. No source conflict was hand-resolved. Combined default-off release rc0/missing.txt present0, ELF SHA256 `d1740528a367990207948d8326cda6993c922be8c2f0cdc111499c071b8ef18a`; complete programme,15 overlays and allocated section metadata/payloads match the bound77461 baseline. Fresh-base and origin-only push/readback pass.

EF02's real public/private producer correction remains explicit opt-in; actual current a-rig legacy headers are byte-identical to retained release headers, certified streams preserve arrays/order/winding and compiled seven target arrays. Current production assets were not replaced. EF07 retains the actual global wrap-consumer invalidation fence and rejects unknown/ambiguous stamps for raw reuse. EF08's original enabled compile failure remains recorded; the changed scoped propagation repair retained every predicate and passed actual macro readback, corrected ON build and release/solo-portal OFF checks.

ALL ON K24 includes PLAN_OWNER_SCOPED=1 and the first four controls, with QA_LINK=1. WORLD_PORTAL_COMPLETION stays0 with WORLD_PORTAL29=0: its supported compose profile requires STREAM/clip extensions off and private authored-cell proof. It is parked with reason/owner instead of forced into an incompatible stack. Fresh private QA source064bfa4e passes compile, existing empty missing.txt, loader+standard disc lint, ZIP test and staged checksums; track03 SHA256 `387fa0007eb91934905d07c30083c1a52df3e08b9f13d30487084b44c525aee6`. Prepared only; no SD copy or current-QA gameplay/look/STRICT/memory/speed/hardware acceptance. The prior77461 QA's separate45s no-input stock capture reached its menu, with all16 runtime payloads bound; damaged512-NUL raw log remains unmodified. That menu observation is not a scene-draw or memory PASS and is not transferred to this new image.

NEXT/BLOCKED: retain all remaining EF card sub-slices and current-asset/output/lifecycle/look/STRICT/heap/stack/full-cost/console gates. Real portal occlusion still needs authored cells and compatible source/view proof. Private console checks require actual intended media selection/swap and reviewed link readiness at the user's console boundary. Frozen release/Pi/media/look holds remain. Independent next native decoder, immutable world preparation and cloth-sheet work proceeds through existing owners; source fixes do not wait for historical QA reconstruction or a broad census.


## Answers (owner): 2026-10-29 expanded cloud ownership

The user assigns all remaining source/synthetic implementation in this build to the cloud, including the relevant continuations from7c4c9200. See the [ready parallel work, exact file handoffs and next consumed slices](systemic-performance-20261029.md#answers-owner-2026-10-29-all-source-work-cloud-assignment). Preserve the already-running local frozen slices and all existing evidence. Cloud owns their source follow-ons after published landing/file release; local owns private assets, actual runtime/console checks and serialized integration. No full-card or hardware acceptance is implied.


## EF09 worker, 2026-10-29: indexed receipt slice

DONE: guarded WORLD_PREPARED09 default0, requiring the existing part plan;
resolve membership by bounded binary search over the loader-validated sorted
witness table and consume the existing exact ticket at queued flush. No new
allocation or visibility authority. Exhaustive N=0..256 tuple tests measure a
worst case of10 comparisons including final match, not an eight-comparison
universal bound. NEXT: plan incarnation, direct source metadata/record use and
optional conservative static bounds within existing cap/floor; then target
identity. BLOCKED: no SDK slot requested/granted; actual private proof/lifecycle/
look/STRICT/memory/hardware acceptance remain pending. No active job.


## EF09 worker, 2026-10-29: plan lifetime and early consumer

DONE: continued past indexed tickets into actual plan incarnation, exact Room4
allocator-token ownership before payload/free, package token/revision, callback-
safe publication, direct current metadata reference and optional conservative
placement boxes consumed before view setup. Base records retain priority under
64KiB/96KiB-floor; dynamic/root-pose/uncertain cases use the original path and
queued matrix/UV/key copies remain. Actual-source host+ASan/UBSan pass7,107 main
checks,86,420 lookup cases and450 ordered live-policy cases; completion628 checks
remain passing under prepared09. Same-gen/address/size stale close leaves the
foreign replacement intact. Unproven allocator returns are counted and further
attempts latched for that room generation; no memory-saving claim.
NEXT: exact target ON plan/compatible portal profiles, baseline/absent/zero
release+existing plan/portal identity, actual macro readback and full programme/
overlay/allocated-section gates. BLOCKED: SDK slot not yet granted; private
cells/proof, live lifecycle/look/STRICT/memory and net hardware cost pending.
Details/commands: [WORLD-PREPARED09.md](../../../tools/cloud/build31/WORLD-PREPARED09.md).
No active SDK/emulator/media process; no release/ALLON or shared provider edit.

EF09 fixture continuation, 2026-10-29: DONE added same-address foreign-payload
ASan poisoning and reentry during free as well as allocation. Old plan/index/
bounds reject the poisoned replacement; free reentry preserves the newer
publication. Current main checks7,107 and controlled allocation balance17/17
pass normal and sanitized. Runtime/source bytes remain exactly `3ded42ac0`.
NEXT target admission; BLOCKED unchanged live acceptance gates, no active job.

EF09 qualification fixture, 2026-10-29: DONE the literal record-access guard
aborts before reading the ASan-poisoned recycled payload; all four call sites
are present. Main checks7,107 and17/17 allocation balance pass normal/sanitized.
Runtime/Make remain frozen at3ded42ac0. NEXT local target qualification only;
new paging, broader portal composition and mutation/scratch follow-ons belong
to the cloud under the user's updated ownership instruction. No active job.


## EF09 worker, 2026-10-29: frozen target qualification DONE

DONE: runtime/Make3ded42ac0 with qualified test/docs625bf8099 passed four serial
full builds: absent, explicit0, enabled plan, compatible portal; each rc0,
nonempty ELF and existing empty missing.txt. Full OFF programme/15 overlays/
all11 allocated section metadata+payload match bound255964fdc/runtime064.
Entire normalized resolved Make state is equal except new default0 name and
exact own output/tree roots. Actual native_static complete ii/g0 identity passes
release, existing-plan and solo-portal source profiles; actual ON -dM facts/
Make bindings pass both enabled profiles. Host/sanitizer7107+86420(max10)+450,
prepared completion628 retained. Helper/config/binding results are committed in
build31; [details](../../../tools/cloud/build31/WORLD-PREPARED09.md).

Matched plan native_static adds2128 text/85 rodata/12 data/44 BSS bytes; local
ps2_pass9012->9020 and open116->252 bytes. Optional bounds24B/placement remain
secondary within64KiB plan/96KiB heap-floor admission. Counted unproven returns
and enabled-provider costs remain memory acceptance inputs, not savings.
NEXT: owner integration of this bounded slice, cloud-owned source/synthetic
paging/composition/mutation/scratch follow-ons. BLOCKED acceptance only: authored
private cells/proof, current look/STRICT/lifecycle, whole-stack/heap and net
console cost. Queued matrices/UV/material keys remain copied; live policies and
dynamic/uncertain fallback remain. No default/ALLON promotion. SDK session29536/
PID1918610 and TU session62931/PID1944733 exited; slot released. No emulator,
media, push, integration or provider edits. Original frozen trees preserved.

# Engine fixes after Builds 31-36: local agent handover

**2026-10-29 progress 3:** DONE: turned the audit into a ranked [engine-fix backlog][BACKLOG] and changed the execution order to architecture/source analysis, bounded implementation, correctness/coverage validation, then performance comparison. NEXT: implement ready data, ownership and dispatch corrections; extend native coverage using the current renderer and SH4ZAM integration. Console and private-input gaps hold only the checks that require them. This commit changes documentation; the proposed engine fixes are not yet implemented.

**2026-10-29 progress 2:** Revision `461e8c97` removed the initial separate S0-S6 organization and resumed existing build owners, mechanisms and records. The local coordinator integrated it at `60d6aaae3`.

**2026-10-29 progress 1:** Initial handover `b431e453` collected the analysis, existing results and local commands. Its emphasis on qualification was too restrictive for source-demonstrated architectural fixes; the instructions below supersede that sequencing.

**Reviewed integration:** `origin/t15/int` at `df7a42a5e4fa1316ca8f245b6d7feab023e7eddf`. Runtime source was reviewed at `10f13fdc`; later commits only change documentation and owner notes.
**Handover branch:** `codex/systemic-performance-handover-20261029`.
**Audience:** the local coordinator and its assigned implementation agents.
**User direction:** the audit should reveal conceptual defects, establish the right native data model and improve SH4ZAM/Dreamcast renderer coverage. The next deliverable is engine fixes that evolve the current implementation.

## 1. Implementation now, comparison afterward

Use [ENGINE-FIX-BACKLOG-20261029.md][BACKLOG] as the implementation queue. It contains sixteen concrete items with source locations, intended contracts, dependencies, small implementation slices and post-change checks.

A missing source extent, invalid ownership check, stale-cache counterexample, ambiguous submission result or incompatible producer contract is enough to begin a bounded correction. Fix the contract identified in source, validate it, and compare the resulting candidate. A new FPS capture, complete game census or reconstructed historical QA image is not permission to write the fix.

Apply this sequence:

1. State the source defect and intended invariant.
2. Extend the existing producer, data model and consumer together.
3. Build the bounded change and validate its correctness, coverage, lifetime and disabled identity.
4. Compare the candidate's output and full cost using the relevant current workload.
5. Enable, revise or park through the existing local acceptance process.

A correctness repair does not need to earn an FPS improvement to be valid. A coverage repair can add legitimate work by drawing something previously absent. An optimization must justify its total cost after implementation. Compare equivalent visual workloads and keep those three conclusions separate.

Uncertain policy choices still need measured comparison: cache capacity, packing tradeoffs, meshlet sizes, optional approximations and additional far/visibility policies are examples. They do not prevent implementing an already identified ownership or representation fix.

**Evolution constraint:** reuse `Re4dcModelPart`, `Re4dcActorChunk`, `NativeDrawPlan`, actor/room owners, texture `Entry`, world plans and current effect queues. Existing FE decoding, generic native drawing, SH4ZAM/AVK kernels and the native water emitter are already present. Extend their authority and coverage. The backlog does not require another renderer, decoder, resource manager, asset pipeline or instrumentation framework.

The existing real NTSC hardware goal remains 30 fps and the planning budget remains gameplay <=24 ms, rendering <=6 ms with about 3.33 ms margin. These are targets. Preserve the playable menu/New Game -> r100 -> r101 -> r103 route and required simulation, events, collision, AI, animation and camera behavior. [Repository instructions][A0] [Contributor gates][A1]

## 2. What the audit established

The Build 29 source sweep read 1,643 source files / 777,164 lines, discovered 6,257 candidate lines and reviewed 72 groups. Build 36 separately inventoried the supplied 1,664-file private image. The work covers substantially more than the barn; it does not claim every retail asset or runtime state was exercised. The 72 groups include required alternative algorithms, compile-time choices, intentional policies and correct failures as well as fix opportunities. [Source sweep][AUDIT] [Build 36][A9]

The actionable shared causes are:

| Cause | Concrete source finding | Engine response |
|---|---|---|
| Incomplete native data authority | UV pointers lack logical allocation bounds; a real offline wrapper writes older certificate semantics | EF01/EF02: bounded, versioned, owned inputs and matching producer/consumer capabilities |
| Reuse without the right lifetime identity | SOB reads stored generation while checking retirement; PS2 headers lack upload incarnation; draw-owner changes reset unrelated plans | EF05/EF06/EF07, then EF15: correct validity first, targeted reusable state second |
| Ambiguous rendering completion | GX geometry sinks discard data; some adapters ignore native refusal or partial output | EF03 and EF04: explicit outcomes and reuse of validated native decoding |
| Narrow native representations | Cloth has width/material exclusions; effect shortcuts do not cover every primitive/material form; water data selection is fragmented | EF11/EF12/EF13: complete existing native representations and their data inputs |
| Incomplete preparation and batching | Portal completion does not compose with primary producers; world metadata still repeats work; current SH4ZAM wiring leaves useful compatible batches | EF08/EF09/EF10/EF14: prepare immutable work once and batch native rendering under explicit ownership |

These findings justify implementation without asserting how often each occurs or how many milliseconds it will save. The backlog distinguishes confirmed source behavior, counterexamples permitted by the contract and proposed design. Required slow paths and rejected corrupt inputs are preserved.

## 3. Start the engine work in this order

Use the priority and dependency tables in the backlog. EF identifiers are references, not new Build 37+ assignments. Keep existing build/lane owners; the coordinator assigns any new work through the current queue.

| Execution order | First concrete output | Subsequent work |
|---|---|---|
| Ready correctness slices: EF03, EF05, EF06 | Explicit native submission result; SOB owner validation before dereference, including same-frame reset; PS2 texture upload incarnation checked by header reuse | Propagate outcomes, preserve intentional drop policies, exercise stale-address and partial-output cases |
| Foundational data slice: EF01 | Exact source spans and owner/mutation identity carried through the current part/chunk/actor owners | Prepare reusable capabilities; keep conservative checks for mutable/unowned input |
| Ownership and producer completion: EF02, EF07 | Correct existing offline certificates; owner-scoped draw-plan invalidation with probe-chain and lease safety | Regenerate actual assets when private inputs are available; unrelated plans stay usable |
| World preparation: EF08, EF09, then EF10 | Producer completion receipts compose; immutable plan facts and placement bounds have correct lifetime; ordered static spans reuse prepared geometry | Validate real occluders when available; compare cache-build cost separately from per-draw cost |
| Native coverage: EF04, EF11, EF12 with EF14 | Reuse existing FE/native decoding for valid uncovered cases; complete cloth/effect views; compatible SH4ZAM batches | Expand one representation/material class per slice and compare equivalent rendered output |
| Further data reuse: EF13, EF15 | Source-bound water layer definitions; version authority for eligible frontend descriptors | Extend qualified input classes using existing owners and pipeline |

Independent rows may proceed concurrently, but edits to `native_ui.cpp`, `native_model.cpp`, `model_bridge.cpp` and shared headers need one assigned writer at a time. EF01 can proceed alongside the first three correctness slices. EF08/EF09 can begin from existing fixtures without waiting for private portal geometry.

### First commits to make reviewable

For each assigned item, choose the smallest producer-to-consumer slice that leaves a working feature:

- **EF03:** introduce internal outcomes without breaking the public ABI, then propagate one existing strip/cloth route. Distinguish policy skip from resource refusal and partial output. Fallback is allowed only before publication.
- **EF05:** publish the SOB allocation incarnation out of band, check it before every state consumption/retirement dereference, and invalidate pending references. Add same-frame reset/reuse coverage before expanding source-content reuse.
- **EF06:** introduce upload incarnation at texture replacement/close/publication and check it in one existing PS2 header path. Cover same-entry/same-VRAM-address reuse with changed format or mip state.
- **EF01:** add exact guarded spans and owner/mutation information to one current actor producer and consumer together. Preserve the disabled ABI/output and the existing conservative path.

Every code commit remains buildable, has the relevant meaningful check, and updates its assigned handback. Avoid an unused abstract interface commit that no real producer consumes.

### Supporting work stays supporting

EF16 is the existing Build 34 logger publication follow-up. Continue its bounded writer-context/serialization correction with that owner. It is not a prerequisite for EF01-EF15. Current failed memory judgments remain failed until the unchanged gate has valid passing results.

The owner has retained a normal-QA package/source discrepancy and capture provenance work. Keep [those notes][OWNER]. The unqualified QA image cannot serve as a claimed matched control; select a fully bound compatible control when a comparison needs one. Recovering the historical image or finishing a broad census must not occupy the engine implementation's critical path.

## 4. Branches, ownership and continuation commands

Read the current original handover, queue, applicable build owner answer and local `AGENTS.md` / `CLAUDE.md` / `re4-dreamcast-d367` skill before using shared resources. Preserve dirty work, active processes and private results. This is a continuation check, not a new baseline-building milestone.

Run in the existing repository:

```bash
git remote get-url origin
git status --short --branch
git worktree list
git fetch origin \
  refs/heads/t15/int:refs/remotes/origin/t15/int
git fetch origin \
  refs/heads/codex/systemic-performance-handover-20261029:refs/remotes/origin/codex/systemic-performance-handover-20261029
git rev-parse origin/t15/int
git show origin/t15/int:port/dreamcast/docs/cloud/HANDOVER-CLOUD-20261028.md
git show origin/t15/int:port/dreamcast/docs/cloud/CLOUD_AGENT_QUEUE.md
git show origin/codex/systemic-performance-handover-20261029:port/dreamcast/docs/cloud/ENGINE-FIX-BACKLOG-20261029.md
git show origin/codex/systemic-performance-handover-20261029:port/dreamcast/docs/cloud/HANDOVER-SYSTEMIC-PERFORMANCE-20261029.md
```

Confirm `origin` is `lamb2k/re4dc`. Base implementation on the newest integration. This documentation branch supplies instructions.

- Use one branch per assigned build, small commits and default-off controls with the required absent/zero identity. Guard shared layout/ABI changes so disabled builds preserve their existing identity.
- Include a dated DONE / NEXT / BLOCKED line in `docs/cloud/handbacks/build-NN.md` with every implementation commit. Reuse the existing owner format and receipt locations.
- Rebase before pushing, stage only owned files, preserve owner answers and verify the remote SHA. Push to `origin`; the local coordinator performs integration. The current task does not redirect work to `dreamcast-port` or `bruce`.
- Keep code, synthetic fixtures, schemas and sanitized summaries public; keep game data, generated assets, private captures and detailed game inventories outside Git.
- Keep the current builder limits, one exclusive emulator/console window and release/recipe/media holds. Independent source and host work may continue while hardware is unavailable.
- Preserve existing parked-control decisions. Additional visibility-table, clip-reuse or room-far work needs coordinator reprioritization; the backlog is not authority to enable every switch.

The local coordinator continues to own private assets, compatible image composition, hardware scheduling, acceptance and integration. Helpers return findings to the assigned writer rather than editing the same handback concurrently. [Original handover][A3] [Queue][A2] [Repository instructions][A0]

## 5. Landed work and closed checks to retain

All Builds 31-36 are integrated at the reviewed pin. Implementation landing and enabled acceptance are separate states.

| Build | Reuse this completed work | Remaining qualification or extension |
|---|---|---|
| 31 | Generic part plans and conservative portal builder/runtime; 21 builder tests, 388 portal checks, 450 plan cases and recorded OFF target comparisons. Actual private part-plan admission observed. | Private portal geometry/proof, current producer compatibility, lifecycle/memory/look/STRICT and net hardware cost. Portal is parked in the present ALL ON composition. |
| 32 | Guarded cone and UV16 admission, corrected UV precision contract, host/sanitizer and OFF target evidence. Real private admissions/refusals observed. | Named live legacy assets, mode-2 verification, appearance boundaries, memory/lifecycle and separate/combined console cost. |
| 33 | Ordered reuse of identical adjacent final TA headers. Host oracle and OFF checks. Private inventory and r105 -> r101 functional cases. | Actual large/blended targets, aligned effective-header/vertex oracle, demanding-view cost, full enabled lifecycle/look/memory/STRICT. |
| 34 | Review of 17 controls and fixes to eligible existing paths. One control already enabled, two conditional candidates, fourteen parked with reasons. Supported SCPS validation profiles are built. | Missing r103 comparison row, active-table retirement/reentry, reliable memory evidence and enabled console acceptance. |
| 35 | 58 added events, 91 total FA reasons, N=1..64 rolling draw-attempt windows. Disabled executable/repacked-image gate closed on the fixed template. CRLF journal repair, complete automatic snapshots, one coherent N32 sample and static BSS ledger retained. | Explicit DIAG still 4/14 parts; marked 600-draw and lifecycle validation, observer CPU cost, whole-stack/headroom, current memory and hardware qualification. |
| 36 | Final composed private image rescan completed; 144 tests and 126 OFF artifact comparisons retained. 1,664 inputs unchanged; 12,589 models inventoried, including 211 legacy geometry models. | The report remains INCOMPLETE: source-bound selection/membership, five route gaps and legacy policy gaps. No scanner correction was requested by that scan. |

Sources: [Build 31][A4] [Build 32][A5] [Build 33][A6] [Build 34][A7] [Build 35][A8] [Build 36][A9].

### Closed gates that must not become busywork

- **Build 35:** baseline/absent/zero raw programme, all 15 overlays and allocated ELF sections match. Independent programme replacements into the same fixed composed asset template produced byte-identical GDI and all three tracks. Whole debug ELFs differ. This closes that scoped OFF gate; it does not establish fresh mastering reproducibility or enabled acceptance.
- **Build 33:** programme, overlays, allocated sections and all 1,667 ISO file payloads match. Raw-track differences are fully localized to timestamp metadata, with zero unclassified bytes. Raw hashes still differ. Retain this exact conclusion.
- **CRLF:** the reviewed companion repair `730d8f910` already recovers complete automatic T snapshots from unchanged retained journals. It does not repair the RAM log or complete the separate D response.
- **Observer storage:** gaps adds 17,312 allocated BSS bytes over existing audit; window32 adds a further 31,040 bytes. Selected local frames and a configured 65,536-byte kernel-thread stack are recorded. These are not runtime headroom or whole-stack bounds.
- **Build 36:** do not repeat the same OFF/ON private scan without changed source, room scope, context or input data.
- Reuse any receipt only while its bound source, definitions, toolchain, relevant input and output identities still apply. Repeat affected checks when those dependencies change. [Build 33][A6] [Build 34][A7] [Build 35][A8] [Build 36][A9] [Build 28][A10]

## 6. Validate the changed contract, then compare

A code slice is implemented when its producer/consumer contract is complete, affected builds pass, disabled identity holds and targeted checks exercise the real failure boundary. Hardware qualification and enabling are separate states.

| Change | Required correctness comparison | Useful cost comparison afterward |
|---|---|---|
| Ownership/data spans | Truncation, mutation, same-address reuse, generation wrap, leases and retirement | Validation scans, metadata, rebuild work, lifetime overlap |
| Native draw routing | Submitted/queued/skipped/refused/partial distinctions, no duplicate fallback, effective output/order | Restored coverage and equivalent-output CPU/traffic cost separately |
| Cache/plan reuse | Current texture state, colliding owner entries, live aliases, leave/reentry and movie loans | Header/setup work, invalidation/rebuild cost, memory and full frame |
| World/visibility | Current scene/view, actual producer completion, conservative bounds, real occluder proof | Rejection before work, surviving work, traffic and total time |
| Cloth/effect/SH4ZAM | Winding, UV/material semantics, clipping, current pose, aliasing, matrix ownership and required simulation identity | Calls/loads/row transforms, stack/workspace, complete cost |

Use existing host/target fixtures and current renderer oracles. Extend only the cases needed for the changed boundary. Retain valid unchanged receipts; repeated broad scans and unrelated suites are not a new implementation gate. Short emulator checks remain within the existing one-minute-per-scene procedure. Real route/reentry checks are needed where lifetime or STRICT behavior changes. [Contributor gates][A1]

For private comparisons, use a compatible source/definitions/toolchain/asset pair, the same workload and quality policy, and a valid timing denominator. State what actually rendered. Label host correctness, emulator function, modelled cost and console timing accurately. Record observer cost when it affects the measurement.

Retain existing counter meanings: N32 is 32 completed draw-attempt ticks, not presentations or a whole 600-draw interval; FA29T totals can include skipped/asynchronous activity; a missing capture is not zero. These rules govern interpretation of a comparison. They are not reasons to postpone the source fix. [Build 35][A8] [Build 28][A10]

A correct repair may be retained despite a cost increase; optimize its implementation next. A restored effect must be judged against the intended rendering requirement. A pure optimization that loses overall should be revised or parked. Promotion still requires the affected look, memory, lifecycle, gameplay and hardware gates.

## 7. Private-input handback and the next useful action

When a slice reaches a real game-data or console boundary, write the exact next commands in its assigned handback and move to an independent ready item. Do all available source, synthetic and target-build work first. Do not invent private filesystem paths or an unimplemented test command.

The handback needs only what the next owner requires: EF/build and commit, changed contract, checks already passed, exact missing input, executable command with the local paths or explicitly named required variables, expected output/verdict, and the next independent task. Use the existing records; no new mandatory ledger is required.

Examples of legitimate boundaries:

- EF02 can correct runtime/public fixtures now; regenerated private blobs need the actual producer and original asset inputs.
- EF08 can implement receipt composition now; enabling real occlusion needs a valid geometry-authored cell and current-view coverage proof.
- EF11/EF12 can implement native primitive/material contracts now; private look checks establish which actual effects and outfits are complete.
- Any performance candidate can remain implemented and default off while a matched console comparison is pending.

Section 8 retains actual existing commands for those boundaries. The local owner adds the exact new feature/build/fixture command as the implementation makes it concrete. An unavailable result is recorded against the affected acceptance question, not promoted to a universal stop.

**Next local update:** name the assigned EF item and first implemented slice, the invariant now enforced, build/disabled identity and targeted correctness result, then any private comparison still needed. Continue the existing build owners and carry accepted changes forward.

## 8. Existing commands for the point that needs them

These are existing entrypoints collected for convenience. Prefer the exact retained owner command when its source and inputs still match. Private variables must name actual local inputs. Running this entire section is not a new checklist; use only the command needed to close the current build's next gap.

### 8.1 Scan the explicit supplied scope

Reuse the owner's current verified room list, adding source-confirmed rooms only when extending scope. `SYSTEMIC_ROOMS_FILE` is a text view of that list with one room ID per line, comments allowed; it does not require a new manifest system. Keep expected missing rooms. Set all four private variables before running. Output must be new and outside the input tree.

```bash
set -euo pipefail
test -d "$PRIVATE_DISC_TREE"
test -f "$IMAGE_KNOBS"
test -f "$SYSTEMIC_ROOMS_FILE"
test -n "$SYSTEMIC_SCAN_OUT"
test ! -e "$SYSTEMIC_SCAN_OUT"

SYSTEMIC_ROOMS="$(
python3 - "$SYSTEMIC_ROOMS_FILE" <<'PY'
from pathlib import Path
import re, sys
rooms = set()
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    item = line.split("#", 1)[0].strip().lower()
    if not item:
        continue
    if not re.fullmatch(r"r[0-9a-f]{3,4}", item):
        raise SystemExit(f"invalid room ID: {item!r}")
    rooms.add(int(item[1:], 16))
if not rooms:
    raise SystemExit("empty verified room manifest")
print(",".join(f"r{room:03x}" for room in sorted(rooms)))
PY
)"

set +e
python3 -B port/dreamcast/tools/d367/fallback_scan/scan.py \
  "$PRIVATE_DISC_TREE" \
  --out "$SYSTEMIC_SCAN_OUT" \
  --rooms "$SYSTEMIC_ROOMS" \
  --knobs "$IMAGE_KNOBS" \
  --scan36=1 --strict
SYSTEMIC_SCAN_RC=$?
set -e
if [ "$SYSTEMIC_SCAN_RC" -gt 1 ]; then
  exit "$SYSTEMIC_SCAN_RC"
fi
```

Exit 0 means recognized/requested static coverage is satisfied; 1 writes an INCOMPLETE report; 2 indicates an invocation/context/output failure. Preserve the actual report verdict. None of these establishes runtime or whole-retail-game acceptance.

Existing outputs are `details.tsv`, `by-model.tsv`, `by-room.tsv`, `barn.tsv`, `spawns.tsv`, `coverage.tsv`, `report.json`, `context-template.json` and `REPORT.md`. The specialized barn file does not restrict the rest of the scan.

Use `--context`, `--room-list` and `--input` only according to their existing source/hash schemas. An untouched context template grants no new authority. `--texpak-layer` means explicit ordered whole-pack replacement, not entry union. [Build 36][A9] [Scanner README][A12]

### 8.2 Reuse the owner's input manifests

The completed Build 36 run already retained a complete before/after manifest for 1,664 files. Reuse that evidence for the unchanged extraction. For a new extraction, changed input set or rerun, use the owner's established complete-file manifest command and compare before/after file paths, sizes and SHA-256 values.

Record the actual command and manifest hash in the existing private result. Keep input trees quiescent. The scanner's recognized-input hashes do not replace the complete-file check. Do not introduce another hashing utility or report schema where the current one already supplies the evidence. [Build 36][A9]

### 8.3 Existing room discovery and portal builder

Reuse existing room discovery with the local asset-pipeline configuration. Its historical `route` alias covers r100/r101/r103; repeat source-verified individual rooms as supported.

```bash
bash port/dreamcast/tools/d367/assets.sh discover r100
```

For a real geometry-authored portal configuration, use the Build 31 commands. `PKG`, `CFG`, `BASE_FIXTURE` and a fresh `PORTAL_OUT` must name actual private inputs. Explanatory schema coordinates are not room geometry.

```bash
set -euo pipefail
test -d "$PKG"
test -f "$CFG"
test -f "$BASE_FIXTURE"
test ! -e "$PORTAL_OUT"
mkdir -p "$PORTAL_OUT"
sha256sum "$PKG/ps2-world.re4mesh" \
  "$PKG/ps2-world.r4pw" "$PKG/ps2-world.ids"
python3 -B port/dreamcast/tools/d367/ps2world/interior/barn_portals29.py \
  --barn-portals29=1 --config "$CFG" --package "$PKG" \
  --out "$PORTAL_OUT/interior.cell" \
  --report "$PORTAL_OUT/portal-proof.json"
python3 -B port/dreamcast/tools/d367/ps2world/interior/graft_portals29.py \
  --barn-portals29=1 --fixture "$BASE_FIXTURE" \
  --cell "$PORTAL_OUT/interior.cell" \
  --out "$PORTAL_OUT/fixture-portals29.json"
```

The filename retains "barn"; the builder supports multiple buildings in explicitly named rooms. Use the exact supported build compositions in the latest Build 31 handback, and the corrected helper/profile commands in Build 34. Do not paste a union of all switches into a build command. [Build 31][A4] [Build 34][A7] [Portal contract][A13] [D367 tools][A14]

### 8.4 QA link readiness and marked capture

The latest owner notes found the Pi service in legacy mode, with its installed CLI rejecting `--review28`. Prepare backed-up compatible PC/Pi companion maintenance at an appropriate console boundary. Preserve the active session and use the owner service procedure; do not start a second service. The console build also needs the reviewed protocol.

After an actual media swap, the user selects the intended QA disc and establishes REMOTE LINK. Retain verified programme/image identity and PING/PONG, not merely a connected status. [Build 28][A10]

Existing entrypoints:

```bash
python3 port/dreamcast/tools/qalink/qalink.py --help
python3 port/dreamcast/tools/qalink/qalink.py \
  --pi "$QALINK_PI" --review28 --out "$PRIVATE_CAPTURE_OUT" status
python3 port/dreamcast/tools/qalink/qalink.py \
  --pi "$QALINK_PI" --review28 --out "$PRIVATE_CAPTURE_OUT" send PING
```

The following is the existing reference manual sequence after readiness and selected preset/camera are verified. It does not implement an automatic 600-draw stopping condition. Use the current session workflow and valid runtime denominators; extend its stopping condition only if needed to close the existing Build 35 interval gate.

```bash
set -euo pipefail
VIEW=systemic-view01
ql() {
  python3 port/dreamcast/tools/qalink/qalink.py \
    --pi "$QALINK_PI" --review28 \
    --out "$PRIVATE_CAPTURE_OUT" "$@"
}
ql send MENU
ql capture start "$VIEW"
ql send RESUME
read -r -p 'Verify at least 600 completed draw-attempt ticks, then press Enter: '
ql send MENU
ql send DIAG
ql capture stop "$VIEW"
```

Capture duration or RECORD ticks are not automatically completed draw attempts. If a required interval cannot fit the approved emulator envelope, return the actual timing conflict to the coordinator. Do not silently extend it or assemble unrelated windows into an exact interval. Capture summaries average coherent snapshot fields; they do not automatically calculate cumulative-counter deltas or per-draw rates. [Build 35][A8] [Build 28][A10] [QA link README][A15]

### 8.5 Relevant regression entrypoints

Run only suites affected by changed code/inputs or a required gate. The existing receipts remain evidence for unchanged code. Use fresh private `OUT` subdirectories.

```bash
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_scan.py' -v
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_*36.py' -v
python3 -B port/dreamcast/tests/test_texpack_index.py
python3 -B port/dreamcast/tools/cloud/build36/verify_identity.py \
  --base bb5f18e0e3b3fac4c76bd42d0c9d8107385c568c \
  --out "$OUT/build36-off-identity.json"
```

The Build 36 historical OFF baseline above is intentional. A new scanner extension also needs its own current-base comparisons.

```bash
python3 -B port/dreamcast/tools/cloud/build35/trans_events.py \
  --output "$OUT/trans-events"
python3 -B port/dreamcast/tools/cloud/build35/trans_events.py \
  --sanitize --output "$OUT/trans-events-sanitized"
python3 -B port/dreamcast/tools/cloud/build35/window_host.py \
  --output "$OUT/window-host"
python3 -B port/dreamcast/tools/cloud/build35/window_host.py \
  --sanitize --output "$OUT/window-sanitized"
python3 -B port/dreamcast/tools/cloud/build35/window_qa.py \
  --output "$OUT/window-qa"
python3 -B port/dreamcast/tools/cloud/build35/window_qa.py \
  --sanitize --output "$OUT/window-qa-sanitized"
python3 -B port/dreamcast/tools/cloud/build28/companion_contract.py \
  --base c528a4dc7d0cf47e6c71486a7c2cfe9cb2940266 \
  --receipt "$OUT/companion-contract.json"
```

The companion base is the owner-verified base for the current 34-case CRLF repair; its older default has a known later-marker comparison mismatch. Use the complete relevant Build 35 suite for changes to other event families. Existing build/public-image, STRICT and KOS commands remain in their linked handbacks and local skill; bind them to the actual private inputs rather than inventing a portable one-command whole-disc rebuild. [Contributor gates][A1] [Build 35][A8] [Build 36][A9] [Build 28][A10] [Build 35 tools][A16]

## Sources

The source sweep and runtime files support the conceptual findings; the backlog links the exact implementation paths and functions. Build handbacks support the retained completion and qualification states. Runtime review at `10f13fdc` remains applicable at the docs-only integration `df7a42a5`. Read newer owner answers before acting.

[BACKLOG]: ENGINE-FIX-BACKLOG-20261029.md
[AUDIT]: handbacks/build-29-sweep.md
[OWNER]: handbacks/systemic-performance-20261029.md
[A0]: ../../../../AGENTS.md
[A1]: ../../CONTRIBUTING-PORT.md
[A2]: CLOUD_AGENT_QUEUE.md
[A3]: HANDOVER-CLOUD-20261028.md
[A4]: handbacks/build-31.md
[A5]: handbacks/build-32.md
[A6]: handbacks/build-33.md
[A7]: handbacks/build-34.md
[A8]: handbacks/build-35.md
[A9]: handbacks/build-36.md
[A10]: handbacks/build-28.md
[A11]: handbacks/build-29-barn-exit.md
[A12]: ../../tools/d367/fallback_scan/README.md
[A13]: ../../tools/d367/ps2world/interior/PORTALS29.md
[A14]: ../../tools/d367/README.md
[A15]: ../../tools/qalink/README.md
[A16]: ../../tools/cloud/build35/README.md

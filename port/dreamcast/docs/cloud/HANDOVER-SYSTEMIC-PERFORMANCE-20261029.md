# Systemic performance: local agent action plan and handover

**2026-10-29 progress:** DONE: architecture, ranked action plan, evidence inventory and local execution handover. NEXT: local owner completes S0 intake and starts S1 observation qualification alongside S2 coverage. BLOCKED: enabled performance acceptance requires private inputs and matched console evidence. This document adds no runtime implementation or performance result.

**Reviewed integration:** `origin/t15/int` at `66da801e7ff457f84d52c4bb379cdaae7aa07e35`.
**Handover branch:** `codex/systemic-performance-handover-20261029`.
**Audience:** the local coordinator and its assigned implementation agents.
**User request:** solve the recurring causes systemically and create a detailed action plan and handover in GitHub.

## 1. Mission and execution boundaries

Deliver shared renderer and asset-pipeline improvements that reduce CPU work and memory traffic across eligible game content. Use the barn, village and other demanding scenes to validate common mechanisms. A successful milestone produces a compatible rendering configuration, documented content coverage and measured gains with preserved gameplay.

The repository's existing real NTSC hardware goal is 30 fps, with a planning budget of gameplay <=24 ms, rendering <=6 ms and about 3.33 ms margin. These are targets, not current measurements or a promise that every supplied room already meets them. Preserve the playable menu/New Game -> r100 -> r101 -> r103 route while broadening the coverage inventory. [Repository instructions][A0] [Contributor gates][A1]

The governing approach is:

1. Prepare immutable facts during conversion or loading where their ownership and lifetime permit it.
2. Reject unnecessary render work before selection, setup, transformation and submission.
3. Preserve required simulation, activation, collision, events, AI, camera state and animation.
4. Measure complete cost, including validation, cache traffic, memory, retirement and feature interactions.
5. Keep a correct ordinary rendering path for unsupported, stale or unaffordable inputs.

Extend the existing native renderer, converters, storage and lifecycle mechanisms. Inspect their contracts and the preserved implementations before proposing a replacement architecture. New SH-4 assembly or linker work requires evidence that removing repeated work, data layout, batching and offline conversion cannot address the problem. [Repository instructions][A0] [Cloud queue][A2]

### Ownership and Git rules

- The local coordinator owns private assets, image composition, source-state comparison, emulator scheduling, console qualification and integration decisions.
- Implementation agents own bounded source/tool changes and their synthetic/target evidence. They use isolated branches/worktrees and avoid overlapping shared-file edits.
- Continue from the newest `origin/t15/int`. This task does not redirect work to `dreamcast-port` or `bruce`.
- Keep new controls default 0; preserve absent/zero source, object and executable identity at the appropriate gates. Use small buildable commits and a dated done/next/blocked line in the assigned handback with every commit.
- Rebase onto current integration before pushing. Stage only owned files. Preserve owner answers and unrelated edits. The coordinator performs merges.
- S0-S6 below are work-package labels, not newly allocated Build 37+ assignments. The coordinator may map them to its queue. Agents must not overwrite `CLOUD_AGENT_QUEUE.md` to claim ownership.
- Keep game data, generated copyrighted assets, disc images, private captures and detailed asset inventories outside Git. Publish code, schemas, synthetic fixtures and sanitized evidence summaries.
- Preserve the established owner process for recipe promotion, physical media changes and release publication. A documentation or implementation commit does not qualify a release.
- Honor the local owner's current builder limits and reserve one exclusive emulator/console window. Read-only analysis and independent host work may proceed in parallel. [Repository instructions][A0] [Cloud queue][A2] [Original handover][A3]

## 2. Start here

Read the current versions in this order:

1. [HANDOVER-CLOUD-20261028.md](HANDOVER-CLOUD-20261028.md).
2. [CLOUD_AGENT_QUEUE.md](CLOUD_AGENT_QUEUE.md), including its current Status rows.
3. This handover and the latest **Answers (owner)** in Builds 28 and 31-36.
4. Local `AGENTS.md`, `CLAUDE.md` and the local `re4-dreamcast-d367` skill, if installed, for current paths, active lanes and harness contracts. The current D367 instructions identify older Astra/Sol and cutover assignments as historical. Do not revive an obsolete branch or assignment from those sections.

The source pin above is a reviewed snapshot. At intake, record newer commits and owner answers before deciding that a listed gap remains open.

### Safe intake commands

Run in the existing repository, without switching or cleaning its working tree:

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
git show origin/codex/systemic-performance-handover-20261029:port/dreamcast/docs/cloud/HANDOVER-SYSTEMIC-PERFORMANCE-20261029.md
```

Confirm that `origin` is the expected `lamb2k/re4dc` repository. Inspect active local processes and lane ownership before using shared build directories or the emulator. Preserve dirty work.

For a newly assigned implementation lane, use a fresh absolute worktree path and an unused descriptive branch name:

```bash
set -euo pipefail
test -n "$SYSTEMIC_WORKTREE"
test ! -e "$SYSTEMIC_WORKTREE"
SYSTEMIC_BASE="$(git rev-parse origin/t15/int)"
git worktree add -b codex/systemic-observation-20261029 \
  "$SYSTEMIC_WORKTREE" "$SYSTEMIC_BASE"
```

The observation branch name is an example for S1. Use separate assigned branches for other implementation packages. Read this handover from its remote branch; do not base runtime work on an unmerged documentation branch.

## 3. Evidence carried forward

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

## 4. Analysis: causes, evidence and limits

### World work is the leading shared opportunity

The barn audit traces outdoor geometry through ordinary frustum/distance/state selection despite opaque walls. A generic earlier visibility decision can prevent placement, part, matrix, transform and submission work. The existing part plan can reduce repeated setup for geometry that remains visible.

The reported outward/inward CPU readings are about 45/33 ms, with 10.8/21.1 FPS and a separate roughly 12 ms graphics-work reading. Treat the 12 ms CPU difference as something to explain with matched phase rows. It is not a proved 12 ms world-only saving, and those unlike windows must not be combined into an FPS calculation. [Barn source audit][A11]

### Character cost has both algorithm and asset causes

Historical console barn readings improved from 5.0 to 9.5 FPS with the common fast-lighting path, and to 12.1 with the earlier ALL ON image. These are prior measurements, not acceptance of the final Builds 31-36 configuration. Cone/UV admission and any asset conversion must now be assessed on the current source and selected actors. [Original handover][A3] [Build 32][A5]

### Repeated setup is a distinct cost from vertex processing

Build 33 saves adjacent identical 32-byte polygon headers. It retains each placement's transforms, lighting, binding, generated vertices and SQ lock pairs. The old 441k-vertex `m_obj_split` inventory is potential structural coverage, not eliminated work. Cache hits, boundary calls and successful admissions also need timing before they can be valued. [Build 33][A6]

### Memory traffic constrains every proposal

The recorded real-console cache experiment changed r101 from 49.3 to 57.5 ms when half the data cache became scratch memory. Count data lines, access order, loads/stores, resident bytes and overlap alongside arithmetic. Additional metadata or random lookup traffic may outweigh a saved computation. [Cloud queue][A2]

### The scan covered a supplied tree, not all runtime states

Build 36 recursively inventoried supported files in the supplied final image. Its requested room reports were r100-r120 plus r200. The prepared older TOUR28 has 33 chapter 1-2 presets. Neither is a complete room-by-room performance census of the game. Keep three denominators separate: content supplied, content scanned, and runtime states visited. [Build 36][A9] [Build 28][A10]

## 5. Ranked work and dependencies

S1 and S2 are enabling work; S3-S5 retain the expected impact order of world, actors, then repeated state. Use the census to revise that order when actual cost contradicts the hypothesis.

| Package | Concrete outcome | Lead responsibility | Can proceed while hardware is unavailable? |
|---|---|---|---|
| S0: intake and ledger | Current source/image/recipe/input identities, active ownership and closed/open gates | Local coordinator | Yes |
| S1: dependable observation | A qualified memory observation contract and complete bounded diagnostic delivery | Local owner plus a narrowly scoped code lane | Source/host work yes; final hardware gates wait |
| S2: content and workload coverage | Authoritative room manifest, source-bound asset selection and a broad workload ranking | Private-data owner plus tool lane | Static and emulator coverage yes |
| S3: common world path | Measured part plan, reusable portal data workflow and a qualified compatible producer path | World lane | Builder/source/oracles yes |
| S4: actor eligibility | Supported converter metadata and justified runtime validation for live costly actors | Actor/converter lane | Source/converter/host work yes |
| S5: repeated state | Qualified header/cache reuse and only measured upstream extensions | State/submission lane | Source/oracles/lifecycle fixtures yes |
| S6: integrate and decide | Compatible profile, workload matrix, hardware cost and explicit enable/hold/park decisions | Local coordinator | Prepare evidence; final decisions require their gates |

Dependency rule: S0 precedes implementation; S1 and S2 proceed independently; S3-S5 may develop against existing contracts while S1 is blocked. Reliable observations and live workload identity are required before performance promotion. S6 uses accepted results from the relevant lanes. Do not make an entire-game census a prerequisite for a provable shared code fix.

### S0. Freeze evidence and establish ownership

**First actions**

1. Record current integration, local dirty state and active lane/process ownership.
2. Inventory retained normal-release, existing-audit, gaps and window32 images, plus the separate front/SCPS validation families.
3. Bind source SHA, full resolved definitions, toolchain, fixture/save/input script, emulator binary/settings, programme, all overlays, image tracks and supplied asset manifest.
4. Record which historical receipts remain reusable and which inputs actually changed.
5. Create the local execution handback and the coverage/experiment ledgers below.

**Done when:** each upcoming experiment names a real control and candidate with exact identities, a single question and a responsible owner. Existing failures remain visible. No image is described merely as "latest" or "ALL ON."

### S1. Repair the observation contract, then complete the snapshot path

**Memory question:** can the unchanged stock judge receive all required evidence from a source-bound, correctly published and correctly observed stream?

Two retained 60-second memory runs explicitly failed the stock judge. Held-allocation readback was empty; one run also had malformed numeric rows. Reader exit 0, zero overruns and zero OOM strings do not override the FAIL verdict. The 64 KiB observer rings were the expected size. [Build 34][A7]

The source/ELF review establishes two risks, not a sole root cause:

- `re4dc_log_raw` can publish a head after overlapping writers have overwritten a byte; an interleaving counterexample leaves a NUL hole without a reader overrun.
- `read_log.py` reads Flycast's raw host RAM backing. Copy-back CPU cache contents need not already be visible there. Exact binary/cache-state provenance was incomplete.

**Action sequence**

1. Bind the failed captures to the actual logger machine code, writer contexts, reader, emulator binary and active cache state.
2. Define the required publication contract: writer serialization, complete records, payload visibility before published head, wrap behavior and reader visibility across cache aliases.
3. Select one changed-input repair experiment that discriminates the identified cause. Keep the stock judge and the fixed observer budget. Use a separate default-off control for a new runtime change.
4. Prove deliberate writer interleavings, wrap, partial publication and the actual cache visibility mechanism with targeted fixtures. Keep formatting and large copies outside long IRQ-disabled regions; report interruption cost.
5. Run a bounded matched memory pair, retaining active track01/fixture identity before teardown. Require complete authentic judge inputs and an explicit valid PASS or FAIL from the unchanged judge. A valid memory FAIL can close the observation-contract question while blocking that candidate's memory acceptance.
6. If capture is incomplete or malformed, record the unresolved observation contract and the next discriminating change. If a valid capture fails memory acceptance, investigate the actual allocation/headroom failure separately. Do not repair malformed numbers, enlarge/shrink logs to make the result pass, waive fields or repeat an identical capture.

Current structured QA rows expose current free/used/brk. They do not supply the held amount, watch minimum, keepcost/top-block information, required aggregate OOM/MISSING/HALT accounting or exact scene-end event. B/L forwarding uses the same RAM ring. A structured replacement is a separate design and must first prove semantic equivalence for every required judge input. [Build 34][A7]

**Snapshot question:** can one explicit diagnostic request deliver every part of one immutable snapshot in the supported run envelope?

1. Reuse the qualified stock PPP runner and reviewed CRLF companion. Keep the current observer size.
2. Record peer arrival, verified PONG, request time, snapshot creation, queue/send events and received parts.
3. Schedule the request at the earliest verified ready point. The retained pilot reached PPP late in a 60-second run; diagnose scheduling before adding a new capture.
4. Require all advertised consistent parts from one immutable snapshot, correct session/build identity and successful complete-response status. The retained window32 profile advertises 14 parts. Automatic T completeness does not close its explicit D 4/14.
5. If the supported schedule cannot fit, return the measured transport budget and exact conflicting constraint. Preserve INCOMPLETE; do not silently extend the run or accept partial output.

**Done when:** the relevant observation contract is qualified, the stock memory judge has a valid complete result, the explicit snapshot is complete, and observer CPU/static/stack/runtime headroom limits are recorded. Source and asset lanes continue while any hardware-specific part is held. [Build 34][A7] [Build 35][A8] [Build 28][A10]

### S2. Build an honest content and workload census

**A. Establish the universe**

Create an authoritative room/preset manifest from the final composed image, loader/source tables and staging manifest. Reconcile expected rooms against supplied directories and supported launch methods. Keep missing expected rooms in the manifest. A recursive directory list alone cannot establish that the entire game is supplied.

For each room/state distinguish `supplied`, `scanned`, `supported-launch`, `visited`, `matched` and `accepted`. Record unsupported formats and unavailable game stages explicitly. Keep global players, weapons, items and retained enemy lists in the inventory even when they have no unique room.

The scanner has no `--all-rooms` flag. Its default room filter is r100-r11f. Use the verified explicit room list in section 8.1. [Build 36][A9] [Scanner README][A12]

**B. Resolve selection with evidence**

The current report retains 612 unassigned models, five route gaps (r110, r114, r115, r116, r120), four missing exact ESL archive candidates and 13 unresolved `emleon09` records. The active stage selector 9 names `omake01`; the filename suffix cannot establish a binding. Conditional archive membership does not establish a live actor.

Texture selection has 7,375 conditional keys, not zero textures. Actual room Original/Standard quality and lookup state are needed to identify effective variants. Whole-pack replacement is distinct from duplicate entries within one physical pack. Legacy geometry-only inventory does not invent material, placement or selected-LOD facts. [Build 36][A9]

First reuse existing discovery, F29 identity rows and loader evidence. If they cannot bind costly live selections, add a bounded optional load/selection trace containing room generation, owner/source identity, selected model/appearance, texture-quality choice and retirement. Emit on meaningful selection/lifetime changes; avoid per-vertex logging. Hash names and payloads offline where practical. Bind trace IDs back to exact private source hashes.

**C. Expand runtime coverage**

Start from the retained 33-preset tour as a seed. Bind a refreshed tour to the actual candidate image and source. Add source-verified rooms and representative states; mark unavailable later-game content instead of claiming it was tested.

Collect world/actor/setup/clip/effects/gameplay phase cost where supported, actual reason units, draw-attempt denominators, memory context, asset selection and transitions. Rank shared causes by measured exclusive cost and workload frequency. Keep MODELLED estimates visibly separate.

**Done when:** every expected room has a coverage status, the highest-cost visited workloads are source-bound, selection gaps are explicit, and the next renderer task is justified by an observed shared cause. Unresolved static candidates may remain in the ledger; do not manufacture completeness.

### S3. Complete the shared world path

**First reuse and measure the part plan.** It already builds ordered immutable spans once per room. Preserve live material/UV state, camera/placement transforms, texture resolution and submission. Preserve the existing 64 KiB plan cap plus alignment and checked 96 KiB heap floor unless a separately measured budget change is justified.

Compare high-eligibility and low-eligibility scenes. Record plan loads/refusals/bytes, setup cost, total CPU time, room generation, inventory/movie lending and retirement. A high planned-part count is activity, not a gain. [Build 31][A4]

**Then make portal content production repeatable.**

1. Produce one real package-bound r103 hull/eye configuration and proof with the existing builder.
2. Generalize candidate discovery and proof reporting across eligible building packages. Automate suggestions; retain explicit authority for safe eye cells and opaque static coverage.
3. Preserve cracks, all openings, LOD coverage, margins, dynamic/breakable/cutout exclusions and current-view completed-wall witnesses.
4. Record every package as eligible, refused with reason, unsupported or not yet assessed. Missing/stale/malformed/complex/heap-short data uses ordinary drawing.

**Resolve producer composition as its own engineering task.** The currently qualified portal profile disables stream/submit batching and the clip gather/indexed paths, along with incompatible source-removing combinations. Trace exactly which producer paths cannot furnish valid completed-wall witnesses. Extend the shared producer contract only where the proof can be preserved. Removing Make guards is not a fix.

Use four clearly named comparisons:

- Current normal release or current accepted production profile.
- Supported portal-profile control with portal off.
- The same supported profile with portal on.
- Any newly compatible profile, compared to its own control and to current production.

A gain against the slower special control must pay back any lost production optimizations before promotion.

**Acceptance:** synthetic/actual-source proofs for the changed contract; real magenta walks through doors, windows, seams and near/FOV boundaries; correct dynamic state, all relevant LODs, room reentry and movie lending; missing/stale/heap fallback; look and STRICT; bounded memory; net hardware cost including witnesses and survivor setup.

Visibility tables, more clip reuse and room-far approximations remain conditional follow-ups. Open one only if measured residual phase cost supports it. Keep deliberate distance/appearance reductions separately identified. [Build 31][A4] [Barn source audit][A11] [Portal contract][A13]

### S4. Make actor eligibility a supported asset contract

Use actor-heavy matched scenes covering Leon, Ashley, Ganados and El Gigante. Bind actual appearance, motion, lighting, texture state and camera. Compare cone-only, UV16-only and combined arms on the same fast-lighting baseline.

1. Join live refusals to exact selected model/source identities.
2. If legacy FE3 assets dominate measured cost, recover the real packer, representation, signedness and source lineage. Extend that converter to emit valid metadata. Do not relabel old blobs as certified.
3. Preserve the repaired UV interval/interpolation and actual bound-texture precision checks, cone quantization/numeric/near checks and ordinary fallback.
4. Measure repeated source validation before proposing to move it to load time.
5. Any cached admission needs real allocation extent, owner generation, mutability policy and invalidation on replacement/reload. The current actor API does not provide UV allocation length; pointer equality and RAM containment do not establish immutable ownership. Keep texture-dependent and other live checks at the necessary runtime point.

**Acceptance:** actual admissions on intended targets; exercised mode-2 verification with bad=0; unsupported/mutable/near/cull refusals; seams, clipping, masks/fades, animation, LOD and texture dimension/scale changes; unload/reload; fast-only lighting fallback/exact counters remain zero where required; STRICT/look/memory; net console cost including scans, packing and split growth.

UV16 retains 32-byte CPU SQ slots. Relevant PVR internal fields shrink from 24 to 20 bytes, while CPU validation/packing is added. Do not claim halved CPU output bandwidth. The historical global CPU-backface regression is distinct from guarded actor cones. [Build 32][A5]

### S5. Remove repeated state according to measured cost

Qualify existing mechanisms before adding a larger batch architecture.

- **Build 33:** find actual source-bound single-part, above-16-part and blended targets. Existing mapping establishes useful single-part targets but no confirmed large/blended target. Compare every vertex with its effective final header in original order, at aligned source tick/pose/view. A raw stream hash legitimately changes when redundant headers disappear.
- **Front texture cache:** retain exact descriptor/dimension/wrap checks and invalidation. Measure hits/builds/refusals, current memory and CPU cost. High hit counts do not establish net benefit.
- **SCPS:** use the existing supported production timing pair and separate validation triplet. Keep batching=1/cache=1 in the production pair. The check family explicitly uses its supported batching/PVS composition; do not enable cache=2 in the rejected production combination.
- Complete an actual active-table route such as 105 -> 101 -> 105 -> 101 with observed retirement and reentry. The earlier control-only pilot did not observe the full route; it is incomplete coverage, not a proved lifecycle failure.
- Resolve the absent r103 PS2HDR comparison row without interpreting it as zero mismatches. Reuse retained journals where possible.

Only if separate setup timings show material residual cost, propose an upstream shared change. Define transforms, lighting, source arrays, texture/material animation, transparent order and invalidation before implementation. Build 33 barrier counts include boundary calls with no reusable run; they are not all missed batching opportunities.

**Acceptance:** effective state and vertex order preserved, actual target classes recorded, foreign/abort/frame/list/scene barriers honored, moving doors/material changes/inventory/reentry/movie boundaries covered, STRICT/look/memory pass and demanding-view console improvement demonstrated. Capped 29.9 FPS arms alone show no gain. [Build 33][A6] [Build 34][A7]

### S6. Integrate, measure and decide

Assemble one compatible candidate only after its component contracts are understood. Recheck interactions that invalidate an earlier receipt, especially actor formats, world producer witnesses, cached headers, ordered transparency and memory lifetimes.

Use normal release / existing audit / gaps / window32 to price observation separately. Compare optimizations with identical observation settings, then verify the intended deployment composition. Do not attribute observer overhead to an optimization or subtract an unmeasured estimate.

Start with one matched bounded control/candidate pair per discriminating case for triage. A promotion claim needs applicable retained repeat-variation evidence or the minimum confirming matched repeats, preferably alternating arm order. Add further runs only when state mismatch, variance or a specific failure prevents a decision. If per-frame samples exist, report median and tail with sample count and spread; otherwise name the actual aggregate. A gain must exceed observed repeat variation and remain useful after memory/observer/composition costs.

The coordinator records each mechanism as **enable**, **retain as candidate**, or **park**, with scope, measured benefit, memory cost and the exact missing gate. Existing owner acceptance is required before recipe changes. No extrapolation from a few visited rooms to whole-game acceptance.

## 6. Validation matrix

Use the broad census to find outliers, then apply focused tests to each changed mechanism. Short emulator checks remain at most one minute per scene under the established project procedure. Continue through a real route for state/lifetime acceptance; a fresh warp does not prove continued-play STRICT. [Contributor gates][A1] [D367 tools][A14]

| Workload class | Seed cases | Main questions |
|---|---|---|
| Interior visibility | r103 barn exit/stalls; other source-verified interiors | Openings, safe camera region, LOD, witness order, survivor cost |
| Outdoor world | r101 cross; quiet farm and forest; later supplied outdoor rooms | Setup/emit cost, low visibility rejection, cache traffic |
| Actor load | Barn Ganado, village crowd, Leon/Ashley, r119 giant where supported | Formats, skin/clip/light cost, appearances, legacy refusals |
| Ordered materials | Actual cutout/blended props, overlapping effects and moving doors | Effective headers, encounter order, foreign producers |
| Near boundaries | Camera crossing doors/windows and near geometry | Clipping, conservative fallback, UV interpolation |
| Effects/gameplay | Supported churn-heavy and large-list states | Actual shared CPU contributors; no simulation omissions |
| Lifetime | Inventory return, actual room leave/reentry, death/retry | Generation invalidation, retention, peak overlap |
| Movie/audio resources | Existing s30/radio and qualified route cases | Lending/restore and required memory coexistence |
| Coverage extensions | Every additional source-verified supplied room/preset | Explicit visited/unvisited/unsupported status; new outliers |

For every result retain source/image identities, room and state, camera, enemies/appearance, actual definitions, selected quality, draw/logic/skip denominators, timing scope, observer footprint, memory result, visual/STRICT result and raw private receipt references.

## 7. Ledgers and acceptance rules

The filenames in this section are **proposed local work products**, not existing commands or completed reports.

### Private evidence set

- `scope-manifest.json`: expected rooms/states and their source authorities; supplied/absent content; image and complete input manifest.
- `coverage.tsv`: one row per room/preset/state with scan, launch, visit, binding and acceptance status.
- `experiments.tsv`: question, changed input, expected discriminating observation, bounded run count/duration, control/candidate identities, verdict and next action.
- `feature-decisions.tsv`: mechanism, eligible coverage, measured cost delta, static/runtime/peak memory, correctness/quality, status and remaining gate.
- `RESULTS.md`: concise findings and unresolved decisions, linked to immutable receipts.

Keep the source/recipe/assets/SDK/emulator/fixture/programme/overlay/track hashes in the ledger. Retain full private reports locally. The public handback contains sanitized counts and hashes, source paths, commands with placeholders and conclusions.

### Counter semantics

- N32 means the last 32 completed draw-attempt ticks. It does not mean GPU presentations.
- A 600-draw qualification interval does not turn an N32 sample into 600-draw totals.
- FA29T contains room totals, including skipped/asynchronous activity. Old MARK/pause/resume does not reset those totals.
- Use monotonic same-room deltas only when reset, overflow and discontinuity checks pass. Follow the new window's separate pause/reset contract.
- Reason units overlap. Parts, vertices, matrices, strips, probes and calls cannot be summed as one workload.
- Zero is meaningful only with proven execution and valid capture. Missing rows, missing parts and unvisited states are not zero.
- Distinguish static eligibility, host correctness, emulator function, MODELLED cost and measured console time. [Build 35][A8] [Build 28][A10]

### Completion criteria

The milestone is ready for a coordinator decision when:

1. The supplied scope is reconciled with an authoritative manifest; unavailable/unvisited content is explicit.
2. The highest-cost observed shared causes have an enable/hold/park decision with supporting evidence.
3. A compatible candidate has matched hardware timing and no unresolved required gameplay, appearance, memory or lifetime failures in its declared scope.
4. All new default-off controls retain their required identity evidence.
5. Content generation is reproducible with source-bound metadata, conservative refusals and bounded runtime cost.
6. Remaining exceptions have named owners and exact next commands or inputs.

This does not require pretending every retail room is available, every counter is exercised or 30 fps has been achieved. Report remaining frame-budget deficits and their measured contributors.

## 8. Verified existing commands

These commands were checked against the reviewed source. Private variables must name the actual local inputs. New manifests, runners and trace contracts described above must be implemented or authored first; their names are not existing tool flags.

### 8.1 Scan the explicit supplied scope

Prepare `SYSTEMIC_ROOMS_FILE` with one verified room ID per line, comments allowed. Derive it from the authoritative manifest; keep expected missing rooms. Set all four private variables before running. Output must be new and outside the input tree.

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

### 8.2 Preserve a complete unchanged-input manifest

Save this small helper as `$PRIVATE_TOOLS_DIR/systemic_input_manifest.py` outside Git. Use a private output path outside the input tree. It records every ordinary input file, not only scanner-recognized formats, and refuses symlinks instead of silently omitting them.

```python
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve(strict=True)
output = Path(sys.argv[2]).resolve()
if not root.is_dir() or output.is_relative_to(root) or output.exists():
    raise SystemExit("need a directory input and a new output outside it")
rows = []
for path in sorted(root.rglob("*")):
    if path.is_symlink():
        raise SystemExit(f"unsupported input symlink: {path}")
    if path.is_file():
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest,
        })
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(rows, stream, sort_keys=True, indent=2)
    stream.write("\n")
```

With Python 3.12, hash before the scan and after it:

```bash
python3 "$PRIVATE_TOOLS_DIR/systemic_input_manifest.py" \
  "$PRIVATE_DISC_TREE" "$PRIVATE_EVIDENCE/inputs-before.json"
# Run section 8.1 here.
python3 "$PRIVATE_TOOLS_DIR/systemic_input_manifest.py" \
  "$PRIVATE_DISC_TREE" "$PRIVATE_EVIDENCE/inputs-after.json"
cmp "$PRIVATE_EVIDENCE/inputs-before.json" "$PRIVATE_EVIDENCE/inputs-after.json"
sha256sum "$IMAGE_KNOBS" "$SYSTEMIC_ROOMS_FILE" \
  "$PRIVATE_EVIDENCE/inputs-before.json"
```

Keep the input tree quiescent for both hashes and the scan. The helper is a proposed handover utility, not a replacement for the scanner or an already-recorded private receipt.

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

The following is a reference manual sequence after readiness and selected preset/camera are verified. It does not implement an automatic 600-draw stopping condition. The S2 runner must derive that condition from valid runtime denominators.

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

## 9. First local checkpoint and handback

Complete these concrete outputs first:

1. Source/image/recipe/input evidence ledger and an explicit closed/open gate list.
2. One chosen changed-input memory observation experiment, with the contract it will prove.
3. A supported complete-snapshot schedule with readiness/transport timing and active-image evidence.
4. The authoritative room manifest and an initial supplied/scanned/visited coverage table.
5. Named S3-S5 owners, source-file boundaries and the next task each can execute independently.

The coordinator owns `port/dreamcast/docs/cloud/handbacks/systemic-performance-20261029.md` as the consolidated status ledger. Each implementation lane owns a separate handback, such as `systemic-observation-20261029.md`, `systemic-coverage-20261029.md`, `systemic-world-20261029.md`, `systemic-actors-20261029.md` or `systemic-state-20261029.md` in that same directory, unless assigned a numbered build handback. Update the lane's own handback with every implementation commit; the coordinator consolidates outcomes. Use this shape:

```text
2026-MM-DD progress: DONE ...; NEXT ...; BLOCKED ...
Branch / integration base / commit:
Shared cause and intended scope:
Changed input and reason:
Control and candidate identities:
Implementation and default-off identity:
Measured cost and denominator:
Memory, look, STRICT and lifecycle evidence:
Coverage and explicit exceptions:
Decision: enable / candidate / park
Exact next command or required owner input:
Private receipt identifiers and sanitized hashes:
```

When blocked on assets, console media or an owner decision, record the exact missing input and command, then continue an independent work package. Reopen a closed task only when new evidence or changed dependencies justify it.

## Sources

All source claims were checked against `66da801e7ff457f84d52c4bb379cdaae7aa07e35`. Relative links resolve within the handover commit; subsequent local execution must check newer owner answers.

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


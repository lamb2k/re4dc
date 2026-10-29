# Continuing Builds 31-36: systemic performance action plan and handover

**2026-10-29 progress 2:** DONE: revised the handover to continue the landed builds and existing local workflow, following the user's direction that this should be an evolution from the current point. NEXT: resume the specific pending owner actions in Builds 28 and 31-36, reuse retained artifacts, and extend coverage incrementally. BLOCKED: the existing private-input and console gates remain as recorded in those handbacks. This is a documentation change.

**2026-10-29 progress 1:** Published the initial detailed plan and evidence inventory as `b431e453`. This revision replaces its separate work-package and reporting structure with direct follow-ups to the existing builds.

**Reviewed integration:** `origin/t15/int` at `66da801e7ff457f84d52c4bb379cdaae7aa07e35`.
**Handover branch:** `codex/systemic-performance-handover-20261029`.
**Audience:** the local coordinator and its assigned implementation agents.
**User direction:** solve recurring causes systemically through an evolution of the work already landed. Continue from the current renderer, converters, tools, evidence and local-agent workflow.

## 1. Continue from the current implementation

Continue the landed Builds 31-36 using the existing renderer, converters, private images, QA tools and owner handbacks. The work below closes their remaining qualification gaps and extends coverage where current evidence identifies a need. The current architecture and accepted results are the starting point.

The next deliverable is progress on those open items: a measured part plan, an actual portal proof, qualified actor formats, completed state-cache lifetimes, dependable captures and better source-bound coverage. Carry each accepted improvement into the local owner's existing integration process.

Use this order for every follow-up:

1. Identify the specific open item in the latest owner answer.
2. Reuse its existing implementation, image, fixture, command and receipt while their bound inputs remain valid.
3. Make the smallest extension or correction that closes the demonstrated gap.
4. Run the affected checks and record the result in the existing handback.
5. Broaden the proven mechanism to the next eligible asset or workload class.

The repository's real NTSC hardware goal remains 30 fps, with the existing planning budget of gameplay <=24 ms, rendering <=6 ms and about 3.33 ms margin. These are targets, not current measurements or a promise that every supplied room meets them. Preserve the playable menu/New Game -> r100 -> r101 -> r103 route while extending the existing coverage. [Repository instructions][A0] [Contributor gates][A1]

Preserve required simulation, activation, collision, events, AI, camera state and animation. Retain the ordinary renderer for unsupported, stale or unaffordable inputs. Reuse current conversion, loading, storage, generation and retirement contracts. Moving immutable work earlier is useful only where those existing contracts justify it.

A new cache, asset contract, trace or tool is conditional work: first name the measured problem and explain why the existing mechanism cannot handle it. Prefer extending the current mechanism and its supported control. New SH-4 assembly or linker work still requires evidence that removing repeated work, data layout, batching and offline conversion cannot address the problem. [Repository instructions][A0] [Cloud queue][A2]

### Existing ownership and Git rules

- The local coordinator continues to own private assets, image composition, source-state comparison, emulator scheduling, console qualification and integration.
- Continue the existing assigned build/lane ownership. Isolate source changes and avoid overlapping shared-file edits; this handover does not require creating another set of lanes.
- Base new source work on the newest `origin/t15/int`. Preserve the current task's restrictions on `dreamcast-port` and `bruce`.
- Keep new controls default 0 and preserve the required absent/zero identity. Push small buildable commits, each with a dated done/next/blocked update in its assigned existing handback.
- Rebase before pushing, stage owned files, and retain owner answers and unrelated edits. The coordinator performs merges.
- Continue using Build 28 and Builds 31-36 for their follow-ups. The coordinator assigns any genuinely new work or build number through the existing queue; agents do not overwrite `CLOUD_AGENT_QUEUE.md` to claim ownership.
- Keep game data, generated copyrighted assets, disc images, private captures and detailed asset inventories outside Git. Publish code, synthetic fixtures and sanitized evidence summaries.
- Follow the established owner process for recipe promotion, physical media and releases. Honor current builder limits and the exclusive emulator/console window. Independent host and read-only work can continue in parallel. [Repository instructions][A0] [Cloud queue][A2] [Original handover][A3]

## 2. Resume the existing handbacks

Read the current versions in this order:

1. [HANDOVER-CLOUD-20261028.md](HANDOVER-CLOUD-20261028.md).
2. [CLOUD_AGENT_QUEUE.md](CLOUD_AGENT_QUEUE.md), including its Status rows.
3. The latest **Answers (owner)** in the build being continued, with this document as a cross-build guide.
4. The current local `AGENTS.md`, `CLAUDE.md` and `re4-dreamcast-d367` skill, if installed, for actual paths, lane ownership and harness commands.

Check what has changed since the retained receipts. Preserve the existing local worktree, active processes and private results. Reuse the current source/image pair where valid; record only the changed dependencies or missing evidence. Intake is a brief continuation check, not a new baseline-building milestone.

### Fetch and read this update

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
git show origin/codex/systemic-performance-handover-20261029:port/dreamcast/docs/cloud/HANDOVER-SYSTEMIC-PERFORMANCE-20261029.md
```

Confirm `origin` is the expected `lamb2k/re4dc` repository. Use the local owner's existing branch/worktree procedure for an assigned follow-up. Runtime changes remain based on integration; this documentation branch supplies instructions.

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

## 5. Continue the existing builds

The expected renderer impact order remains **Build 31 world -> Build 32 actors -> Builds 33/34 repeated state**. Finish the open observation work and extend coverage alongside those follow-ups. They support the current improvements; they do not form a new prerequisite project.

| Existing work | Next concrete continuation | Extend only when evidence requires it |
|---|---|---|
| Build 31 | Measure the existing part plan and produce the pending real portal proof using the current builder | Extend a specific producer/witness contract if useful hidden work justifies the compatibility change |
| Build 32 | Complete the existing format comparisons, mode-2 checks and named live-model qualification | Extend the real converter for costly legacy refusals; consider cached validation only if its cost warrants it |
| Builds 33/34 | Finish effective-state checks, missing target classes, SCPS retirement/reentry and demanding-view timing | Extend upstream setup/batching only for measured residual cost |
| Builds 28/34/35 | Close the retained memory-observation and incomplete-DIAG questions using the existing tools | Add the smallest missing observation or publication fix needed to answer those questions |
| Builds 36/28 | Add verified selection context to retained reports and extend the existing room list/tour | Add an optional field or targeted trace only where current loader/F29 evidence cannot resolve a named binding |
| Local integration | Carry accepted follow-ups into the existing combined candidate and decision process | Recheck only the interactions and gates affected by the changed composition |

Start each follow-up from its latest owner answer. Keep source/image/recipe/asset identities in the existing receipt and report format. A console or capture hold blocks the acceptance that depends on it; other source, converter and fixture work continues. Whole-game coverage grows incrementally and does not block a provable shared fix.

### Builds 28, 34 and 35: finish the existing capture and memory follow-ups

**Memory question:** can the unchanged stock judge receive all required evidence from a source-bound, correctly published and correctly observed stream?

Two retained 60-second memory runs explicitly failed the stock judge. Held-allocation readback was empty; one run also had malformed numeric rows. Reader exit 0, zero overruns and zero OOM strings do not override the FAIL verdict. The 64 KiB observer rings were the expected size. [Build 34][A7]

The source/ELF review establishes two risks, not a sole root cause:

- `re4dc_log_raw` can publish a head after overlapping writers have overwritten a byte; an interleaving counterexample leaves a NUL hole without a reader overrun.
- `read_log.py` reads Flycast's raw host RAM backing. Copy-back CPU cache contents need not already be visible there. Exact binary/cache-state provenance was incomplete.

**Action sequence**

1. Complete the missing provenance fields in the retained source/ELF/reader audit, especially actual writer contexts, emulator binary and active cache state. Reuse the already-bound source, machine-code and ring-size findings.
2. Use the retained counterexample to identify the smallest publication or reader-visibility correction needed: writer serialization, complete records, payload visibility before published head and wrap behavior.
3. Select one changed-input repair experiment that discriminates the identified cause. Keep the stock judge and the fixed observer budget. Use a separate default-off control for a new runtime change.
4. Prove deliberate writer interleavings, wrap, partial publication and the actual cache visibility mechanism with targeted fixtures. Keep formatting and large copies outside long IRQ-disabled regions; report interruption cost.
5. Run a bounded matched memory pair, retaining active track01/fixture identity before teardown. Require complete authentic judge inputs and an explicit valid PASS or FAIL from the unchanged judge. A valid memory FAIL can close the observation-contract question while blocking that candidate's memory acceptance.
6. If capture is incomplete or malformed, record the unresolved observation contract and the next discriminating change. If a valid capture fails memory acceptance, investigate the actual allocation/headroom failure separately. Do not repair malformed numbers, enlarge/shrink logs to make the result pass, waive fields or repeat an identical capture.

Current structured QA rows expose current free/used/brk. They do not supply the held amount, watch minimum, keepcost/top-block information, required aggregate OOM/MISSING/HALT accounting or exact scene-end event. B/L forwarding uses the same RAM ring. A structured replacement is a separate design and must first prove semantic equivalence for every required judge input. [Build 34][A7]

**Snapshot question:** can one explicit diagnostic request deliver every part of one immutable snapshot in the supported run envelope?

1. Reuse the qualified stock PPP runner and reviewed CRLF companion. Keep the current observer size.
2. Start with the retained peer/PONG/request/part timings. Add missing queue or snapshot timing only if those existing observations cannot explain the incomplete response.
3. Adjust the existing command schedule to request at the earliest verified ready point. The retained pilot reached PPP late in a 60-second run; use that finding to define one changed-input follow-up.
4. Require all advertised consistent parts from one immutable snapshot, correct session/build identity and successful complete-response status. The retained window32 profile advertises 14 parts. Automatic T completeness does not close its explicit D 4/14.
5. If the supported schedule cannot fit, return the measured transport budget and exact conflicting constraint. Preserve INCOMPLETE; do not silently extend the run or accept partial output.

**Record in the existing handbacks:** whether the observation question is closed, the stock judge's valid result, explicit snapshot completeness and the remaining existing observer-cost/stack/headroom gates. Close each item independently as its evidence arrives. Source and asset work continues while a hardware-specific item is held. [Build 34][A7] [Build 35][A8] [Build 28][A10]

### Builds 36 and 28: extend the existing scan and tour

**Start from retained results.** Build 36 already has `coverage.tsv`, `report.json`, membership details, a context template and the owner's complete input manifest. Build 28 already has a 33-preset tour and session evidence. Continue those artifacts and their formats.

**Resolve the named gaps needed by the current follow-ups.** The report retains 612 unassigned models, five route gaps (r110, r114, r115, r116, r120), four missing exact ESL archive candidates and 13 unresolved `emleon09` records. The active stage selector 9 names `omake01`; the filename suffix cannot establish a binding. Conditional membership does not establish a live actor.

The texture report has 7,375 conditional keys, not zero textures. Add actual room quality and selection context for the targets being measured. Whole-pack replacement differs from duplicate entries within one physical pack. Legacy geometry-only inventory does not establish material, placement or selected-LOD facts. [Build 36][A9]

Use existing discovery, F29 identity rows, loader evidence and the owner's exact source/model/hash context first. Resolve the costly targets in the Build 31-34 runs before attempting to assign every global model to a room. If those tools cannot resolve a specific needed binding, add the smallest optional field or bounded selection event to the existing path. A new general tracing system is not a deliverable of this handover.

**Broaden scope using the current room list and reports.** Reconcile the requested rooms with the final image, source loader tables and existing staging manifest. Retain expected but missing rooms as coverage gaps. Extend the same list and report when additional supplied rooms are ready. The scanner has no `--all-rooms` flag; omitting `--rooms` selects r100-r11f. Section 8.1 shows the existing explicit-list invocation. [Scanner README][A12]

Keep the goal of coverage across supplied game content visible. Add supplied/scanned/supported-launch/visited/matched status to the existing report or a short adjacent summary where those fields are missing. A folder listing alone does not establish full-game completeness.

**Extend the existing tour by workload class.** Use the retained 33-preset tour as the seed. Bind each new or rerun case to its actual image, source, selected actors/materials and runtime denominators. Preserve qualified cases whose inputs still match. Add source-verified states that cover a new renderer boundary or reveal an outlier. Mark unavailable later-game content explicitly.

Use the phase timings and reason counters already available. Rank shared causes by measured exclusive cost and relevant workload frequency, keeping MODELLED estimates separate. Refresh a private scan or capture only for changed code, inputs, verified context or room scope.

**Useful next result:** the named assets and rooms needed by the current build follow-ups are bound, the next missing coverage is explicit, and existing reports explain which shared path merits the next improvement. [Build 36][A9] [Build 28][A10]

### Build 31: qualify the part plan and existing portal workflow

**First reuse and measure the part plan.** It already builds ordered immutable spans once per room. Preserve live material/UV state, camera/placement transforms, texture resolution and submission. Preserve the existing 64 KiB plan cap plus alignment and checked 96 KiB heap floor unless a separately measured budget change is justified.

Compare high-eligibility and low-eligibility scenes. Record plan loads/refusals/bytes, setup cost, total CPU time, room generation, inventory/movie lending and retirement. A high planned-part count is activity, not a gain. [Build 31][A4]

**Complete the pending portal proof, then extend the proven workflow.**

1. Produce one real package-bound r103 hull/eye configuration and proof with the existing builder.
2. If that proof establishes useful eligible geometry, reuse the same builder/configuration workflow for the next building class. Automate repetitive candidate discovery or reporting only where repeated use demonstrates a need; retain explicit authority for safe eye cells and opaque static coverage.
3. Preserve cracks, all openings, LOD coverage, margins, dynamic/breakable/cutout exclusions and current-view completed-wall witnesses.
4. Record every package as eligible, refused with reason, unsupported or not yet assessed. Missing/stale/malformed/complex/heap-short data uses ordinary drawing.

**Extend producer composition only when the proof and measured workload justify it.** The currently qualified portal profile disables stream/submit batching and the clip gather/indexed paths, along with incompatible source-removing combinations. Once a real candidate shows useful exclusions, trace the exact producer path that cannot furnish a valid completed-wall witness. Extend that existing path where its proof can be preserved. Removing Make guards is not a fix.

Use four clearly named comparisons:

- Current normal release or current accepted production profile.
- Supported portal-profile control with portal off.
- The same supported profile with portal on.
- Any newly compatible profile, compared to its own control and to current production.

A gain against the slower special control must pay back any lost production optimizations before promotion.

**Acceptance:** synthetic/actual-source proofs for the changed contract; real magenta walks through doors, windows, seams and near/FOV boundaries; correct dynamic state, all relevant LODs, room reentry and movie lending; missing/stale/heap fallback; look and STRICT; bounded memory; net hardware cost including witnesses and survivor setup.

Visibility tables, more clip reuse and room-far approximations remain conditional follow-ups. Open one only if measured residual phase cost supports it. Keep deliberate distance/appearance reductions separately identified. [Build 31][A4] [Barn source audit][A11] [Portal contract][A13]

### Build 32: qualify existing actor formats and address demonstrated converter gaps

Continue the existing control, cone, UV16, combined and verification profiles from the Build 32 handback. Reuse their qualified images and fixtures where valid. Use actor-heavy matched scenes covering Leon, Ashley, Ganados and El Gigante, with actual appearance, motion, lighting, texture state and camera bound.

1. Join live refusals to exact selected model/source identities.
2. If legacy FE3 assets dominate measured cost, recover the real packer, representation, signedness and source lineage. Extend that converter to emit valid metadata. Do not relabel old blobs as certified.
3. Preserve the repaired UV interval/interpolation and actual bound-texture precision checks, cone quantization/numeric/near checks and ordinary fallback.
4. Complete the existing admission/appearance/timing checks before changing the ownership model. Consider moving source validation earlier only if measured validation cost remains material.
5. If that evidence justifies cached admission, it needs real allocation extent, owner generation, mutability policy and invalidation on replacement/reload. The current actor API does not provide UV allocation length; pointer equality and RAM containment do not establish immutable ownership. Keep texture-dependent and other live checks at the necessary runtime point.

**Acceptance:** actual admissions on intended targets; exercised mode-2 verification with bad=0; unsupported/mutable/near/cull refusals; seams, clipping, masks/fades, animation, LOD and texture dimension/scale changes; unload/reload; fast-only lighting fallback/exact counters remain zero where required; STRICT/look/memory; net console cost including scans, packing and split growth.

UV16 retains 32-byte CPU SQ slots. Relevant PVR internal fields shrink from 24 to 20 bytes, while CPU validation/packing is added. Do not claim halved CPU output bandwidth. The historical global CPU-backface regression is distinct from guarded actor cones. [Build 32][A5]

### Builds 33 and 34: finish state reuse and lifecycle qualification

Qualify existing mechanisms before adding a larger batch architecture.

- **Build 33:** find actual source-bound single-part, above-16-part and blended targets. Existing mapping establishes useful single-part targets but no confirmed large/blended target. Compare every vertex with its effective final header in original order, at aligned source tick/pose/view. A raw stream hash legitimately changes when redundant headers disappear.
- **Front texture cache:** retain exact descriptor/dimension/wrap checks and invalidation. Measure hits/builds/refusals, current memory and CPU cost. High hit counts do not establish net benefit.
- **SCPS:** use the existing supported production timing pair and separate validation triplet. Keep batching=1/cache=1 in the production pair. The check family explicitly uses its supported batching/PVS composition; do not enable cache=2 in the rejected production combination.
- Complete an actual active-table route such as 105 -> 101 -> 105 -> 101 with observed retirement and reentry. The earlier control-only pilot did not observe the full route; it is incomplete coverage, not a proved lifecycle failure.
- Resolve the absent r103 PS2HDR comparison row without interpreting it as zero mismatches. Reuse retained journals where possible.

Only if separate setup timings show material residual cost, propose an upstream shared change. Define transforms, lighting, source arrays, texture/material animation, transparent order and invalidation before implementation. Build 33 barrier counts include boundary calls with no reusable run; they are not all missed batching opportunities.

**Acceptance:** effective state and vertex order preserved, actual target classes recorded, foreign/abort/frame/list/scene barriers honored, moving doors/material changes/inventory/reentry/movie boundaries covered, STRICT/look/memory pass and demanding-view console improvement demonstrated. Capped 29.9 FPS arms alone show no gain. [Build 33][A6] [Build 34][A7]

### Local owner: continue combined qualification and integration

Continue the owner's existing combined candidate and qualification process. Incorporate accepted follow-ups incrementally. Recheck interactions that invalidate an earlier receipt, especially actor formats, world producer witnesses, cached headers, ordered transparency and memory lifetimes.

Use normal release / existing audit / gaps / window32 to price observation separately. Compare optimizations with identical observation settings, then verify the intended deployment composition. Do not attribute observer overhead to an optimization or subtract an unmeasured estimate.

Start with one matched bounded control/candidate pair per discriminating case for triage. A promotion claim needs applicable retained repeat-variation evidence or the minimum confirming matched repeats, preferably alternating arm order. Add further runs only when state mismatch, variance or a specific failure prevents a decision. If per-frame samples exist, report median and tail with sample count and spread; otherwise name the actual aggregate. A gain must exceed observed repeat variation and remain useful after memory/observer/composition costs.

The coordinator records each mechanism as **enable**, **retain as candidate**, or **park**, with scope, measured benefit, memory cost and the exact missing gate. Existing owner acceptance is required before recipe changes. No extrapolation from a few visited rooms to whole-game acceptance.

## 6. Validation matrix

Use the existing fixtures and tour results, extending them to expose outliers or exercise a changed boundary. Apply the relevant rows below to each follow-up; unchanged cases keep their valid receipts. Short emulator checks remain at most one minute per scene under the established project procedure. Continue through a real route for state/lifetime acceptance; a fresh warp does not prove continued-play STRICT. [Contributor gates][A1] [D367 tools][A14]

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

## 7. Extend current records and preserve acceptance rules

Use the existing private receipts, result files, input manifests, hold decisions and Build 28/31-36 handbacks. Link to retained records rather than copying them into a new reporting structure. Add only the missing context needed for the next decision.

| Existing artifact | Useful addition when missing |
|---|---|
| Build 36 `coverage.tsv`, `report.json` and owner input manifest | Verified additional rooms/context; supplied/scanned/visited distinction; exact missing source |
| Build 28 tour/session results | Newly exercised state, actual current image, coherent draw denominator and unavailable presets |
| Build 31-35 experiment receipts | Specific question, changed input, discriminating observation, bounded run and verdict |
| Existing owner acceptance/hold records | Measured cost, memory/quality limits and exact remaining gate |
| Existing build handback | Dated result, receipt references, next action and blocker |

Keep the source/recipe/assets/SDK/emulator/fixture/programme/overlay/track identities required by the existing gate. Reuse an identity record where it still applies. Full game reports remain private; publish sanitized counts, hashes, source paths, commands and conclusions.

### Counter semantics

- N32 means the last 32 completed draw-attempt ticks. It does not mean GPU presentations.
- A 600-draw qualification interval does not turn an N32 sample into 600-draw totals.
- FA29T contains room totals, including skipped/asynchronous activity. Old MARK/pause/resume does not reset those totals.
- Use monotonic same-room deltas only when reset, overflow and discontinuity checks pass. Follow the new window's separate pause/reset contract.
- Reason units overlap. Parts, vertices, matrices, strips, probes and calls cannot be summed as one workload.
- Zero is meaningful only with proven execution and valid capture. Missing rows, missing parts and unvisited states are not zero.
- Distinguish static eligibility, host correctness, emulator function, MODELLED cost and measured console time. [Build 35][A8] [Build 28][A10]

### When a follow-up is ready for the owner's decision

Use the build's existing acceptance gates and declared scope:

1. The specific open item has a source-bound result; affected identity, correctness, look, memory and lifecycle gates are satisfied or explicitly held.
2. A performance claim has matched console evidence with its denominator, observer cost and repeat variation.
3. Relevant coverage and exceptions are stated. Broader unvisited content remains visible without becoming an unrelated prerequisite.
4. The owner can enable, retain as candidate or park the change using the current decision process.
5. The existing handback gives the exact next command or missing input for anything unfinished.

Continue carrying accepted improvements forward. Report remaining frame-budget deficits and their measured contributors without implying whole-game or 30 fps acceptance.

## 8. Verified existing commands

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

## 9. Immediate continuation and handback

The first update should report progress in the current build handbacks:

1. **Builds 28/34/35:** use the retained pilot to complete the explicit diagnostic response, and choose one concrete changed-input follow-up for the memory observation failure. Keep valid memory FAIL separate from capture failure.
2. **Build 36:** add the actual owner/appearance/quality context needed for named targets in the pending renderer runs. Keep other unresolved inventory visible. Extend the current room list and tour as additional supplied workloads become ready.
3. **Build 31:** measure the already-landed part plan and run the pending actual-package portal builder/proof. Use the result to decide the scope and value of a producer-compatibility extension.
4. **Build 32:** continue existing format/mode-2/look/timing qualification; identify exact costly legacy sources before changing a converter or runtime ownership contract.
5. **Builds 33/34:** finish the missing effective-state targets, SCPS retirement/reentry and r103 comparison evidence using the supported profiles.
6. **Local coordinator:** carry accepted results into the current combined candidate and acceptance/hold records.

Maintain one assigned writer per existing handback. Helpers return findings to that owner; they do not all edit the same file concurrently. Use a separate follow-up file only if the coordinator's existing lane practice requires it. Every implementation commit still includes the dated progress update required by the queue.

In the existing format, record the shared cause, actual changed input, reused receipt identities, affected validation, measured cost/denominator, explicit exceptions and next command. The coordinator may keep a concise cross-build summary linking those handbacks; a new systemic ledger is optional.

**Operating instruction:** continue from the latest owner answers. Close the next concrete gap using the existing mechanism; extend a tool or contract only when current evidence shows what it cannot yet do. Record the result in the existing handback and carry accepted work forward.

When a private input or console result is unavailable, record that exact blocker and continue another already-assigned follow-up. Reopen completed work only when a changed dependency or new finding warrants it.

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

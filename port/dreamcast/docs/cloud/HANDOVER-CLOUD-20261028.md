Current owner update, 2026-10-29 (RE4-PLAN-SYNC-20261029-1202): frozen local EF04/09/11/16 deliveries are now integrated at `c027b26e32229dc9035b9fe2e1ac399bd9ee20b0`. Their local source-file reservations are released to the cloud task matrix; all further source-only/synthetic implementation belongs to cloud, with one writer per shared file and existing producer dependencies retained. Local now owns private-data/runtime/console qualification and serialized integration only. First slices are not full EF acceptance. Compatible ALLON K27 is prepared with QA_LINK=1; LOG_ATOMIC16 and portal controls remain parked. Exact file grants and evidence: [owner handoff](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-frozen-local-source-release). This update supersedes older pending-local-delivery status, not the unfinished scope or holds.

CURRENT 2026-10-29 cloud-thread recovery (RE4-PLAN-SYNC-20261029-1202): user requests a fresh thread to continue interrupted source implementation. Read [recovery handover](HANDOVER-CLOUD-RECOVERY-20261029.md) first, then existing task/file matrix and ranked backlog. RuntimeD13/K35 prepared, owner14b5 checkpoint, two unchanged frontend/worldstream blockers. Check surviving workers/unpushed work before assigning exclusive writers; do not infer live activity from assignment or Working badge. All public-source/synthetic continuation remains cloud-owned; local private/runtime/console/integration holds remain. Recover, report actual worker/current task/next deliverable/wait matrix, then implement. Emails remain stopped; local cloud watch5m.


# Cloud agent handover, 2026-10-28 (evening)

## Current execution agreement

**SYNC: RE4-PLAN-SYNC-20261029-1202.** Scope is the current-source review7c4c9200 plus all unfinished EF01-EF16 cards. The [queue](CLOUD_AGENT_QUEUE.md) and [full owner task/file matrix](handbacks/systemic-performance-20261029.md#answers-owner-2026-10-29-all-source-work-cloud-assignment) define current ownership and writer handoffs. This agreement supersedes historical first-wave assignments and one-build-at-a-time cloud ordering; preserve their evidence.

Cloud owns ALL public-source/synthetic implementation, with independent workers for EFM identity, collision dirtiness, line traversal, water and frontend now. Actor/world/binding/static/effects/cloth/batches/logger successors are also cloud-assigned, waiting only for their exact current local writer/dependency release. Local finishes frozen EF04/09/11/16 qualification/delivery, then owns private assets/loaded-package binding, actual Flycast/look/gameplay/STRICT/memory/current-cost/console checks and serialized integration/release-recipe builds. No private-input wait blocks unrelated source work. All new simulation continuations are tracked under existing Build29, not renderer EF12 or new Build37+.

Current runtime integration remains064bfa4ea (first EF01/02/03/05/06/07/08 slices); their required remaining scope is open. EF04 is frozen/target-running; EF09 frozen/target-validated/unmerged; EF11 corrected frozen/target-validated/unmerged; EF16 partial selector target-validated/unmerged. Exact delivery commits and live jobs stay in local OWNER-STATUS/ACTIVE and existing build handbacks. None is full enabled or hardware acceptance. Shared files transfer only after an integration SHA and explicit queue release; earlier local statements that a worker finished are not an early cloud write grant.

Preserve default0/absent-zero identity, source pose/material/order/gameplay, fixed budgets, valid existing evidence and frozen release/look/console/media holds. The local owner merges no-ff only after source/target/release/missing/OFF gates and fresh origin-base verification; conflicting source/build failure stays blocked. Compatible ALLON uses QA_LINK=1 after runtime changes, with incompatible or unqualified controls individually parked. Never merge dreamcast-port into t15/int or push bruce. Cloud watch remains every5m; emails remain stopped. A prepared image, parked control or passing synthetic fixture is not accepted real-content or hardware work.


The user: "lets give the cloud agent all the work ranked by impact with incremental commits and updates." This file is your work order. `CLOUD_AGENT_QUEUE.md` keeps the full build descriptions and the Status table. Work the list below top to bottom. You are code-only: no game data, no console, no Flycast. Prove everything on synthetic fixtures and give Claude the exact commands to run on the private data and the console.

## Where things stand (console facts, 10-28)

- **Barn, next to the hay-forking Ganado:** 5.0 fps on the old lighting, 9.5 with `ACTOR_LIGHT_FAST_ONLY` (now in the release recipe, f5980b96), 12.1 with every landed speed switch on (the ALL ON disc).
- **Barn exit:** 10.8 fps looking out through the doorway vs 21.1 facing the stalls. About 12 ms per frame is CPU world drawing; the graphics chip is idle (13%).
- **Quiet farm:** 29.9 fps (the cap).
- **Scanner run on the private data** (Build 29 tool, route r100-r120 + r200; report summary below): the biggest static triggers are `a_cone_absent` and `a_uv32`, 19.5k parts and 1.375 M vertices each, i.e. every character part. Both are removed by switches that are OFF in the recipe (`ACTOR_BACKFACE_CONE=0`, `NATIVE_ACTOR_UV16=0`). Next: `m_obj_split` with 441k vertices (parts `STATIC_OBJ_BATCH=2` refuses: single part, more than 16 parts, blend), then `a_chunk_unique` with 35k (`CHAR_CHUNK=0`). The scanner rejected `dc/tex.pak` ("duplicate texture key with different payload"): our packs are layered, and the last set wins on purpose.
- **20 local fast-path switches at 0 in the recipe** with no recorded reason (from your sweep). The list is in `docs/cloud/LOCAL-OFFKNOBS-20261028.txt`; `SCENERY_N256` is already parked by the user's decision.

## Ranked work (highest expected impact first)

| Rank | Build | Work | Why this rank |
|---|---|---|---|
| 1 | **31** | Doorway / portal culling from PS2 data (`WORLD_PORTAL29`, tool `--barn-portals29`), generalised to any room with buildings; plus `WORLD_PART_PLAN29`. Already described in the queue. | Measured 12 ms per frame at the barn exit; the same pattern repeats in every village house and castle room. |
| 2 | **32** | **The two biggest scanner triggers.** Find out from the code and git history why `ACTOR_BACKFACE_CONE` and `NATIVE_ACTOR_UV16` are off. Fix what blocks them (e.g. data the cone needs, the UV16 range/precision limits; an offline converter step is fine). Make both safe to turn on together with `ACTOR_LIGHT_FAST_ONLY=1`. Add counters showing parts admitted vs declined. | Every character part hits both; the barn and village crowds are character-heavy. |
| 3 | **33** | **Object batching refusals** (`m_obj_split`, 441k vertices). Extend `STATIC_OBJ_BATCH` to the refused cases (single-part objects merged across placements, more than 16 parts, blended parts in a separate ordered batch), under a new default-off switch. Keep the translucent order. | Second largest static trigger, props everywhere. |
| 4 | **34** | **Review the other 17 local off switches** (`LOCAL-OFFKNOBS-20261028.txt`). For each: what it does, when and why it went off (git log / docs), the risk, and a recommendation (enable, enable after a fix, or park with a reason). Fix the cheap blockers under the same switch. Output a table Claude can turn into recipe lines or `offknob-hold.txt` entries. | Turns 17 unknowns into decisions; some may be free speed. |
| 5 | **35** | **Close the counter gaps** your sweep names (cloth simulation, front texture object cache, espgen/EspDelete scans, collision body-list overflow, motion index, SKIN_CENSUS-only paths). Also add a windowed DFA/FA29 mode that sums each reason over the last N drawn ticks. | Lets one console tour measure all 72 groups. Claude is building that tour disc now. |
| 6 | **36** | **Scanner fixes:** read layered `tex.pak` with last-set-wins (as the game does), take room membership from the room lists so global models stop showing as `unassigned`, and accept the old world meshes without an R4PW sidecar or report them separately. | Makes the next scan complete. |
| 7 | standby | Barn proposals 2 (visibility table), 4 (clip reuse) and 5 (room far): only if the console meter rows Claude sends make one of them worthwhile. | Data first. |
| 8 | standby | Bake adapter working together with `ACTOR_LIGHT_FAST_ONLY` (Ganado brightness): only if lane ganlight28's runtime fix falls short. Claude will say. | Local lane first. |

## How to work (new: incremental commits and updates)

- **One branch per build** (`codex/<name>-<date>`), based on the newest `origin/t15/int`. Rebase onto it before every push.
- **Commit and push small, often.** Each commit is one mergeable step: a tool, a runtime piece, a counter, or a fix. Every pushed commit must:
  - build;
  - keep every new switch default 0;
  - keep the release image identical with the switches off.
  Claude's watch runs twice an hour and merges whatever is pushed, so a half-done build is fine as long as each commit stands on its own.
- **Update as you go.** Each commit also updates your hand-back file `docs/cloud/handbacks/build-NN.md`:
  - a dated progress line at the top: done / next / blocked;
  - any questions for Claude, under "Questions".
  Don't edit `CLOUD_AGENT_QUEUE.md`; Claude keeps the Status table.
- **Move on when blocked.** If a build needs data or a console result, write the exact commands for Claude in the hand-back, push, and start the next build. Come back when Claude's answer lands in your hand-back file under "Answers (Claude)".
- **Shared files** (`qa_menu.cpp`, `native_actor_fast.cpp`, `native_model.cpp`, `native_static.cpp`, `qalink*`): add code in its own `#if KNOB` block; never widen another switch's condition.
- **Reports:** cycles warm/cold, loads/stores, 32-byte lines touched, code/stack size, MODELLED whole-frame figure, and which outputs change if the change approximates. No new SH-4 assembly or linker work unless data layout, batching or offline conversion can't get there.
- **Never** push to `bruce`, publish, post on GitHub, or merge anything yourself. Never touch `dreamcast-port`.

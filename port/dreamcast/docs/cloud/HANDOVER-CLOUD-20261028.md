# Cloud agent handover, 2026-10-28 (evening)

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
| 4 | **34** | **Review the other 18 local off switches** (`LOCAL-OFFKNOBS-20261028.txt`). For each: what it does, when and why it went off (git log / docs), the risk, and a recommendation (enable, enable after a fix, or park with a reason). Fix the cheap blockers under the same switch. Output a table Claude can turn into recipe lines or `offknob-hold.txt` entries. | Turns 18 unknowns into decisions; some may be free speed. |
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

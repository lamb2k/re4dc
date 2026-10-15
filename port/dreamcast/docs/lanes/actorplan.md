# Lane actorplan (2026-10-15): character draw plan (fix 2) and one-pass character vertex kernel (fix 3)

Handover state, written at the coordinator's STOP on 2026-10-15. CPU and rendering optimization moves to another team.

- Branch `lane/actorplan`, worktree `/root/probe/lanes-20261015/actorplan`.
- Base `cb4e24c6` (t15/int: T15REC + LOGIC_WASTE=1 LOGIC_WASTE_MASK=0x02).
- Evidence root: `C:\Flycast-Evidence\re4-dreamcast\actorplan-20261015\`.
- Inputs:
  - `C:\Game Dev\Emulators\CPU-ANSWER-20261015.md`: fixes 2 and 3, where the A1 / A4-A6 buckets come from.
  - `C:\Game Dev\Emulators\CPU-SAVINGS-PLAN-20261015.md`: the user's plan; this lane is its steps 2 and 3.

## Status in one table

| Item | State | Knob | Notes |
|---|---|---|---|
| Fix 2 ceiling (characters) | Priced, MODELLED | - | See "Ceilings" below |
| Existing exact knobs (ACTOR_PROOF_LEAN, ACTOR_MATERIAL_RECORD, ACTOR_BIND_REUSE) | Measured: **no effect** | existing, default 0 | The image is byte-identical with them on in the t15 recipe. Cause not found yet (see "Known failures") |
| Fix 2 draw plan (ACTOR_PLAN) | **Proposed only**, no code | not created | Candidate items listed below |
| Fix 3 ceiling | Priced, MODELLED (calibration trace only) | - | |
| Fix 3 fused kernel (ACTOR_ONEPASS) | **Proposed only**, no code | not created | The coordinator put it on hold until fix 2 is gated |
| Object path (b) ceiling | Base numbers only | - | The coordinator asked for it after fix 2: not priced |

No source file changed on this branch. The only commit is the lane tools (`port/dreamcast/tools/d367/actorplan/`) and this doc. No gate has run, because no knob was built.

## Measurements (all MODELLED, SH-4 hw model; nominal hwsim plus the design-logic call-tree build `hwsim_cg`)

### A. Calibration trace (test 12.1 benchmark disc 76f40d95, r101 cross)

| | |
|---|---|
| Trace | `D:\Flycast-Evidence\re4-dreamcast\hwcal-20261015\hw-cross` |
| Settings | PACE_MODE=fast; global frames 301..1199 step 23; 40 ticks, alternating drawn and skipped |
| Call tree | `actorplan-20261015\cg-cross` |
| Units | ms per tick averaged over drawn and skipped ticks; per drawn picture = x2 |

Total 40.70 ms per tick (nominal).

| Subtree | ms/tick | per drawn picture |
|---|---|---|
| ModelRender (inclusive) | 11.59 | 23.2 |
| Owned characters: re4dc_actor_transaction_draw minus the PS2 world flush it triggers (re4dc_ps2_world_before_owned_tr, 1.43) | 5.19 | 10.4 |
| - vertex (avk kernels, Part::whole/strips, pass_*) | 2.28 | 4.6 |
| - pose palettes (owner_*_palettes, skin_groups/bones, MTX) | 0.42 | 0.8 |
| - **setup** | **2.49** | **5.0** |
| Objects: re4dc_draw_model_part (sob static batch, props, accessories) | 4.15 | 8.3 |
| - vertex | 1.90 | 3.8 |
| - **setup** | **2.25** | **4.5** |

The owned path already makes one native call per actor (COARSE_ONE_SUBMIT window, `re4dc_actor_submit_owned_runs` -> `one_chunk`). About 5 transaction calls a picture: Leon has 2 OT passes, plus ~3 Ganados. They contain ~18 chunks.

Kernel cost per loop iteration (2 vertices), all-in (`kern.py`):

| Kernel or wrapper | Cycles |
|---|---|
| avk_pos_skin_u16 | 114 per iteration |
| avk_pos_skin_s16 | 104 per iteration |
| avk_pos_rigid_s16 | 98 per iteration |
| avk_light_skin_n16 | 102 per iteration |
| avk_light_skin (s8) | 87 per iteration |
| avk_light_rigid | 90 per iteration |
| Part::whole | 34 per iteration |
| pass_lights wrapper | 524 per call (I-miss heavy) |

### B. t15 base on the current recipe (arm ap0rW)

| | |
|---|---|
| Arm | ap0rW: the t15 recipe from cb4e24c6 + PACE_MODE=off PC_SAMPLER_BYTES=8192; ELF ada02aa3; `_end` 8c427098 |
| Scene | benchmark-r101-t12 |
| Data | T15_DATA |
| Window | global frames 500:799, trace stride 10 (30 frames) |
| Evidence | `actorplan-20261015\hwmodel-ap0-cross` (proj/ and cg/; raw traces deleted, sizes.txt kept) |
| Units | every tick is drawn, so ms/frame = ms per drawn picture |

| | ms/frame (nominal) |
|---|---|
| Total | 61.85 (hwproject TOTAL 61.9) |
| ModelRender | 16.45 |
| Owned characters (4.7 transaction calls, 17.1 chunks) | 10.04 |
| - vertex | 4.58 |
| - pose | 0.70 |
| - **setup** | **4.77** |
| Objects (30.3 draw_model_part calls) | 2.30 |
| - vertex | 0.67 |
| - **setup** | **1.63** |

STATIC_OBJ_BAKE cut the object calls from 75 to 30 a picture.

Owned setup, top items in ms/frame, with calls per frame in brackets:

| Function | ms (calls) |
|---|---|
| one_chunk self | 0.713 (17.1) |
| owner_leon_bind | 0.280 (2.0) |
| memcpy | 0.231 (664) |
| transaction_draw self | 0.200 |
| memset | 0.197 (102) |
| role_bindings | 0.188 |
| probe_dirs_all | 0.181 |
| owner_ganado_bind | 0.132 |
| build_lights | 0.132 (10.4) |
| one_qualifies | 0.129 (52) |
| immutable_chunk_proof | 0.087 (51) |
| life::info_current | 0.087 (234) |
| actor_current_role | 0.086 |
| model_packet_reserve | 0.075 (43) |
| probe_lights | 0.072 |
| actor_semantics | 0.071 |
| owned_source | 0.067 |
| memcmp | 0.062 |
| owned_run_load | 0.061 |
| material::texture | 0.059 |
| preflight_owned_runs | 0.059 |

The full list is `owned.py` output.

one_chunk self is mostly per-meshlet bookkeeping, the constant-colour fill and `Part::prime`, not plan work. It belongs to fix 3. Per line: `fnlines.py hwmodel-ap0-cross one_chunk`, lines 5535-5587 and 2905.

### C. Existing knobs (arm ap1rW = ap0rW + ACTOR_PROOF_LEAN=1 ACTOR_MATERIAL_RECORD=1 ACTOR_BIND_REUSE=1)

- ELF 6701cabd. The `objcopy -O binary -R .stack` image is **byte-identical** to ap0rW.
- `coarse_actor.o` disassembly is identical too, although build.log line 924 passes all three -D flags to coarse_actor.cpp.
- The hw traces, the call tree and every number are identical. **Saving 0.00 ms MODELLED.**
- Evidence: `actorplan-20261015\hwmodel-ap1-cross`.

## Ceilings (MODELLED; corr = nominal x1.09 console-fit x1.13 render residual, per CPU-ANSWER)

| Game area | Work it cuts | In plain words | ms MODELLED | confidence |
|---|---|---|---|---|
| Fix 2: Leon + Ganados (owned path) | Per-frame re-proof: plan_leon/plan_ganado and owner_*_bind (Leon's bind runs twice a frame, each with a 119x24 finite scan), role_bindings/info_current/actor_current_role, actor_semantics + material certificate + immutable_chunk_proof, the preflight run twice (acquire, then submit), one_qualifies 52x a frame, skin/texture validate, per-chunk lights (build_lights/probe_lights), part of 664 memcpy + 102 memset | Prove once that the character is still the same character, and reuse that instead of re-proving it every frame and every chunk | Ceiling 2.4-2.8 nominal = **-2.9 to -3.4 corr**; realistic -1.5 to -2.5 | medium-low |
| Fix 2: must stay per frame | Pose palettes 0.7, fog gate, modelview concat, one TA header per material | Bones move every frame | 0 | - |
| Fix 3: all skinned characters | A fused position + light loop (one record read, one call per meshlet): ~15 cycles x ~8.7k lit vertices, plus the pass_lights/build_dirs wrappers. s8 normals for the PS2 cast: n16 51 vs s8 44 cycles a vertex, 0.14 | Shade each point in the same pass that places it | **-1.0 to -1.3 corr**, lower on t15 (GANADO_LOD=2 cuts Ganado vertices) | low-medium |
| Objects, path (b) | Per-draw fee on props and accessories | Same paperwork for objects | Setup 1.63 nominal on t15; resolvable part probably < 1 ms; not priced | - |

Why fix 3 is below CPU-ANSWER's -3..-4:
- The emit pass copies by index (Part::whole). It cannot fuse without strip-ordered duplicated vertices, which raise the transform count.
- XMTRX holds the skin matrix, so the light directions need FV registers or reloads.

The user's plan (CPU-SAVINGS-PLAN step 3) agrees: keep small scratch buffers where shared vertices or clipping make them worthwhile.

## Proposed ACTOR_PLAN items (not built; each exact; ranked by t15 ms/frame nominal)

1. **Preflight once per call** (~0.25):
   - submit_owned_runs repeats `re4dc_actor_preflight_owned_runs` right after actor_acquire preflighted all runs in the same `re4dc_actor_transaction_draw` call.
   - Skip it when the record was acquired in this call and life::serial has not moved. This is the ACTOR_PROOF_LEAN audit.
   - Hand each run's one_qualifies result (SkinEntry + source) to one_chunk. The `one_chunk_core(p, w, known, known_src)` hook exists under LEON_NATIVE_PIPE.
2. **Leon bind reuse inside the transaction** (~0.14): the Leon twin of ACTOR_BIND_REUSE. owner_leon_palettes repeats owner_leon_bind right after re4dc_actor_plan_leon.
3. **Role-row memo across frames** (~0.3 of role_bindings + info_current + actor_current_role + find_info):
   - Key: model, appearance, the info list (pointers, pData, tpl_addr) and life::serial/epoch.
   - Measure the compare cost against the saving.
4. **Certificate / immutable_chunk_proof memo across frames** (~0.2): what ACTOR_MATERIAL_RECORD was meant to do. First fix the no-op (see "Known failures").
5. **Lights once per actor** (~0.1-0.2): build_lights/probe_lights per chunk. probe_dirs_all is already about once per actor.
6. **memcpy/memset audit** (~0.2): 664 memcpy a frame on the owned path (part records, modelviews, Frame copies).
7. The user's plan step 2 wants more than a cache: prepare parts, materials and bindings at **asset load**, and update shared character state once per rendered tick.

Gate before the large build: the estimate must reach >= 2 ms. Items 1-6 total ~1.2-1.4 nominal (~1.5-1.7 corr). The asset-load preparation of step 2 is what moves it past 2 ms.

## Known failures and traps

- **ACTOR_PROOF_LEAN / ACTOR_MATERIAL_RECORD / ACTOR_BIND_REUSE compile to nothing in the t15 recipe.** The image is identical. Next check:
  - Preprocess coarse_actor.cpp with the build.log line 924 flags plus `-E`.
  - grep for `lean_serial` / `owner_ganado_bind_tx`.
  - Follow the `#if` chain around `coarse_actor_transaction.inc`. ACTOR_BIND_REUSE's code is in coarse_ganado_cast.cpp, which builds into coarse_ganado.o as well.
- Two hw runs at once are fine: per-name disc staging. But `actorplan/hw.sh` builds `bench-hw-keep.sh` by deleting `--drop-traces` with sed, and the copy then stops at `rc: unbound variable` after hwproject. The projection is complete, but `SCENE.txt`/`fixture.json` are not copied into the hwmodel dir. Fix that `set -u` line before reuse.
- The call-tree simulator `/root/probe/d367-agents/design-logic/tools/hwsim_cg` is the older hwsim without `--console-fit`. Its numbers are **nominal**. Scale with the CPU-ANSWER factors, or port the cg option into tools/hwmodel/hwsim.c.
- Calibration trace trap (CPU-ANSWER): drop frame 1033 of hwmodel-ml-skip. It was not used here.

## Exact next experiment

1. Resolve the no-op above, rebuild ap1rW, and re-price:
   - `XON="PACE_MODE=off PC_SAMPLER_BYTES=8192" bash tools/d367/actorplan/build.sh ap1 rW ACTOR_PROOF_LEAN=1 ACTOR_MATERIAL_RECORD=1 ACTOR_BIND_REUSE=1`
   - `bash tools/d367/actorplan/hw.sh r101-t12 ap1rW ap1b-cross 500:799 10`
   - `bash tools/d367/actorplan/cg.sh /mnt/c/Flycast-Evidence/re4-dreamcast/actorplan-20261015/hwmodel-ap1b-cross`
   - `python3 tools/d367/actorplan/owned.py <ap0 cg> <ap1b cg>`
   - Measure incrementally, each arm against the previous stack (user plan).
2. Then ACTOR_PLAN item 1 (preflight once per call), default 0, measured the same way.

## Commands (paths relative to port/dreamcast; WSL root unless noted)

- **Build** (t15 recipe from this tree; label prefix, arm, extra knobs): `XON="PACE_MODE=off PC_SAMPLER_BYTES=8192" bash tools/d367/actorplan/build.sh <lp> rW [KNOB=v...]` -> `/root/probe/lanes/route/out-<lp>rW`. Use the trace arm `rT` for STRICT (XON without PACE_MODE).
- **hw model** (traces kept): `bash tools/d367/actorplan/hw.sh r101-t12 <lp>rW <name> 500:799 10`, then `bash tools/d367/actorplan/cg.sh <evidence>/hwmodel-<name>`. The second step builds the call tree and deletes the raw traces. `waitcg.sh <name>` waits for both.
- **Analysis:**
  - `owned.py <cg dir>...`: owned / objects split.
  - `selfwithin.py <cg dir> '<root regex>' '<exclude regex>' [top]`
  - `parents.py <cg dir> '<fn regex>' '<sub regex>'`
  - `fnlines.py <hwmodel dir> '<fn regex>'`: per source line.
  - `kern.py`: kernel cycles per iteration; it has the calibration path.
- **STRICT, not run yet** (copies of the logicwaste tools):
  - Fixtures: `mkfix.sh <arm> <json> tools/d367/fullplay/segments/{bell-warp.txt|bell-trg-warp.txt|door103-warp.txt}`, for fight / bell / door103.
  - Runs (Git Bash): `TRACE=1 bash t-run.sh <name> <arm> <fixture> 60`, two at a time under trace_lock.
  - Compare: `strict.sh <ref run> <cand run>` (logic_trace_diff --align frame).
- **Identity:** `objcopy -O binary -R .stack` on both ELFs, then `cmp`.

## Evidence

All under `C:\Flycast-Evidence\re4-dreamcast\actorplan-20261015\`:

| Path | Contents |
|---|---|
| `cg-cross\` | Call tree of the calibration traces |
| `hwmodel-ap0-cross\` | t15 base, proj + cg |
| `hwmodel-ap1-cross\` | Existing-knob arm: identical image |
| `_tools\` | Same scripts as tools/d367/actorplan |

The build log is `/root/probe/lanes-20261015/actorplan-k/logs-build.txt`; hw logs are in `actorplan-k/hw/`. Arm outputs `/root/probe/lanes/route/out-ap0rW` and `out-ap1rW` are rebuildable and may be pruned.

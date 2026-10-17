# Lane actorplan17: character draw plan (CPU-SAVINGS-PLAN step 2), 2026-10-16/17

Branch `lane/actorplan17` (base origin/t15/int b850c47d). Console A/B program: `lane/actorplan17-t16` (test 16 program
72871476 + this lane's commits). Knobs in `game/actorplan.mk`; all default 0. With every knob at 0 the image is
byte-identical (knob-off identity below).

## Knobs

| Knob | What it does | Ships? |
|---|---|---|
| `ACTOR_PROF=1` | Diagnostic only. Cycle spans of the owned character path per class (Leon / Ganado / other) and phase. Prints an `APROF` line every 300 frames. | Never in a play image |
| `ACTOR_PLAN=1` | Render only, exact. The owned character path replays proofs it already made instead of proving them again (list below). Runtime switch `re4dc_actor_plan_on`; warp line `actorplan 0\|1`. | Candidate |
| `ACTOR_PLAN=2` | Compare build. Every original proof also runs and decides; `APLAN` lines count reuses whose verdict differed (`bad` must be 0). | Test only |
| `ACTOR_PLAN_AB=1` | `BENCHMARK=1` only. Four bench scenes: cross off / on, farm off / on. | Console A/B disc |

`bench.cpp` gained `RE4DC_BENCH_SCENES` 2..4 and the start-screen scene menu from lane/stress16b b90c17d6. This only
affects `BENCHMARK=1` builds; with the default of 2 scenes the bench program behaves as before.

## Profile (step 1)

Measured at the r101 cross benchmark (`benchmark-r101-t12`), test 15 data, 6 Ganados alive.

**Flycast (`ACTOR_PROF`, emulated µs per frame).** Window: frames 482..781. Base `prof-p0b-cross`.

| Phase | Leon (2 OT passes, 8 chunks, 4,545 verts) | Ganados (2.3 drawn per frame, 9.4 chunks) |
|---|---|---|
| plan (bind, roles) | 200 | 374 |
| semantics + certificate | 155 | 129 |
| acquire (of which skeleton / palette blend) | 616 (407) | 573 (254) |
| preflight at acquire / at submit | 86 / 94 | 105 / 89 |
| second-pass checks | 182 | 13 |
| skin (positions) | 1,388 | 686 |
| light | 1,169 | 99 (flat probe colour) |
| pack | 751 | 401 |
| chunk overhead | 242 | 259 |
| **total, world flush excluded** | **4,874** | **2,751** |

**Hardware model (`ap17b0`, MODELLED).** Window: frames 500..799, stride 10, 30 frames.
- Whole frame: 56.40 ms (console fit 60.21).
- Characters: 9.18 ms. That is the owned transaction, 12.41 ms, minus the 3.23 ms PS2 world flush it triggers.
- `one_chunk` (skin, light, pack): 5.38 ms.
- Setup and proofs (transaction minus `one_chunk` and the flush): 3.80 ms.

**Repeated work found:**
- Leon's palette bind ran twice per call: once in the plan, then again in the palette build. The second run included
  the role scan and a 119-bone finite scan.
- Every run was preflighted twice per call: at acquire, then again at submit.
- Every frame re-ran the role scans for the role bindings and the current row (re-scanned from the lifetime tables).
- Every pass re-compared the header bytes of Leon's pose-hand TPL textures (16 small copies per texture).

## What ACTOR_PLAN=1 replays

Each reuse is keyed on everything its proof read.

1. **Leon's same-call bind token.** Inputs: model, transaction call, source frame, lifetime serial, binding revision,
   and owner fields. Between the plan's bind and the palette build only native code runs, which writes no `cModel` or
   `cParts` (the ACTOR_PROOF_LEAN audit), so the bone scan is not repeated either.
2. **The first submission reuses the acquire preflight.** It applies when `lean_held` is set, meaning the call's
   lifetime token holds. Cheap live checks still run: workspace, skin and texture leases.
3. **Word-OR finite scans.** Uses the same exponent test as `coarse_finite`.
4. **`re4dc_actor_role_bindings` memo.** Keyed on model, appearance, count and lifetime serial. On reuse it re-walks
   the info list and re-checks each info's record and `info_current` (per-info clauses: asset sections, `pData`,
   `tpl_addr`), plus the hand role. Two cases are never kept: a failure, and an info the readopt rule would try to adopt.
5. **`actor_current_role` memo.** Same key and live re-checks as item 4.
6. **TPL texture verdict memo.** A `None` verdict is kept together with the 19 words `texture()` reads (descriptor,
   header, R4NREF). Keyed on descriptor, row entry and serial. Palette rows and bump rows are never kept.

Every write to the lifetime tables (adopt, retire, revoke, forget, room rows, park, stream pending) moves the serial.
A clause that depends on game state is read again on every reuse.

**Not done:**
- Semantics static memo: about 0.1 ms. Chunk proofs are already cached by ID; what remains is struct compares.
- One-chunk known skin entry: about 0.06 ms. Not proven safe across the skin cache.
- Step 3 (fused transform + light + pack): priced below ("Step 3"), not built.

## Results (ms saved)

**Flycast, `ACTOR_PROF`, same window, deterministic logic (`prof-p3-cross` vs `prof-p0b-cross`):**

| | Leon | Ganados (2.3 drawn) | Total |
|---|---|---|---|
| Change in µs per frame | 4,874 → 4,599 (−275) | 2,751 → 2,552 (−199) | **−0.47 ms** |

In frames 782..1081 (3.6 Ganados drawn) the total is −0.52 ms.

**Hardware model, MODELLED (`ap17b3` vs `ap17b0`):**
- Character setup and proofs: 3.80 → 3.27 ms (**−0.54**).
- Characters with the flush excluded: 9.18 → 8.72 (**−0.47**).
- Whole frame: 56.40 → 56.42 nominal, 60.21 → 60.29 console fit. That is inside the model's ±1-2 ms layout noise.
  `one_chunk` moved +0.07 with 0.3 more chunk calls in the sampled frames.

**Console:** not measured yet. The A/B disc is below.

**Verdict.** The large version of the plan (estimate ≥2 ms) is not reached. The exact replays remove about 0.5 ms of
character setup. The rest of the per-character fixed fees are live checks (model, info and GX state, leases, packet
reserve) or real work (skeleton blend, skinning, lighting, packing).

## Gates

| Gate | Result |
|---|---|
| `ACTOR_PLAN=2` compare (`cmp-c4-cross`, `cmp-c4-farm`) | bind / pre / roles / row / hand: every check hit, **bad = 0**. Cross 599 / 1,878 / 2,431 / 6,305 / 16,884. Farm 599 / 5,990 / 6,269 / 6,157 / 17,398. |
| STRICT + decisions (`ap17nrT` knob-off vs `ap17yrT`, 60 s each, stop 2000) | **fight:** STRICT, MUST-IDENTICAL, 841 ticks. **bell:** STRICT, MUST-IDENTICAL, 397 ticks. **door103:** STRICT, MUST-IDENTICAL, 1,188 ticks (reaches r103). 0 overruns. |
| Knob-off identity | `ap17k1rW` == `ap17b0rW` (t15/int b850c47d), image 1ee3a782. `ap17t16K` == test 16 `out-t16rcrP`, image d551dab2. |
| Still pair at the cross (freeze 400) | Plan on vs plan off in the same image: identical (fb0 and fb1). Knob-off vs plan: fb0 identical; 2 pixels in fb1 differ. The knob-off arm against itself shows the same 2 fb1 pixels (Flycast run-to-run back-buffer noise), so the pair is pixel-identical. |
| KOS squeeze 48 KiB (twin `fpap17sqW` from `ap17qrP`, release identity OK, mastered on the test 16 disc tree) | **GATE PASS**, 10/10. Min headroom: fight 12,344, call 30,152, door 14,792, leave100 / leave103 12,392 B. 0 OOM lines. |
| KOS squeeze again after the table move (twin `fpap17srW` from `ap17rrP` at e2d1474a, identity OK 288b6092; evidence `kos2`) | **PASS 10/10**. Min headroom: fight 12,312, call 30,120, door 14,760, leave100 / leave103 12,376 B. 0 OOM lines. The script's own summary said FAIL for door and leave103 (`end_marker=0`): it read those logs before the captures finished. Evaluated again with the script's rules once every capture had its `capture stop` line, every run reached its end marker. |
| r100 s30 movie gate (H2 through s30, 400 s, stop tick 2500; run-length exception per the coordinator) | **340/340 on both arms** (`s30-plan` `ap17srW`, `s30-off` `ap17s0rW`). Same underruns (1) and silence bytes on both. `heap_before` 117,024 (plan) vs 125,216 (knob-off). |
| `ACTOR_PLAN=2` compare after the table move (`cmp-c5-cross`, `cmp-c5-farm`) | bad = 0; hit counts identical to c4 |
| STRICT + decisions after the table move (`ap17zrT` vs the same knob-off references; `st3-*-x`, door rerun `st4-door-x` after a LOG OVERRUN gap in `st3-door-x`) | fight 841, bell 397, door103 1,188 ticks: STRICT, MUST-IDENTICAL |
| Align logger (hwmodel, 60 s, cross + farm) | 0 MISALIGN, 0 HALT |
| `_end` / heap 4 | See the next section |

## Size

**10-17: the memo tables moved out of the padded block (e2d1474a).** `CHAR_DATA_BLOCK=1` pads the data of
`coarse_actor.o` to 16 KiB steps. The base had 3,776 B of slack, so 6 KB of memo tables crossed a step and added
10,304 B of padding. The tables now live in `re4dc_actor_plan_store` (4 KiB, platform `.bss`, `actor_plan.h`
`RE4DC_PLAN_ARRAY`). They are also smaller: 16 texture memos instead of 32, and role arrays of `kRe4dcActorRoles` (9)
instead of 16 infos. Hit counts in the `=2` compare did not change.

| Item | Before the move | After (e2d1474a) |
|---|---|---|
| `_end` (rT arms, knob-off vs plan) | +20,000 B | **+7,744 B** (`8c434ff8` → `8c436e38`) |
| Heap 4 (arena fit, `rW` arms) | −20,480 B | **−8,192 B** (12,005,376 → 11,997,184) |
| r100 s30 movie, `heap_before` | not run | 125,216 → 117,024 (−8,192), 340/340 on both |
| KOS squeeze | PASS 10/10 | PASS 10/10 (min headroom 12,312 vs 12,344) |

The disc below was built before the move (tree 4799bc79). Its behaviour is the same; only the layout differs.

## Step 3 (fused transform + light + pack): priced, not built

The coordinator's order applied: first repeated or avoidable work, then batching and data layout, then a fused C kernel,
and assembly only if the whole-frame gain justifies it.

**Where the time goes.** Leon on Flycast (`ACTOR_PROF`, µs per frame): skin 1,388, light 1,169, pack 751.
MODELLED `one_chunk` at the cross (`ap17b3`, all characters): 5.76 ms in total.

| Part | MODELLED ms | Notes |
|---|---|---|
| `pass_positions` | 2.31 | Kernel `avk_pos_skin_u16` 1.93. Per frame: base 275k cycles, data misses 44k, prefetch wait 30k, I-misses 17k |
| `pass_lights` | 1.12 | Kernel `avk_light_skin_n16` 1.00. Base 148k cycles, data misses 40k |
| `Part::whole` (pack) | 0.78 | |
| `Part::strips` | 0.25 | |
| `probe_dirs_all` + `probe_lights` | 0.36 | |

The kernels are generated, list-scheduled SH-4 loops (`mkavk.py`, 36.5 model cycles per vertex for the scheduled
loop). That works out to about 41 base cycles, or 57 cycles all-in, per record.

**Census of repeated work** (`ACTOR_PROF`, `prof-p5-cross`, frames 482..781, per frame):

| | Records | Distinct positions per chunk | Distinct positions per meshlet (sum) | Distinct normals per chunk | Distinct (position, normal, uv) |
|---|---|---|---|---|---|
| Leon | 4,545 | 3,115 | 3,724 | 3,209 | 4,345 |
| Ganados (2.3 drawn) | 2,202 | 1,137 | 1,482 | 1,344 | 2,097 |

**Candidates and their ceilings.** All figures are MODELLED estimates: census counts times measured per-record costs.

| Candidate | What it would take | Ceiling, MODELLED |
|---|---|---|
| Within-meshlet duplicate positions (Leon 821 records, Ganados 720), mostly uv seams and hard edges | Offline record reorder plus a "same position as the previous record" flag, and a `pos.tpl` (asm template) change to copy xyz / outcode instead of transforming | ~0.35 ms |
| Across-meshlet duplicate positions (Leon 609, Ganados 345) | A chunk-wide transformed-position table. Every record then pays a gather of about 15 cycles to save 31% to 48% of the transforms | about zero or negative |
| Duplicate normals in lighting (Leon 1,336 per chunk) | Per-normal colour memo. A stamp check costs about 6 cycles on every record | ~0.1 ms |
| Light setup per chunk (`probe_dirs_all` 7 calls per frame) | Already about one rebuild per skeleton per frame; the fold changes when the fill direction changes | <0.1 ms |
| Fused transform + light + pack in C | The passes already run per meshlet on L1-resident data (`kMaxVertices`), so fusing removes only per-meshlet loop overhead and in-cache copies. Pack expands vertices into strip corners by index, so it cannot be fused away. A C loop gives up the scheduled asm's 36.5 cycles per vertex | negative to ~0.1 ms |
| Source-data misses (pos 74k + light 40k cycles per frame, about 0.57 ms) | Interleave position and normal per record offline (one stream instead of three) | Layout lever; the hardware-model trust policy says console only. Ceiling about 0.3 ms |

**Verdict.**
- The total ceiling is about 0.5 ms MODELLED. That is below the coordinator's 1 ms threshold for a console disc, and
  below the model's ±1-2 ms whole-frame noise.
- The one candidate with a real ceiling (0.35 ms) needs an assembly template change plus an offline record format. The
  optimization rule only allows assembly when the whole-frame gain justifies it, and this gain does not.
- No prototype was built and no disc was made.
- Backlog, if wanted: the offline interleaved record layout, as a console-only layout A/B.

## Console A/B disc

| Item | Value |
|---|---|
| Program | `ap17t16B` = test 16 + bench knobs + `ACTOR_PLAN=1 ACTOR_PLAN_AB=1` (tree 4799bc79) |
| Data | Test 16 |
| Disc | `C:\Game Dev\Emulators\RE4DC-Bench-ActorPlan17-4799bc79\gdemu` |
| SD script | `C:\Game Dev\Emulators\re4-batch-sd-actorplan17-20261016\update_sd_actorplan17.py` (next free slot) |

Scenes (each 300..1200 room frames, then the results screen):
1. Cross, plan off.
2. Cross, plan on.
3. Farm, plan off.
4. Farm, plan on.

Smoke runs: Flycast 60 s with a short window (5..15). `actorplan 0/1` was applied, scenes 1→2 advanced, and the
farm-first variant ran scenes 1→2 at r103. The final disc booted into scene 1 at r101 (`smoke-ab-final`).

**Package audit (10-17).** `ab-package.sh` passes `PKG_SRC=/root/probe/lanes-20261015/t15k/pkgsrc-t14cand`
explicitly, following the coordinator's warning that the default `PKG_SRC` is a symlink into the shared base.

The first packages (00:05 and 00:20) ran the unfixed `t8-pkgtree.py`. Two consequences:
- **What those runs wrote:** this lane's overlays and the `pkg-t16rcrP` replacements went into the shared base, which
  was repaired at 00:39.
- **What the first disc picked up:** batch17's `dc/native/r101/ps2-wv5.*` from that base. These are unused files,
  since this program has `WORLD_VERT=0`.

The disc was packaged again (track03 9113c098). Its file manifest against the test 16 candidate disc shows:
- 0 files missing.
- 4 extra files: the scene fixtures.
- 7 files differ: `1ST_READ.BIN` and the six program overlays.

## Scripts

All in `tools/d367/actorplan/`:
- `build.sh`: arms.
- `mkfix.sh` / `mkbfix.sh`: fixtures.
- `t-run.sh` / `trace-run.sh`: Flycast runs.
- `strict.sh`.
- `hw.sh` / `cg.sh`: hardware model and call tree.
- `ab-build.sh` / `ab-package.sh`: the A/B disc.
- `farm-warp.txt`.

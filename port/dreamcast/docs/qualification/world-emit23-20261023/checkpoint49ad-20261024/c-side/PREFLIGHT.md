# world-emit23 preflight

**Plan only; not qualified.** Read takeover/current coordinator status, all CLAUDE rules, FIX23/carry, lane INBOX and select-only PAUSED. Inspected local origin/t15/int **933936ea7f45ba81c09277a780ed00111407aa23** through Git objects. Root freezes the actual post-stat/post-audits source before execution. No shared source edits, SDK/builds, guests, staging, merging or pushes. Dedup compact/QA and deferred re-strip I-001 remain unchanged. Source, harness and existing-output pins: preflight-pins.json.

## Reusable inputs and limits

The old /root/work/lanes/select-only23 tree is at dc87c4658d65ba992d266e3cb1893ecd485da661 with dirty native_static counters; preserve it. All three old ELF outputs and b1/s2/f1/f2 discs exist under /root/probe/lanes/route/out-so{N,Y,X}rW and /root/work/lanes/select-only23-scratch/discs.

| Old arm | SELECT/REPLAY/SUBMIT | ACTOR_SETUP/UV_SNAPSHOT | LEAN2 | Recorded ELF SHA256 |
|---|---|---|---|---|
| soN | 0/0/0 | 0/0 | 0 | 20c1936dca1e8785d2b15ee9b4f53676139ff246557a7e372cd54b648a49eac2 |
| soY | 1/1/1 | 1/1 | 0 | 2e2971b54ef8f4866d02dec22ac7e67e2ad7ec1639802ecce2a840b30199a579 |
| soX | 1/1/1 | 1/1 | 1 | bebaf958b095287a4c118cd79bce989f73f7c6d117637ee9d729569483ff4bae |

These programmes predate EMIT_PREFETCH and are not the requested current-recipe arms. All have WORLD_METER/QA_MENU1, PC_SAMPLER0 and diagnostic ARENA_FIT_KOS_BYTES262144. ELF hashes here are retained elf.sha256, not a fresh large-file rehash.

Reuse pinned scratchpad so23/scenes:
- b1: r101 cross -7914,0,2000, angle1.5708, alert30. Verify cap4 in alivelog.
- s2: r100 forest -99685,-484,-1343, angle2.246, rsf0x100/13, scenario0/0x10.
- f1/f2: same views with source freeze330.

Reuse an.py PT field semantics, but use explicit captures, complete common windows and n-weighted means. World=wopq+wxlu+wshell; report setup/cpu/wall separately. Historical87/50 parts are not meshlets or current census. Do not invoke old scripts unchanged: runpair uses70seconds; run1 bypasses trace_lock; pixm chooses the last wall-time shot; arms5 stashes shared source and enables unrelated switches; c5 deletes older outputs.

## Four-arm programme plan

Freeze one source/recipe/DATA/KOS/toolchain; retain identical original assets, VMU, cap4 and scene settings. Labels we23-<sha8>-R/L/E/B are new owned outputs.

| Arm | SCENERY_SELECT_LEAN2 | SCENERY_EMIT_PREFETCH |
|---|---:|---:|
| R current recipe | 0 | 0 |
| L selector | 1 | 0 |
| E emitter | 0 | 1 |
| B both | 1 | 1 |

Preserve SELECT_ONLY/REPLAY_LEAN/SUBMIT_BATCH1. Explicitly verify ACTOR_SETUP_LEAN0, UV_SNAPSHOT0, SCENERY_DEDUP0 and the newly frozen audit recipe; introduce no dedup alternates. Capture runtime view/quality/LOD, MESH_LOD_PX, SCENERY_FAR_LOD and cull flags. Old outputs compile MESH_LOD_PX3/FAR_LOD4, but QUALITY can select runtime lod_px. Do not substitute the earlier offline LOD5 estimate.

Concrete existing build primitives after root allocation (D is T/port/dreamcast/tools/d367):
```sh
. "$D/rr/recipe.conf"
BASE_CH2="$CH2"
# Repeat serially with (LEAN,EMIT)=(0,0),(1,0),(0,1),(1,1), new LABEL each.
CH2="$BASE_CH2 SCENERY_SELECT_LEAN2=$LEAN SCENERY_EMIT_PREFETCH=$EMIT" \
 T="$T" K="$OWNED_LOGS" LP="$LABEL" JOBS=1 bash "$D/ch2/ch2-build.sh" rP
FP_TREE="$T" FP_SKIP_IDENTITY=0 bash "$D/fullplay/fp_twin.sh" "$PLAY_OUT" "$LABEL-g"
```

One tree lease/one shared SDK slot/JOBS1, serial arms, release priority. Check actual flag propagation, resolved knobs, source/recipe/DATA hash, main/all14overlay ELF/raw hashes and staged tracks. R's objcopy -R .stack image and overlays must equal the exact same-source rr candidate; old dc87 identity is insufficient.

Timing twins: same WORLD_METER1, GAME_TICK_LOG60, PHASE_METER1, PC_SAMPLER0 and warp/view settings in all arms. No one-shot census, KOS squeeze or unrelated diagnostic changes in timing runs. Standard release-derived twins establish heap acceptance, not the old QA/262144 profile.

## Narrow census diagnostic proposal

Existing SCN_CENSUS1 (game/logiclod20.mk:58; native_static.cpp:629,3089,6110) gives120-frame aggregate visits/corners/strips. It has no indexed/plain, per-part/per-flush or indexed nr0 counts, so cannot answer INBOX. No patch applied.

Propose **SCENERY_EMIT_CENSUS=0 default**; nonzero selects a minimum UI capture frame. Capture one eligible frame in the target room, all passes/flushes, in separate b1/s2 diagnostic runs; repeat per arm if selected signatures differ.

Root-owned integration:
1. Isolated make validation/define and gated namespace/include. Knob0 preprocessing/object identity required.
2. At ps2_pass chunk_flush (native_static.cpp:6246), construct a diagnostic RAII scope BEFORE SubmitScope. Save immutable cctx/cpk/package references and original counts. Its destructor runs AFTER batch/SQ closure on normal and abort exits. Save counts because existing exits zero nctx/npk. Iterate retained picks after close; no per-pick persistent table or heap, and no logger in emit_pick/SQ/G2.
3. Per-part row: room/frame/pass/flush/queue slot, placement/source key plus part index, selected picks, indexed/plain meshlets and full vertex sums, whole/partial/nr0, transformed span, indexed nr0 vertex sum. Distinct placements must not merge by part index. Report zero-pick parts. Flush totals must equal part sums.
4. Track replay attempted/completed prefix and terminal result separately. Selected population remains a selection count after failure; it is not accepted emission. Missing pass/frame END, duplicate row or sum mismatch invalidates census.
5. Indexed=strip_count bit15. nr0=pk.nr==0; whole=0xff. Full indexed gather uses l.vertex_count; span is full for0xff, hi-lo+1 for nonempty partial, zero fornr0. Keep gather/span/output distinct. E's emit_corners at3063 skips only nr0's unused gather; bind/borrow/prime remain. No inferred transform saving for already-empty spans.
6. Each row below256-byte logger bound; split identity/count rows if necessary. Scope state has bounded scalars/references, no new resident array. Actual code/BSS/stack pricing remains a target gate.
7. Host extraction controls: mixed plain/indexed/empty, nr0 versus0xff, zero-pick part,48-part/320-pick pressure, multiple flushes and failure after earlier success. Assert accurate totals and logger outside SQ. Compile-disabled identity before target integration.

Build5 report is sensitivity for assumed500 pieces: all-plain +0.263840ms; indexed -0.923645ms;10%-empty indexed -1.417440ms, excluding data-cache latency. Census informs applicability; it does not turn separately measured leaves into current whole-frame timing.

## Harness execution after allocation

Stage on ext4 with existing test11/t11-fix.py, test8/t8-pkgtree.py, mkgdi.sh; lint loader and standard. Same original data in all arms, unique C: bases. C floor20GiB, live-process/trace-holder checks immediately before launch; release priority, <=3/lane/global16, plan serial or at most2 matched guests, each<=60seconds. Use trace_lock for all lane guests despite its older trace-only header.

```sh
export RE4DC_EMU=console FP_NOLIMIT=1
# Preserve existing WSLENV and add RE4DC_EMU:FP_NOLIMIT; assert Windows Python sees both.
TRACE_LOCK_OWNER="world-emit23-$LABEL-$SCENE" \
 bash "$D/trace_lock.sh" "$WINPY" "$FPD/fp_run.py" \
 --base "$BASE_WINDOWS" --cap "$NEW_CAPTURE_WINDOWS" --syms "$SYMS_WINDOWS" \
 --warp "$EXACT_SCENE_WINDOWS" --seconds 60 --period 0 --name "$LABEL-$SCENE"
```

Run b1/s2 in all arms; repeat matched samples if variance is material. Initial PT target f0 in[300,1140); analyze exact complete intersection reached by all arms and report actual tick count. Missing warmup/windows stays pending; do not extend70seconds. Record scene/cap4, actual world package binding, phase windows and no fallback/refusal/fault. Report R→L, R→E, R→B and interaction B-L-E+R. Flycast timings remain MODELLED; physical-console readings decide speed.

Stills use f1/f2 freeze330. Match source tick, camera, viewport, actors, framebuffer and upload/present state before pixel comparison; inventory/hash both framebuffer images. Reuse diff arithmetic only after that match. Latest directory or arbitrary wall-time shot is insufficient.

## Gates and console pair

Each ON arm: current matched standard KOS48KiB held/headroom; H2 s30 340/340, restored1 and actual heap_before; TEXCHK with census diagnostics confirmed active; CAST-GC; VRAM/refusal/fault0; GDEMU seed1 throughr101/door. Do not infer diagnostic pass from absent flags. Final release retains standing10 seeds; seed1 is this render-only quick row. Reuse root's authenticated <=60s H2 fixture; stock rr300s launcher is unsuitable unchanged. Compare exact-profile OFF/ON heap, not historical94KB prose.

After gates, root stages C:\Game Dev\Emulators\RE4DC-QA23-WorldEmit-{Off,On}-<sha8>; Off=R, On=B. Reuse rr-qa primitives with unique labels to avoid its same-SHA QA cache reusing the wrong arm. Standard QA flags, no census/KOS contamination, source/programme/DATA/README pins, no warp, standard lint. STEPS: QA r101 cross and house-wall view, cap4, same overlay/view/quality; wait stable, record fpsx10 three readings per arm. Console results separate. No SD/publication.

Root owns recipe decisions after console feedback. Keep both switches off until qualified; report nil/slower results too. No cloud branch/queue changes.

Source implementation checkpoint: 2adba133279d62d49416be99dbb9180df50e2846 on origin/wip/world-emit23-census-20261023, based on a5e972e44. New game/platform/include/scenery_emit_census.hpp and tools/d367/world_emit23 contain the diagnostic, capture parser and RAM controls. STATUS.md records exact shared claims and open target/runtime gates. The actual implementation uses a bounded48-part progress array (384B stack before surrounding fields), so fallback continuation retains per-part attempts; this supersedes the earlier no-array proposal. No heap allocation. Still no SDK or guests.

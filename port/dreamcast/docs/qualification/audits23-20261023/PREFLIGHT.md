# audits23 preflight — 2026-10-23

**NOT QUALIFIED / no recipe enablement.** Bounded read-only review at local `origin/t15/int` **933936ea7f45ba81c09277a780ed00111407aa23** (same before/after); fixes originally merged at 377569a3. Root owns implementation, integration and gates. No builds, guests, staging, SDK/recipe edits, cloud operations or shared runtime edits performed.

Read takeover/COMMON/CLAUDE and audits23 INBOX, all three audit reports, the four fix paths/build wiring, rr scripts/fixtures, and arena23 sealed handback/cache notes. Repository is `/root/work/re4-dreamcast`. Abbreviated `game/`, `tools/`, `docs/` and `patches/` paths are under `port/dreamcast/`; `src/` is at repository root.

## Findings that block qualification

1. **KOS_CACHE_P2=1 cannot prepare in the current release environment:** `tools/d367/build-r21.sh:104-106` selects `/root/work/kos-re4dc-d367` and explicitly sets PATH to its wrappers, compiler bin, `/usr/bin:/bin`. There is no executable `rg` there. Frozen `kos_cache_audit/prepare.py:33-35` invokes `rg`; both preparation and its prelink check therefore fail with FileNotFoundError. Independently executed only the read-only `validate()` portion: d367 HEAD and all eight input hashes pass before this error. Do not change the SDK to resolve this. Owner can provide the required host dependency or a reviewed fail-closed inventory implementation outside the SDK.
2. **Generic rr full does not qualify this unit.** Current `/root/rr/state/last-good` is **377569a3586b8c979ff0fdc769ae36c64d32f81f**, image **dba997478ac575140777e60507d854e2138bdfcabe7d546af75758ca0f64a6ab**. That commit contains the fixes but leaves all four OFF. `rr-cycle.sh:167-176` rechecks last-good rather than building a prospective four-knob candidate. Pin a fresh private release/twins and their resolved knobs first; do not invoke rr full expecting it to enable the fixes.
3. **Required coverage is missing from stock rr:** `rr-jobs.sh:17` omits r10c from ALL_ROOMS. `recipe.conf:69` has `CH2_REF=""`, so trace arms/bell comparisons are skipped; even enabled, decisions only cover h2/bell/door103/r11b (`rr-jobs.sh:83`, `rr-judge.py:200`), not Mendez. Release-checks seg-mendez is a kill/exit rig, not an A/B decision comparison. Stock census/entry does not prove the r117 light mechanism was solved or that the dam first-villager event loaded. Add explicit scoped checks, with the same all-four-ON unit and matched OFF control where decisions are required.
4. **h2 heap receipt is not mandatory in rr's pass predicate:** `rr-judge.py:115-123` accepts 340/340 without `heap_before`; it only records that field if found. Audits handback must separately require the heap_before line/value and inspect the exact release/twin pair.
5. **Whole-cache invocation frequency/interrupt-blocked duration are unmeasured.** The P2 helper and audit fixtures contain no per-room runtime measurement satisfying INBOX. Opcode-model instruction counts are not duration. A separately reviewed bounded diagnostic is needed; no logging/hash under the IRQ-masked helper, and account for diagnostic image/layout changes.
6. **Arena fixture remains unbound for this new candidate.** The sealed arena lane has no ready two-minute executable fixture/command in the files reviewed. Its release programmes af84fd8f have DBG_WARP0; its gate request explicitly requires a reviewed gate-twin/profile rebind and preserves original B/B3 controls. `test_arena23_allocator.py` is a host allocator fixture, not the user arena repro. Do not substitute it or infer hardware repair from a generic fight/KOS pass. Exact arena room/input/profile and console two-minute instructions must be bound by the owner before that row can pass.

## Does P2 reach KOS library users?

**The source/build design covers them, rather than only a game shim; actual final linked coverage is still a gate.** `game/kos_cache_p2.mk` compiles complete replacement exec.c, dmac.c, g1ata.c and broadband_adapter.c TUs plus cache_p2.S into OBJDIR. It also recompiles game misc/modules/subscreen_backing with an overlay arch/cache.h and forced `require_p2.h`. The shared SDK and libkallisti.a remain unchanged.

`game/Makefile:3431` includes the mk; its added objects enter OBJS, passed by `game/tools/link.sh` to kos-c++ before KOS_LIBS. The installed kos-c++/kos-cc wrappers append the `--start-group -lkallisti ...` archive group after explicit objects. Complete replacement TUs are intended to satisfy the archive member roots before extraction. `check_objects.py` requires real T definitions for arch_exec_at/dma_map_src/g1_ata_write_lba_dma/bba_tx and undefined references to arch_dcache_wback_all_p2, plus the helper's real definition; it rejects stub resolution. The inherited cloud archive check used a synthetic partial archive, not this full release library. Final ELF/map/disassembly must establish one real helper, caller references and no extraction of old inline caller members (including overlay link passes); object symbols alone do not prove that.

Release SDK: `/root/work/kos-re4dc-d367`, HEAD **804b3195ebd1a06a27cc2b3a5eacf7a2429040a3**; lib/dreamcast/libkallisti.a **5770580 B**, SHA256 **5e2d867fb5825e7825e1843f2542446288e18c383341a58426e452a0b620daaf**. This differs from `/root/work/kos` library **5739242 B**, **c75afb32915b6b5d355e1fe6fe1e6f7da34af4424b3933930ec59d2f905cb571**; do not price/prove one as the other. Both have the four expected real archive root symbols and no P2 helper definition. Both source trees pass the eight pinned hashes. A separate read-only Python traversal using the frozen audit's exact comment/API-token expressions found the expected four callers in each: exec.c lines45/58, dmac.c86, g1ata.c895, broadband_adapter.c628. This supports source coverage without bypassing the production inventory prerequisite.

The threshold remains >=65560 B. The new external helper executes cache-array RMW from P2 with full SR save/restore and the reviewed CCR bank path. The source inspection found no additional confirmed runtime defect in these four fixes. An arena crash cause/repair remains unproven.

## Existing fixtures and exact entry points (NOT RUN)

All relative commands below run from an isolated checkout pinned to the audited candidate; output must be an owned RAM/private directory. These are recorded future commands, not authorization to run now.

```sh
D=port/dreamcast/tools/d367
python3 "$D/effect_pool_audit/inventory.py" --output "$OUT/fx-inventory"
python3 "$D/effect_pool_audit/test_failures.py" --output "$OUT/fx-failures"
python3 "$D/dam_audit/check_missing_actor.py" --output "$OUT/dam-host"
# Object/model checks require the separately allocated compiler/build slot:
python3 "$D/effect_pool_audit/build_controls.py" --output "$OUT/fx-objects" --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$PUBLIC_SDK"
python3 "$D/dam_audit/build_controls.py" --output "$OUT/dam-objects" --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$PUBLIC_SDK"
python3 "$D/kos_cache_audit/verify.py" --output "$OUT/cache-objects" --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$PUBLIC_SDK"
python3 "$D/kos_cache_audit/check_thresholds.py" --prefix "$SH4_PREFIX" --kos-root "$KOS_ROOT" --prepared "$PREPARED" --output "$OUT/cache-thresholds"
python3 "$D/kos_cache_audit/check_helper.py" --prefix "$SH4_PREFIX" --object "$CACHE_P2_OBJECT" --output "$OUT/cache-helper"
```

Cloud reports retain 48 pool controls, 36 r117 controls and 40 dam scenarios, plus the KOS 384-case instruction model/threshold controls and original default-off object comparisons. Those are inherited evidence at their reported baseline; no fresh tests or current-profile identity claimed here. EM_READ_RETRY defaults to1 at `game/game30.mk:3519`; no current CH2 token disables it. R10C_SPAWN_LIVE_GUARD=1 refuses EM_READ_RETRY!=1. Explicitly pin1 in the audit invocation and verify resolved output. The four defaults are0 (`esppool.mk`, `kos_cache_p2.mk`, `game30.mk`).

Private candidate command shape after root allocates gates:

```sh
. "$T/port/dreamcast/tools/d367/rr/recipe.conf"
CH2="$CH2 EM_READ_RETRY=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1" \
  T="$T" K="$AUDIT_LOGS" LP=aud23 bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" rP
# fp_twin.sh reproduces the exact candidate recipe plus diagnostics. Keep identity enabled:
FP_TREE="$T" FP_SKIP_IDENTITY=0 bash "$T/port/dreamcast/tools/d367/fullplay/fp_twin.sh" "$PLAY_OUT" aud23g
FP_TREE="$T" FP_SKIP_IDENTITY=0 bash "$T/port/dreamcast/tools/d367/fullplay/fp_twin.sh" "$PLAY_OUT" aud23c KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150
```

Existing rr job templates (`rr-jobs.sh`, Windows Git Bash; FPD is the Windows-accessible frozen fullplay directory, EVW Windows evidence, BASE_G/BASE_C exact master directories, SYMS_G/SYMS_C bound to those twins):

```sh
python "$FPD/fp_run.py" --base "$BASE_G" --cap "$EVW/h2" --syms "$SYMS_G" --seconds 300 --warp "$FPD/segments/h2-warp.txt" --pad "$FPD/segments/h2-pad.txt" --stop 'route movie terminal=. id=10030' --grace 10
bash "$FPD/kos_squeeze.sh" "$BASE_C" "$C_LABEL" "$EVW/kos" '49152:0 49152:1' fight
# Full KOS: repeat the preceding command for call, door, leave100, leave103.
MAXP=5 bash "$FPD/gdemu_gate.sh" aud23 "$EVW/gdemu" "$BASE_G" "$SYMS_G" "$FPD/segments/door103-warp.txt" 1 2 3 4 5
MAXP=5 bash "$FPD/gdemu_gate.sh" aud23 "$EVW/gdemu" "$BASE_G" "$SYMS_G" "$FPD/segments/door103-warp.txt" 6 7 8 9 10
```

Existing census warps: `tools/d367/castgc/warps/{r117,r10c,r200}.txt` (60s template rr-jobs:56); explicitly add r10c. r10c warp is an entry at27865,-15316,43935, not a first-villager event proof. `ch2/warps/a-r117.txt` is an Ashley still with rescue flag, not a light puzzle solve. Bell fixture is `fullplay/segments/bell-trg-warp.txt`; matched trace logs compare with `tools/game30/decision_cmp.py REF RUN --align frame` (STRICT reported separately). Mendez uses `fullplay/segments/mendez-{warp,pad}.txt`, 900s release-checks row expecting r11f -> r10f; source damage/QTE inputs are diagnostic and must be described. An additional matched Mendez trace/decision comparison is required by INBOX.

Existing outer command is `MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /root/rr/bin/rr.sh full`; **do not use until its last-good/candidate identity and recipe binding are correct**. It also performs builds/guest jobs and cleanup, so it was not invoked here. Installed rr.sh, rr-cycle.sh, rr-jobs.sh, rr-judge.py and release-checks.conf match the frozen source hashes; installed recipe.conf differs/stale. rr-cycle correctly reads recipe from the built commit, not only that installed copy.

## Handback

Preflight is complete; four-knob acceptance is open. Resolve rg dependency, freeze exact stat-bytes-successor candidate/profile and OFF control, obtain current full linked identity/coverage, then allocate/run the required shared gates plus the explicit missing event/decision/arena/cache-measurement rows. Only after those pass should the owned audits branch commit CH2 += the four knobs. No current recipe acceptance or console/hardware claim.


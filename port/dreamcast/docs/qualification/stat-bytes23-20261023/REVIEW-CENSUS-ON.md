# STAT ON census qualification — PASS 27/27

Frozen source **2a14662d4b025031cd93f64eed6a5d8159d473b7**, clean `/root/work/lanes/stat-bytes23-complete` before/after. **Bounded ON census CLEAR** for the 26 current rr rooms plus r10c. Root owns all remaining gates/integration/recipe. This is Flycast console regression evidence, not physical-console or performance acceptance and not a repro of every repaired stat site.

- CAST-GC: **1584 census rows, 61 room/model rows, 0 unallowed GC/MIXED rows — PASS**.
- NOT-DRAWN stat23-on: 905 alivelist lines, 25 room/id rows, 0 alive but never drawn (PASS)
- LEON-GC: **27/27 PASS**, no fallback rows.
- TEXCHK: **27/27 PASS**; no new allowlist.
- Every target room has actual entry plus 23–118 NMRS/native-or-crowd draw rows, target lifecycle/heap and VRAM records, and 4 screenshots (**108 PNGs**).
- HALT/FAULT/RE4DC MISSING/log-overrun/no-contiguous: **0**. Heap checks ok; no harness/screenshot errors.
- Guest lifetime guard: **40.859–41.516s**, 55s safety cap fired 0 times; all owned guests and the coordinator exited. These durations describe containment only.

Rooms: `r100, r101, r102, r103, r104, r105, r106, r107, r108, r109, r10a, r10b, r10f, r111, r112, r113, r117, r118, r119, r11a, r11b, r11c, r11d, r11e, r11f, r200, r10c`.

## Exact binding

Release data is unchanged 933936ea7f45ba81c09277a780ed00111407aa23; new 2a programme and all 14 staged overlays only. `base-diff.txt`: 1697 identical members, 18 allowed differences (programme + 14 overlays + 3 diagnostic fixtures), 0 forbidden. ON-c resolved STAT_ROUTINE_BYTES=1 / STAT_DIAG=0, CENSUS=1 / period=150, TEX_CHECK=1, MCHECK_LEONGC=1. Staged track03 SHA256 **e6960258ab7732b3fb925ec6dd5951782adb1f88932f464dfb7cd2c1e35c8c53**. Source/ELF/overlay/knob hashes are under `takeover-2a14662d/identities/on-c-*`.

Every guest ran WSL stat-guest-slot -> trace_lock -> owned bounded launcher -> unchanged frozen fp_run.py, sharing at most 3 total stat guests and global 16 trace slots. Launcher verifies exact capture executable path/SHA against the console binary, owns its Popen handle, caps at 55s and preserves evidence. Actual console executable SHA **8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a**; harness SHA **646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747**. FP_NOLIMIT=1; 40s reader, screenshots every 15s. No global process kill. The coordinator was paused after 14 at root request for H2/KOS fairness, then resumed for 13; root's guests retained their acquired slots.

The 27 copied source warps retain hashes. r11b gets rr's existing reset flag; warps without alivelog get read-only alivelog 150 (exact edits in receipt.json). Canonical cast_gc.py --not-drawn, mcheck/leongc_check.py and texchk/texchk.sh judge every log with unchanged pinned allowlists. Per-room outputs/input fingerprints and failures remain explicit; no room-specific failures occurred. Earlier successful checks were reused only when input/output hashes matched.

## Evidence and limits

Evidence root: `C:\Flycast-Evidence\re4-dreamcast\stat-bytes23\takeover-2a14662d\census-on`. `results.json` contains every room, historical933 comparison, memory rows, screenshots/hashes and tool receipts. `base-identity.json` and `final-receipt.json` bind the source/programmes/assets/scripts; exact executed launcher sources are preserved in scripts/. C summary is CENSUS-ON-RESULTS.json. Final receipt SHA **a69e6c541e3f6ed0ae4fd4f761d8bdc1d0bc12b79c532489cdbb7c89cc2ba69a**; results SHA **ad4e9639cd839ed259280d7d39086f9a67fe272c8f1636e12d5129f8292f686d**.

Existing rr933 census/logs are historical baseline only: 26 rooms, 57 model rows, TEXCHK 26/26; none count as fresh ON results. Different windows/sample counts are not a performance comparison. This census establishes entry/draw/resource regressions for the listed fixtures, not puzzle solves, first-villager/other per-site stat repros, full-route equivalence or pixel identity. Late overlays absent from the staged disc and unvisited late rooms remain untested. No SDK/HEAD/shared runtime/recipe/cloud changes or builds by this reviewer.



# hwmodel: SH-4 hardware projection for D367 candidates

Flycast's dynarec does not model the SH-4's caches, and it pairs instructions naively. It
charges roughly 1.0 cycle per instruction plus 2 cycles for each of the first three memory
operations in a block. A Flycast ms/frame is therefore a poor proxy for a real Dreamcast.
These tools trace a candidate instruction by instruction in a patched Flycast interpreter. They
replay the trace through an SH-4 timing model and report projected hardware ms/frame per
function and per area, next to what Flycast charges for the same instructions.

Reference numbers for the LD build, steady-state frames 2401..2520:

| | Flycast | hardware (nominal) | band (low..high) |
|---|---|---|---|
| LD (`d367-native-static-ld`) | 95.6 ms | 157.8 ms | 136.7 .. 186.5 |
| LF + frontend30 + UI_VRAM + tex-vq3 | 79.6 ms | 130.3 ms | 114.7 .. 151.1 |

## One command

```
port/dreamcast/tools/hwmodel/hwproject.sh [--name N] [--drop-traces] <evidence-dir | build-dir>
```

- **Input.** Use a harness capture dir (`re4dc-game.elf`, `syms.txt`, `disc-output/disc.bin`).
  A `build.sh` output dir also works, with the disc in `./disc`, `../disc` or `--disc FILE`.
- **What it does.** It stages a new evidence dir, `$HWM_EVROOT/hwmodel-<name>`, from the hwtrace
  binary dir `$HWM_BIN`. It boots the disc in the interpreter, which exits by itself after the
  window. It then runs `hwsim` in four variants (nominal, low, high and no-DMA) and prints the
  area table. The delta against the reference projection `$HWM_REF` (LD) includes a "kept"
  column: how much of each area's Flycast delta survives on hardware.
- **Re-simulation.** Pass an existing `hwmodel-<name>` dir to re-simulate its traces, for
  example after a model change. No Flycast run is needed.
- **Cost.** About 6 minutes wall per candidate:
  - about 4.5 min for the interpreter trace run, one Flycast slot, one core;
  - about 1 min for `hwsim` (4 parallel jobs);
  - under 30 s for disc staging and the report.
- **Disk.** Traces take about 0.8 GB (15 frames of about 55 MB). `--drop-traces` deletes them
  after the projection and keeps a size list. The disc copy (about 0.6 GB) is staged in
  `HWM_DISCS` and deleted after the run. A full disk truncates traces silently. `hwproject.sh` then refuses to
  report: it checks the simulated insns/frame against `hwtrace.log` and writes
  `proj/INVALID.txt`.
- **Representativeness.** The 15 traced frames (2401..2520 step 8) come within 0.3% of the
  120-frame instruction count. For LD, step 8 and step 4 projections agree to 0.1 ms.

Environment variables and their defaults:

| variable | default | meaning |
|---|---|---|
| `HWM_BIN` | `/mnt/c/Flycast-Evidence/re4-dreamcast/hwmodel-bin` | hwtrace `flycast.exe` + harness scripts + `emu.cfg` with `Dynarec.Enabled = no` (on C: since 2026-10-17) |
| `HWM_EVROOT` | `/mnt/c/Flycast-Evidence/re4-dreamcast` | where new `hwmodel-<name>` dirs go (on C:, user 2026-10-15) |
| `HWM_DISCS` | `/mnt/c/Flycast-Evidence/re4-dreamcast/_hwmodel-discs` | disc staging, outside evidence dirs; deleted after the run, sha256 kept in `disc-output/` |
| `HWM_MINFREE_MB` | `10000` | refuse to start a trace run that would leave less than this free on the trace drive |
| `HWM_REF` | `$HWM_EVROOT/hwmodel-ld2/proj` | reference projection for the delta table |
| `HWM_TID1`, `HWM_TID12` | LD `pcs_symbolize.py --csv` tables for tid 1 / tid 12 | split of shared GC helpers into game-render-side / game-logic |
| `PCS_SYMBOLIZE` | profiler `pcs_symbolize.py` | used only with `--pcs run.pcs` (sampled Flycast ms of a dynarec capture) |

## Files

| file | role |
|---|---|
| `hwsim.c` | SH-4 timing model driven by traces (`gcc -O2 -o hwsim hwsim.c -lm`; `hwproject.sh` builds it on demand) |
| `hwreport.py` | per-PC output to per-function / per-area tables (`functions.tsv`, `areas.tsv`), what-ifs as `wi_*` columns |
| `hwcompare.py` | candidate vs reference area table (called by `hwproject.sh`) |
| `gen_whatif.py` | builds what-if inputs from a baseline: I-cache relink maps, ORA pin sets, copy/SQ skip lists, FDIV→FSRRA sites |
| `run_whatifs.sh ELF TRACEDIR OUT` | sensitivity band + 20 what-ifs (perfect I/D cache, ORA, OIX, relink, prefetch, write-allocate, FSRRA, copy removal...) |
| `flycast/hwtrace.patch` | Flycast patch (base `12bb43652`): interpreter trace + DMA events |
| `flycast/build_fc.bat` | MSVC + Ninja build of the patched Flycast |
| `flycast/hwtrace-run.ps1` | per-run launcher placed in `HWM_BIN` (sets the `HWTRACE_*` env, calls `boot2.ps1`) |

## The Flycast side (`flycast/hwtrace.patch`)

Apply the patch to Flycast `12bb43652`. Configure with
`-DUSE_VULKAN=OFF -DUSE_BREAKPAD=OFF -DUSE_DISCORD=OFF -DUSE_LUA=OFF -DUSE_DX9=OFF` and build
(`build_fc.bat`). Then create `HWM_BIN`:

1. Copy the harness template (`boot2.ps1`, `read_log.py`, `read_pcs.py`, `data/`).
2. Copy the new `flycast.exe`.
3. Add `emu.cfg` with `Dynarec.Enabled = no` under `[config]`.
4. Add `hwtrace-run.ps1`.

Never replace the template's `flycast.exe`. The hwtrace build does nothing unless `HWTRACE_DIR`
is set and the dynarec is off.

- The patch sets `CPU_RATIO = 1` (non-strict interpreter), so guest time runs at one cycle per
  instruction. This only changes pacing, never the traced instruction stream.
- `HWTRACE_FRAMEADDR` is the physical address of the `re4dc_pcs` LAST_FRAME word:
  `syms.txt` 4th field + 0x0c000000 + 64. Every store to it ends a frame. It needs a
  `PC_SAMPLER=1` build, which provides `syms.txt` field 4.
- Env: `HWTRACE_COUNT=A:B` gives per-PC execution counts (`counts.bin`).
  `HWTRACE_TRACE=A:B:S` gives full traces `trace-NNNNN.bin`. `HWTRACE_EXIT=1` exits after the
  window. The per-frame log is `hwtrace.log`: `frame V insns N cycles C [counted] [traced]`.
- Trace format: little-endian u32 pairs.
  - `w1>>28 == 1`: an instruction run (w0 = start pc, low 28 bits = count).
  - Otherwise an event: w0 = address, `w1 = type<<28 | sizecode<<24 | (pc>>1 & 0xffffff)`.
  - Types: 2 read, 3 write, 4 pref, 5 ocbi, 6 ocbp, 7 ocbwb, 8 movca, 9 SQ flush, 10 sleep,
    11 DMA start (sizecode = kind: 1 ch2→TA, 2 ch2→texture, 3 PVR-DMA, 4 G2/AICA, 5 GD-ROM),
    12 DMA length (w0 = bytes).
  - Events precede the run that contains their instruction.

## The model (`hwsim.c`)

- **Pipeline.** In-order dual issue with the SH-4 group/pairing table (SH-4 Software Manual,
  section 8), issue rates and latencies, and the F0 (FTRV/FIPR) and F3 (FDIV/FSQRT) locks.
  Branch redirects cost 2 cycles (BT/BF/BRA/BSR taken) or 3 (JMP/JSR/RTS/BRAF/BSRF).
- **I-cache.** 8 KB direct-mapped, 32 B lines, index `[12:5]`. A miss is a line fill that
  blocks issue.
- **Operand cache.** 16 KB direct-mapped, index `[13:5]` (KOS CCR: OIX=0, copy-back,
  write-allocate).
  - Fills are critical-word first. There is a write-back buffer.
  - MOVCA.L allocates without a fill. PREF is a non-blocking fill.
  - OCBI/OCBP/OCBWB are supported.
  - `--oc-kb 8` models ORA, with `--pin` for the RAM half.
- **Memory.** One external bus with a 4-bank, 2 KB-row SDRAM model. The bus carries fills,
  write-backs, SQ bursts (to the TA), uncached accesses (Sega access-time table) and DMA
  bursts.
- **Penalties.** Taken from the SH7750 hardware manual and Sega's SH4 access-time note, and
  stated in bus clocks ×2:
  - nominal: fill 14 (row hit) / 24 (row miss) + 4 overhead, write-back 8/18, SQ burst 14;
  - low/high: fill 12..16, 20..26, SQ 10..24.
- **Stall attribution.** Stalls are attributed per PC to base, dependency (load/FPU/FDIV/other),
  FPU lock, branch, I-miss, D-miss, prefetch wait, SQ and uncached. Each PC also gets the
  Flycast dynarec charge for the same instructions. Over the LD traces that charge sums to
  95.6 ms, against 95 ms sampled in the dynarec.

### Known gaps

The projection is biased low. The penalties are documented values, not measured ones.

- **TA FIFO backpressure.** Covered only by the SQ cost band.
- **DMA contention.** Modelled, but the LD and frontend30 windows issue no DMA from RAM. TA
  input goes through store queues, and there is no audio or GD streaming in the window.
  - An `AICA_AUDIO=1` build will show its G2/AICA DMA or SQ traffic here.
  - The G2 FIFO wait on uncached AICA writes is modelled only as the per-access table cost.
- **Coherency cost.** The trace contains the flush instructions, but DMA-coherency
  write-backs issued by other agents are not modelled.
- **Interrupts and exceptions.** Not modelled beyond the traced handler code.

One hardware session calibrates the penalties. Run five microbenchmarks:

1. pointer-chase over 64 KB (read-miss latency);
2. a streaming store (write misses);
3. a 16 KB code loop (I-cache misses);
4. an SQ burst loop;
5. an FDIV chain.

Put the results into `--fill-*`, `--wb-*` and `--sq-cost`.

## Console column (refit 2026-10-15, lane storemiss)
`hwsim --console-fit` (hwproject's "console" column) is the refit **D fill +6, I fill +5, store miss 0**, constrained by
the console Bench A (ACTOR_MOVCA, no change) and Bench B (MEM_MOVCA, +0.5 ms house) pairs; `--console-fit-w70` keeps the
first fit (D 0, I 4, store miss 70) for comparison only. Label results "MODELLED console-fit". Render parts are still
under-priced by a cause the model does not simulate (console/model: actor draw 1.11-1.19, world 1.07-1.19; logic
0.96-1.03). MOVCA / store-miss levers are CLOSED: no store-miss lever is above 0.13 ms. Tools: miss/storemiss/refit.py,
miss/reprice.py (default = refit, `--w70` = first fit).

## Phase stamps: calibrating against console QA-link PT logs (2026-10-31)
`hwsim --ticks <proc_tick> --tick-zero <zero_tick>` (addresses from `sh-elf-nm`: `__ZL9proc_tick`, `_zero_tick`) writes
`PREFIX.ticks.tsv`: the modelled cycle of every store into debug.cpp's `proc_tick[]` / `zero_tick` per traced frame.
`phases.py PREFIX.ticks.tsv [console_pt.json KEY]` turns them into the same phases tick_log.cpp reports on the console
(setup, each move/trans marker, logic, trans, post, cpu), so a model run lines up with a GAME_TICK_LOG / QA-link capture
phase by phase. `console_pt.py LOG...` averages the complete PT windows of QA-link logs. Model ticks are bimodal (drawn
vs skipped): compare drawn-tick setup and all-tick logic. First fit (ALL ON 20318342, r100 A/B/C): logic x1.16,
render setup per drawn tick x1.19, objTrans x0.73 (C:\Flycast-Evidence\re4-dreamcast\hwcal31-20261031\CALIBRATION.md).

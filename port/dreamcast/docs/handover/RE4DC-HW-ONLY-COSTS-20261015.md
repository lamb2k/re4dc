# RE4DC r101: costs only real hardware pays (crash lane, 2026-10-15)

The question: on preview 2 (t12r8pP) the console runs r101 at 19.9 fps facing a wall, about 12.5 fps at the cross
(the same with FSAA) and about 10 fps in combat. Which costs does real hardware pay that Flycast and the model do not
charge?

Every count below comes from the Flycast observer, not the console: the interpreter with the operand-cache model and
the new `HWTRACE_HWCOST=1` census. The tools are in lane/ss-chain-check afd595a1 (tools/d367/hwready/observer).

## Setup

- Build: ssctW = preview-2 recipe + DCINV_PURGE=1 + SS_CHAIN_CHECK=1 + DBG_WARP=1, on the preview-2 data tree.
- Runs (1 minute each):
  - hc2 combat: benchmark-r101 (Leon by the cross, crowd alerted at room frame 30). Window: rendered frames 270-360.
  - hc3 away: same position, angle -1.5708, no alert. Window: frames 330-360.
- Units: counts are per rendered frame.

## Counts per frame

| | combat (hc2) | away (hc3) | real-hardware cost not in Flycast |
|---|---|---|---|
| Operand-cache read misses | 100,000 | 82,000 | line fill from SDRAM |
| Operand-cache write misses (write-allocate) | 29,500 | 23,300 | line fill |
| Write-backs of dirty lines | 48,600 | 40,500 | bus write |
| Prefetch fills (pref) | 22,400 | 18,900 | bus, asynchronous |
| SQ flushes to the TA (32 B each) | 25,700 (820 KB) | 18,700 (600 KB) | TA FIFO back-pressure |
| FPU ops | 2.55 M | 2.06 M | - |
| FPU denormal inputs | 0 | 0 | - |
| FPU ops with DN=0 | 2,400 | 2,400 | only KOS context save (save_regs_finish, fmov) |
| Double-precision (PR=1) FPU ops | 3,000-3,300 | 3,600 | re4dc_model_packet_reserve (8c02fbac) |
| Uncached RAM | 32 reads / 950 writes | same | memset over a P2 buffer (L_store_long_loop) |
| AICA RAM writes (G2) | 205-410 (11,500 in the alert window) | 273 | g2_write_block_32 + g2_fifo_wait polls |
| Holly registers | 110-190 reads / 210-360 writes | 134 / 262 | G2 FIFO polls, irq9 handler |
| VRAM writes from the CPU | 617 | 617 | pvr_set_presort_mode rewrites 600 words every frame |
| PVR registers | 8 / 19 | 8 / 79 | - |
| P4 registers | 1,100 reads | 980 | timer reads (__dreamcast_get_ticks, sq_lock) |
| ocbi / ocbp / ocbwb | 45-70 / 0 / 1,200 | 38 / 0 / 1,160 | ocbwb in main (8c02385a); DCInvalidateRange is not in the frame path |
| TRAPA | 0 | 0 | - |
| Misaligned accesses (align logger) | 0 | 0 | - |

Top operand-cache miss pcs (combat):
- re4dc::vp::transform_sched<3> 8c015828: about 3,400 per frame
- memset (L_store_long_loop): about 2,400
- native UI load() 8c071fec: about 1,900
- re4dc_avk_pos_skin_u16 8c026016: about 1,050

## Ruled out

- **FPSCR / denormals.**
  - KOS startup.S sets FPSCR to 0x00040000 (DN=1), and new threads copy the current FPSCR when they are created
    (arch_irq_create_context).
  - Arithmetic always runs with DN=1. FPSCR values seen: 00040001 and 00040000, plus SZ/FR/PR variants from fmov pair
    moves and the KOS context save.
  - Zero denormal inputs in combat.
  - With DN=0 an SH-4 raises an FPU error for a denormal input, which would crash rather than slow down.
- **Misaligned accesses:** 0 in a combat window with the align logger.
- **Traps:** 0 TRAPA. No FPU exception is possible without denormal inputs, and address errors would be fatal.
- **Cache maintenance in combat:** no ocbp per frame. ocbi is 45-70 per frame (cdrom stream). ocbwb is about 1,200
  lines (38 KB) per frame in main.

## Suspects, ranked by possible size (MODELLED estimates)

1. **Cache-miss latency charged too low.**
   - The hw projection charges a fill 12-20 cycles (low) to 16-26 (high). For example, hwmodel-sup-mp-r101b-on
     works out to about 9 effective cycles per D-fill.
   - Each frame has about 130,000 D-fills, 22,000 prefetch fills, 49,000 write-backs and (from the hw projection)
     about 145,000 I-cache fills.
   - Every 10 cycles of real latency above the model adds about 3.5 M cycles, roughly 17 ms per frame at 200 MHz.
   - It grows with combat: about 25 % more D-misses than the away view.
   - This is the only suspect big enough to explain tens of ms.
   - Console meter row: SH-4 PMC counter 2 (counter 1 may be KOS's ns timer) cycling once a second through
     0x25 (pipeline freeze by D-cache miss, cycles), 0x24 (freeze by I-cache miss, cycles), 0x04 / 0x05 (OC read /
     write misses) and 0x08 (IC misses), reported per frame. Real cycles per miss = freeze cycles / misses, to compare
     with the model's per-fill charge.
2. **TA input back-pressure on the store queues.**
   - 25,700 SQ flushes (820 KB) per frame in combat versus 18,700 away.
   - The model charges 10-24 cycles a flush (1.3-3.1 ms). If the TA FIFO fills, the CPU stalls inside
     transform_sched / walk_lean.
   - Meter: TMU time of the per-frame submit section (walk_lean / transform_sched callers) against its instruction
     count. PMC 0x28 (freeze by CPU register) does not cover SQ stalls, so time it directly.
3. **G2 bus.**
   - AICA RAM writes of 200-400 per frame, plus g2_fifo_wait polls, cost about 0.05-0.1 ms.
   - Sound uploads reach 11,500 writes per frame in the alert window, which could be 1-2 ms or more for a few frames.
   - Meter: time g2_write_block_32 (µs per frame).
4. **pvr_set_presort_mode every frame.** 600 VRAM word writes over the PVR bus while the PVR renders, about
   0.05-0.3 ms. A cheap fix: call it only when the mode changes.
5. **Small items (under 0.1 ms each):**
   - uncached memset of about 980 words a frame
   - about 3,000 double-precision ops in re4dc_model_packet_reserve, which looks like an accidental `double`
   - about 1,000 P4 timer reads

The hw projection for r101 (hwmodel-sup-mp-r101b-on, 10-03 build) already came to 89.5 ms per frame [77.6-106]. That
is about the console's combat rate, so the per-Ganado figure should be checked against the whole-frame projection of
the current build before blaming hardware-only costs.

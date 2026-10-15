# Lane sh4zam-adopt (2026-10-15): SH4ZAM for skinning, memory and logic (HANDED OVER 10-15 evening)

Branch lane/sh4zam-adopt, base t14/rc e2048df6 + the kos-ports switch (622c28cb) and the v0.9.1 bump (6b51cae0).
Worktree /root/probe/lanes-20261015/sh4zam/adopt. SH4ZAM comes from the shared kos-ports install (33fa4850, v0.9.1).
Evidence: C:\Flycast-Evidence\re4-dreamcast\sh4zam-skin-20261015 (scripts in _tools; hw-model scripts in
/root/probe/lanes-20261015/sh4zam/scr: hwq14.sh, zhwc14.sh, cmp.py). Phase 1 (render-only direct mapping, adopted for
test 14) is docs/lanes/sh4zam-direct.md. Findings for the SH4ZAM author: docs/lanes/sh4zam-upstream.md.

Labels: MODELLED = SH-4 hw model, hw ms per drawn frame, 10 traced frames, r101 cross (frames 500-799) or house siege
(1700-1999). The store-miss term is being refitted against the console Bench A/B, so every MODELLED number here is
"model, unconfirmed". FLYCAST = emulator runs. There are no CONSOLE numbers.

## Knobs (all default 0; knob-off kP image c1ae83dd = test 13 / t14rckP, identical on the rebased branch)

| knob | what | state |
|---|---|---|
| SKIN_SH4ZAM=1, SKIN_SH4ZAM_BOOT=mask | actor skinning on the SH4ZAM XMTRX API, run-time mask re4dc_skin_sh4zam_set: 0x1 bones+groups, 0x2 skin table, 0x4 light dirs, 0x8 C vertex pass, 0x10 run matrix in XMTRX, 0x20 GC weight palette, 0x40 cache lines | **closed: our asm stays (boot mask 0)**. No bit beats it. |
| GAME_SHZ_MEMSET=1 | memset >= 64 B through shz_memset8 (link wrap, build time) | open: keep or close by console. See below. |
| GAME_SHZ_MEM=1, SHZ_MEM_BOOT=mask | global wraps memset / memcpy / memmove to kos-ports shz_memset8 / shz_memcpy / shz_memmove; run-time mask re4dc_shz_mem_set: 0x1 memset, 0x2 memcpy, 0x4 memmove. Main-RAM ranges only. | the switch for the user's "use shz_memcpy" rule (coordinator 10-15: the wrap is the switch, call sites not converted). Default off: a measured loss. |
| GAME_SH4ZAM_LOGIC=1 | gameplay-maths arm: XMTRX load-once at logic sites (include/re4dc_xm.h) + global rebinding (Inverse / MultVec kept on mtx_sh4.S) | **closed: under 0.4 ms** |
| tools/d367/sh4zam/memcpy_lint.sh | raw memcpy / memmove calls in game and port code against a baseline (587 calls in 153 files) | report only (exit 0 unless MEMCPY_LINT_STRICT=1) |

GAME_SHZ_MEMSET and GAME_SHZ_MEM refuse to build together, and GAME_SHZ_MEM refuses MEM_MOVCA / MEMPROF (all wrap
memset).

## Main-RAM-only copy rule (GAME_SHZ_MEM, 3870142e)
Only calls whose ranges lie in main RAM (any P0-P3 mirror of 0x0C000000-0x0CFFFFFF) take the SH4ZAM paths; overlapping
memcpy (undefined behaviour, but newlib's forward copy gives a fixed result) stays on newlib. Why: the first house
hw-model runs with memcpy on (masks 0x6 and 0x7, before the guard) left the game in texture / movie loading
(hwmodel-m6h / m7h: UI image load, OSCheckHeap, movie_window_release on top; 1154 s instead of ~290 s). SH4ZAM's copies
use FMOV.D (8-byte) stores and movca.l, which the G2 bus (AICA sound RAM: 32-bit accesses only), the TA FIFO and other
non-RAM areas do not take. **Open: the house re-measure with the guard (zf7rW, hwmodel-f7h) also ran past the
control's time (10.5 min against ~6) and was stopped at the handover, so the guard is not proven to fix it.** Re-run:
`bash /root/probe/lanes-20261015/sh4zam/scr/hwq14.sh L zf7rW:f7h:h zf7rW:f7c:c` (delete hwmodel-f7h first), then
compare with `python3 cmp.py f0h f7h` / `f0c f7c` in scr/. If it is still stuck, run a plain Flycast house run of
zf7rW against zf0rW and diff the event lines, then narrow by mask (0x2 alone, 0x4 alone).

## Results

### Skinning (SKIN_SH4ZAM; same image, boot mask only; MODELLED, r101 cross; corrected = x1.25 actor draw)
| mask | delta | corrected | main function rows |
|---|---|---|---|
| 0x1 | +0.53 | +0.66 | groups 0.214 -> 0.388, bones 0.116 -> 0.183 |
| 0x2 | +0.21 | +0.26 | skin table 0.139 -> 0.297 |
| 0x4 | -0.04 | -0.05 | light dirs 0.209 -> 0.163 (the one SH4ZAM win; whole frame inside noise) |
| 0x8 | +2.73 | +3.41 | vertex pass 2.247 -> 4.841 |
| 0x18 | +3.22 | +4.03 | |
| 0x40 | +0.34 | +0.43 | |
| 0x67 | +0.77 (house +1.63) | +0.96 | |
| 0x7f | +3.79 | +4.74 | |

### GAME_SHZ_MEMSET (memset only)
- MODELLED, matched layout (control = mask-0 arm + IMAGE_PAD_BYTES=512, _end 64 B off): cross -0.65, house -0.55.
  The function rows say the routine itself is not faster: shz_memset8 0.801 against L_store_long_loop 0.837, and the
  wrapper's head / tail adds about +0.3. The frame gain sits in buckets the change does not touch (logic -0.38). So the
  -0.65 is most likely layout luck. Treat it as unproven until a console A/B.
- STRICT (test 13 data, with SKIN mask 0x04): H2 244 ticks and r101 bell 602 ticks MUST-IDENTICAL (FLYCAST).
- KOS squeeze 48 KiB (t14/rc + GAME_SHZ_MEMSET twin fpszmsqW): PASS 10/10. Minimum headroom fight 10,496 B (t14final
  11,520), call 40,936, door 17,096, leave100/103 10,696. _end +512 B (8c41d038 -> 8c41d238).
- Verdict: **close unless a console A/B shows a gain**. The function rows tie newlib.

### GAME_SHZ_MEM (global wraps; one image per mask, the same layout)
MODELLED, r101 cross, before the main-RAM guard:
| mask | frame delta | routine rows |
|---|---|---|
| 0x1 memset | +0.14 (house -0.12) | shz_memset8 0.622 + wrapper 0.383 vs newlib 0.628 + 0.233 |
| 0x6 memcpy + memmove | +0.15 | shz_memcpy (inlined in __wrap_memcpy) 0.872, 134.7k insn vs L_al4both 0.332 + memcpy 0.091, 62.8k insn |
| 0x7 | +0.34 | |
House 0x6 / 0x7: invalid (the hang above). The "copies" bucket falls (-0.50 / -0.42 / -0.92) only because the inlined
bodies are counted under their callers.
- STRICT (pre-guard build, t14 data, stop 600, mask 7 vs mask 0, FLYCAST): fight, bell, door103 602 ticks, H2 244 ticks:
  all MUST-IDENTICAL.
- Not done: KOS squeeze, align logger, GDEMU race gate, the guarded house re-measure.

### GAME_SH4ZAM_LOGIC
- MODELLED at matched layout (lprW = logic arm + IMAGE_PAD_BYTES=448): cross +3.09 with actors +2.03 (actor code is
  unchanged: layout), house +1.22. Unmatched (lhrW): +0.18 / -0.68. The game-logic bucket ranges from -0.29 to
  +0.19: under 0.4 ms, so it is closed.
- Gameplay equivalence (FLYCAST, 60 s, control zcrW vs zlrW): bell (frame 485, kills 0, alive 6), cap (the same kills
  and releases; one kill position 1 unit off), H2, door103, call: the same events. The final arm (zmrW: Inverse /
  MultVec on mtx_sh4.S): call and door103 the same; the cap run is a truncated prefix match; bell and H2 not run (C:
  staging floor).

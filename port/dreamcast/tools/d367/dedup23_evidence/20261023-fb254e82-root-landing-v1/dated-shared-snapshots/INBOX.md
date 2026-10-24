# dedup-offline23 INBOX

## I-001 (2026-10-23, user approved): re-strip the world offline — start after the dedup QA pair is packaged

**Why:** world strips average only 4.4-4.7 corners (SCENERY-WASTE-20261019.md: r101 cross 3,479 strips for 9,308 triangles, 16,267 corners sent to the TA). These short strips are likely the PS2 VU packet cuts carried over by our converter. Each strip pays 2 extra corners plus per-strip walk cost. If strips doubled in length, corners sent would drop by roughly a quarter to a third. That means less SQ/TA traffic, a smaller TA vertex buffer (the r10d overflow), and less strip-walk CPU. Console showed the game is very data-cache sensitive: halving the D-cache cost +8.2 ms at R101.

**Do:**
1. **Offline estimate first, no game changes.**
   - Re-stripify each meshlet's triangles across the old PS2 packet boundaries, within the existing meshlet vertex limit, the strip-group ranges and the 7-bit/8-bit index limits.
   - Do it on top of your dedup ordering, so both compose.
   - Report for r101, r103 and r100 at the benchmark cameras: strips, corners sent, average strip length, and data bytes before and after.
   - Same triangles and same winding, so the picture is exact.
2. **GO if corners sent drop by ≥15%** at the r101 cross with no data growth that hurts r100 s30. Then build it as a data option in the world build (e.g. `--restrip`), plus a runtime knob only if the format changes. Default off, and knob-off identical.
3. **Gates:** pixel-identical look views (as for dedup), KOS 48 KiB, census, GDEMU seed, h2 s30 heap. Then a console QA pair Off/On, staged as `C:\Game Dev\Emulators\RE4DC-QA23-Restrip-{Off,On}-<sha8>` with a README (R101 cross + R10D merchant hut, QA overlay fps x10).

**Note:** t15/int is now eb1fe953 or newer. The cloud agent's world changes (SELECT_ONLY, SUBMIT_BATCH, REPLAY_LEAN; all default 0) are merged; keep the restrip composable with them. The Claude lane fix-r10d-speed23 is re-cutting r10d's big slab clusters and adding LOD for that room only; coordinate through STATUS "Shared-file changes" if you both touch the world build tools.

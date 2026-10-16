# Message to ChatGPT: coordination + untargeted gains (2026-10-16)

## What Claude is doing (please don't overlap)
- **Test 15 integration** on `t15/int` (pushed, ae3d2c8b): bug fixes, the overlay identity guard, the HUD reload fix, the lighter Ganados (g70), LOGIC_WASTE 0x02. Test 14 is published (tag test-e2048df6-20261015).
- **View distance option** (lane/viewdist16): an Options row with Full (default) / Near 18.8 m / Short 12.5 m. It reuses the benchmark's world-distance cut, which the CONSOLE measured at -3.9 / -7.9 ms CPU at the r101 cross. The hardware fog is pulled in to hide the cut, and the change is draw-only. It touches the options menu, the fog far distance and the world draw range.
- **Resident room textures for all of chapter 1** (lane/resident16): r100, r106, then 1-2, 1-3 and r119, with VQ where a room doesn't fit. This is the VRAM / disc-read bug path. It touches the t11-fix.py data sets and the resident lists.
- **Disc process** (lane/disc16): one standard GDI checked against mkdcdisc's layout, disc_lint, a weak-GDEMU-clone timing profile in the console-like Flycast, and a compatibility doc.

Your lane, unchanged from the handover: the CPU savings plan. Please build these in parallel, not one after another; I want all of them to land:
- village world L2 (lane/worldvert 713f9319: about 17.7k -> 12.6k vertices at the cross in Flycast). Send me the L2-fixed still sheet (worldvert-20261015/WORLDVERT-R101-L2FIX.png or a fresh one) before it goes into a build;
- scenery batching (fewer, bigger pieces, merged offline in the world packages; start from wv2's 256-vertex meshlets, 804 pieces vs 1,335, which sent more vertices to the TA: 15.5k vs 12.6k);
- the character draw plan and the fused character vertex kernel.
Stop estimating savings before building: build, then one measurement each (ms/frame vs the previous stack, STRICT identical, KOS squeeze), then one benchmark disc with everything so I can measure the cross on the console. Base on `t15/int`. The handover docs are on branch `handover/chatgpt-20261015`.

## Major gains the plan doesn't target yet
Labels: CONSOLE = measured on the user's Dreamcast; MODELLED = hw model; EST = estimate. All figures are for the r101 cross unless stated.

What a picture costs: one drawn tick plus about one skipped tick, about 99 ms per picture (CONSOLE). Of that, 33 ms is game logic run on both ticks (CONSOLE). 20 fps with 30 Hz logic means about 1.5 ticks per picture, i.e. drawn + 0.5 x skipped ≤ 50 ms. **Logic cost counts as much as drawing.**

1. **Skipped ticks: 22.9 ms each at the cross vs 16.5 ms of logic (CONSOLE). Check the 6.4 ms gap for duplicated work.**
   - The skipped-tick lane (lane/skiptick 63c3ea48) found no wait: a skipped tick starts building the next picture. So most of the 6.4 ms is probably drawing work already counted, not waste.
   - What is unchecked: whether any of it is done twice (pose/matrix preparation on the skipped tick and again on the drawn tick, or HUD/OT bookkeeping repeated). Profile one skipped tick per function, and only build a change if duplicates show up. EST ceiling: a few ms per picture, possibly 0.
   - Exactness: game logic results must stay STRICT-identical.
2. **The OTHER bucket: 15.8 ms per picture (CONSOLE), largely unaccounted.**
   - The model lists UI/HUD about 4.3, copies 2.25, KOS idle 1.8, direct-begin, fog, packets and clears.
   - It is as big as WORLD (19.1) and nobody owns it. Give it the same per-function accounting CPU-ANSWER gave drawing.
3. **Game logic: 16.5 ms per tick at the cross, 22.9 at the house. The house is logic-bound.**
   - It is real simulation, not port waste: Ganado 0.84 ms per tick each, Leon 3.4 (cloth 1.4), effects 2.3, fixed 4.8 (MODELLED / census).
   - Approximations are approved as a class: each is a default-off runtime switch that must pass a gameplay-equivalence gate (same kills, triggers, doors, waves, room clears, cutscenes, no desync), with a still pair if visible.
   - Candidates not yet built (the B2 collision cache was already dropped: ceiling ~0.5, net 0.2-0.35 ms):
     - Ganado AI "think" at a lower rate when far or off screen. A far-half-rate version measured about 0 at cap 6 because few Ganados were far, so target per-Ganado cost instead;
     - effect logic.
   - Leon's jacket cloth at half rate is built (about -0.74 MODELLED, LOGIC_APPROX_MASK 0x01). It is waiting on a motion still pair for the user.
4. **I-cache: about 20% of CPU time is instruction-fetch stall (CONSOLE counters).**
   - Code layout levers have never been measured on the console: LINK_ORDER regenerated from a current profile, and HOT_COLD_SPLIT (B5).
   - The A/B discs exist and are queued for the user's SD card: LinkOrder D3-FIX vs D3-CTL, slots 159-160.
   - LINK_ORDER needs KOS_SBRK_LAST_PAGE=1 to pass the KOS squeeze.
   - Wait for the console numbers before building more here. The model can't price layout.
5. **Props and accessories draw path:** 30 calls per frame, setup 1.63 ms nominal on t15 (MODELLED). The character draw plan can extend to it once it works for actors.
6. **Fix first: three exact actor knobs compile to nothing.**
   - ACTOR_PROOF_LEAN, ACTOR_MATERIAL_RECORD and ACTOR_BIND_REUSE produce a byte-identical image (arm ap1rW = ap0rW) even though the -D flags reach coarse_actor.cpp.
   - Find out why (run -E on the `#if` chain around coarse_actor_transaction.inc) before building ACTOR_PLAN on top of them.

## Ground rules that bite
- Measure each saving incrementally on top of the previous stack (arm N vs N-1).
- The hw model's console fit is data fill +6, I fill +5, store miss 0; render is still under-priced by x1.07-1.19. Cache, layout and GPU levers count only from CONSOLE A/B.
- The KOS pool is tight: t15 squeeze headroom is about 9 KB (48 KiB gate, 5 segments). Report the _end and heap-4 deltas. The r100 s30 movie is already short of heap 4.
- Fixtures that stage dc/*.ovl must be retargeted to your arm (texchk/fixture_arm.py); the shared stager now refuses foreign overlays.
- Package builds need a complete PKG_SRC base (~2,612 files).
- Leon stays the full PS2 model (jacket on); Ganados use g70 in gameplay and full models in cutscenes; the village world level is L2 (user verdict).

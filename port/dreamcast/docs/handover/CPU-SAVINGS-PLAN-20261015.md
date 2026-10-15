# RE4 Dreamcast CPU savings plan (adopted by the user 2026-10-15 evening)

Basis: CPU-ANSWER-20261015.md. The vertex maths is fast (35-38 cycles a vertex). The cost is the path that feeds it:
per-piece fixed fees, layered bookkeeping, and 2-3 memory passes per vertex. Keep the fast maths and rebuild the feed
path: rendering decisions move into prepared Dreamcast data, leaving a small runtime loop that walks compact arrays.
Character LOD and lower animation update rates come after this work.

## Delivery order

| # | Step | Game area | Work it cuts | In plain words | Owner lane | Expected (provisional) |
|---|---|---|---|---|---|---|
| 1 | Village scenery reduction at the chosen level (L2, "salvaged": wall slivers fixed) | r101, then the worst rooms | World vertices in view | Fewer scenery points, same look up close | worldvert | -3.9 ms (18.8 m cut) to -7.9 ms (12.5 m cut), CONSOLE-measured range; L2 priced on its own |
| 2 | Character draw plan: stable parts, materials and bindings prepared at asset load; shared character state updated once per rendered tick. One plan can still emit several hardware draws when materials need it | Leon, Ganados (then props) | Per-frame and per-chunk re-proof, binds, material validation | Work out each character once, then replay it | actorplan | -1.5 to -2.5 ms realistic (ceiling -2.9 to -3.4), MODELLED. Gate: build the large version only if its estimate is at least 2 ms |
| 3 | Fused character vertex processing: transform, light and pack together; drop intermediate passes; keep small scratch buffers where shared vertices or clipping need them | All skinned characters | Memory round trips per vertex | Each point is placed, lit and sent in one go | actorplan (after step 2 is gated) | -1.0 to -1.3 ms ceiling, MODELLED |
| 4 | Batch the selected scenery: merge compatible pieces within spatial cells; check that the setup saved outweighs the extra geometry submitted | Every room with a converted world | The per-meshlet fixed fee (~3.4k cycles x ~616 a picture) | Fewer, bigger scenery pieces | worldvert (same converter pass) | -2 to -4 ms, estimate |

Provisional target: 74 -> 55-62 ms per drawn tick at the r101 cross. The ~10 ms lean renderer is a longer-term hypothesis.

## Measurement rules
- Measure each saving incrementally on top of the previous stack (arm N vs arm N-1, same scene and window), never each
  against the same baseline, to avoid double counting.
- Label every figure MODELLED (hwproject, refit console column) or CONSOLE. Cache, layout and GPU effects count only from
  console A/B results.
- Lean runs: each Flycast check 1 minute or less, gates run in parallel.
- Exact items: STRICT fight/bell/door103 MUST-IDENTICAL, knob-off identity, KOS squeeze (5 segments), align 0, plus the
  _end and heap-4 deltas. Visible items need still pairs, and the user judges the look.

## Acceptance
- Step 1: the user's look verdict on the L2-fixed sheet; gates pass; a priced ms.
- Steps 2-3: identical gameplay (STRICT); the measured incremental ms; normal-conversion stills if used.
- Step 4: net ms positive after the extra TA geometry; no cracks or seams in the stills.

## Not in this budget
- The jacket cloth half-rate (look review pending, separate).
- GANADO_LOD g70 stays in test 15 as gated.

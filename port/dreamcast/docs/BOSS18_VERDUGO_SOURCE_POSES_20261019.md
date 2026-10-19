# Verdugo full source pose checks — 2026-10-19 (H-040)

The unchanged full body and separate tail have been checked on **40 poses from eight original GC clips**, using the existing recovered-game host motion helper. All 201 body joints remain present, and the 70 render slots resolve to the exact original source joint IDs. The tail retains all 20 parts. No model, candidate, converter, runtime, recipe, guard or Flycast run was changed.

## Original source selection

Original em2c.drs SHA256 remains `d98465b2da842e0b8b74a8e3609977f69d2b012aaa614502cfed6442217aa9b2`. Body BIN5 and tail **decimal BIN134, hex0x86** match the original modelInit calls. The first intake misread the unprefixed source literal as 0x134; the archive bounds check refused it. That failed attempt is preserved and corrected from source, without fallback or a guard change.

| Form | Original FCV arc | Source use | Last frame | Poses |
|---|---|---|---:|---:|
| Body, 201 source joints | 7 | Idle | 70 | 5 |
| Body | 25 | Attack wind-up | 110 | 5 |
| Body | 34 | Frozen turn | 79 | 5 |
| Body | 79 | Move to ceiling | 29 | 5 |
| Body | 90 | Standing death | 180 | 5 |
| Tail, 20 joints | 87 | Ceiling tail sequence | 80 | 5 |
| Tail | 8C | Floor tail sequence | 80 | 5 |
| Tail | 8E | Hidden tail sequence | 20 | 5 |

Arcs in this table are hexadecimal. Every FCV parses and serializes byte-exact. Samples include frame 0, fractional frame 0.5, quarter-plus-0.25, midpoint and last frame. The helper executes original MotionSetCore/MotionMove, IK and blend-table code, retaining every source joint matrix.

A proposed tail FCV8A correctly refused because it targets part21 outside the 20-part tail. Original routine tracing shows 8A belongs to the body HideAtk2 path; separate-tail routines at em2c.cpp3949..4139 select 87/8C/8E. The rejected candidate and source correction remain in the private receipt. No joint expansion or decoder bypass was used.

## Unchanged full data and numeric result

Twenty original full-data input hashes recheck exactly, covering both models' source/bindings/validation/mesh, native arrays/report and runtime headers. Full body header is `6b768b2c339fb38ac121b2fc7f340c97c1af1948aa66967b7e110c1f76b47f5a`; tail is `15fc6e67903d89ee5edbca7ffc4de34ccc67518f0d9585496086aebe3c2baecc`. No candidate data was rebuilt or retested.

The check pairs every original nondegenerate PS2 oriented corner with the retained full native arrays through the original GX references. Body has 12,346 triangles / 37,038 corners; tail has 3,002 / 9,006. The body's four original zero-area triangles remain the existing draw-nothing omissions. All original parent tables are retained. Every native body weight slot maps to its exact original source ID, and all 201 body matrices remain finite in each pose.

| Measurement | Full body | Full tail |
|---|---:|---:|
| Source poses | 25 | 15 |
| Corner-pose checks | 925950 | 135090 |
| Static position error | 0 mm | 0 mm |
| Maximum posed position difference | 0.000211813697 mm | 0 mm |
| Maximum posed normal-vector error | 0.000062728453 | 0.000065894286 |
| Maximum native weight difference | 0.000000089406967 | 0 |

Body weight values differ at 874 repeated corners, while original bone IDs remain exact. These existing native float differences are measured in the posed result; they are not called bit-exact, normalized away or repaired with a new tolerance. Tail weights and posed positions are exact in this sampled calculation. This is numeric array/palette evaluation, not a measurement of target float execution, appearance or speed.

## Limits and owner handoff

Playback uses the existing plain host float helper at a fixed root. It excludes source world/ceiling root transitions, live transition blending, procedural cloth and neck updates, floor contacts, source ice/material/lighting and the coupled player callbacks. A frozen-turn clip checks skeletal packing; it does not implement the active ice material.

H-027's P2 requirements remain: original OT5/pass ownership, full selection throughout actual custom-damage interactions and active Ctrl12 ice. Source parts, cloth, hit/collision, attachments, events and game state remain unchanged. Actual native all-live/all-drawn, source animated look, grabs/death, full fight cost, VRAM/residency, 48 KiB KOS, STRICT/decisions, route and off-image acceptance remain open. This source-only check neither selects the protected candidate nor requests a new level or still sheet under I-013.

Private `boss18-verdugo-source-poses-20261019`: 75 files / 14335946 bytes, SHA256SUMS `ba110d3bc02da105a470785ade39da0b5d0f9d6572fbf4c69325ecc584e5c7d8`. Immediate C mirror byte-verified. Original full data, source clips/poses, source/helper snapshots, guards and rejected intake attempts remain; owned compiler objects/library were pruned with a hash manifest.

Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/verdugo-source-poses-20261019/`. Public hash-only reference: `tools/d367/boss18/verdugo-source-poses-20261019.json`. Original assets, motion clips, generated header/data and media remain private.

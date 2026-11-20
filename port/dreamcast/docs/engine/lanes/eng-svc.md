# Lane eng-svc (native skeleton and collision services, PC-only), 2026-11-19

**Goal:** engine versions of the two services that dominate the Services row (skeleton and pose, collision queries),
laid out for the Dreamcast's caches, proven on the PC to give the original units' results.
Full write-up: [../SERVICES.md](../SERVICES.md).

## Result

- **Skeleton** (`engine/services/skeleton`): per-actor bone tables (world record 64 B, local matrix 48 B, palette
  64 B, pose and history rows), one world pass in chain order through SH4ZAM's XMTRX (`skel_xm`, SH4ZAM style),
  motion sampling into the tables, blends, hokan, the blend table and the leg IK on them, the palette once a tick.
  Leon 49 KB (cParts records: 56 KB), a Ganado 15.5 KB, Ashley 58 KB.
- **What behaviour reads** (census of every guest-memory access, five fixtures): bones only through `getPartsPtr`,
  one parent through `pParent`, and every bone in `at_pos_calc` (replaced). Served by a mailbox: 13 to 22 of Leon's
  119 records, 5 to 21 of a Ganado's 34, 18 of Ashley's 141; everything else in the records is never written (NaN in
  the check build).
- **Collision** (`engine/services/collision`): the room's SAT and EAT baked at room load into a flattened block tree
  (SoA box rows, skip links) and one 96-byte record per polygon; the three query cores (`hitCheck2`, `hitCheck`,
  `polySphereCk`) run on them in the original's walk order. Village square: 370 KB.
- **Equivalence (PC):** six fixtures (door103 walk, E1 route, bell Ganados, a hit, Ashley on the r11d hill, Ashley
  following): bones equal as numbers on every tick (bit-identical but for zero signs), collision queries and traces
  bit-identical; native against native bit for bit. Controls (parent off by one, floors +1 unit, IK skipped) fail.
- **Cost (PC counts, no timing):** SERVICES.md section 6.

## Evidence

`E:\RE4DC-Lanes\eng-svc\ev`: `controls\` (svc_controls.md and per-fixture compare.json), `cost\` (cost tables,
census summaries), `fields_table.md`, `sizes\` (table and piece sizes). Scripts: `E:\RE4DC-Lanes\eng-svc\s`.

## Not done

See SERVICES.md section 9: offline key conversion, actor volumes and capsules native, the pendulum cloth under the
check build, a farm Ganado fixture, timing (emulator lane).

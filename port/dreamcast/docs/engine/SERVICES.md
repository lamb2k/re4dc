# Native skeleton, collision and cloth services (lanes eng-svc, eng-svc2 and eng-svc3, 2026-11-19)

The services that dominate the budget's Services row, as engine code on engine tables, proven on the PC to give
the original units' results. Tier of every number here: **PC** (re4ref, the host build of the original code). No
console, no Flycast, no MODELLED number; no timing claim.

**Round 2 (lane eng-svc2), sections 10 to 15:** offline motion keys (no key search, history or decoding in a tick),
the bone history kept for the bones code reads (not every bone), a native cloth service (Leon's hair and jacket,
Ashley's hair, skirt and sweater) on engine generator random numbers, and a cell grid that cuts the polygons a line
query tests by 44 to 68%. Sections 1 to 9 are round 1 as it was handed back; where round 2 changed them, section 15
says so.

**Round 3 (lane eng-svc3), sections 16 to 22:** the motion keys' memory (16-bit rows for a per-room clip set from
captured play, the keys resident: recommended), root motion and the key decoder native (the original decoder out of
the skeleton service), the cloth's tick as one SH4ZAM kernel with its passes fused (a true single pass measured and
rejected), the swept sphere on the collision grid and the masks smaller. Section 21 lists what the engine image must
change, section 22 the interface changes.

- **Skeleton:** `port/dreamcast/engine/services/skeleton/` (`skel.h`, `skel.cpp`, `skel_xm.h/.c`).
- **Collision:** `port/dreamcast/engine/services/collision/` (`col.h`, `col.cpp`).
- **The re4ref switch and the tools:** `port/dreamcast/engine/hostref/svc/` (`svc.mk` and the files it names).
- **Result:** on six fixtures (Leon's door103 walk, the E1 route, the bell Ganados, a hit on a Ganado, Ashley on the
  r11d hill, Ashley following Leon), every bone of every actor on every tick and every collision query are the
  original's: bones equal as numbers (bit-identical but for the sign of exact zeros), queries bit-identical, traces
  bit-identical. Three controls (a parent off by one, floors 1 unit higher, the IK pass skipped) fail as they must.
- **Cost (PC counts):** the skeleton makes 30 to 42% fewer memory accesses an actor and touches 12 to 21% fewer
  32-byte lines for Leon and Ashley (about level for a Ganado); it now also writes the skin palette the renderer
  multiplies out today. Collision touches about as many lines as the original (-7% to +10%): its lever is the number
  of polygons a query tests, not their layout (section 6).

## 1. What replaces what

| Original (behaviour still calls it) | Native body | Stays original |
|---|---|---|
| `MotionSetCore`, `MotionMove`, `MotionMoveCore`, `MotionMoveSub`, `MotionHokan`, `MotionClear`, `PartsWorldPosCalc` (motion.cpp) | `skel.cpp` on the actor's `SkelTable` | the key decoder `HermiteInterpolation` and the motion key lease (the data format); the clock and root motion (`MotionSequenceCtrl`, `MotionGetSpeed`, `MotionAddSpeed`, `MotionCheckCrossFrame`: `MotionWork` state behaviour reads) |
| `IKInit`, `InverseKinematics` (ik.cpp, not linked) | `skel.cpp` | the floor query (collision, native) |
| `cModel::partsMatCalc`, `partsWorldCalc`, `matBlend`, `matUpdate`, `setPos`, `updateOldPos`, `partsFixMemory`, `partsFixAdjust`, `setParent` (both), `setPartsOffset`, `releasePartsList`, `getPartsPtr`, `GetPartsAddr` (model.cpp) | `skel.cpp` | model and parts allocation, model info, relocation |
| `at_pos_calc` (atari.cpp: a collision push moves every bone) | `skel.cpp` | |
| `cSatMgr::hitCheck2`, `hitCheck`, `polySphereCk` (atari.cpp) | `col.cpp` on the room's `ColPiece` tables | `check`, `checkAir`, `scrAtCheckSphere(Air)`, `wallAdjust`, `adjust`, `getFloor`, `atck` (per-model logic above the three cores); the actor volumes (`EmAtCheck`, `ObjHitCheck`, `EmHitCheck`, `cAtariInfo`, capsules) |

**The collision entry points** (E1's 21 and the Ganado closure's, `hostref/closure-map*.tsv`):
- *through the native cores:* `cSatMgr::check`, `checkAir`, `getFloor`, `hitCheck` (and `scrAtCheckSphere(Air)`,
  `wallAdjust`, `adjust`, `atck` inside them): floors, walls, the swept sphere, line checks against the scenery;
- *original:* the actor volumes and their tests (`cAtariInfo::init/set/move/setPriority`, `EmAtCheck`, `EmHitCheck`,
  `ObjHitCheck`, `ObaLineHitChk`, `At_em_rect_rect_ck`, `YarareAdd/Init`, `AtSphereCapsuleCk`, `AtBoxCapsuleCk3`,
  `At_box_sphere_ck`, `collision_sphere_hexahedron`), `EatGetEffectType`, and the route checks (`RouteCk*`,
  `getNearPoint`, `AreaGetCenterPos`);
- *stubs in re4ref:* the scenario item tests (`SceAt*`); debug drawing (`DrawOba`); `cubeMemoCk` is not linked.

The re4ref build is the switch: `make native` links the native bodies; `game/ik.o` is left out and `motion.o`,
`model.o`, `atari.o` are linked with the replaced functions made weak (`objcopy --weaken-symbol`, lists in
`svc.mk`), so every call, from any unit, reaches the native body. Nothing switches at run time.

## 2. Skeleton tables

One `SkelTable` per model with parts, one 32-byte aligned block from the service pool (n bones, cap = n rounded up
to 8). The world record is two cache lines; a bone's world pass reads its local matrix and writes its world record.

| Array | Bytes a bone | Content |
|---|---:|---|
| header | 128 (once) | counts, owner, record pointers, mailbox list, IK chain index |
| `world[n]` | 64 | world matrix 3x4, accumulated scale (`r_scale`), motion flags (`MotionParts::flags`) |
| `lmat[n]` | 48 | local matrix |
| `pal[n]` | 64 | skin palette (world x bind), 3x4 + pad, written once a tick for the renderer |
| `prev[n]` | 48 | previous motion's local matrix (hokan) |
| `soa[33][cap]` | 132 | rows: pose pos / ang / scale; blend-saved pose; world position; world_old; world_old2; bind translation; addRot (IK length aliases it, as in the record) |
| `ikAng[cap]`, `hist[n]` | 4 + 36 | IK twist angle; key history (6 channels x 3 axes) |
| `parent`, `mbox`, `mlist`, `handed` [cap], `rec[n]` | 4 + 4 | parent bone (0xFF the model, 0xFE an outside coordinate); mailbox state, list and the bones handed out since the last entry; the cParts record |
| `ik[8]` | 96 a chain | IK plane matrix, axis, direction of each chain root |

| Actor | Bones | Native table | cParts records (472 B a bone) | World pass reads + writes a tick per pass |
|---|---:|---:|---:|---:|
| Leon | 119 | 49,184 B | 56,168 B | 13,328 B (112 B a bone) |
| Ashley | 141 | 58,400 B | 66,552 B | 15,792 B |
| Ganado | 34 | 15,616 B | 16,048 B | 3,808 B |
| Handgun (object) | 4 | 3,200 B | 1,888 B | 448 B |

The check build adds 196 B a bone (what each mailbox record was given, section 4); the sizes above are without it.

**The world pass** (`world_calc`): one pass in chain order. The parent's world matrix is loaded into SH4ZAM's XMTRX,
the bone's local matrix applied, the result stored; when the next bone is the child of the one just computed (a
parent -> child run, the common case) XMTRX already holds its parent and nothing is loaded. A parent with a
non-uniform accumulated scale takes the original's P S^-1 L S form as XMTRX column scales. Counted on the fixtures:
blended poses (Ashley, Leon running and aiming) make `r_scale`'s three components differ by rounding, so most bones
of a blended pose take that form (e1-route: 239,550 of 264,889 bone passes). On the SW back-end XMTRX forms every
element as the C matrix library does (the sums commute exactly), which is why the PC tables carry the original's
bits; on the SH-4, FTRV rounds its own way (section 7).

**The palette** (`skel_publish`, once a tick after the behaviour): world x bind, where bind is the rest translation
negated (`cParts::lt_inv_mat`): XMTRX holds the world matrix and the bind translation goes through it as a point.

## 3. Collision tables

One `ColPiece` per collision piece (`cSat`), baked once at room load (`col_bake_all`) from the room archive's SAT and
EAT files.

| Array | Bytes | Content |
|---|---:|---|
| header | 64 | counts, the piece and its file |
| node rows [nNode] | 20 a node | the block tree flattened in the walk's order: box min x / z, size x / z (f32 rows), skip (the node after this one's subtree: where a failed test continues), leaf number |
| leaf [nLeaf] | 8 | first list entry, floors + slopes count, walls count |
| idx [nIdx] | 2 | the leaves' polygon lists, leaf after leaf |
| hot [nPoly] | 32 | one line per polygon: first vertex, face normal, attribute word, normal index. Every polygon test starts with a plane test on these |
| cold [nPoly] | 64 | the other two vertices and the three edge vectors: read only by a polygon that passed its plane test |

| Room, piece | Nodes | Leaves | List entries | Polygons | Native tables | The file's tables the original walk reads |
|---|---:|---:|---:|---:|---:|---:|
| Village square (r101), scenery (SAT) | 605 | 454 | 5,325 | 1,198 | 141,536 B | 122,542 B |
| Village square, effect (EAT) | 1,149 | 862 | 11,165 | 1,831 | 228,128 B | 205,778 B |
| Hill path (r11d), scenery | 293 | 220 | 4,142 | 1,150 | 126,464 B | 99,764 B |
| Hill path, effect | 265 | 199 | 3,324 | 949 | 104,864 B | 83,704 B |

A polygon test reads its 32-byte hot line, and the 64-byte cold record only if the plane test passes; the original
reads the polygon (20 B), then a vertex and a normal, then two more vertices and three edges, from five tables. The
walk is the original's (same box tests, same order, same per-query polygon dedupe), so the number of box and polygon
tests is the same; what changes is where the bytes are. A first form with one 96-byte record per polygon touched up to
19% more lines than the original (door103 146 against 123 a tick, hill 951 against 839): most polygons a query visits
end at the plane test, and the original's shared vertex and edge tables are denser than three lines a polygon. The
file stays resident: the hit report's normal pointer (`pFloor_norm`, `hitCheck2`'s `attr`) points into its normal table.

## 4. Fields behaviour reads, and how they are served

**How this was found.** `make census` builds the reference with every call across the service boundary counted
(`--wrap` trampolines with a shadow stack: `svc/gen_wraps.py`) and, with `RE4_SVC_TRACE=1`, every load and store the
tick makes to guest memory traced (the arena is PROT_NONE during the tick; each fault is recorded and the
instruction single-stepped: `svc/svc_trace.cpp`). `svc/census.py` names the instructions; `svc/fields_table.py`
keeps the accesses to cParts records by code outside the skeleton units. Five reference runs (door103 ticks 1-40,
e1-route 40-600, bell 2-121, hill 2-121, follow 2-200):

| Field | R/W | Accesses a tick (most) | Bones | Code | Fixtures |
|---|---|---:|---:|---|---|
| addRot, flags | W | 46.0, 16.0 | 3 | `cPlBody::waistMove`, `cSubChar::neckCtrl`, `em10NeckMove`, `em10WaistMove` | all |
| ang | W | 6.0 | 3 | `cPlayer::moveEyeNormal`, `cSubChar::moveFace` | all |
| mat | R | 247.7 | 64 | `at_pos_calc` (every bone), `cObjWep::getMarkerPos`, `cSubChar::moveBust`, `cameraHitCheck`, `em10NeckMove` | route, bell, hill, follow |
| mat | W | 136.2 | 64 | `at_pos_calc` (every bone), `cSubChar::moveBust` | route, bell, hill, follow |
| pList | R | 41.4 | 64 | `at_pos_calc` | route, bell, follow |
| pParent | R | 1.0 | 1 | `cSubChar::moveBust` | hill, follow |
| pos | W | 9.0 | 3 | `cSubChar::moveBust` | hill, follow |
| world | R | 167.7 | 64 | `at_pos_calc` (every bone), `CameraControl::Check`, `cAtariInfo::getPos`, `getSpeedVector`, `cSatMgr::hitCheck2` (a point passed in), `moveBust`, `pantsCheck`, `em10NeckMove` | all |
| world | W | 127.1 | 64 | `at_pos_calc` (every bone), `moveBust` | route, bell, hill, follow |
| world_old | R | 18.0 | 1 | `cAtariInfo::getSpeedVector` | all |
| world_old2 | R | 3.0 | 1 | `cSubChar::moveBust` | hill, follow |

("Bones" counts bone indices below 63 in the census mask; "every bone" rows are 64 because of that cap.)

The census's own control: `RE4_SVC_CONTROL=plant` makes a behaviour-side unit (`svc/svc_plant.cpp`) read Leon's bone 3
world position straight from its record once a tick; the fields table of that run lists `svc_plant_read` reading
`world` (and `pList`, the walk to it), as it must.

What it shows: outside `at_pos_calc`, the behaviour reaches a bone only through `getPartsPtr` (or `GetPartsAddr`),
and then reads that record or, once (`moveBust`), its parent's through `pParent`. `at_pos_calc` is collision code that
walks every record after a push; it is replaced (it moves the table).

**How they are served: the mailbox.**
- A record becomes its bone's mailbox when code outside asks for it (`getPartsPtr`, `GetPartsAddr`, a
  `setParent` target). After every native entry the record gets the table's values for the field groups that entry
  may have changed (world: mat, world, r_scale, flags; local: l_mat, pos, ang, scale, addRot; history: world_old,
  world_old2). Before the next entry the table takes back the records handed out since the last one: the census
  shows the behaviour writes a bone (eyelid angles, waist addRot, bust positions and matrices) right after asking
  for it.
- Its ancestors (reached through `pParent`) are served the world matrix, world position, `r_scale` and scale only,
  and nothing is taken back.
- A root bone's parent is re-read from its record before every evaluation (`objWep` writes its root's `pParent`
  directly to hang the handgun on Leon's hand).
- Everything else in a record is never written: the check build fills it with NaN at table creation, so a read the
  census missed would turn a trace into NaN. It also remembers what every mailbox record was given and counts any
  later difference the table did not take back (lost writes), and records whose `pParent` disagrees with the table.
  On all six fixtures: **lost writes 0, parent mismatches 0**, traces identical.

| Fixture | Leon (119) | Ganados (34 each) | Ashley (141) | Handgun (4) |
|---|---|---|---|---|
| door103-walk, e1-route | 22 (10 direct + 12 ancestors) | | | 0 / 1 |
| bell-ganado | 13 (9 + 4) | 21 (14 + 7) / 5 / 5 / 5 | | 0 |
| bell-ganado-hit | 13 | 21 / 5 / 19 / 14 | | 0 |
| hill-ashley | 13 | 5 each | 18 (10 + 8) | 0 |
| square-follow | 22 | | 18 | 0 |

(Mailbox bones a table had at the end of the run.)

## 5. Equivalence (PC)

`svc/svc_controls.sh` runs each fixture on the reference with the dump (`make odump`) and on the native build
(`make native`), and compares:
- **bones** (`svc_compare.py`): every live model with parts, every tick, every bone: world matrix, world position,
  palette. Tolerance 1 unit and 0.1 degree (SHELL_MAP section 6); reported: bit-identical and equal-as-numbers counts.
- **collision queries**: every query the behaviour and the IK make (`--wrap` on the entry points, nested queries not
  logged), in call order: kind, inputs, results. Hit, attribute, normal pointer exact; points within 0.01 unit.
- **traces** (`plays_right.py`, tolerances.json): Leon's T lines and every actor's A lines.

| Fixture | Ticks | Bone-ticks | Bit-identical | Equal as numbers | Queries (getFloor / hitCheck / check / EAT hitCheck) | Identical | Traces |
|---|---:|---:|---:|---:|---|---:|---|
| door103-walk (Leon) | 348 | 42,804 | 42,456 | 42,804 | 3,993 (696 / 2,949 / 348 / 0) | 3,993 | PASS, 349 ticks |
| e1-route (Leon walks, runs, aims) | 640 | 78,720 | 78,610 | 78,720 | 7,220 (1,286 / 5,201 / 640 / 93) | 7,220 | PASS, 641 |
| bell-ganado (Leon, 4 Ganados) | 300 | 77,700 | 77,400 | 77,700 | 8,304 (2,723 / 4,216 / 1,211 / 154) | 8,304 | PASS, Leon + 4 actors |
| bell-ganado-hit (a hit at tick 60) | 200 | 51,800 | 51,600 | 51,800 | 5,580 | 5,580 | PASS, Leon + Ganado 0x14 |
| hill-ashley (Leon, Ashley, 4 Ganados) | 600 | 240,000 | 240,000 | 240,000 | 24,250 (8,107 / 11,937 / 3,600 / 606) | 24,250 | PASS, Leon + 5 actors |
| square-follow (Ashley follows) | 240 | 63,360 | 62,880 | 63,360 | 5,153 | 5,153 | PASS, Leon + Ashley |

The values that are not bit-identical are exact zeros of opposite sign (for example Leon's bone 0, element m[2][1]:
+0 in the reference, -0 native): the C library adds a literal +0 where XMTRX adds `a*0`.

| Check (door103-walk and bell-ganado) | Must | Bones and collision | Traces | First divergence |
|---|---|---|---|---|
| native against native (each fixture) | PASS | PASS, bit for bit | PASS | none |
| bone 5's parent one bone too low | FAIL | FAIL | PASS | tick 1, Leon bone 5: 212 units, 14.6 degrees |
| floors 1 unit higher (baked tables) | FAIL | FAIL | FAIL | tick 1, Leon bone 0: 1.0 unit; queries 699 of 3,993 identical |
| IK pass skipped | FAIL | FAIL | PASS | tick 1, Leon bone 6: 1.6 degrees; no IK floor queries |

The parent and IK controls pass the traces: Leon's position, angle and motion do not depend on those bones. That is
why the bones are compared directly.

## 6. Cost indicator (PC counts, no timing)

Both builds traced over the same ticks (`make census` / `make ncensus`, `RE4_SVC_TRACE=1`, check build off): door103
1-40 (Leon idle), e1-route 200-279 (running, turning, aiming), bell 61-90 (Leon, four Ganados), hill 61-90 (Leon,
Ashley, four Ganados), follow 31-70 (Ashley following). Operations are math library calls per tick (the native
chain kernel's calls included); memory is every load and store the service made, and the distinct 32-byte lines (the
SH-4 operand cache line) they touched in that tick, every entry point of the service together. x86 counts, not SH-4
instructions; no timing. Tables per fixture: `E:\RE4DC-Lanes\eng-svc\ev\cost\cost-*.md` (`svc/svc_cost.py`).

**Skeleton, memory per actor per tick** (reference / native)

| Actor, fixture | Accesses | Lines | of which cParts and model records | archives (motion keys) | native tables |
|---|---:|---:|---:|---:|---:|
| Leon idle (door103) | 65,318 / 44,661 | 1,337 / 1,116 | 1,110 / 114 | 206 / 151 | 0 / 829 |
| Leon running and aiming (e1-route) | 89,631 / 51,849 | 1,349 / 1,187 | 1,117 / 166 | 212 / 163 | 0 / 837 |
| Leon (bell) | 65,084 / 44,606 | 1,325 / 1,101 | 1,107 / 118 | 198 / 155 | 0 / 807 |
| Ganado, each of three (bell) | 25,500-26,100 / 16,200-16,500 | 631-671 / 633-665 | 352-357 / 62-116 | 260-295 / 194-219 | 0 / 312-357 |
| Ganado, each of four (hill) | 25,100-26,100 / 15,900-16,500 | 654-692 / 628-664 | 358-360 / 63-64 | 262-300 / 193-221 | 0 / 309-344 |
| Ashley (hill) | 120,117 / 75,210 | 1,926 / 1,528 | 1,569 / 108 | 322 / 278 | 0 / 1,106 |
| Ashley following (follow) | 125,906 / 75,997 | 1,830 / 1,481 | 1,513 / 114 | 296 / 253 | 0 / 1,093 |
| Handgun (door103) | 2,698 / 1,882 | 66 / 69 | 59 / 22 | 7 / 7 | 0 / 40 |
| Palette, every table once a tick (door103 / bell / hill) | 0 / 4,817, 10,165, 17,558 | 0 / 557, 1,201, 1,893 | | | |

- **Accesses fall 30 to 42% an actor; lines touched fall 12 to 21% for Leon and Ashley and stay about level for a
  Ganado** (-6% to +5%; 34 bones: the table's rows are touched nearly whole every tick).
- **The cParts records drop from 1,107-1,569 lines to 62-166** (the mailbox); the native tables are 807-1,106 lines.
- **The palette is new work for the service** (557 lines a tick for Leon and the handgun): the E1 renderer does that
  multiplication today in drawing (actor_e1.inc step 2), so it moves from the Drawing row to the Services row.
- **Where the native lines go** (Leon, 829): world records 238, local matrices 179, key histories 134, pose and
  history rows about 280. Two levers measured, not done: `updateOldPos` copies the world history of every bone each
  tick (9 rows, 135 lines for Leon) while code reads it for 1 to 3 bones; converting the keys offline removes the key
  history (134 lines) and the archive reads (151 lines).

**Skeleton, operations per actor per tick** (reference / native)

| Actor, fixture | Matrix x matrix (C library) | XMTRX apply | XMTRX column scale | XMTRX load | Matrix x vector | Inverse | Quaternion | Trig | Key segments |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Leon idle (door103) | 565.7 / 65.0 | 0 / 362.5 | 0 / 138.3 | 0 / 203.9 | 392.5 / 392.5 | 27.0 / 27.0 | 32.6 / 32.6 | 740 / 740 | 60.2 / 60.2 |
| Leon running and aiming (e1-route) | 1,185.5 / 63.0 | 0 / 398.5 | 0 / 724.0 | 0 / 375.5 | 427.7 / 427.7 | 25.6 / 25.6 | 115.9 / 115.9 | 847 / 847 | 64.0 / 64.0 |
| Ganado (bell, em1) | 308.7 / 28.1 | 0 / 104.8 | 0 / 175.8 | 0 / 91.9 | 124.9 / 124.9 | 10.0 / 10.0 | 14.3 / 14.3 | 216 / 216 | 51.7 / 51.7 |
| Ashley (hill) | 1,352.2 / 54.0 | 0 / 440.4 | 0 / 857.8 | 0 / 429.5 | 469.0 / 469.0 | 22.0 / 22.0 | 430.1 / 430.1 | 1,491 / 1,491 | 103.3 / 103.3 |

- The C matrix products of the world pass become XMTRX applies (one per bone); the non-uniform scale form (blended
  poses) becomes one apply and two column scales instead of three products and two scale matrices.
- Everything else is the same count: same arithmetic, same key decoder, same IK, hokan and blends.

**Collision, all queries of a tick** (reference / native; the scenery and effect queries together)

| Fixture | Accesses | Lines | of which the room's collision files | native tables | Most lines in one tick |
|---|---:|---:|---:|---:|---:|
| door103 | 3,533 / 4,327 | 123 / 135 | 89 / 0 | 0 / 100 | 89 / 100 |
| e1-route | 4,244 / 5,080 | 164 / 180 | 92 / 0 | 0 / 136 | 506 / 459 |
| bell | 12,576 / 13,375 | 622 / 581 | 538 / 0 | 0 / 496 | 1,370 / 1,310 |
| hill | 23,461 / 22,388 | 839 / 787 | 713 / 1 | 0 / 658 | 1,075 / 1,016 |
| follow | 7,614 / 8,939 | 200 / 216 | 124 / 1 | 0 / 161 | 602 / 509 |

- **About level:** lines -7% to +10%, the worst tick 4 to 15% lower in four of five fixtures. The box tests and
  polygon tests are the original's in number (same walk); the original's shared vertex and edge tables are already
  dense.
- **The collision lever is the number of polygons a query tests**, not their layout: 35,399 line-polygon tests for
  4,714 line queries on door103 (7.5 each) and 934,473 for 31,473 on the hill (30 each). Testing fewer with the same
  results needs a finer index that replays the original's visit order (the sphere's pushes are order dependent);
  not done.
- The actor-volume tests (`EmAtCheck`, original code) cost about 20% more accesses natively: each `getPartsPtr` they
  make now does the mailbox's bookkeeping.

## 7. What the engine image must change to use them

1. **Link** (`engine/game/hosted.mk`, `Makefile`): add `services/skeleton/skel.cpp`, `skel_xm.c` and
   `services/collision/col.cpp`; drop `game/ik` from `SVC_ORIG_SRCS`; link `motion`, `model` and `atari` with the
   replaced functions weakened (the `WEAK_*` lists of `hostref/svc/svc.mk`, `sh-elf-objcopy --weaken-symbol`).
2. **Memory:** provide `svc_pool_base` (the skeleton pool; Leon and the handgun need 52 KB, four Ganados and their
   weapons add about 70 KB: 256 KB covers E2) and `svc_pool_carve` (room tables; the village square needs 370 KB)
   from the engine heap (E1's map has 2.2 MB free).
3. **Room load:** call `col_bake_all()` after the SAT and EAT pieces are created (`e1_collision_room_init`).
4. **Once a tick**, after the behaviour and before drawing: `skel_publish_all()`.
5. **Renderer** (`services/actor_e1.inc`): read `skel_table_of(model)->pal[k]` (already world x bind) for bone k + 1
   instead of walking the cParts chain for `cCoord::mat` and multiplying by the pack's bind; check once at load that
   the pack's bind equals the table's bind translation (if not, multiply the table's `world[k]` as today).
6. **Trace:** E1's `pm` digest (every cParts block) reads records the service no longer writes; digest the table.
7. **Release build:** `skel_poison = 0` (no NaN fill, no shadow).
8. **Before switching:** run re4ref with `pendulum.cpp` hosted under the check build. E1 hosts Leon's pendulum cloth
   (`PenClothMove`, 1.45 ms a tick in Flycast); re4ref stubs it, so the mailbox has not seen the cloth's accesses.
9. **SH-4 rounding:** FTRV rounds differently from the PC; the plays-right gate on Flycast decides (bones within
   1 unit / 0.1 degree, collision results exact).

## 8. Tools

| Command | What |
|---|---|
| `make -C port/dreamcast/engine/hostref census` / `ncensus` | the reference / the native build with the call census; `RE4_SVC_TRACE=1` (`_FROM`, `_TO` ticks) adds the memory tracer; tables in `RE4_SVC_OUT` |
| `make ... odump` / `native` | the reference with the per-tick dump / the native build with it |
| `svc/svc_controls.sh <out> [fixture...]` | the equivalence table and the controls (`RE4_TREE` set) |
| `svc/svc_compare.py <ref> <native>` | bones and collision queries, tick by tick |
| `svc/census.py`, `svc/fields_table.py`, `svc/svc_cost.py` | census summaries; the fields table; the cost table |

Controls by environment: `RE4_SVC_CONTROL=parent=<bone>`, `floor=<units>`, `noik` (native build), `plant` (census
builds); `RE4_SVC_POISON=0` turns the check build's poison and shadow off.

Round 2 adds: `bake/motion_keys.py` (the baked keys; `RE4_SVC_MK=<pack>` loads them, `svc_controls.sh` bakes them
when unset), `svc/cloth_stats.py` (the cloth with the wind on), `svc_compare.py --skip-cloth`, `hist.bin`;
`RE4_SVC_CLOTH_WIND=0` (both builds: no cloth wind), `RE4_SVC_COLGRID=0` (the line queries without the grid); the
controls `mkrow`, `histnone`, `histfrozen`, `clothshort`, `clothnograv`, `clothwind`, `colgrid`.

## 9. Limits and what is not done

- **Key sampling is the original decoder.** `HermiteInterpolation` and the port's key lease decode the keys; the
  native part is where samples go (table rows) and the per-bone history. Converting the keys offline to an engine
  format (no history search) is not done.
- **Actor volumes stay original:** `EmAtCheck`, `ObjHitCheck`, `EmHitCheck`, `cAtariInfo`, the sphere and capsule
  tests between characters (at_mod, at_sub). They reach bones through `getPartsPtr` and are served.
- **Cloth:** Leon's pendulum cloth and Ashley's lapel paths are not hosted in re4ref (stubs), so they are not covered
  (section 7, item 8).
- **Fixtures:** six, from the plays-right set plus the E1 route. No farm (em12) Ganado, no carried Ashley, no event
  or door.
- **No timing:** the cost table counts operations and memory; the emulator lane times them.
- **Collision memory:** the native tables are a second copy (370 KB for the village square). After the bake only the
  file's normal table must stay; releasing the rest needs the room archive split.

# Round 2 (lane eng-svc2)

Branch `lane/eng-svc2`. Same fixtures, same tier (PC), no timing. `svc/svc_controls.sh` now bakes the motion keys,
runs every fixture with the cloth's wind on and off, and runs every control; 37 rows, all as they must
(`E:\RE4DC-Lanes\eng-svc2\ev\controls\svc_controls.md`).

## 10. Offline motion keys

**Why.** Round 1 sampled every pose channel with the original decoder: per axis a key search from the bone's key
history, then the Fcc decode of the key pair (nine encodings) and the Hermite blend. A tick read the clip's frame
tables and key data scattered over the archive (206 lines for Leon idle) and the key history (36 B a bone).

**What the fixtures sample** (counted, `svc.txt` "motion samples"): 99.8% of MotionMoveCore calls are at an integer
frame (the sequence clock steps whole frames); 15 of 9,000 calls are fractional (the flinch on the hit fixture).

**The format** (`bake/motion_keys.py` writes it, `services/skeleton/skel_mk.h` reads it; the baked pack is private
data, never committed):
- per clip a **row table**, frame-major: row k holds every pose joint's three values at frame k, the joints in clip
  order, as float32; a row is padded to 8 floats so it starts on a 32-byte line. Joints whose three axes never
  change go to a **const** table once. The last row (frame maxFrame) holds each axis's last key: the original's
  answer for a frame at or past the end of a clip that does not loop (a looping clip wraps first, as the original);
- a **joint table** (8 B a joint: the kind word, parts, source, first column);
- the clip's own key blocks as a **cold** section, for fractional frames.

**Exact.** Each value is the original's arithmetic in float32 (the Fcc decode with its 0.0001f scale, `hermite()`
in its order; a frame on a key takes the key), rotations already through `VecRadLimit` (idempotent on its output).
Fractional frames go through the original decoder on the cold blocks with its history off: the baker checks that
every axis's keys run from 0 to maxFrame strictly rising, and on such keys the search from key 0 finds the same
bracket the history search finds, so the history changes no value. A clip that fails the check is not baked (the
service keeps the original decoder for it): 1 of 415 (no joints). **Binding:** MotionSetCore binds a clip header to
its baked clip once, by identity (FNV-1a of the header and every pose joint's key block, as the baker computed it);
MotionMoveCore then reads one row.

**Sizes** (the archives the fixtures load; em12 and em16 share em15's clips; 414 distinct clips):

| Archive | Clips | Original clips | Rows + const + tables (hot) | Cold key blocks | Frames per clip | Row floats per clip |
|---|---:|---:|---:|---:|---:|---:|
| em/pl00 (Leon) | 65 | 439,520 B | 722,816 B | 403,996 B | 43.9 | 59.5 |
| em/pl0e (Leon) | 41 | 359,040 B | 944,192 B | 318,776 B | 111.4 | 46.8 |
| em/pl0f (Leon) | 26 | 286,752 B | 567,840 B | 278,440 B | 82.1 | 64.3 |
| em/wep02 (handgun) | 42 | 178,784 B | 311,232 B | 166,020 B | 34.7 | 47.1 |
| em/pl11 (Ashley) | 71 | 495,264 B | 883,104 B | 455,760 B | 45.7 | 61.1 |
| em/em15 (+ em12, em16: Ganados) | 169 | 1,971,520 B | 3,442,720 B | 1,859,960 B | 76.9 | 62.5 |
| **All** | **414** | **3,730,880 B** | **6,871,904 B** | **3,482,952 B** | | |

The hot tables are 1.84 times the original clips, and the cold blocks are the original keys again: a memory decision
for the engine image (section 14).

**Equivalence.** Six fixtures: every bone of every actor bit-identical as in round 1 (the same counts), every motion
sample from rows (15 fractional from the cold keys), the original decoder 0. Control `mkrow` (the next frame's row)
fails.

**Counts** (per actor per tick; original / native; the skeleton service, every entry point together):

| Actor, fixture | Key segments (hermite) | Archive lines (keys) | Baked-key lines | Skeleton lines | Skeleton accesses |
|---|---:|---:|---:|---:|---:|
| Leon idle (door103) | 60.2 / 2.9 | 206 / 11 | 0 / 16 | 1,336 / 896 | 65,304 / 43,496 |
| Leon running and aiming (e1-route) | 64.0 / 2.4 | 212 / 12 | 0 / 17 | 1,347 / 959 | 89,611 / 50,617 |
| Leon (bell) | 61.1 / 2.9 | 198 / 12 | 0 / 16 | 1,325 / 882 | 65,084 / 43,450 |
| Ganado, each of three (bell) | 51.7-80.7 / 3.8-6.0 | 260-295 / 8-19 | 0 / 17-21 | 631-671 / 394-445 | 25,500-26,100 / 14,900-15,600 |
| Ganado, each of four (hill) | 80.4-80.5 / 6.0 | 262-300 / 8 | 0 / 21 | 654-692 / 390-408 | 25,100-26,100 / 14,700-15,100 |
| Ashley (hill) | 103.3 / 0.8 | 322 / 4 | 0 / 32 | 1,772 / 1,076 | 116,421 / 68,833 |
| Ashley following (follow) | 112.1 / 0.0 | 296 / 6 | 0 / 29 | 1,711 / 1,078 | 123,065 / 70,786 |

Operations other than the key segments are unchanged against round 1 (section 6): the same matrix, quaternion and
trigonometry counts (for example Leon idle 65 C matrix products, 392.5 matrix x vector, 740 trig a tick).

The remaining key segments are root motion and MotionSetCore's start values (still the original decoder: they fill
`MotionWork` state the behaviour reads). Round 1's native skeleton touched 1,116 lines for Leon idle; the baked keys
and the history (section 11) take it to 896 (-20%; -33% against the original).

## 11. The bone history kept for the bones code reads

**Why.** `updateOldPos` copied every bone's `world_old` and `world_old2` (six SoA rows; 119 bones for Leon) each
tick. The census (section 4) shows behaviour reads them only for bones it asked for (`getPartsPtr`): the body
(`getSpeedVector`, `moveBust`, the cloth's root speed) and the em10 attack checks' parts.

**The layout** (`skel.h`): the six rows are gone. A table keeps up to 32 **history bones**, 32 B each (`world_old`,
`world_old2`), with a bone-to-slot byte map. The history bones are bone 0 (always: the body's history is the one read
most, and the cloth reads it before it ever asks for bone 0) and every bone code outside asked for (the mailbox's
direct bones). `updateOldPos`, `setPos` and `setPartsOffset` move those and nothing else.
- A bone that joins during set-up starts with the original's values: until the first `updateOldPos` the table keeps
  every bone's history in a temporary block (freed then).
- A bone that joins later starts unknown: NaN in the check build, so a read before two `updateOldPos` have passed
  would show in the comparison; in the release build, its current world position.

**Equivalence.** `svc_dump` writes `hist.bin` (reference: every bone's `world_old` / `world_old2`; native: the kept
bones) and `svc_compare.py` compares them: every known value of a kept bone bit-identical on all six fixtures; the
values not known yet (2 to 27 bone-ticks a fixture, late joins) are never read (check build: bones and traces
bit-identical). Controls `histnone` (no history kept: NaN served) and `histfrozen` (the history never moves) fail.

**Counts** (`updateOldPos`, every actor, a tick; original / native): door103 377 / 71 lines (1,117 / 448 accesses), e1-route 377 / 83, bell 797 /
293, hill 1,223 / 427, follow 803 / 201. Six SoA rows a table are gone (Leon: 2,880 B).

## 12. Native cloth

**Hosting the original first.** Every svc build of re4ref now hosts `game/pendulum.cpp` (the plain build keeps its
stubs). Leon's chains run every tick on all six fixtures (hair: `PenClothMove`, 21 links; jacket: `PenClothMove3`,
24 links), Ashley's on the hill and follow fixtures (hair 21, skirt 48, sweater 8). Under the check build the round-1
skeleton served the original cloth through the mailbox (68 of Leon's 119 bones became mailbox bones) and matched
once bone 0 kept its history from the start: round 1's section 7 item 8 is done.

**The service** (`services/cloth/cloth.h`, `cloth.cpp`): engine bodies for `PenClothSet`, `PenClothMove`,
`PenClothMove3`, `PenClothFixSet` and `PenClothFixClear`.
- **Resolved once.** `PenClothSet` maps every link to its bone, its upper and side neighbours to link indices, the
  collision volumes to their bones. The original reached every link through `getPartsPtr` in every pass and every
  neighbour lookup, and kept each link's state inside its 472-byte parts record.
- **Link records.** A link's state is one 64-byte record (position, old position, speed, rest direction, length,
  bone, upper link, hit, pin, side links): two operand-cache lines, a chain contiguous. A cold 48-byte record holds
  the rest direction, the side distances and the pin position. Records rather than SoA rows: every pass reads and
  writes a link's position, old position and speed together, and the vector operations take xyz triples.
- **On the skeleton's tables.** The bones' world matrices and positions are read and written in the skeleton tables
  (new API: `skel_table_for`, `skel_parts_bone`, `skel_record_bone`, `skel_enter`, `skel_serve_bone`,
  `skel_history`, `skel_parent_mat`); a link bone's record is written only when it is a mailbox bone. The cloth no
  longer makes its links mailbox bones (Leon's mailbox: 68 back to 22).
- **Random numbers** (owner 2026-11-19, "Split it"). The cloth is presentation: its draws (the wind phase, the floor
  jitter) come from a presentation generator, one xorshift32 state a chain seeded from its set-up order, never from
  the behaviour's Rnd. The hosted original's `fRand0_1` / `fRand1_1` are renamed to a presentation stream of its own
  (`svc_cloth_glue.cpp`), so in both builds the behaviour's Rnd sees no cloth draw.
- **Stays original:** the link-against-volume tests (`penClothAtCk`, `penClothAtCkBorder`, `penClothAtCkParallel`:
  arithmetic on the volume list), `PenClothMove2` (the enemy weapons' flails) and the wind (`PenWindSet`). A chain
  the service cannot resolve (a parts table outside the owner's bones, a neighbour that is not a link of the chain)
  runs the original bodies, linked renamed `pen_orig_*`: none on the fixtures.

**Equivalence.**
- **Wind off** (`RE4_SVC_CLOTH_WIND=0` sets every chain's no-wind flag in both builds): every bone, the links
  included, bit-identical on all six fixtures; traces identical.
- **Wind on:** every bone that is not a link bit-identical; traces identical in every field (the generator field
  included); the links by `svc/cloth_stats.py`: per chain, the mean horizontal distance of its links from bone 0
  within 0.4 units of the original's, and every link's mean position within 2 units. Measured: radius within 0.251
  units (Leon's hair on the follow fixture; 0.044 on the E1 route; under 0.01 elsewhere), mean positions within 1.7
  units. Single-tick differences of the links reach 44 units (the phases differ: reported, not checked).
- **Controls:** `clothshort` (every chain one link short) and `clothnograv` (gravity off) fail with the wind off;
  `clothwind` (the wind's push twice as strong) fails the statistics on the E1 route (radius 0.552 units over 0.4).
  The wind pushes in proportion to the root's speed, so the wind control runs where Leon moves. The margin is thin
  (0.25 from the phase alone against 0.55 doubled); a longer moving fixture would widen it.

**Counts** (per actor per tick; original / native; the cloth step and everything under it; operations are math
library calls):

| Actor, fixture | Lines | of which parts records | link records and volumes | Accesses | Matrix x matrix | Matrix x vector | Normalize | Rotation about an axis | Trig |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Leon: hair + jacket (door103) | 377 / 261 | 365 / 2 | 12 / 259 | 21,927 / 23,410 | 45 / 45 | 114.7 / 114.7 | 350.9 / 350.9 | 73.7 / 73.7 | 123.5 / 123.5 |
| Leon (e1-route) | 377 / 261 | 365 / 2 | 12 / 259 | 22,202 / 23,625 | 45 / 45 | 121.6 / 121.6 | 354.0 / 354.0 | 80.6 / 80.6 | 123.5 / 123.5 |
| Ashley: hair, skirt, sweater (hill) | 637 / 452 | 614 / 2 | 23 / 450 | 57,967 / 61,017 | 73.6 / 73.6 | 172.4 / 172.4 | 700.2 / 700.2 | 96.7 / 96.7 | 199.7 / 199.7 |
| Ashley (follow) | 637 / 454 | 614 / 2 | 23 / 451 | 58,645 / 61,675 | 75.9 / 76.0 | 180.2 / 180.2 | 698.2 / 698.2 | 105.5 / 105.5 | 199.2 / 199.1 |

(The original's volume list, `re4dc_locked_cache`, is traced in the service region as the native one is.)

- **Lines fall about 30%**: the links' state leaves the 472-byte records for two lines a link.
- **Accesses rise 5 to 7%; operations are the same.** The arithmetic is the original's, call for call (the PC
  equivalence needs it), and the native side copies vectors in and out of the link records and the skeleton's SoA
  rows. That is the lever for the SH-4 version (section 14): SH4ZAM vector kernels (FIPR dot, FSRRA normalize, FTRV
  for the matrix-vector products and the axis rotations) and one pass over a chain's links where the original makes
  four (wind, angle limit, Bundle_num constraint passes, matrices), judged by the wind-on statistics.

## 13. Collision: a cell grid for the line queries

**Why.** Line queries (floors, walls, the camera, line of sight) tested every polygon of every leaf the segment's box
reached: 7.5 to 30 polygon tests a query on the fixtures. The walk itself (box tests) was cheap.

**The index** (`col.h`): each leaf of a piece's block tree gets a cell grid, 2 x 4 cells over the block's x / z
extent and 8 bands over its polygons' heights (32 B a leaf), and each leaf list entry the 64-bit mask of the cells
its polygon's box, grown by 1 unit, overlaps (8 B an entry), built at room load. A line query takes the cells of its
own grown box and tests, in the list's order, only the entries whose cells meet them.

**Exact.** A polygon the grid skips cannot be hit: a hit point lies in both boxes (1 unit is far above the line
test's rounding; a float step at 65,536 units is 0.008). The one exception is a segment lying exactly in the
polygon's plane, which the original's test reports as a hit at the segment's end wherever the polygon is; such a hit
never replaces the nearest hit (its distance is the whole segment's, and the nearest is kept with a strict compare).
The check build tests every skipped polygon too and counts both kinds: 0 hits; 2 end-point-only hits on the hill
(results unchanged). The grid shape was picked from nine measured (4x4x2, 4x4x4, 8x8x1, 8x4x2, 2x2x16, 4x2x8,
2x4x8, 1x1x64, 2x1x32, on door103, the hill and the bell).

**Equivalence.** Every collision query bit-identical on all six fixtures; the same build without the grid
(`RE4_SVC_COLGRID=0`) gives the same traces. Control `colgrid` (the query's cells one cell to the side) fails.

**Counts** (`col_cnt`; `RE4_SVC_COLGRID=0` is the original's walk):

| Fixture | Line queries | Polygon tests (original / grid) | Per query | Change |
|---|---:|---:|---:|---:|
| door103-walk | 4,714 | 35,399 / 11,671 | 7.5 / 2.5 | -67% |
| e1-route | 8,525 | 68,285 / 31,004 | 8.0 / 3.6 | -55% |
| bell-ganado | 10,752 | 193,697 / 107,983 | 18.0 / 10.0 | -44% |
| bell-ganado-hit | 7,227 | 131,909 / 73,016 | 18.3 / 10.1 | -45% |
| hill-ashley | 31,520 | 935,155 / 370,884 | 29.7 / 11.8 | -60% |
| square-follow | 6,142 | 115,797 / 37,522 | 18.9 / 6.1 | -68% |

Lines touched by the collision service (all queries of a tick, original / native; round 1's native in brackets):
door103 123 / 144 (135), e1-route 164 / 184 (180), bell 622 / 591 (581), hill 839 / 760 (787), follow 200 / 223
(216). **Level:** every entry a leaf visits now reads its 8-byte cell mask (four to a line, in the list's order), which
costs about the lines the skipped polygons' 32-byte records saved. The tests are what fall: 44 to 68% fewer
plane-and-edge tests, the arithmetic the SH-4 pays; the lines are a wash on the PC count.

Memory: the village square's tables grow from 370 KB to 544 KB (scenery 141,536 -> 198,720 B, effect 228,128 ->
345,088 B); the hill path's from 231 KB to 305 KB.

## 14. What the engine image must change for round 2

1. **Motion keys.**
   - Bake the archives with `bake/motion_keys.py` into the disc tree and load each archive's baked clips with it;
     bind each FCV entry to its baked clip at archive load (an entry table from the baker), not by identity at
     `MotionSetCore` (the PC build binds lazily, outside the counts). Provide `svc_mk_pack` or its per-archive form.
   - **Memory decision:** the hot tables are 1.84 times the clips (Leon's four archives: 1.26 MB of keys, 2.55 MB of
     rows). The cold section can point at the clip's own keys instead of a copy. Options to measure: 16-bit rows
     with a per-column scale (half the size; a step of at most 0.0055 degrees, not exact, so plays-right decides),
     rows only for the clips a room uses, or both.
2. **History:** nothing beyond the new `skel.cpp`; 32 history bones a table cover the fixtures (at most 14 direct
   mailbox bones a model).
3. **Cloth:** link `services/cloth/cloth.cpp`; link `pendulum.cpp` with its five bodies renamed (`pen_orig_*`, the
   fallback) and its `fRand` calls renamed to the presentation generator; 34 KB of `svc_pool_carve` (32 KB of
   chains, 2 KB of volumes). The E1 image hosts Leon's cloth through the original today: this replaces it. The SH-4
   version should take SH4ZAM's vector kernels and fold the passes (section 12); the wind-off comparison and the
   wind-on statistics on Flycast decide.
4. **Collision grid:** in `col.cpp` (room load); the village square's tables grow 47% (544 KB).
5. **Random numbers:** the engine's presentation generator replaces the cloth's per-chain xorshift when it exists.

## 15. Round 1 sections round 2 changed; limits

- Section 2: the six `world_old` / `world_old2` rows are gone (`soa[27][cap]`), the history set is new (section 11);
  `hist` (the key history) is touched only by clips without baked keys. Leon's table without the check build:
  about 47.5 KB (49.2 KB in round 1).
- Section 7, item 8 (the pendulum hosted under the check build): done (section 12).
- Section 9: key sampling is baked (section 10); the cloth is covered (section 12).
- **Not done:** the motion keys' size decision (section 14); root motion and `MotionSetCore`'s start values still on
  the original decoder; SH4ZAM kernels and a single-pass cloth (no new math kernel was written, so no SH4ZAM-style
  commit); the swept-sphere queries without the grid (a push moves the sphere mid-query, so the cells would have to
  follow it); no farm (em12) Ganado fixture; no timing (emulator lane).

# Round 3 (lane eng-svc3)

Branch `lane/eng-svc3`. Same six fixtures, same tier (PC, re4ref), no timing. What round 2 left open: the motion
keys' memory, the cloth's math on SH4ZAM, the root motion through the original decoder, the swept sphere without the
grid and the masks' memory. `svc/svc_controls.sh` now also runs, per fixture, the native build with no pack (every
sample decoded natively) and with 16-bit rows, and the controls `mkroot` and `mkcoarse`: 52 rows, all as they must
(`E:\RE4DC-Lanes\eng-svc3\ev\controls\svc_controls.md`).

## 16. Motion keys: the memory decision

**The pack, version 2** (`bake/motion_keys.py` writes "RE4MK2", `services/skeleton/skel_mk.h` reads it):
- **Pose rows** (MotionMoveCore's channels) as float32 (exact) or as **16-bit steps** (`--rows s16`): per column a
  float32 scale and offset, value = offset + step x scale (the service's arithmetic; the baker picks each step by
  that arithmetic). Rows start on a 32-byte line (16 steps a line).
- **Aux rows**, float32 always: the root motion's two channels (`Null_pos`, kind 1; `Null_rot`, kind 0x40) and the
  attach camera's (channel 6 / 7). Root motion moves the actor: it stays exact. Unpadded (a tick reads two joints).
- **No copy of the keys.** Round 2 baked a cold copy of every clip's key blocks (3.48 MB) for fractional frames. The
  clip's own key blocks stay resident with its archive anyway (behaviour reads the clip header); the service keeps
  the clip's key table when it binds the clip and decodes fractional frames from it (section 17).
- **A per-room clip set** (`--set <file>`): only the listed clips are baked. A clip the pack does not hold is decoded
  from its keys on every sample: exact, slower, counted ("outside the pack"). So a set that misses a clip costs time,
  never correctness. `bake/motion_sets.py` makes a room's set from captured play (the service logs every clip it
  binds).
- Identity: the FNV-1a of the clip header and every served joint's key block (pose, root and camera now), as the
  service computes it at MotionSetCore. 415 distinct clips in the fixtures' archives (round 2: 414; one pair shared
  its pose keys but not its root keys), 1 rejected (no joints).

**Bytes** (`E:\RE4DC-Lanes\eng-svc3\ev\motion\mk-bytes.md`; the fixtures' rooms, every clip of the archives the room loads; the clip keys are
resident today and stay):

| Room | Actor | Clips | Clip keys (resident) | float32 rows | 16-bit rows | Named by the behaviour: clips | float32 | 16-bit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Village square (r101) | Leon (pl00 + wep02) | 107 | 618,304 | 1,095,104 | 680,576 | 105 | 1,064,800 | 661,856 |
| Village square | Ashley (pl11) | 71 | 495,264 | 951,584 | 592,256 | 53 | 660,416 | 411,424 |
| Village square | Ganado (em15) | 166 | 1,945,120 | 3,571,840 | 2,045,248 | 135 | 2,929,728 | 1,664,352 |
| Hill path (r11d) | Leon | 107 | 618,304 | 1,095,104 | 680,576 | 105 | 1,064,800 | 661,856 |
| Hill path | Ashley | 71 | 495,264 | 951,584 | 592,256 | 53 | 660,416 | 411,424 |
| Hill path | Ganado (em16) | 156 | 1,845,984 | 3,328,960 | 1,904,928 | 130 | 2,705,248 | 1,540,768 |
| **All 415 clips** | | | **3,738,784** | **7,381,312 (1.97x)** | **4,387,904 (1.17x)** | | | |

Round 2's form was 6.87 MB hot + 3.48 MB cold copy (2.77x the keys); float32 here is 1.97x (no cold copy, root rows
added), 16-bit 1.17x. One scale for a whole clip (`--qscale clip`) was measured and rejected: up to 5.2 rad and 5.2 u
off (a clip's positions span tens of thousands of units), the bones 24 u / 17 deg off, an e1-route collision result
flips.

**The per-room set.** Two sources measured:
- *Named by the behaviour* (every FCV entry a behaviour source names by a literal archive index, `PL_ARC_PTR` /
  `SUB_MOT`, for the archives the room's actor list loads; the handgun archive whole): 64 of Leon's 66 pl00 clips, 53
  of Ashley's 71, 135 of em15's 166. Saves 3 to 31% an archive, and **misses clips the fixtures play** (tables and
  computed indices): 1 to 3 clips outside the set on four of six fixtures (hill: 78,893 samples decoded from keys).
  Not a usable set.
- *Captured play* (`motion_sets.py` over the fixtures' logs): the village square's five fixtures bind 25 clips, the
  hill path's 7. Packs: village square 416,736 B float32 / 244,896 B 16-bit; hill path 173,696 / 100,128. No clip
  outside the set on its own fixtures. A real room's capture is larger than these short fixtures; the miss counter
  shows what a capture lacked.

**Equivalence** (`E:\RE4DC-Lanes\eng-svc3\ev\controls\svc_controls.md`, wind off):
- float32 rows: every bone bit-identical on six fixtures (as round 2), traces identical.
- No pack (every sample, root motion included, decoded natively from the keys): bit-identical on six fixtures.
- 16-bit rows (an approximation, owner 2026-10-19): every bone but the cloth links within 0.14 u and 0.006 deg
  (bell-ganado-hit; door103 0.023 u, e1-route 0.055 u, bell 0.046 u, hill 0.093 u, follow 0.031 u), the cloth links
  by `cloth_stats.py` (chain radius within 7e-5 u, link means within 0.003 u), collision results identical with query
  points within 0.38 u (the IK's foot queries move with the feet), traces PASS in every field (gameplay fields
  identical). The cloth links alone, compared bone for bone, reach 0.7 deg on Ashley's skirt (the chain amplifies a
  pose difference), which is why they are judged by their statistics as with the wind on.
- 16-bit rows of the per-room captured sets: as the 16-bit rows above, 0 clips outside the pack.
- Controls: `mkrow` (pose rows one frame late) and `mkroot` (root rows one frame late: Leon's position, traces FAIL)
  fail; `mkcoarse` (16-bit steps cut to 8 bits) fails the tolerance (13.8 u / 0.8 deg on door103, 19.2 u / 2.5 deg on
  the bell).
- Fractional frames served from the rows instead of the keys (`--frac-check`, every clip at k + 1/4, 1/2, 3/4): linear
  up to 45 deg / 298 u, Catmull-Rom 40 deg / 168 u, root channels 2,000 u (clips with cuts). Not safe: the keys stay.

**Recommendation: 16-bit rows for a per-room set from captured play, the keys resident.**
- Against the memory map (SHELL_MAP section 3: the room pack 4,096 KiB with actor meshes and motions; E1 measured
  2.2 MB free to the arena): rows for every clip do not fit beside the keys in a fight room. The bell fight's Leon and
  Ganado archives hold 2.56 MB of keys; their float32 rows add 4.67 MB, 16-bit rows 2.73 MB (the Ganado archive alone
  2.05 MB). Captured sets add 0.10 to 0.25 MB a room (16-bit; 3 to 8% of the room's keys).
- 16-bit rows halve every set's bytes (1.17x the keys against 1.97x) within 0.14 u / 0.006 deg.
- A capture that misses a clip costs that clip's decode on every sample until the next bake, never correctness; the
  miss counter goes in the room's capture gate.
- Not chosen: rows replacing the keys (fractional frames need them: the error above); named-by-behaviour sets (miss
  played clips).

## 17. Native root motion and key decoder

- **Root motion** (`skel.cpp`): `MotionGetSpeed`, `MotionGetPosition`, `MotionAddSpeed`, `MotionSequenceCtrl` and the
  clock's small functions (`MotionBlendOff`, `MotionPause`, `FcvGetMaxFrame`, `MotionGetMaxFrame`,
  `MotionGetCurrentFrame`, `MotionCheckCrossFrame`, `MotionGetState`) are native: the original's arithmetic in its
  order on `MotionWork`; the root samples from the aux rows. `MotionSetCore`'s start values (the root at the start
  frame, the clip's whole displacement `Pos_dist` / `Ang_dist`) likewise. `svc.mk` weakens the eleven in motion.o.
- **The decoder** (`mk_decode`): one joint's three axes from its key block: a binary search for the last key at or
  before the frame (key 0 is frame 0), the Fcc field conversions (f32, s16 and s8 times 0.0001f) and `hermite()` in
  the original's order; a looping clip wraps once per axis, a frame at or past the end of one that does not takes the
  last key, as HermiteInterpolation. Exact on the clips the baker accepts (strictly rising keys from 0 to maxFrame,
  checked: the bracket a history search finds is the same). It serves fractional frames, clips outside the pack and
  everything when no pack is loaded.
- **The original decoder is out of the service:** `skel.o` references no motion.cpp symbol (`nm -u`); the key history
  (`hist`, 36 B a bone; 4,284 B for Leon) is gone from the table. HermiteInterpolation stays in motion.o for two
  other units only: `cam_motion` (camera curves) and `shape` (shape keys).
- **Equivalence:** six fixtures bit-identical with the float32 pack and with no pack. Samples: root motion from rows
  363 (door103) to 5,693 (hill) a fixture, decoded 15 (the fractional frames of bell-ganado-hit, where the pose has 315
  decoded samples); the original decoder 0.

## 18. The cloth on SH4ZAM

**The kernel** (`services/cloth/cloth_kernel.h`, `.c`; its own commit): one chain's tick on the link records and the
skeleton's bone rows, in C on SH4ZAM's primitives: `shz_dot6f` / `shz_mag_sqr3f` (dot products, magnitudes),
`shz_inv_sqrtf_fsrra` (normalise), `shz_sqrtf_fsrra` (SQRTF), `shz_acosf` / `shz_asinf`, `shz_sincosf` (the axis
rotations), `shz_vec3_cross`. On the SW back-end each forms its result as the C library the original calls does
(VECNormalize, PSVECDotProduct, PSMTXRotAxisRad, PSMTXMultVec(SR), PSMTXConcat; the transcendental functions are the C
library's); on the SH-4 they are FSRRA and FSCA (`sh-elf-gcc -m4-single-only -O2`: 11.3 KB, 38 FSRRA, 1 FSCA, no
libm call; SH4ZAM leaves FIPR off by default). The **volume tests** (`penClothAtCk`, `penClothAtCkBorder`,
`penClothAtCkParallel`) are native in the kernel. `cloth.cpp` sets up a step (the floor, the reset, the volumes, the
wind phase, the root's motion) and calls it.

**One pass, measured and rejected.** `cloth_k_step_onepass` moves, limits, constrains (Bundle_num times) and orients
each link before the next: a link's later neighbours hold last tick's positions while it is constrained. Six fixtures,
wind off: links' mean positions 11 to 54 u from the original's (bound 2), chain radius up to 6.25 u (bound 0.4); the
other bones untouched. Not used (`RE4_SVC_CLOTH_PASSES=1` runs it).

**The schedule used: fused, exact.** The original makes Bundle_num + 3 passes (motion and wind, angle limit,
Bundle_num constraint passes, matrices). `cloth_k_step` makes Bundle_num + 1: the motion and the angle limit in one
pass when every upper link comes before its link (the angle limit reads the upper link after its own motion and
limit), and the last constraint pass with the matrices (a link's matrix stage runs as soon as no later constraint can
move it or its upper link). Every stage reads what it reads in the original's order. Passes over a chain a step on the
fixtures: 3.5 against 5.0 in the original order for Leon's two chains (door103), 3.8 against 5.4 for the hill's five.

**Equivalence:** wind off, every bone, the links included, bit-identical on six fixtures; wind on: the round-2
statistics exactly (chain radius within 0.251 u on the follow fixture, 0.044 u on the E1 route; link means within 1.7
u). Controls `clothshort`, `clothnograv` and `clothwind` fail as before. `RE4_SVC_CLOTH_PASSES=4` (the original pass
order through the kernel) is bit-identical too.

**Test and benchmark** (`cloth_kernel_test.c`, `make cloth_ktest`; `E:\RE4DC-Lanes\eng-svc3\ev\cloth\cloth_ktest.txt`):
- the nine primitives against the C library over 200,000 random inputs: bit-identical;
- 264 random chains (both variants, upper links before and after their links, side links, spheres and cylinders,
  eleven flag combinations, Bundle_num 1 to 3) x 120 ticks: the fused schedule bit-identical with the original pass
  order (44 million volume tests, 345,570 hits);
- PC host timing (x86, not SH-4; two runs, the second on a loaded machine): hair-like chain 2.3 / 2.4 us a step
  (original order / fused; 3.8 / 4.4 loaded), jacket-like 4.1 / 4.8 (5.7 / 5.2), skirt-like 24.5 / 21.9 (37.6 / 33.9).
  No consistent gain on the PC: the chains are 3 to 7 KB and stay in the cache between passes. The SH-4 lever is the
  arithmetic (FSRRA and FSCA instead of library calls), which the emulator lane times.

**The presentation generator** (`services/cloth/pres_rng.h`): the interface the cloth draws through (owner
2026-11-19, "Split it"): a stream a chain, `pres_seed` / `pres_next` / `pres_f01` / `pres_f11` (xorshift32, the
round-2 generator). The engine image can put its generator behind the same four functions.

## 19. Collision: the swept sphere on the grid, smaller masks

**The swept sphere** (`polySphereCk`, the walls and floors that push a moving sphere): per leaf the cells of the box of
its segment (old position to current position) grown by its radius; an entry whose cells miss them is skipped and
**marked visited**; after every push the cells are taken again (the sphere moved). Exact:
- a polygon can change the sphere only if the sphere comes within its radius of it (`At_poly_sphere_ck2`'s plane
  and edge cases) or its segment crosses it (the surface-line case); both put the polygon's box inside the grown
  segment box, so a skipped polygon's test returns 0 and changes nothing;
- the original marks a polygon visited when it tests it; the native marks a skipped one visited too, so a polygon in
  two leaves is not tested later from the second leaf with the sphere moved (which would differ from the original).
The check build tests every skipped polygon on a copy of the sphere: 0 hits on six fixtures.

**Smaller masks.** Round 2: a 64-bit mask (2 x 4 x 8 cells) for every leaf list entry, and a 32-byte grid a leaf (the
village square's tables 370 -> 544 KB). Measured (`E:\RE4DC-Lanes\eng-svc3\ev\collision\col-variants.md`; all exact, 0 check-build misses):

| Shape, smallest masked leaf | Village square tables | Hill path | Line tests a query (door / route / bell / hit / hill / follow) | Sphere tests a query |
|---|---:|---:|---|---|
| no grid (the original's walk) | 470,240* | 272,800* | 7.5 / 8.0 / 18.0 / 18.2 / 29.7 / 18.9 | 6.0 / 7.3 / 13.3 / 15.1 / 17.2 / 20.8 |
| round 2's shape: 2x4x8, 64-bit, every leaf (the sphere on it too) | 543,808 | 304,544 | 2.5 / 3.7 / 10.0 / 10.1 / 11.8 / 6.1 | 5.4 / 3.7 / 4.5 / 5.4 / 3.2 / 5.7 |
| 2x4x8, 64-bit, leaves of 8 or more | 528,608 | 300,800 | 2.5 / 4.5 / 11.2 / 11.2 / 11.8 / 7.0 | 5.4 / 4.0 / 5.7 / 6.7 / 3.2 / 7.2 |
| **2x2x8, 32-bit, leaves of 8 or more (chosen)** | **470,240** | **272,800** | 3.5 / 5.4 / 11.7 / 11.7 / 12.0 / 8.4 | 5.4 / 4.9 / 6.3 / 6.9 / 4.2 / 9.7 |
| 2x2x8, 32-bit, every leaf | 477,824 | 274,688 | 3.5 / 4.7 / 10.6 / 10.7 / 12.0 / 7.6 | 5.4 / 4.7 / 5.4 / 5.6 / 4.2 / 8.7 |
| 2x2x8, 32-bit, leaves of 16 or more | 447,520 | 267,232 | 7.5 / 6.3 / 12.3 / 12.5 / 17.3 / 8.5 | 6.0 / 5.7 / 6.9 / 8.6 / 6.7 / 10.0 |
| 2x4x4, 32-bit, 8 or more | 470,240 | 272,800 | 2.5 / 4.7 / 12.0 / 11.9 / 14.0 / 7.0 | 5.4 / 4.0 / 7.2 / 8.2 / 3.2 / 7.2 |

(* the no-grid run is the chosen build with the grid switched off: its tables are the chosen ones.)

Chosen: 32 cells (2 x 2 x 8) in a 32-bit mask, masks only for leaves of 8 entries or more: the village square's tables
**470 KB** (round 2: 544 KB; round 1: 370 KB), the hill path's 273 KB (305 KB). Over the six fixtures, line and
sphere polygon tests together fall from round 2's 847,000 (lines on the grid, the sphere on the original walk) to
778,000, and from the original's 1.69 million (-54%).

## 20. Counts against round 2 (PC census)

Round 2's windows and reference runs (the reference is unchanged); the native build with the float32 pack and with
the 16-bit pack (`E:\RE4DC-Lanes\eng-svc3\ev\cost\cost-f32-*.md`, `cost-s16-*.md`; per actor per tick; original / round 2 / round 3). x86
counts, no timing.

| Actor, window | Skeleton lines | Archive (key) lines | Baked-key lines f32 / s16 | Skeleton accesses |
|---|---:|---:|---:|---:|
| Leon idle (door103) | 1,336 / 896 / 892 (s16 903) | 206 / 11 / 6 | 18 / 29 | 65,304 / 43,496 / 43,509 |
| Leon running and aiming (e1-route) | 1,347 / 959 / 952 (965) | 212 / 12 / 6 | 19 / 32 | 89,611 / 50,617 / 50,617 |
| Ganado (bell, em1) | 631 / 445 / 432 (444) | 260 / 19 / 5 | 20 / 32 | 25,582 / 15,625 / 15,615 |
| Ganado, each of four (hill) | 654-692 / 390-408 / 388-407 | 262-300 / 8 / 4 | 24 / 36 | 25,100-26,100 / 14,700-15,100 / 14,748-15,173 |
| Ashley (hill) | 1,772 / 1,076 / 1,079 (1,102) | 322 / 4 / 8 | 32 / 55 | 116,421 / 68,833 / 69,022 |

- Key segments (hermite) a tick: 0 for every actor (round 2: 2.4 to 6.0 for root motion and MotionSetCore).
- The archive key reads that remain in round 2 (root motion and MotionSetCore through the original decoder) are gone
  but the clip header and key-table reads: 4 to 8 lines.
- The 16-bit rows touch 11 to 23 more lines a tick than float32 (each clip's scale and offset table, 8 B a column, is
  read with the row): the price of half the bytes.

| Cloth, window | Lines (original / round 2 / round 3) | Accesses |
|---|---:|---:|
| Leon: hair + jacket (door103) | 377 / 261 / 261 | 21,927 / 23,410 / 19,437 |
| Leon (e1-route) | 377 / 261 / 261 | 22,202 / 23,625 / 19,492 |
| Ashley: hair, skirt, sweater (hill) | 637 / 452 / 452 | 57,967 / 61,017 / 53,797 |
| Ashley (follow) | 637 / 454 / 454 | 58,645 / 61,675 / 54,009 |

The kernel's accesses are 17% under round 2's and 11% under the original's (the vector copies in and out of the
library calls are gone); the lines are the same (the link records and the bones).

| Collision, every query of a tick | Lines (original / round 2 / round 3) | Accesses (original / round 3) |
|---|---:|---:|
| door103 | 123 / 144 / 140 | 3,533 / 4,264 |
| e1-route | 164 / 184 / 179 | 4,244 / 4,918 |
| bell | 622 / 591 / 538 | 12,576 / 12,615 |
| hill | 839 / 760 / 667 | 23,461 / 18,893 |
| follow | 200 / 223 / 212 | 7,614 / 8,724 |

Lines a query (the tick's lines over the fixture's line and sphere queries a tick, an estimate): door103 7.9 / 9.3 /
9.0, e1-route 10.7 / 12.0 / 11.7, bell 14.2 / 13.5 / 12.3, hill 13.0 / 11.8 / 10.4, follow 6.8 / 7.6 / 7.2. The
fights (bell, hill) now touch 13 to 20% fewer lines than the original; the walks stay 3 to 14% above it (the masks
and the grid records of the leaves they visit).

## 21. What the engine image must change for round 3

1. **Motion keys.**
   - Bake with `bake/motion_keys.py --rows s16 --set <room>.lst` (RE4MK2); make each room's set with
     `bake/motion_sets.py` from captured play of the room (benchmark and full-play runs log every clip the service
     binds); put the room's miss count ("outside the pack") in its capture gate and add the missed clips at the next
     bake.
   - Keep the archives' clip keys resident (fractional frames and clips outside the set are decoded from them); no
     cold copy is baked any more.
   - Bind each archive's clips at archive load (identity, as `mk_bind`: the clip's key table pointer is kept, so the
     keys must not move while the clip is bound); call `skel_mk_forget(base, bytes)` when an archive is freed.
   - Link `skel.cpp` with the eleven motion.cpp functions it now defines weakened in motion.o (`svc.mk` WEAK_motion),
     or drop motion.o once `cam_motion` and `shape` (the two other HermiteInterpolation users) have their own decoder.
     **Required for the E1 image** (`engine/game/Makefile`, merged from eng-e1c): with round 3's skel.cpp its
     `WEAK_motion` list must gain MotionGetSpeed, MotionGetPosition, MotionAddSpeed, MotionSequenceCtrl,
     MotionBlendOff, MotionPause, FcvGetMaxFrame, MotionGetMaxFrame, MotionGetCurrentFrame, MotionCheckCrossFrame and
     MotionGetState; without them the link stops on eleven multiple definitions, with them `e1.elf` links (checked:
     `make WEAK_motion="..."`, sh-elf, no disc). Without a motion pack the image decodes every clip natively.
   - The table is 36 B a bone smaller (no key history).
2. **Cloth.** Compile `services/cloth/cloth_kernel.c` as C with SH4ZAM's include path and the engine's SH-4 flags
   (`-m4-single-only`; without `-ffast-math` SH4ZAM's sincos is FSCA, with it the compiler's); `cloth.cpp` drives it.
   The volume tests are native; `pendulum.cpp` is still linked for `PenClothMove2` (enemy flails), `PenWindSet` /
   `GlobalWind` and the fallback bodies: porting those is what remains for "no original service code" in the cloth.
   Put the engine's presentation generator behind `pres_rng.h` when it exists.
3. **Collision.** `col.cpp` with the swept-sphere grid and 32-bit masks: the village square's tables 470 KB (the
   round-2 544 KB figure in section 14 is replaced); `svc_pool_carve` sized to that.
4. **SH-4 rounding.** FSRRA and FSCA round differently from the PC's library: the cloth's wind-off comparison becomes
   a statistics check on Flycast (the round-2 bounds); the 16-bit rows' tolerance check (bones 1 u / 0.1 deg, links by
   statistics) is unchanged.

## 22. Interface changes and tools (round 3)

- `skel_mk.h`: RE4MK2. `MkPack.flags` (1: 16-bit rows); `MkClip` gains `nAux`, `auxStride`, `oAux`, `oQuant` and loses
  `oColdTab`, `oCold`, `coldBytes`; `MkJoint.src` is `MK_ROWS`, `MK_CONST`, `MK_AUX` (root and camera), `MK_NONE`.
- `skel.h`: `SkelTable::hist` removed; `SkelCounters` `mk_cold` / `mk_orig` replaced by `mk_dec`, `mk_miss`,
  `mk_root_rows`, `mk_root_dec`, `mk_axes`, `mk_rebinds`; `skel_control_mk` 2 (root rows late) and 3 (8-bit steps);
  new `skel_mk_forget()`. `skel.cpp` defines MotionGetSpeed, MotionGetPosition, MotionAddSpeed, MotionSequenceCtrl,
  MotionBlendOff, MotionPause, FcvGetMaxFrame, MotionGetMaxFrame, MotionGetCurrentFrame, MotionCheckCrossFrame,
  MotionGetState (same signatures as motion.h).
- `cloth.h`: `ClothChain::rng` is a `PresRng` (same 4 bytes); `cloth_passes`; new `cloth_kernel.h` (C API: `ClothKStep`,
  `cloth_k_step`, `cloth_k_step_passes`, `cloth_k_step_onepass`, the three volume tests, `cloth_k_cnt`) and
  `pres_rng.h`. `PenClothSet` / `Move` / `Move3` / `FixSet` / `FixClear` unchanged for callers.
- `col.h`: `ColGrid.mask` (was padding), `ColMask` (u32; u64 with `COL_MASK64`), `ColPiece::cmask` is `ColMask*` with
  `nMask`; new counters; `col_sphere_grid_off`, `col_mask_min`. `cSatMgr` entry points unchanged.
- `motion_keys.py`: `--rows`, `--qscale`, `--set`, `--frac-check`; labels are `archive:entry` for proxy clips too.
  New `motion_sets.py`.
- re4ref (`svc_io.cpp`): `RE4_SVC_MK=none` (no pack), `RE4_SVC_MK16` (the 16-bit pack for svc_controls),
  `RE4_SVC_CLOTH_PASSES=4` / `1` (original order / one pass), `RE4_SVC_COLSPHERE=0`, `RE4_SVC_COLMIN=<n>`,
  `RE4_SVC_CONTROL=mkroot` / `mkcoarse`; `make cloth_ktest`; `svc.mk` `COL_DEFS`.

**Not done:** per-room sets from real room captures (only the fixtures' short captures exist); PenClothMove2, the wind
and the fallback still original (pendulum.cpp linked); HermiteInterpolation still in motion.o for the camera and
shape units; the grid for unmasked small leaves still allocated (32 B a leaf); no farm (em12) fixture; no SH-4
timing (emulator lane).

# Native skeleton, collision and cloth services (lanes eng-svc and eng-svc2, 2026-11-19)

The services that dominate the budget's Services row, as engine code on engine tables, proven on the PC to give
the original units' results. Tier of every number here: **PC** (re4ref, the host build of the original code). No
console, no Flycast, no MODELLED number; no timing claim.

**Round 2 (lane eng-svc2), sections 10 to 15:** offline motion keys (no key search, history or decoding in a tick),
the bone history kept for the bones code reads (not every bone), a native cloth service (Leon's hair and jacket,
Ashley's hair, skirt and sweater) on engine generator random numbers, and a cell grid that cuts the polygons a line
query tests by 44 to 68%. Sections 1 to 9 are round 1 as it was handed back; where round 2 changed them, section 15
says so.

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

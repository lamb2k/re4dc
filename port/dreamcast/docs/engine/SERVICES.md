# Native skeleton and collision services (lane eng-svc, 2026-11-19)

The two services that dominate the budget's Services row, as engine code on engine tables, proven on the PC to give
the original units' results. Tier of every number here: **PC** (re4ref, the host build of the original code). No
console, no Flycast, no MODELLED number; no timing claim.

- **Skeleton:** `port/dreamcast/engine/services/skeleton/` (`skel.h`, `skel.cpp`, `skel_xm.h/.c`).
- **Collision:** `port/dreamcast/engine/services/collision/` (`col.h`, `col.cpp`).
- **The re4ref switch and the tools:** `port/dreamcast/engine/hostref/svc/` (`svc.mk` and the files it names).
- **Result:** on six fixtures (Leon's door103 walk, the E1 route, the bell Ganados, a hit on a Ganado, Ashley on the
  r11d hill, Ashley following Leon), every bone of every actor on every tick and every collision query are the
  original's: bones equal as numbers (bit-identical but for the sign of exact zeros), queries bit-identical, traces
  bit-identical. Three controls (a parent off by one, floors 1 unit higher, the IK pass skipped) fail as they must.

## 1. What replaces what

| Original (behaviour still calls it) | Native body | Stays original |
|---|---|---|
| `MotionSetCore`, `MotionMove`, `MotionMoveCore`, `MotionMoveSub`, `MotionHokan`, `MotionClear`, `PartsWorldPosCalc` (motion.cpp) | `skel.cpp` on the actor's `SkelTable` | the key decoder `HermiteInterpolation` and the motion key lease (the data format); the clock and root motion (`MotionSequenceCtrl`, `MotionGetSpeed`, `MotionAddSpeed`, `MotionCheckCrossFrame`: `MotionWork` state behaviour reads) |
| `IKInit`, `InverseKinematics` (ik.cpp, not linked) | `skel.cpp` | the floor query (collision, native) |
| `cModel::partsMatCalc`, `partsWorldCalc`, `matBlend`, `matUpdate`, `setPos`, `updateOldPos`, `partsFixMemory`, `partsFixAdjust`, `setParent` (both), `setPartsOffset`, `releasePartsList`, `getPartsPtr`, `GetPartsAddr` (model.cpp) | `skel.cpp` | model and parts allocation, model info, relocation |
| `at_pos_calc` (atari.cpp: a collision push moves every bone) | `skel.cpp` | |
| `cSatMgr::hitCheck2`, `hitCheck`, `polySphereCk` (atari.cpp) | `col.cpp` on the room's `ColPiece` tables | `check`, `checkAir`, `scrAtCheckSphere(Air)`, `wallAdjust`, `adjust`, `getFloor`, `atck` (per-model logic above the three cores); the actor volumes (`EmAtCheck`, `ObjHitCheck`, `EmHitCheck`, `cAtariInfo`, capsules) |

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
| `parent[cap]`, `mbox[cap]`, `mlist[cap]`, `rec[n]` | 3 + 4 | parent bone (0xFF the model, 0xFE an outside coordinate); mailbox state and list; the cParts record |
| `ik[8]` | 96 a chain | IK plane matrix, axis, direction of each chain root |

| Actor | Bones | Native table | cParts records (472 B a bone) | World pass reads + writes a tick per pass |
|---|---:|---:|---:|---:|
| Leon | 119 | 49,056 B | 56,168 B | 13,328 B (112 B a bone) |
| Ashley | 141 | 58,240 B | 66,552 B | 15,792 B |
| Ganado | 34 | 15,552 B | 16,048 B | 3,808 B |
| Handgun (object) | 4 | 3,168 B | 1,888 B | 448 B |

The check build adds 84 B a bone (the ancestor shadow, section 4); the sizes above are without it.

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
| tri [nPoly] | 96 | one record per polygon: three vertices, face normal, three edge vectors, attribute word, polygon number, normal index |

| Room, piece | Nodes | Leaves | List entries | Polygons | Native tables | The file's tables the original walk reads |
|---|---:|---:|---:|---:|---:|---:|
| Village square (r101), scenery (SAT) | 605 | 454 | 5,325 | 1,198 | 141,536 B | 122,542 B |
| Village square, effect (EAT) | 1,149 | 862 | 11,165 | 1,831 | 228,128 B | 205,778 B |
| Hill path (r11d), scenery | 293 | 220 | 4,142 | 1,150 | 126,464 B | 99,764 B |
| Hill path, effect | 265 | 199 | 3,324 | 949 | 104,864 B | 83,704 B |

A polygon test reads one 96-byte record (three lines); the original reads the polygon (20 B), three vertices, a
normal and three edges from five tables. The walk is the original's (same box tests, same order, same per-query
polygon dedupe), so the number of box and polygon tests is the same; what changes is where the bytes are. The file
stays resident: the hit report's normal pointer (`pFloor_norm`, `hitCheck2`'s `attr`) points into its normal table.

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

What it shows: outside `at_pos_calc`, the behaviour reaches a bone only through `getPartsPtr` (or `GetPartsAddr`),
and then reads that record or, once (`moveBust`), its parent's through `pParent`. `at_pos_calc` is collision code that
walks every record after a push; it is replaced (it moves the table).

**How they are served: the mailbox.**
- A record becomes its bone's mailbox when code outside asks for it (`getPartsPtr`, `GetPartsAddr`, a
  `setParent` target). From then on every native entry takes the record's fields back first (the behaviour may have
  written eyelid angles, waist addRot, bust positions, matrices) and writes the table's values to it after.
- Its ancestors (reached through `pParent`) are served the world matrix, world position, `r_scale` and scale only,
  and nothing is taken back.
- A root bone's parent is re-read from its record before every evaluation (`objWep` writes its root's `pParent`
  directly to hang the handgun on Leon's hand).
- Everything else in a record is never written: the check build fills it with NaN at table creation, so a read the
  census missed would turn a trace into NaN; it also counts writes to ancestor records (lost writes) and records
  whose `pParent` disagrees with the table. On all six fixtures: **lost writes 0, parent mismatches 0**, traces
  identical.

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

[COST]

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

Controls by environment: `RE4_SVC_CONTROL=parent=<bone>`, `floor=<units>`, `noik`; `RE4_SVC_POISON=0` turns the check
build's poison off.

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

# Lane eng-skel1: the skeleton service's entries, the chain object, the cloth in the boss image

Status: in progress (Part A). Branch `lane/eng-skel1`.

## How to call (the bone entries; `services/skeleton/skel.h`)

For native behaviour code that today writes or reads a parts record after `getPartsPtr(no)`. Name the bone as the
behaviour does: the model and the parts number (`no`, 0 and up). Each entry returns 0, or -1 when the model has no such
bone (nothing is done and the outputs are left as they were; the original would have crashed or read garbage there).
The entry works on the skeleton's table and serves what it changed to every record the behaviour still holds, so hosted
code that keeps reading records sees the change. No entry makes the bone a mailbox bone: prefer them to `getPartsPtr`
in native code (a mailbox bone is served after every skeleton entry for the rest of the model's life).

| Original statement after `p = m->getPartsPtr(no)` | Entry |
|---|---|
| `PARTS_FLAGS(p) \|= 0x40000000; PARTS_ROT_OFS(p) = r;` (em10NeckMove part 3, em10WaistMove parts 1, 2) | `skel_addrot_set(m, no, &r, 1)` |
| `PARTS_FLAGS(p) &= ~0x40000000` | `skel_addrot_set(m, no, 0, 0)` (rot NULL: kept) |
| read `PARTS_ROT_OFS(p)` and the flag | `int on = skel_addrot_get(m, no, &r)` (1 set, 0 clear, -1 no bone) |
| `PSMTXRotRad(R, 'z', a); PSMTXConcat(p->l_mat, R, p->l_mat);` (em10NeckMove part 13) | `skel_local_post(m, no, R)` |
| `PSMTXConcat(p->mat, R, p->mat);` (em10BombNeckMove parts 0x24, 0x1B) | `skel_world_post(m, no, R)` |
| `p->ang = a; p->pos = q; p->scale = s;` (MouthPartsReset, GatlingRollMove, ClawMove, BowgunMove, BombNeckMove) | `skel_pose_set(m, no, &q, &a, &s)` (any NULL: kept) |
| read `p->pos`, `p->ang`, `p->scale` | `skel_pose_get(m, no, &q, &a, &s)` (any NULL: not read) |
| read `p->world`, `p->world_old`, `p->world_old2` (BombNeckMove) | `skel_bone_world(m, no, &w, &o, &o2)` |
| read `p->mat` (NeckMove: the player's head, `pPL->getPartsPtr(4)->mat`) | `Mtx M; skel_bone_mat(m, no, M)` (a copy) |

Notes:
- **When.** The entries have the record's timing: an added rotation is applied once by the next world pass and its
  flag cleared there (MotionMove's first pass for the IK's bones, `partsWorldCalc`); a local post-multiply lasts until
  the next matrix pass; a world post-multiply until the next world pass (so call it after the model's last world pass of
  the tick, as em10BombNeckMove runs after the move); a pose write is read by the next matrix pass and is overwritten
  by the motion for the bones the clip keys. A Ganado function that read-modify-writes (`ang.x += d`, the claw steps)
  does `pose_get`, the arithmetic, `pose_set`.
- **History.** `old` / `old2` of a bone are kept from its first ask (this entry or `getPartsPtr`): ask once at set-up
  (or one tick before) when the first values matter, as the original's record had them from the start. Bone 0's
  history is always kept.
- **A rotation.** Build it with the math service as the original does (`PSMTXRotRad(R, axis, angle)`); the entries
  take any 3x4 (rotation, scale).
- **Another model's parts** (the weapon: `w->pWep` in BowgunMove) work the same: pass that model.
- **Cost.** One parts-number walk (`no` steps, as `getPartsPtr`) and the mailbox's take-back of records handed out since
  the last entry; no per-bone serve unless the bone is a mailbox bone.

### The chain object (`services/cloth/chain.cpp`)

`SetChain`, `cObjChain::setChain`, `setParent`, `setParent2` keep their original names and arguments (`pl_cloth.h`):
em10ChainSet / em10BeltSet / em2bShortRopeSet / em2bChainSet call them as they are. The object is a record of the
engine's object pool (kind 0x1D), moved by the pool each tick; it dies with its parent; its pendulum chain is stepped
by the cloth service after its pose. `chain_cnt` counts made / refused / moves / hung / steps / orphans / lost.
**Give each chain object its own PenCloth**: the cloth service keeps one chain a PenCloth (see Findings).

### The cloth set-up (Em1fClothSet)

`PenClothSet(m, (PenCloth*) c, 100.0f)` is the cloth service's entry in every image that links it: a native
Em1fClothSet fills the PlCloth's description (its parts, up and down tables, limits, volume) and calls it, and its move
calls `PenClothMove(m, c)` and clears `be_flag` 0x00E00000.

## PC check (`hostref/svc/skent_check.sh`, 9 rows)

`RE4_TREE=<tree> skent_check.sh <out>` with `make odump native` built. odump runs the original statements on the
records (and links `game/obj1d.cpp`), native the entries (and `services/cloth/chain.cpp`), same fixture, same exercise
(`svc/skent_dump.cpp`), wind off, motion keys decoded:

| Row | Must | What |
|---|---|---|
| skent bell-ganado, skent shot-ganado | PASS | from tick 30, every tick on the first Ganado: the ten functions' statements on planted values (added rotation with the flag on and off, local and world post-multiply, pose angles / position / scale writes and reads, world position and history, the player's head matrix), with world and matrix passes between them; every bone equal every tick, every value read back identical |
| skchain bell-ganado | PASS | em10ChainSet (tick 40) and em10BeltSet (41) on the original em10 code, hung from a part, then between two parts (setParent2, tick 60) and from another part (tick 80); every bone of the Ganado and of both chain objects (their cloth links included) equal every tick; the objects' state, position and matrix identical |
| effect | FAIL | the reference with the exercise against the reference without it (the exercise moves the bones) |
| controls entflag, entpost, entpose, enthist, chainmid | FAIL | the flag never set; r x M; pose angles x / z swapped; old2 read as old; the hung chain at its first offset |

## Findings
- The native cloth keeps **one chain per PenCloth** (`cloth.cpp find(c)`); the original keeps a chain's state in the
  model's parts records, so one description can drive two models. El Gigante's chained form does that (em2bChainSet:
  the second and third arm chains share `rope[1]`): in the engine the second set-up takes the first chain over. Request
  to the cloth's owner (eng-cloth1): key a chain by (PenCloth, model), and give a chain back when its model goes.

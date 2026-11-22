# Lane eng-rec1: the ten chapter 1 rooms captured and baked into game packs (2026-11-22)

**Status: finished, unaudited** (see "Not done" for the rooms whose bake had not finished at hand-back).
Tier of everything here: **Flycast plain** (function runs of the old game as a recorder, slots std1/std2) and
**counts** from the baked data. No timing.

## How a capture is made
- `tools/engine/room_capture.sh build` builds the old game's capture image from this tree: the release recipe of
  `tools/d367/test15/t15-build.sh` plus `M1_FRAME_CAPTURE=3` (`engine/bench/r3_capture.hpp`, `r3_guest.inc`,
  `r3_inputs.inc`) and the warp rig (`DBG_WARP=1`), objects in RAM. `room_capture.sh disc` stages its disc from the
  pristine disc tree by hard links, `/dc/warp.txt` redirected into track01.
- `tools/engine/room_capture.py <room> <slot> --warp <file> --out <dir>` (Windows) leases the slot, runs Flycast on an
  inactive desktop, arms the capture and writes 300 consecutive LOG3 pictures (room, sequence, tick), Leon's cloth
  binds, a 16 MB RAM snapshot, the props (`extra-models.json`, `models.json`), one still and `receipt.json` (every
  file's size and SHA-256, the room, the warp text, the image hash, the tree commit, the first tick).
- Props: every live ObjMgr model that is not SMD scenery (cModel kindid 2, already in the world) and every live EmMgr
  model that is not Leon or a Ganado, whose every texture carries a tex.pak key of a PS2 package. Instances drawing the
  same ModelData share one catalogue template. The village and farm recordings took only the props drawn in the first
  picture; this takes the room's whole live set.
- In this image `cManager` and `cUnit` start with their vtable pointer: `pAlive` is at +0x14 and a unit's `be_flag`,
  `pNext` at +4, +8 (`include/cManager.h` gives the GameCube offsets).
- `engine/bench/r3_guest.inc` recorded only r101, r103, r119 and r11d; it now records any stage 1 room (r100-r11f).
  The old game's code is not changed; this is the capture hook's room filter.

## Checks and their failing inputs (`bake/room_bake.py --controls`)
Seven rows, all "failed as it must" (`E:\RE4DC-Lanes\eng-rec1\packs\ctl\controls.json`): the five of lane eng-bake1
and two new:

| Check | Failing input | How it failed |
|---|---|---|
| capture from the wrong room | r100 baked from r106's capture | `logic discontinuity in .../r106/picture-001.bin` (LOG3 room differs) |
| capture receipt | r106's receipt with picture 150's hash changed | `picture-150.bin does not match its receipt` |

`room_bake.py` refuses a lane capture without a receipt naming its room and 300 pictures, or with any file changed.

## How many pictures a capture needs
The engine images keep frame 0 of a recording (lane eng-load2, NAT3 version 5). The bake still reads 300 pictures:
`native_pack.build` refuses fewer, the bench plays all 300, and the game pack's visibility table is grown from the
recorded cameras. So a capture is 300 pictures today; a one-picture capture (plus the snapshot and binds) would do
once `native_pack.py` (not this lane's) accepts it, since the offline seeds alone cover every recorded camera of
every room that has both. The three older recordings cannot be cut until then.

## What could come from the room's files offline (a result, not done)
| Item | Offline? |
|---|---|
| Props | Yes in principle: the room's object tables place them and the room archive holds their models; no converter exists in `bake/`. |
| Lights | Partly: the LIT gives each cut's static lights; the recorded set is larger (effect lights). |
| Environment | Fog and ambient are in the LIT; the light record as a whole (volume, masks, room status) is recorded. |
| Effect placements | Partly: the room's effect tables place the static ones; the recording has those alive at the tick. |
| Leon's bind pose | Yes: Leon's model data; the capture's `leon-bind.bin` is byte-identical to the village recording's. |
| HUD sizes | Yes: the same widget table in every room; one table would serve all. |

## Old-port parts considered
- The capture hook (`engine/bench/r3_*`) and eng-e0b/eng-e1d's collectors: taken as the method (edge tooling), the
  collector rewritten as one tool for every room with a lease, a receipt and a room check.
- The warp rig (`tools/d367/warp.py`): used as it is; four rooms have no preset and use door entry points.
- Nothing enters an engine image. No stubs. No original unit linked.

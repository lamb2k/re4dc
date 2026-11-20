# Lane eng-svc4: retire the remaining original service units (E1 audit section 1)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-svc4\HANDBACK.md`. PC-only (re4ref); no timing, no
emulator, no console. Write-up: `SERVICES.md` sections 23 to 31.

## Result

| Brief step | Result |
|---|---|
| 1. Allowed list and link check | `engine/game/allowed_original.txt`, `tools/engine/check_link.py` (+ `check_link_controls.sh`). Today: default image FAIL, 241 service functions (54,300 B); FIGHT=1 FAIL, 843 (381,008 B); BOSS=1 FAIL, 471 (151,392 B). The image does not link the new services yet (lane eng-e1e). |
| 2.1 Actor volumes (atariInfo, at_mod, at_sub) | native, `services/volumes` |
| 2.2 Collision response (atari) | native, `services/collision/col_model.cpp`, the managers included |
| 2.3 Routes (route_ck) | native, `services/routes` |
| 2.4 Root-motion follower (cMotBase) | native, `services/motion/follow.cpp` |
| 2.5 Model parts (model) | native, `services/model` (+ the record pools, `pool.h`) |
| 2.6 Camera, frustum, Hermite tracks | native, `services/camera` (view, camera, cam_motion, HermiteInterpolation; split: cam_ctrl, cam_sys, cam_extra) |
| 2.7 Pad and rumble (pad) | native, `services/input` |
| 2.8 Math helpers (math_sub, sub2) | **not done** |
| 2.9 Garment pose (pl_cloth) | **not done** |
| 2.10 SDK math and the allocator (+ fdlibm) | **not done** |
| 3. Rumble on the engine generator | done with 2.7: random strength from `eng_pres_u8` |
| 4. Strict plays-right reader | **not done** (a draft is in the evidence folder, `s/p_strict.py`, not in git) |
| 5. Documents | `SERVICES.md` sections 23 to 31 for the services above; `PLAYS_RIGHT.md` not changed (item 4) |

re4ref native link: 0 original functions kept in at_mod, at_sub, atariInfo, atari, route_ck, cMotBase, model, view,
camera, cam_motion, motion, pad, and in the named functions of cam_ctrl, cam_sys, cam_extra (`svc4_units.sh`).
`svc_controls.sh`: 70 rows, 70 as they must (`E:\RE4DC-Lanes\eng-svc4\ev\ctl-final.md`).

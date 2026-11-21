# Lane eng-e1g: pace on the display, finish the unbuilt work (2026-11-20)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1g\HANDBACK.md`. Every emulator number is
**Flycast** (standard harness slots, function checks); PC numbers are re4ref. No timing claim.

| Brief item | Result |
|---|---|
| 1. Pace on the display's field count | The pacer waits on the vblank handler's field count; pictures are released on a fixed field (KOS manual flip, one picture of latency). Intervals over two fields per 600, no late picture: village 5 -> 0, hill 3 -> 0, fight 29 -> 0, boss (headless) 0 -> 0 |
| 2. Engine pad clamp | The input service clamps stick and trigger (the SDK's regions) on every image's pad path; PADCLAMP boot option gone. Village route against re4ref: 641 of 641 ticks bit-identical with no option |
| 3. Native aim | `services/aim/aim.cpp` in every image; original GetWepTargetPos and emLineAtCk2 out of FIGHT / BOSS. PC check: every call's answer equal; why a shot changed nothing in the reference found and worked round |
| 4. SDK math, allocator, float library | sdktest and alloctest bit-identical; newlib's float functions not bit-identical, judged by outcome: PASS on eight fixtures |
| 5. Link into the image | Default 98 -> 8, FIGHT 202 -> 118, BOSS 152 -> 67 SERVICE functions |
| 6. Allowed list | drawLaserSight allowed (H-014.3); default 8 -> 6, FIGHT 118 -> 116, BOSS 67 -> 65 |
| 7. Docs | SERVICES.md 32-40, PLAYS_RIGHT.md outcome reader, lanes/eng-svc5.md, this note |
| 8. Skinning palette, HUD | not done |

## 1. Presentation on the display's field count

- `core/frame.cpp e1_pace_end`: each tick's target is two fields after the last (the first from the field boundary
  `e1_fields_start` returns on). A tick that ends after its target field began is late: no wait, the next target is two
  fields from then.
- The pacer alone (commit d41199fa5, Flycast disc t1) left 3-field gaps with no late picture: hill 3, fight 1. A picture
  whose CPU work ends in time but whose render ends after the boundary was flipped a field late.
- `core/draw_e1.c`: KOS's manual flip holds each rendered picture; the pacer queues its release field (the next tick's
  second field), and the E1 vblank handler, which runs after KOS's own (list order), releases it when that field begins,
  so KOS flips it at the next. The chip renders picture k while the CPU runs tick k + 1. Headless images and the lab
  arm keep KOS's automatic flip.
- Row table: the `wait` column is still the pacer's wait, from the end of the picture's submission (after the LATEPIC
  hold) to the target field; 0 means late. Busy (frame less wait and PVR wait) and the late count read as before.
- Controls (Flycast): LATEPIC (picture 300 held 100 ms) shows one long interval at picture 300 (6 or 7 fields) in every
  scene, late 1; the lab arm PACETMU (the 33,367 us timer pacer, boot option) shows the gaps again: village 3, hill 4,
  fight 27.

| Scene (Flycast) | Before (eng-e1f t1) | Pacer only (t1) | Fixed field (t2) | LATEPIC (late2) | PACETMU (tmu2) |
|---|---:|---:|---:|---:|---:|
| Leon, village | 5 | 0 | 0 | 1, worst 6 @300 | 3 |
| Leon and Ashley, hill | 3 | 3 | 0 | 1, worst 7 @300 | 4 |
| Four-Ganado fight | 29 | 1 | 0 | 1, worst 7 @300 | 27 |
| El Gigante hosted (tick) | 0 | 0 | 0 | 1, worst 6 @300 | 0 |

## 2. Pad clamp

SERVICES.md section 40. Control: the test build `PAD_EXTRA=-DE1_PAD_NOCLAMP=1` splits from the reference at tick 424.

## 3. Native aim

SERVICES.md section 39. On the engine image (Flycast, disc a1): village 93 calls (scenery), fight 333 (67 on a Ganado's
boxes), boss 93 (52 on El Gigante's); the village trace still PASSes 641 of 641 against re4ref; the fight's events are
unchanged (spawn 4, hit 5, kill 0). Not done: a shot fixture on the default image (the village has no enemy; the
default image stubs GetWepTargetList2, so a shot hits nothing there).

## 4 and 5. Round 5 in the image

SERVICES.md sections 35-38. svc5_units.sh on re4ref native: 0 original functions kept of math_sub, sub2, pl_cloth and
the five SDK units; control (the census map) 22 kept.

The round-5 image on the SH-4 (Flycast, disc f1, newlib's float functions, sdk_math, the native heap): the village
route's trace still PASSes 641 of 641 ticks bit-identical against re4ref; the fight's events are unchanged (spawn 4,
hit 5, kill 0); every scene's heap map PASSes and E1 HEAPSVC shows 0 bad frees and 0 overlaps; the HEAPCK exercise
PASSes. Control HEAPBAD (disc f1ctl: heap 0 over the whole arena): the map FAILs, the exercise FAILs, and the native
heap counts 1 overlap and refuses 4 frees. (f1 runs with traces on: the hill's trace flush inside the run shows as one
993-field interval; the timing discs run with NOTRACE.)

## Link check, SERVICE functions per image

| Image | origin/engine 31860a307 | + aim | + round 5 | + allowed list |
|---|---:|---:|---:|---:|
| default | 98 | 98 | 8 | 6 |
| FIGHT=1 | 204 | 202 | 118 | 116 |
| BOSS=1 | 154 | 152 | 67 | 65 |
| default SENDABLE=1 | 98 | 98 | 8 | 6 |

Still offenders in the default image: drawPoint and Draw_line3d_local_222 (laser drawing), cManager<cLight> (pl_npc),
cManager<cEm>::createBack and cEmMgr::memClear (pl_sub).

## Machine notes

- The WSL distro stops when no session is open, and `/dev/shm` is emptied with it: the lane kept a `sleep` session open
  while its builds lived in RAM.
- Symbols in SH-ELF objects carry a leading underscore (`_GetWepTargetPos`): eng-e1f's draft weakened the C name, and
  the FIGHT image did not link until that was fixed.

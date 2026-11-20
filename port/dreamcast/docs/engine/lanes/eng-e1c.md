# eng-e1c hand-back (E1: the Leon image on the native skeleton and collision), 2026-11-19

Lane `eng-e1c` on `lane/eng-e1c` from `origin/engine` 760c2e118, merged `origin/engine` 28189e752 (eng-e1b: Ashley,
the hill scene) before the baseline. Tiers: **Flycast** = guest timer, standard harness Flycast (std slots), 600
pictures 41-640 (the hosted boss: 900 headless ticks); **MODELLED** = nominal 200 MHz SH-4 hwsim over a Flycast
hwtrace (fly slots), 25 pictures 41..617 step 24. No console number. Evidence: `E:\RE4DC-Lanes\eng-e1c` (runs, build, s).

## 1. What changed in the image

| Item | Before (first form) | After |
|---|---|---|
| Skeleton | motion.cpp, model.cpp parts half, ik.cpp, at_pos_calc (original units) | `services/skeleton` (skel.cpp, skel_xm.c on SH4ZAM XMTRX); motion/model/atari built with the replaced functions weakened (svc.mk lists), `--gc-sections` drops the originals (map checked: every replaced function is linked from `n/skel.o` or `n/col.o`); ik.cpp not linked |
| Collision cores | atari.cpp hitCheck2 / hitCheck / polySphereCk | `services/collision` col.cpp; `col_bake_all()` at room load (village 2 pieces, 369,728 B; hill 231,392 B; boss 8 bakes, 6 late, 251,840 B) |
| Cloth (pl_cloth.cpp, pendulum.cpp) | original | **not linked: logged stubs** (owner 11-19: no original service code); cloth bones keep their animated pose; the stub keeps the cloth's one state effect (be_flag 0x00E00000 cleared) |
| Shape keys (shape.cpp) | original | not linked: logged stubs (the engine draws no shape keys) |
| Memory | KOS heap / arena | fixed services region 0x8cec0000-0x8cfc0000 (top 1 MB of the old arena; arena now 2.75 MB, high water 170-465 KB): skeleton pool 256 KB (Leon + handgun 52,384 B; + Ashley 110,784 B; boss 11 tables 99,872 B) + collision tables |
| Palette | drawing multiplied world x pack bind | `skel_publish_all()` once a tick after the behaviour (services row); the renderer copies `pal[k]`; checked once: pack bind = table bind on all 41 bones used |
| Renderer, trace | cParts records in place | the table's world records and palette (`services/e1_skel_view.h`); Ashley's marks from her table; `pm` digests the table |
| Check build | - | boot option `SKELCHECK` (skel_poison: NaN in every unserved record field); release default 0 |
| Random numbers | one shared generator | presentation functions (eye wander, aim sway `PlWepLockRand`, camera sway and look-at, cartridge, water shot, damage voice, Ashley's face) placed in section `e1_present` by objcopy; their draws come from an engine generator, Rnd serves the behaviour only. Diagnostic arm `PSEED` |
| Accounting | 17 wrapped entry points | every service entry point the behaviour can call, grouped (motion, cloth, parts and palette, collision), per tick in ROW; MODELLED service stamps (`e1_svc_stamp`). Found: the old Rnd wrap never applied (C linkage), cSatMgr::check's wrap dropped its int |

**Original units still linked** (no native service; a stub would change gameplay): cMotBase (root motion follower),
atariInfo / at_mod / at_sub (actor volumes, capsules: pushes and hits between characters), route_ck (Ashley's follow;
boss image too), obj20 (boss: scroll-object collision); kept parts of model.cpp (allocation, 5.2 KB), motion.cpp (key
decoder, clock, root motion, 3.9 KB), atari.cpp (check / getFloor / wallAdjust above the native cores, 4.7 KB); pad,
math_sub, sub2. Effects: the boss image's effect service is engine code (first form, records).

## 2. Budget rows (ms a picture; budget behaviour 2, services 9, drawing 14, system 3.5, busy 33.3)

| Scene, tier | Behaviour | Services (motion / cloth / parts+palette / collision) | Drawing | System | Busy mean / p99 / worst | Services over 9 |
|---|---|---|---|---|---|---|
| Village, Flycast, before | 0.18 | 4.81 / p99 5.99 / w 8.43 (2.18 / 1.56 / 0.75 / 0.32) | 10.83 / 12.95 / 12.98 | 0.12 | 15.93 / 20.68 / 23.59 | 0 |
| Village, Flycast, after | 0.18 | **2.33** / 4.19 / 4.89 (1.49 / 0.00 / 0.57 / 0.26) | 10.83 / 14.25 / 15.03 | 0.13 | **13.47** / 18.08 / 23.46 | 0 |
| Village, MODELLED, before | 0.30 | 6.85 / 8.35 (3.19 / 2.02 / 1.20 / 0.45) | 14.03 / 16.69 | 0.04 | 21.21 / 23.52 / 23.52 | 0 |
| Village, MODELLED, after | 0.30 | **3.08** / 4.16 (1.86 / 0.01 / 0.82 / 0.39) | 14.50 / 17.08 | 0.04 | **17.92** / 20.38 / 20.38 | 0 |
| Hill, Flycast, before | 0.20 | 12.29 / 14.38 / 15.97 (4.90 / 5.34 / 1.37 / 0.68) | 7.35 / 8.63 / 9.12 | 0.04 | 19.87 / 23.76 / 27.12 | 600 / 600 |
| Hill, Flycast, after | 0.24 | **5.10** / 6.64 / 7.88 (3.50 / 0.00 / 1.08 / 0.51) | 7.31 / 11.04 / 11.11 | 0.03 | **12.67** / 16.72 / 19.97 | 0 |
| Hill, MODELLED, before | 0.42 | 17.53 / 19.38 (7.34 / 6.94 / 2.28 / 0.97) | 9.64 / 11.07 | 0.04 | 27.63 / 30.91 / 30.91 | 25 / 25 |
| Hill, MODELLED, after | 0.43 | **6.80** / 8.06 (4.44 / 0.01 / 1.54 / 0.80) | 10.16 / 11.59 | 0.04 | **17.42** / 20.12 / 20.12 | 0 |

- **Native services alone** (cloth taken out of both sides): MODELLED village 4.83 -> 3.07 ms, hill 10.59 -> 6.78 ms;
  Flycast village 3.25 -> 2.33, hill 6.95 -> 5.09. Parts+palette now includes the palette (Flycast 0.08 ms village,
  0.18 hill). Cloth removal is the rest (2.0 / 6.9 ms MODELLED).
- **Drawing:** the palette copy replaces the multiplication, but MODELLED drawing rose 0.47 (village) / 0.52 (hill):
  per function (village), actor strip emission +0.34 and weight-set build +0.10 (the unswung cloth pose changes which
  jacket parts are drawn and clipped), block copies +0.12 (the palette copy). Flycast drawing mean equal (10.83); its p99 moved because a
  periodic 2.5 ms event (every 30 pictures, in both images) now lands in drawing on pictures 49..259.
- Behaviour worst pictures (Flycast 4.9-6.1 ms) are first-call stub log lines on serial (4 per stub name), both images.
- Half-budget rule (no console number yet): village services 3.08 MODELLED fits half its row (4.5); hill 6.80 does
  not; busy 17.9 / 17.4 MODELLED is just over half of 33.3.

## 3. Plays right (gameplay equivalence + position 1 unit, angle 1 degree; generator state not compared)

| Check | Result |
|---|---|
| Leon, village, vs the old game (`ref-route-4`, eng-e1's `plays_right.py`) | Mot_frame, Mot_state exact 641/641; angle 641/641 (worst 0.197 deg); position 525/641 within (ticks 0-524), worst 4.19 units from tick 525; pf digest (model coordinates) bit-identical ticks 0-484, as before the switch |
| Cause of the drift after the aim (tick 485) | aim sway is presentation randomness now (engine generator). Arm `PSEED` (only the presentation generator's start changed) against the default engine: identical to tick 484, then 7.5 units apart: the drift is the sway, not the services. Before the switch: 539 / 1.35 (the old shared generator) |
| Ashley and Leon, hill, engine vs re4ref, FEED (`hill-follow-feed`) | **every field 729/729, bit-identical** (p, a, mid, mf, ms, r, hp, be, f, aps; Leon p, a, mid, mf, ms, r, ps) |
| Same vs the old game, FEED + RESUMEA (`fx-hill-1`) | Leon 728/728 every field, bit-identical; Ashley p 728/728 (0.0117), a 728/728, r 728/728, hp, be 728/728, mf 679/728 (resume), as before |
| Hill, no feed, vs re4ref | Ashley's routine from tick 61 (before: 361): her idle timer is a behaviour draw; re4ref's shared generator still takes the presentation draws (eye wander) the engine now gives to its own generator. re4ref needs the same split to compare without a feed |
| Check build (`SKELCHECK`), village and hill | lost writes 0, parent mismatches 0 (123 / 264 records poisoned); traces identical to the release image |
| Determinism | village trace identical over four runs (images n2 and n4, the check build, the staged disc); hill identical (FEED run and its check build) |
| Control CTRLSPD (motion speed 0.97) | FAILS: state at tick 75, angle at 204 |

## 4. El Gigante (`make BOSS=1`, headless, 900 ticks, vs eng-boss `ref-fight2`, engine k = reference 184 + k)

| Check | Before (first form) | After (native) |
|---|---|---|
| Builds | yes | yes (+ pendulum stubs for the loincloth and ropes) |
| Boss routine changes, kind and tick exact | 8 of 10 (first difference 868) | 7 of 10 (0, 109, 166, 317, 483, 513, 764; 794 picks 0x11 for 0x09) |
| Boss stat / Mot_frame exact | to 867 / 868 | to 793 / 839 |
| Boss position within 1 unit | 0-484 | 0-391 |
| Hut C destroyed | tick 371 | tick 371 |
| Leon position within 1 unit / routine | 0-129 / to 377 | 0-125 / to 474 |
| Native vs first form, same fixture | | Leon bit-identical (pf) to tick 116, El Gigante to 371; the `PSEED` arm alone gives the same first differences (Leon 117, boss 372 / 374): the presentation generator moves Leon (aim sway, 5 units by 371) and El Gigante turns toward him |

Budget rows of the hosted fight (Flycast, headless, 900 ticks; before / after): behaviour 0.56 / 0.58 mean (worst 14.84
both, the hut break); services 6.00 / **4.48** mean, p99 9.10 / 7.13, worst 11.70 / 9.34, over 9: 11 / 3 (motion
3.82 / 2.93, cloth 0.45 / 0.02, parts+palette 1.07 / 0.95, collision 0.67 / 0.58); busy 6.60 / **5.09** mean, worst
20.85 / 19.65. Arena high water 464,576 B, 0 failures, both.

## 5. Staged disc

`E:\RE4DC-Lanes\eng-e1c\build\E1C-GDEMU-native` (KEEP, SHA256SUMS, SHA256SUMS.boot, disc_lint standard PASS; no boot
option: the village route with its trace and report on serial; boot options HILL, NOTRACE, SKELCHECK, PSEED, CTRLSPD
are empty root files). Booted in Flycast (`runs\staged-native`): trace identical to the image's.

## 6. Not done

- Native cloth (Leon, Ashley, El Gigante): stubbed; look change (cloth does not swing) not shown to the owner as a still
  pair; base vs native stills (Flycast) differ by MAE 0.1-0.5 before the aim, 2-9 during and after it (camera sway).
- Native actor volumes, capsules, route checks, root motion, scroll-object collision: still original (section 1).
- re4ref with the presentation split (no-feed comparison of random-driven idle choices); re4ref with pendulum under the
  check build (the pendulum is no longer in the image).
- MODELLED rows of the hosted boss (headless image: no picture marker); console run.
- Offline key conversion, updateOldPos copying every bone's history (SERVICES.md section 9).

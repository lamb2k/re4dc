# eng-e1d hand-back (E1 finish: Leon and Ashley on the engine with native services only), 2026-11-20

Lane `eng-e1d` on `lane/eng-e1d` from `origin/engine` 7869ba2ff; merged `origin/engine` d12109859 (eng-svc3, services
round 3) on the integrator's note. Tiers: **Flycast** = guest timer, standard harness Flycast (std slots), 600 pictures
41-640; **MODELLED** = nominal 200 MHz SH-4 hwsim over a Flycast hwtrace (fly slot), 25 pictures 41..617 step 24;
**PC** = re4ref. No console number. Evidence: `E:\RE4DC-Lanes\eng-e1d` (runs, build, evidence, s).

## 1. Aim sway is behaviour

- `PlWepLockRand` left the presentation section (`game/Makefile` PRESENT_game/pl_wep): it draws from the original
  generator again. Eye wander, camera sway (scope, look-at), water shot, cartridge, damage voice and the partner's
  face stay on the engine generator; the cloth joined them (section 2).
- **Village vs the old game (`ref-route-4`), no feed:** Mot_frame, Mot_state 641/641, angle 641/641 (0.241 deg);
  position within 1 unit ticks 0-522, then up to 5.12 units. Not past 524.
- **Why, tested:** the engine's generator carries only Leon's 270 behaviour draws over the route; the old game's
  is advanced about 205 times a tick by the rest of the village (held-away Ganados, effects), so the sway draws other
  values. With FEED (new: the boot option works in the village scene; `FEED-vil.BIN` = the old run's generator state
  at the start of each tick) every field is within on all 641 ticks, worst 0.001 unit. The remaining divergence is
  the generator state the old game's other code leaves, not the hosting. It closes when E2 hosts the village's
  other drawers, or with the feed.
- Control CTRLSPD (motion speed 0.97) still fails: position at tick 49, state at 75, angle at 204.

## 2. Native cloth

- Round 3 (eng-svc3, merged on the integrator's note): `services/cloth/cloth.cpp` + `cloth_kernel.c` (SH4ZAM, no
  libm) linked in the E1 image (`game/Makefile` NATIVE_OBJS, not in the boss image). The presentation generator behind
  `pres_rng.h` is the engine's: `host/e1_pres_rng.h` is force-included (same guard, same four functions) and draws from
  `e1_pres_u32` (host/e1_wraps.cpp).
- `pl_cloth.cpp` (the behaviour's side: chain set-up and the PenCloth* calls) is hosted. **`pendulum.cpp` is not
  linked**: the wind globals (`GlobalWind`, `GlobalWindAdd`) are engine data at the original's start values (no room
  wind setter is hosted); the service's fallback (`pen_orig_*`) is a logged stub, never hit; `PenClothMove2` (enemy
  flails) has no caller here. The boss image keeps its cloth stubs.
- Leon's jacket, holster and hair and Ashley's hair, skirt and sweater swing again (5 chains in the hill scene).
- **Motion check** (`CLOTHSTAT` boot option, `s/clothcmp.py`): per chain the mean horizontal distance of its links
  from bone 0 over the run, per link the mean offset, from the engine's skeleton tables on Flycast, against re4ref's
  original cloth (odump build, pendulum.cpp, wind on) on the same fixture. Bounds of round 2: radius 0.4, means 2.

| Scene | Chains | Radius difference, worst | Link mean difference, worst | Verdict |
|---|---|---|---|---|
| Hill (hill-follow, 728 ticks), Flycast vs PC original | 5 | 0.017 | 0.385 | PASS |
| Village (e1-route, 640 ticks), Flycast vs PC original | 2 | 0.228 | 1.149 | PASS |
| Control CLOTHCTL (gravity off), hill | 5 | 1.529 | 31.36 | FAIL, as it must |

- Still pairs: `E:\RE4DC-Lanes\eng-e1d\evidence\stills\cloth-ashley-280.png` (Ashley's hair, sweater, skirt) and
  `cloth-leon-280.png`, old game (Flycast capture) against the engine at the same tick.

## 3. Ashley drawn, the hill path baked

- **Capture:** an r3 capture of r11d by the old game (`bench/r3_guest.inc` accepts 0x11d; eng-boss's capture build
  with LOGIC_TRACE; fx-hill warp, 300 pictures from t=412: streams, stills, trace; `runs\cap-hill`).
- **Pack** (`bake/hill_pack.py`, HILL.PAK 7.75 MB): r11d's whole-room world from the PS2 sidecars as the village
  (native_pack.py), the capture's lights, fog and HUD; Leon in the chapter-2 costume (pl08 roles 0, 1 and its extra
  chunk over pl00 with eng-look's hair); **Ashley at catalogue 6** from her PS2 cast package (`bake/ashley_model.py`,
  dc/native/r11d/partner.re4nmr: 141 source joints = her native table's bones, the 64 skin slots mapped to their
  joints, 263 weight sets, 2,975 positions, 4,925 triangles, one atlas). Visibility HILL.VIS (bench/bake_vis, 48 eyes,
  150 mm, erode: 1,041 cells, 125,208 B).
- **Drawing:** the hill scene opens HILL.PAK; Ashley goes through the E1 actor pass (one slot per character; her
  palette check: 64 of 64 bones equal the table's bind, the skeleton's palette used). Leon's hair as the bench draws
  it since eng-look (role 7 opaque, role-8 hair run in the translucent list).
- **Still pairs** (old game | engine, Flycast, FEED + RESUMEA): `evidence\stills\hill-pair-{200,240,280,320}.png`;
  MAE 18.6 / 12.5 / 12.6 / 13.7 RGB levels. Same people in the same places and poses. Differences: the camera (its
  state is not carried by the resume: lower and closer until about tick 200, a few degrees off after), barrels and
  props (objects not drawn in E1), the ground light pool (an effect), the HUD's partner portrait and ammo digits,
  the handgun (not in any pack), and Leon's chapter-2 body, which reads browner than the old game's (PS2 pl08 chunks
  over the pl00 atlas: an owner look call).
- **Visibility check:** culled against full (`NOVIS`) at the 19 still pictures: 0 pictures differ (any channel > 9).
  Control (bake_vis `--control`, the 60 most-seen instances hidden in 4 route cells): 16 of 19 differ.

## 4. re4ref split

- `hostref/host_present.cpp` + Makefile: the same presentation functions moved to section `re4ref_present`, Rnd /
  fRand0_1 / fRand1_1 wrapped; their draws come from a generator with the engine's algorithm and start. Linked with
  `-z start-stop-gc` like the engine. `RE4_PRESENT_SPLIT=0` is the control.
- The engine's hill scene now starts its generator at the fixture's seed 0x0d37, as re4ref does (it started at 0:
  that, not the presentation draws, made Ashley's routine differ from tick 61 before).

| Hill (729 ticks) | Leon | Ashley |
|---|---|---|
| engine vs re4ref split, **no feed** | every field 729/729 | every field 729/729 |
| control: re4ref without the split | 729/729 | routine from tick 367 (her face's draws shift her idle timer) |
| engine vs re4ref split, FEED | every field 729/729 | every field 729/729 |
| engine vs old game, FEED + RESUMEA | every field 728/728 | p, a, r, hp, be 728/728; mf 679/728 (resume), aps 727 |

Still differing: generator state against the old game (it is fed or compared to re4ref), and the camera at the resume.

## 5. Budget rows (ms a picture: mean / p99 / worst; services = motion / cloth / parts+palette / collision)

Before = eng-e1c's final image (this branch's start). After = image c10 (Flycast) and c9 (MODELLED; c10 adds only a
pack-name test).

| Scene, tier | Services | Split | Drawing | Busy | Over budget |
|---|---|---|---|---|---|
| Village Flycast before | 2.33 / 4.19 / 4.89 | 1.49 / 0.00 / 0.57 / 0.26 | 10.83 / 14.25 / 15.03 | 13.47 / 18.08 / 23.46 | svc 0 |
| Village Flycast after | 3.28 / 5.47 / 7.84 | 1.50 / 0.94 / 0.55 / 0.29 | 10.82 / 12.99 / 14.92 | 14.40 / 19.17 / 21.91 | svc 0, draw 5/600, busy 0 |
| Village MODELLED before | 3.08 / 4.16 | 1.86 / 0.01 / 0.82 / 0.39 | 14.50 / 17.08 | 17.92 / 20.38 | |
| Village MODELLED after | 4.25 / 5.37 | 1.87 / 1.22 / 0.74 / 0.43 | 14.01 / 16.68 | 18.60 / 21.19 | draw 9/25, busy 0 |
| Hill Flycast before | 5.10 / 6.64 / 7.88 | 3.50 / 0.00 / 1.08 / 0.51 | 7.31 / 11.04 / 11.11 (no world) | 12.67 / 16.72 / 19.97 | 0 |
| Hill Flycast after | 8.50 / 11.16 / 11.79 | 3.46 / 3.48 / 1.03 / 0.53 | 14.68 / 16.87 / 18.71 | 23.44 / 27.81 / 30.77 | svc 89/600, draw 222/600, busy 0 |
| Hill MODELLED before | 6.80 / 8.06 | 4.44 / 0.01 / 1.54 / 0.80 | 10.16 / 11.59 (no world) | 17.42 / 20.12 | |
| Hill MODELLED after | 10.91 / 12.20 | 4.50 / 4.23 / 1.39 / 0.80 | 19.15 / 22.10 | **30.53 / 34.76** | svc 25/25, draw 25/25, **busy 3/25** |

Behaviour 0.18-0.43, publication 0, system 0.04-0.13. What moved: the cloth (village 0.94 Flycast / 1.22 MODELLED;
hill 3.48 / 4.23, Ashley about 2.5 of it) and, in the hill, the world and Ashley's mesh (+7.4 ms Flycast, +9.0
MODELLED drawing). The hill misses its services and drawing rows on the model and its busy picture on 3 of 25: the
first scene that needs the content steps (character levels for Ashley, world cap) and the cloth's cost cut.

Memory (Flycast, hill): pack resident 6.6 MB, free to the arena 540,672 B, arena high water 300,736 B, collision tables
272,800 B, overlaps 0. Village: collision tables 470,240 B (round 3 grid), free 860,160 B.

## 6. Staged disc

`E:\RE4DC-Lanes\eng-e1d\build\E1D-GDEMU-both` (KEEP, SHA256SUMS, SHA256SUMS.boot, disc_lint standard PASS). One disc,
both scenes: the village route by default; **hold A or Start while the program starts** for the hill path (the root
file HILL does the same in test ISOs). Flycast boot of the staged disc: the village trace equals image c8's.

## 7. Not done

- Motion-key packs (RE4MK2, eng-svc3): not wired into the image (clips still read through the native decoder).
- Ashley's mask runs (hair and lash alpha): not baked, drawn opaque; her model light is Leon's record.
- The room's wind (PenWindSet from the light data): not hosted; engine start values.
- Village cloth still pair against the old game: no old-game stills of the village route exist (the hill pairs show
  both characters' cloth). Props, effects, foot shadows, HUD portrait not drawn. Hill over budget on the model.
- Console run.

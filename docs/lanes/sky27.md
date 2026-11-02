# Lane sky27: PS2 sky in normal play (SKY_PLAY=1)

User 2026-11-02, "Yes fix the sky"; pulled into Test 26 ("I want that sky in build 26"). Default off.

Test 26 scope: the Disc 1 route rooms (DATA sky27: r100..r11f + r200). The castle set (D2_DATA sky27c) goes to
Test 27: r201/r202/r203/r208 load and draw, but the warp views show little sky; r206/r20a/r20b/r20d did not reach the
room from a warp (chapter line needed).

## What it does

- Each outdoor room gets a baked PS2 sky panorama (1024x256 VQ, 67,584 B of VRAM, room arena), loaded at room entry
  from `dc/native/rXXX/ps2-sky.r4sk`.
- The panorama is drawn as the PVR background plane (ISP_BACKGND_T/D), so it costs no TA geometry and no CPU per pixel.
  `__wrap_pvr_begin_queued_render` (res_mode.cpp) writes a textured plane in place of KOS's clear colour.
- The plane depth is set to 1/cull_far, so world geometry past the cut is clipped per pixel against the sky (no fog
  silhouettes).
- While the plane is armed, the room's own sky rows are culled (they were drawn fully fogged under look A sky=0 and
  hid the plane). This removes geometry, so the net cost is at or below zero.
- Only in normal play with look A sky=0. Under SKY_EVENT=2 scripted cameras the real rows draw and the plane is off.
  Indoor rooms (no .r4sk) keep the clear colour.

## Data

- Bake: `port/dreamcast/tools/ps2_sky_bake.py` (PS2 world OBJ/TPL + RTP + LIT). Rows are classified by data
  (median triangle area >= 30 m2, reach >= 20 m, vertical span >= 5 m), rendered into 6 cube faces with PS2 fog from
  LIT cut 0 baked in, then resampled equirect (+80..-35 degrees) and VQ encoded. R4SK v2 carries the row list.
- Data sets (t11-fix): `sky27` (Disc 1 rooms + r200), `sky27c` (Disc 2 rooms). Source dir
  /root/re4data/private/sky27-20261102.

## Recipe

Test 26: `CH2 += SKY_PLAY=1`, `DATA += sky27`. Test 27: `D2_DATA += sky27c`. Requires SKY_EVENT=2, PS2_WORLD_ROOMS, RES_MODES,
RENDER_OPTION=1, not RENDER_DOUBLE (post30.mk checks).

## Not covered

- r210..r22c: there is no PS2 world package on Disc 2 for these rooms (room.r4rc only), so there are no rows to replace.
- r102, r10d, r10e, r112 and r204/r205/r207/r209/r20c/r20e/r20f: no sky rows found (indoor, or no RTP data).

## Evidence

C:\Flycast-Evidence\re4-dreamcast\sky27 (runs, sheets, speed, bake).

## Gates (2026-11-02)

- Knob-off identity: image f6f938e659f5a85a = release 15ed29fe, 15/15 overlays identical.
- Cost, MODELLED (SH-4 hw model, rr-speed on 15ed29fe vs 15ed29fe + SKY_PLAY + sky27), work = frame minus main:
  cross 35.88 -> 35.91 (+0.03), farm r103 36.70 -> 35.92 (-0.78), barn 38.30 -> 37.70 (-0.61). The sky functions
  themselves: row check 0.02-0.04 ms, frame setup 0.007 ms, render hook 0.008 ms.
- VRAM: 67,584 B per outdoor room (room arena), loaded at entry; no refusals or no-contiguous-block lines in 29 rooms.
- Cost, GPU (cache-model Flycast, rr-speed-gpu; not console ms): cross SQ->TA -0.6%, TA list -0.6%; farm r103 -0.5% /
  -0.5%. Barn not measured (no fast state for the barn scene). TSP fill of the textured background is not modelled by
  any tool here: it needs the console A/B.
- KOS squeeze 48 KiB: PASS (10/10; fight min headroom 5,896 B, leave100/103 6,096 B).
- Logic: decisions-identical on the r101 cross warp to tick 1500 (discrete and coords identical every tick). The parts
  hashes (pm/em: render-side parts world matrices) differ from frame 216; off vs off is STRICT.

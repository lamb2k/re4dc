# Lane world-ch31 (chapter 3-1 to the chapter-done bar, Test 27)

Branch `lane/world-ch31` from t15/int 15ed29fe; pushed as wip/world-ch31-20261102. Carry list: `C:\Game Dev\Emulators\CH-FIXES-CARRY.md`.

## rr 1102-1750-426089f1 (ON arm: goto switch on, cgca27; lane head 426089f1 = t15/int 799960376 + lane): 37/38 PASS
- Disc 1: all PASS. Disc 2: CAST-GC, LEON-GC, TEXCHK, VRAM no-contig 0, HALT 0, cap 4, KOS 48 KiB (min headroom 31032),
  GDEMU 1 seed: PASS.
- Disc 2 GC-ASSET: r200 r201 r202 r204 r208 clean. r203 went from 13 rows to 4: layout 96e39bd7, GC model 08d57f77, textures
  72be589c and 761e77f9. r207 still has 6: layout dca7d347 and textures 77c1171c, 511673a2, 5224f21f, b894c4b5, 70524d21.
  The textures look like world pack keys, as in r200: next is a cpic27 pack set from r203.dat / r207.dat (em_eff_pics.py
  --pair -, base cpic26c). Its first run was stopped by the host's low-memory reaper while it waited on the lock; not rerun.
- r207 clear rig (d2clear-r207, 180 s): 10 Ganados killed through the source damage path from frame 1000. At most 4 alive at
  once, and held ones came in as others died. Ganados alive 0 from frame 1830 to the end (3660). The two id 0x43 enemies stay.
  rsf stays 86300000 after the kills, so a clear/door flag is not shown.
- The OFF arm has not run (the coordinator stopped it).

## State 11-02 (paused: disk)
- Already on Disc 2 from earlier lanes: PS2_CH3_ENEMY=1 (one knob, all of chapter 3, PS2_ENEMY_CH3_DIR ps2enemy-ch34-20261018/PE3),
  ALIVE_CAP=4, ALIVE_CAP_NOVIS=1, ALIVE_CAP_DEFER_FLAGS=1, ALIVE_CAP_R202_GATE=1; GC-ASSET and CAST-GC PASS (castle-gca-26).
- Added: `D2_EXTRA` (recipe.conf, read by castle31/build-disc2.sh; Disc 2 program only) = `ALIVE_CAP_DEFER_GOTO_R207=1`.
  Held r207 hall Ganados keep the room code's walk-upstairs command (8bab3d5b9). Off, they were released standing (mode 0).
- rr cycle 1102-0904-8b49d9dc (quick, RR_DISC2=1): FAIL 6/37. C: dropped to 16.8 GB during the cycle ("C: too full for 891 MB"),
  and Disc 1 KOS/GDEMU failed too, although its program and data are unchanged. Disc 2 r204 census log empty, r208 cut short.
  Disc 2 CAST-GC PASS. r207 enters (alive 3 + 2 non-cap ids at frame 60). These are not a valid gate.
- Cap and park (coordinator 11-02): chapter 3 stays hold-only, a documented cap exception, because the room code keeps
  pointers to the enemies it sends. A per-room parking design is needed only if a room deadlocks under hold.
- Route plan note: the bot needs to use the stairs and heal in the r207 hall. That is for the later play-through, not this lane.

## r207 finding (so far)
- castle-disc2-26's no-warp bot stands on the ground floor at (1191, -2650) and shoots ("fight 25 9000") while 4 Ganados
  close in. Its life goes 965 -> 490 -> 0, with shots 21 then 0. The bot does not retreat, heal or use the stairs.
- With cap 4 and the goto switch off, the held D4/D5 come in without their upstairs walk. That changes the fight's shape
  but not its counts.
- Next: run w31-r207-fight (castle31/warps, god + stock) on both arms; done when the kill count reaches the room clear and
  the doors open.

## Play-through prep
- Start: VMU `castle31/vmu/handoff-ch23end-A1.bin` + `warps/d2-fastload-pad.txt` (Disc 2 boot, load the 2-3 end save).
- Route: `warps/plan31-steer.txt` (r200 -> r202 -> r207, keys A/B). Room presets: a-r200 b-r202 c-r207 d-r203 e-r201 f-r208 g-r204(b).
- End: r204 chapter end (g-r204 / end-pad.txt).

## Gates 11-03 (lane head 5b8537f1 = t15/int 7ec95b326 + lane; logs D:\RE4DC-Lanes\world-ch31\rr and \rroff)
- Disc 1 identity: image eec23ce1925ac9b2 = t15/int base cycle 1103-0015-7ec95b32 (same program; DATA line untouched).
- OFF arm 1103-0338 (D2_EXTRA empty): 37/38. Only Disc 2 GC-ASSET fails, 9 rows:
  - r203: layout 96e39bd7, GC model 08d57f77 (record 2003104; likely item itm57, which has no PS2 twin in r203.dat),
    texture 72be589c;
  - r207: layout dca7d347, textures 77c1171c, 511673a2, 5224f21f, b894c4b5, 70524d21.
  - The textures have no unique PS2 picture in r203.dat / r207.dat: NCC ties on flat pictures, MAE >= 19. 761e77f9 is
    fixed by cpic27 (r203.dat TPL 67t, NCC 1.000). r203 / r207 have no room BINs on either side, so there are no pairs.
- ON arm 1103-0531 (goto switch on): verdict PASS 38/38, but the Disc 2 GC-ASSET gate twin was not built ("C: too full for
  891 MB, floor 16 GiB" in the d2a base step, with C: at 17 GB) and the judge reported no row for it. The data equals OFF,
  so OFF's 9 rows stand.
- Both arms, Disc 2: CAST-GC, LEON-GC, TEXCHK, VRAM no-contig 0, HALT 0, cap 4 (r200=4 r201=1 r202=4 r203=4 r204=0
  r207=3 r208=4), KOS 48 KiB, GDEMU 1 seed: PASS.
- r207 clear rig: ON killed 10 Ganados, OFF 8. Both reach 0 Ganados alive (ON frame 1830, OFF ~1800), with at most 4 alive.
  With the switch off, 2 held hall Ganados never come into play. rsf 86300000 does not change after the last kill, so the
  rig cannot show a clear/door flag.

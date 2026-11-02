# Lane world-ch31 (chapter 3-1 to the chapter-done bar, Test 27)

Branch `lane/world-ch31` from t15/int 15ed29fe; pushed as wip/world-ch31-20261102. Carry list: `C:\Game Dev\Emulators\CH-FIXES-CARRY.md`.

## State 11-02 (paused: disk)
- Already on Disc 2 from earlier lanes: PS2_CH3_ENEMY=1 (one knob, all of chapter 3, PS2_ENEMY_CH3_DIR ps2enemy-ch34-20261018/PE3),
  ALIVE_CAP=4, ALIVE_CAP_NOVIS=1, ALIVE_CAP_DEFER_FLAGS=1, ALIVE_CAP_R202_GATE=1; GC-ASSET and CAST-GC PASS (castle-gca-26).
- Added: `D2_EXTRA` (recipe.conf, read by castle31/build-disc2.sh; Disc 2 program only) = `ALIVE_CAP_DEFER_GOTO_R207=1`.
  Held r207 hall Ganados keep the room code's walk-upstairs command (8bab3d5b9). Off, they were released standing (mode 0).
- rr cycle 1102-0904-8b49d9dc (quick, RR_DISC2=1): FAIL 6/37. C: dropped to 16.8 GB during the cycle ("C: too full for 891 MB"),
  and Disc 1 KOS/GDEMU failed too, although its program and data are unchanged. Disc 2 r204 census log empty, r208 cut short.
  Disc 2 CAST-GC PASS. r207 enters (alive 3 + 2 non-cap ids at frame 60). These are not a valid gate.
- Cap and park: chapter 3 rooms hold only. The Makefile says ALIVE_CAP_PARK is not used because their room code keeps wrap
  pointers of its sends. Parking them would need a design decision.

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

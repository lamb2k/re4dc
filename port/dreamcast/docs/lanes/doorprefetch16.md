# Lane doorprefetch16 (2026-10-16): next room's reads during the door sound / music hand-over

User 10-16: "Start the next room's reads while the door sound and music hand over." Base t15/int 439304e6. WIP, PAUSED
(usage limit), not gate-clean. Evidence C:\Flycast-Evidence\re4-dreamcast\doorprefetch-20261016 (all times EMULATED,
console-like Flycast; not console).

## Knob DOOR_PREFETCH=1 (default 0)
- Window 1 (gameDoordemo, SndStatDisp wait, ~0.5 s): next room's textures (PS2 world part keys from
  dc/native/r<room>/ps2-world.r4pw + its dc/resident.bin records) into VRAM, a 28 ms slice per frame; early
  ROOM_CHANGE_EVICT of the old room's leftovers; KOS floor 64 KiB (closes LRU old textures like RETIRE_KOS_FLOOR).
- Window 2 (SndRoomBgmLoad old-music wait): the busy loop sleeps a frame while the room's list still has work.
- No main RAM (stack 2 KB pieces). Code: platform/include/door_prefetch.{h,inc}, hooks in game.cpp / snd.cpp (lines
  kept), native_ui.cpp (2 includes/hooks), Makefile block. Log "DOORPF:". Enemy archives / .dar are NOT prefetched:
  heap 4 is still the old room's in window 1 and they need 1..3.5 MB.

## Results so far
- Knob-off identity (main image): kP 12dddcac, rP 137aa574 = t15/int 439304e6. Overlays not compared yet.
- rP + knob image 4ff2d455, _end 8c4210d8 -> 8c422218 (+4,416 B: too much, shrink before landing).
- GDEMU profile (dpparse.py cg / ng): door totals -0.17 s (r100->r101, r105->r101) .. 0, no door slower after the
  idle-yield + early-evict revision; fragmentation retries back to control levels.
- WEAK profile (cw / nw): NOT a win: +0.1..+0.9 s on most doors (d05 +0.7, d08 +0.9, d12 +0.9), -0.5 s d13, d04/d10
  incomplete in 150 s. Cause not analysed yet (suspects: prefetch reads delaying the door SE read / window 1 end;
  slices longer than the wait on a slow drive; KOS closures causing reloads).

## Next
1. Analyse weak-profile DOORPH phases cw vs nw (snd / bgm / scen) and cap window 1 by the wait (stop when the door SE
   read is done), then re-run weak + GDEMU.
2. Gates not run: decisions (trace arms dpcrT / dpnrT built, bases not mastered), KOS squeeze, GDEMU + weak race,
   VRAM gate, overlay identity, _end shrink.

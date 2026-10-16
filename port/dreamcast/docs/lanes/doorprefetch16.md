# Lane doorprefetch16 (2026-10-16): next room's reads during the door sound / music hand-over

User 10-16: "Start the next room's reads while the door sound and music hand over." Base t15/int 0596b7ed. Not gated
(the coordinator's rule: gates only if it wins; the win is small, the coordinator decides). Evidence
C:\Flycast-Evidence\re4-dreamcast\doorprefetch-20261016 (`_tools/dpparse.py`; all times EMULATED on console-like
Flycast, not console).

## Knob DOOR_PREFETCH=1 (default 0)
- Window 1 (gameDoordemo, the SndStatDisp wait, ~0.5 s): once the door sound's own read is done (RE4DC_DPF_READ in
  SndStatDisp), the next room's textures (PS2 world part keys from dc/native/r<room>/ps2-world.r4pw + its
  dc/resident.bin rows) load into VRAM in 28 ms slices per frame. Before the uploads: an early ROOM_CHANGE_EVICT (old
  room leftovers that the first preload pass closes anyway; the bound enemy / player / weapon keys are pinned first, as
  the pass does). KOS floor 64 KiB (closes LRU old-room textures, as RETIRE_KOS_FLOOR would).
- Window 2 (SndRoomBgmLoad, old music's slot): the busy loop sleeps a frame while the room's list still has work.
- No main RAM (2 KB stack pieces). The .dar and enemy archives are NOT prefetched: heap 4 still holds the old room in
  window 1 and they need 1..3.5 MB.
- Code: platform/include/door_prefetch.{h,inc}, hooks in game.cpp / snd.cpp (lines kept), native_ui.cpp (include +
  frame hook), Makefile. Log "DOORPF:".

## Results (attempt 2, base 0596b7ed; control arm dpbrW, knob arm dperW; per-door total ms, door press -> play)

| Door | GDEMU off | GDEMU on | delta | weak off | weak on | delta |
|---|---|---|---|---|---|---|
| d01 r100->r101 | 2352 | 2161 | -191 | 23872 | 23616 | -256 |
| d02 r101->r103 | 2496 | 2430 | -66 | 19346 | 19346 | 0 |
| d03 r103->r106 | 1950 | 1849 | -101 | 18069 | 18069 | 0 |
| d04 r106->r104 | 2374 | 2329 | -45 | 8739 | 8739 | 0 |
| d05 r104->r107 | 2425 | 2375 | -50 | 17858 | 17961 | +103 |
| d06 r107->r105 | 2680 | 2563 | -117 | 14625 | 14299 | -326 |
| d07 r105->r101 | 2222 | 2221 | -1 | 23638 | 23634 | -4 |
| d08 r101->r102 | 2558 | 2491 | -67 | 13600 | 13605 | +5 |
| d09 r102->r108 | 2386 | 2324 | -62 | 25949 | 25949 | 0 |
| d10 r108->r109 | 2664 | 2632 | -32 | 9494 | 9494 | 0 |
| d11 r109->r10a | 2023 | 1957 | -66 | 18929 | 18940 | +11 |
| d12 r10a->r10b | 1552 | 1489 | -63 | 19784 | 19751 | -33 |
| d13 r10b->r11b | 2531 | 2481 | -50 | 18015 | 17555 | -460 |
| c1 r101->r100 / back | 2476 / 2308 | 2394 / 2185 | -82 / -123 | 18227 / 20417 | 18227 / 20054 | 0 / -363 |
| c2 r101->r103 / back | 2498 / 2395 | 2432 / 2220 | -66 / -175 | 18957 / 22564 | 19050 / 22167 | +93 / -397 |

Route mean d01..d13: GDEMU -70 ms per door, weak -74 ms per door. No door hangs (all reach play within 150 s).

Why so little:
- Weak drive: window 1 is spent on the door sound's own read (it ends with the wait on 9 of 13 doors: nothing loads),
  and window 2 is gone (the 2 s music fade ends before the room set-up reaches SndRoomBgmLoad). A texture loaded alone
  costs ~110 ms there vs ~48 ms inside the ordered preload pass.
- GDEMU profile: the waits are idle, but textures are only 46..270 ms of each door; the rest is CPU set-up.
- Attempt 1 (no read gate, unprotected early evict) was slower on weak: +0.1..+0.9 s (window 1 delayed the door sound
  read; the evict closed shared villager textures, +25 loads on d05).
- _end +4,160 B text with the knob (dpf_* ~4 KB even at -Os); knob-off images identical to t15/int (checked on 439304e6).

## Not run (gates only if kept)
Decisions on every door, KOS squeeze 48 KiB, GDEMU + weak race, VRAM gate, overlay identity. Trace arms were built
(dpcrT / dpnrT on 439304e6) but not run.

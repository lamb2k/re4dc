# Lane land17 (2026-10-17): Test 16.4 fixes onto t15/int for Test 17

Brought FOLIAGE_NEAR_FIX (T15_FN) and LAKE_FAR / LAKE_FAR_SHORE = 45000 / 45000 (T15_LF) from lane/lake17 onto
t15/int cbdde6de, with the 16.4 KNOWN_ISSUES / CONTRIBUTING-PORT text. Built with T15_ST="" on both sides (stump17 data
not restored after the 10-17 rebuild). Evidence: C:/Flycast-Evidence/re4-dreamcast/land17-20261017.

## Gates
- Knob-off identity (T15_FN= T15_LF=): rP 52f7b2d14ea1d221, rW 643ed2357201c228 (= cbdde6de), also after SS_CLOSE_HOLD.
- Knob-on: rP 5be87ce8782dc224, rW 5b949dd0a649b463, missing=0.
- KOS squeeze 48 KiB: PASS 10/10 (min headroom 6,368).
- Boots, 60 s each, knob-on rW: r10b boat and r100. Both had 0 HALT, 0 FAULT and 0 MISSING.
- STRICT bell: MUST-IDENTICAL.
- STRICT door103: the trace is STRICT. Decisions show ep at 1176 only, the first r103 frame after the door. The same
  ep difference shows between two knob-off runs (oT vs oT2), so it is run noise inside the door-load frame. The door
  itself lands on the same tick (1175) in every run.
- STRICT h2: plain, it FAILS at 1229 (FOLIAGE_NEAR_FIX alone, bisect arm fT). With SS_CLOSE_HOLD=1 and
  `sshold 1232` on both arms, it is MUST-IDENTICAL (2002 ticks, decisions ok). The shift was timing only.

## Open: the sub screen close is not deterministic (later fix)
The sub screen backing close (SubScreenExit -> SubScreenExitCore, the room REL relink) lands on wall/thread timing.
The radio voice stream ends on the AICA clock, and the sub screen thread starts after it. So any frame-cost change
can move the close by a tick, and the logic trace diverges from there. STRICT pairs that cross a sub screen close
need SS_CLOSE_HOLD=1 (test only, mcheck.mk): a `sshold <frame>...` line in the w11.txt fixture slot
(`fp_run.py --w11`) is read by the hold. The later fix is a deterministic close, for example one keyed to game
ticks instead of the voice clock.

# Lane farhalf (2026-10-15): far / off-screen Ganados at half rate (backlog D1)

Branch `lane/farhalf` (local only), worktree `/root/probe/lanes-20261015/farhalf`, base dreamcast-port 1c79d543
(test 13). Evidence `C:\Flycast-Evidence\re4-dreamcast\farhalf-20261015` (`_tools\` = the run kit, warp files in
`_tools\w\`). Labels: every number says MODELLED (SH-4 hw model), MODELLED-corrected (x1.06 for logic, the
HWMODEL-CALIBRATION-20261015 factor), FLYCAST or CONSOLE.

## Why the September variant failed, and what this lane does differently

- **ACT_CAP (B1, September)** parks Ganados beyond a cap N (no emMove at all, one "creep" emMove every 4th tick). It
  is a real update-rate cut: a parked Ganado walks at 1/4 speed and its Rnd() draws move to other ticks, so every
  later Rnd consumer (other Ganados, effects) sees a different sequence. Its trace was never STRICT once anything was
  parked, and the uncapped-baseline review (2026-09-26) ruled that capped arms "throttled the encounter" (G understated
  by 4.82 ms). **ACT_CAP_FAR_M** (crowd12, 10-14) extended it to far in-view Ganados and "fails decisions"
  (VILLAGE-LEVERS-20261014.md).
- Reason, in one line: skipping a Ganado's AI moves its Rnd draws, so the shared stream (and every decision after it)
  diverges; exact half-rate pose updates were also called impossible because the pose drives hits / collision / root
  motion.
- The lane el census (docs/lanes/el-20261005.md) says what a Ganado tick costs (MODELLED, per Ganado update):
  motion keys 0.13, skeleton 0.12, foot IK 0.09 + its floor lines 0.035, route / sight lines 0.07-0.12, AI 0.05,
  sphere 0.04, wall lines 0.03 (em-em 0.08 in the square). The pose (keys + skeleton + IK) is ~45-60 % of it.
- So this lane splits the update: **FAR_HALF=1 (pose half)** keeps every state-changing step at full rate (AI,
  routine, root speed / position, frame and sequence bookkeeping, collision, the sight check, which reads only
  `em->mat`) and halves only the pose; **FAR_HALF=2 (full half)** is the approximation, offered only if it is worth a
  few console ms.

## The knob (game30.mk, default 0 = nothing built; knob-off image identical)

`FAR_HALF=1|2`, `FAR_HALF_M=12` (metres), `FAR_HALF_LOG=N` (census), `FAR_HALF_RT=1` (run-time switch for a
benchmark disc A/B, warp line `farhalf 0|1`), `DT_IK_APART=1` (trace builds: the leg IK floor queries out of the
decision hash "lq", both arms).

- Selection (act_cap.cpp, built with or without ACT_CAP / ACT_CAP_TABLE): eligible = Ganado id 0x10..0x20 in a
  whitelisted walking / idle routine (the cap's threat() list), > FAR_HALF_M from Leon (horizontal), outside the last
  view frustum + 3 m, hp > 0, no pending damage, not the lock-on target, not parked by the cap. Eligible ones
  alternate full / reduced ticks (a per-entry phase, never two reduced in a row; any ineligible tick is full, so one
  that turns visible or comes within N m is full on that tick). No selection while the sub screen has swapped the
  room lists (re4dc_ss_ui_order), during event pauses or frozen characters. Nothing is deleted or re-queued.
- FAR_HALF=1 reduced tick (motion.cpp `farHalfMotionMove`, em10.cpp): root speed exactly as MotionMove; MotionMoveCore
  bookkeeping (Mot_frame / _old / _sav, the model matrix from pos / ang / scale, flag clears); both sequence steps;
  the hokan counter step; then the parts follow the body by translation (`re4dc_far_half_follow`: world / matrix
  translation by pos - Pos_world, Pos_world = pos, r_scale = scale, as partsWorldCalc / PartsWorldPosCalc leave them).
  Skipped: key evaluation, partsMatCalc, the matBlend / additive pose, partsWorldCalc (x3), the leg IK and its floor
  queries, the hokan pose blend, the blend table. Falls back to the full MotionMove when a part is fixed
  (partsFixAdjust moves pos by a part's world position; only the gatling routine) or a motion drives a camera.
- FAR_HALF=2 reduced tick: no emMove (em.cpp emParkMove: plDist2 / l_sub kept current), as the cap's parked tick.

## Status / results

(filled in below as the gates run)

# Ordinary footsteps and Garrador approach

Normal walking is not inherently silent. The frozen source has `cPlayer::seqSeCtrl`, not a tracked `PlSetFootStep` function under that name. At `src/game/pl_class.cpp:840-868`, it clears `Status_flg[1]` bit 31 on every call, then sets it for motion sound identifiers `seNo-1` equal to 0,1,2,3,0xD,0xE,0x14. This is driven by authored motion sound keys and has no run-only condition. Audio surface-kind selection happens afterwards and does not prevent the flag. The observed transient bit during an ordinary walk is consistent with this code; do not call that walk silent.

`em10FindCk2` at `src/em10/em10.cpp:21691-21739` checks in order:

1. A nonzero `Goto_mode` refuses this target search.
2. Published bit 29 with `bell_stat` 2 or 1 selects `bell_pos` within squared distance 400,000,000 (radius 20,000); state 2 also resets `CriAtk_wait`. A published ringing bell therefore takes priority over this function's footsteps branch.
3. Bit 31 selects current Leon position within squared `em->plDist2` 12,250,000 (radius 3,500), increased to 64,000,000 (radius 8,000) when Leon is in routine `(0,3)`, running.
4. Below squared distance 1,000,000 (radius 1,000), it selects Leon even without the footstep flag.
5. Room/player alert `Status_flg[0] & 0x00800000` with route distance below 25,000 also selects Leon.

Thus switching from B-running to ordinary walking avoids the *run-expanded hearing radius*. It does not suppress step events, erase the last heard destination, or prove that the entire AI will ignore Leon. The source comparisons use `em->plDist2`; a controller's planar or route-distance sample should not be silently substituted for that field at a threshold.

`game.cpp:815-823` runs enemies before the player update, then clears bell bit 29. Player `seqSeCtrl` is near the end of `cPlayer::move`, and the bell object publishes later in `ObjMgr.move`. The enemy can consume the last step pulse after the host releases movement. Wait for actual axes/ordinary movement to settle and observe subsequent enemy updates; the destination already copied into `x5F0` persists.

For found claw types 0xA/0xD with `Goto_mode=0`, route computation at `em10.cpp:16851-16860` uses remembered `x5F0` when work flag 0x100 is set. `em10FindLostCk` at 27128 refreshes `x654` to 150 on a positive target check, then decrements it; reaching zero enters FindLost 0x5D, whose motion completion clears found flag 0x100 and starts wandering. This is source-tick logic dependent on actual routine calls and motion completion, not a guaranteed 150-frame safe window.

There are direct target refreshes independent of the footstep flag. In StickClaw 0x59 (`em10.cpp:5043-5103`), the routine chooses a turn based on actual player bearing and can randomly copy current Leon position into `x5F0` in `Goto_mode=0`. Therefore a turn during an otherwise quiet walk does not by itself establish an incorrect hearing implementation. Do not repeatedly flank based only on a cleared bit 31.

The ordinary bell at `obj14.cpp:111-129` republishes its position while its `ringTimer` is nonzero. A hit sets 90 at line 195. That is a bounded source-update distraction, not a permanent target lock. Observe bit 29, `bell_stat`, remembered target, and current enemy routine/yaw; a consumed or broken bell must remain consumed. Other source reactions can alter destination or facing during the distraction.

The current controller's strong-rear predicate `back_dot < -0.7 * planar_distance` describes a cone within approximately 45.57 degrees of directly behind. It is a conservative controller firing condition, not a source-wide Garrador hearing rule. Its useful duration depends on actual yaw motion, route target and active attack/recovery. For example ClawAtk 0x2B (`em10.cpp:10914-10949`) turns toward `Pl_pos` during its timer/animation flag window, at a maximum 0.19634955 rad per update, or 0.049087387 under the alternate animation flag. No fixed multi-frame settling delay can be assumed harmless to the rear opportunity.

A useful ordinary attempt should prealign at distance, switch to walking outside the run-expanded radius, keep the final walking segment outside the ordinary 3,500 hearing radius where geometry permits, and stop movement before aiming. Then use actual enemy yaw, remembered target and recovery/bell state to exploit a rear opening promptly. Recompute the physical weapon ray from the current pose and preserve the actual ray, laser, ammo, HP and damage-part checks. Waiting silently alone cannot force a rear opening, and a stationary turn/aim animation should be called quiet only when the actual step flag and source sequence confirm it.

Useful read-only telemetry is source frame; raw Joy and translated Key; Leon routine and sound-event flag; `Status_flg[1]` bits 31/29; bell state/position; enemy routine/yaw/position; work `Goto_mode`, flags, `x5F0`, `Pl_pos`, `Go_pos`, `x654`, `CriAtk_wait`; and the current rear dot, physical ray and target identity. Work fields are defined in `include/em10.h`; use the frozen ELF/layout pins rather than importing another build's offsets.

`garrador-hearing-source-identity.json` records seven source SHA-256/Git blobs and verifies current bytes equal frozen runtime 12a841d7c. This was source review only. No controller/runtime changes, host game tests, builds, guests, release checks or physical Dreamcast tests were performed. Castle21 retains combat/progression ownership and authentic lineage; original 127 and prior replay completion remain preserved.

tools/d367/motion: motion streaming for enemies whose resident archive does not fit their rooms' heap 4
(lane ch5found16 round 4, 2026-10-16). Runtime: no new code. The play recipe's native_motion.cpp knobs
(MOTION=1 MOTION_RESERVE=1 MOTION_PRESSURE_BYTES MOTION_COLD_POOL MOTION_RESERVE_SPILL MOTION_OOM_EVICT, test 15 on)
bind any prepared archive that carries a motion table: hot clips load at room entry (motion bind), cold clips load on
first use into the reserve slabs / spill (MOTION_MISS_LOG=1 logs each "motion miss").

Add an enemy (em39, Saddler em31, ...):
1. Audit its source (tools/prepare_enemy_motions.py, comment above MOTION_SMALL): every FCV it names must reach
   MotionSetCore (directly or through MotSetObj00 / MotSetObj16 / blend helpers); list any FCV header read (maxFrame:
   headers stay resident, so allowed) and any FCV passed elsewhere (not allowed: keep that clip hot or resident).
   MotionSetCore's `seq` argument is a SEQ key table (always resident). ARC(n) = archive slot n-4.
   Then add '<em>.drs' to MOTION_SMALL.
2. All-cold archive: prepare_enemy_motions.py --source em/<em>.drs --output prepc-<em> --hot-audit <empty hot json>
   --diagnostic-incomplete-prefetch --textures tex-<em> (empty: {"source_complete": false, "union": {"source_arc_indices": []}}).
3. Runs: a MOTION_MISS_LOG=1 build of the room's arm with prepc-<em> on the disc (and its dc/mot/*.fcv files), warps that
   make the enemy play its fight (<= 60 s each).
4. motion_hot.py prepc-<em>/motion-residency-report.json hot/<em>-<room>.json <run-output.txt>... ; commit the hot json.
5. Re-prepare with --hot-audit hot/<em>-<room>.json; check: a MOTION_MISS_LOG run has no in-play miss in the hot scene,
   heap 4 fits, and STRICT + decisions MUST-IDENTICAL against the all-hot reference (every clip hot) in a LOGIC_TRACE arm.

hot/em36-r307.json: 9 of 72 clips (119,776 B), r307 runs m4c..m8c (spawn, the room's release of the regenerator, walk,
hit reactions, death). Evidence C:\Flycast-Evidence\re4-dreamcast\ch5found-20261016 (h-cx5mmW, h-cx5srT).

# engine19 lane scripts (enemy wall check, ENEMY_VIS_CULL)

Lane scripts as run for the option C gates (2026-10-19). Paths are the lane's own (worktree
/root/work/lanes/engine19, k dir /root/probe/lanes-20261019/engine19/k, evidence
C:\Flycast-Evidence\re4-dreamcast\engine19-20261019); copy and edit them before reuse.

- b1.sh / bw.sh: build arms (k base, x knob-off, w cull, wS/kS PACE_MODE=off + ENEMY_VIS_DEBUG stills arms,
  wK KOS squeeze twin, kM/wM hw-model arms). fix.sh: fixture json with the RC19D room files.
- g.sh / run.sh: one Flycast run (<= 60 s), disc deleted after the run.
- strict.sh: kT vs wT logic trace, logic_trace_diff --align frame.
- stills.sh + mkfreeze.sh + fbdiff.py: tier-2 pixel stills at a frozen tick (use SUF=s: pace-off arms; frozen
  pictures land on different frames under normal pacing).
- kos.sh + sq.sh: KOS 48 KiB squeeze, same scenes/markers/criteria as fullplay/kos_squeeze.sh, one run at a time.
- cg.sh / nd.sh: CAST-GC, TEXCHK, NOT-DRAWN on runs of the mW arm.
- hw.sh: stage a fixture disc and run hwmodel/hwproject.sh on it.
- ro.sh / vx.sh: OCCL room-file compiles. occ_eval.py / hide_check.py / occ_why.py: offline replica + oracle.

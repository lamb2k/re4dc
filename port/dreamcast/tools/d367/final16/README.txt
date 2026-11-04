tools/d367/final16: lane final16 (2026-10-16) scripts for the final boss room r332 (Saddler, em31) on the ROUTE_FINAL arm.
Lane-local paths (/root/probe/lanes-20261016/final16, C:\Flycast-Evidence\re4-dreamcast\final16-20261016) are as used; no
assets here. Order: setup.sh (merge + submodule), b2.sh (play-warp arm f2mW) / b3.sh (trace arm f3rT), reg.sh (Saddler
registry package), prep1-4.sh (em31 all-cold / all-hot / hot-set preparations; hot.sh = motion_hot.py over the miss-log
runs), snd.sh / sndx.sh (AICA banks; OUT=<suffix> for a second set), str.sh (the ch5f stream file), fx4.sh / fxh.sh /
mktr.sh (fixtures: c5merge + fixture_arm + sound + padscript for the s00 skip), run.sh (<=60 s Flycast run), summ.py
(per-run memory / pacing / misses / Saddler emlog summary), ident.sh (knob-off identity of the test 15 rP image).
warps/fx-r332-*.txt: r332 warp rigs (m3 fight with A presses for the s00 up-cut, m4 run at him, m5 beside him, c1 control
without Saddler); padskip-s00.txt skips the s00 route movie (START while movie=1).
run.sh takes RUNPY=<lane py/rfp-run-trace.py> for the trace arms (the skill copy refuses LOGIC_TRACE=1 harnesses); strict.sh = logic_trace_diff + decision_cmp, frame aligned.
Report: C:\Game Dev\Emulators\FINAL16-20261016.md.

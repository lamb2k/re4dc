# The integration lane: standing instructions (2026-11-21, H-024)

The owner: "Run as many as possible with an integration lane as long as they aren't redundant." You are that lane.
Lanes hand back to the integrator (the Claude session that briefs you); the integrator sends you one lane at a time
to gate. Only you merge into `engine`. You do not do lane work, you do not fix a lane's code, and you do not rule on
rules: a failed gate goes back to the integrator with the evidence.

Read first: `E:\RE4DC-Lanes\COMMON-BRIEF-20261121.md`, then in your worktree `AGENTS.md`, `CLAUDE.md` (the integrator's
merge gate), `port/dreamcast/docs/engine/LANES.md` section 4, `HANDOVERS.md` H-016 to H-024.

## Your worktree and tools
- `/root/work/lanes/eng-int` (WSL Ubuntu-24.04, root), on a local branch that tracks `origin/engine`. Never work in
  `/root/work/lanes/reassess19` (the integrator's) or a lane's worktree.
- The integrator's gate scripts are the pattern: `E:\RE4DC-Lanes\reassess19\gate\g17.sh` (the checks) and `g17c.sh`
  (the final merge, tree check and push), `g14.sh` (reference controls and Flycast logs re-judged), `g21.sh` (a
  documents-only merge). Build one parameterised script from them, `E:\RE4DC-Lanes\eng-int\gate.sh <lane> [options]`,
  and keep it there; its outputs go to `E:\RE4DC-Lanes\eng-int\gates\<lane>-<head>\`.
- Builds in `/dev/shm/eng-int`, deleted after each gate. `make -j4`. Machine rules as in the common brief.

## The gate, in order (stop at the first hard failure and report)
1. Fetch. The lane's head is the one the integrator named. `origin/engine` must already be merged into it (else:
   back to the lane). Trial merge with `--no-ff --no-commit`; a conflict goes back to the lane.
2. Hygiene on the lane's diff against `origin/engine`: no blob over 300 KB; no data files (elf, o, pak, drs, arc, bin,
   gdi, iso, png, jpg); no dot-folder paths; no file outside the lane's owned list in its `BRIEF.md` (list any, with
   the hand-back's explanation if it gives one); `src/`, `include/`, `STATUS.md`, `HANDOVERS.md` untouched; no pacer
   or field-counter file touched unless the brief owns it.
3. **Nothing loosened:** diff `tools/plays_right/tolerances.json`, `outcome.py`, `plays_right.py`,
   `hostref/svc/*compare*.py`, `camcheck.py`, `camengine.py`, `refctl.py`, and every "must", "tol" or bound line of
   `svc_controls.sh`, `camcheck.sh`, `camengine.sh`, `loader/selector.c`'s checks. Any change is reported verbatim; a
   loosening not asked for by the lane's brief is a hard failure.
4. Reference changes: any change under `hostref/` that alters what the reference computes (not what it logs) needs
   its cause in the hand-back and a control row; otherwise a hard failure.
5. Images: default, `FIGHT=1`, `BOSS=1`, `SENDABLE=1` link on the merged tree; `check_link.py` verdict and counts for
   each, compared with `origin/engine`'s (default and SENDABLE must stay at 0 service functions; FIGHT and BOSS must
   not rise); the lane's link controls fail as its hand-back says. Full hashes and verdicts to `images.txt`.
6. PC suites on the merged tree, each to a file: `svc_controls.sh`, `camcheck.sh`, `refctl.sh`, `controls.sh`,
   `outcome_controls.py`, `aim_check.sh`, and any suite the lane added. Every row "as it must", none WRONG or ERROR,
   row counts not lower than on `origin/engine`. Re-run two of the lane's own controls and see them fail.
7. Flycast evidence: re-judge the lane's serial logs against a reference you build (`shot_engine.py`,
   `hill_engine.py`, `camengine.sh`, `hudcheck.py`, whatever the lane cites), and check two numbers cited in its
   hand-back against the files. If the lane changed an image and gave no clean-disc run of the merged head, build
   a disc with the repository script (LEON, HILL, FIGHT, BOSS and the lane's control scenes, at most 8) and run it
   in a slot by lease: clean scenes OK under the strict selector, each control FAILED with its reason. Delete the
   disc after the run.
8. A documents-only or tools-only lane (it says so, and step 2 confirms it): steps 5 to 7 reduce to "the four
   images are byte-identical to `origin/engine`'s when built to the same OUT path" or are skipped if nothing under
   `port/dreamcast/engine` or a script the images use changed; check the document's cited numbers against the
   lane's files instead (five of them).
9. **Verdict.** PASS only if nothing above failed. On PASS: the final merge (`git merge --no-ff` with a message
   that states what the gate checked, in the style of the integrator's merge messages, ending
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`), confirm the merged tree equals the gated tree, add
   one "Merged <date>, finished, unaudited: <lane> (...)" note to `port/dreamcast/docs/engine/STATUS.md` above "##
   Waiting on the owner" and remove the lane's row from the lanes table, commit, push `engine`. On FAIL: no merge;
   say exactly which step, with the file.

## Report to the integrator after each gate
PASS or FAIL; the new `engine` head if merged; per step one line; the two numbers you checked; anything the lane
claimed that you could not verify; any change to a comparator, quoted. Keep `E:\RE4DC-Lanes\eng-int\STATUS.md` as a
log of gates (lane, head, verdict, engine head, time).

## Limits
- One gate at a time; never two merges in flight. If `origin/engine` moved since the lane merged it, the lane must
  merge again (send it back) unless the move was documents only and the trial merge is clean.
- You never edit a lane's code to make it pass, never loosen a check, never rule on a contested point (report it).
- You never touch the SD card, the console disc folder, another project's files, or `t15/int`.
- No window focus, no input to windows; Flycast slots by lease; test discs deleted after their runs.

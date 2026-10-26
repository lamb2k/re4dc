# Castle 3-1 coverage (lane castle-events22), PAUSED 2026-10-22 by the user

Status: setup only. No room has been run yet. Nothing below is a pass.

## Rooms and events (chapter 3-1, from Codex's door graph + CASTLE18_CH31 doc)

| Room | Place | Events / triggers | How to reach | Result |
|---|---|---|---|---|
| r200 | Castle gate | AEV4 chapter-start s00 (Codex r200a passed), Merchant, stairs (AEV9 r200->r200), door 1 -> r202 | warp `w/a-r200.txt` (goto door 1, A) | not run |
| r202 | Cannon courtyard | Zealot waves + catapults, cannon callback (Merchant list 30), cap 4 gate (ALIVE_CAP_R202_GATE), door 1 -> r207 | warp room 0x202 jp 0, kill rig, goto door 1 (20361 9000 -58061) | not run |
| r207 | Hall | door 1 -> r203 | goto (-9764 4149 -10683), A | not run |
| r203 | Key room | chest 7 / key 8A, 14-Ganado key wave (atfunc), door 1 -> r201 | atfunc + goto (-30736 4156 -23004), A | not run |
| r201 | Prison | Garrador (J218, em 0x1b, 4000 HP), switch / disarmTrap / reset waves 57,5b,5c / 58,59,5a, door 7 -> r208 | Codex controlled-event001..003 warps (Garrador kill passed for Codex: HP to 0, RSF0, door +2600) | not run |
| r208 | Crank bridge | two cranks (trg 0), bridge, Ashley snipe platforms, door 1 -> r204 | Codex controlled-event004 | not run |
| r204 | Chapter end | area 2 r204_EventExec: s00, SceSetChapterEnd(3_1), save, Salazar radio | Codex controlled-event005 | not run |

Doors out of 3-1 (not in scope): r201->r210/r219, r204->r205/r209/r22c.

## Where it stopped

- Tree: /root/work/lanes/castle22/tree, branch wip/castle22 = origin/wip/codex-int22 d0dba247 + warp files under
  port/dreamcast/tools/d367/castle22/. sh4zam submodule must be initialised (`git submodule update --init`).
- Built: k22amW (mW arm, disc-2 recipe via castle18/build-test21-disc2.sh, LP=k22a), ELF 6082469edfbb95eb, missing 0,
  _end 8c47af78, out /root/probe/lanes/route/out-k22amW; syms "0x4238e0 0x4338e4 0x4338e0".
- Base disc: fp_master.sh of the J data tree (/root/probe/castle21-recovered-j-content-20261021/tree) with this program;
  deleted at pause (manifest castle22-20261022\DELETED-MANIFEST.txt). Remaster in ~3 min to resume.
- First two runs (r200 door, r201 Garrador) did not launch: run1.sh passed fp_run.py as a \\wsl.localhost path that
  Windows Python mangled. Fix: copy fp_run.py to a C: scratch dir (or use the same-named tool in a C: harness) and rerun.

## Resume

1. Remaster base (fp_master.sh, see above), fix run1.sh path, run the warps 2 at a time (60 s, --align).
2. Judge each run: cast_gc.py, texchk.sh, alivelog peak <= 4, room VRAM line, align log, `room enter` of the next room.
3. Record results here; fixes on wip/castle22 behind default-off switches.
Input: warp `act` lines only (in-game pad, no host input); if a prompt will not take them, teleport past and note it.

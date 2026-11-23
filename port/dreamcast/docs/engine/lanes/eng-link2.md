# eng-link2 hand-back (2026-11-23): RE4 on QA Link 0.2, a testing candidate

**Status: finished, unaudited.** Branch `lane/eng-link2`. dc-qalink pinned at the v0.2.0 tag (88d9379c1). FIGHT, BOSS and E1
pushes carry the layer (FIGHT SENDABLE ruled in 2026-11-23, about 300 KB heap left). Design: CONSOLE_LOOP.md section 17. Full hand-back with evidence paths:
`E:\RE4DC-Lanes\eng-link2\HANDBACK.md`. Every time here is **Flycast** (a function check, never a console figure).

## What RE4 has now
- `engine/qalink/e1_qalink.cpp` (QA/test images only: `game/qalink.mk`, `DCQL_ENABLE` defaults to `SENDABLE`): live
  record per picture (ROW phases, room, Leon, enemies, play-file guards), PC commands (warp presets through the loop's
  room change; options menu, end, crash, readx), RE4 menu pages (Scene, Timing, Warp, Tests), the network disc mounted
  at boot (the whole RE4 disc from the PC, or an overlay over GDEMU), room-entry times.
- `core/main.cpp`: three calls under `#ifdef E1_QALINK`; `core/play_files.c`: `e1_play_files_counts`.
- `tools/engine/build_console_disc.sh --folder` (the disc folder the bridge serves, and the push images) and
  `--loader-disc` (dc-qalink's loader booting with the RE4 data on the GDI); `CDISC_JOBS`.
- `tools/consoleloop/re4_bridge_proof.py`, `re4_link_check.py` (with its controls), `re4_increment.py` (build, stage,
  push in one command).

## Old-port parts considered
- QA teleporter (`game/qa_menu.cpp` presets from warp-rig fixtures, story state through the old room loader): taken as
  an idea (presets grouped by place, landing judged by the room id, a state page with room and enemies), written the
  engine's way through `e1_room_change_run`; its fixtures and the warp rig's control flow left (old core).
- Old QA link protocol and commands (`tools/qalink/`, modem): left; dc-qalink 0.2 replaces them.
- Pad scripts and remote driving (`PAD`/`GOTO`/`SCRIPT`): left for now; the engine's pad is its scene script (a PC
  `pad` command is refused with that reason). A later lane can map dcql's pad command onto `e1_input_latch`.

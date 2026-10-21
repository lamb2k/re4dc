# Native room presentation during ordinary pause

`PAUSE_NATIVE_PRESENTATION` defaults to 0 and requires `COARSE=1`. It extends only the presentation context for ordinary OPTIONS modes 0–2 whose source-owned saved mode begins with gameplay mode 3. Existing system/status/movie exclusions and the dropped-image latch remain. It reads the saved state through a guarded accessor in `src/game/game.cpp`; `gameOption` still owns simulation stopping, menu movement and mode restoration.

The current QA aafc10f3 baseline reproduces missing room walls/floor behind OPTIONS in r100. The enabled candidate keeps those surfaces and the menu visible, then resumes normally. The original report is public Release21; this is an independently bound current-QA reproduction, not proof that the public binary is identical.

Actual predicate/accessor source tests cover 8,192 contexts per mode plus null state, with UBSan and Make guard checks. Disabled preprocessing compares the predicate against original integration 892c10dd. Full SH4 OFF and ON builds pass; OFF's raw program and all 14 overlays match the QA disc exactly. ON grows the program by 224 bytes and carries all 14 matching newly linked overlays. The private image preserves all 1,728 other files exactly. Source/build identity and the bounded 46.3-second Flycast run are in `../tools/d367/feedback21-pause/qualification.json`.

The initial ON build failure (GameWork's private declaration) is preserved in private build logs and repaired by the source-owned accessor. That failure is not acceptance evidence. The host tests alone did not establish target compile correctness.

Screenshots, run logs, exact build outputs and receipts are preserved under `C:/Flycast-Evidence/re4-dreamcast/feedback21-runtime-20261021`. The ON run executed all eight ordinary input steps, exited its owned emulator and reported no harness errors. Screenshots were visually inspected; no inventory, boss, movie/death/held-background or whole-renderer pass is claimed. Those remain required before recipe adoption. No performance, hardware, release or SD claim.

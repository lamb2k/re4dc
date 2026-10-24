# Owned still tools

`force_limited.py` is a config-only wrapper around the unchanged fullplay harness. Use Windows Python under `stat-guest-slot.sh` -> `trace_lock.sh` -> `census-bound-run.py` -> `force_limited.py` -> `fp_run.py [args]`. Require `RE4DC_EMU=console` and `FP_NOLIMIT=0`. The wrapper writes exactly one explicit `aica.LimitFPS = yes` in the fresh owned capture config before the exact child spawns, rejects off/ambiguous/duplicate configurations, records prelaunch/final identity and leaves shared template/runtime/assets alone. Frozen SHA256: `872a4a2d30ec342cf01e15d04507269f02a713c8eccc68c3dde5320afb1eff15`.

`freeze_capture.py` adds marker-triggered framebuffer reads using the existing exact PID/image-bound read-only RAM backend and frozen VRAM decoder. It requires outer exact55s bounded-Popen, console and explicit limiting. Actual placed room plus exact freeze330 marker gate capture. It reads existing8MiB VRAM twice0.15s apart, saves only both framebuffer RGB565 regions and decoded images, and records errors/config/image/time identities. It never reads actor or viewport state or uses the withdrawn49ad observer.

`run_still.py ARM {f1,f2} TAG` is the WSL orchestrator for this completed allocation. It pins helpers/template data/console/fixtures/source/profile/14 overlays/bases; verifies C floor24GiB; serializes one owned guest; refuses any duplicate arm/scene or fifth case. All four authorized cases have now been consumed. No further guest is authorized by this report.

`seal_stills.py` is a guest-free WSL evidence checker/comparator. It verifies all recorded identities, bounds, explicit prelaunch config and unchanged final config, marker/actual room, exact PID/image, per-buffer read stability and saved image/raw hashes. It compares corresponding fb0-to-fb0 and fb1-to-fb1 for each scene, preserving mismatch results. It writes fresh `RESULTS.json` only and refuses overwrite. Existing results need no rerun.

Host controls (Windows Python, no guest): `python -B -m unittest test_force_limited.py test_freeze_capture.py` (9 PASS). The capture tests require Windows because the existing backend path and APIs are Windows-owned.

Read `HANDBACK.md` for actual results, private evidence paths and the freeze330 evidence limits. `SHA256SUMS` seals this subsection; private captures/logs/assets are not included in the helper snapshot.

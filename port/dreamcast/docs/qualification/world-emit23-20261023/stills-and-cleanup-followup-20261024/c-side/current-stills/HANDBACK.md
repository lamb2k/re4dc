# Current49ad R/B authored still comparison

Complete within the allocated four single attempts: cross `f1.txt` and forest `f2.txt`, R/B g profiles, explicit FPS limiting enabled. Both corresponding framebuffer indices match in both scenes: **0 changed pixels, maximum channel difference 0, identical raw RGB565 bytes**. All eight first-read images were visually inspected: clean scene, Leon and HUD; no Loading/watchdog screen. Both buffers are retained, including their differing animation contents; no buffer permutation or best-buffer selection.

| Scene | Actual placed room | Buffer | Shared R/B PNG SHA256 |
|---|---|---|---|
| Cross f1 | 101 | fb0 | a90ba2fd6c7ca7ba24e1802da485e4b0c1dd3e91830c0902f2ea513585ac4985 |
| Cross f1 | 101 | fb1 | 3b232c20784edd7673fb9c9799000a1da4089d1ef6df8076491a26c12dfac037 |
| Forest f2 | 100 | fb0 | 945a82e61b81c6f7e3b5187973323e496f4bf9c922109e92442d92418b47039c |
| Forest f2 | 100 | fb1 | f88957797b1d9e5cdab4e3758624188cc5381465849eb898362fc2b55af5a338 |

`RESULTS.json` binds all four full launch/result receipts, current source/profile, raw main/full ELF/all14 overlay identities, resolved knobs, baseline release/asset manifests, actual disc track, fixture bytes, console executable, template VMU/data, capture helper, exact PID/image, prelaunch/final config, marker, capture timings and both reads/images/raw hashes. Each buffer was stable across two exact-owned reads separated at least0.14 seconds. All four goal runs completed without harness errors or deadline. Exact child exit rc1 after goal stop is preserved separately from harness RUN_COMPLETE.

Requested logical source: `49ad20f9932d638ddb7becf5db6f86b92e0a76a2`. B uses its current g stage. R uses the preserved actual old `5e4de9a0262d3629c9833c959557de198b2e9f0c` on-g base/ELF, explicitly qualified by current49ad R raw-main plus all14-overlay byte proof and common baseline asset identity. No duplicate R stage or new assets were made. Shared asset manifest SHA256: `de1f410a4c2f6175a728ff50fee8a555db20b5fa76873733eab2659647617830`.

Each launch used `FP_NOLIMIT=0` and a fresh owned config with explicit `aica.LimitFPS = yes` authored and checked before Popen; that config remained unchanged through capture/final inspection. The shared template was not edited. All four guests were serial under one owned worker lock, shared stat3 slot, trace16 slot and exact-child55s guard, with45s harness ceiling/period0/marker stop/grace2. Nine host controls pass. No reruns were used.

Evidence root: `C:\Flycast-Evidence\re4-dreamcast\world-emit23-takeover\49ad20f9\current-stills`. Capture tags: `R-f1-limited-r1`, `B-f1-limited-r1`, `R-f2-limited-r1`, `B-f2-limited-r1`. Images reside under each `captures\TAG\freeze330-frames\{first,second}\fb{0,1}.png`; raw RGB565 counterparts and original logs remain private and preserved.

This qualifies **visible fixed authored scenes only**. Freeze330 holds the game thread before frame completion; last completed world328 is the pinned source-call-order relation, not a counter independently sampled by this wrapper. No strict completed actor/viewport/presentation/upload/full-runtime-pose proof is claimed. The withdrawn current49ad observer was not used. These stills do not close the strict Mendez material-pair failure or establish private QA, release, hardware or performance acceptance. The sealed24-gate pre-repair aggregate remains unchanged.

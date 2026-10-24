# First-stage river location audit — 2026-10-24

**Location: UNKNOWN. No room-specific repair is admitted by this evidence.**

The frozen issue 55 snapshot says “It also happens at the first stage, the river carries no watter.” This is a separate sentence after four comparison-image links. It supplies no room code, player position, event, chapter subsection or explicitly identified first-stage image. The frozen comment only acknowledges missing river/waterfall water; it adds no location. This audit uses the existing local snapshot, not a fresh network read.

What the existing local images establish:

- `fix-water-traps23/stills/r10c-river.png` shows a wooden waterwheel/dam with a steep rocky bank. It is a historical comparison composite labelled GameCube (issue 55), Dreamcast extension off and on.
- `fix-water-traps23/stills/r10e-river.png` shows an enclosed cave river and tiered rock formations. It is another historical comparison composite. Neither still is explicitly tied to the separate first-stage sentence.
- `water-20261016/fm-f108/capture/shots/t0056/frames/fb0.png` shows a rope suspension bridge. The capture log explicitly binds its warp to room 108 at line 329. This authenticates that old reference's room, not the reporter's location.

Actual source identity and the limits of room names:

The clean, read-only water-rain24 source is `bca44d58a1fa0a51fd87ba94deba8cba925c8998`. `src/game/water_ps2_table.inc` has two generated room 108 / area 1 rows referencing `r108.ps2.eff0`, SST 5 records 1 and 2. This is an existing PS2-derived water-table reference, not a new payload ancestry proof or an identification of the issue location. The historical `water16.md` calling room 108 a river is therefore a concrete candidate, not enough to resolve the report.

There is also a distinct early-room candidate: `src/st1/r100.cpp` describes the village approach, police car bridge and ravine (lines 51–52), registers a pond render target, and describes bridge areas/events (line 1366 onward). These are controller/source landmarks only. They neither bind the reporter sentence to room 100 nor prove PS2 water ownership or authorize a GameCube render fallback. `src/st1/r108.cpp` also labels its room as the church/puzzle/bell, illustrating that a single room can contain several landmarks; names alone are insufficient. The absence of room 100 from this particular generated water table is not proof that the reported river is room 100, nor proof of missing PS2 content.

The scoped local stills and metadata supply no positive exact landmark match for the separately reported first-stage river. No exhaustive machine-wide image search is claimed. The missing evidence is either a reporter-identified frame of that river or an exact room/position/event description. Only after that match should the existing PS2 room/container geometry and source owner be checked for a repair. Comparison images may help location; they are never PS2 ancestry proof.

`READBACK.json` contains twelve input hashes, image dimensions, the exact room 108 warp row and the scope. Its SHA256 is `2d415cd59104baf69a5c11b1f4f78a87555001c3b5763d79e89712e6566070a5`. Host analysis used a 256 MiB address-space cap and peaked at 17,152 KiB RSS. An initial readback attempt stopped when Git's index helper could not create a thread under the cap; the successful readback used one index thread. Neither attempt changed source or evidence.

No network, emulator, GameCube asset playback, source edit, converter, SDK, asset regeneration or large-file census was used. Prior evidence remains untouched. This audit does not overlap rain, GC filter or culling claims.

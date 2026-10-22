# Actual run 293: normal exit proof and second bell

Run 293's harness result records RUN_COMPLETE, elapsed 18.3 seconds, emulator_exited true and early_emulator_exit 0. The watcher receipt records process_exited true, exit_age null and a generic AssertionError after its last resource sample at process age 18.0478. In watcher v3, the unconditional `verify()` after the WaitForSingleObject loop queries creation time and full image path again, even after the retained process handle is signaled. This is the concrete post-exit verification failure path. The generic assertion does not establish which of GetProcessTimes or QueryFullProcessImageName failed.

The next supervisor should preserve the last successful live PID/path/creation-time verification, use the retained handle's signaled state plus GetExitCodeProcess (exit code not STILL_ACTIVE) and record observed exit age. It need not query an image path after exit. Add a mocked ordinary-close case in which the name/time query becomes unavailable after termination; earlier mocks allowed those queries forever. Preserve all live-process identity checks and exact owned termination checks.

The actual control trace refused the South bell shot: source frame 29080, physical ray miss 49.49, but laser_target `0x8caf2460` was Garrador rather than bell hit body. Zero shots were recorded. This is correct guard behaviour, not successful bell qualification. The exact closed state is source 29083, health 1200/90, boss 4000 and handgun 9+25. State SHA-256 is `ffccc76c0546a8a200ad5dd398317b7abc345df8f7881f884f26fb168ee3ef24`; ELF remains `4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f`.

A fresh read-only census decoded that immutable save, matched its checkpoint hash and anchored RAM with four exact frozen ELF code signatures. `closed293-original-bells.json`, SHA-256 `53f2ed1dddcbaac9a98e9b61f0a1c68c1c7c3a43d69a110646cc52e4d9f60e69`, confirms both original bells are present and unbroken:

- South object `0x8caddab8`, hit body `0x8cc28b00`, position (26972,178,-50004), hit world center (26972,-472,-50004), timer 0.
- North object `0x8cadd6e0`, hit body `0x8cc27d20`, position (27273,178,-33277), hit world center (27273,-472,-33277), timer 0.

Each hit body has id/type 4d01, part 1, offset (0,-650,0), width 300 and height 50. Frozen source `src/st2/r201.cpp:239-255` creates North with rotation Y=PI and South with rotation Y=0. Do not copy South identities/rotation into a North controller.

From exact closed hero position (18679.855,-2000.004,-44815.254), the North bell has planar bearing +0.640134 radians and range 14386.57. The current boss center is approximately 333 units from the hero-to-South line and 6359.96 from the hero-to-North line. These are planar center projections, not collision, line-of-sight, muzzle geometry or ballistic acceptance.

An ordinary alternative is to align and aim at the North bell from the current West position before adding another traversal, using the exact North hit body for the physical laser predicate. The current boss center does not occlude that planar line as it does the South line, but walls, height, range, animation and the actual weapon ray remain guest gates. Preserve all ammo, injury, phase, time, resource and exact-state guards. No shot or relocation is authorized by metadata alone; castle21 already owns the continuing ordinary-control work.

This lane only read existing run results and decoded the closed state into a small owned metadata artifact. No guest, input, process termination, game/controller/source/state write, release or physical Dreamcast test was performed here.

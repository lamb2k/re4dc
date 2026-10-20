# QA menu close watchdog repair

The Test 21 QA tester reported a source `main.cpp(548)` HALT when closing
Diagnostics in r11e, before the El Gigante fight. The preceding slowdown is
separate; its bounded motion-data repair is recorded in R11E-IO-20261020.md.

`qa_poll` intentionally stops the frame loop and sets the source no-hang-check
bit while the menu is open. Vblank continues incrementing `vsync_cnt`. On exit,
the original code restored the bit without resetting this presentation counter.
If the menu accumulated at least 3,600 retraces, the next retrace could run the
original hang detector against the intentional pause and halt immediately.

The QA-only repair resets `vsync_cnt` before restoring the previous check bit.
The ordinary hang detector, its threshold, the original bit state, and unrelated
system flags are preserved. This does not alter the release path when
`QA_MENU=0`, gameplay state, source events, assets, or the diagnostic menu.

`python3 port/dreamcast/tools/d367/qa20/test_menu_heartbeat.py` compiles the actual
source watchdog and retrace functions, plus the pause-exit statements, with host
AddressSanitizer and UndefinedBehaviorSanitizer. Its 21 cases reproduce the old
long-pause close, cover the boundary, preserve flags, and require a real stalled
gameplay frame still to halt. This is a host source check, not a Dreamcast test.

The fixed QA program is built with the original resolved knobs. A private RAM
image contains its matching boot and all fourteen overlays, with the qualified
hot-motion data. A real owned-window L+R+Down chord opens the in-game menu; normal
directional/A input selects Diagnostics. Two bounded state-chained Flycast runs
hold the menu beyond sixty seconds: source frame446 remains stopped while the
original retrace counter rises to3,896. The saved states retain five exact fixed
boot-program anchors. No host writes alter game state or the counter.

A third 30.7-second run resumes that exact snapshot. It observes4,048 retraces
before ordinary B returns to the menu and B closes it. The next observation has
the original gameplay flags0x800 and counter1. Gameplay then advances446→1,233,
including ordinary forward/back movement, with unchanged health and phase and
no HALT. Final saved-state counter is0; both original guards remain active in
normal play. This is a Flycast runtime qualification, not console acceptance.

With QA_MENU=0, the complete dbgwarp translation unit preprocesses byte-identical
before/after this repair using the same compiler arguments (768,625 bytes,
SHA256b664421d2d443e07f9639e2d7ae54482584736acd6b4b60855cd38fa34906a9b).
No redundant whole-program off build was made; this is not a linked-ELF identity
claim. Console confirmation remains pending. No replacement tester package or
release is published by this lane.

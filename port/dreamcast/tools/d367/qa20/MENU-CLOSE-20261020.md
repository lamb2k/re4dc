# QA menu close watchdog repair

The Test 21 QA tester reported a source `main.cpp(548)` HALT when closing
Diagnostics in r11e, before the El Gigante fight. The preceding slowdown is
separate and remains under investigation.

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

Runtime qualification, disabled-path program identity and console confirmation
are pending. No replacement tester package or release is published by this lane.

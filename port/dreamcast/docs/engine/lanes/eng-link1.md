# eng-link1 / ql-core hand-back (2026-11-22): the console link over the broadband adapter, in dc-qalink 0.2

**Status: finished, unaudited.** Lanes eng-link1 (stopped at the RE4 pause) and ql-core (plan L1, which finished it).
Branch `lane/eng-link1`; dc-qalink `v0.2-bba-loader` pinned as the submodule `port/dreamcast/engine/loader/dc-qalink`.
Full hand-back with evidence paths: `E:\RE4DC-Lanes\ql-core\HANDBACK.md`. Design and results: CONSOLE_LOOP.md sections
15 and 16.

Every time here is **Flycast** (plain build, its broadband adapter or modem emulation), a function check. No number
here is a console number or a speed claim.

## What RE4 has now
- The loader, return stub, client library, transports, protocol and PC tool are dc-qalink's; RE4 keeps
  `engine/loader/selector.c`, `cl_send.c`, `sendable.mk`, `kosfix.mk`, and `tools/consoleloop/consoleloop.py` (a thin
  wrapper of dc-qalink's `pc/dcql_loop.py`). The old copies (`link.c`, `link.h`, `main.c`, `cl_core.*`, `cl_util.c`,
  `client.c`, `cl_client.h`, `host.c`, `testprog.c`, `cl_proto.h`, `cl_handoff.h`, the old host tests) are removed.
- `tools/engine/build_console_disc.sh`: dc-qalink archived at the commit the ref records (as SH4ZAM); `--link <PC
  address>` writes the disc's `LINK.TXT` (adapter, DHCP); `CPCOPEN` (needs `--link`): the Leon scene with `src=pc` and
  the `OPENX` boot file, a file read from the PC in play, must FAIL as `COPENX` does for the disc.

## In Flycast (dc-qalink's side, details in the full hand-back)
- Files from the PC at load time: 1 MiB 3.36 s, 8 MiB 26.8 s, SHA-256 equal.
- Push, verify, run, report, stills (10 of 10), screen grabs, a corrupted image refused, crash, wrecked heap, deadline
  and RESET all back to the loader through the return stub, without a BIOS reboot; the first stage pushing a newer
  loader; a program that ignores RESET ends at "power cycle needed". Flycast does not emulate the SH-4 watchdog.
- The modem path: the same loop over Flycast's modem (180 KB in 46 s), and dc-qalink 0.1.0's example unchanged.

## Old-port parts considered
- The old port's QA link (`game/qa_link.cpp`, `qa_menu.cpp`, `tools/qalink/`): left. It is the in-game command layer
  (plan B8, a later lane), modem only, and the release line keeps it as it is.
- KOS's broadband adapter driver and network stack: taken (the console's own driver, at the edge).
- dcload-ip: taken as ideas only (files served by the PC as `/pc`, console output to the PC), written the loop's way
  (verified images, the hand-off report, the selector's records); its protocol and loader not adopted.

## Not done here / for other lanes
- The memory map owner: the loader's text 299.8 KB, `LOADER.BIN` 308 KB; the stub 2,120 B at the hand-off area
  (+0x1000); the client in an image: see the full hand-back's link sizes.
- Console checks (deferred with the rest): the adapter's real speed; the stub's return on hardware; GDEMU's slot after
  a soft reset; the watchdog; vertical-blank gaps against the watchdog's 20.97 ms.

---
name: dc-qalink-integrate
description: Add the dc-qalink modem QA/telemetry link to an existing KallistiOS (KOS) Dreamcast game - Makefile, dial, per-frame poll, telemetry rows, a command handler with PING and a GOTO teleporter, an on-screen link status line - then verify it in Flycast's emulated modem. Use when asked to add remote QA, telemetry, a debug link or "the qa link" to a KOS project.
---

# Integrate dc-qalink into a KOS game

Reference: the package README (API and wire tables) and `example/main.c` (a complete small program). Don't repeat
them; copy from them.

## Steps

1. **Find the build and the loop.** The KOS Makefile (`include $(KOS_BASE)/Makefile.rules`) and the main loop (the
   function that waits for vblank / calls `pvr_scene_begin` each frame).
2. **Makefile:** put `all:` first, then
   `DCQL_DIR := <path>/lib`, `include $(DCQL_DIR)/dcql.mk`, add `$(DCQL_OBJS)` to the objects, `$(DCQL_CFLAGS)
   -I$(DCQL_DIR)` to the compile of files that call it, `$(DCQL_LDFLAGS)` to the link. Remove any `-lppp`.
   QA builds: `make DCQL_ENABLE=1`. The default (0) compiles every call to nothing.
3. **Start:** at boot (or from a debug-menu item): fill a `dcql_config_t` (host = relay address or `"peer"`; under
   Flycast `lport = 52042`), `dcql_set_command(handler, NULL)`, `dcql_start()`.
4. **Per frame:** `dcql_poll()` once, on the game thread.
5. **Telemetry:** once a second `dcql_telemetry("frame fps=%u scene=%d\n")` (count frames over the last second;
   one `name k=v k=v` line per subsystem). Log lines worth seeing remotely: `dcql_log()`.
6. **Commands:** in the handler, `GOTO <preset>` calls the game's own "jump to" (level select, warp, checkpoint
   load) and answers with `dcql_answer(id, ok, ...)`. Add `PRESETS` to list them. Return 0 for verbs you don't know.
   `PING`, `MARK`, `STATUS` are built in.
7. **Status line:** draw `dcql_state_text()` somewhere on the debug overlay (DIALLING n/3, PPP, UP ip TO peer,
   FAILED, LINE DROPPED); a button calls `dcql_start()` to redial after FAILED / LINE DROPPED.
8. **Build** with `DCQL_ENABLE=1` and once with it off (the link must vanish: compare `sh-elf-size`).
9. **Verify in Flycast:** run `relay/dc_qalink_relay.py serve` on the PC, emu.cfg `[network] DCNet = no`, console
   `host` = the PC's LAN address, `lport` 52042. Expect the status line to reach UP, then
   `pc/dc_qalink.py send PING` answers `A c1 OK PONG`. Only then try real hardware (skill dc-qalink-pi-setup).

## Do not

- Call anything that blocks on the game thread: no sockets, no `thd_sleep`, no waiting for UP in a loop.
- Send rows over 1200 bytes as one datagram (`dcql_send_raw` refuses them; telemetry/log split themselves).
- Send telemetry every frame: once a second is the budget at 33.6 kbps (rows are skipped, not queued, when behind).
- Call the send functions from two threads (the rings are single-producer).
- Ship it in a retail or public build: keep `DCQL_ENABLE` off there and check the size.
- Link `-lppp` as well, or drop the `--wrap` flags (the hardened modem/PPP paths depend on them).

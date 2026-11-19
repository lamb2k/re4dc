# Lane eng-loop: console loader over the QA link

Brief 2026-11-19 (integrator). Kind: PC-only tooling. Design: [../CONSOLE_LOOP.md](../CONSOLE_LOOP.md).

## State (2026-11-19)

- **Built and host-tested.** Not yet run in Flycast or on the console.
- Loader (`engine/loader/`): KOS d367, 262 KB `LOADER.BIN`. The QA link's console transport copied to `link.c`.
- PC sender (`tools/consoleloop/consoleloop.py`): ELF or bin, deflate, windowed chunks, resume, run, report.
- Host tests (`tools/consoleloop/test_consoleloop.py`): the loader's own protocol code built for the PC (`cl_host`,
  ASan + UBSan) behind a simulated bad line. 16 of 16 pass, including the corruption controls.

## Numbers

| What | Number | Tier |
|---|---|---|
| Console to Pi, line full (`PCS SNAP` captures) | 1.38 to 1.39 KB/s UDP payload | console (11-11 logs) |
| Pi to console | not measured: only commands ever went down | - |
| E0 bench image (270,300 B) deflated | 178,817 B: 2.2 min at 1.36 KB/s | estimate |
| Room pack, village cross, LZMA | 3.44 MB: 42 min | estimate |
| Host test, line simulated at 1390 B/s each way, 300 ms latency | 1263 B/s program bytes (96% of what the line carries) | host model |

## Files

- `engine/loader/`: `main.c` (loader), `link.c` / `link.h` (modem, PPP, UDP), `cl_core.c` / `cl_core.h` (protocol
  state machine), `cl_util.c` (CRC-32, SHA-256, inflate, framing), `cl_proto.h`, `cl_handoff.h`, `client.c` /
  `cl_client.h` (program side), `testprog.c` (the test program), `host.c` (PC build), `Makefile`.
- `tools/consoleloop/`: `consoleloop.py`, `simlink.py`, `test_consoleloop.py`.
- Evidence and the staged disc: `E:\RE4DC-Lanes\eng-loop` (maintainers' machine).

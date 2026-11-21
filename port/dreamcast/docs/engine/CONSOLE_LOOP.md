# Console loop: send a program to the Dreamcast over the QA link

Lane eng-loop, 2026-11-19. Design first; the code is in `port/dreamcast/engine/loader/` (console) and
`port/dreamcast/tools/consoleloop/` (PC). Built and host-tested on the PC. Lane eng-loop2 (2026-11-20): run in the
console-like Flycast (section 8, results) and the one console disc with every engine scene (section 10). Not yet run
on the console.

## The point

- The owner puts one **loader disc** on the SD card once and boots it.
- After that the PC sends a program over the existing QA link (Dreamcast modem, DreamPi), the console checks it,
  runs it and hands its report back. Nobody touches the pad.
- Only code travels. Room packs stay on the disc.

## 1. What the link carries (measured)

Source: the console sessions of 11-11 and 11-12 (`E:\RE4DC-Lanes\perf30\console-*`), Pi capture logs with the exact
packet journal (`X28` rows), and the console's own `link tx=` counters timed by its own clock.
Tool: `E:\RE4DC-Lanes\eng-loop\s\throughput.py` and `perfile.py`.

| Direction | Number | Tier | How |
|---|---|---|---|
| Console to Pi, line full | **1.36 to 1.39 KB/s** UDP payload | console | 10 captures where `PCS SNAP` parts kept the console's send queue full (bulk skips rising): 1357 to 1393 B/s at the Pi, each over 22 to 25 s (two more with idle gaps read 0.79 and 0.81) |
| Console to Pi, normal play | 1.2 to 1.3 KB/s | console | 40 other captures (telemetry plus log lines, 31 to 33 s each) |
| Console to Pi, 1 s intervals with the queue full | median 1379, p10 1062, p90 1804 B/s | console | 137 intervals of the `link tx=` counter (the 1 KiB modem buffer adds jitter) |
| Pi to console | **not measured** | - | only commands ever travelled down (at most 44 B/s seen). The loader's first transfer is the measurement |
| Command round trip | median 0.76 s, up to 14 s behind a full send queue | console | Pi `C` row to `A` row |

- The modem's connect rate was never logged on the console (Flycast reports 33600 bps). 1.39 KB/s of payload is about
  12 to 14 kbit/s on the line, so the console probably connected well below 33.6k, or its send path is the limit.
- For planning, down = up = **1.36 KB/s of program bytes** (estimate): 1.39 KB/s less this protocol's 2% headers.
  The table also gives a pessimistic 1.0 KB/s and the 33.6k ceiling (3.3 KB/s).

Compression, measured on real images (`s/ratio.py`): raw deflate level 9 and raw LZMA.

| Payload | Bytes | 1.0 KB/s | **1.36 KB/s** | 3.3 KB/s |
|---|---|---|---|---|
| E0 bench image (e0b, raw) | 270,300 | 4.5 min | **3.3 min** | 1.4 min |
| E0 bench image, deflate (66%) | 178,817 | 3.0 min | **2.2 min** | 0.9 min |
| A 1.2 MB program, raw | 1,200,000 | 20 min | **14.7 min** | 6.1 min |
| A 1.2 MB program, deflate (66%, estimate) | 792,000 | 13 min | **9.7 min** | 4.0 min |
| Game image (lab33, raw) | 3,488,304 | 58 min | **43 min** | 18 min |
| Game image, deflate (56%) | 1,955,737 | 33 min | **24 min** | 10 min |
| Room pack, village cross (raw) | 7,765,688 | 129 min | **95 min** | 39 min |
| Room pack, village cross, LZMA (44%) | 3,442,201 | 57 min | **42 min** | 17 min |
| Room pack, farm hay-fork (raw) | 9,166,408 | 153 min | **113 min** | 46 min |
| Room pack, farm hay-fork, LZMA (39%) | 3,529,022 | 59 min | **43 min** | 18 min |

Add about 20 to 40 s to dial before a transfer and again after each run (the loader redials when the program
hands back).

**Decisions from the numbers**
- **Code travels, packs do not.** A pack costs 40 minutes or more even compressed; the loader disc carries them.
- **Deflate, not LZMA.** On code, LZMA saves 10% more (13 s on the E0 bench image); its decoder is several times
  larger and slower. Deflate's decoder is about 300 lines of C. LZMA only matters for packs, which stay on the disc.
- A delta against the image already on the console would save most of an iteration's transfer. Not built: the
  console keeps no image across a run. Listed under next steps.

## 2. Pieces

```
PC: consoleloop.py ──ssh──> Pi: relay (python3 from stdin, UDP 52060) ──PPP over the modem──> console: loader
                                 (qalink_pi.py on 52040 keeps running; nothing is installed on the Pi)
```

- **Loader disc** (`engine/loader/`): a small KOS program, its own GDEMU image. It dials, brings up PPP, beacons
  `HELLO` once a second and waits. It shows its state on screen.
- **PC sender** (`tools/consoleloop/consoleloop.py`): builds the image from an ELF, compresses it, sends it, runs
  it, waits for the console to come back, collects the report.
- **Relay**: a 40-line Python program the sender pipes to `ssh <pi> python3 -` each session. It binds UDP 52060 on
  the Pi and copies datagrams to and from the ssh pipe. The DreamPi itself is not changed; `qalink_pi.py` (UDP
  52040) can keep running beside it.
- **Client library** (`engine/loader/client.c`, optional, linked into the sent program): reads its arguments, writes
  its report into the hand-off area and returns to the loader on exit, crash or timeout.
- `--udp host:port` talks straight to a console without the relay (Flycast's modem emulation, where the PC is the
  PPP peer, or a routable console address).

## 3. Protocol (UDP port 52060, little-endian)

Every datagram is at most 1200 bytes (the console has no IP fragment reassembly; the qalink limit):

```
0  'C' 'L'   magic            8  u32 a      (chunk index, offset, code ...)
2  u8  1     version          12 u16 len    payload bytes
3  u8  type                   14 u16 b      (count, flags ...)
4  u32 session                16 payload    then u32 CRC-32 of bytes 0..16+len
```

A datagram whose CRC fails is dropped and counted; nothing is parsed before the CRC passes.

| Type | Way | Meaning |
|---|---|---|
| `HELLO` 0x01 | console to PC | beacon (1 s idle, 3 s busy): loader build, boot count, state, transfer progress, pending report (run id, length, CRC, how the run ended) |
| `ACK` 0x02 | console to PC | `a` = first chunk not held; bitmap of the next 2048 chunks; have count, bad-CRC and duplicate counts |
| `VERDICT` 0x03 | console to PC | result of the whole-image check: 0 = verified, else the reason (CRC, inflate, length, SHA-256, size, address) |
| `REPORT` 0x04 | console to PC | 1024 bytes of the last run's report at offset `a` |
| `EXEC` 0x05 | console to PC | sent just before the jump |
| `ERR` 0x06 | console to PC | refusal with a code (`RUN` before verify, unknown session, no memory ...) |
| `LOAD` 0x10 | PC to console | session, compressed and raw length, chunk size 1024, codec, SHA-256 of the raw image, CRC-32 of the compressed stream, load address, deadline, arguments |
| `DATA` 0x11 | PC to console | chunk `a` |
| `RUN` 0x12 | PC to console | run the verified image of this session |
| `REPQ` 0x13 | PC to console | send `b` report blocks from offset `a` |
| `REPDONE` 0x14 | PC to console | the PC holds the report; clear it |
| `PING` 0x15 / `ABORT` 0x16 / `VERIFY` 0x17 | PC to console | beacon now / drop the transfer / repeat the verdict |

**Transfer**
- Chunks of 1024 bytes; 98% of each datagram is program.
- The PC keeps a window of chunks in flight (start 4, 2 to 16), opened one chunk per clean window and halved on a
  loss. The window stays near the line's delay times its rate, so the Pi's PPP queue never overflows.
- The console acknowledges every 4 new chunks and 150 ms after the last one. Acks carry a cumulative point and a
  bitmap, so one lost chunk costs one resend. A chunk the PC has not seen acknowledged in 2.5 round trips (at least
  1.5 s) is sent again.
- **Resume after a dropped link:** the loader keeps the partial image in RAM and redials. A `LOAD` with the same
  SHA-256, lengths and stream CRC (even from a new PC session) answers with the chunks it already holds; only the rest
  travels. A different image starts over.

**Checks before anything runs**
1. Per datagram: CRC-32.
2. Whole compressed stream: CRC-32 against `LOAD`.
3. Inflate with bounds checks on every read and write; the output must be exactly the declared raw length.
4. SHA-256 of the raw image must equal the one in `LOAD`.
5. Load address 0x8C010000 and the image must end below the hand-off area.

Only a session whose image passed all five holds `verified`. `RUN` on anything else is refused with `ERR`. The jump
uses only the verified buffer.

## 4. Running the program and the hand-off area

- **Hand-off area:** the top 128 KiB of RAM, 0x8CFE0000 to 0x8D000000. KallistiOS puts the main stack at
  `arch_stack_16m`, a weak symbol, and keeps the heap below the stack. The loader and every client program define it
  as 0x8CFE0000 (and `arch_stack_32m` as 0x8DFE0000, so the 16 MB check still finds the mirror), so neither touches
  the area. A program built without the client library may overwrite it; the loader then sees no valid report.
- **Contents:** a header (magic, version, header CRC, boot count, run id, state, exit code, deadline, link settings,
  the PC's arguments, crash registers) and a report of up to 126 KiB with its own CRC. Run states: `RUNNING`,
  `DONE`, `CRASHED`, `TIMEOUT`.
- **Run:** the loader writes the header (`RUNNING`, run id = session, arguments, deadline), sends `EXEC`, hangs up
  the modem (so the program may dial its own QA link), and calls `arch_exec_at` with the verified image.
- **Client program:** `cl_init()` checks the header and starts a watchdog thread for the deadline. `cl_report()`
  appends text. `cl_exit(code)` marks `DONE` and goes back to the loader.
- **Back to the loader, in order of preference:**
  1. Normal exit or deadline (a thread still runs): the client reads `/cd/LOADER.BIN` from the loader disc at
     `cl_init()` (about 300 KB of the program's heap) and jumps to it with KallistiOS's own trampoline, after
     stopping the graphics chip, controller DMA and sound as `arch_abort` does.
  2. Crash (unhandled exception, double fault, `arch_abort` when wrapped): the exception handler writes the
     registers and `CRASHED`, then jumps to the preloaded loader the same way. No disc access in that context.
  3. No preloaded loader, or interrupts dead: BIOS reboot (`0xA0000000`). Whether GDEMU then boots the same image
     or openMenu is a **console check** (below). If it boots openMenu, the loop needs a power cycle and the menu pick.
  4. A hang with interrupts off: power cycle (owner or smart plug). The SH-4 hardware watchdog tops out at about
     21 ms, too short to use without the program's help.
- **Loader start:** before its heap grows, the loader reads the hand-off header. A valid header with `DONE`,
  `CRASHED` or `TIMEOUT` and a valid report CRC becomes the pending report (in `HELLO`). `RUNNING` means the program
  came back without the client (or rebooted): reported as `LOST`. An invalid header (power-on) starts fresh.
- After `REPDONE` the loader clears the report, so the next run cannot be confused with this one.

## 5. Loader on the console

- KallistiOS d367 (the release toolchain). The link is the QA link's console code (`game/qa_link.cpp`, the review28
  and fix26 paths), copied to `engine/loader/link.c`: KOS libppp compiled from source with the same four
  redirections (a sleeping receive loop that also moves datagrams, a modem write that cannot spin on a dropped line,
  counted reads, bounded PPP wait), static thread stacks, no `net_init()`. Larger rings (64 KiB in) because data
  now flows down.
- Settings: `/cd/LINK.TXT` (same lines as the QA link's `link.txt`: `number`, `host`, `port`, `lport`). Defaults:
  dial 1111111, learn the Pi from its first reply, port 52060 both ways.
- Dials at boot, 3 tries, then again every 30 s for ever; A redials at once. A dropped line redials and keeps the
  partial image.
- The screen: title and build, link state (`DIALLING 1/3`, `PPP`, `UP <ip> TO <pi>`), `WAITING FOR THE PC` with a
  turning marker and the beacon count, transfer progress (chunks, KB, KB/s), `VERIFYING`, the verdict, the last run's
  result.
- Program size limit: the image must end 0x11000 below the hand-off area (the loader's stack holds the exec
  trampoline during the copy), and the compressed plus raw copies must fit in the loader's heap: about 9 MB raw for
  a deflated image.

## 6. What it does not do

- It does not keep the line up across the jump. A program that wants live telemetry dials its own QA link
  (the bench's `qa_link_bench.cpp` path) after the loader has hung up.
- It does not send room packs (section 1). A program that needs new packs needs a new loader disc.
- It does not prove anything about the console's frame budget. It only removes the disc swap.

## 7. Host tests (PC, done)

`tools/consoleloop/test_consoleloop.py`: the loader's own `cl_core.c` / `cl_util.c` built for the PC (`cl_host`,
AddressSanitizer and UBSan), the real `consoleloop.py`, and `simlink.py` between them (loss, one-bit corruption,
duplicates, reordering, a rate-limited line with a bounded queue, dead windows). Program: the E0 bench image
(270,300 bytes, deflated to 178,817). 16 of 16 pass (commit 907bb1a24, `E:\RE4DC-Lanes\eng-loop\evidence\host-q3`).

| Case | Result |
|---|---|
| Inflate equals zlib: 5 inputs x 6 encodings (stored, fixed, dynamic, Huffman-only, RLE) | 30 / 30 |
| Inflate on 155 malformed streams (truncations, random bytes) | all refused, no crash, no truncated stream accepted |
| SHA-256 equals hashlib; datagram CRC catches all 8,352 one-bit flips of a data datagram | pass |
| Clean line: send, verify, run, report back | image byte-identical, report CRC ok |
| 10% loss, 5% corruption, 5% duplicates, 150 ms reordering, both ways | pass; the console dropped 8 corrupt datagrams on CRC |
| Line dead for 12 s mid-transfer | resumed with `LOAD`, pass |
| PC sender killed halfway, restarted with a new session | console held 82 of 175 chunks; only the rest travelled |
| **Control:** stream damaged after its CRC was taken | `VERDICT stream crc`, `RUN` refused, nothing ran |
| **Control:** a valid stream of different bytes under the declared SHA-256 | `VERDICT sha256`, `RUN` refused, nothing ran |
| **Control:** the right bytes under a wrong declared SHA-256 | `VERDICT sha256`, `RUN` refused, nothing ran |
| **Control:** image larger than the console allows | refused at `LOAD` |
| Outcomes through the hand-off area: crash, deadline, no client | `CRASHED`, `TIMEOUT`, `LOST` |
| Line at the measured 1390 B/s each way, 300 ms latency, 1% loss, 60 KB image | 1263 B/s of program bytes: 96% of what the line carries (host model) |

## 8. Checks still to run

**Flycast (modem emulation, PC as the PPP peer; the staged `flycast` image has `LINK.TXT` with `host 192.168.1.191`
(the PC in the lab33 twin; change it if the PC moved) and `lport 52062`; the sender runs `--udp 127.0.0.1:52062 --bind 52060`):**
1. The disc boots to `DIALLING`, then `UP`, then `WAITING FOR THE PC` with the beacon count rising.
2. `consoleloop.py --udp <flycast>` `status` sees `HELLO`; `run` sends the client test program, the console shows the
   progress, `VERDICT 0`, `EXEC`, and the test program's report comes back after the loader redials.
3. Control: `run testprog.elf --corrupt payload` is refused with `VERDICT sha256` (and `--corrupt stream` with
   `stream crc`); the screen shows `REFUSED` and never leaves the loader.
4. Crash control: `run` the test program with `crash` in its arguments: the report says `CRASHED` with a PC value.
5. Deadline control: `hang` with a 20 s deadline: the report says `TIMEOUT`.
6. Resume: kill the PC sender halfway and start it again; only the missing chunks travel.

**Flycast results (lane eng-loop2, 2026-11-20; console-like Flycast `fly1` with the GDEMU disc profile; loader
`98aced1dc` plus the client changes of this lane; evidence `E:\RE4DC-Lanes\eng-loop2\evidence\k*`).** How Flycast
stands in for the Pi: its modem emulation is the PPP peer and the console's UDP leaves through a PC socket, so the
relay runs on the PC (`consoleloop.py relay-local`, started before the loader boots: a Windows socket that once took
an ICMP port-unreachable stops passing datagrams down), and the sender talks to it (`--udp 127.0.0.1:52059 --bind 0`).

| Check | Result | Control |
|---|---|---|
| 1. `UP`, `WAITING FOR THE PC`, `status` sees `HELLO` | pass (`k1-status.log`, `shots\k1-waiting.png`) | - |
| 2. `run testprog --args report` | pass: `DONE`, exit 0, report CRC ok (`k2-report`) | - |
| 3. Refusals | `--corrupt payload`: `VERDICT sha256`; `--corrupt stream`: `stream crc`; both "refused: not verified", nothing ran (boot count unchanged) | they are the controls of check 2 |
| 4. Outcomes | `crash`: `CRASHED`, event 180, PC in the program; `hang` with 20 s: `TIMEOUT`; `return`: `DONE` exit 0; the loader waiting again after each (boot count +1) | each is the others' control. Flycast does not raise the address error of a misaligned write (the first crash run came back `DONE`): the test program falls through to an illegal instruction |
| 5. Resume | sender killed at 66 of 128 chunks; the restarted sender's first ack starts at chunk 68 | a different stream (stored, not deflated) after the kill: the first ack starts at 0 |
| Host tests after the hand-off header change | 16 / 16 (`evidence\host-tests`) | as section 7 |
| Engine images through the loop (step 6) | the bench (`SENDABLE=1`, `root=E0S`, schedule `c0 f0`) and the E1 image (`root=E1`, village) sent, run and their reports back: 2 `WINDOW` rows, `SCHEDULE DONE`; 640 `ROW` lines, `E1 END` (`k6-bench`, `k6-e1`) | - |

Link rates, **Flycast** (not a console figure): down 3.1 to 3.9 KB/s of deflated bytes, 5.0 to 6.2 KB/s of program
bytes (130 to 373 KB images, 34 to 95 s); reports up 1.32 KB/s (100 KB in 75.8 s) and 1.46 KB/s (57 KB, 39 s).
Flycast's modem reports 33600 bps; the console's rate is still unknown.

The console-like Flycast also showed a console failure mode: a program that reads the disc sector by sector after
the loader's jump stopped with "SH4 exception when blocked" under the GDEMU profile (stale GD DMA completions). The
loader, the test program and every `SENDABLE` image now link the release game's KOS disc fixes (`kosfix.mk`); the
unfixed test program is the control (it stops; the fixed one returns `DONE`).

**First console run (owner powers on, picks the loader in openMenu once):**
1. The loader dials the DreamPi and the beacons reach the Pi through the relay while `qalink_pi.py` runs.
2. **Downlink rate**: the PC's transfer report of the E0 bench image (first real measure of Pi to console).
3. The client test program's report comes back (normal exit path).
4. The crash path returns to the loader without a hand on the console.
5. A BIOS reboot (`reboot` argument to the test program): does GDEMU boot the loader again or openMenu?
6. The E0 bench image (no client) runs from the loader as it does from its own disc; then power cycle.

## 9. Next steps (not built)

- Delta transfer against the last image the console ran (the hand-off area could keep its hash; the image itself
  would need RAM the program does not use).
- A smart plug for the cases that need a power cycle (`Dream-TOS` testing notes).
- A broadband adapter or serial cable path (dcload-ip / dc-tool), many times faster, if the owner has one.

## 10. Engine images through the loop, and the one console disc (lane eng-loop2)

**An engine image made send-able: `SENDABLE=1`** (`engine/loader/sendable.mk`, included by `engine/bench/Makefile`
and `engine/game/Makefile`; no image source changes). It links the client library, the KOS disc fixes (`kosfix.mk`)
and `cl_send.c`. Booted from its own disc the image runs as before: `cl_init()` finds no `RUNNING` hand-off and
everything stays off. Started by the loader or the console disc's selector, a constructor turns on:
- **the report:** a dbgio handler in front of the serial one copies the image's own text lines into the hand-off
  report and passes everything on (serial unchanged). Arguments: `rows=skip|compact|keep` for `ROW` lines (compact
  drops the field names), `skip=<prefix>,..` for other lines (the console disc skips the bench's `MEMBLK` lines);
- **the end:** the image's last line (`SCHEDULE DONE`, `E1 END`) hands in `DONE`, exit 0, once the image has printed
  nothing for 1.5 s (the fight and boss images print their event lists after `E1 END`); a refusal line
  (`SCHEDULE REFUSED`, `M1 native pack REFUSED`, `STACK GUARD BROKEN`, `E1 draw: renderer refused`,
  `E1 load: missing / read failed / bad DRS`) hands in exit 1, with the renderer's pack-loader stage when the image
  has one. Crash and deadline as section 4;
- **the data root:** `root=E1` makes `/cd/<path>` open `/cd/E1/<path>` first, then the disc root
  (`-Wl,--wrap=fs_open`); `root=E1H:E1` tries both folders in order (the hill scene's `HILL` file sits alone in
  `E1H`). `/cd/LOADER.BIN` is never redirected.
- The watchdog sleeps once to the deadline and the end thread waits on a semaphore, so neither wakes inside the
  timed pictures.

**The console disc** (`tools/engine/build_console_disc.sh`, `engine/loader/selector.c`):
- One GDEMU disc (standard layout) from a clean checkout of a commit (default `origin/engine`; `git archive` plus the
  SH4ZAM submodule at the recorded commit) and the private packs, which never enter git. Output folder: the four
  GDI files, `SHA256SUMS`, `MANIFEST.txt` (commit, program hashes, every input's hash, the disc tree), `SCENES.TXT`,
  the ELFs, `KEEP`.
- `1ST_READ.BIN` and `/LOADER.BIN` are the selector. It runs every line of `/SCENES.TXT` in order: checks the scene's
  files, writes the hand-off area (`RUNNING`, arguments, deadline, a report cap), jumps to `/PROG/<image>.BIN`. The
  image runs from its folder and hands back through the client library to `/LOADER.BIN`, the selector again, which
  reads the report and keeps the scene's summary in a journal above the report cap (top 24 KiB of the hand-off area).
- Scenes, in order: **BENCH** (village cross and hay-fork view, arms `c0 f0 ca c0 cb c0 fa f0 fb f0`, then the
  control window `c0dh`), **LEON** (village route), **HILL** (Leon and Ashley), **FIGHT** (four Ganados),
  **BOSS-BENCH** (El Gigante on the bench, `c0 cn c0 c0dh`), **BOSS** (El Gigante hosted, headless). The E1-family
  scenes run with `NOTRACE`.
- **Summary rows.** Bench scenes: the bench's own `WINDOW` rows (mean, p99, worst, over 14, over 33.3, presented
  intervals over two fields, 600 pictures a window). E1-family scenes: computed by the selector from the image's
  `ROW` lines, pictures 41 to 640 (the lane tools' `budget.py` rows): drawing, busy picture (frame less the pacer's
  and the PVR waits), services, behaviour (mean, p99, worst with its picture, count over the row's budget), and
  late pictures (no pacer wait). The E1 images print a `fields` column but do not count presented fields yet: the
  summary says "fields not counted" rather than "0 over".
- **A scene is FAILED, never skipped:** a missing file (the selector checks the scene's list first), an unreadable
  program, a crash, the deadline, a return without a hand-in (`LOST`), a non-zero exit, a bad report CRC, a refusal
  line in the report, no rows, or no end line. B held during the 3 s countdown before a scene skips it (recorded as
  FAILED, "skipped by the owner").
- **The end:** one summary screen, in pages of 16 lines that change every 10 s (the first line says `FINISHED: n OF
  m SCENES OK`), and on the serial line `CDISC RESULT`, `CDISC SUM` and `CDISC SUMMARY` lines. The images print their
  raw `ROW` lines on the serial line during their run, as on their own discs.
- **A reset during the run:** if main RAM kept the journal the running scene is recorded `LOST` and the run goes on;
  otherwise it starts again. After the summary is shown the journal is closed: the next reset starts a new run.
- Controls: `--drop <disc path>` removes a staged file; `--no-precheck` leaves the refusal to the image itself;
  `--scenes` picks a subset.

**Flycast proof (lane eng-loop2, 2026-11-20; console-like Flycast, GDEMU profile; Flycast ms, not a result).** One
boot ran all six scenes and showed the summary. Bench OK (11 windows; the control window `c0dh` read +5.0 ms and one
interval over two fields, as it must), Leon OK, hill OK, fight OK, El Gigante hosted OK (headless). **El Gigante on
the bench FAILED**: the engine's bench refuses lane eng-boss's `boss2-full.pak` at pack-loader stage 5 (the recorded
input checks); its pack needs a re-bake with the current packer. Controls: `--drop FIGHT/CROSS.PAK` gives FIGHT
"FAILED missing FIGHT/CROSS.PAK"; with `--no-precheck`, `--drop BENCH/FARM.PAK` gives BENCH "FAILED M1 native pack
REFUSED" and `--drop E1/st1/r101.arc` gives LEON "FAILED E1 load: missing /cd/st1/r101.arc". Evidence:
`E:\RE4DC-Lanes\eng-loop2\evidence` (`final-*journal.txt`, `shots\final-*.png`).

## 11. A scene record that proves itself (lane eng-e1k, 2026-11-21)

Status: finished, unaudited. Answers HANDOVERS.md H-016.6 (second E1 audit section 6). Flycast runs are function checks.

**What a timing scene needs to be OK** (`engine/loader/selector.c` `collect`, E1-family scenes), checked in this order
after the existing refusals, pools, exit and CRC:
1. the image's run-kind line: `E1 RUN timing (no trace, no stills)`, or `E1 RUN function (traced|stills): not a timing
   run` (`core/frame.cpp`). A function run (traces formatted inside the pictures, or stills handed over in play) is
   judged on its end line, refusals and pools only; its summary says "not a timing run" and gives no timing rows;
2. the after-play memory line `E1 MEM after play:` (below);
3. the 600 picture rows 41 to 640, each once: a repeated row is counted and fails the scene ("rows: N of 600
   pictures, D repeated"), never summed twice;
4. a drawing image in `presented` mode, a headless one in `tick` mode. A drawing image now always counts presented
   flips (`core/frame.cpp e1_fields_finish`: the mode follows whether the renderer opened, not whether a flip was
   seen), so a drawing failure shows as 0 intervals, not as a silent fall-back to tick mode;
5. zero release-queue drops (`E1 FIELDS ... release queue full N`). A full queue now refuses the release and counts it
   (`core/draw_e1.c e1_present_at_c`); before, it overwrote the oldest queued release while the tail moved past it;
6. 600 measured intervals (a row whose fields column is 0 has no flip).

**After play** (`core/memmap.cpp e1_memmap_after`, printed by the report before its end line): the stack's paint high
water (the deepest any tick reached) and its 1 KiB guard (the lowest 256 words of the 64 KiB painted stack must still
hold the paint; `E1 STACK GUARD BROKEN`, a refusal line, otherwise), the KOS heap's tracked bytes and their peak (kept
by the malloc wrappers through load and play), the sbrk top and its margin to the behaviour arena (sbrk only grows:
after play is the worst), mallinfo, and video memory free (sampled before and after play; the renderer takes video
memory at pack open and no cheap per-tick sample is taken). The selector's summary prints stack, arena margin and video
memory free.

**Controls** (boot files; Flycast test disc c3 of commit 313d1cd71, one boot, eight scenes,
`E:\RE4DC-Lanes\eng-e1k\ev\record\c3-summary.txt`):

| Scene | Boot file | Result |
|---|---|---|
| LEON, FIGHT, BOSS (headless) | none | OK (600 rows, presented / tick, 600 intervals, 0 drops; after play: stack 9,112 / 9,260 / 8,996 B, arena margin 503,808 / 278,528 / 2,125,824 B, video memory free 2,639,720 B in the drawing images, the same as before play) |
| CROWDUP | `ROWDUP`: the row of picture 300 printed twice | FAILED "rows: 600 of 600 pictures, 1 repeated" |
| CNOFLIP | `NOFLIP`: the vblank handler records no flip | FAILED "presented intervals: 0 of 600 measured" (before: tick mode, OK) |
| CQDROP | `QDROP`: picture 300's release refused as if the queue were full | FAILED "release queue drops 1" (flips 639 of 640) |
| CSTACK | `STACKX`: one guard word overwritten at tick 300 | FAILED "E1 STACK GUARD BROKEN: 1 of 256 guard words ..." |
| SHOT | the shot fixture (traced) | OK, "not a timing run", no timing rows |

The test scenes are added by the lane's disc wrapper (`E:\RE4DC-Lanes\eng-e1k\s\cdisc3.sh`, `CTL3=1`); the console
disc's scene list is unchanged. `build_console_disc.sh` has four new scenes that run only when `--scenes` names them:
`SHOT`, `SHOTNP`, `SHOTDMG`, `SHOTLATE` (the engine's shot against the PC reference: PLAYS_RIGHT.md, last section).

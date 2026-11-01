# QA remote link (QA_LINK)

Read a QA disc's diagnostics and drive its QA menu from a PC, through the Dreamcast's built-in modem and a
Raspberry Pi running DreamPi. No build travels over the link: the disc still loads from GDEMU as usual.

- **Console:** a QA disc built with `QA_MENU=1 QA_LINK=1` (never the game disc). QA menu row
  `REMOTE LINK: OFF / DIALLING n/3 / PPP / UP <console ip> TO <pi ip> / FAILED / LINE DROPPED`.
- **Pi:** `qalink_pi.py serve` logs everything the console sends and passes commands to it.
- **PC:** `qalink.py` runs one `ssh` call per action (send a command, tail or fetch the log).

## What you need

- A Raspberry Pi with DreamPi installed and working (the image from dreamcast.online).
- A USB modem DreamPi supports (the Conexant-based ones in the DreamPi guide).
- A line-voltage inducer between the modem and the Dreamcast. Without it the Dreamcast modem sees a dead line.
- Two RJ11 phone cables: Dreamcast to inducer, inducer to USB modem.
- The Pi on your home network, with SSH enabled. Note its address (for example `192.168.1.50`).

## First-time setup

1. Check DreamPi works on its own: any online Dreamcast game or browser should connect.
2. Copy the service to the Pi:
   ```
   scp port/dreamcast/tools/qalink/qalink_pi.py pi@192.168.1.50:~/qalink/
   ```
   (Create `~/qalink` first: `ssh pi@192.168.1.50 mkdir -p qalink`.)
3. Start it on the Pi (once by hand, or as a service, below):
   ```
   ssh pi@192.168.1.50
   python3 ~/qalink/qalink_pi.py serve
   ```
   It listens on UDP 52040 on every interface (the console's PPP link appears as `ppp0` while connected) and on
   TCP 127.0.0.1:52041 for commands. The log is `~/qalink/qalink.log`.
4. Optional, start at boot: `/etc/systemd/system/qalink.service`
   ```
   [Unit]
   Description=RE4DC QA remote link
   After=network.target

   [Service]
   User=pi
   ExecStart=/usr/bin/python3 /home/pi/qalink/qalink_pi.py serve --log /home/pi/qalink/qalink.log
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   then `sudo systemctl enable --now qalink`.
5. On the PC, set up an SSH key for the Pi (`ssh-copy-id pi@192.168.1.50`) so `qalink.py` needs no password.

## Each session

1. Boot the QA disc from GDEMU. In game, hold L + R and press D-pad Down for the QA menu.
2. Pick `REMOTE LINK` and press A. The row shows `DIALLING 1/3`, then `PPP`, then `UP ...` (about 20 to 40 s).
   The game keeps running while it dials; close the menu if you like.
3. On the PC:
   ```
   python qalink.py --pi pi@192.168.1.50 status
   python qalink.py --pi pi@192.168.1.50 tail -n 40
   python qalink.py --pi pi@192.168.1.50 send PING
   python qalink.py --pi pi@192.168.1.50 send TELEPORT r103
   python qalink.py --pi pi@192.168.1.50 send QA LEON ON
   python qalink.py --pi pi@192.168.1.50 send RECORD 300
   python qalink.py --pi pi@192.168.1.50 send DIAG
   python qalink.py --pi pi@192.168.1.50 fetch qalink.log
   ```
4. To hang up, pick `REMOTE LINK` again (A).

## Commands

| Command | What it does |
|---|---|
| `PING [text]` | Answers `PONG`, the build name and whether the menu is open. |
| `TELEPORT <preset>` | A preset by file (`r103`, `r103.txt`) or label words (`FARM`). Runs at the next free-play moment, through the menu's own teleport. |
| `QA <row> <value>` | `LEON`, `PARTNER`, `ENEMY` `ON`/`OFF`; `SPEED` `ON`/`OFF`; `SHORE` `30`/`45`; `HEALTH`; `TITLE`; on WORLD_METER builds `WOPQ`/`WXLU` `GAME`/`FULL`/`12.5`/`10`/`8`, `WSHELL` `GAME`/`ON`/`OFF`, `PVS` `ON`/`OFF`. |
| `RECORD <ticks>` | The wall time of each game tick (µs), 30 per datagram, then mean / p50 / p99 / max and the fps and phase rows. 1 to 1800 ticks. |
| `DIAG` | The full Diagnostics page (as the QR snapshot) including the last 20 log lines. |
| `MENU` / `RESUME` | Opens the in-game QA menu at the next free-play moment / closes it. |
| `TELEPORT POS <x> <y> <z> [yaw]` | Moves Leon within the current room at the next free-play tick (the warp rig's `goto` path). Refused while the QA menu, a movie, an event or a door load is up. The floor is not checked: use positions read from a `drv` row. |
| `PAD <buttons> <lx> <ly> <ticks> [ANY]` | Buttons plus stick for N ticks, queued (up to 64 steps). Buttons: hex GameCube bits as the fixtures (`0100`) or names joined by `+` (`A`, `R+A`, `B+UP`, `NONE`). Stick -72..72, +y forward, +x turns right. `PAD STOP` clears the queue. |
| `GOTO <x> <z> [run] [timeout_s] [ANY]` | Walks Leon in a straight line (turn, then walk; `run` holds B). Answers `GOTO DONE arrived` within 0.5 m, `timeout` (default 20 s) or `stuck` (under 0.3 m in 3 s). No path finding: teleport to exact spots instead. |
| `SCRIPT <name> [ANY]` | Plays `/cd/dc/qa/pad/<name>.txt` (fixture lines `[+]frame buttons hold [stick=lx,ly]`, plus `goto`, `mark <label>`, `wait <ticks>`). Shipped: `look-around`, `aim-hold`. |
| `MARK <label>` | A marker: `qamark: <label>` in the RAM log and an `M <ms> <label>` datagram (the PC cuts sections between markers). |

Driving rules: steps run at the game's pad read in free play only (no QA menu, movie, event, sub screen or door load) unless
the command ends in `ANY`. Any real pad input cancels the queue at once and blocks driving for 3 s. The top-left label reads
`PC DRIVING (QA LINK)` while a step runs, `PC DRIVE: HOLD (PAD PRESSED)` for 3 s after a cancel. GOTO and SCRIPT answer
twice: `started`, then `DONE <reason>` with the room, position and facing.

## Driving and capture from the PC (qalink.py)

Every action is one ssh call (alias, e.g. `--pi re4pi`):

```
python qalink.py --pi re4pi teleport r103
python qalink.py --pi re4pi teleport pos -11000 163 -1000 -1.1
python qalink.py --pi re4pi goto -15500 -2300
python qalink.py --pi re4pi pad A 0 0 5
python qalink.py --pi re4pi script look-around
python qalink.py --pi re4pi mark doorway
python qalink.py --pi re4pi capture start barn-inside
python qalink.py --pi re4pi capture stop
python qalink.py --pi re4pi session sessions/barn.txt
```

- `capture stop` writes the Pi log between the two markers to `C:\Flycast-Evidence\re4-dreamcast\console-<date>\<label>.log`
  and `<label>.summary.txt` (every numeric telemetry field averaged over the section: fps, cpu, ms10 phases, KOS, VRAM,
  Ganados, link). `--out <dir>` picks another folder.
- `session <file>`: one action per line (`teleport`, `goto`, `pad`, `script`, `mark`, `capture start|stop`, `record`,
  `qa`, `wait <s>`), `#` comments. Shipped: `sessions/barn.txt` (r103 barn inside / by the west wall / 21 m out) and
  `sessions/cross.txt` (r101 cross with and without the crowd in view), 20 s sections each.
- The Pi service must be the version with GOTO / SCRIPT waits (`qalink_pi.py` from this folder; copy it to the Pi once).
- `drv` telemetry row, once a second: `drv room=103 pos=x,y,z ang=<mrad> cam=<mrad> free=0|1 q=<steps> cancels=n <state>`.

## What the console sends

One UDP datagram each, text, first line is the header. The Pi log prefixes every line with a UTC time and the kind.

- `T <seq> <ms> <part>/<parts>`: once a second, the Diagnostics rows (fps, speed, CPU, MS10 buckets and TOTAL,
  HEAP4, KOS, VRAM free / big / fails, Ganados alive, live effects, DRAW_SETUP_AUDIT rows on those builds) and a
  `link` row (bytes, drops, the link's own game-thread cost).
- `L <seq> <dropped>`: new RAM log lines, at most 640 bytes a second (the rest is counted as dropped).
- `R`, `A`, `D`: RECORD rows, command answers, DIAG parts.

About 1 KB/s in steady play; RECORD and DIAG add short bursts.

## Settings file (optional)

`/cd/dc/qa/link.txt` on the disc, one setting per line:

```
number 1111111      the number to dial (DreamPi answers any)
host peer           the Pi's address; "peer" (default) learns it from the Pi's first reply
port 52040          the Pi's UDP port
lport 52040         the console's UDP port
auto 1              dial at the first game tick (harness runs)
```

## Which discs carry the link (lane link28, user 10-28)

- **Every QA disc:** `QA_LINK` defaults to `QA_MENU` (game/qalink.mk), so any `QA_MENU=1` build has the menu row.
  `QA_LINK=0` on the make line turns it off for one arm. The rr QA disc (rr-qa.sh) says `QA_LINK=1` explicitly.
- **Benchmark, arena and scenario discs** (`BENCHMARK=1`, no QA menu): add `QA_LINK=1` and put `auto 1` in
  `/dc/link.txt` (the fixtures folder mkgdi.sh copies to `/dc/`). game/qa_link_bench.cpp dials at the first game tick
  and sends `T` (link row, scene number), `L` (log, 640 B/s) and `B <seq> <dropped>`: every RAM log line starting
  `bench: ` or `PACE` (results, phases, tail summary, code, pace windows), lossless, including the results screen.
  Only `PING` is answered; menu commands answer `ERR`. benchpub/bench-build.sh and lake20/scn-disc.sh do this.
- **The game disc never** (QA_MENU=0): +94 KiB static would cost heap 4 and the s30 movie room.

## Limits

- Hardware only: the real modem, the inducer and DreamPi's pppd. The same disc was proven end to end in Flycast's
  modem emulation (its built-in PPP peer, with `[network] DCNet = no` in emu.cfg, and `host <PC address>` plus
  `lport 52042` because Flycast opens the console's port on the PC).
- No IPv4 fragment reassembly on the console: commands are small, and the service never sends more than 1200 bytes.
- The link costs about 0.12 ms a frame (Flycast) and 2.5 KiB of KOS heap while up; nothing while off.

## Build28 opt-in companion review (`--review28`, default off)

Build28 adds a bounded companion implementation in `qalink_review28.py`. The console review is separately selected by
`QA_LINK_REVIEW28=1` on a `QA_LINK=1` QA build. Both Python CLIs require their explicit `--review28` option to select the
new behavior. Without that option their original service, client, capture and summary functions are unchanged; the CLI
parser/help gains the new option. This section describes the opt-in behavior and supersedes the legacy behavior above
only when that option is present.

Copy **both** service files to the Pi, then start the review service. Keep the helper beside `qalink.py` on the PC too:

```sh
scp port/dreamcast/tools/qalink/qalink_pi.py port/dreamcast/tools/qalink/qalink_review28.py pi@192.168.1.50:~/qalink/
ssh pi@192.168.1.50 'python3 ~/qalink/qalink_pi.py serve --review28'
```

Send from a second terminal, or use the PC client:

```sh
python3 ~/qalink/qalink_pi.py send --review28 PING
python3 ~/qalink/qalink_pi.py send --review28 DIAG
python qalink.py --review28 --pi re4pi status
python qalink.py --review28 --pi re4pi send DIAG
python qalink.py --review28 --pi re4pi script look-around
python qalink.py --review28 --pi re4pi capture start barn-inside
python qalink.py --review28 --pi re4pi capture stop
python qalink.py --review28 --pi re4pi session sessions/barn.txt
```

For a service unit, add `--review28` to the existing `ExecStart`. The opt-in service accepts commands through its TCP
control port; it does **not** read interactive stdin. Use `qalink_pi.py send --review28` or the PC client. The PC client
propagates the option to the remote Pi send command and invokes the bounded helper for capture, tail and fetch. A
review client checks `STATUS` first and refuses to send commands through a legacy service, which would not enforce the
new completion and storage rules. Existing plain control clients can still send one command per connection; review
clients use a byte-counted `Q28` reply frame, so a diagnostic payload line containing only `.` cannot truncate a reply.
The console UDP format is unchanged.

### Completion and deadline behavior

- A `DIAG` succeeds only when every unique numbered part is present. Repeated identical parts do not advance completion;
  conflicting contents, inconsistent totals, malformed bounds, and `A ... ERR DIAG busy` fail. At most 16 parts with
  1100 payload bytes each are accepted; the largest current console snapshot uses 12. The DIAG service deadline is
  at least 30 seconds to accommodate the paced snapshot and a slow modem.
- A `RECORD` succeeds only after its final summary **and** every requested tick are received. All 1800 ticks fit:
  60 data datagrams plus the final answer. Loss of a data row or the final answer is an error, including when some
  useful partial output was received.
- `GOTO` and `SCRIPT` wait for `DONE`. `started` alone never means success. `arrived`, `ok` and `marked` are successful
  terminal reasons; timeout, stuck, real-pad cancellation and other failure reasons return a nonzero exit status.
  Service deadlines are 75 seconds for GOTO and 290 seconds for SCRIPT. A RECORD deadline is its requested ticks
  divided by 25, plus 10 seconds, up to 82 seconds. Other commands use five seconds. Every service deadline is capped
  at 300 seconds. Client socket deadlines include the service budget plus five seconds, including SCRIPT sent directly
  through `qalink_pi.py`.
- Commands to an endpoint quiet for more than 30 seconds are refused with a PING suggestion. PING and HELLO can still
  probe that known endpoint: the console may suppress bulk telemetry while short of heap without losing command
  connectivity. Receipt of a packet refreshes the endpoint. An endpoint change fails pending requests.
- UDP remains best effort. There is no new acknowledgement or retransmission for A/R/M packets or driving completion.
  A deadline error can mean the request or its reply was lost. It does **not** prove a drive stopped; inspect status or
  send `PAD STOP` when appropriate. The companion does not automatically cancel another pending drive.

### Resource bounds and log retention

| Resource | Opt-in bound |
|---|---|
| Console datagram | 1200 bytes; oversized receive packets are rejected |
| Command text | 1184 printable ASCII bytes, one line; fixed nine-character command ID |
| Control connections / command waiters | 8 / 8; excess work receives busy or is closed, with no extra application queue |
| Control socket read/write | 5-second I/O timeout; a client that stops reading cannot retain a worker indefinitely |
| Stored command response | 128 distinct packets and 128 KiB, including terminal errors |
| Service logs | Current file up to 16 MiB plus one `.1` generation up to 16 MiB |
| Log reader | At most those two 16 MiB files; each line at most 8192 bytes |
| Capture section | 8 MiB and 65,536 lines; missing/expired markers fail |
| Telemetry assembly | 8 pending snapshots, 16 parts each, 1100 bytes per part, 30-second expiry |
| Summary numeric fields | 512 distinct field names |
| Remote capture subprocess | 8 MiB stdout, 4096 bytes stderr, 20-second deadline |

These are application payload/file limits, not a bound on total Python process RSS or OS thread stacks. The service has
at most eight control workers; remote capture uses two bounded pipe readers. A failed thread start releases its client
slot. Send failures, deadline expiration and service shutdown remove pending command state. No new allocation or
Python code runs on the Dreamcast.

The review service keeps the readable timestamped log lines and adds an `X28` line containing the exact base64 UDP
packet. A multipart split may occur inside a number or across a newline; the exact journal is needed to reconstruct
that data correctly. Logs rotate from the selected path to `<path>.1`, replacing the older generation. If either file
already exceeds 16 MiB at startup, the review service refuses to start instead of truncating it; preserve the old file
and select a fresh `--log` path. `fetch` includes both retained generations in chronological order. At sustained high
traffic the capture start can expire from this bounded history, in which case capture stop reports an error.

### Capture output changes

Capture labels are 1–24 letters, digits, underscores or hyphens, starting with a letter or digit. Each capture uses a
random marker identity and a separate `.qalink-capture.review28` state file. State is written after the start MARK
command succeeds; a failed start leaves no new state. Stop checks the saved endpoint and requires both exact marker
packets in the retained log. A lost MARK packet can therefore fail capture even if its command answer arrived.

Successful capture writes `<label>-<identity>.log` and `<label>-<identity>.summary.txt` in the chosen output folder,
then clears the state. Existing artifacts are not overwritten. A failed stop retains the state for inspection/retry.
The summary reports **complete telemetry snapshots**, not “seconds.” It concatenates complete numbered payloads before
parsing fields, drops incomplete/conflicting/expired snapshots, counts duplicate parts, and averages each numeric field
over the samples actually present. Console DIAG preemption and packet loss can intentionally leave gaps. A gap does
not become a partial numeric sample or fabricated time coverage. Legacy logs without `X28` packets cannot be used for
review captures; their readable content remains available through tail/fetch.

### Reproducible companion qualification

```sh
python3 port/dreamcast/tools/cloud/build28/companion_contract.py \
  --base 8a55a9d5d94271d33150135aede8d7d094f28fdf \
  --receipt port/dreamcast/tools/cloud/build28/receipts/companion-contract.json
```

The fixture executes the actual Python implementation, including local TCP/UDP, slow clients, floods, malformed and
duplicate parts, complete 1800-tick recordings, deadline/teardown paths, capture limits and child-process pipe bounds.
It also compares all original non-`main` function/class ASTs and compiled code objects against the named base. These
host fixtures do not qualify DreamPi, a real modem, physical Dreamcast performance, or an end-to-end capture.

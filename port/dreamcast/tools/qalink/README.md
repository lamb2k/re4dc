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

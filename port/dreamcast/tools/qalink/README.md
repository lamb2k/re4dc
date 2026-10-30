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

## Limits

- Hardware only: the real modem, the inducer and DreamPi's pppd. The same disc was proven end to end in Flycast's
  modem emulation (its built-in PPP peer, with `[network] DCNet = no` in emu.cfg, and `host <PC address>` plus
  `lport 52042` because Flycast opens the console's port on the PC).
- No IPv4 fragment reassembly on the console: commands are small, and the service never sends more than 1200 bytes.
- The link costs about 0.12 ms a frame (Flycast) and 2.5 KiB of KOS heap while up; nothing while off.

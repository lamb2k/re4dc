---
name: dc-qalink-pi-setup
description: Set up a DreamPi / Raspberry Pi (or any Linux box with pppd) as the dc-qalink relay from a PC on the same network - find it, key-based ssh, checks, install and start the relay service, verify. Use when asked to set up, install, find or fix the Pi / relay side of the Dreamcast QA link.
---

# Set up the dc-qalink relay on a Pi

Tool: `relay/pi_setup.py` (PC side; Python standard library + system ssh). Idempotent; `--dry-run` first.

1. **Preview:** `python relay/pi_setup.py --dry-run` and show the human the plan.
2. **Find the Pi:** run `python relay/pi_setup.py` (tries `dreampi.local` / `raspberrypi.local`, the ARP table for
   Raspberry Pi MAC prefixes, then a /24 scan for ssh). It lists candidates; **ask the human which one** unless they
   gave `--host`. Never guess between two candidates.
3. **Key:** it creates `~/.ssh/dc_qalink_ed25519` and installs it. The human types the Pi's password once, at ssh's
   own prompt. Never ask for the password in chat, store it, or put it on a command line.
   It writes `Host dreampi` (or `--alias`) to `~/.ssh/config`.
4. **Checks + install:** it prints OS, pppd, the dreampi service, the modem device, then copies the relay and runs
   `sudo install.sh` (systemd unit `dc-qalink-relay`, UDP 52040 open; the control port stays on 127.0.0.1).
   Report anything MISSING to the human (no pppd = no PPP peer; no modem = check the USB modem).
5. **Verify:** `ssh dreampi python3 ~/dc-qalink/dc_qalink_relay.py ctl '!STATUS'` shows the relay. After the
   Dreamcast dials: `python pc/dc_qalink.py --ssh dreampi send PING` answers PONG.

## Wi-Fi

`--wifi-report` only reports. Changing the Pi's network needs the human's explicit OK, because a wrong network
strands a headless Pi. If they approve a change: pass the passphrase via a file or stdin, never on a shell command
line (quoting breaks it); some routers reject the Pi under WPA3/SAE (`ASSOC-REJECT ... status_code=16`), use WPA2
for it; add the new network with `disabled=1` first and keep the working one until the new one is proven.

## Troubleshooting

- `ERR no console yet`: the Dreamcast has not reached UP, or it is configured with a fixed host that isn't the Pi.
- Relay up but no rows: `journalctl -u dc-qalink-relay`, and `tail ~/dc-qalink/relay.log` on the Pi.

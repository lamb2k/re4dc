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
2. Install the service on the Pi as a systemd unit, over SSH (one shot, safe to run again):
   ```
   ssh pi@192.168.1.50 mkdir -p /tmp/qalink-install
   scp port/dreamcast/tools/qalink/{qalink_pi.py,qalink.service,install.sh} pi@192.168.1.50:/tmp/qalink-install/
   ssh -t pi@192.168.1.50 bash /tmp/qalink-install/install.sh
   ```
   It copies `qalink_pi.py` to `~/qalink`, installs `/etc/systemd/system/qalink.service` (runs as your user,
   starts at boot) and prints `active`. It does not touch DreamPi's own services or settings. The service listens
   on UDP 52040 (the console's PPP link appears as `ppp0` while connected) and on TCP 127.0.0.1:52041 for
   commands. The log is `~/qalink/qalink.log`. Remove it with `bash /tmp/qalink-install/install.sh --uninstall`.
   To run it by hand instead: `python3 ~/qalink/qalink_pi.py serve`.

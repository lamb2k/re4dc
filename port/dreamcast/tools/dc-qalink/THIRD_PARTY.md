# Third-party software

dc-qalink ships no third-party source. At build time it uses:

| Component | Where | Licence |
|---|---|---|
| KallistiOS (kernel, modem driver, network stack, sockets) | your `$KOS_BASE`, linked as `libkallisti` | KOS License (BSD 3-clause style), `$KOS_BASE/doc/license/LICENSE.KOS` |
| libppp (Lawrence Sebald) | `$KOS_BASE/addons/libppp`, compiled by `lib/dcql.mk` with four function names redirected | KOS License, as above |
| newlib / libgcc | your KOS toolchain | their own licences (see the toolchain) |

`lib/dcql.c` mirrors the layout of KOS's modem `CHAIN_BUFFER` struct and calls three KOS-internal functions
(`_ppp_enter_phase`, `modemIntShutdown`, `net_udp_init`); no KOS code is copied.

A program built with the link carries KOS and libppp under the KOS License: keep its copyright notice in your
distribution's documentation, as KOS itself requires.

The Python tools use the Python standard library only (PSF licence) and the system `ssh` / `scp` / `ssh-keygen`.

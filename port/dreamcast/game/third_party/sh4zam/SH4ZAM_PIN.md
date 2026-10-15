gyrovorbis/sh4zam 0fd3a1e1fa0809d33198c062632b1494ec2f57df (v0.9.0, the pin of port/dreamcast/room/sh4zam.lock.json)
https://github.com/gyrovorbis/sh4zam
MIT license: LICENSE in this directory (Copyright (c) 2025, 2026 Falco Girgis and SH4ZAM Contributors).

Unmodified upstream headers, only the closure that platform/sh4_approx.c and game30_trig.c include
(shz_xmtrx.h and shz_trig.h with the files they pull in: cdefs, scalar, trig, vector, quat, mem, xmtrx, their
inline/*.inl.h and inline/sh4/*_sh4.inl.h). No library is linked; everything used is inline.

Used only by the SH4_APPROX_RENDER / SH4_APPROX_LOGIC knobs (game/game30.mk, default 0; lane approx 2026-10-15),
which evaluate the SH4ZAM approximations the contributor Bruceleeto measured on his fork
(github.com/Bruceleeto/re4dc dreamcast-port 8e769a9dd8, fe2aed7945). A knob-off build compiles none of it.
Toolchain: SH-GCC 15.2 (toolchain.lock, kos-re4dc), C (-std=gnu11) and the game's KOS_CFLAGS (-m4-single -ml -mfsca);
no toolchain change.

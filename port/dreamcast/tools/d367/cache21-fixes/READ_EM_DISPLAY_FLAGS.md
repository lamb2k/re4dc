# Full-slot enemy admission display restoration

Base: `54cef5d1560c41d074beee05ffa1ecd38f2ee642`, verified current
`origin/t15/int` on October 21. `EM_ADMISSION_DISP_FIX=1` restores the saved
`Disp_flg` when `readEm` cannot obtain a free module slot. Default is zero.
The transport-failure and success returns already restore that state and are
unchanged. The guard is Dreamcast-only; original PowerPC behavior is unchanged.
No renderer, asset, recipe, motion or audio changes are included.

H064 reproduced four occupied slots changing `0x12340800` to `0xfffff7ff`.
This repairs that failed-admission cleanup. It is not a demonstrated cause or
cure for normal gameplay disc reads, a generic reset fix or whole-cache closure.

## Actual-source host proof

`test_readem_display_flags.py` exports the three required H064 fixture files
byte-for-byte from `d396bd9e70f7953866e2055b392dda39e0087644`. It reuses their
method extraction, actual release SDK allocator, source memory and native-motion
scaffolding. Its compile-command adapter selects the added matrix main and the
guard value; it does not replace runtime method bodies. A local repository must
contain that fixture revision (fetch `origin/codex/boss21-motion-lifetime-audit`
if necessary). Only A08-SLOTS runs; unrelated H064 lifetime cases are explicitly
skipped, not claimed as passing on this newer integration source.

The matrix runs baseline, disabled and enabled arms under ASan and UBSan. Each
arm covers 24 flag patterns, 24 full-slot refusals, 96 transport failures and
96 immediate success retries, with each of the four slots being the only free
slot. Full-slot refusal makes no transport request and preserves every module
slot. Transport refusal preserves the free slot and other modules; retry selects
that slot and restores the caller's flags. Baseline and disabled retain the
characterized full-slot defect; enabled restores all 24 original flag values.
The transport and module-link boundaries remain the external H064 stubs. This
is actual-source control-flow proof, not target ABI or gameplay evidence.

Run from WSL with a fresh output directory:

```
python3 port/dreamcast/tools/d367/cache21-fixes/test_readem_display_flags.py --out /root/probe/<owned-new-output>
```

## Actual SH-4 object proof

`qualify_readem_display_flags_sh4.py` uses the pinned KOS d367/GCC15.2 toolchain
and actual Make commands for the whole `read.cpp` unit. Baseline Make/read.cpp
are exported from the exact base. Source snapshots share a compile path and
all remaining headers/flags match. `--strip-debug` removes only debug sections
before comparison; actual commands and unstripped objects are preserved.

| WEAPON_HEAP4 | Baseline and disabled stripped read.o SHA-256 | Enabled stripped read.o SHA-256 |
| --- | --- | --- |
| 0 | `cc49999f326f976a6a617aca2dd57030708fb7cf799946f2a47f7eeac4caed09` | `a7f516b817886480dbed1c01b8d02b91bafb9429d11d1b5e1f48807d81cffa15` |
| 1 | `1f1a3346f05ee832d839d74a427271e446cbeb693ba61bcb78939389a2fba921` | `6f685adc2eda707b5640192bfe6e5f718e9e48e729c6ac2bd85217492376faab` |

Both enabled objects are four text bytes smaller; data/BSS are unchanged. This
is compiler output, not a timing claim. Make emits the define only when enabled
and rejects `2`, `-1` and `yes`. The small-object C: guard starts at 16 GiB plus
128 MiB and stops at 16 GiB plus 64 MiB; logs are bounded to 4 MiB per command.
Full-build guards were not changed. With the existing environment sourced, run:

```
python3 port/dreamcast/tools/d367/cache21-fixes/qualify_readem_display_flags_sh4.py --out /root/probe/<owned-new-output>
```

Receipts are `readem-display-flags-host-receipt.json` and
`readem-display-flags-sh4-receipt.json`. Private raw host/SH-4 proof is mirrored
under `C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/readem-display-flags`.
Earlier unsuccessful scaffolding runs remain preserved separately and are not
acceptance evidence. No full build, linked-program/overlay identity, stage,
guest, gameplay screenshot, physical-console check, release or SD action ran.
Those final chosen-candidate gates remain with root and Claude.

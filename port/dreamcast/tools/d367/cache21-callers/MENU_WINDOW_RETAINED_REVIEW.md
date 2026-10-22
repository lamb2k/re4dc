# Menu-window restoration: retained negative result and extra work

`SS_WINDOW_HOLD_RESTORE` stays **disabled**. This read-only review verifies the
existing one-cycle OFF/ON evidence and adds a bounded join to its VRAM retry
logs. It does not rerun a guest/build/host replay, change runtime code, or claim a
performance improvement. Original window-demand `2367dbcad` and payload traffic
reconciliation `1fbda7546a8966c777bfe80e0e9abcb67742abaa` remain the authorities.

## Exact comparison

Frozen source: `b21116ec0cf2c984e9f49769a148373553bff00d`, parent
`892c10ddeadcfcc0bb55bcf53c9b4ac25fd035e8`. OFF exactly reproduced the prior QA
`aafc10f3601b087f60311ca5f24bb641ef6114bb` program and14 overlays. ON's matching
program/14 overlays came from the same b211 build. The retained candidate receipt
reports1,728 unrelated inner files unchanged. This review rehashes the retained
programs/ELFs, generated KOS sources, pack and selected members; it does not repeat
the whole-image inner-file comparison.

| Identity | OFF | ON |
|---|---|---|
| Program SHA256 | `8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d` | `fca8d1debdf2d5889f2a6e1f617c70a7d0da71cb3a7156bebba940027dd8a1c4` |
| ELF SHA256 | `51da665e4293a113ac541dfc79c68f525ce83322f7e1abf26c2ab9b3d5d41802` | `25d64552500e02a75d08f6a0c9a5ec08878ac90e9f93a76d53a5b0b6c0955639` |
| Outer track3 format | 2352-byte-sector `track03.bin` | 2048-byte-sector `track03.iso` |
| Outer track3 retained SHA256 | `5ae451a0cb1e5c6e6db9b68d27335a09a00d27abd83e9c838c66ef2f8b69cfa8` | `b5e951b1ff1c0f6e7f5a5d0a208558c400ea5f0e31c4fa8c2daba5d693b3fd3a` |

Outer track hashes above come from preserved input manifests; large tracks were
not rehashed/copied here. Different outer layouts must not be described as the
same disc image or as timing-equivalent. The unchanged inner asset comparison and
exact request-byte source accounting do not establish physical drive timing.

The exact shared pack is
`18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef`
(156,254,208B). The generated patched KOS ISO source in both arms is
`500da02b87d0e0790585f9a3661abd487a2bde0bca0ff1126cb561277113a0bc`.
The review checks seven complete Git source identities against the sealed traffic
receipt; native_ui is `6c2adb5ff72e903e76a263cfbc30c07d6d1cf25e6352b773b70cd42f152ebc4b`.
Current unpatched KOS code is not substituted. Resolved definitions include
KOS_DISC_FIX1, IO_SERIAL1, TEX_PACK1, TEX_RESIDENT1, TEX_PAYLOAD_CRC0,
TEX_PACK_WINDOW0, STORAGE_BOUNCE_ALIGNED0, a16KiB storage bounce,
DISC_READ_METER1, DISC_READ_LOG0 and IO_PROBE0. A second runtime payload CRC pass
or pack read-ahead window is not a supported explanation.

Both launches were cold ordinary-input runs. The saved QA preset label says
AFTER S20, but the observed fixture is the r100 opening house. Eight issued key
steps produced **one actual inventory open/return**, not two. Retained screenshots
show inventory/returned room; this review rehashes the t0048 returned-room images
without creating new captures. The raw game_mode_bytes sample field is unvalidated
and is not used. Inventory and source-return frames are not matched frame-for-frame.

## Original counter windows, unchanged

| Arm / host window | Requests before → after | Bytes before → after | Delta |
|---|---:|---:|---:|
| OFF29.015..49.984s | 1692→1881 | 17,100,288→19,331,104 | 189 /2,230,816B |
| ON29.016..50.000s | 1692→1983 | 17,100,288→19,499,136 | 291 /2,398,848B |
| ON minus OFF | | | **+102 /+168,032B** |

The original block-counter difference is+417,678 microseconds in Flycast; no
causal time attribution or physical Dreamcast acceptance follows. These are
low-level nonmusic request sizes, not unique optical seeks or consumed texel
bytes. Internal real fallback attempts are not individually counted; other
nonmusic threads are included.

The earlier held-menu plateaus are identical at130 requests/2,095,168B. The return
plateaus are OFF59/135,648B versus ON161/303,680B. These are retained samples from
the same original windows, not newly spliced counts. The source restoration replay
accounts for OFF16/47,584B versus ON118/215,616B, leaving the same43/88,064B
unassigned common return remainder in each arm. The final plateau continues to
the original window end; no missing reads are filled from another run.

## What caused the added demand

Both arms' hold logs release the same movie-window region:26 entries/122,912B at
`a47ac300`, pinned_ok0. The candidate adds `RE4DC_HOLD_EVICTED(e)` to that window's
entry-close loop (native_ui4509). It changes which evicted entries are remembered,
not which window was released in this cycle. Existing historical SS_HOLD_RESTORE
is separate from this new SS_WINDOW_HOLD_RESTORE guard.

The remembered set grows10→36; restore filtering grows3→29 of the same29 potential
picks. `vram_unclaim` schedules the pass; `ui_begin` runs it when no claims remain.
It loads remembered keys in the prepared preload order before ordinary demand.
The complete logs show exactly26 additional distinct logical opens/uploads,
totalling122,912B, matching the26 released window entries. OFF does not later open
any of those26 within its retained tail; that does not prove they are never needed
on a future camera/path. Entry.frame is also written by preload selection and
ordinary lookups, so the60-frame remember condition is not proof of recent visible
draws. No future traffic saving is inferred.

The payload lane's frozen-source host replay already reconciles all added drive
accounting:

| Additional component | Requested bytes | Request classes |
|---|---:|---:|
| Native texture payload | 122,912 | included in bulk/tail calls below |
|26 headers/descriptors | 3,744 |26 header-sector calls |
| Unused final stream-tail bytes | 416 |28 bulk +28 tail calls across members |
|20 extra index-sector transitions | 40,960 |20 index streams |
| Total | **168,032** | **102** |

Index transitions are ON23 versus OFF3, derived from the full logged order and
real pack index. Two extra18,432B payloads cross the16KiB chunk and add two calls
each compared with the smaller-member pattern. The actual patched ISO read body
explains the16B unused final32B stream tail per extra member. This is an identified
source replay with mocked drive calls, not an old per-request target trace.

## Additional VRAM work in the same retained logs

Frame360 held-state counters match in both arms: retries3/evicted10, with the same
used/free counts. Unclaim free space is103,776B in both. The return preload is
OFF source frame438 and ON439:

| Logged counter/state | OFF | ON | Difference |
|---|---:|---:|---:|
| Logical restoration loads |3|29|+26|
| Visit loads |269|295|+26|
| Upload-path reclaimed/evicted counter |17|24|+7|
| Fragmentation retries |5|10|+5|
| Accounted resident bytes |2,358,648|2,386,840|+28,192|
| Free VRAM |110,432|82,240|-28,192|
| Largest free extent |12,416|8,192|-4,224|

The five additional retry rows associate with four extra keys:
`9bcfefbd-d81c6b31`, `b5603f79-e30d477e`, `c696ceea-ea7e04f9`,
`e7dbb42b-ab309443`; the fifth is common key `cf2208cd-a6bfb2ef`, which did not
retry in OFF. The first two common keys have matching retry rows in both arms.
Thus eager restoration also changes fragmentation pressure on a later common
load. Source `load:3447..3459` evicts, probes for a contiguous block, then reopens
the package and retries upload. One logged logical load per key therefore does
not mean one metadata-open attempt. The logs do not identify each victim or its
bytes; the displayed evicted counter is source `reclaimed`, not every possible
VRAM release including the separate26-entry window.

Do not add those five retries to the already-reconciled102 low-level requests.
A metadata reopen can hit the KOS sector cache, and the old run has no per-call
path/LBA trace. Repeated source attempts, low-level request counts and GPU binding
counts are different observations. No log proves repeated successful restores of
the same key, nor does this review claim a complete bind census or assign the
417,678us block delta to particular retries.

## Review receipt

`review_menu_window_evidence.py` performs28 retained-source/identity/counter
checks, rehashes29 input reads and7 complete Git source objects, and verifies all26
selected pack members. It emits only a small derived receipt, without copying
programs/private assets/logs. `menu-window-review03-receipt.json` pins all inputs,
retry lines/keys, counters, launch times, screenshot hashes and limitations.
The existing replay is identity-verified, not rerun. Review01's assertion caught
the incorrect inference that all five new retries belonged to extra keys; review02
passed and review03 corrected the held-frame360 field label. All drafts remain
preserved. Entire new tools/report/receipt and mirrors are below4MiB.

No new build, stage, guest, performance benchmark, release check or hardware
acceptance. No runtime/shared claim. Main retains holistic audit/integration
ownership and Claude retains production ownership. Candidate remains disabled.

# Build 28 — QA link review

Branch: `codex/qa-link-review-20261028`.
Initial integration base: `8a55a9d5d94271d33150135aede8d7d094f28fdf`.
Final integration base: `568c357656efbec468db06a282c1f79caebaa725`.

## Gate and scope

The link28 prerequisite was checked before this build started. The queue's
Status table still labelled Build 28 "QUEUED 10-28 (after local link28 lands)",
but `7acd7d8fd6a828d4e596fdb57516a0655b4dc032` — **link28: QA_LINK on every
QA/test/bench disc + console link fixes** — is an ancestor of this integration
base. The base also contains `e6f69b9c` (remote driving/capture) and the Build 26
merge `33efaa8d`. This review therefore covers the landed link, not the earlier
faulty lane. It does not merge any branch.

All console changes use the new **`QA_LINK_REVIEW28=1`**, default **0**, and
are selected only with `QA_LINK=1`. The existing default for `QA_LINK` on QA
discs is unchanged. Pi/PC fixes have their own default-off `--review28` flag.
No production assembly, linker policy, renderer, world/model draw code or
weapon code is changed. Existing BSS stacks, rings, transport entry points and
KOS APIs are reused.

The initial integration base blocked raw menu compilation. Its
`qa_menu.cpp` contains literal `\n` tokens in three preprocessor conditions
(base lines 347, 511 and 1492). An independently archived, unmodified base
fails the pinned SH-4 preprocessor with `token '\\' is not valid in preprocessor
expressions`. These conditions are outside the QA_LINK-only change scope.
Claude corrected them upstream in `568c3576`; this branch rebased cleanly
onto that commit, also retaining the Build 27 merge `39c1742a`. Final
qualification uses the corrected production bytes. Earlier test-only syntax
experiments are historical evidence, not raw knob-off proof.

## Findings and changes

### Console transport

Code sites: `game/qa_link.cpp`, especially `Ring::put/get`, `pump`,
`re4dc_qalink_modem_write`, `re4dc_qalink_thd_pass`, `hang_up`, `dial_once`,
`spawn_dial`, the two thread entry functions and the public send/receive APIs.
The pinned KOS implementation is part of the review, rather than assumptions
about a newer libppp.

| Finding | Change with the new knob enabled |
|---|---|
| The documented maximum was 1200 bytes, but the ring admitted 1400. A small receive buffer could execute a truncated command; a zero capacity underflowed. | Enforce 1..1200-byte datagrams, reject null input, retire a too-large command whole, and guard zero/null receive destinations. Count refused incoming packets. |
| Unknown/stale peers and commands could survive a reconnect. Socket nonblocking setup was unchecked. | Validate incoming address/port/size, preserve the configured peer separately from the learned address, relearn on a new call, retire RX data before publishing the new socket, and reject failed nonblocking setup. |
| A connected modem whose TX buffer never progresses can retain libppp's send loop indefinitely. The pinned shutdown does not itself clear the driver's connected flag. | Explicit retiring/stop/fault state makes writes discard during teardown. Two seconds without progress triggers a counted fault; the redirected thread pass enters PPP DEAD after the mutex is released. Progress resets that deadline. This bounds the no-progress case, not the duration of every possible network call. |
| Pinned `ppp_shutdown` leaves the username/password allocations alive; `ppp_init` then clears their pointers. | Call the existing `ppp_set_login(nullptr,nullptr)` after PPP exits and before shutdown. It frees the old strings without allocating replacements. |
| The old timeout forcibly destroyed a potentially live PPP thread. A detached thread also cleared its running flag before its final return, leaving a window for BSS-stack reuse. | Keep a timed-out thread, credentials and stack intact and report retryable DROPPED. Track child-owned thread IDs and require absence/ZOMBIE/FINISHED before reuse. Only the ID lookup/state read is protected by IRQ masking; allocation is outside that new region. |
| Hang-up thread creation failure could leave a misleading HANGING UP state. | Report FAILED and the existing error code; a subsequent start can retry cleanup. |

The existing command-first, one-TX-datagram-per-PPP-pass policy stays intact.
The 4096-byte rings, 2400-byte bulk cap and 32768-byte KOS-free-plus-break-room
floor stay intact. The new compact telemetry fields are `rxdrop` and `stall`.
The low `kos free` figure alone is not the admission budget: the existing
policy also includes available break room.

### QA menu and benchmark producers

Code sites: `game/qa_menu.cpp` (`link_send_parts`, `link_telemetry`, `link_log`,
`record_tick`, `link_pump`, command/driving entry points),
`game/platform/include/qa_link_review28.hpp`, and `game/qa_link_bench.cpp`
(`send_log`, `send_results`).

| Finding | Change with the new knob enabled |
|---|---|
| A full DIAG burst exceeds the TX ring. Telemetry without the Build 26 audit sender can exceed the bulk cap. Rejected later parts were discarded. | One immutable T/D snapshot advances only after successful queue admission, attempts at most once per 50 ms, and retains an unaccepted part. Payloads are at most 1100 bytes; tested whole datagrams are at most 1130 bytes. |
| Commands need priority over periodic snapshots. A new DIAG must not silently replace an accepted DIAG. | Process commands first. DIAG preempts an unfinished T snapshot; a second pending DIAG gets an explicit busy error. Explicit D parts use ordinary TX with the same 2400-byte reservation, so diagnostics remain available below the T/L bulk heap floor. Disconnect cancels the pending snapshot. Existing Build 26 behavior remains in its unchanged off branch. |
| Background snapshots reset the viewed Diagnostics page outside the Build 26 composition. | Preserve the current page for telemetry, DIAG and RECORD summary snapshots. |
| Linkpad telemetry adds a drive row to the reserved tail. | Reserve sufficient space for that row plus the new counters, and accumulate actual bytes stored by formatting. This is bounded-tail handling; no old memory-corruption claim is made. |
| L-stream cursors advanced even when bulk admission refused the packet. | Commit cursor/sequence only on acceptance. Subsequent output counts overwritten or budget-pruned bytes and sends the newest bounded 640-byte slice. |
| RECORD insertion-sorted up to 1800 samples on the game thread, with quadratic worst-case work. | Keep insertion sort for at most 4*n shifts, then use an in-place, nonrecursive heap sort. Ordered/nearly ordered samples retain the inexpensive case; the maximum is bounded O(n log n). Integer results and percentile definitions remain exact. |
| Remote controls and deferred commands could survive link loss; NaN/Inf coordinates can enter casts or the angle-wrap loop. | Release queued driving and pending position/navigation/record actions on link loss. Reject nonfinite/out-of-range coordinate input (±10000000 game units, yaw ±1000 radians); invalid drive-feed state cancels control. SCRIPT GOTO timeouts use a bounded conversion and a 60-second clamp before multiplication. |
| Benchmark scanning restarted at an incomplete long line every tick, and oversized wanted lines were silently omitted. | Retain the scan position, examine at most 2048 new log bytes per pass, emit at most 3 bounded result datagrams, retry refused output, and report oversize/overwrite gaps. These gap bytes are not an exact count of lost benchmark-only payload. |

There is no allocation or network wait in the new snapshot/sort/scan helpers.
One snapshot replaces the previous telemetry storage; a second large DIAG
buffer is not introduced. The longest supported composition has a 12288-byte
Diagnostics buffer and a 12672-byte T/D workspace, so it needs at most 12 parts.

### Pi and PC companions

Code sites: `tools/qalink/qalink_pi.py`, `qalink.py`, and the opt-in
`qalink_review28.py`. The legacy service/client functions are retained and the
new helper is imported only when selected; adding a CLI flag is not a claim
of whole-Python-bytecode identity.

The opt-in service bounds active control clients and command waiters at 8,
command data at 1184 bytes, datagrams at 1200 bytes, reply storage at 128 KiB and
128 packets, and multipart messages at 16 parts of 1100 bytes. It validates
unique part numbers and consistent totals, rejects conflicting duplicates,
and uses semantic completion for RECORD/GOTO/SCRIPT. Timeout, incomplete
records and missing terminal drive status become errors; a first "started"
reply is not treated as successful completion. DIAG has a 30-second minimum
service deadline to accommodate the paced full snapshot. PING/HELLO can probe
a known endpoint after it becomes quiet, so bulk suppression does not prevent
recovery; other stale-endpoint commands request that probe first.

Exact packet journals preserve byte boundaries that the old human-readable
line log could not reconstruct. Capture summaries count complete telemetry
snapshots and discard/report incomplete, conflicting, expired or duplicate
parts. Pending assembly is bounded at 8 snapshots with a 30-second expiry.
Log rotation retains two 16-MiB files; capture extraction is bounded at 8 MiB
and 65536 lines. Capture state is associated with the endpoint and a unique
marker token, and is written only after the start command succeeds.

These changes do not make UDP reliable. Ordinary A/R/M packets can still be
lost after admission; the companion reports a missing result instead of
claiming success. A superseded T snapshot, a log gap or a busy DIAG is an
explicitly changed QA output. No render approximation or normal gameplay
change is intended. The opt-in service accepts commands through TCP/PC tools;
its legacy interactive stdin worker entry is not enabled.

## What remains outside the measured envelope

The game-thread start/stop path still creates a KOS thread record for a
background operation. Dial/PPP/modem workers use the existing BSS stacks;
thread records, sockets, UDP receive packets and login strings still have KOS
allocation lifetimes. The wrappers also retain their existing fallback for
unexpected modem-buffer/worker users. This is not an allocation-free-network
claim.

The initial config read and explicit SCRIPT/preset reads still use the
existing disc fixture reader on the game thread. They are command/setup work,
not a newly asynchronous file system. The new sorter removes a concrete CPU
stall, while target measurements do not price real disc waits, modem baud
rate, PPP escaping, KOS scheduling, PVR IRQ interaction or data-cache misses.

The link code still owns no SQ or PVR submission. New IRQ protection is limited
to lifecycle thread lookup/state checks, not ring copying, snapshot formatting,
allocation or modem I/O. Its duration depends on the KOS thread list and must
be checked in the console stress run. Modem-connect cancellation remains the
existing background timeout, not an instantaneous cancellation promise.

## Verification and reproduction

The [validation report](../../../tools/cloud/build28/VALIDATION.md) records the
pinned GCC 15.2.0 / binutils 2.45.1 toolchain, KOS `804b3195`, SH4ZAM
`33fa4850`, exact source closures and reproduction commands. Real Make rules
provide flags and object selection. The public qualification mirrors
`NMR_POOL_LOD=0` on both sides because private Ganado assets are unavailable;
it retains the actual prepared KOS cache header. Complete preprocessor and
object comparisons exclude debug/line records consistently, without editing
or normalizing the compared bytes.

**Final raw target gate: PASS on `568c3576`.** The full matrix passes
56 absent/zero comparisons, nine enabled compositions, and eight additional
comparisons with `QA_LINK=0 QA_LINK_REVIEW28=1`. It covers
both draw-audit knobs, their combined diagnostics capacity, and the separate
link benchmark. Release Make checks exclude the reviewed link TUs, and
invalid empty, multiword or nonbinary review-knob assignments are rejected.
All compiler source inputs are unmodified production bytes; no syntax overlay
is used. See the [OFF receipt](../../../tools/cloud/build28/receipts/target-off.json)
and [ON receipt](../../../tools/cloud/build28/receipts/target-on.json).

Host controls exercise actual production code against explicit synthetic
service boundaries:

| Control | Result and scope |
|---|---|
| Complete transport and benchmark translation units | 28 transport and 14 benchmark cases, normal and ASan/UBSan. Synthetic KOS/socket/timer/thread services; real scheduling and modem behavior are not simulated. |
| Complete QA protocol block plus three driving entry points | Five capacities (3072/4096/7168/8192/12288 B), 166 cases each, normal and ASan/UBSan. Each profile includes 54 snapshot retry cases, 1652 attempts with 1436 refusals, and 80 exact sort cases. Largest tested datagram: 1130 B. |
| Actual Python companions | 31 test methods, including 11 loopback TCP/UDP service methods. Every original non-main function/class has identical AST and marshalled code against final integration. This is not whole-module bytecode identity. |
| SH-4 pieces | Ten exact-output sort cases and 26 ring boundary/wrap/refusal cases. The report distinguishes freshly executed rows from rows retained only after fresh object **and ELF** identity. |

ASan/UBSan runs disable LeakSanitizer because this sandbox cannot inspect
`/proc` under ptrace. No heap-leak sanitizer, full private game-image, Flycast,
console, PVR-contention or real-modem acceptance is claimed. The companion
loopback suite's 2.607-second host elapsed time is a fixture duration, not a
performance result.

Further source-site detail is in the [transport review](build-28-transport.md)
and [companion review](../BUILD28_COMPANION_REVIEW_20261028.md). All synthetic
fixtures and compact receipts live in [tools/cloud/build28](../../../tools/cloud/build28).
No private game data, disc image, login configuration or captured console
session is committed.

## Cost, traffic footprint and size

Warm timing uses perfect instruction/data caches. Cold-I starts an isolated
8 KiB instruction cache empty while leaving the data cache perfect. Loads
and stores are real opcode accesses, including stack and literal pools;
distinct 32-byte lines are address footprints, **not measured cache misses,
fills, writebacks or bus transactions**. The figures below price only the
named piece. They do not include modem throughput, PPP escaping, device waits,
disc access or network allocation.

### Exact RECORD completion sort

| Input | Warm cycles, old → new | Cold-I cycles, old → new | Loads / stores, old → new | 32-byte lines, old → new |
|---|---:|---:|---:|---:|
| 128 ascending | 1414 → 1422 | 1456 → 1504 | 257 / 128 → 261 / 132 | 18 → 18 |
| 128 reverse | 57548 → 25757 | 57591 → 25896 | 8258 / 8256 → 3040 / 1600 | 18 → 18 |
| 1800 ascending | 19806 → 19814 | 19848 → 19896 | 3601 / 1800 → 3605 / 1804 | 227 → 227 |
| 1800 nearly sorted | 19813 → 19825 | 19856 → 19904 | 3602 / 1801 → 3606 / 1805 | 227 → 227 |
| 1800 reverse | 11342712 → 531421 | 11342755 → 531560 | 1620902 / 1620900 → 61844 / 28560 | 227 → 227 |

The nearly sorted fixture swaps the central adjacent pair. The full reverse
case executes all 1800 samples; it is not extrapolated. Wrapper executable
size is 78 → 328 B; observed fixture stack is 4 → 20 B. Repeated accesses
fall sharply without reducing the unique input-line footprint. Ordered input
adds eight warm cycles; nearly sorted adds twelve. Statistics are exact.

**Whole-frame MODELLED sensitivity:** assume an unchanged 30 ms for everything
outside one sort on a RECORD completion tick, at 200 MHz. Reverse 1800 gives
`30 + 11342712 / 200000 = 86.713560 ms` before and
`30 + 531421 / 200000 = 32.657105 ms` after. Ascending gives
30.099030 → 30.099070 ms; nearly sorted gives 30.099065 → 30.099125 ms.
These are synthetic completion-tick totals, not regular-frame FPS or console
timings, and they must not be added to the separate ring example below as a
claimed measured frame.

### Actual transport ring

| Operation | Warm cycles, old → new | Cold-I cycles, old → new | Loads / stores, old → new | 32-byte lines, old → new |
|---|---:|---:|---:|---:|
| Put 1100 B | 6639 → 6657 | 6694 → 6722 | 1114 / 1104 → 1118 / 1105 | 74 → 74 |
| Put 1200 B | 7239 → 7257 | 7294 → 7322 | 1214 / 1204 → 1218 / 1205 | 80 → 80 |
| Get 1100 B | 9946 → 9948 | 10018 → 10018 | 1114 / 1103 → 1115 / 1103 | 74 → 74 |
| Get 1200 B | 10846 → 10848 | 10918 → 10918 | 1214 / 1203 → 1215 / 1203 | 80 → 80 |
| Put 1201 B: old accepts, new refuses | 7245 → 15 | 7300 → 36 | 1215 / 1205 → 3 / 0 | 80 → 2 |
| Get 1130 B into 512 B: old truncates, new retires whole | 7745 → 43 | 7817 → 110 | 526 / 515 → 14 / 3 | 37 → 5 |

The last two rows deliberately change the result. Valid enqueue adds 18 warm
cycles; valid dequeue adds two. Combined wrapper code is 254 → 296 B and
allocated size is 270 → 312 B including the 16-byte layout descriptor.
Observed put stack is 4 → 8 B; get remains 8 B. The new early oversize refusal
uses zero fixture stack.

For one 1130-byte enqueue and one 16-byte dequeue, plus the same assumed 30 ms
of all omitted work, the total is **30.035045 → 30.035145 ms MODELLED**.
This 20-cycle difference is not an end-to-end transport or pump deadline.

### Complete selected console objects

These are complete production-TU section deltas before final linking and
garbage collection. Allocated size includes code, read-only data, initialized
data and BSS; do not add the BSS column again. The final raw
[production metrics](../../../tools/cloud/build28/receipts/production-metrics.json)
confirm the table against the rebased integration source.

| Configuration | Added executable | Added allocated | Added BSS |
|---|---:|---:|---:|
| QA_LINK=0, every DFA/DSA composition | 0 B | 0 B | 0 B |
| QA_LINK=1, DFA=0, DSA=0 | 2696 B | 3264 B | 300 B |
| QA_LINK=1, DFA=0, DSA=1/XLU=1 | 2708 B | 3276 B | 300 B |
| QA_LINK=1, DFA=1, either DSA arm | 2464 B | 3000 B | 268 B |
| QA_LINK=1 benchmark, QA_MENU=0 | 1608 B | 1648 B | 36 B |

The transport alone contributes 1152 B executable, 1183 B allocated and
27 B BSS. Its largest local frame remains 248 B; hang-up changes 16 → 24 B,
start/send remain 8 B, and bulk send remains 24 B. Menu `link_pump` changes
2648 → 3092 B with DFA off and remains 3092 B with DFA on; `record_tick`
remains 456 B. The largest benchmark local frame changes 2968 → 3108 B.
These are compiler local frames, not full call-chain or IRQ stack watermarks.
The otherwise-zero snapshot stays in BSS; setting its kind before use avoids
moving the full buffer into initialized data.

## Questions and owner acceptance

1. On the corrected integration plus `QA_LINK_REVIEW28=1`, please run the
   largest DFA+DSA diagnostics composition with a slow/full TX queue and a
   low heap budget. Can PING/DIAG still complete, does the viewed Diagnostics
   page stay put, and do T/D sequences assemble without mixed snapshots?
   Run the paired Pi/PC tools with `--review28` for multipart/loss reporting.
2. Please soak repeated connect/hang-up/redial, including cable/peer loss,
   failed thread creation and a modem TX stall. The credential fix frees the
   two existing strings (16 payload bytes per completed teardown for the
   configured credentials, plus allocator overhead); it does not explain
   the entire previously observed ~1.3 KiB free-heap fall. Record free plus
   break room, live allocations, `rxdrop`, `stall`, and thread/stack reuse.
3. Please check PVR progress and real stack margins under simultaneous
   drawing, link traffic and RECORD completion. The new short IRQ-protected
   lookup still depends on the length of the KOS thread list; no console
   duration or contention result is available here.
4. Please exercise PAD/GOTO/SCRIPT cancellation on link loss and real-pad
   override. Confirm the new coordinate limits are sufficient for the QA
   route set. UDP loss can still prevent the PC from observing a terminal
   response; companion timeout reports uncertainty, not proof that a
   remote action was cancelled.
5. Please run the full private release-image identity and QA image/link
   gates, then decide when to enable the switch. All new defaults remain
   zero; Claude owns merges and recipe changes.

Per the user's explicit hand-back request, a concise dated summary and these
questions are also linked under **Open questions back to Claude** in the
queue. The full report is kept here to follow the later standalone-handback
layout; the queue Status table is left to Claude.

#### Owner: Windows packet-journal CRLF reader, 2026-10-29

The local Windows relay writes CRLF text records. log_lines reads binary and
removes only LF; journal_packet formerly left the terminal CR in its base64
field and strict decoding silently ignored every X28 record. This produced
a misleading zero-snapshot summary despite actual recorded telemetry.
journal_packet now strips only the text-record CR/LF terminator before
splitting. The encoded datagram, its internal newlines, strict base64 decoding,
datagram/part bounds and coherent multipart assembly remain unchanged.
No game-side code, scheduling, protocol or legacy default client changes.

Three new cases cover LF/CRLF file-read multipart summaries, exact datagram
and capture-marker identity with payload-internal CRLF, and rejection of
embedded base64 whitespace/invalid/oversized packets. New CRLF cases reproduce
on the old reader; final actual companion suite34/34 PASS with explicit
--base c528a4dc7d0cf47e6c71486a7c2cfe9cb2940266. The historical default568c
legacy comparison differs from later marker fixes; that initial run remains
recorded separately, not reported as a pass. Current-base AST/code identity
for unchanged legacy clients passes. This is host tooling only; no SDK rebuild.

Offline replay of unchanged retained Windows journals:24 X28 packets per arm,
old parser accepted0/fixed parser24; two complete automatic T snapshots each.
Control retains one incomplete T snapshot; gaps none. Raw journal hashes
unchanged, old companion/captures retained, no emulator rerun or payload/row
normalization. Prior zero summary is unusable, not evidence of zero telemetry.
These automatic snapshots do not clear explicit DIAG4/14, marked600-draw,
window semantics, matched camera/frame, CPU/memory or console gates.

# Build 28: console transport and benchmark review

This is the console-side supporting review for [build-28.md](build-28.md).
The final integration base is `568c357656efbec468db06a282c1f79caebaa725`;
`7acd7d8f` (link28) is already an ancestor. This base includes Build 27 and
the upstream repair of the three menu syntax defects. The transport and
benchmark sources are unchanged by the rebase, and both host receipts
still match all six recorded source/fixture hashes. The changes are compiled only
for QA_LINK with `QA_LINK_REVIEW28=1`, default 0. Existing absent/zero arms
remain in place; the combined hand-back owns the final raw target identity
result against this base.

## Findings and fixes

Sites below name the reviewed functions in
[`qa_link.cpp`](../../../game/qa_link.cpp) and
[`qa_link_bench.cpp`](../../../game/qa_link_bench.cpp). The frozen enabled
transport source is SHA-256
`d6bb30e27c94c88b28aae187cf9a7af19e1143ac947bd7a790db53c39370c61b`;
benchmark source is
`31ed7eb9819904318d4ae92ba3ec0cdb1d825516716aa00e435df5fd9d58c6ac`.
The receipts bind the final files rather than relying on line numbers.

| Finding | Code site | Review-only behavior |
|---|---|---|
| Application rings accepted 1,400-byte datagrams although the link protocol promises at most 1,200. | `Ring::put`, `pump`, `re4dc_qalink_send` | Reject null, empty or over-1,200-byte outgoing packets; reject over-1,200-byte incoming packets, including larger packets truncated by the socket API to its receive-buffer size. There is no packet fragmentation or command-prefix execution. |
| `re4dc_qalink_recv(max=0)` underflowed `max-1`; a short destination silently received a truncated command. | `Ring::get`, `re4dc_qalink_recv` | Null/zero destinations return without consuming. A datagram that will not fit is retired whole and returns `-2`; `rxdrop` increases. The next complete datagram remains intact. |
| Learned `host peer` replaced configuration permanently and could target the old peer on a later call. | `re4dc_qalink_config`, `dial_once`, `pump` | Preserve configured host separately and restore it on each dial. Learn only from a valid packet on the configured UDP source port; once learned, accept that address only. Fixed-host configuration remains fixed. The Pi service uses its same bound socket for HELLO and command sends. |
| RX-ring refusals were silent; a zero-length UDP packet ended the receive-drain loop. | `pump` | Count rejected/full-ring packets in `rxdrop`; retire empty packets and continue draining. Receive remains before the existing single transmit datagram per pass. |
| Stale RX bytes could be appended by a finishing old PPP pass after `start` had cleared the ring. | `hang_up`, `dial_once` | Clear RX after the previous PPP owner has exited and again before publishing the new socket. |
| The pinned modem shutdown leaves its CONNECTED flag set; a write can therefore see connected hardware after its software buffers have been destroyed. | `hang_up`, `re4dc_qalink_modem_write` | Publish an explicit retiring flag before shutdown. Writes during stop/retirement discard the remaining PPP fragment and return, independent of the modem status bit. |
| A connected modem accepting zero bytes could leave libppp's transmit loop waiting indefinitely. | `re4dc_qalink_modem_write`, `re4dc_qalink_thd_pass` | After two seconds without write progress, mark the transmission failed, count one `stall`, discard remaining fragments and enter PPP DEAD at the following redirected thread pass. Successful write progress resets the timer. The socket result is not counted as successfully transmitted when the wrapper discarded bytes. |
| PPP shutdown does not free login strings, and subsequent initialization zeroes their pointers. | `hang_up` | After actual PPP-thread exit, call the existing `ppp_set_login(nullptr,nullptr)` before `ppp_shutdown`. This releases the six-byte username and ten-byte password allocations, plus their allocator overhead, on every completed teardown. It is not claimed to explain the whole original console free-memory delta. |
| Forced thread destruction could destroy a libppp mutex owner or recycle a stack beneath a live thread. | `hang_up`, `dial_main` | Keep the existing 400 × 8 ms cooperative wait. If the thread still runs, retain its state, credentials and stack, report retryable DROPPED/error -31, and refuse to start another PPP owner. A later A retries cleanup. No forced destroy runs in the enabled path. |
| Thunks clear their running flags just before returning; a preemption in that gap could admit reuse of their static stacks. | `stack_busy28`, `ppp_trampoline`, `dial_main`, thread-creation wrappers | Each child records its own stable KOS thread ID before callback work. Reuse also requires the old ID to be absent or ZOMBIE/FINISHED. A short IRQ-masked lookup protects the detached-thread record from concurrent reaping; creation itself gains no extra masked region. |
| Failed creation of the hang-up worker left the UI claiming HANGING UP. | `re4dc_qalink_stop` | Report FAILED/error -30 and keep enough state for the next A to run cleanup before redial. |
| Failed nonblocking configuration could leave `recvfrom` blocking the PPP loop. Login allocation failure was ignored. | `dial_once` | Check `fcntl(O_NONBLOCK)` and `ppp_set_login`; refuse the attempt with -13/-15 and use the existing background cleanup/retry path. |
| Benchmark L rows advanced their cursor and sequence even if queue admission failed. | `send_log` | Commit cursor/sequence only after acceptance. A later accepted row reports the byte gap caused by log overwrite or the 640-byte sampling cap. |
| Benchmark result scanning could revisit an incomplete 64 KiB line each game tick; oversized wanted lines were skipped without a loss count. | `send_results` | Retain a scan cursor across ticks; scan at most 2,048 new log bytes per call, with at most three packets. Retry preserves the cursor. Oversized wanted rows and overwritten/unaligned fragments contribute to the B byte-gap counter, including an empty-body B packet when only a gap needs reporting. |

`re4dc_qalink_review_counters(unsigned* rx_drops, unsigned* tx_stalls)` is the
only new shared API. Both counters are cumulative, unsigned and diagnostic.
`rxdrop` includes oversize/empty/foreign-peer datagrams, a full application
RX ring and an undersized caller destination. It is not a count of packets
lost on the line. `stall` counts the first no-progress timeout per dial
attempt; discarding later fragments does not increment it repeatedly.

## Queue ownership, allocation and timing boundaries

The two application rings remain 4,096 bytes of payload storage each, plus
two 32-bit counters per ring: **8,208 bytes** for both `Ring` objects on the
target. Messages occupy a two-byte length and their complete payload. The
PPP datagram buffer remains 1,408 bytes. The dial, PPP and modem timer stacks
remain BSS-backed at 8,192 / 4,096 / 4,096 bytes. The modem's two 1,025-byte
chain-buffer backing arrays remain BSS-backed. No new application queue,
heap-backed snapshot, network thread, assembly or linker mechanism is added.

The normal game-tick send/receive interfaces copy bounded bytes into or out
of those rings. They perform no socket I/O or modem wait. Bulk admission
still checks the existing 2,400-byte queue cap and the existing 32 KiB
`free_chunks + break_room` floor; the latter calls the allocator's
`mallinfo`/`sbrk` diagnostic and is not assumed to have zero cost. A `kos free`
row by itself does not establish that floor: the `brk` value is needed too.

Starting/stopping from the menu is **not allocation-free**: spawning a dial
worker calls KOS `thd_create_ex`, which allocates a thread record despite
the supplied static stack. That allocator and KOS's existing creation
critical section are not priced as a bounded queue copy. Thread creation
failure is handled, and detached records remain owned by KOS's reaper.
The first configuration read still uses disc/fixture I/O from the game
thread. Benchmark configuration tries `/cd/dc/link.txt`, then
`/cd/dc/qa/link.txt`; this review does not turn either read into background
I/O. QA SCRIPT and other existing action-side fixture reads are reviewed in
the main hand-back.

Socket calls, modem initialization, dialing, negotiation, modem writes and
teardown run on the existing background dial/PPP workers. A modem connect
attempt retains libppp's 60-second timeout; stop during that stage can wait
for the current step. The two-second guard bounds **lack of write progress**,
not the total time for a slowly progressing frame or all kernel services.
Entering DEAD uses the existing PPP mutex; this is not a newly proven
hard real-time bound for every hardware failure.

KOS UDP receives allocate one packet record and one data block, then free
both in `recvfrom`. The UDP implementation has no intrinsic receive-queue
length cap. In this transport the same PPP thread produces network input
and drains UDP before its next read pass; `ppp_modem_rx` supplies at most
1,024 raw bytes per pass, with at most one partly assembled PPP frame carried
from the prior pass. The application ring being full does not stop this
drain: excess packets are freed and counted. This supports a finite
per-pass allocation argument for the reviewed single-PPP-receiver setup;
it is not a global KOS socket-queue guarantee if another network producer is
added. No receive-pump iteration limit was added that would leave heap
packets behind while the PPP producer continues.

## IRQ, store queues and PVR

The transport and benchmark code contain no PVR submission, store-queue
ownership or render-scene calls. Modem I/O still competes for CPU and IRQ
service. The pinned driver briefly masks IRQs around its RX/TX lock flags;
the modem ASIC callback handles hardware FIFO work. Its timer worker is
separate from the renderer. No claim of zero frame-time interference is
made from source inspection alone.

The new stack-retirement lookup masks IRQs only while walking the existing
KOS thread list and reading the matched state. Its work scales with the
number of active KOS thread records and occurs on start/cleanup, not every
game tick or byte copy. It does not wait, allocate or call `thd_create_ex`
while holding the added mask. KOS `thd_exit` marks the old thread
ZOMBIE/FINISHED with IRQs disabled before switching away, and KOS destroys
only stacks it owns. Those pinned semantics make reuse of a supplied stack
safe after the checked transition. The modem timer already uses
`thd_worker_destroy` → `thd_join` before its static stack is reused.

## Benchmark row semantics and work bound

Result packets now use a 1,200-byte local array with 48 bytes reserved for
the header; accepted complete wanted lines occupy at most 1,152 body bytes.
This admits every line that fit the old 1,100-byte packet. The fixed local
array increases by **100 bytes**; compiler frame sizes and complete TU
section sizes belong to the target receipts, not this source-level count.

The 2,048-byte scan budget applies to the forward newline scan. Matching
the short `bench: `/`PACE` prefixes and copying completed wanted lines add
bounded rereads, and up to three output packets add formatting/queue work.
It would be incorrect to describe the entire function as exactly 2,048
loads or one queue increment. When an incomplete line is unchanged, its
saved cursor avoids scanning that prefix again. Ring overwrite can make
the function realign to the next newline, so it never treats a surviving
mid-line fragment as a complete result row.

The B `dropped` field is a **byte-gap indicator**. It includes all log bytes
overwritten before the result scanner catches up, the initial unavailable
prefix, fragments discarded while finding the next line boundary, and
oversized wanted lines. It is not an exact count of lost benchmark-result
bytes alone. L remains a sampled log stream. Acceptance into a UDP queue
does not establish delivery, so neither stream is described here as an
end-to-end lossless channel.

## Pinned source evidence

The reviewed KOS revision is
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`, the same pinned source used by
the target compilation gate. Relevant files below are relative to
`KOS_BASE`; none was changed by this build:

| Source | Relevant contract |
|---|---|
| `addons/libppp/ppp.c`: `ppp_main`, `ppp_set_login`, `_ppp_enter_phase`, `ppp_init`, `ppp_shutdown` | Read-pass/pump ordering, recursive PPP mutex, DEAD wakes a connection waiter, login freeing in the setter, pointer loss on reinitialization. |
| `addons/libppp/ppp_modem.c`: `ppp_modem_tx`, `ppp_modem_rx`, `ppp_modem_init` | Transmit-until-complete loop, 1,024-byte RX chunk, 60-second dial-connect limit. |
| `kernel/net/net_udp.c`: `net_udp_input4`, `net_udp_recvfrom`, `net_udp_send_raw` | Per-datagram two-allocation receive queue, receive frees, truncating receive result, stack-backed transmit packet. |
| `kernel/arch/dreamcast/hardware/modem/modem.c`: `modem_shutdown`, `modem_is_connected` | Shutdown does not clear the CONNECTED flag used by the status query. |
| `kernel/arch/dreamcast/hardware/modem/mdata.c`: lock helpers and `modem_write_data` | Short IRQ-masked buffer flags; writes return zero with no software TX buffer. |
| `kernel/arch/dreamcast/hardware/modem/mintr.c`: `modemIntInit`, `modemIntShutdown` | ASIC handler and oneshot timer ownership. |
| `kernel/thread/thread.c`: `thd_birth`, `thd_exit`, `thd_by_tid`, `thd_destroy`, `thd_create_ex` | Returning thunk versus final thread exit, stable-ID lookup, atomic finished-state transition, supplied-stack ownership and thread-record allocation. |
| `kernel/thread/worker.c`, `kernel/thread/oneshot_timer.c` | Timer-worker destruction joins before releasing the worker and timer objects. |

## Verification and limits

[`transport_host.py`](../../../tools/cloud/build28/transport_host.py)
includes the complete production translation units without rewriting their
bodies. Synthetic headers provide KOS classes, timers, threads, sockets and
services. Both O2 and ASan/UBSan pass **28 transport controls and 14 benchmark
controls**; receipts bind the source and fixture hashes:

- [Normal source execution](../../../tools/cloud/build28/receipts/transport-host.json).
- [ASan/UBSan source execution](../../../tools/cloud/build28/receipts/transport-host-sanitized.json).

The controls cover maximum/oversized/empty packets; full and wrapping rings,
including unsigned counter wrap; whole-message rejection; peer/port checks;
receive-first and single-datagram transmit order; non-progress timing and
reset on progress; cooperative retirement; retained live-thread state on
timeout; credential-release ordering; failed login/nonblocking/thread
creation; learned/fixed peer redial; detached-stack retirement; accepted-only
L progress; partial/oversized/overwritten result rows; backlog and retry;
the 2,048-byte forward-scan bound and 1,200-byte wire bound.

These are boundary-controlled execution tests, not real thread scheduling,
target ABI, PPP decoding, modem IRQ, store-queue coexistence or hardware
acceptance. Target warm/cold-I cycles, loads/stores, 32-byte lines, complete
code/local-stack sizes, disabled identity and the whole-frame figure labelled
**MODELLED** are reported with their exact scopes in [build-28.md](build-28.md)
and the shared target receipts. Queue-helper prices do not price modem
blocking, kernel allocator walks, full PPP framing or complete game ticks.

### Independent menu/header review

The separate read-only review of `qa_menu.cpp` and
`platform/include/qa_link_review28.hpp` examined snapshot ownership and
accepted-only progress, T/D pacing against the real transport cap,
disconnect cancellation of PAD/GOTO/teleport/RECORD state, finite-coordinate
admission and the adaptive exact sort. It identified two concrete issues
that the menu owner corrected:

- Sending D through bulk admission would make explicit DIAG wait forever
  while `free_chunks + break_room` remained below 32 KiB. D now uses normal
  transmit admission with the same 2,400-byte queue cap; T keeps the bulk
  heap guard. TX admission itself allocates nothing. This preserves the
  ability to inspect low-memory diagnostics without filling the whole ring.
- SCRIPT GOTO parsed its timeout with `atoi` and multiplied by 30 in signed
  `int` before narrowing. A value of 1,000,000,000 could overflow despite
  the direct GOTO command's existing cap. The reviewed path parses with
  `strtol` and clamps to 60 seconds before multiplying.

The owner reports **830 normal actual-protocol controls**, 166 across each
of five menu capacities/profiles, including both corrections and
queue-cap refusal/retry. Its final sanitizer and target receipts are owned
by the main hand-back. No other concrete correctness defect was found in
the scoped independent review. The earlier suspicion of an old telemetry
tail-buffer overflow was not substantiated and is not a finding: the
original link row fits its reserved tail and `drive_row` already returns
the stored count.

The owner still needs repeated dial/drop/redial, command traffic during
telemetry and benchmark backlogs, free-plus-break memory trends, and modem
operation alongside PVR work on the real console. This review does not
change the pinned modem driver's unrelated allocation-assert behavior or
claim that all KOS out-of-memory paths are recoverable.

# Build28 Python QA_LINK companion review

Final base: `568c357656efbec468db06a282c1f79caebaa725`, the newest `origin/t15/int` at the final rebase.
The frozen production companions were requalified against this base; the parent hand-back records console qualifications. This report covers only
`tools/qalink/qalink_pi.py`, `qalink.py`, the new opt-in `qalink_review28.py`, their README, and
`tools/cloud/build28/companion_contract.py`. These are QA_LINK host companions; none is linked into a game disc.
No private capture or game data is included.

## Findings and corrections

| Original code site | Concrete failure | Opt-in correction |
|---|---|---|
| `qalink_pi.py: Service.serve`, `control_client` | Every TCP connection spawned a worker; line reads and reply storage had no application bound. A client that never finished a line or read its response could retain a worker. | At most eight control clients and eight waiters, bounded input and output, five-second socket I/O deadlines, immediate busy/close on excess admission. Thread-start failure releases the socket and slot. |
| `qalink_pi.py: Service.send` | DIAG used the count of received packets, allowing duplicate parts to finish an incomplete response; malformed totals could raise. Send failures had no `finally` waiter removal. | A unique part map validates total/index/payload bounds; conflicting duplicates and malformed parts fail. Every exit removes the waiter. |
| `qalink_pi.py: Service.send`, `send_command`; `qalink.py: Link.send` | A partial RECORD or a GOTO/SCRIPT `started` line could be returned as success after timeout. The direct Pi client's default 120-second socket deadline was shorter than the 290-second SCRIPT service wait. | Require all RECORD ticks plus summary and require a successful drive `DONE` reason. Incomplete/failed/cancelled results return nonzero. The client deadline includes the service wait plus slack. |
| `qalink_pi.py: Service.send` | Outbound command size was unbounded despite the console's no-fragment requirement. | One printable ASCII command line of at most 1184 bytes, a fixed nine-character ID, and a complete UDP packet below 1200 bytes. Oversized received packets are dropped. |
| `qalink_pi.py: Service.write`, `qalink.py: Link.send_and_cut` | The service log grew without limit. Capture read the full local log or accumulated an unbounded remote awk buffer. | Two retained 16 MiB log generations, bounded streaming readers, an 8 MiB/65,536-line section limit, and bounded subprocess stdout/stderr capture. Oversized pre-existing logs are preserved and require a new path. |
| `qalink.py: do_capture` | A failed start still wrote state. Stop ignored a failed MARK send and could write an empty or incorrectly selected artifact. Reused labels could select an older section. | Start state follows a successful answer; exact nonce-bearing markers and endpoint identity select the section. Stop requires both packet markers; success writes unique filenames then clears state. Failure retains state and reports an error. |
| `qalink.py: summarize`, Pi human line logging | Multipart data may split a numeric token or newline; processing each logged fragment independently changes values. The old “telemetry seconds” count actually counted parts. | Add exact base64 `X28` packet journal records, assemble complete snapshots, then parse fields. Summaries count complete snapshots and explicitly report incomplete/conflicting/expired groups and duplicate parts. |
| New service integration, found during review | Rejecting every request to an endpoint quiet for 30 seconds would prevent recovery when console low-heap policy suppressed only bulk telemetry. A five-second DIAG wait was insufficient for the largest paced snapshot at a slow link. | PING and HELLO can probe a known stale endpoint. Other commands suggest PING. DIAG has a 30-second minimum deadline; no unbounded retry is added. |

The new implementation is a separate helper, imported only by `--review28`. Existing class/function definitions remain
unchanged. The only modifications in the old files are additive argparse options and `main` dispatch. This placement
preserves legacy behavior and keeps console protocol handling separate from the review implementation.

## Changed outputs and operational semantics

Both the Pi service and client must opt in. The PC client propagates `--review28` to the remote Pi send operation and
uses the helper for capture/tail/fetch. It checks the service's STATUS version marker before sending a command. The
opt-in service takes control commands through TCP rather than interactive stdin; the documented foreground workflow
uses a second `qalink_pi.py send --review28` invocation.

Review clients use a bounded byte-counted `Q28` TCP response; legacy plain clients can still issue one command per
connection. UDP headers remain unchanged. A diagnostics data line equal to `.` no longer terminates a review response.
Review captures write `<label>-<nonce>.log` plus `<label>-<nonce>.summary.txt`; they do not overwrite the legacy label
artifact. Capture state is separate from legacy state. Summaries use only fully reassembled snapshot fields and count
actual samples rather than claiming seconds of coverage.

The console can deliberately preempt a pending T snapshot for DIAG. Such a gap, an expired snapshot, or dropped UDP
parts contributes no partial numeric sample. A/R/M and terminal drive packets remain best effort. The Pi does not add
acknowledgements or retransmissions. An error after a drive deadline does not establish whether the console stopped;
the operator may inspect status or send PAD STOP. No automatic drive cancellation is sent.

## Bounds and cost scope

The constants are recorded in `tools/cloud/build28/receipts/companion-contract.json` and documented in the tool README.
The important ceilings are:

- 1200-byte datagrams; 1184-byte command text; 16 parts × 1100 payload bytes. The largest current T capacity is 12672
  bytes and therefore needs at most 12 parts. The DIAG capacity is also within 12 parts.
- Eight control worker threads and eight pending commands. Each command retains at most 128 distinct packets and
  128 KiB including an error allowance. The synthetic full 1800-tick RECORD retains 60 data rows plus its final answer,
  below 24 KiB even when every value is the maximum unsigned 32-bit integer.
- Eight pending T snapshots, at most 140800 payload bytes in their part maps, with a 30-second expiry and 64 completed
  identities retained for immediate duplicate suppression. The summary accepts at most 512 numeric field names.
- Current log and one prior generation: at most 32 MiB combined. Each capture is capped at 8 MiB and 65,536 lines;
  remote capture pipes are capped at 8 MiB stdout and 4096 bytes stderr with a 20-second child deadline.
- Deadlines: PING and ordinary commands five seconds; DIAG 30; GOTO 75; SCRIPT 290; RECORD 1800 ticks 82. No command
  wait exceeds 300 seconds. These are bounded host waits, not a guarantee of console completion at a minimum frame rate.

These are application buffer, file, and worker bounds. Python strings, dictionaries, transient encoding/join copies,
interpreter state, kernel socket buffers and OS thread stacks add storage. No exact whole-process RSS bound is claimed.
There are no new SH-4 instructions, stack allocations, game-thread work, or target data-line touches from these Python
files. Their own SH-4 warm/cold cycles, loads, stores and 32-byte lines are therefore **zero**; the changed console
network and snapshot code has separate measurements in the Build28 hand-back. Pi/PC CPU cycles and cache-line costs
have not been modelled. The host fixture's wall duration is not a Dreamcast timing result.

At this source revision the new helper contains 33094 source bytes. CPython 3.12 compilation produces 51 code objects
with 26292 instruction bytes in aggregate and a largest interpreter evaluation stack of 13 slots. Those values
describe Python code, not target text bytes or native stack depth. Native Pi/PC stack depth has not been measured.
**MODELLED whole-frame accounting:** the off-console companion contributes 0.000 ms to SH-4 execution; a synthetic
frame with an otherwise fixed 30.000 ms remains 30.000 ms when only this companion contribution is included. This
accounting excludes the separately changed console implementation, network scheduling effects and modem behavior.

## Qualification and identity

`companion_contract.py` executes the actual new helper and both actual CLIs. At the named base, all **31 unittest
methods pass**, including eleven real local TCP/UDP service methods. The socket fixtures required the environment's
approved loopback execution permission. They do not contact any external host.

Coverage includes duplicate and conflicting DIAG parts, out-of-order completion, twelve supported and sixteen maximum
parts, malformed bounds, DIAG busy, delayed complete DIAG delivery, all 1800 RECORD samples with the summary received
first, missing/malformed RECORD rows, successful and failed drive terminal reasons, storage limits, 30-second stale-peer
PING/HELLO recovery, oversized packets/commands, eight-client floods while UDP continues draining, slow-reader timeout,
eight-waiter pressure, thread-start failure, send failure, shutdown cleanup, log rotation, capture marker/size/state
rules, split numeric tokens, incomplete/expired telemetry, both bounded subprocess pipes and subprocess timeout.

The identity method compares every existing non-`main` top-level class/function in both old Python files with the base:
their ASTs and complete marshalled compiled code objects are exactly equal. It also executes default/opt-in CLI routing.
The whole Python module bytecode is intentionally not identical: `main` and help now expose the default-off option.
The helper is not imported by default dispatch. This is the precise companion identity claim; target preprocessed/object
identity is covered separately by the parent validator.

Reproduction:

```sh
python3 port/dreamcast/tools/cloud/build28/companion_contract.py \
  --base 568c357656efbec468db06a282c1f79caebaa725 \
  --receipt port/dreamcast/tools/cloud/build28/receipts/companion-contract.json
```

The receipt names the base, interpreter, test results, bounds and source hashes. Hardware DreamPi/modem traffic,
physical Dreamcast redial and captures under genuine console heap pressure remain local-owner checks. No hardware,
modem, SSH-server, end-to-end capture or gameplay result is claimed by these host fixtures.

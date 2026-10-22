# Fresh debug-file admission cleanup

`EVD_DEBUG_READ_CLEANUP=1` defaults zero and requires
`EVD_ADMISSION_TXN=1`. It repairs a separate failure-path allocation leak in
`GetEvd` and `GetBin`. After `HDReadDebugAlloc` succeeds but the table admission
refuses, the call still owns the newly allocated input. The repaired branch
frees that input once before returning failure. Successful admissions transfer
the allocation to the existing dat2 ownership and retain the usual final free.

The transactional prerequisite matters: legacy SetEvd can publish a partial
parent before returning failure; freeing its input would create a dangling
registration. Transactional failure unwinds only its new references and takes
no input ownership. Prior owners and successful lookup paths are unchanged.
This remains the existing synchronous source call contract, without a new
general concurrency/reset/generation policy.

The actual current Dreamcast PCopen/PCcreat backend refuses these host-file
paths. The earlier actual-backend controls establish that boundary; this repair
qualifies the explicit debug-transport success/failure paths with synthetic
inputs. It is not evidence of ordinary gameplay file traffic or a measured
performance improvement.

`test_event_start_rollback.py --debug-cleanup-pair` passes 19 actual-source cases
in each OFF/ON arm. It executes actual GetEvd/GetBin, transactional SetEvd,
SetBin and table deletion. Parent-table and bin-table refusal free the exact
fresh input once only when enabled; no partial registration survives. Successful
event/bin ownership transfer, repeated lookup and final release are checked.
The prior caller and shared-parent cases remain in these runs. Debug transport
and allocator free are explicit observed boundaries; source/host64 adaptations
and other fixture boundaries are recorded in the receipt.

`qualify_event_start_rollback_sh4.py --debug-cleanup-pair` compares whole SH4
event.o against source commit `1d1576c35`, with prior rollback selected when
transaction1 is selected. All four disabled object identities pass for cabin0/1
and transaction0/1. Omitted and explicit-zero compiler commands are exact;
invalid values and absent transaction prerequisites reject. Selected PPC source
preprocessing is unchanged. Enabled text grows32B; data4/BSS640 remain unchanged.
The previously selected static frames remain unchanged; this is not dynamic
high-water or whole-program acceptance.

Receipts: `event-debug-read-cleanup-host.json` and
`event-debug-read-cleanup-sh4.json`. Source SHA
`5a75a243c71492a2e66fa21d470210e3c909767a7d56fc294c808afff749b86c`.
Raw source/commands/binaries are mirrored in
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/debug-read-{host-02,sh4-01}`.
No full linked/overlay build, guest, screenshot, gameplay I/O, console, recipe,
production merge, release or SD action is included.

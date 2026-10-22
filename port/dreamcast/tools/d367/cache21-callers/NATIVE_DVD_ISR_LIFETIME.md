# Native DVD / ISR destination lifetime qualification

Read-only source pin: `edfe8f1765fbbd418235537e7b2f0b3b6aeab25d`.
This extends the corrected `92812cb2a` graph. **The source DVD ISR is native**;
only the old `ReadAreaData` room decode/read branch is PPC-only. No runtime,
shared source, knob, recipe, program or asset changed. Main owns the whole
archive/reset architecture; Claude owns production merge/release.

## Request producers and destination ownership

`cDvdQueue::Initialize:1066` maps mode bit1 to synchronous execution, otherwise
mode0x100 to the ISR slot. Mode4 captures the current heap index and allocates
MRAM; mode2 captures the debug heap; neither stores an allocation generation.
Mode0x8000 enables source part headers, whose destinations can differ from the
request's initial buffer. `Watcher:1640` launches `iTaskExec(DvdReadProc)` for
0x100, otherwise ordinary slot3. A lexical census of143 request/EmReadSearch
lines includes definitions, macros and comments: it is not143 runtime requests.

| Native producer | Mode / destination | Publication and ordinary lifetime ordering |
|---|---|---|
| `ReadAreaData`, read.cpp263 | 0x8104; fresh current-heap MRAM allocation sized from type0 parts | Game room initialization calls `gameRoomMemInit` before ReadAreaData. Caller sleeps/polls until `ReadCheckInfo==1`, then publishes pRoom and binds native room effects/identities. The read can progress on native ISR while main renders loading/UI work; it is not a PPC decoder. Fresh allocation does not alone prove the captured heap stays valid across every reset. |
| `ReadPlayerData`, read.cpp878 | 0x8100; fixed `PL_DATA_ADDR` | ReleasePlData/unbind_player occurs before submitting the overwrite. Caller sleeps/polls completion before publishing native player identity. The fixed address is an authentic source overwrite path; this unit found no still-live old native player borrower at that boundary. The earlier PL/CABIN refusal reachability qualification remains in force. |
| `readEmData`, read.cpp584..593 | mode0x100 only when Rno0==2, otherwise synchronous mode1; headered mode0x8004 for fresh allocation, mode0x8000 for caller destination | Caller waits before native effect/UI/motion binding and module publication. Existing module lookup returns its already-loaded archive instead of rereading it. The caller-destination branch is a source API possibility; the saved source census finds actual EmReadSearch call expressions with second argument0 (nonzero matches are declarations/definition). It is not established as a current route that overwrites an unrelated live archive. A fresh enemy allocation can be resized after completion; that is a separate source allocation identity issue, not asynchronous DVD write after completion. |
| `cRoomData::linkRelData`, roomdata.cpp345 | 0x104; current heap allocation | StageSet stops/unlinks the previous room REL, replaces the stage heap and selects heap3 before requesting the new REL. Caller waits before copying pModule, allocating BSS, linking and prolog. Captured heap number is not a global epoch lease. |

Other apparently dynamic producers were checked: the actual `readEmList` caller
passes1, so its `mode|0x10` request is synchronous. `cDataUnit::wait` and the
setCommand parameter are u8, so `wait|0x10` / `wait|0x8` cannot introduce bit0x100.
Those DataCtrl asynchronous requests use ordinary slot3, not the ISR. The old
ReadAreaData0x8120 plus iTaskExec(decodeData) is in the PPC branch. Raw SDK library
functions do not imply the selected native platform service has PPC semantics.

## Actual source writes and callbacks

Source `fileReadAsync:1204` always supplies `dvdread_callback`. The platform
`DVDReadAsyncPrio:369..472` runs on that same calling thread, inside Re4dcIoScope:
fs_open/seek/read/retries, completion state, then callback, then return. Generic
queue payloads first go into DVD_BUFF (headers into header_buff); subsequent
source readMain steps copy accepted bytes to m_TransAddr. `dvdread_callback:632`
only clears busy and records cancel/size-error flags. It does not publish a
model, invoke gameplay retirement, or arm a later independent write.

`readMain:787..985` validates the resident type0 span before transfer and checks
cancel before copying the staging piece. That check is a capacity rule, not
allocation-generation ownership. Header type0/3 may specify `dest`; type1/2
sound parts select sound MRAM/ARAM destinations. A fabricated header destination
is not a proven asset-triggered archive overlap. The shared staging/header pump
is separately serialized by the DVD source-step borrow.

There is a real second callback policy: Makefile1293..1296 unconditionally wraps
DVDReadAsyncPrio and ARQPostRequest. `audio_strm.cpp:73` matches exactly
`cb_dvd_read_end`; other callbacks use the generic native function. The matched
stream wrapper **does not write its passed GC ring destination**. It marks the
global stream work busy and queues a Pend entry, reporting requested length.
`re4dc_audio_pend_run:101` detaches the batch under IRQ exclusion, then completes
DVDFileInfo and calls the source callback before the next audio driver run
(audio_stub62, audio_aica1445). This repairs source snd_str2's issue-call-then-set-
busy ordering. It is not a new synchronous callback defect.

The actual stream callback scans the four stable Snd_str_work slots, clears
dvd_busy and advances read/DMA counters. It retains no arbitrary archive write
destination. `Snd_str_init` maps the ring to Snd_str_buff/SndMem; source stream
close/abort waits dvd_busy and dma_busy before clearing work. Platform cancel
does not remove an existing Pend entry; the queued completion clears the source
busy state on the following audio frame. Pend stores a work pointer/callback,
not a general archive allocation receipt. Its ordinary source waits and the
separate CABIN audio/world contracts must not be generalized to all archive
borrowers or all reset paths. Source SHD/RIT borrows in the audio driver remain
separate from this skipped GC ring write.

## Cancellation, drain and rearm

- Every native `cDvdQueue::Read:1021` enters re4dc_dvd_step_begin before its
  routine-table call and ends after it. The step includes staging transfer and
  any nested platform I/O/callback. That borrow also increments the executing
  OSThread's nativeIoDepth; it is not restricted to the fs_read body.
- Source step owner/depth serializes the shared header/staging pump. A competing
  source pump waits/retries; same-thread recursive blockRead borrowing is
  permitted. IRQ exclusion protects admission and counter changes, not the
  entire yielding step.
- Native OSCancelThread waits for the executing thread's nativeIoDepth/motion
  scopes, unparks it if required, then holds IRQ exclusion across final zero
  check and thread destruction. TaskKill uses this drain for another thread's
  running source task. Thus source ReadCancelAll's iTaskKill/TaskKill occurs
  before queue-memory clearing, not while the drained worker still owns its
  protected source step. OSExitThread also rejects exiting with an active scope.
- Platform DVDCancelAsync updates state and synchronously invokes its cancel
  callback; it does not interrupt a remote fs_read. DVDCancelAll is a no-op.
  Source ReadCancelAll supplies the meaningful worker drain, then clears queues.
  This does not automatically free all destination allocations; error polling
  separately calls ErrMemFree for an allocating failed/cancelled request.
- Source ReadCancel marks a pending/current request or invokes the synchronous
  cancel callback; it is not the same operation as ReadCancelAll's task drain.
  DataCtrl clear's caller and its ordinary-task scheduling must be considered
  before assuming an in-flight destination free. No target overlap was proved
  from the flags alone.
- ReadNblk2Blk changes policy, kills/drains the prior worker and pumps the saved
  request on the caller. blockRead holds Re4dcDvdBorrowScope across shared header
  save/use/restore and preserves the prior request only if its saved ID, live
  slot and unpublished state still match. It does not resurrect a completed
  slot. Request IDs identify queue slots; they are not heap-generation leases.
- Door transition calls ReadCancelAll/DmaCancelAll before EmReadInit; soft reset
  likewise drains these workers before MemClearAllHeap. Existing earlier
  DataCtrl/weapon/overlay mutations and native borrowers remain main's broader
  reset audit. Those orderings do not close the whole reset transaction.

## Qualification and evidence

The normal source graph admits background native writes to newly admitted room,
enemy and REL allocations, and an explicitly retired fixed player span. It
establishes useful callback/worker-drain semantics; it does **not** establish a
normal request that writes a still-live native effect/model archive after its
heap is retired. The exact destination/range, normal task/ISR reachability and
active borrower would all be needed to make that stronger claim. No adversarial
callback/header/mock interleaving is counted as evidence, and no runtime fix is
proposed by this unit. Current missing diagnostics remain nonreturning.

`audit_native_dvd_lifetime.py` pins23 complete source objects and the lexical
callsite census, with29 static checks and function spans in
`native-dvd03-receipt.json`. Two initial metadata runs failed because a forward
declaration was mistaken for a definition and a brace was duplicated in a search
signature. Their snapshots are retained as native-dvd01/02; neither was a C++
source failure or runtime test. Run03 uses definition-aware, brace-bounded source
extraction. Its snapshot/census/receipt size is1,013,159B. No compiler, target
build/link, stage, guest or asset conversion ran. All snapshots/tool/docs and
failed-run disposition are mirrored; the total unit, including failed snapshots
and mirrors, remains below20MiB. Earlier928 evidence remains untouched. Source,
Flycast, release and physical Dreamcast acceptance remain distinct and open.

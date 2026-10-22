# Direct world draw meter

`WORLD_DRAW_METER=1 PS2_WORLD_DRAW=1` enables a default-off diagnostic. It does
not alter a recipe or change rendering. QA Diagnostics and its QR pages show a
frozen completed window of 60 accepted CPU world submissions, with mean/peak
milliseconds per accepted submission, per-pass mean microseconds, room/generation, first/last render
frame, runtime View setting, actual OP/PT/TR far planes, shell call/success
frames, disc-read frames and stopped frames. The QA header supplies build and
preset identity. The existing broad `scenery` phase remainder is unchanged.

## Boundaries

The total is the sum of disjoint synchronous calls in `native_ps2_world.cpp`:
opaque, punch-through, translucent and the optional far shell. Shell time is
separate from opaque, so it is included only once. Both the coarse entry and
the noncoarse/source entry are covered, including the reference `.r4p` and
kernel paths. Setup, source receipts, diagnostics logging, presentation and
the outer frame wait are outside those intervals. There are two timer reads
per executed pass (normally six, eight with a shell).

These are CPU submission **elapsed** times from KOS's existing microsecond
clock, including any synchronous stall inside a measured call. They are not
GPU render time, independent exclusive transform/submission stages, an estimate
of saved work, or proof of memory stalls. The real-console instrumentation cost
still needs measuring. No per-vertex/meshlet timestamps were added.

The frame starts immediately after native UI's real `++frame`, before its
preload work, and captures the discard baseline there. Eligibility checked at
frame end rejects `present=0`, VI-black, abort and any changed `stream_discards`
since that begin, including earlier scene discards. Eligibility alone cannot
admit a sample: an exact token/frame-bound renderer outcome must also exist.
An early return with no completion stays invalid, and the next begin discards
it. The native skip functions never enter the meter. Thus skipped logic ticks
do not become zero-time images or dilute the denominator. Completion requires
all three main passes exactly once and a **positive** return; source-world `-1`
failures are rejected while preserving the original return to its caller.
Duplicate/partial/main-pass failure/no-world frames clear the current and completed windows. A shell call
returning zero is timed and explicitly counted as an unsuccessful shell call;
it does not erase otherwise complete main-pass timing.

Renderer outcomes have explicit contracts. The synchronous stream path records
the actual `guard_present` decision and successful resolve. Pipeline 1 records
the presenter thread's guarded decision and successful resolve using the token
and frame captured when that work was submitted. Pipeline 2 records its guarded
decision plus successful async queueing or an explicitly accepted Steady defer.
The nonstream path requires successful list and scene finish. These witnesses
establish **accepted CPU submissions**, not an eventual IRQ/vblank flip or
physical display. The QA denominator is named `accepted_submits`; its frame
range is `submit_frames`. This is not a counter of images confirmed displayed.

The presenter writes only a small outcome receipt. Receipt publication and
copying share short interrupt exclusions; that thread never accesses the live
Meter. Main keeps an immutable pending end context if the receipt is not yet
known. Snapshot or the next begin consumes a matching outcome after revalidating
live room/generation/View. If still unresolved at the next begin, that context is
rejected without waiting. Late/wrong-frame/wrong-token/reset receipts cannot
revive it. Multiple outcomes for one token before consumption are ambiguous and
fail closed; duplicate outcomes after consumption cannot count a second sample.
Thus Pipeline 1 may provide fewer eligible samples if its presenter resolves
too late; the meter never assumes that pending work succeeded.

Room/generation changes, world retirement/movie discard, runtime View changes,
per-pass far-plane changes and shell participation/result changes invalidate
the old window. Snapshot readback validates the live room/generation/View again.
No valid completed window means `NA`; it never presents a prior-room number as
the current room. While the next matching window fills, the previous completed
window stays frozen. Diagnostics copies it into its existing text snapshot,
which every QR page then reuses while gameplay is paused.

The existing weak disc-total export marks any frame with changed read count,
including preloads outside the timed pass. If unavailable, `read_frames=NA`.
The source Stop flag marks `stopped_frames`; this is not a claim that every
stopped frame is a room load. Inspect these flags before calling a window steady.
Transformed/submitted vertices, submitted bytes and strips are explicitly `NA`:
the initial unit does not edit `native_static.cpp` or invent counts from total
frame counters.

View names are read from the existing runtime option, not inferred from far
distance. At this source baseline `0=Full`, `1=Near`, `2=Short`; the actual far
planes remain authoritative in rooms with exceptions. A `FAR_SHELL` build knob
alone does not prove participation. In the baseline shell mode 2 is not a valid
isolated shell-cost control because residency is released outside mode 1; this
meter does not use that control. User observations about Full/Short/Near are not
converted into a universal performance ordering.

## Small source/host gates

Run `python3 port/dreamcast/tools/d367/world_meter23/run_tests.py`.

The tests compile and execute the real accumulator and runtime callback unit,
exercise timer/frame/read-count wrapping, mean/peak aggregation, shell separation,
frozen windows, skipped gaps, missing end, partial/no-world/failure/duplicate
rejection, room/generation/View/far changes and read/stop flags. Runtime controls
also cover negative pass/outcome returns, callback-before-end, delayed callback
consumed by snapshot, negative guard/resolve/queue disposition, prior-discard
eligibility, pending work dropped at next begin, late/wrong/reset/duplicate
receipts and changed live identity. Actual host
objects prove the disabled expression wrapper is identical to its baseline
expression (default and explicit zero), and the disabled runtime has no symbols.
Real Make evaluation checks off/on/invalid values and the world-draw dependency.
Supplemental source guards check instrumentation coverage and skip exclusion.

These are host/source results only. Full target object/link, whole-program
knob-off identity, KOS 48 KiB squeeze, r100 s30, source-state/gameplay acceptance,
exact console-mode Flycast Diagnostics/QR capture, timer-overhead measurement
and physical-console timing remain integration gates. No full build, guest,
disc, release, production recipe or SD change belongs to this source-only unit.

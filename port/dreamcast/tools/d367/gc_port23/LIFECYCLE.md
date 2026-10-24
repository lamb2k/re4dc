Current protocol is v2/Required3ff; current wired1f6 remains incomplete because
Motion and geometry/Weapon coverage are unwired. Historical v1 visits cannot
pass the current judge. See PROTOCOL-V2.md; no lifecycle namespace is invented
to imply Motion zero use.

Diagnostic visits use three explicit namespaces. Startup/title/menu rows have
`phase=startup`, loading/door rows have `phase=transition`, and both omit room.
Game-room rows have `room=hhhh` and no phase field. The same visit serial
increases across all namespaces. Exactly one complete startup visit must precede
an initial transition and the first game room in each judged log.
Startup alone is not route coverage. Unknown phase names, both location fields,
room 0000 used in place of startup, missing startup, duplicate/reordered visits
and incomplete checkpoints fail. The startup phase receives the same catalog,
provenance, coverage, counter and overflow checks as every game room.

Allowlist schema 1 now also accepts an exact `phase: "startup"` location instead
of an exact room. Kind, ID, full SHA, provenance, reason, owner and evidence remain
mandatory. Startup and room identities are disjoint; a room exception cannot
authorize a startup asset. The accepted baseline must already contain each
startup exception, so this extension does not learn or add allowances. Missing
historical startup evidence remains an explicit gate failure.

Transition BEGIN adds `transition_reason=initial-room from_phase=startup` for
initial entry, or `transition_reason=room-retire from_room=hhhh` for a completed
room. The origin must equal the preceding completed visit. Each game room must
follow a complete transition; repeated transitions or direct room-to-room
labels fail. Other rows retain only phase/visit so maximum ASSET/COUNTS lines
fit the production 256-byte logger; their allowance identity inherits the exact
origin/reason from the matching BEGIN. Transition allowance entries require
that same `transition_reason` and `from_phase` or `from_room`, in addition to the
human approval `reason`, owner, evidence and full asset identity. A transition
from room0111 cannot borrow an exception for room0113, startup or a game room.

The runtime API separates checkpoint preparation from audio admission:
`begin_startup_closed` or `begin_closed` initializes and logs outside the audio
mutex, with admission still closed. `open_audio_admission` then publishes only
fixed state under the existing audio mutex. Closing admission under that same
mutex precedes unlocked flush/end. Neither admission function hashes, logs,
allocates or performs IO. Outstanding tickets, queue contention and late
startup-to-room completions remain fail-closed and cannot acquire a new label.

For continuous transitions, `handoff_audio_admission` publishes separate next
admission room/visit fields under that same audio mutex before unlocked old END
and new BEGIN. Current events drain normally; exact future-tagged queue events
and tickets remain bounded until the matching `begin_*_handoff` adopts them.
Old/unexpected outstanding work still fails, future overflow still fails, and
explicit terminal close cancels the handoff so pending future work cannot be
silently excluded. No event is retagged. The real production formatter controls
include maximum-width transition metadata and all counters. The core/judge
handoff contract is implemented and adopted by the actual lifecycle helpers.

Successful native UI initialization now starts the named startup visit. Every
accepted direct UI room retirement hands off to transition after the existing
movie-owner refusal and before member/package retirement. Repeated retirement
in that transition is idempotent and still flushes accepted events. The actual audio_step records
SoundBank/SoundStream checkpoints after its original flush under g_lock; the
main finalizer only marks those bits if this visit actually observed that step.
The gate currently requires AICA_AUDIO=1; silent-backend lifecycle qualification
is not inferred. Admission resets the audio checkpoints at the next visit.

Geometry and weapon bits intentionally remain unwired until every specialized
static/coarse replacement carries its own complete payload proof. The current
mask is 1f6 with the qualified native glyph path; a legacy font configuration
also leaves Font unwired. An empty room cannot hide these outstanding bridges.
Existing texture/effect/UI/movie observers and native glyph upload paths get
their final checks at the unlocked finalizer, independently source-audited and
tested for accepted/rejected packets. These declarations do not substitute for
the remaining full callgraph audit or runtime negative controls.

The actual ui_bridge room-entry calls `re4dc_gcasset_room_enter` after its heap-4
open and before room-file/package loads. Root-reviewed audits23 commit 6a3f6b60e
was picked first; all twelve guarded cache diagnostic lines remain composed.
Source-extracted actual enter/leave functions preserve the movie-owner refusal
and absent-live-heap guards: a refused retirement cannot print END. The accepted
UI retirement uses the same transition handoff as direct retirement. The next
room entry atomically publishes its new admission, closes transition unlocked,
and begins that room. An omitted transition is an explicit error, even though
the diagnostic continues collecting evidence. An injected producer during the
old flush/new BEGIN gap retains its transition identity in the source controls.

`re4dc_gcasset_finish` is an exported callable; rr-owned final-stop wiring is
still pending and belongs to root. It closes diagnostic admission, not the
existing audio producer. Later accepted key-ons create unowned faults for the
next pump/BEGIN. A trace cut immediately after END cannot establish absence of
future events; final-stop integration must quiesce accepted producers and retain
the final drain. Loading/door audio now stays in the explicit transition visit;
it receives no inferred game room or PS2 provenance. Missing reviewed transition
allowances, overflow, stale proofs and missing real audio coverage still fail.

Source-extracted real UI helpers and audio-admission code exercise startup to
room transitions, same-mutex publication, unlocked flush/logging, duplicate
retirement, missing audio execution, omitted retirement and visit exhaustion.

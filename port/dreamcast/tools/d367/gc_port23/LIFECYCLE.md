Diagnostic visits use two explicit namespaces. Startup/title/menu rows have
`phase=startup` and no room field. Game-room rows have `room=hhhh` and no phase
field. The same visit serial increases across both namespaces. Exactly one
complete startup visit must precede the first game room in each judged log.
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

The runtime API separates checkpoint preparation from audio admission:
`begin_startup_closed` or `begin_closed` initializes and logs outside the audio
mutex, with admission still closed. `open_audio_admission` then publishes only
fixed state under the existing audio mutex. Closing admission under that same
mutex precedes unlocked flush/end. Neither admission function hashes, logs,
allocates or performs IO. Outstanding tickets, queue contention and late
startup-to-room completions remain fail-closed and cannot acquire a new label.

Successful native UI initialization now starts the named startup visit. Every
accepted direct UI room retirement finalizes after the existing movie-owner
refusal and before member/package retirement. Repeated finalization is
idempotent but still pumps late audio errors. The actual audio_step records
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

`re4dc_gcasset_room_enter` and `re4dc_gcasset_finish` are callable integration
boundaries. Actual ui_bridge room-entry and rr-owned final-stop wiring is still
pending. The ui_bridge shared-file window is temporarily returned to the root
audits23 priority-2 diagnostic hooks; this lane has not edited that file.
Source-extracted real UI helpers and audio-admission code exercise startup to
room transitions, same-mutex publication, unlocked flush/logging, duplicate
retirement, missing audio execution, omitted retirement and visit exhaustion.

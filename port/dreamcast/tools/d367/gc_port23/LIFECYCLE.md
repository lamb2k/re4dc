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

This checkpoint implements the core/judge contract and negative controls only.
Actual UI startup, successful room-retirement and shutdown hook integration is
still pending. The ui_bridge shared-file window is temporarily returned to the
root audits23 priority-2 diagnostic hooks; this lane has not edited that file.

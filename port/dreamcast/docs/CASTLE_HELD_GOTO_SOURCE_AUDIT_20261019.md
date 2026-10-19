# Held enemy movement commands: source audit, 2026-10-19

The original r207 entry event sends D3/D4/D5 and gives D4/D5 a mode13
destination of (-1834,4149,-11795). With cap4, those last two actors can
still be held when the room calls the live-only `cEmWrap::setGoto`.
Main's original-route capture observes D4 admitted after D8 dies, then
`Goto_mode == 0` and a zero secondary floor target. This narrows a lost
command; a repaired matched run is still required.

Observation: `r207-I013-normal-held-D4-goto-observation-20261019.json`,
SHA256 82e413168ee6d14142e48690156c191be171b47c5651971284f49df6acbbd7af.
Its actor+0x9D0 sample is **x5F0**, not the separate Goto_pos field;
actor+0x9CC is Goto_mode. The file binds the original controller logs,
saved states and exact immutable ELF746 capture. No memory was written.

Relevant source:

- `src/st2/r207.cpp:491`: sends; lines500-503 give the movement orders.
  Lines523-524 repeat them on the event-cancel path. Later waves at
  lines549-552 and565-568 also send then give orders.
- `src/st/em_wrap.cpp:984`: the wrapper forwards only to a live actor.
- `include/em_wrap.h:98`: cEmGanado is the virtual forwarding declaration.
  The implementation is `src/em10/em10.cpp:24277`, cEm10::setGoto.
- `src/em10/em10.cpp:2941`: original initialization clears Goto_mode.
- `src/st2/r203.cpp:221`: GetKeyItem immediately gives each new actor a
  destination. This is an additional source risk, not a reproduced
  r203 failure yet.

The original setter copies the target, queries its floor, changes work
flags and respects an existing protected-state guard. Any narrow fix
should invoke it after initialization. Copy the input Vec and mode,
since the room's Vec is stack-local. Use a separate valid bit because
mode0 is a real command. Later goto calls should replace the pending
one. The record belongs to the queued entry, shared by its wrappers;
it must survive compaction and allocation refusal and disappear on
destroy or room/Continue/list reset. Preserve the wrapper ABI and cap
admission; `getPtr` must not be used to force the enemy into existence.

Do not extend this blindly to all setters. In r207, setNoSuspend1 is
followed by setNoSuspend0 before the event ends. Replaying only the
earlier command would create a different bug. Floor evaluation at
admission also means this restores the delayed command under cap4;
it does not prove identical uncapped timing.

Keep the implementation default-off until actual-source queue/lifetime
tests, Disc1 off identity and a matched r207 release/movement test pass.
Check r203 key/door progression and movement wait loops separately.
No source runtime edit is made by this audit. The already tested
setFlag preservation remains a separate change.

Full source hashes and test constraints:
`workers/ch34/held-goto-source-audit-20261019.json` under the castle
evidence root. The frozen diagnostic program does not qualify the
new ACTOR_PLAN chapter acceptance build.

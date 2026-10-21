# QA shortcut leaves a stale map tap

The original QA shortcut opens correctly after 30 safe gameplay ticks. On a
standard controller, one mapped Down poll is enough to arm the short-tap map
action. The QA menu then stops game polls, reads the raw controller itself,
and waits for release. On return, the mapper sees Down released and emits
two synthetic GameCube Z polls. The map opens immediately; its existing
subscreen safety gate correctly rejects a further QA shortcut.

The repair reserves the raw QA chord in QA builds and clears its tap state.
It consumes Down through partial releases so releasing triggers before Down
cannot create a new map tap. Ordinary map taps and dual-controller mapping
remain covered. The raw QA menu's free-play, event, player routine, subscreen,
and 30-tick gates are unchanged. `qamenu.mk` passes the existing QA define to
the pad object only when QA_MENU=1; no release default changes.

## Reproduction and identity

Private evidence: `feedback21-boss-qa-20261021/qa-reopen03` under the normal
Flycast evidence root. The normal QA preset is r100. Only controller posts
to the owned emulator PID were used; no game-state, HP, AI, invincibility,
forced damage or encounter writes were used.

- Input source: aafc10f3601b087f60311ca5f24bb641ef6114bb.
- Track03: 5ae451a0cb1e5c6e6db9b68d27335a09a00d27abd83e9c838c66ef2f8b69cfa8.
- Raw program: 8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d,
  3,348,164 bytes; matches the preserved OFF ELF's independently extracted
  binary exactly.
- OFF ELF: 4c92ce29920476605c297bc5ea319bde9bbd24a1a5a5a6bc5012c4a31ebc9a2c.
- The pad source is unchanged from aafc10f3 through this branch's original
  892c10dd base. Layouts and addresses come from the matching ELF's DWARF/nm.

Read-only, non-atomic samples show qa_frames=32 at game frame213, Rno=3/0,
player routine0, event count0, subscreen0 and QA flags0 before the chord.
The menu holds game frame218 with mapped triggers150/150. Normal Start
closes it; the log then reports mapped buttons0010 and subscreen type2.
Samples show the map active at frame220, with qa_frames reset to0. No ring
overrun was reported. A pending second chord was withheld by the observer
because the map's safety gate was active. The 48-second host guard ended
the run; that termination is not a game hang.

Earlier attempts sent the chord during room load and are retained as
unqualified input attempts. Host timestamps are controller/capture context,
not Dreamcast performance measurements. This current QA program has not
been established as byte-identical to the original tester's public build.

A second unchanged-program run, `qa-reopen04`, completes in46.1 host seconds
with no runner errors or log overruns. It opens the QA menu, closes with
normal Start, then closes the unsolicited map with ordinary B. The map's
backing restore hash matches its saved hash. The QA chord subsequently
opens the menu again; closing repeats the unsolicited map. Thus reopening
is possible after the map is closed. Actual menu screenshots are preserved
in `events/05-before-start/frames/fb0.png` and
`events/09-before-start/frames/fb0.png`, with source state context adjacent.

## Source validation

Run `python3 -m unittest discover -s port/dreamcast/tools/d367/feedback21_boss_qa -p 'test_*.py' -v`
and `python3 port/dreamcast/tests/test_pad_mapping.py`.

The actual original mapper is a negative control: a one-poll full chord
produces two stale map polls. The repaired mapper passes 33 release-order,
context, controller-kind and threshold cases, including ordinary map taps
after the chord. Its complete host mapper object matches the original
exactly with RE4DC_QA_MENU undefined or0. The existing standard/dual mapping
suite also passes. A fourth focused test evaluates the actual qamenu.mk
include and verifies that the pad-object QA define is present only in QA
builds. Only port A reserves the shortcut; other ports retain native Down.

This is source/host qualification. A rebuilt matching QA program must still
show menu close, normal play and repeated reopening without the map opening.
No fixed-program runtime, hardware, release or whole boss-fight acceptance
is claimed. Mendez's actual normal fight/resume remains a separate open gate.

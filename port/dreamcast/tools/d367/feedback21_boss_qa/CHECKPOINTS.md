# Unedited checkpoint continuation

Main explicitly authorized this continuation on October21. Every checkpoint is
Flycast's normal AutoSaveState on owned SDL-window close, copied byte for byte to
the next private guest. There are no serialized-state edits, field pokes,
invincibility, forced damage, enemy/phase/RNG writes or retargeting. The first
checkpoint follows our recorded original QA-menu r11f selection and ordinary
controller walk into the meeting trigger. It is a preset-started route; a natural
no-warp boot-to-boss release check remains separate.

`checkpoint_runner.py` derives from the SHA-pinned original fullplay runner and
adds exact data copying, explicit AutoLoad/AutoSave slot0 and graceful bounded
unload. `run_unchanged.py` retains the one owned guest, PID/path/start identity,
global launch-pressure and 48-second hard guards. Normal close begins at the
requested bound minus half a second. The health guard reads DWARF GlobalWork.pl_life
and closes on its first natural decrease. cEm.hp on the player is not authoritative
life; earlier actor-HP samples cannot qualify that guard. No health value is set.

`checkpoint.py` reads FLYSAVE1/RZIP without modifying it. Four distinct 256-byte
immutable .text signatures at actual ELF addresses uniquely locate contiguous
16MiB main RAM. All context reads are bounded and use the exact ELF's DWARF fields.
Each receipt seals disc files, raw program, ELF, emulator, complete emulator data,
serialized state and controller records plus its parent's receipt hash. Before
restore all hashes and code anchors are rechecked. The restored initial data must
equal the sealed parent exactly. The reader waits for Flycast's actual successful
load record, then continues after the parent's sealed log head; historic bytes are
not mislabeled as a new ring overrun. No live overrun is suppressed.

The first checkpoint matches unchanged raw program
`8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d` and
ELF `4c92ce29920476605c297bc5ea319bde9bbd24a1a5a5a6bc5012c4a31ebc9a2c`.
State e566b5a5337190dcddafada4c4a83e8a9f8c5c5b35e86e5596ab6cf135f97c41
saves at room11f/source frame714, original meeting event, life1200/1200 and QA
flags0. The original source QTE prompt begins at cancel-clip picture145, lasts
25 pictures, and requires its randomly selected exclusive A+B or L+R chord.
Early or simultaneous four-button probes fail normally; they are preserved.

`mendez-checkpoint05` restores that checkpoint unchanged, passes the source QTE
with ordinary L+R at153/170, skips r11fs02 normally, and reaches actual alive
em35/type0 with HP1500. Start enters and exits the original option flow. Its actor
motion freezes at68 during the pause; after normal resume it walks from z=-57564
to -61538, enters attack routine1/4, and naturally hits Leon1200 to400. The guard
saves and exits in25.8s. Actual before/paused/attack buffers and read-only source
context are retained. Thus this bounded unchanged-current-QA run does not reproduce
a boss that remains frozen after resume. Original tester build/device and later
forms/phase progression are not established by it.

The focused repeat `mendez-checkpoint06` holds the actual visible OPTIONS menu
for six host seconds before normal Start resume. The paused source sample is
Rno=[6,1], Stop_flg=0x7fffffbf with em35 motion83. After the original resume
reaches Rno=[3,0]/Stop0, ordinary back+B is held exactly45 source frames971-1016.
Leon responds and changes direction/position, while the boss continues motion
and AI through source frame1522. Life remains1200, QA flags0. The owned guest
exits in45.0s with errors=[] and zero log overruns. Its actual paused-menu PNG
is events/04-before-start/frames/fb0.png, inspected alongside the combat/attack
captures from repeat05. Earlier probes02-04's missed/invalid QTE attempts remain
separate from these two qualified combat observations.

Synthetic tests reject malformed containers, changed disc/emulator/data ancestry
and a mismatch in any of the four code anchors. Actual private checkpoints are
never used as mutable test fixtures. `mendez-checkpoint01` had a harmless observer
teardown-read race after normal save/exit; its error is retained. Later runs avoid
sampling after normal close is requested.

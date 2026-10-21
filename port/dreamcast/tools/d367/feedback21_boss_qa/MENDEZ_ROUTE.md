# Mendez original-route continuation: combat pause/resume passes

The latest original-program checkpoint continuations now reach combat and test
ordinary pause/resume. Repeat05 shows actual em35/type0 moving and naturally
attacking after resume; Leon's authoritative life drops1200 to400 and the health
guard ends the guest. Repeat06 holds the visible OPTIONS menu six seconds,
resumes normally and accepts45 source frames of ordinary back+B input. The boss
continues moving/animating through source frame1522 with Stop0, life1200 and
QA flags0. See CHECKPOINTS.md for exact ancestry, program/code binding and PNGs.
This does not reproduce a post-resume boss freeze on unchanged current QA.
Tester Release21 program/device identity and later boss phases remain open.

## Preserved earlier route probes, before checkpoint authorization

The unchanged aafc10f3 QA disc's r11f entry preset starts outside the barn.
It does not spawn a combat Mendez immediately. With ordinary controller
input, the player reaches the original meeting volume, starts movie11f00,
uses normal Start skip, and reaches the original QTE/cancel clip1011f00.
No combat em35 actor has been observed yet. This does not reproduce or
refute the reported post-resume boss freeze.

The disc/program/ELF identity is recorded in [QA_REOPEN.md](QA_REOPEN.md).
The exact standard QA preset has no invincibility, forced damage, goto,
phase or AI commands. The default VMU is empty. The forced Mendez second
form fixture was deliberately not used.

Read-only extraction of the actual selected `st1/r11f.dar` gives SHA256
2dd4355511221247d3e411927ebaad8ec4e24ae2dd55495dde482843fee6e855.
Its AEV0x18 meeting volume has XZ corners
(33261,-49029), (45339,-48184), (46921,-45171), (33094,-44976),
with floor-8278. This is navigation evidence, not a forced warp target.
The route uses normal forward+B, left-stick turning and the original
trigger's own event logic.

`mendez02` establishes normal movement from (7719,-1025,-10620) to
(30148,-3757,-17770), HP1200 and Stop0. The pause guard correctly withholds
Start because no Mendez actor exists there. Subsequent route probes reach
the meeting. Movie11f00 has1465 pictures and48.882166 seconds of media.
Movie/route control stops and player routine5 at that point are expected
event state, not evidence of an AI freeze.

`mendez06` and `mendez07` use the actual game frame counter for normal
movement and normal Start movie skip. They reach QTE clip1011f00,170
pictures/5.706 seconds; normal A+B+L+R presses are posted to the original
QTE. The run ends before the QTE outcome/follow-up movie/combat is observed.
Both have zero ring overruns and complete with owned guest exit within50
host seconds (48.4 and48.5 including cleanup). No guest-state, HP, AI,
invincibility, phase or forced damage writes, or state restores were used.

The earlier WSL FP_NOLIMIT export did not cross to Windows; those runs
remained at the normal setting. `mendez07` uses the explicit `--no-limit`
argument and verifies `aica.LimitFPS=no` in its private emulator config.
That setting still does not complete the approach and original event
within the bounded run. No host elapsed time is a hardware measurement.

Actual meeting-movie screenshot: private evidence
`feedback21-boss-qa-20261021/mendez07/events/10-before-start/frames/fb0.png`,
with sampled source context adjacent. This is a movie image of Leon and
Ashley before combat, not a native boss rendering acceptance still.
The latest run also preserves exact owned tool snapshots and SHA256 values.

At that earlier checkpoint the remaining gate was to continue through the QTE and
follow-up movie, observe a real combat Mendez, pause/resume normally, then
record movement/attacks and source stop/motion state. Untampered emulator
checkpoint continuation was raised with the coordinator because every
guest must remain bounded; none has been restored without clarification.
No boss runtime or AI repair was justified by those pre-combat probes.

# Preserve the original presentation failure, 2026-10-09

The issue 9 console backtrace enters `re4dc_missing` through the presentation
fence while uploading a texture. That fatal handler sleeps forever. Thirty
seconds later, the watchdog previously displayed a generic hang, obscuring the
original reason and the graphics state when the failure occurred.

With `CRASH_SCREEN=1`, `re4dc_missing` now captures the first reason before
logging or sleeping. The existing watchdog shows **MISSING** and that reason.
It also shows the captured UI frame, pending-presentation flag, TA readiness,
PVR frame/vblank counts at failure and at display, and raw TA vertex/OPB bounds
and positions. `ta0` means available; `ta-1` means busy. OPB position remains in
raw register units, which are words on hardware. The captured ISP vertex-buffer
address identifies the render bank separately from the TA input bank.

The snapshot is immutable after the first fatal call. It tolerates an
uninitialized PVR and a KOS build without the optional async-present query.
There are no extra per-frame polls, allocations, register writes, IRQ handlers,
timeout changes, recovery attempts or gameplay changes. Builds without the
crash screen use an absent weak hook. Normal fault, halt and hang reports remain.

## Evidence and limits

- Host sanitizer tests exercise the actual fatal handler and snapshot: capture
  precedes logging, the first record survives later failures, an uninitialized
  PVR is not queried for readiness/registers, long reasons are bounded, and the
  optional async query may be absent.
- The existing full crash-screen layout test now includes the new rows and
  verifies that the main/task backtraces still fit a 640x480 photograph.
- A private `crashtest.txt` value `missing` deliberately invokes the fatal path
  and blocks the next game-task signal. The 81.88-second Flycast test visibly
  shows the exact reason, snapshot rows and both backtraces. PVR frames remain
  291/291 while vblanks advance 1188/2981 in the inspected image. This is a
  display/retention test, **not reproduction of the console presentation hang**.
  The test fixture is absent from normal media.
- The combined transparency/snapshot traced build, ELF
  `6be21e3c787f23e7a29e807c58a6a1ab5c3f19b58af7a5c0f39fb4f0398f2e5d`,
  completes the r108-to-r109 source-transition fixture in 240.97 seconds:
  2,937 STRICT frames and required decisions, 14,389 identical raw records,
  zero reported errors, fence timeouts or presentation failures. Both inspected
  views retain the scaffold correction. Synthetic placement/god mode and
  ACT_CAP=0/Off remain explicit; this is not physical-console acceptance.

This instrumentation can distinguish a fatal wait whose PVR frame later
completed from one that remained stuck. It does not expose every internal KOS
state or retain all earlier ASIC error IRQs. Zero register/flag values are not
proof that no earlier overflow occurred. The hardware root cause remains open.

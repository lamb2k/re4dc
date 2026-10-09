# PS2 world transparency order, 2026-10-09

The r109 scaffold could show trees and fog through foreground wood, with large
black surfaces. PS2 scenery was submitted in package order while PVR automatic
transparency sorting was disabled for UI ordering. Translucent world polygons
do not write depth, so package order cannot resolve their mutual overlap.

`WORLD_AUTOSORT` uses the existing KOS per-bank sort mode. It defaults to 1 for
`PS2_WORLD_DRAW=1 SS_UI_ORDER=1`; other profiles default to 0. An explicit 0
retains the comparison path. No converter, package, queue, framebuffer, source
gameplay or memory-budget change is involved.

The current TA bank is reset to manual ordering only after the first list has
acquired it. World submission then enables automatic sorting once. Inventory,
pickup and movie ownership retains source ordering. Planar HUD, glyph, post and
screen-effect packets receive increasing constant reciprocal depth when they
are actually emitted, preserving overlay order and texture coordinates. World
effect depth is unchanged. Changing the global initialization flag alone would
not preserve those UI semantics.

## Qualification

- Host tests exercise the production bank-acquisition order, ownership gates,
  8,192 overlay layers, exact post/sprite packet transformations, disabled
  nonstream compatibility and profile defaults. Address/undefined sanitizers pass.
- Flycast, ACT_CAP=0, Off, synthetic r108 placement followed by the ordinary
  source door into r109: 241.67 seconds, 2,936 STRICT frames and 2,935 identical
  required decisions. All 14,377 common raw source records match. Of 1,198
  payloads, only the boot program and relocated subscreen overlay change.
  Foreground scaffold surfaces are restored in both inspected views. A separate
  per-pixel renderer run retains that improvement. Some dark surfaces remain;
  this does not classify every dark pixel as missing geometry.
- Original supplied VMU, ACT_CAP=0, Fast: 361.08 seconds, 6,311 STRICT frames,
  6,310 identical required decisions and 22,796 matching raw records. Ordinary
  combine/examine/rotate inputs, three exact 3 MiB inventory restores and walking
  pass; four checkpoint images were reviewed.
- Nominal SH-4 model at 200 MHz, ACT_CAP=0, Fast, r102 walking after the third
  inventory close, source frames 142820-142823: 63.193515 to 63.003683 ms/frame
  in the instrumented build, delta -0.189833 ms. All four frames are drawn and
  every recorded instruction is projected. The 32-tick census has 32 draws,
  zero skips and 64 candidate sort-mode calls. 2,720 post-load frames/decisions
  and 10,239 raw source records match. This is no material CPU regression in
  this sample, not a speedup or physical-console FPS claim.

The earlier r109 cost pair is **rejected**: different boot loading yields led
to different source state at the nominally equal frame numbers. Its 100.25 and
99.55 ms values are not an accepted delta. The earlier visual candidate that
reset tile mode before TA-bank acquisition is also rejected and retained.

Qualified visual/runtime ELF: `e89e5b46a3459bbc36dffdd533ed92cc01704dee15e3ebd31004dcb224f743de`.
The compatibility rebuild ELF is
`4eaa76edf6d82e7709ce40d0fd45af68df3fbb4367cbb029d991d146a429ab9a`;
every loaded byte and relocated overlay is identical. Their loaded program SHA
is `a6f178a39fb7e3ca9a816837515ae392c86b7aaeb88af7a119acacd729e43b24`.
Traced-build text grows by 512 bytes; linked data/BSS sizes are unchanged.

The physical bridge presentation timeout remains unresolved. These bridge runs
never block in the timed presentation fence. Automatic sorting's physical PVR
cost is not measured; this change is not a timeout fix. All private captures,
inputs, models and rejected attempts are preserved separately; none are
published with this document.

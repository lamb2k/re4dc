# Lane trans17: the game-wide transparency policy (Test 17)

Design: `C:\Game Dev\Emulators\TRANSPARENCY-PLAN-20261017.md`. Branch `lane/trans17` (base origin/t15/int cbdde6de).
Coordinator decisions (10-17): the class table lives in a separate sidecar (ps2-world.r4tc), with no package or image
change. Tier 2 thresholds: <= 1.0 % of pixels changed, nothing changed outside a 2-px dilation of the converted
geometry's silhouette, and a max delta of 24/255 inside it. Tier 3 items wait for the user: flat walls over the
threshold, extending foliage Near beyond ch1, and the island. Equal-header merges stay out (they would change packages).

## Built (phase 1, b197ea77)

- `TRANS_POLICY=<mask>` (game/hwfog.mk). Unset or 0 = no code, identical image. Built bits:
  - 1 FLAT: uniform 14/15-alpha parts and fully opaque textures in the translucent pass draw opaque (Tier 2);
  - 128 DROP: translucent parts whose texture has alpha 0 everywhere are not drawn (Tier 1; no such part exists in
    the 66 packaged rooms, so it is a guard for future rooms).
  Bits 2/4/8/16/32/64 make the build stop with an error until they are built. The old knobs keep their code, and the
  alias table is in hwfog.mk.
- Runtime (`platform/native_static.cpp` `trans::`): reads `/cd/dc/native/rXXX/ps2-world.r4tc` (R4TC v1, bound to
  the R4PW body crc). It adds the opaque-pass bit to the PS2_PASS_MASK byte of placements holding a moved part. The
  runtime word is `re4dc_trans_policy`, the warp line is `trans <mask>`, and the log lines start `trans:`.
  Vertex-alpha parts never move, and FOLIAGE_TRIM's choice wins. After a movie-arena re-adopt the policy is idle
  (no I/O is allowed on that path).
- `tools/d367/tr_classify.py`: the class of every part, written as sidecars plus TRCLASS.tsv. It is deterministic
  (`--check`) and has a coverage gate (`--strict`).
- `tools/d367/tr_pixdiff.py`: the Tier 2 gate with the thresholds above. Pure Python: PNG/PPM input, JSON output,
  heat PNG.

## Evidence

- Knob-off identity with T15_ST="": the rP image 52f7b2d14ea1d221 and the rW image 643ed2357201c228 are identical
  between base cbdde6de and the lane. The TRANS_POLICY=129 rW arm links with missing=0 and _end +1,376 B.
  Logs: /root/probe/trans17/k.
- Classification: C:\Flycast-Evidence\re4-dreamcast\trans17-20261017\classify (66 rooms). It is deterministic, and
  all 2,634 translucent texture classes agree with the plan's census. FLAT is r109 769 KB and r119 791 KB.
- Foliage pass-mask question (10-17): with PS2_PASS_MASK=1, Near cards in placements whose only parts are
  translucent are drawn in no pass. This is fixed by FOLIAGE_NEAR_FIX (lake17, 2f26b834/49f205f2), which is ON in
  16.4 but NOT in t15/int: t15/int needs it merged before Test 17.

## Next (phase 2)

Stage the r109/r119 sidecars, run TRANS_POLICY=1 against 0 and judge each with tr_pixdiff, Flycast ms (labelled
Flycast), the STRICT trio, then Part B census rooms r100 / r101 / r109 / r119 / r11e / r200.

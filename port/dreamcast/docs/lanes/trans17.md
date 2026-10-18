# Lane trans17: the game-wide transparency policy (Test 17)

Design: `C:\Game Dev\Emulators\TRANSPARENCY-PLAN-20261017.md`. Branch `lane/trans17`, rebased onto t15/int b5537823
(FOLIAGE_NEAR_FIX now comes from t15/int). Evidence: C:\Flycast-Evidence\re4-dreamcast\trans17-20261017.
Coordinator decisions (10-17):
- The class table is a separate sidecar; no package or image change.
- Tier 2 thresholds: <= 1.0 % of pixels changed, nothing changed outside a 2-px dilation of the silhouette, max delta
  24/255 inside it.
- Tier 3 items go to the user. Equal-header merges stay out.
- Use a per-disc index, not a sidecar in every room.

## Built

- **`TRANS_POLICY=<mask>`** (game/hwfog.mk). Unset = no code, identical image. The runtime word is
  `re4dc_trans_policy`; warp lines `trans <mask>` and `transfar <low%> <high%>`.
  - 1 FLAT: uniform 14/15 alpha parts and fully opaque translucent-pass textures draw opaque.
  - 2 CARD: CARD_NEAR parts (texel alpha error <= 0.08) draw punch-through.
  - 4 SOFTA: CARD_SOFTA parts (error 0.08-0.15) draw punch-through.
  - 8 FAR: passes 1-2 stop where this frame's loaded PVR fog table reaches `re4dc_trans_far_pct` (default 70 % for
    cards moved to punch-through, 90 % for the rest; vertex-alpha and opaque parts are untouched).
  - 128 DROP: parts whose texture is alpha 0 everywhere are not drawn (none in any packaged room).
  - 16 VA, 32 FX, 64 WATER: refused until built.
- **`TRANS_POLICY_DEBUG=1`** (test arms only): `transdbg <class mask>` drops those classes in any pass. A still taken
  with it is the silhouette input for `tr_pixdiff.py --mask-diff`.
- **Sidecars:** `dc/native/rXXX/ps2-world.r4tc` (R4TC v1, bound to the R4PW crc) plus the disc index
  `dc/native/trclass.idx` (R4TI). The index is read once, so a room without a sidecar costs no file open.
- **Tools:** `tools/d367/tr_classify.py` (deterministic; `--check`, `--strict`; writes the sidecars, TRCLASS.tsv and
  trclass.idx) and `tools/d367/tr_pixdiff.py` (the Tier 2 gate; pure Python).

## Gates (10-17)

- **Knob-off identity, T15_ST="":**
  - cbdde6de: rP 52f7b2d1 / rW 643ed235, identical between base and lane;
  - 509076dc: rP 5be87ce8 / rW 5b949dd0, identical between base and lane.
  - b5537823 changes hwmodel tools only.
- **STRICT trio** (TRANS_POLICY=15 on, sidecars and index on the base, SS_CLOSE_HOLD with `sshold 1232` on h2):
  - h2 and bell: MUST-IDENTICAL.
  - door103: STRICT; decisions differ only at ep@1176, which land17 shows between two knob-off runs (run noise).
- **Look** (frozen frames, A = trans 0, silhouette = transdbg):
  - FLAT: r109 tier 3 (28 % changed, max 107); r119 tier 3 (2.4 %, max 82). Stills are in flat\.
  - CARD: r100 / r101 0 px changed; r109 tier 3 (0.10 %, max 33, 4 px outside the mask); r119 under its frozen-frame
    noise (r119 A vs A repeats differ, so its numbers are not usable).
  - SOFTA: r100 / r101 / r109 0 px changed (FOLIAGE Near already moves the near ch1 cards).
  - FAR: r100 / r101 / r109 0 px at 70/90; r100 0.002 % (max 8) at 50/70: tier 2. The cuts land at 23.5 / 25.0 m
    (70/90) or 22.2 / 23.5 m (50/70) against the 25 m fog far, so FAR removes almost nothing.
- **Flycast ms:**
  - FLAT: r109 CPU 47.4 ms in both arms, r119 41.0 ms in both.
  - CARD / SOFTA / FAR: same draw count in passes 1-2 or fewer clusters only at 22-25 m. No CPU change is expected;
    the gain is GPU fill and console-only.

## Open

- FLAT and CARD (r109) are tier 3, so the decision is the user's.
- Every class is GPU-only: it needs a console benchmark disc with `trans` warp arms.
- r119 frozen-frame noise needs a deterministic view.
- r11e / r200 are not on the 16.3 base.

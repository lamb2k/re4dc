# Boss18 r224 original twins source, 2026-10-18

This bounded step prepares the original full type1/type3 bodies and full auxiliary source. Both bodies draw in the source room diagnostic. The complete PS2 boss is unqualified: separate chain material and ObjMgr ownership, props, audio, residency and complete fight gates remain open. No reduced model, source fallback approval, engine implementation or production selection is included.

## Original source and owners

Original em2b.dat is4899744B, SHA256 ab04fb10bf115d731269fdb5f8139998d5decb005fa37bc752e4a6e7f35c6562; original em2b.drs is6365504B, SHA256 a6bf8a8bb5387f730d238f953674372b5fb5c573dd1f453b5838d0e846752fdf. These are different forms from r119type0/r11etype2; their geometry was not substituted.

|Source|Original GC joints/PS2 parts; infos|Full triangles/strip vertices|Source systems|
|---|---|---|---|
|type1 BIN8+9/TPLA|74/74;2|4448/6612|10 embedded chain-cloth parts64..73; original grabs, parasite and source event handoff|
|type3 BINE+F/TPL10|66/66;2|4706/7100|three separate nine-part chains attached59/64/65; source grab, cart/lava and death callbacks|
|cObjChain id1D BIN13/TPL14|9/9;1|320/432|three original source instances; separate opacity image1, partial alpha and original procedural chains|
|cObj16 type8 BIND6/TPLD7|25/25;1|907/1407|parasite attached body62; original D8..DE motion slots|
|cObj16 type9 BINE0/TPLE1|10/10;1|111/121|up to ten original procedural tentacles attached body2|

For both bodies, independent original PS2 ordered oriented corners/positions/weights/normals/material-TPL atlas UVs and all original GC parents/rest pass. Existing0.02mm source joint tolerance was reused; observed maximum0.011126mm. Current512KiB native host3poses/GXVERIFY pass. Original encoded textures were reused byte-exact; independently encoded outputs remain unselected.

The auxiliary source has the same independent corner/weight/normal/UV/original-owner proofs and512KiB native3pose/GXVERIFY. Independent original PS2 decode plus the existing character-image interlace transpose exactly matches selected source RGBA atlas cells. Failed/unselected shift4 and unoriented auxiliary preparations remain private. The chain uses the existing shift2 input to satisfy unchanged signed16 bounds. It has no encoded RGB565 texture and no regcast admission: materialflag7 uses diffuse0, opacity1 and bump2; preserving diffuse partial alpha alone does not qualify its separate opacity/blend/order contract. All three original oriented images remain separately preserved. No tolerance, runtime capacity, source checker or material gate was changed.

## Full source packages

The two-body package is byte-identical to Castle's retained original full package:187584file +20160skin =207744/425984B, SHA256 c6412eb08717da0f319f80f7c9f0b8a59a57778c5e2dae8b47139dca574c1674. Eight actual target controls pass under96bones/ROLE_TEX23=0: good, wrongroom, corruption, invalidweight, plus self-parent/nonfinite bind for both owners.

An explicitly incomplete four-descriptor source package adds the full25part parasite and10part tentacle:210976file +23280skin =234256/425984B, SHA256 9ba91baab91fc5b5404e6526799915b0100e532a8be67c1f35ae322170e89fd4. Twelve actual target controls pass, including self-parent/nonfinite bind for all four owners. Separate unsupported chain is excluded explicitly; this is source preparation, not whole-boss admission. The new specs configure existing registry data only. No chapter recipe selects them.

## Source diagnostic and measurement

Build b18abrT is runtime3830a335, clean sourcef5214b22, CH4+T15 cap4 with actual49152B KOS hold. Stripped ELF e3b60546cc768bb62978212aa16a67612e1f7ee9797c81f36f0378d06ec39329; retained final pre-strip ELF6e9cda07d1485740b4fdf2f8220f402f6f6fed877dc6baccaf1923fda74bf580. All linked overlays and boot were pinned.

Original staged ESL C8/C9 are types3/1, HP1000 each. The disclosed initial position6000,0,-6000 is inside original AEV9; ordinary forward at240/60 lets the original source callback construct both actors and run its platform/camera/no-suspend/restore sequence. No HP, damage, kill, god, flags, atfunc or source state commands were used. Positioning is not route traversal.

The55s-budget normal run actually lasts56.22s. Both original bodies remain alive HP1000, moving and native-drawn74/2 and66/2, cumulative599draws each. First run exposes the missing original GC chain texture pair. Restoring that existing source texture for diagnosis gives TEX0/CAST-GC drawn0/LEON-GC0; it does not approve PS2 chain material or auxiliary drawing ownership. Pair b5e4651f-7ad40bce is16528B, SHA256 776f475f9fa9e61ab53c54ccd3a62414b68571dcd23b924753a378372a6fd459, original GC TPL14 images0/1 at archive bodyentry16 offset1792928. Castle received the exact bytes and independently observed TEX0. Props43 NOT-DRAWN and two AICA failures remain FAIL.

Observed heap4 minimum/free-largest737888/737120B. Later VRAM1306432pinned/672320dynamic/498560free/472064largest,0evictions/retries. Late loads/motion reads remain; full residency is not accepted.

Complete HWM window410:429 has20counted ticks and four complete traces410/415/420/425. Actual run54.1746258s. Exact relocated runtime em2b/st2_3 overlay bytes and byte-bound pre-strip symbols qualify70.198ms MODELLED per sampled physical iteration, whole frame. The legacy stripped-only input projects70.199ms. Samples carry10.874M instructions versus10.842M average across20counts(+0.3%). Low/high are model assumptions, not console measurements. Original UTF16 log is retained and exact decoded UTF8 copy recorded; normal-vs-HWM LT/LU is STRICT on all20ticks, no gaps or masking. This is one full source diagnostic, not model-level A/B or complete fight acceptance. Earlier430:449 capture has only3/4traces and counts through442; it is excluded.

I006 attribution replays identical ordered traces with uninstrumented and instrumented current hwsim on the exact augmented ELF. Timing outputs match byte-for-byte; charge conservation passes. Eight cEm2b::move roots are observed, five complete/noninvalid. Their covered cost is2.68456625ms per sampled iteration, with raw incomplete-inclusive owner cost3.28339875ms. These are partial cohort coverage, not an extrapolated boss total. Boss drawing remains unpriced: shared character draw cannot isolate the twins from Leon/auxiliary objects, and aggregate cost is not divided by two.

## Private evidence and next boundary

Private set /root/re4data/private/boss18-twins-20261018 is immediately mirrored at C:/Game Dev/Emulators/re4-assets-private/boss18-twins-20261018:485files/51735066B, SHA256SUMS bb7a71a2ef08a89d175f89af41a1802d48633d38b82bb6f7c4b7d3f9e7088859. TWINS_PROGRESS.json, FULL_SOURCE_PROOF.json and SUPPORT_FULL_PROOF.json describe scope and selected/unselected source. Public source contains no game bytes or media.

Evidence root C:/Flycast-Evidence/re4-dreamcast/boss18-20261018: h-b18twins/scenarios/cx-r224-twins-pair-b, hwmodel-b18-r224-full-b/qualified-window-and-attribution.json, attribution-v1/{validation,summary,runtime-symbols.proof}.json. Copy/retarget every program file before fixture reuse. No reduced look, full grab/death/cart/lava/parasite, source chain admission, wholefight, route, residency or console acceptance is claimed.

Priority now returns to chapter3-1 r201 Garrador core ownership and Leon grab/death source handoff. I006 forbids boss18 engine implementation. Later boss identification is deferred; Island stays paused.

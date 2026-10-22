# Room 207 radio needs room for both source archives

The native chapter 3-1 route reaches r207 through the original r202 crank,
cannon, gate and door. Both swords can be picked up and the Platinum Sword used
on the upper mount with normal controls. The timed source event reaches four
live Ganados and holds D4/D5; the room clear is not yet accepted. A later combat
failure/normal Continue resets this attempt to the original r207 autosave.

The opening radio leaves Ashley id03 (141 parts, seven infos) with registry
roles refusals. The full partner package loads successfully. Read-only exact-ELF
snapshot audits show all seven source infos certified in r202, but no matching
asset or info records after the r207 radio. The original log reports one
certificate archive parked (22 assets, 28 infos) and one revoked.

The production park has 24 asset records with ACTOR_GANADO_PS2_STUMP. A complete
em11 archive adopts 22 assets, and full pl11 adopts 10. The capacity check can
therefore revoke the latter before the radio's memory swap. Matched guest gates
now reproduce that refusal and restore both archives with capacity 32.

SS_CERT_PARTNER_CAPACITY=1 selects 32 parked asset records, default 0.
It changes bounded metadata capacity only. Archive count, info count, ownership,
pending conversion, saved-byte coverage, row generation, byte hashes and
current-asset validation are unchanged. CH4 selects it after matched guest
qualification; T15 is untouched. No renderer, geometry, source role or fallback
admission condition is relaxed.

The host test uses the actual actor_lifetime.inc and actor_swap_park.inc.
Two source archives are adopted through the production entry point with 22 and
10 distinct BIN entries. The old capacity reproduces the revoked partner; the
new capacity restores both. Changed restored bytes, an unsaved byte and 23+10
assets still refuse the partner. ASan/UBSan pass all six variants (4, 71, 73, 75,
99 and 100 checks). The old test prelude also now explicitly disables the
recently introduced headless appearance macros, so it builds against current
source.

The matched fresh source-radio diagnostic uses explicit room/entry placement
and the original ScenarioRoomInit Ashley-present precondition (Status3 bit
0x04000000). It is not a natural-door or whole-chapter traversal claim.
Control c18oemW/0efeb8dc parks one archive/22 assets, revokes Ashley, and returns
with native 0 / registry-declined 150. Candidate c18ogmW/5b3c17ae parks and
restores two archives/32 assets. Ashley's full 141-part/seven-info model reaches
300 cumulative native draws, registry-declined 0. The standard CAST-GC and
NOT-DRAWN gates pass for the candidate; the control correctly fails Ashley.
The two fixtures have identical non-program payload inputs. All four captures
are 52.92-53.08 seconds through trace_lock, with exact-disc production snapshots
only between windows, never retargeted across builds.

The full current Test 18 combination c18oimW/746a2a5f also restores both archives
and draws Ashley natively with zero declines. FX_MIST_PS2=1,
HAZE_SPRITE_CUT=1, PS2_HDR_SETS=128, LEON_SKIN_SLOTS=2 and AUX_OBJ_NATIVE=0
are resolved. Actual 48 KiB squeeze minima are 37,264 bytes in this r207 window
and 5,384 bytes in busy r101 (55.88 seconds). Standard CAST/NOT-DRAWN/TEX/VRAM
checks pass, with zero late play uploads, evictions, retries or refusals in the
observed windows. Current literal T15 control c18ojrP is byte-identical to the
frozen release control for 1ST_READ.BIN and all ten overlays (11/11).

Private C evidence root: castle18-20261018. Exact ledgers are
r207-sscert-partner-capacity-matched-proof-20261019.json,
r207-I009-full-current-recipe-proof-20261019.json,
ch31-sscert-partner-I009-builds/proof.json and
ch31-I009-r101q-current7ed-official-vram.json. First missing-Ashley coverage and
private harness-name staging refusals are retained as invalid attempts, never
runtime failures or passes. The evidence root is 15.75 GiB allocated after
retiring the completed invalid diagnostic disc; logs and states are retained.

Pending: active four-enemy/inventory readoption, the remaining current-recipe
chapter 3-1 room gates, original route completion and chapter-end save/cold load.
Full chapter route remains open.

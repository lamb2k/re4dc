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
must still establish that all other save/restore preconditions pass.

SS_CERT_PARTNER_CAPACITY=1 selects 32 parked asset records, default 0.
It changes bounded metadata capacity only. Archive count, info count, ownership,
pending conversion, saved-byte coverage, row generation, byte hashes and
current-asset validation are unchanged. CH4 does not select it before guest
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

Pending: matched current-source r207 entry/radio/return/inventory gate, active
four-enemy partner readoption, actual 48 KiB KOS headroom, and literal current
T15 boot plus ten-overlay off identity. Full chapter route remains open.
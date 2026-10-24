from pathlib import Path
base=Path(r'C:\Game Dev\Emulators')
p=base/'CONSOLE-DISCS-TEST23.md'
s=p.read_text(); anchor='## Private WorldEmit comparison accepted for console feedback'
assert anchor not in s
s+='''

## Private WorldEmit comparison accepted for console feedback (2026-10-23, no SD copy)

RE4DC-QA23-WorldEmit-Off-49ad20f9 and RE4DC-QA23-WorldEmit-Both-49ad20f9 are root-reviewed private comparison discs. Source 49ad20f9932d638ddb7becf5db6f86b92e0a76a2. Off uses the current recipe; Both enables SELECT_LEAN2 and EMIT_PREFETCH. Both switches remain off in production.

Follow STEPS.md: compare R101 cross and close house-wall views at identical settings, three Diagnostics readings each. Photograph the disc label, world/phase/FPS rows and the matching camera. Hardware improvement is not established; earlier MODELLED combined differences were negligible or slower.

Independent readback verifies all 1,747 files per arm, main/all 14 overlays and the exact two-switch profile difference. Actual final-GDI boots and separately labelled proxy menu-warp/H2 checks pass. Normal QA H2 is 340/340/restored, Off 40,576 / Both 44,448 bytes. These do not replace production-profile KOS/memory gates. No QA Mendez or full-route test was run.

Both arms preserve all original assets and share one private PS2 load/upload repair file. Visible use and appearance remain unproven; production appearance is unapproved. No GameCube fallback was added. Track03: Off 4930522dfb2dcdd68219d159c4f54d30eaf13d28c7f54cd5108447303830f987; Both eb2c05fbe7ed104d91d8ed51048a5a0c7a0fd03b396ddb94eefa03472537647b. ROOT-ACCEPTANCE.json and refreshed IDENTITY/SHA256SUMS accompany each disc; earlier worker metadata is preserved in private root-delivery evidence. No publication, ZIP or SD copy.
'''
p.write_text(s)
p=base/'codex-lanes/CODEX-TAKEOVER-STATUS.md';s=p.read_text()
s=s.replace('Review the completed world console pair, finish dedup QA and prepare its default-off integration.', 'The world console pair is reviewed and indexed. Finish dedup QA and prepare its default-off integration.')
s=s.replace('Accept and index the world pair after independent review; finish dedup QA and merge its current unit, then start queued re-strip I-001 in this session.', 'Finish dedup QA and merge its current unit with the confirmed prefetch composition fix, then start queued re-strip I-001 in this session.')
s=s.replace('pending root independent review and registry entry', 'accepted by root after independent all-file/media/probe review and indexed for private console feedback')
s=s.replace('Frozen source 683be321 adds fail-closed', 'Frozen source bf276b34 adds fail-closed')
s=s.replace('Combined host controls and independent review are in progress.', 'Combined host controls pass; independent review found a lost Weapon failure mask, now corrected in bf276b34 and awaiting successor review.')
s=s.replace('Re-strip I-001 remains queued until this unit lands.', 'A separate review confirmed missing decoder setup in the optional prefetch combination; its narrow source fix is in progress. The qualified pair uses prefetch off. Re-strip I-001 remains queued until this unit lands.')
s=s.replace('- RE4DC-QA23-StatBytes-2a14662d: own boot, warp, H2 and disc-seed checks pass.', '- RE4DC-QA23-StatBytes-2a14662d: own boot, warp, H2 and disc-seed checks pass.\n- RE4DC-QA23-WorldEmit-Off/Both-49ad20f9: root-reviewed private pair; all-file/programme identity and six bounded probes pass. Console speed, full route, QA Mendez and physical acceptance remain pending.')
p.write_text(s)
p=base/'codex-lanes/world-emit23/STATUS.md';s=p.read_text();s=s.replace('Main and an independent reviewer are checking final media, programme identities and probe receipts before marking the private pair ready for console feedback.', 'The private Off/Both pair is accepted for console feedback after root and independent media, programme and probe review; it is indexed in CONSOLE-DISCS-TEST23.md.')
s=s.replace('The private console pair is sealed, pending root review;', 'The private console pair is root-reviewed for console feedback;')
p.write_text(s)
print('World private pair accepted and indexed; takeover status current.')
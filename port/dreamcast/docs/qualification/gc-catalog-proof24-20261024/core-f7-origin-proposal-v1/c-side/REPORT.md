# One exact PS2-origin attestation proposal

Smallest mechanically demonstrated subset: **one texture**, kind texture, id 47a9bc5b-b0495b0f, full immutable RE4TEX SHA256 91ad12accc6fd1ad52b1f6289ef2ffebc1cbc31b91a964e6295498419e301900, 208 bytes. It is the PS2 Core.dat EFF1 picture f7. This is an unapproved origin proposal for root review, not an automatically promoted catalog row. The existing 7,304-row all-Unknown index remains byte-identical and the production pin remains 0.

## Original source to exact selected output

1. Read the existing original PS2 USA disc image at C:/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso. Bounded ISO9660 checks bind SYSTEM.CNF to SLUS_211.34 and verify the boot executable is little-endian MIPS ELF. The AFS table hash is a7b0c37119f9ccabf8711ead7d83189065fe1d5df8c427cffe32022403ce3182, matching existing PS2 extraction provenance. Full ISO/retail authenticity is not independently established by those checks; root must accept the existing original-disc source authority. No full ISO scan was performed.
2. Core.dat is actual BIO4DAT.AFS member 368, offset 1,260,908,544, size 1,524,064. Its full SHA is c48e2165a41cb20b124a11a96e9b00bcdcd051f435475004edcc23a47e920e33. Actual disc bytes equal the existing immutable private Core.dat cache. EFF entry 1 starts 14,400 bytes into that member, absolute ISO offset 1,260,922,944, size 861,056, full SHA e0a571bec16baa427c4267feb59ea6ec9aa64703b833d7ed42598115c62b0124. Its full bytes also equal the existing extracted EFF cache.
3. Select actual texture id f7, table slot 53, one 8x8 linear PSMT4 picture. The exact source TPL span is EFF offset 682,464, 224 bytes, SHA 65bdb3dcdec9ace0ad999a6fd26346f308f97efb18ed785e910dcca780556280. CHECKS.json records descriptor/index/CLUT offsets and full hashes. Its 64 decoded pixels have one color; no source pixels were inferred from the target or name.
4. Existing ps2lib INDEX.tsv binds common/etc/core.das:0#1:0xf7 to Core.dat:1 through fx_ps2_pack.py@5182665f. The historical aggregate SHA is 7f7cb6a3ace45ffc051b0dcfbf071b054ac6be9ff9e7264e9543606489ad32f5, which independently equals SHA256(lookup-key ASCII concatenated with the entire 208-byte library payload). The KEYS row binds the exact lookup key/frame 0. Historical PASS labels are fx12-b-cand, fx12-h-cand and fx12b-candm-a; their original capture directories were not rebound or replayed here. Those labels alone are not the proposed origin proof.
5. Under root's explicit single 8x8/208-byte RAM-only grant, retrieve exact historical public converter commit 5182665f6d6b62aee348e58266c015c891da5d85. The complete fx_ps2_pack.py SHA is 41d9cafee8e82bd254bad6c02e202b0f398892b7a9ba894fd7fc3aa71c9ce3d5; convert_tpl.py SHA e306b31fb8a46d2fc993c75be22ee0064454fd0d91d32135b5c5bb08b4d232c2. Execute unmodified historical package/palette/premultiply/4444/twiddle functions extracted from those files. The selected picture is decoded by a bounded read-only checker following the historical linear PSMT4/CLUT path; the entire old batch converter is not run. Exact function hashes and invocation scope are recorded. The resulting 208 bytes exist only in RAM, have zero conversion error, and equal the complete library file and actual selected pack member byte for byte.
6. Rehash the actual selected current tex.pak: size 162,154,496, SHA 5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da. Read its selected member at offset46,774,272, 208 bytes; its full payload is identical to that exact historical replay. This matches current manifest and selection SHA 5f917f3521be886568e3880f63404def99a9cfaa1c0810321713f216c98d4484. No target-only or pixel-body-only hash substitutes for the full member.

Four RAM negatives pass: one changed source pixel changes the reproduced full output; changed output header changes its full SHA; wrong lookup key fails the historical aggregate; wrong source picture dimensions are rejected. These are real data-bound checks, not a claim that a converter filename or successful parser proves PS2.

## Explicit proposal and authority boundary

attestation-proposal.json has exactly one row with provenance ps2 but **reviewed=false** and root-review-pending owner/reason. Its chain pins CHECKS.json and both exact historical public source files. The actual catalog tooling rejects it with “origin is not independently reviewed”; PROPOSAL-PREFLIGHT.json records that intended refusal and unchanged old index SHA. Root may make a separate approved attestation after independently reviewing source authority, selected source spans and the replay. This report neither edits that authority nor changes allowances or indexes.

Remaining manual authority: the provided private disc image is the trusted source boundary; full retail/untampered-dump certification was not performed. Historical gate labels are recorded metadata rather than fresh scene/look acceptance. The mechanical reconstruction proves this exact output is produced from the identified PS2 source picture under the pinned historical algorithm. It does not prove every output of that converter, room or pack is PS2, and proves no accepted draw/play use.

## Other existing receipts: useful pointers, insufficient automatic attestations

- ASSET-SOURCE-LEDGER-20261014.md is historical Test11 source/status and Flycast evidence, not a current origin certificate. It explicitly includes GC-light-baked P* worlds and then-GC movies. It cannot bless current whole assets or supersede the newer selected manifest.
- ps2lib INDEX.tsv/KEYS.tsv/NOTES.tsv provide exact converter/member/key links and historical gate references. Source filenames, PS2 directory names and PASS text alone are insufficient. Only the single f7 row above was closed here through actual original-disc spans and byte-identical reconstruction.
- mip22b/pak-derived.json links predecessor/output pack hashes and one held texture key; it proves a pack transformation link, not origin of all 7,299 members. No blanket pack provenance is proposed.
- Current r100 mesh/ids match older PS2 world receipts, but current R4PW is the mip22b derivative, not the older world16 R4PW. Geometry material/constituent ancestry and exact consumed identity remain separate owner work. No Model/Motion/geometry positive row is proposed here.
- Four loose overrides and the audio stream are exact current identities in the new private index but still lack an accepted source-origin chain. They remain Unknown. Neither local conversion nor old class labels upgrade them.

## Selected r100 paths supplied to water owner

Actual current full hashes match the selected 1,697-asset manifest:

- mesh: /root/re4payload/t164-20261018/tree/dc/native/r100/ps2-world.re4mesh; 1,537,920 bytes; SHA 130bac7969255f0bf31d5f9226cee21a33415103f044f0fdc7dda3607ffc89bb.
- R4PW: /root/re4data/private/mip22b-20261022/dc/native/r100/ps2-world.r4pw; 19,612 bytes; SHA 07acc55b2b009abd8368af2880c556272cf6de41595908739afc589baceab6cd.
- IDs: /root/re4payload/t164-20261018/tree/dc/native/r100/ps2-world.ids; 320 bytes; SHA c4394a5fb19f0a89bcef4f42134d4cfa7dff7619a8368c9a7a967fdca7011cb3.

The older world16 R4PW be83... is a predecessor, not the currently selected 07acc... derivative. The water owner received these exact paths/hashes. No GameCube-object-to-PS2-placement correspondence is inferred.

Execution took 0.372 seconds wall time (inner checks 0.250 seconds), peak child RSS 41,576 KiB under 256 MiB/120 seconds. Only the explicitly selected source spans/current pack were read. No SDK, guests, staging, broad regeneration, asset-file output, current catalog mutation or production pin change occurred. Public source snapshots and hash-only metadata may be preserved in Git; original pixel/index/CLUT/asset bytes never leave RAM.

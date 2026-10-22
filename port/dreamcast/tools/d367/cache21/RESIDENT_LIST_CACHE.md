## Core metadata discovery repair, October 21

The enabled cache now discovers core keys and whether this room has an own list independently of texture admission slots. Earlier owner passes can fill all slots, or leading core rows can fill them before later own-room rows. Previously both cold scanning and warm replay then skipped those metadata rows and CORE_PIN=2 incorrectly disabled core pinning. The existing differential tests preserved this shared baseline defect.

The existing default-off RESIDENT_LIST_CACHE guard contains this repair. Disabled behavior is unchanged. The original validation order, sixteen-key deduplication/capacity, own-row predicate, file order and successful-prefix behavior remain. Admission counts, texture picks and byte/slot budgets are unchanged. A failed read before the first own row still cannot establish complete ownership; no complete-list claim is made for a partial scan. Cache overflow still disables replay and retries the full scan.

The main rerun passes 141 admission comparisons plus 98 independent semantic assertions under UBSan, including all-full/leading-core/actual owner-selection, warm cache, cross-block rows, sixteen-key cap, invalid own rows, late failures, partial tails and overflow. Checked-in six-core/219-r101 metadata is a host fixture, not proof of saturation on a staged disc. The canonical admission suite separately retains ASan+UBSan. Run the independent suite with core_pin_discovery/run.py --source TREE --ref 8b0340cf7dd0916c6094d2c3db4fecd91a4408a7 --working-ui TREE/port/dreamcast/game/platform/native_ui.cpp --expect-fixed --out FRESH_DIR.

Whole SH4 native_ui OFF objects match exactly. Correctly enabled versus prior enabled adds 20 text bytes, no data/BSS change. Attempt01 is preserved/disqualified because the retained pipeline header overrode the command-line guard to zero; attempt02 uses a final single-guard header and verifies resolved macros. No full linked successor, Flycast occurrence, performance, release or physical acceptance follows from these tests.

---

# Reuse the current room resident-list metadata

`RESIDENT_LIST_CACHE=1` requires `ROOM_RESIDENT=1` and defaults to zero. This caches copied list metadata, not texture payloads. New weapon/enemy identity admission, missing texture loads, VRAM limits, core pin decisions, and existing eviction policy still run on every preload pass.

## Trigger and change

The frozen QA weapon control repeatedly bound warmed weapons with no new textures. Every bind scheduled `preload_identities`, whose resident-list step opened and read the entire immutable `dc/resident.bin` in 512-byte pieces. One late handgun return logged a 722,193 us whole-room preload with zero textures loaded. That is a Flycast observation of the existing path, not a measured saving from this patch; the weapon task itself logged 89,101 us separately.

The enabled path copies matching room rows and core rows in original order after a complete scan. Later passes in the same room replay those rows through the original validation/admission body, with zero resident-list reads. It does not skip owner identity tables or required texture acquisition. Room changes replace the single-room list. Menu/movie texture releases can refill from the copied keys without retaining pointers into released archives.

The bound is 256 records (4,108 B total fixed BSS; no heap allocation or new payload reserve). The selected-list census had at most 224 room rows plus six core rows; the proposed 14-core-row successor also fits. These data-specific counts are capacity observations, not a new format limit. If matching rows exceed the bound, replay stays disabled and the original full-scan path continues.

Exact EOF and stable size certify a cache entry. Missing files, failed reads, read-layer allocation failures, trailing partial pieces, and size changes never produce a reusable partial list; the next pass retries. Existing partial admission before failure is preserved. Invalid/duplicate matching rows retain their original side effects and admission validation. The contract is an immutable mounted disc list: any future runtime replacement of that file or same-room disc data must add explicit cache invalidation.

## Validation

`python3 port/dreamcast/tools/d367/cache21/test_resident_list_cache.py --out <directory>` extracts the actual baseline and candidate `preload_select`/`preload_resident` functions and compares their results with a synthetic file/identity backend. ASan+UBSan pass 47 checks for each CORE_PIN 0, 1 and 2 (141 total): cold/warm, new owner, room change/return, menu/movie refill, admission limits, absent/retry, I/O/size/truncation faults, read-layer OOM, invalid/duplicate rows, exact bound/overflow, empty file/selection, and room zero. This is parser/admission control-flow coverage, not a complete renderer or physical I/O test.

The SH4 translation unit was compiled with the retained QA native_ui command flags against base `c7e0358a44677a15123a7f4233c4115eba627694`, using the same stdin virtual source for baseline/off/on. Baseline and disabled preprocessing and whole object are byte-identical. Enabled compilation passes: text +588 B, data unchanged, BSS +4,108 B. `resident-list-validation.json` seals hashes, source identity, sizes and host results.

Full-program disabled identity, enabled target repeated-switch/new-owner checks, movie/menu return, and physical Dreamcast timing remain pending with the integrating lane. The frozen motion candidate, its disc, and saved states are unchanged.

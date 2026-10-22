# texsrc22 resume: source qualification and candidate tooling

Date: 2026-10-22. Base: [`00ec40a4679e817593cc53bfe0ef704f7ae2b2ba`](https://github.com/lamb2k/re4dc/commit/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba), the inspected `wip/texsrc22` head.

## Status

The source review, classifier fixes and portable candidate converter are ready for integration. **No private texture pack was available, so no game mipmaps were built and no new texture data is included.** The existing 1,035-row classification and summary remain the frozen first pass. The new review ledger is an annotation of that evidence, not a rerun against the latest pack.

`TEXSRC22-PARKED.md` was absent from the complete tree at the inspected commit. This note records the continuation from the checked-in scripts/table and the coordinator's handoff; it does not reconstruct the missing note.

The main open question has a useful source-level answer: **the shared GameCube archive textures cannot be excluded merely because the PS2 Chapter 1 cast is selected.** The cohort has broader consumers, explicit room references and supported fallback paths. Exact route activation remains unresolved for part of it.

## Reconciliation of the published numbers

| Frozen first-pass decision | Keys |
|---|---:|
| mip-chain | 70 |
| convert-blocked | 57 |
| not-reachable | 898 |
| exclude | 8 |
| already-mipped | 2 |
| Total | 1,035 |

These are reproduced from [texsrc22.tsv](port/dreamcast/tools/d367/texsrc22/texsrc22.tsv), not freshly qualified counts. In particular:

- **844 is the entire world category:** 823 were labelled not-reachable, 14 conversion-blocked and seven mip-chain. All seven candidate package labels describe PS2 room objects.
- **The eight exclusions are six HUD textures and two tiny textures**, not eight HUD textures.
- All 70 candidates were either unseen in the older runtime sample (66) or previously labelled not-worth (four). Their format/source eligibility does not establish useful minification or a speed gain.
- The table records 117 conflicts with the earlier not-on-route label. A static route reference can correct incomplete runtime sampling; it does not establish that every such texture is currently drawn.
- The original writer limited source lists to eight entries. **22 of the 70 candidate rows reach that limit.** The table therefore cannot prove that a key has no additional shared or cutscene consumer.

There are also two explicit false-unreachable cases. Their package names did not identify a semantic class, and that unknown-class branch overrode positive resident evidence:

| Key | Positive evidence | Required treatment |
|---|---|---|
| `279052e0-b695f91f` | `resident:r207`; prior needs-work observation | Bound consumer with unresolved role; retain original |
| `dc363980-b5147ee2` | `resident:r100`; prior not-worth observation | Bound consumer with unresolved role; retain original |

Thus 898 must not be used as a disc-pruning list. This review does not claim the other 896 are proven unreachable either.

## Shared Ganado result

The visible `em/em10.drs` cohort contains **41 keys: 24 first-pass mip candidates and 17 blocked keys**. Every one of the 24 candidates has other Ganado archive origins in the visible source list.

| Evidence | Mip candidates | Blocked | Total |
|---|---:|---:|---:|
| Explicit r201 resident reference | 1 | 1 | 2 |
| Consumer activation unresolved | 23 | 16 | 39 |
| Total | 24 | 17 | 41 |

The two positive references are `70aead5f-07fae149` (256×256) and `dfb309b8-6dbeb0de` (256×128). They occur in the [r201 resident list at the source pin](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/port/dreamcast/tools/d367/vram/resident/r201.tsv). Residency is load evidence, not a draw or minification measurement. Keep both originals; the square key can remain a static candidate for the later quality and memory checks.

The archive entries are broader than the five Chapter 1 body atlases. Visible provenance subentries include castle zealot and island soldier body/head/hand tables, separate accessories and a core object. For example:

- Castle type 9 selects archive entry `0x21E` / decimal 542; types 10 and 13 use 546 and 548. See [em1c_set.cpp](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/src/em1c/em1c_set.cpp#L114).
- Island tables use several of the remaining entries, including 570–588. See [em1d_set.cpp](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/src/em1d/em1d_set.cpp#L66).
- Actor types 10 and 13 create a separate `cObj16` core with TPL `0x228` / decimal 552. Eight cohort keys have that visible origin, five of them mip candidates. Replacing the host body does not automatically replace this object. See [em10.cpp](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/src/em10/em10.cpp#L3089).

Those subentry matches are source associations; final staged archive identity and material-image selection still need the complete provenance map. They do not establish that each key activates on the selected route.

The PS2 owner also retains deliberate GC fallback when binding, LOD or required package validation fails. The render caller clears the original model-info list only when ownership succeeds. Some successful ownership paths can retain original grip-hand and attachment materials; the recorded keys for those particular materials do not overlap this 41-key cohort. They explain why blanket exclusion is invalid, without proving these 41 keys draw. See [owner admission/fallback](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/port/dreamcast/game/coarse_actor_owner_ganado.inc#L1201) and [render caller](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/src/game/trans.cpp#L2964).

**Disposition:** retain all 41 originals, hold speculative expansion for the 39 unresolved consumers, and authorize no pruning. Resolve the actual build knobs, qualified PS2 runtime headers, staged overlay/registry manifests, shared archives, cutscenes and preload aliases before treating an original consumer as removed. `COARSE_GANADO_CAST=1` alone does not establish PS2 asset selection; see [the PS2 build inputs](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/port/dreamcast/game/game30.mk#L1176).

## Review ledger for the 70 candidates

[resume-review.tsv](port/dreamcast/tools/d367/texsrc22/resume-review.tsv) lists every candidate and its next check. [resume-review.json](port/dreamcast/tools/d367/texsrc22/resume-review.json) pins the source-table hash, records all 41 shared Ganado keys, preserves the two false-unreachable cases and records the current integration policy. Neither file is an approval manifest.

| Review group | Keys | Next evidence |
|---|---:|---|
| Shared GC Ganado archives | 24 | Exact active consumers and fallback reachability; one has r201 residency |
| Cutscenes | 12 | Staged cutscene use and camera minification |
| PS2 items | 10 | World/inventory sharing, near detail and inventory memory |
| PS2 room objects | 7 | Material binding in staged rooms and useful minification |
| PS2 masks | 6 | Selected consumers, coverage and thin-feature quality |
| Alternate Leon variants | 4 | Whether the exact build selects each variant |
| Core effects | 3 | Effect activation and every-level colour/alpha quality |
| Standard actor packages | 3 | Selected Leon, Luis and PS2 Ganado atlases; mid/far appearance |
| Shared breakable | 1 | All shared uses, coverage and tight-room residency |
| Total | 70 | Source/format candidates, not approved additions |

The four alternate Leon keys correspond to AO, SKY, GCB and GVQ variants; the header explicitly identifies variant 0 as the play build. A `leon4k` name does not select a variant. See [charbake_variants.h](https://github.com/lamb2k/re4dc/blob/00ec40a4679e817593cc53bfe0ef704f7ae2b2ba/port/dreamcast/game/charbake_variants.h).

For the next batch, start by checking the seven resident-referenced PS2 room objects against the actual current pack and stage. They are a bounded scene-content group with positive references; that makes them practical to qualify, not a measured claim that they deliver the largest gain. Items, masks and actors have separate near-detail/shared-use concerns. Promote candidates according to useful minification and room memory, not the size of a category. The first-pass 70 may overlap chains or quality holds already handled by other lanes, so join against the exact current pack before counting new work.

## Tooling changes

### Classifier

[classify.py](port/dreamcast/tools/d367/texsrc22/classify.py) retains its existing CLI and original columns, then appends `classes`, `binding_rooms`, `consumer_status`, `minification` and `source_count`.

It preserves all supplied provenance instead of truncating sources or choosing only the first class. Any HUD alias protects the shared package. Structured R4PW material references are separated from arbitrary native byte matches, and text/global archive hints no longer establish a route consumer. Positive resident evidence survives an unknown semantic class; earlier positive drawing evidence is also retained as a conflict needing resolution. Pack/index validation and required-input checks stop malformed or absent inputs from looking like empty evidence. Future mip-chain rows explicitly mean format-eligible static candidates with unmeasured minification.

The frozen `texsrc22.tsv` and `texsrc22-summary.json` are intentionally unchanged. A complete new classification requires the exact private pack, complete provenance JSON, staged native data and scoped origins, resident lists and prior runtime table.

### Converter

[convert.py](port/dreamcast/tools/d367/texsrc22/convert.py) reuses the repository's VQ, native16 twiddled and PAL4 generators. It removes the old continuation's dependency on a hard-coded private `miprecover22` checkout. The parked base does not include the current quality gate, room policy or the recovery encoder, so these are not assumed to exist.

- Default OFF copies the entire input pack byte for byte.
- ON requires a reviewed key list bound to the exact pack, quality-gate and room-policy SHA256 values.
- All selected keys must exist and be supported single-image packages. Unsupported rectangles fail before any output is written.
- Every changed package retains its base image bytes, decoded full-resolution pixels and material identity. Changed passing packages receive canonical CRCs.
- Every selectable mip level through 1×1 must be present in the gate audit. Quality failures, room holds and existing mip chains retain their exact original package bytes.
- Unselected members remain byte-identical; the rebuilt pack and member map are verified. An all-held/no-change result retains even the original pack padding.
- Reports include changed keys, source/output hashes, payload and rounded allocation-request deltas, policy hashes and the actual imported encoder/gate-helper source hashes.
- `--dry-run` performs encoding and checks but emits only the report. Output paths must be new; in-place pack replacement is rejected.

The allocation delta is an accounting input, not a room-peak or fragmentation measurement. The converter creates a private candidate; it does not change recipes or install a release pack.

## Current mipmap integration pin

The current checked `wip/mipmap22` commit is [`e8c5dadfd3e5d42b630d7e316e25a10b26828dec`](https://github.com/lamb2k/re4dc/commit/e8c5dadfd3e5d42b630d7e316e25a10b26828dec). Its Round 4 [room-select.tsv](https://github.com/lamb2k/re4dc/blob/e8c5dadfd3e5d42b630d7e316e25a10b26828dec/port/dreamcast/tools/d367/mipmap22/room-select.tsv) restores the previous holds under `VRAM_ROOM_ARENA`; the inspected file has zero hold rows. No historical 121-key hold list is baked into this continuation. An explicit empty policy file is supported and still hash-bound.

The inspected current [mip_quality.py](https://github.com/lamb2k/re4dc/blob/e8c5dadfd3e5d42b630d7e316e25a10b26828dec/port/dreamcast/tools/d367/mipmap21/mip_quality.py) SHA256 is:

```text
5eeba3db83758935d4302d7bbd7d2942edc4e61ef90a1bc58884e9e7e481c7fd
```

Fetch and review the actual integration revision used for the next pack; a moving branch name alone is not a qualification receipt.

## Validation and private-environment continuation

Focused host validation: **29 passed, zero skipped or failed: 18 classifier tests and 11 converter tests**, using generated in-memory fixtures and the current full-level external quality gate. The [validation receipt](port/dreamcast/tools/d367/texsrc22/resume-validation.json) records the gate pin and scope. The tests exercise the two false-unreachable regressions, shared HUD precedence, structured material references versus incidental byte matches, scoped aliases, missing inputs, the retained classification CLI, all supported conversion formats, exact base/unselected/OFF preservation, checksum handling, room and quality holds, existing-chain identity and output protection. No private pack, Flycast scene, console timing or VRAM re-entry claim is made by these host tests.

From this source tree, with the reviewed integration tree available separately:

```bash
TEXSRC22_TEST_QUALITY_GATE=/reviewed/mipmap22/port/dreamcast/tools/d367/mipmap21/mip_quality.py \
  python -m unittest discover \
  -s port/dreamcast/tools/d367/texsrc22 -p 'test_*.py' -v
```

Without that external gate, the real-gate converter cases are explicitly skipped; a successful test command with skips is not equivalent to the recorded qualification run.

In the private asset environment:

1. Pin the current pack and resolved build/stage manifests. Regenerate classification with full source provenance and actual resident/material bindings. The original classifier arguments remain available via `classify.py --help`.
2. Resolve candidate consumers and current-pack overlaps. Use the ledger as a review queue; do not feed all 70 directly into conversion.
3. Create the reviewed selection JSON below with real SHA256 values and only admitted keys. This source change deliberately supplies no fabricated pack hash or pre-approved selection.
4. Run the converter dry-run, inspect per-key quality and allocation results, then use a new output path to create the candidate.
5. Run room entry/re-entry and inventory checks with the exact candidate: no allocation failures or extra evictions, preserve near detail, and assess mid/far actors and thin alpha features. Console A/B timing remains the performance acceptance check.

Selection schema (placeholders must be replaced):

```json
{
  "schema": "re4dc-texsrc22-selection-1",
  "base_pack_sha256": "<exact private pack SHA256>",
  "quality_gate_sha256": "<reviewed quality script SHA256>",
  "hold_keys_sha256": "<current explicit room-policy SHA256>",
  "approved_keys": ["<reviewed crc-fnv key>"]
}
```

Dry-run command:

```bash
python port/dreamcast/tools/d367/texsrc22/convert.py \
  --pack /private/test22/tex.pak \
  --selection /private/test22/reviewed-selection.json \
  --quality-gate /reviewed/mipmap22/port/dreamcast/tools/d367/mipmap21/mip_quality.py \
  --hold-keys /reviewed/mipmap22/port/dreamcast/tools/d367/mipmap22/room-select.tsv \
  --enable --dry-run \
  --report /private/test22/new-run/qualification.json
```

After reviewing it, use a fresh report path, omit `--dry-run` and add `--out /private/test22/new-run/candidate.pak` to emit the candidate. Keep generated packs and game payloads private.

**Remaining prerequisite:** access to the exact current private pack and the matching full provenance/build/stage inputs. Source preparation is complete; the real asset run and runtime qualification remain pending those inputs.

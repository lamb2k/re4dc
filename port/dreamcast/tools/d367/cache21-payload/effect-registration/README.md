# Effect registration: bounded source audit (A11)

This audit establishes the response to a registration refusal. It does **not** establish that a normal room reaches such a refusal, and it does not justify a new runtime repair yet. No runtime files were changed. The existing default-off `EFFECT_ADMISSION_GUARD` remains unchanged.

The selected source is `a18f2cf60faa25266271b2c33a6c7c8b0f3e3c1f` in the main integration worktree. `src/game/eff_sys.cpp` is byte-identical to `e7bb2e5bf`, SHA256 `83c5ae8deb709982a37dfeb371038a8d5263f36b7fe180530ddda0857828465f`. `validation.json` binds the source, host fixture, exact asset census and original binary receipts. Private artifacts are under `C:/Flycast-Evidence/re4-dreamcast/cache21-payload-20261021`.

## Actual table and caller contracts

`EFF_OWNER_MAX` is `0xD3`: **211 rows**, not 220. The 220 literal in EspRoomInit is a diagnostic ceiling. The owner sentinel is `0xD2`; ordinary owners are 0 through `0xD1`. `estTbl`, `sstTbl` and `pathTbl` each select **their own row by owner**, rather than searching a shared free-slot pool. Occupying all other owners cannot exhaust an otherwise empty valid owner's row. Consistent repeated owner loads increment the owner count and skip registration. Synthetic same-owner table occupancy with a zero owner count is not evidence of a normal full-table defect.

Texture and effect-model IDs select separate 256-row tables. Texture animation frames consume a shared contiguous GXTexObj run from the 500-entry array; its allocator admits at most indices 0..498 with the existing predicate. The 63-byte bitmap covers the declared array. `EspPullTexObj` is called only by `espTexRegist` in the selected source. Array access, release and draw access use the reserved base plus frame index; no separate pool[499] sentinel consumer was found. `EspGetTexObj`/EspTexSet do not themselves bound-check the requested pattern. This audit does not prove a reason to change the allocator endpoint.

The original G4BE08 DOL settles source fidelity: EspPullTexObj at `0x800EB6F4` has `cmplwi r0,499` at `0x800EB740` and `bgt` refusal at `0x800EB744`. The exact-end refusal is **not a newly identified port defect**. Its intent is not inferred. Original EspDataLoad also ignores the five registration results and returns 1 after the loops (calls at `0x800EB978`, `0x800EB9A4`, `0x800EB9BC`, `0x800EB9D4`, `0x800EBA54`; final `li r3,1` at `0x800EBA64`). Private four-function bytes/disassembly retain their exact ISO offsets and hashes; no game bytes are committed here.

The pinned textual caller census contains **200 EspDataLoad invocations**: 195 literal owner arguments, all in 0..209, and five dynamic arguments. Of these, 199 ignore the result; Event::ExePacket_SetEff checks it. This is a source invocation census, not a runtime count or co-residency claim. The dynamic callers are:

- `emdata.cpp:105`: GetEmEffId validates supported enemy IDs and maps 0x11..0x20 to the same owner 0x10. Unsupported IDs return before load.
- `et00.cpp:59`: the 29 selected EtXX_init wrappers provide constant owners 0x54..0xB9. Successful SetWindow precedes load and the caller then installs effId without observing the load result.
- `event.cpp:1172`: the manager has two events, construction assigns the manager work index, and normal slots 0/1 select owners C4/C5. SetEff checks the return before publishing status bit 0x40000. Since EspDataLoad masks subordinate refusals, that outer check cannot detect a subordinate refusal if one occurs.
- Two `t_esp/db_port.cpp` tool callers use db_effOwner. Tool state validity is not certified here and is not used as a gameplay trigger.

Core uses owner0; subscreen ownerD1; room owner1; player archive owner3; common em10 initialization owner10. The em11..17 variants do **not** imply seven simultaneously distinct effect owners. The separate RoomEfmRegist overloads return void and ignore efmRegist, but no selected src caller was found by the exact symbol search.

## What actually allocates or can refuse

`espTexRegist` can refuse an occupied texture ID, frame/descriptor mismatch, or unavailable contiguous GXTexObj run. EspCalcTplAddr mutates in-file TPL descriptor/header/image/CLUT offsets **before** the run reservation; it performs no allocation. After reservation succeeds, the texture work stores borrowed header/animation/TPL pointers and writes GX descriptors. Native GXInitTexObj/GXInitTlutObj write fields and GXLoadTlut is a stub. **No native heap/VRAM allocation admission is performed here**; later draw/upload admission is a separate boundary.

`efmRegist` can refuse an occupied global model ID, but registration only stores model/TPL/motion/shape pointers. It does not allocate a model. EST/SST/path registration can refuse an invalid owner or an already occupied same-owner row. Their data/list pointers remain borrowed. Runtime ownership/worker/retirement safety is a separate A11 audit owned by main and the caller lane.

## Actual-source service controls

`test_registration_boundaries.py` extracts 15 complete function bodies and effect-file structures from the pinned git blob. The host executes actual owner counters, ID tables, allocator/bitmap, registration and release code against projected service structures with the actual array counts. Non-PIE static fixtures preserve the source's u32 address interface. TPL relocation/descriptor lookup and GX initialization are explicit stubs; the fixture is not a native Package/VRAM/complete-game test.

**46 checks pass with admission guard OFF and 46 ON under UBSan**. These cover successful registration, duplicate/refcount and force-release snapshots; occupied other-owner EST/SST/path rows; injected pool pressure and fragmentation; exact allocator endpoint; existing texture/model collisions; mismatched frame count; release/retry recovery; and preserved wrong-version guard behavior.

With 498 synthetic occupied slots, one one-frame texture is admitted, a following two-frame texture refuses, and EspDataLoad still returns1 with owner count and EST/SST/path/model registrations published. The failed texture remains ownerD2 with pTexObj NULL and nTexObj set. A normal duplicate load increments the count and returns1 without retrying that missing texture. Forced release, removing injected pressure and retry succeeds. Injected global ID collisions and frame mismatches show the same masked subordinate-failure mechanism. These are **conditional service-boundary observations**, not evidence that the injected pressure/collision state occurs in valid gameplay. The original binary has the same ignored-result contract.

## Exact original asset census and its limits

`census_effect_admissions.py` hashes every parsed input against the retained texture consumer policy before inspecting its active native payload. Policy SHA256 `1864af25107b50e4f0039d4798b5216d3aa2617cbdc810d03be5eb410b097d28`. The result covers **89 files, 107 EFF blocks**: 44 enemy, 32 st1, 28 ss and three etc blocks. No parse errors, ID above255, texture frame/TPL descriptor mismatches, or within-block duplicate texture/model IDs were found. Maximum single block demand is200 GXTexObjs; maximum single texture is75 frames.

`etc/core.das` word5, bound by source to owner0, requests56 texture IDs /200 objects; word20 for ownerD1 requests zero textures/models. Word29 requests117 objects but belongs to **IdTexDataLoad/HUD**, not the effect pool. The ss blocks also must not simply be added to this pool. The first EFF in each of25 audited room archives (24 at word11; r100 at word12), selected by the normal room caller GetDataExt(..., "EFF", 0), is individually at most178 objects. All25 have texture/model ID sets disjoint from core. The32 st1 total also includes seven additional tagged EFF blocks. em11..17 word4 blocks each request42 objects with the same ID set and common owner10.

Even a simple 200+178+42 =420 total only describes these three categories under assumed co-residency. It omits player, weapon, ETM and event allocations, registration order, prior release and contiguous-run fragmentation; it is **not a global safety proof or a reproduced overflow**. The policy was collected for texture consumer auditing, so it is not a complete live effect owner manifest. Summing all 107 EFF blocks would combine mutually exclusive rooms, duplicate shared owners and the other HUD pool.

Next required evidence before a repair: exact valid co-resident owner/asset identities and registration order that cause a real refusal (or a bounded native live counter/capture from an already authorized target run). Then assess caller propagation and ownership-safe cleanup against actual surviving effects. Neither an unconditional no-fail assumption nor whole-owner rollback is justified by this audit.

## Reproduce

Read-only metadata:

```sh
python3 audit_source.py --source /root/probe/codex-cache21-integration-next --ref a18f2cf60faa25266271b2c33a6c7c8b0f3e3c1f --out /path/to/fresh-source.json
python3 census_effect_admissions.py --policy /path/to/consumer-policy.json --tools /root/probe/codex-cache21-integration-next/port/dreamcast/tools --out /path/to/fresh-assets.json
```

Small host compilation (fresh output, current disk/resource guards required):

```sh
python3 test_registration_boundaries.py --source /root/probe/codex-cache21-integration-next --ref a18f2cf60faa25266271b2c33a6c7c8b0f3e3c1f --out /path/to/fresh-host
```

The retained latest host-v2 output is190457 bytes before its JSON receipt. The first host-v1 missing-header compilation failure and first caller-census v1 (which accidentally included declarations) are preserved and superseded. No SH4 rebuild, full program, stage, guest, release check or physical Dreamcast acceptance was performed for this audit. Original staged assets and production recipes are untouched. Menu-window restoration remains disabled after its measured regression.

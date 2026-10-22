# CORE_PIN2 classification under a full preload admission limit

The frozen8b0340cf7 preload skips semantic core/own discovery once its slot limit is full. Main's candidate fixes that only under the existing default-off `RESIDENT_LIST_CACHE` guard. This worker changes tests/docs only; main retains runtime review, SH4 and integration ownership.

Baseline `native_ui.cpp`: `8b0340cf7dd0916c6094d2c3db4fecd91a4408a7`, SHA256 `09b256cf1fcf33d900d4a1f00a3ca748b597f5584354d0ac4a707ffeb8bb23df`.

Qualified main candidate: raw CRLF SHA256 `839d6cd68151a91ffb05e683bc8ef0d6ff04b0364a9a0676871bb218ac903fd7`; normalized LF SHA256 `4b275db2a0e5206a70ac24845887b097c209ccf01c14e5f58700f0e9ab63bb2a`. The fixture normalizes line endings before extracting complete source functions and binds both identities.

## Source contract and caller reachability

The core-key set is16 unique keys, retained across passes. `core_pinned()` under CORE_PIN2 first checks `core_room_on`, then whether the entry key is in that set. It affects victim selection in load/retry, leftover eviction and release paths; CORE_PIN2's existing large-picture yield is separate and unchanged.

The documented rule in preload_resident is that the core keys are pinned where the room has its own resident list. Both the baseline default512-byte scan and cached replay put the core-key discovery and own-row count **inside** an inner loop conditioned on `n+resident<limit`. At the end CORE_PIN2 assigns `core_room_on=own!=0` unconditionally. Thus a full admission limit can classify a room with known own rows as having no own list. A cached cold scan still captures every matching row independently of admission; this does not help if replay classification uses the same admission-conditioned loop.

Normal `preload_identities()` computes `limit=max(kTextureCount-reserve_slots-pinned,0)`, runs room/PS2-world, enemy, player and weapon selection before calling preload_resident unconditionally. The declared source recipe chain (`ch2-build.sh` through test15/route/build-r21) supplies TEX_RESIDENT1/TEX_SLOTS448. The checked-in test21 knobs declare ROOM_RESIDENT1/CORE_PIN2. The source reserve is32 slots, giving nominal416 before pinned deductions. RESIDENT_LIST_CACHE defaults0 in Makefile and is absent from the production test21 knob list. No recipe/default was changed or actual program recipe certified by this source audit.

Room/player/weapon/enemy binds and a subscreen release can mark a pass pending; the frame path executes it when frame_ready and no VRAM claims. The caller does not reserve slots for metadata discovery. The host also executes the actual preload_select with410 or416 synthetic8x8 owner identities to reach the same conditions through the normal function interface. These are valid source-level conditions, **not proof that a real archive/scene fills that limit**. No target saturation, core eviction or visual failure was observed in this unit.

## Baseline reproduction and candidate result

The metadata projection uses the exact checked-in r000/r101 TSV identities: six core rows and219 r101 rows, packed in the producer's room/key order, padded to4096bytes. It is a constructed selected-room metadata fixture, not a staged dc/resident.bin. The219 own rows include the six core texture keys, so the roomy pass selects219 distinct keys from225 rows.

| Condition | Baseline default and cache | Candidate cache ON | Admission result |
| --- | --- | --- | --- |
| n416, limit416 on entry |0 discovered core keys; own=false |6 keys; own=true |unchanged n416,0new list picks |
| n410, six leading core rows fill limit |6 keys; own=false |6 keys; own=true |unchanged n416,6list picks |
| n410, six core uploads already resident |6 keys; own=false |6 keys; own=true |unchanged n410/resident6 |
| Warm metadata after a roomy pass, then n416 |6 retained keys; own=false |6 keys; own=true |cache0reader calls; default9 |
| Byte budget0, slots available |6 keys; own=true |6 keys; own=true |0picks in both |

`core_pinned()` follows the classification: false in the saturated baseline examples and true for the known core key under the candidate, with core yield outside this fixture. Guard-OFF behavior remains unchanged. This is a semantic correction under its experimental guard, not a measured performance improvement.

## Independent controls

Both baseline and main candidate pass98 independent source-host assertions across24 cases. They cover equality/over-limit/zero limits, resident saturation, selection filling the limit before own rows, warm replay, byte-only pressure, absent own rows, malformed own-row semantics, cross-block late rows,16-key capacity/duplicates, error before and after a known own prefix, recovery, trailing partial pieces, and257-row overflow with continued full scans.

The exact predicates matter: core discovery requires room0, nonzero width and a nonzero key, **before** height/size validation. Own count includes any matching nonzero-room row, also before dimension validation. Tests preserve those existing semantics rather than silently strengthening file validity. The real r000 metadata has only six keys, below the16-key bound. The synthetic20-key/cross-block fixtures test the bound/order and are not claimed as production data.

On a late read error, only successfully read pieces contribute. If the error precedes the first own row, own remains false; that inherited uncertainty is not proof the file has no own rows. If a valid own row was seen earlier, the candidate retains that positive classification even though caching remains invalid. Partial tails are not processed, and incomplete/overflow scans remain uncached and retry. The fix does not add rollback, a no-fail assumption, or a complete-list guarantee on partial I/O.

The pre-existing47-case differential suite is also retained for CORE_PIN0/1/2 (141 cases). The baseline run compares full output, including old metadata, and reproduces the flaw while passing all141. The candidate run compares **admission output** (selected keys, n/resident/bytes/listed/picked) and separately uses the independent semantic oracles above. It passes all141 admission cases, including all absent/error/OOM/truncation/size-change/overflow/retry controls. The original141 receipt is untouched. The existing suite projects a64-key metadata array; the independent oracle uses the actual16-key bound and448-entry recipe size. New runs use UBSan; the earlier ASan+UBSan qualification remains separate.

## Evidence and scope

`baseline-receipt.json` and `candidate-receipt.json` bind exact source/helper/test/recipe/TSV hashes, generated source, commands and results. Raw outputs:

- `C:/Flycast-Evidence/re4-dreamcast/cache21-payload-20261021/core-pin2-baseline-host-v1`
- Sibling `core-pin2-root-host-v1`

Combined output before receipts is1205523bytes, below the4MiB task cap. Shared buildslot, fresh disk floors, owned PID/process-group identity,55-second/512KiB log and4MiB output limits are enforced. No runtime/shared files, production recipes, original assets or SD content were changed. No SH4/full-program/Flycast/release/physical-console acceptance or target performance claim follows from these tests. Main's independent SH4 checks are outside this worker unit. Window restoration remains disabled after its established regression.

```sh
python3 run.py --source /root/probe/codex-cache21-integration-next \
  --ref 8b0340cf7dd0916c6094d2c3db4fecd91a4408a7 --out /path/to/fresh-baseline

python3 run.py --source /root/probe/codex-cache21-integration-next \
  --ref 8b0340cf7dd0916c6094d2c3db4fecd91a4408a7 \
  --working-ui /root/probe/codex-cache21-integration-next/port/dreamcast/game/platform/native_ui.cpp \
  --expect-fixed --out /path/to/fresh-candidate
```

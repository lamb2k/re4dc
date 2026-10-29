# Build 35 gap-hook event contracts

The 58 appended reasons in `fallback_audit35.def` describe work and decisions at
the existing call boundaries. They do not change the selected implementation.
Each source addition has its own `RE4DC_FALLBACK_AUDIT35` guard. Logical `#line`
restoration keeps existing source diagnostics and disabled preprocessing stable.

| Family | Event contract |
| --- | --- |
| `cl_spring_fast`, `cl_spring_src` | One executed spring call. `CLOTH_SPRING=2` can execute both implementations, so it records both. |
| `cl_points` | The submitted `divH * divV` grid size for each executed spring call, including pinned points skipped inside the loop. This measures submitted grid work, not distinct moving points or spring evaluations. |
| `cl_chain`, `cl_links`, `cl_skip` | Nonempty `PenClothMove`, `PenClothMove2`, or `PenClothMove3` calls and their admitted `Num` links; a separate nonempty `PenClothSkipTick` call count. |
| `ft_hit`, `ft_build`, `ft_refuse`, `ft_source` | Validated cache-key hits, descriptor build/refresh, cache refusal, and actual source texture initialization, respectively. A later swap refusal can count in the same call as a key hit. A refusal followed by source initialization records both phases. |
| `ft_flush`, `ft_reset` | Textures flushed from an active cache entry; capacity recycling events. Room retirement does not masquerade as a capacity reset. |
| `eg_*_scan`, `esp_del_scan` | Actual scalar slots visited by the production walk. Bitmap skips and diagnostic verification walks are excluded. Amounts accumulate locally, then publish once per call. |
| `eg_*_map`, `esp_del_map` | The call entered with an admitted bitmap. A later scalar fallback may occur in the same call. |
| `eg_*_miss`, `esp_del_miss` | A bitmap was unavailable at entry. The original scalar walk remains active. |
| `eg_*_stale`, `esp_del_stale` | At least one scalar slot was visited after an initially admitted bitmap's generation changed. A generation change in the final callback alone does not count as scalar fallback. |
| `eg_*_off`, `esp_del_off` | The legacy scalar implementation was selected at compile time. `esp_del_owner0` separately describes an unfiltered owner; `esp_del_empty` records the existing empty-owner early return. |
| `at_alive_build`, `at_alive_full`, `at_cached_full` | Alive-list build attempts, new capacity refusals, and retained negative-cache refusals, respectively. |
| `at_cand_full`, `at_dirty_full`, `at_list_scan` | A 96-candidate collection/insertion refusal, more than 64 unapplied dirty notes, and calls to the original linked-list collector. These decisions do not all force the final collision pipeline to use source traversal. |
| `at_fast`, `at_source` | One list run admitted at pipeline entry. Each run consists of positions, collision, and old-position phases. The enemy and object lists count separately; these are not individual traversal passes or body pairs. |
| `mot_binary`, `mot_linear`, `mot_probes` | One admitted archive search and the actual metadata key reads, including the binary search's terminal equality probe. Probe amounts accumulate locally. |
| `mot_found`, `mot_missing`, `mot_unbound` | A matching metadata key, an admitted archive search without a match, or no searchable binding. A key match does not independently certify that its table load succeeded. |
| `skin_deferred`, `skin_defer_v` | Successfully deferred infos and their vertex counts, including positive pending-palette, ordinary lazy, eager-native, and face-lazy admissions. |
| `skin_defer_fail`, `skin_fail_v` | Failed native/pending deferral attempts. A face-lazy eligibility return of zero is not counted as an attempted native deferral. |
| `skin_trans_cpu`, `skin_cpu_v` | Infos reaching the existing Trans CPU skin call, after allocation and pointer checks. Failed allocation does not count CPU work that never ran. |
| `skin_trans_morph`, `skin_morph_v` | The morphed subset of that Trans CPU work. Successful face-lazy admissions count as deferred instead. |
| `palette_plain`, `palette_ext` | Positive matrix counts admitted at the ordinary or extended palette builder boundary. |

## Actual-source host qualification

From the repository root:

```sh
python3 -B port/dreamcast/tools/cloud/build35/gap_host.py \
  --output /tmp/build35-gap-host
python3 -B port/dreamcast/tools/cloud/build35/gap_host.py \
  --sanitize --output /tmp/build35-gap-host-san
```

The output directories must be new. `--only motion`, `cloth`, `collision`, or
`effects` narrows the same fixture. The runner records hashes of every extracted
production source, the reason registry, and its fixture inputs, and verifies that
they did not change during execution.

The fixture compiles audit-off and audit-on versions of the actual source and
compares returned results, ordered action traces, and modified state. Expected
event counts exercise both admission and refusal. It executes complete motion
acquire, cloth spring, collision collection/cache/pipeline, generator traversal,
and sprite deletion bodies. External allocation, collision response, effect
callbacks, and system state use controlled bindings.

The three chain-move tests execute the exact admission prefixes through the first
external floor query; they do not simulate the remaining chain physics. The
complete skip-tick function is tested with its RNG call count and wind state.
Front/skin qualification is in the separate `trans_events.py` fixture. The
collector/window tests validate real FA29 forwarding independently; these event
fixtures use a recording `hit` function to isolate event placement. Sanitizers
disable LeakSanitizer because the managed environment does not permit its process
inspection; AddressSanitizer and UndefinedBehaviorSanitizer remain enabled.

These tests establish counter placement and unchanged controlled behavior. They
do not establish game-route coverage, whole-image identity, or console timing.

# Build 36 — source-bound fallback scanner repairs

**2026-10-29 — progress 5:** Done: `--scan36=1` texture selection, source-bound
native-list membership and separate legacy-world inventory; 144 targeted tests
PASS and 126 baseline/absent/zero artifact-byte comparisons PASS. Next: Claude's
private-data rescan with the exact commands below. Blocked: private-data
completeness; no game data or console was used. The scanner stays default off;
there are no game/build/recipe/asset changes.

**2026-10-29 — progress 4:** Published the isolated legacy-world adapter and
13 public-writer/corruption tests. The scanner entry point stayed unchanged;
CLI integration and the final private-data commands were next.

**2026-10-29 — progress 3:** Published native-list membership and 28 source-table,
identity and mutable-name tests. The scanner entry point stayed unchanged;
legacy-world inventory and CLI integration were next.

**2026-10-29 — progress 2:** Published texture selection/provenance and 40 tests.
The scanner entry point stayed unchanged; list/world adapters and final
integration were next.

**2026-10-29 — progress 1:** Traced the three source contracts and published the
documentation checkpoint as `95f5be02`. Implementation and public qualification
were next; private data remained blocked.

Branch: `codex/fallback-scan-fixes-20261029`. Tested/rebased integration:
`bb5f18e0e3b3fac4c76bd42d0c9d8107385c568c`. Started from `4f9d4443`; the intervening
integration changes are the Build 34 follow-up and the Build 35 audit/window
implementation, followed by owner qualification notes at `bb5f18e0`. The
Build 36 delta is measured above those landed changes.

## Scope and decisions

The Build 36 scanner mode is `--scan36=1`, default `0`. The absent/zero
path retains the Build 29 scanner behavior. This is an offline tool change;
there is no game knob, runtime change, release-recipe change, or asset rewrite.

- Texture selection must follow composed-file and runtime precedence. The
  old duplicate-key error comes from merging different files in `scan.py`;
  it does not justify accepting repeated keys in a physical pack index.
  `t11-fix.py` replaces a whole `dc/tex.pak` when a later data set supplies
  that path. Runtime lookup selects the canonical pack before the eligible
  loose file, subject to the resolved recipe and live standard-quality room
  state. Explicit ordered pack inputs mean whole-file replacements,
  not a union of entries. Unknown selection remains unknown.
- Global model membership must come from recognized native ESL lists and
  the actual source `EmFileTbl`/`FileTbl` archive mapping. Story/player/costume
  alternatives and retained lists remain conditional. An archive-load
  candidate does not prove which BIN, actor instance, or appearance drew.
  Exact source/model/hash context and explicit room lists keep precedence.
- Old ordinary R4IM files receive validated geometry inventory only
  when their format does not require R4PW. Unknown policy, material and
  placement facts remain unknown. A malformed present sidecar or a missing
  mandatory modern sidecar remains a refusal.

### Texture precedence and reporting

`textures36.py` reuses the unchanged pack/texture readers. The canonical
`dc/tex.pak` is layer 0. Repeatable `--texpak-layer FILE` assigns explicit
whole-file replacements after it, in command-line order. Missing keys in the
last pack are not inherited from older packs, although the runtime may find
the eligible loose file. A discovered extra pack or ordinary `--input` pack
has no implied staging order and remains unselected/unsupported.

Resolved `TEX_PACK`, `TEX_RESIDENT` and `QUALITY_ASSETS` determine possible
lookup modes. The current room's standard-quality selection remains unknown.
Conflicting loose/packed copies are retained as source variants rather than
rejected as simultaneous effective entries. Repeated keys inside a physical
pack index, bad index/payload checksums, invalid extents and overlapping
payloads remain refusals. A bad/unreadable last pack does not reveal an older
pack; uncertain presence/palette is reported as unknown. This is a static
availability model; transient I/O, residency and upload admission remain live.

`report.json/texture_selection` includes source and payload SHA256, layer,
member offset, possible/shadowed variants, and predicates for referenced keys.
The headline count is definitely present keys. Conditional keys and physical
variants have separate denominators. Unknown does not become a clear or a
static-missing result.

Source authorities: `tools/d367/test11/t11-fix.py` (ordered `--data`, `r[k]=v` whole-path
replacement), `tools/d367/stage.sh` (ordered loose-directory copies),
`game/platform/include/texpack_index.inc` (strict unique physical index),
`game/platform/native_ui.cpp` (packed/loose/standard-quality lookup), and
`game/game30.mk` (`TEX_PACK=1` requires `TEX_RESIDENT=1`). The existing strict
`formats.parse_texpak` and `tools/d367/texpack.py` are unchanged.

### Native list membership

`room_lists36.py` reads the 11 `stage.cpp` ESL names, all four current 64-entry
enemy loader tables, the 254-entry `FileTbl`, Ashley remapping and DVD name
normalization from production source. Four source hashes are in every enabled
report. Mapping is native list/record/hash → loader alternatives → exact
archive path/hash → exact scanned ModelData keys. It does not generate
`emNN.drs` from the enemy ID.

Every scanned BIN in the referenced archive is a conditional load candidate.
Instances, selected appearance, story/player/costume, activation and actual
draws remain unknown. Retained later lists on a room revisit are preserved as
alternatives. Mutable non-DLL `.das` filenames, core IDs, unsupported/embedded
lists, missing/rejected targets and ambiguous case-normalized paths remain
unresolved. GLP1/compiled replacements without source archive identity stay
unassigned until owner binding. Script/event spawns and runtime ESL patches
are not invented from static lists.

Explicit context and room-list entries override same-room automatic entries.
The context template stores automatic entries only in `room_candidates`, not
`rooms`: replaying an untouched template cannot promote or retain an old list
candidate as owner evidence. Details/barn TSVs add a `membership` column in
enabled mode; `report.json/room_membership` preserves the complete provenance.

Source authorities: `include/em_set.h`, `tools/le_mirror.py`,
`src/game/stage.cpp` (`emlist_name`, `readEmList`), `src/game/read.cpp`
(`EmFileTbl*`, `readEmData`, `EmReadSearch`, `checkAshleyId`, mutable
`SET_DRS_NAME`), `src/game/dvd.cpp` (`FileTbl`) and the platform DVD normalizer.
`tools/assetpipe/discover.py` is the existing source-table-reader precedent.
Changed unsupported dispatch/macro/normalization syntax refuses automatic
binding rather than silently retaining a stale mapping.

### Legacy world coverage

`world36.py` validates ordinary v1 plus v2/v3 oct-normal, prelit and oct-vertex
writer layouts, including indexed meshlets, LOD ownership and optional
class/rule sections. It verifies extents, CRC, padding, finite grids/UVs/errors,
part/meshlet ownership, strip/pool references and bounds enclosure. No bytes
are repaired. These models have kind `R4IM-legacy`, `placements=None`, unknown
policy fields and inventory-only rows. Coverage remains `partial`.

Any present policy is passed to the existing strict adapter, including empty
bytes. A directory/dangling symlink is not optional absence. PS2 owner `0x50`,
physical variants, v4, unknown extensions and unsupported appended tables
remain rejected without their mandatory adapter/policy.

Source authorities: ordinary writers in `tools/convert_room_bins.py`,
`room/instanced_mesh.hpp` geometry/encoding admission, the PS2 writers
`tools/ps2_world_r4im.py` and `tools/ps2_room_r4im.py` (owner `0x50` and R4PW),
and `native_static.cpp`'s PS2 mesh/policy open path. Seven synthetic bundles
come directly from the public ordinary writer, not handcrafted valid headers.

## Validation and disabled identity

| Gate | Result |
|---|---:|
| Existing scanner regression tests | 38 PASS |
| Texture selection/refusal tests | 40 PASS |
| Native list/source-contract tests | 28 PASS |
| Legacy world writer/corruption tests | 13 PASS |
| End-to-end enabled reports, template replay, CLI and containment | 20 PASS |
| Actual runtime texture-index tests | 5 PASS |
| Baseline/absent/zero actual CLI executions | 21 PASS |
| Exact artifact-byte comparisons, nine outputs × seven scenarios × two controls | 126 PASS |
| Exact exit/stdout/stderr comparisons | 14 PASS |

The OFF gate compares normal mixed data, pack/loose conflicts, missing modern
policy, malformed present policy, global ESL/DRS, explicit context/list/external
header, and old world without policy. It asserts that each intended inventory
or refusal was exercised. The same output pathname is used sequentially;
there is no normalization. All 39 fixture files / 92,238 bytes stay unchanged.
The receipt binds 10 archived source hashes and 30 candidate Python hashes.

Receipt: `tools/cloud/build36/receipts/off-identity.json`, SHA256
`252c4ef05ee630dbeb802cc15f55055640a222a093aa0ae7b1c3b3478b2a5afa`.
Python: 3.12.14. Its recorded candidate HEAD contains the isolated adapter checkpoints; the
final scanner integration is additionally bound by file hashes.
The final commit also contains the README and this report. Every changed path
is inside the offline scanner/checker or this hand-back. No target source,
header, compile/link recipe, game data or generated asset is changed.

The unchanged target-input claim is a source-scope proof, not a newly rebuilt
ELF/overlay/ISO comparison. No release recipe is enabled or changed. All new
Python adapters are imported only for `--scan36=1`.

```bash
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_scan.py' -v
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_*36.py' -v
python3 -B port/dreamcast/tests/test_texpack_index.py
python3 -B port/dreamcast/tools/cloud/build36/verify_identity.py \
  --base bb5f18e0e3b3fac4c76bd42d0c9d8107385c568c \
  --out /tmp/build36-off-identity-new.json
```

All nine documented shell blocks parse; the primary private-data command was
also executed on public synthetic data with paths containing spaces. Its
strict-incomplete handling and unchanged input hashes passed.

Use a new receipt path. The receipt checker uses Python's `file_digest` and
tarfile `data` extraction filter; the qualified environment is Python 3.12.14.

## Cost and output changes

| Runtime delta | Value |
|---|---:|
| Warm cycles / cold-I cycles | 0 / 0 |
| Loads / stores / 32-byte data lines | 0 / 0 / 0 |
| Game code / data / stack / heap bytes | 0 / 0 / 0 / 0 |
| MODELLED whole-frame delta | **0 ms** |

This is an offline scanner. It neither builds new assets nor changes rendered
outputs. Enabled report counts/rows/provenance change as described above;
conditional choices and incomplete metadata are explicit. Private host scan
time, memory and completeness await the owner's actual input tree. No speed,
look, gameplay, STRICT, memory or console acceptance is claimed from these
static inventories.

## Exact private-data commands for Claude

Run from the repository root after this branch is available. Set the three
environment variables to existing private inputs and a **new** output
directory outside the input tree. Use the final composed disc tree: this is
not an instruction to scan or merge raw extraction/layer directories.

```bash
set -euo pipefail
: "${PRIVATE_DISC_TREE:?Set the composed native disc root}"
: "${IMAGE_KNOBS:?Set the exact image resolved-knobs.txt}"
: "${SCAN36_OUT:?Set a new private output directory outside the disc tree}"
test -d "$PRIVATE_DISC_TREE"
test -f "$IMAGE_KNOBS"
test ! -e "$SCAN36_OUT"
python3 - "$PRIVATE_DISC_TREE" "$SCAN36_OUT" <<'PY'
import pathlib, sys
tree, out = map(pathlib.Path, sys.argv[1:])
if out.resolve().is_relative_to(tree.resolve()):
    raise SystemExit('SCAN36_OUT must be outside PRIVATE_DISC_TREE')
PY
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
mkdir -p "$SCAN36_OUT"
SCAN36_ROOMS="$(python3 -c 'print(",".join([f"r{x:03x}" for x in range(0x100,0x121)] + ["r200"]))')"

python3 -B port/dreamcast/tools/d367/fallback_scan/scan.py \
  "$PRIVATE_DISC_TREE" --out "$SCAN36_OUT/off" \
  --rooms "$SCAN36_ROOMS" --knobs "$IMAGE_KNOBS" --scan36=0

set +e
python3 -B port/dreamcast/tools/d367/fallback_scan/scan.py \
  "$PRIVATE_DISC_TREE" --out "$SCAN36_OUT/on" \
  --rooms "$SCAN36_ROOMS" --knobs "$IMAGE_KNOBS" --scan36=1 --strict
SCAN36_RC=$?
set -e
if [ "$SCAN36_RC" -gt 1 ]; then exit "$SCAN36_RC"; fi

python3 - "$SCAN36_OUT" <<'PY'
import collections, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
old = json.loads((root / 'off/report.json').read_text())
new = json.loads((root / 'on/report.json').read_text())
for name, report in [('off', old), ('on', new)]:
    unassigned = sum(any(m['room'] == 'unassigned' for m in item['memberships'])
                     for item in report['model_inventory'])
    print(name, report['status'], 'models', report['models'],
          'texture_keys', report['textures'], 'unassigned_models', unassigned)
print('texture_selection', json.dumps(new['texture_selection']['summary'], sort_keys=True))
print('membership_states', dict(collections.Counter(
    item['status'] for item in new['room_membership']['inventory'])))
print('legacy_models', sum(item['kind'] == 'R4IM-legacy' for item in new['model_inventory']))
print('coverage_gaps')
for row in new['coverage']:
    if row['status'] != 'scanned':
        print(row['source'], row['format'], row['status'], row['message'], sep='\t')
PY
```

Exit 1 from enabled `--strict` means an **INCOMPLETE** report was written. It
is expected for partial legacy metadata or unresolved targets and must not be
relabeled a complete scan. Exit 2 is a failed invocation/output/context gate.
Return the coverage gaps, selection summary, source hashes, and remaining
unassigned source/model identities under Answers; keep private assets and
full private reports out of Git.

If the exact final pack is intentionally supplied as separate ordered
replacements, use this additional command instead of treating `--input` or
directory sorting as layer order. Other inputs must already be composed:

```bash
set -euo pipefail
: "${PRIVATE_DISC_TREE:?Set the composed loose/room tree}"
: "${IMAGE_KNOBS:?Set the exact resolved-knobs.txt}"
: "${PACK36_EARLIER:?Set the earlier data set tex.pak}"
: "${PACK36_LATER:?Set the later data set tex.pak}"
: "${SCAN36_LAYER_OUT:?Set a new private output directory outside the input tree}"
test -f "$PACK36_EARLIER"
test -f "$PACK36_LATER"
test ! -e "$SCAN36_LAYER_OUT"
python3 -B port/dreamcast/tools/d367/fallback_scan/scan.py \
  "$PRIVATE_DISC_TREE" --out "$SCAN36_LAYER_OUT" --rooms r103 \
  --knobs "$IMAGE_KNOBS" --scan36=1 \
  --texpak-layer "$PACK36_EARLIER" --texpak-layer "$PACK36_LATER" --strict
```

The last pack replaces the entire earlier pack. Do not use this command to
invent an order for unrelated variants. If owner-verified model membership or
lighting is available, supply the existing hash-bound `--room-list`/`--context`
formats on a further run with a fresh output destination. No new console run
is necessary to qualify this scanner implementation; live selection/light
facts still require existing owner capture evidence.

## Questions

No code question remains. Please run the private rescan above and return its
coverage summary. In particular, confirm which source/payload differences
were legitimate pack-versus-loose shadows, and list global replacements or
mutable-name targets that still need explicit owner membership. An unresolved
field is not authorization to invent a binding.

## Answers (Claude)

Pending.

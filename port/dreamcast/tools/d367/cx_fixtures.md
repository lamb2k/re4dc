# Private room fixtures for first-pass checks

`cx_room_fixtures.py` produces one entry, two heading views, and one short-walk
warp per room, plus fixture JSON and a source/dependency manifest. It consumes
the stage-1 and castle asset hand-back indices and an existing reviewed fixture.
It writes generated assets outside the repository. It does not launch Flycast,
change runtime code, suppress actors, or modify texture packs.

## Reproduce

Supply paths owned by the current lane; the examples below are placeholders.

```sh
python3 port/dreamcast/tools/d367/cx_room_fixtures.py \
  --stage1-index PRIVATE/stage1-index.json \
  --castle-index PRIVATE/castle-index.json \
  --base-fixture PRIVATE/reviewed-fixture.json \
  --room-fixture r112=PRIVATE/reviewed-r112.json \
  --iso PRIVATE/source.iso --out PRIVATE/cx-fixtures \
  --prepare-missing --texture-index-dir PRIVATE/texture-selections \
  --arm-tool port/dreamcast/tools/d367/texchk/fixture_arm.py \
  --candidate-dir PRIVATE/programs/candidate-routecxARM --arm-label cxARM
```

`--rooms` restricts generation. Omit arming options when only preparing fixtures;
all three arming options are required together. Every usable `.armed.json` is
written by `fixture_arm.py`, never by string replacement of overlay paths. An
unavailable overlay leaves its intended fixture unarmed and is a recipe blocker.
Do not reuse an overlay built against another ELF.

The source door scan is reused only with the same ISO SHA-256 and scan-tool
SHA-256. Arrivals are fresh AEV door destinations with destination part zero.
Existing presets select a matching source arrival; they do not replace extracted
coordinates. The event-only r22b arrival uses the explicit `vecZero` jump in
`src/st2/r221.cpp`. Left/right views change the arrival heading by 0.65 radians;
the walk adds `act 360 fwd 12`. These are proposed camera/walk checks until target
execution establishes their safety and visible coverage.

The r111/r112/r113/r11c presets preserve the chapter-2-2 Ashley requirements.
A `status 3 0x04000000` line is a documented runtime requirement: the base
90606dcf warp bridge does not implement it. Its presence does not prove the
status applied. No `dead` or `kill` commands are generated.

## Ancillary assets and dependencies

For a missing room archive the generator uses the existing native-LE mirror and
native texture extraction tools. A room in `prepare_native_ui.ROOM_CONTRACTS`
also follows the reviewed compact/release recipe. Other rooms retain uncompact
archives and a blocker; this tool never broadens consumer contracts silently.
Any conversion rejection remains a blocker and retains its log. New room AICA
banks, object/native-model coverage, events, and runtime modules require their
own qualification. A generated archive is not gameplay acceptance.

The native mirror supports authored empty ITM tables (zero id count, both model
and texture offsets null), following the zero-iteration loop in
`src/game/item_model.cpp::cItmSys::DataLoad`. AEV type 0 scratch is cleared by
`sceAtDataLoopInit`; type 2 never reads its union in `sceAtFunc_exec`. Their
unused authored bytes are preserved. Type 11 accepts a small nonzero placeholder
only for an enabled, uncreated, unparented quad whose corresponding SAT/EAT slot
will be overwritten by `sceAtSetScrAt`. Live callback and parent fields still
require null values, and unreplaced collision slots and PPC addresses reject.
Synthetic layout/rejection tests cover these source contracts; control room
ARC/DAR byte identity is a separate private-source check.

`cx_room_dependencies.py --iso SOURCE --fixture-index OUT/index.json --out DEPS`
uses the source ESL selection rules, archive tables, and room scripts to prepare
available endian-correct ESL/model files and qualified EVD transports. Add
`--dependency-dir DEPS` on a subsequent fixture-generation pass to fill absent
fixture keys. Existing reviewed fixture entries always win. Generic source model
archives still require the PS2/native rendering census; no GC fallback is accepted
merely because a source archive converted successfully. The dependency report
retains unavailable events and unsupported formats.

Texture selections are read from the texture lane's per-room `textures[].chosen`
records. The chosen loose files are staged, but packed entries still win their
keys. Audit actual packed/loose winner bytes before claiming the selection was
tested. Shared pack application belongs to the pack owner.

World-only texture lists do not include every material composite used by item
or actor draws. For a separately qualified supplement, create new variants:
`cx_fixture_supplement.py --supplement SUPPLEMENT.json --fixture ORIGINAL.unarmed.json
--arm-tool fixture_arm.py --candidate-dir CANDIDATE --arm-label ARM
--suffix pairfixed --report REPORT.json`. Repeat `--fixture` for every view.
The supplement must provide exact package SHA-256 and native-parser PASS for
each pair. The tool refuses shared-pack shadowing, writes only new named
variants, records source-fixture and supplement hashes, and re-arms overlays.
A static winner/path check still needs a new runtime TEX_CHECK capture.

## Audit and run

```sh
python3 port/dreamcast/tools/d367/cx_fixture_audit.py \
  --root PRIVATE/cx-fixtures --candidate-dir PRIVATE/programs/candidate-routecxARM \
  --dependencies PRIVATE/dependencies --texture-audit PRIVATE/selection-audit.json \
  --output PRIVATE/fixture-readiness.json
```

The audit reports every required room ARC/DAR, missing source path, mismatched
build overlay, unsupported status requirement, source entry, dependency error,
and texture selection result. Conversion errors are associated with the selected
archive roots or the exact current failed preparation path; retained older
errors are reported separately as `historical_archive_errors`.
`PASS_PATHS_AND_ARM` is a static check only. Attach
first-pass logs/stills/TEX_CHECK and fallback results to the exact fixture SHA.
Use the walk plus two independent view fixtures when the bridge has no supported
camera-control directive. Keep initial diagnostic fixtures immutable once used.

The legacy private staging harness cannot add event certificate names with two
extensions (for example `evd/e113.evd.evq`) to the primary ISO namespace. Adapt
only an owned harness copy before staging those fixtures:

```sh
python3 port/dreamcast/tools/d367/texchk/cx_iso_names.py \
  --input PRIVATE/stage-scenario.py --output PRIVATE/stage-scenario-v2.py
```

This retains exact Rock Ridge and Joliet names and payloads while making a valid
primary alias (`E113_EVD.EVQ`). Existing single-extension aliases stay unchanged;
alias collisions are rejected. The output must be new, and a provenance sidecar
records both script hashes. The stage utility still verifies both runtime
namespaces, the independent raw reader, payload hashes and the original boot area.

## Portable definitions and extra overview views

The standard room fixture recipe is checked-in source:
`cx_room_fixtures.py::entry_for` selects the named incoming source doors, resolves
other arrivals from the source AEV scan, and preserves chapter requirements.
The generation loop defines entry, left, right and walk headings/actions. The
reproduction command above supplies private assets as inputs; generated private
fixture JSON is not the only definition of those presets.

Additional named heading presets live in `cx_view_presets.json`. The
`r112-overviews` set defines `overview-back` (+pi) and `overview-quarter`
(+pi/2), measured from the exact captured entry warp heading. Reproduce with:

```sh
python3 port/dreamcast/tools/d367/cx_fixture_views.py \
  --source-fixture PRIVATE/cx-r112-entry.armed.json \
  --view-set r112-overviews --out PRIVATE/r112-overviews-NEW \
  --arm-tool port/dreamcast/tools/d367/texchk/fixture_arm.py \
  --candidate-dir PRIVATE/programs/candidate-routecxARM --arm-label cxARM
```

This command copies the entry fixture's exact assets and source warp commands.
Only the warp name and heading change. It records source fixture/warp and
registry SHA-256, refuses existing output names, re-arms every overlay, and
requires that only `dc/warp.txt` differs in the replacement map. The candidate
must therefore match the captured entry arm. Camera visibility still requires
new target captures.

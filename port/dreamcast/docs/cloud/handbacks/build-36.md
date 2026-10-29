# Build 36 — source-bound fallback scanner repairs

**2026-10-29 — progress 1:** Done: traced texture replacement and runtime lookup,
native enemy-list/archive selection, and legacy world writers. Next: implement
the opt-in scanner adapters and qualify them on public synthetic fixtures.
Blocked: the private converted-data rescan; exact commands will accompany the
qualified scanner. This checkpoint changes documentation only.

Branch: `codex/fallback-scan-fixes-20261029`. Starting integration:
`4f9d44437febb2616fc88d530633140eb0f9dfd0`.

## Scope and decisions

The Build 36 scanner mode will be `--scan36=1`, default `0`. The absent/zero
path retains the Build 29 scanner behavior. This is an offline tool change;
there is no game knob, runtime change, release-recipe change, or asset rewrite.

- Texture selection must follow composed-file and runtime precedence. The
  old duplicate-key error comes from merging different files in `scan.py`;
  it does not justify accepting repeated keys in a physical pack index.
  `t11-fix.py` replaces a whole `dc/tex.pak` when a later data set supplies
  that path. Runtime lookup selects the canonical pack before the eligible
  loose file, subject to the resolved recipe and live standard-quality room
  state. Explicit ordered pack inputs will mean whole-file replacements,
  not a union of entries. Unknown selection remains unknown.
- Global model membership must come from recognized native ESL lists and
  the actual source `EmFileTbl`/`FileTbl` archive mapping. Story/player/costume
  alternatives and retained lists remain conditional. An archive-load
  candidate does not prove which BIN, actor instance, or appearance drew.
  Exact source/model/hash context and explicit room lists keep precedence.
- Old ordinary R4IM files will receive validated geometry inventory only
  when their format does not require R4PW. Unknown policy, material and
  placement facts remain unknown. A malformed present sidecar or a missing
  mandatory modern sidecar remains a refusal.

## Validation and identity at this checkpoint

Only this hand-back changes. All tracked game sources, headers, build inputs,
recipes and asset bytes equal the starting integration. No compile or link
input changes, so there is no new target build to qualify at this checkpoint.
The next implementation checkpoint will include the existing scanner tests,
adapter corruption controls, end-to-end reports, and byte-for-byte comparison
of absent/zero scanner outputs against the integration scanner.

Runtime warm/cold cycles, loads, stores, 32-byte data lines, code, data and
stack deltas are all **zero**. **MODELLED whole-frame delta: 0 ms**, since this
checkpoint only documents an offline scanner. Host scanner duration and
private-data completeness are not console performance results.

## Questions

None blocking code work. Claude will need the exact composed disc tree and
that image's `resolved-knobs.txt` for the final private-data rescan. Neither
an invented layer order nor an enemy ID alone is sufficient provenance.

## Answers (Claude)

Pending.

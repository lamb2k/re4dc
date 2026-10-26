# Texture arena key and final-refusal controls

These controls support the independent, default-off `TEX_ARENA_CURRENT_KEY` fix
and `TEX_FINAL_REFUSAL_LOG` diagnostic. They use public source and synthetic
inputs. No game data, emulator, or physical console is required.

## Host behavior

From the repository root:

```sh
python3 -m unittest discover -s port/dreamcast/tests -p test_tex_arena_current_key.py -v
python3 port/dreamcast/tools/d367/tex_arena_current_key/host_checks.py \
  --output /tmp/tex-arena-host
```

`host_checks.py` extracts the complete current `load()`, its final-refusal helper
and macros, the arena classifier, and the `Key` definition from `native_ui.cpp`.
It compiles the unchanged `vram_pages.cpp` allocator. Package/filesystem operations
are injected; assertions exercise the actual load control flow. UBSan is enabled.
Temporary sources/executables are removed; text logs and a receipt remain in
the requested output directory.

The 10 variants execute 108 cases:

- Six allocator variants cover fix off/on, fresh core keys, reused core slots,
  ordinary room placement, a controlled fragmentation schedule, `CORE_PIN=0`,
  and preservation of the `VRAM_ROOM_ARENA_NO_TOP` upper exclusion.
- Four load variants cover fix off/on × logging off/on. Each exercises 17
  terminal refusals: invalid input/identity, effect guard, minimum budget,
  missing key, fragmentation latch, no slot, pack lookup/retry, loose-file
  absence, package open, count/budget admission, upload, payload release, and
  unrecovered fragmentation. Logging arms emit exactly one line per final
  refusal with the request identity, stage/reason, room/frame, need and allocator
  free/largest extent. The mock close clears its error, verifying that the
  diagnostic captures it before cleanup.
- Successful upload and metadata retries, resident hits, and successful loads
  emit no final-refusal line. Publication remains after success, and the optional
  arena ring records the incoming key only with the fix enabled.

The fixture uses synthetic power-of-two allocations and injected package errors.
It establishes the named control-flow behavior, not a complete game or console
failure. The allocator rounds a 16-byte request to 32 bytes; the census checks
use the actual allocation size.

## Target compilation and default-off identity

Use the retained GCC 15.2.0 / binutils 2.45.1 KOS toolchain and initialized
SH4ZAM submodule. `--output` must be outside the checkout and must not exist.

```sh
python3 port/dreamcast/tools/d367/tex_arena_current_key/build_controls.py \
  --output /tmp/tex-arena-target \
  --sh4-cxx /path/to/sh-elf/bin/sh-elf-g++ \
  --kos-root /path/to/kos \
  --sdk-root port/dreamcast/game/third_party/sh4zam
```

The script reuses the existing current-public-recipe Make expander, including
ordered `rr/recipe.conf` assignments and the documented public asset fallbacks.
It archives integration base `db222fc618045fc1da2bb3c7222743f83612ed1b` into the
output directory. The complete baseline, current absent, and explicit-zero
`native_ui.cpp` preprocessing and objects must be byte-identical. Debug records
are omitted consistently so changed source line numbers do not contaminate
the comparison. Fix-only, log-only, and combined arms compile independently.
Make guards reject invalid, empty and multiword values and missing prerequisites.

The retained result is four complete-TU OFF identity comparisons, three enabled
arms, and 13 rejected Make configurations. Object-section and stack changes are:

| Arm | Executable sections | Allocated sections | Zero-fill | `load()` stack | Logging helper stack |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline / absent / zero | 81,730 B | 394,052 B | 153,375 B | 216 B | — |
| Fix only | −4 B | −4 B | 0 B change | 212 B | — |
| Log only | +472 B | +796 B | 0 B change | 220 B | 112 B |
| Both | +472 B | +796 B | 0 B change | 216 B | 112 B |

Section deltas are relative to baseline; they are not final linked-image sizes.
Stack numbers are per-function GCC reports, not whole call-chain peaks. The
logging helper and its callees add their own stack on a refusal.

The fix retains the same bounded `core_nkeys` scan, at most 16 two-word keys
(128 bytes of key-table payload). It adds no allocation, file I/O, additional
table traversal, or VRAM data store. The diagnostic separately scans allocator
bookkeeping and logs each final refusal. Warm/cold cycles, console cache costs,
and whole-frame performance have not been measured; no speed gain is claimed.

## Retained receipts

The small JSON files in `receipts/` retain source hashes, compiler/dependency
pins, case results, object/preprocessing hashes, sections, relevant stack data,
and the Make controls. Regenerate them after successful local controls:

```sh
python3 port/dreamcast/tools/d367/tex_arena_current_key/compact_receipts.py \
  --host /tmp/tex-arena-host/host-controls.json \
  --target /tmp/tex-arena-target/target-controls.json
```

No objects, archived baseline tree, absolute output-tree command dumps, or game
assets belong in Git. Complete release linking, image identity, private-asset
memory pressure, same-route visual checks, and physical-console acceptance
remain owner gates.

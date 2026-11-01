# Qualified church puzzle fallback

`R117_FX_QUALIFIED_FALLBACK=1` repairs the interaction between the r117 puzzle
replacement and the Essential effect filter. Its default is **0**. It requires
`FX_TRIM=1` and `PS2_FX_ADDITIONS=1`; this change does not enable it in a recipe.

## Failure and scope

`Ps2fxPuzzleDraw` already qualifies the complete red, green and blue source
groups, then submits each replacement color atomically. A refused batch does
not set that color's success bit, so `Ps2fxPuzzleSuppress` leaves its GC copies
available. Essential subsequently cuts those room-owned texture-`0xff` copies.
This can remove both representations even when an individual source sprite
could still draw.

The setting records a failed color only after a **nonempty, fully qualified
replacement batch returns failure**. It reuses the existing frame, effect-pool
pointer and `TrailEvidence` identity and records the validated live room
generation. Only exact matching source copies of that failed color may pass
Essential, including the optional `ESP_SETUP_LEAN` early predicate.

The matcher checks the existing source signature: r117, streak mode, effect ID,
owner/kind, texture, starting color/size, tool/lifetime/motion fields, call/core
identity, parent, model and model serial. A successful replacement color always
takes precedence. Successful empty or culled batches still suppress their source
copies, so the change does not add a second draw. A new Prepare clears the failed
mask and generation; the match also rejects a changed frame, pool or live room
generation. Consuming the pending render ticket still prevents duplicate render
calls from revoking a completed decision.

This is a narrow draw fallback. Missing, malformed, incomplete or duplicated
qualification metadata does not receive an exemption. An invalid replacement
texture descriptor or viewport rejected before batch submission also receives
no exemption. Replacement texture **residency** failure after qualification is
covered. Ordinary source visibility, texture admission, native sprite cap, queue
capacity and spill behavior remain in force. A full sprite budget, absent source
texture or exhausted queue can still prevent a fallback from drawing.

The bug is conditional, not exclusive to hardware. Hardware may encounter the
relevant residency or capacity conditions differently, but a slow successful
read alone is not proof of this trigger. No affected private room assets or
console symptoms are claimed to have been reproduced here.

## Checks

Baseline: `db222fc618045fc1da2bb3c7222743f83612ed1b`.
The compact results and source hashes are in `verification.json`.

| Check | Result |
| --- | --- |
| Complete `esp_sub.cpp` preprocessing and SH4 object, knob absent and explicit zero | 12 byte-identity comparisons passed across FX3/lean0, FX3/lean1 and FX0/lean1 |
| Enabled SH4 compile | All three profiles passed |
| Church setting + `FX_R200_ENTRY_CAP=1` + `ESP_SETUP_LEAN=1` | Actual `esp_sub` and `native_ui` Make-derived target TUs compiled |
| Actual-source host semantics | Eight off/on × early-filter off/on × r200 off/on arms passed with ASan and UBSan |
| Make validation | 13 cases passed, including empty, multiword, wildcard, invalid numeric values and missing dependencies |
| Actual C++ feature guard | Native enabled; PPC and non-game guard controls disabled; no PowerPC compile/run claim |

The semantic fixture extracts the complete production puzzle discovery/draw and
Prepare/render ticket functions, source match/suppression, both Essential
predicates, `FxTrimSprite`, native atomic batch and scalar sprite admission.
It checks missing replacement residency, partial sprite/queue capacity, lazy
24 KiB spill acquisition by the ordinary scalar path, full-capacity boundaries,
source texture absence, success with no double draw, mixed successful/failed
colors, same-frame retry, invisible/cull-only success, incomplete/duplicate
qualification, unrelated identities, model serial change, same-frame pool
reuse/rebind, room generation and frame changes, skipped/stale tickets and
runtime Essential/streak toggles. Refused batches are asserted to emit no
packets, reserve no nodes and perform no partial draw. Source pool bytes remain
unchanged by qualification and replacement.

The host fixture controls model/pool field layout, texture residency, matrix
arithmetic, packet encoding and transport. It validates control flow and
admission, not target floating-point output, a full engine frame, gameplay
STRICT traces or a rendered image. Its r200 arm uses the real selector's
`OtherRoom` result for r117; the complete target compile also includes the
unchanged production r200 wiring.

Target controls reuse the established `esp_setup_lean` Make expander and pinned
KOS declaration overlay. Their recipe reader derives `RELEASE_KNOBS` from the
default selection in `build-public.sh`: currently
`port/dreamcast/tools/d367/test24/release-knobs.txt`. It combines the inherited
R21 profile, that selected release and every ordered literal `CH2` assignment
in the current rr recipe. The selected release path/hash and ordered CH2
assignments are recorded in each profile receipt. Private generated character
headers use the documented `build-public` fallbacks. These are complete
translation-unit checks, not a linked release disc or KOS patch/link acceptance.

## Measured size and known cost

SH4 GCC 15.2.0, pinned KOS 804b319 headers, Make-derived public profiles:

| Profile | Executable bytes added | Total allocated object-section bytes added | Zero-fill state added | Common sprite worker stack, before → after |
| --- | ---: | ---: | ---: | ---: |
| FX3, `ESP_SETUP_LEAN=0` | 368 | 376 | 8 | 408 → 424 B |
| FX3, `ESP_SETUP_LEAN=1` | 360 | 368 | 8 | 404 → 404 B |
| FX0, `ESP_SETUP_LEAN=1` | 360 | 368 | 8 | 404 → 404 B |

The new state is two unsigned words: failed-color mask and generation. No new
allocator, reserved heap/VRAM block, queue arena, source pointer or DMA path is
introduced.
The compiler reports 16 B for the shared source matcher and, when emitted as a
separate function, 32 B for the fallback predicate. Existing puzzle-draw and
stage-one render frames remain 1,064 B and 284 B respectively. The common worker
is `EspCommonTrans.part.0`; GCC's `.su` file labels this clone `0(cEsp*)`.
These are individual compiler frame sizes, not complete call-chain peaks or a
system-memory squeeze result.

Only a matching failed source reaches the added room-generation query. With the
early filter enabled, both the early and late predicates can make that query.
Accepted fallback sprites use the existing scalar queue and texture paths, so
they can add ordinary sprite traffic, load source textures and acquire the
existing lazy spill. Peak dynamic memory and texture traffic are unmeasured.
The number and cost of recovered sprites depend on the live scene. There is no
measured millisecond gain, physical bus-traffic measurement, Flycast capture,
Dreamcast run, visual acceptance, full STRICT trace or KOS squeeze result for
this setting. Those remain the gates before recipe enablement.

## Reproduce

Run from the repository root; choose fresh output directories. The SDK paths
are read-only inputs. No assets are downloaded and no generated build products
are written into the source tree.

```sh
python3 port/dreamcast/tools/d367/r117_fx_fallback/build_controls.py \
  --output /tmp/r117-target \
  --sh4-cxx /path/to/sh-elf/bin/sh-elf-g++ \
  --kos-root /path/to/kos \
  --sdk-root /path/to/sh4zam

python3 port/dreamcast/tools/d367/r117_fx_fallback/check_runtime.py \
  --output /tmp/r117-host

python3 port/dreamcast/tools/d367/r117_fx_fallback/check_make.py \
  --profile /tmp/r117-target/fx3-lean0-profile/esp-profile.json \
  --output /tmp/r117-make
```

Expected final results are 12 disabled identity comparisons, eight host arms
with `status: PASS`, and 13 Make cases plus three native feature guards. Each
script retains its detailed commands/logs and JSON receipt under its output
directory. The host checks need `g++` with AddressSanitizer and
UndefinedBehaviorSanitizer; the target checks need Python 3.12+, Git and Make.

# Texture arena identity and final refusal diagnostics

Base: `t15/int` at `db222fc618045fc1da2bb3c7222743f83612ed1b`.

## Change

`native_ui.cpp::load()` used `slot->key` to select the VRAM room arena. The slot
has already been closed at that point, but its old key is retained until the
new package succeeds. A new core texture could therefore receive room placement,
and a room texture reusing a core slot could receive core placement. The arena
was enabled in Test 23, making this a specific candidate for the Test 22–24
console regression. It is a code defect; this change alone does not establish
that it caused every reported missing object.

`TEX_ARENA_CURRENT_KEY=1` classifies using the incoming, validated local `key`.
The existing arena scope covers the upload and its retries. Publication of
`slot->key` still happens only after success. The optional arena crash ring also
records the incoming CRC instead of the prior occupant's CRC. The existing
`VRAM_ROOM_ARENA_NO_TOP` allocator policy is left in charge of class 2 placement.

## Controls

Both new Make variables default to `0`. Their enabled definitions affect only
`platform/native_ui.o`.

| Control | Purpose | Requirements |
| --- | --- | --- |
| `TEX_ARENA_CURRENT_KEY=1` | Correct arena selection and optional ring identity | `VRAM_ROOM_ARENA=1 VRAM_PAGES=1 UI_VRAM=1` |
| `TEX_FINAL_REFUSAL_LOG=1` | Emit one line per final `load()` refusal | `VRAM_PAGES=1 UI_VRAM=1` |

The diagnostic is independent of the fix so the same refusal logging can be
used on both A/B arms. No release recipe is enabled by this branch. Use the
normal integration build recipe with these assignments appended:

```text
TEX_ARENA_CURRENT_KEY=1 TEX_FINAL_REFUSAL_LOG=1
```

## Refusal log

```text
TEX-REFUSE r=117 f=1234 k=12345678-90abcdef kv=1 s=upload why=PVR texture allocation failed wh=256x256 fmt=6 need=18432 free=32768 max=8192
```

This line illustrates the format; it is not a console measurement.

The fields identify room (`r`), native UI frame (`f`), incoming texture CRC/FNV
(`k`), whether a key was available (`kv`), failing stage (`s`), reason (`why`),
source image dimensions/format, requested package bytes (`need`), free VRAM and
the largest free extent (`max`). `need=0` means no package size was available;
the early budget guard reports its minimum encoded-size estimate instead.
`kv=0` is reserved for an invalid descriptor or failed identity lookup, where
the key is explicitly zero and no old slot key is reported.

Every terminal path is covered: invalid input, identity failure, effect
residency guard, budget, remembered missing key, fragmentation latch, exhausted
slots, pack lookup error, pack payload retry delay, missing loose package, and
final package open/upload/payload-release failure. The package error is consumed
before `close()` clears it. Successful cache hits, successful loads and
recovered intermediate retries do not emit a refusal line. Repeated refusals
are intentionally not sampled or deduplicated.

The longest formatted line is 215 bytes including its newline with all unsigned
fields at their maximum and the reason capped at 56 characters, within the
existing 256-byte logger buffer. Logging and the allocator census have a cost;
enable this diagnostic for short reproduction runs and retain the log promptly
because a persistent missing texture can fill the bounded RAM log.

## Verification and target cost

The source-based host matrix passed 108 case executions under UBSan across ten
variants. It extracts the production classifier, complete `load()` and logging
helper, and runs the actual page allocator with controlled package/filesystem
substitutes. Coverage includes fresh/recycled slot keys, core pin disabled,
`VRAM_ROOM_ARENA_NO_TOP`, 17 terminal refusal cases, metadata/upload recovery,
cache hits, publication and the optional ring's incoming key.

In the synthetic 1 MiB arena, room retirement leaves 896 KiB free in both arms.
The old classification splits it into 448 KiB extents and refuses a 512 KiB
request; corrected classification retains one 896 KiB extent and admits it.
This demonstrates the fragmentation consequence without claiming a measured
console room result.

The current public recipe was expanded through Make, including the ordered
`rr/recipe.conf` appends and public asset stand-ins. The complete SH-4
`native_ui.cpp` translation unit was preprocessed and compiled against the
pinned GCC 15.2.0/binutils 2.45.1/KOS/SH4ZAM toolchain. Base, absent controls and
explicit zero controls have identical `.ii` and `.o` bytes (four comparisons).
Fix-only, log-only and combined arms compile. Thirteen Make invalid-value and
missing-prerequisite cases are rejected.

| Arm | Executable section delta | Allocated section delta | BSS delta | `load()` local stack frame |
| --- | ---: | ---: | ---: | ---: |
| Base / absent / zero | 0 B | 0 B | 0 B | 216 B |
| Fix only | -4 B | -4 B | 0 B | 212 B |
| Refusal log only | +472 B | +796 B | 0 B | 220 B |
| Fix and refusal log | +472 B | +796 B | 0 B | 216 B |

The diagnostic helper has a 112-byte local stack frame; callee frames are not
included in these figures. The fix retains the bounded core-key scan and adds
no allocation, file I/O, texture bytes or VRAM stores. Timing, warm/cold cache
cycles and whole-frame performance have not been measured. Target compilation
uses consistent debug-free controls; it is not a full game link or whole-image
identity test. Reproduction tools and compact receipts are in
`tools/d367/tex_arena_current_key/`; the test-suite entry is
`tests/test_tex_arena_current_key.py`.

## Console acceptance

Use the same data pack, room, camera and route for both arms. First compare
`TEX_ARENA_CURRENT_KEY=0` and `=1` with `TEX_FINAL_REFUSAL_LOG=1` in both. Match
missing scenery/windows/effects to the texture key and frame in `TEX-REFUSE`.
Test a room transition as well as the first room load, because reusing a slot
with a different prior key is central to this bug. After diagnosis, disable
the refusal log when measuring game speed. Actual console visibility, GDEMU
timing and whole-game memory gates remain owner-side acceptance checks.

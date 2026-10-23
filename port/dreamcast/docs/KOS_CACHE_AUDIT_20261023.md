# KOS whole-cache writeback audit — 2026-10-23

Base: RE4 `ea969bb241f77291d2ca43d706c9dc2d1226ee76`, KOS
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`. New switch: **`KOS_CACHE_P2=0`**
by default. The shared KOS checkout and accepted build recipes are unchanged.

## Finding and its limit

**The pinned KOS whole-cache writeback violates the SH7750 cache-array access
rules when entered from the normal cached P1 image. The arena crash's cause is
still unproved.** The implementation in KOS `arch/cache.h:163–179` switches at
**`count >= 65560`**, then performs 512 read/modify/write operations on
`0xf4000008 + i*32`. Compiled SH-4 code contains that loop directly in its caller;
there is no P2 transition or interrupt exclusion. This is a concrete SDK defect,
not evidence that a particular arena call caused the reported corruption.

The primary reference is Renesas, [SH7750/SH7750S/SH7750R Group User's Manual:
Hardware, R01UH0456EJ0702 Rev.7.02](https://www.renesas.com/en/document/mah/sh7750-sh7750s-sh7750r-group-users-manual-hardware?r=1055161):

- **SH7750/SH7750S §4.5, printed p.131** (PDF page 183): memory-mapped cache
  accesses must execute in P2; use longwords, write zero to reserved bits, and
  execute at least eight instructions after the array MOV before returning to
  cached regions. The manual does not guarantee operation otherwise.
- **§4.5.3, pp.133–134**: array index bits are `[13:5]`, unaffected by OIX/ORA.
  Bit 3 selects associative access. A non-associative write writes back a dirty,
  valid old entry before replacing its tag/U/V. The original `& ~2` also preserves
  undefined reserved read bits, and its associative address unnecessarily depends
  on address translation when the MMU is enabled.
- **§4.3.6, p.123**: in SH7750/S OC RAM mode, entries 128–255 and 384–511 belong
  to cache RAM. These are the Dreamcast-relevant rules, not the separate SH7750R
  mapping later in the same manual.

A cache-tag-shaped bad word is consistent with the suspected route but does not
identify its producer. Proving arena causation still needs the console A/B and a
call/length or fault trace. This audit has no new game-data or hardware run.

## Repair

[`kos-804b319-cache-p2.patch`](../patches/kos-804b319-cache-p2.patch) redirects only
whole-cache writeback to a 116-byte assembly leaf. The existing range threshold
and short-range `ocbwb` loop remain unchanged. The helper:

1. Enters its P2 alias with a PC-relative target, then saves the complete SR and
   blocks interrupts without changing the caller's register bank.
2. Reads CCR. With ORA clear it visits 512 entries; with ORA set it visits only
   entries 0–127 and 256–383. OIX does not change this physical array walk.
3. Uses **non-associative** `0xf4000000` addresses and mask **`0x1ffffc01`** to
   retain physical tag/V, clear U, and zero all reserved bits. It never writes
   cache data or changes CCR and uses no stack.
4. Executes eight explicit NOPs after the sweep before restoring the saved SR and
   returning. No interrupt can replace a tag between its read and write.

[`game/kos_cache_p2.mk`](../game/kos_cache_p2.mk) follows the existing KOS_DISC_FIX
build-local override approach. It verifies the KOS commit, exact hashes of eight
inputs, and the current source API-token census; copies/patches into OBJDIR; and
recompiles **all four pinned KOS inline users**, not just the port wrappers.
The five replacement objects precede `libkallisti.a`. A prelink check requires
their real strong symbols and the helper reference, preventing a missing helper
from entering generated-stub handling. That check is order-only, so validation
does not force relinking an otherwise current image.

The source census includes ordinary calls, address-taking and macro aliases after
comments/strings are removed. It runs again before linking, including when the
prepared output already exists. It checks the pinned source tree; it is not a
promise about arbitrary token-pasting, unscanned foreign libraries or future
binary-only code. Unsupported source changes fail clearly.

## Caller coverage

The reproducible [token inventory](../tools/d367/kos_cache_audit/callers.json)
records paths, lines, expressions and source hashes: 125 repository references
and 50 KOS references, including declarations/definitions. It is a source census,
not a runtime call graph. The recovered `src/game` contains **52 DCFlush/DCStore
calls**, all routed through `platform/misc.cpp:19–22` in this port.

| Port / recovered-game family | Range and threshold assessment |
|---|---|
| `modules.cpp:616,815`; `subscreen_backing.cpp:743` | Overlay image sizes / code-sync byte count. Can cross 65560; actual loaded sizes need assets or a trace. The following instruction-cache synchronization is retained. |
| `main_sub.cpp:390,391`, `ScreenReSize` (2 calls) | Fixed `0x8C000` = 573440 bytes: definitely above the threshold when executed. |
| `block.cpp` (1); `datactrl.cpp` (3) | Package/member sizes; data-dependent and potentially large. |
| `dvd.cpp` (5) | Whole MemorySwap writes use the whole size and can be large. Ordinary `0x10000` = 65536-byte transfer chunks are **below** 65560. Other transfer lengths require their caller's bound. |
| `Espgen42.cpp` (9), `Espgen43.cpp` (5), `espgen45.cpp` (9) | Grid positions, normals, bump/height buffers and display lists. Data-dependent; existing feature switches remove some calls. Source count does not mean all execute in Test 22. |
| `trans.cpp` (5) | Primitive ranges and `nVtx*6` / `nNrm*6`; the latter cross at 10927 entries. No asset maximum established here. |
| `sofdec.cpp` (3) | Texture plane/ARGB sizes; data-dependent. The port's movie route can bypass this recovered decoder. |
| `card.cpp` (4) | `SAVE_SIZE=0xEAFC` and `SYS_SIZE=0x1E7C` are below threshold; the variable-length read path needs its caller's bound. |
| `dbmodule.cpp` (4), `snd_main.cpp` (1), `eff_sys.cpp` (1) | Fixed small buffers: below threshold. |

The preserved PowerPC `src/lib` cache callers are also inventoried. Current
`SDK_UNITS` are `mtx mtxvec mtx44 vec quat OSAlloc`; those recovered OS/card/AX/AR
implementations are not compiled into the SH-4 port. Their source presence is
not an additional active KOS route.

KOS has **five inline calls in exactly four C files**:

| KOS boundary / indirect chain | Can select whole-cache writeback? |
|---|---|
| `kernel/exec.c:45,58` | Image `length` can be large; the copied execution trampoline is small. `arch_exec` is a separate SDK API, not RE4's overlay loader; no direct port call was found. |
| `hardware/dmac.c:86`, `dma_map_src` | Cacheable P0/P1/P3 sources and arbitrary `len`. Covers all downstream PVR/SCI DMA clients below. |
| `pvr_dma_transfer` → `dma_map_src`; `pvr_txr_load_dma`, `pvr_dma_load_ta`, `pvr_dma_yuv_conv`; texture-image DMA and the internal TA DMA callback | Variable transfer lengths can cross. Current port PVR parameters leave `dma_enabled` zero, and no direct port DMA call was found: library coverage, **not an established arena route**. |
| `sci_dma_write_data`; `sci_spi_dma_write_data` → `dma_map_src`, including SD/W5500 users | Serial lengths can be large. SPI is limited by its configured buffer size, not a universal sub-threshold constant. Normal sector/frame operations are small. |
| `hardware/g1ata.c:895`, `g1_ata_write_lba_dma`; block-device adapter at line 1191 | `count*512`; **129 sectors** cross, 128 do not. Filesystem/block-device callbacks can reach it without a direct port call. |
| `hardware/network/broadband_adapter.c:628`, `bba_tx_dma` | Normal Ethernet frames are below threshold. This public path does not itself universally cap `len`, so an oversized invalid request is not statically impossible. |

Deprecated `dcache_flush_range/all` aliases also route to writeback. Direct
`dcache_wback_all` would always use the helper; no extra direct users exist in the
pinned census. Existing `CACHE_LINEWISE` covers the three port TUs and thus the
many recovered SDK callers, but does not replace KOS's inlined copies.

## Verification and cost

The checked-in [verification receipt](../tools/d367/kos_cache_audit/verification.json)
contains source/object/preprocessor hashes, the Make-derived Test 22 public
profile and asset-related overrides, section totals and stack deltas.

| Check | Result |
|---|---|
| Three complete port TUs × original Make / absent / 0 / 1 × CACHE_LINEWISE 0/1 | **24 compiles pass.** Absent/0 Make command arrays, `-E -P` text and whole raw objects equal the base. With CACHE_LINEWISE=1, enabled objects also equal that baseline. |
| Four complete KOS TUs × original header / patched header absent / 0 / 1 | **16 compiles pass.** Absent/0 preprocessed text and raw objects equal; enabled objects reference the real helper. |
| Actual Make-derived `-H` include traces | Patched `arch/cache.h` selected in all seven TUs. The pinned environment's `-isystem` paths cannot outrank the overlay's `-I`; a forced include also fails if the patched header was not selected. |
| Threshold probes, `-O2` and `-Os` | 11 lengths including 65536, 65559 and 65560 pass. Short-path code/resolved relocations match; only the large arm calls the helper. |
| Linked helper opcode-contract model | **384 cases** across three link addresses, ORA/OIX 0/1, four SR states and eight tag seeds pass. Checks array entry coverage, P2, IRQ mask, reserved bits, tag/V/data preservation, SR and callee-saved registers. Three P1-mutated negative controls fail as intended. |
| Archive precedence | Relocatable target link with all four original objects in a synthetic archive pulls none of those members; the helper resolves to its real definition. |
| Prelink gate with Python optimization enabled | Good objects pass; a missing real helper fails even under `python -O`. |

No complete `libkallisti.a` or release image was available, so the archive check
is deliberately partial. Debug records were omitted for raw-object identity.
Asset-bearing actor toggles are disabled exactly as recorded by the shared
public-profile derivation; no private world or actor data is needed by these TUs.

Executable bytes before linking, with CACHE_LINEWISE=0:

| TU | Base | Enabled | Delta |
|---|---:|---:|---:|
| misc | 520 | 488 | −32 |
| modules | 4032 | 4000 | −32 |
| subscreen_backing | 5456 | 5456 | 0 |
| KOS dmac | 884 | 884 | 0 |
| KOS g1ata | 7456 | 7460 | +4 |
| KOS broadband_adapter | 6004 | 5984 | −20 |
| KOS exec | 292 | 268 | −24 |
| New helper | 0 | 116 | +116 |
| Sum | 24644 | 24656 | **+12** |

Allocated-section totals also grow by 12 bytes across these objects; BSS is
unchanged. This is **not linked-image size**: section retention and alignment
still matter. Compiler stack changes are +4 bytes in each of the four SDK cache
wrappers, +8 in `re4dc_ssb_code_sync`, +8 in `dma_map_src_dst`, and −4 in `bba_rtx`.
The helper itself needs zero stack; other measured functions are unchanged.

The actual helper instruction stream executes 3105 instructions / 512 array
loads / 512 array stores with ORA clear, or 1576 / 256 / 256 with ORA set. These
are instruction/access counts, **not cycles or a frame-time estimate**. It blocks
interrupts while draining dirty cache lines; hardware bus and writeback latency
must be measured. No frame-rate benefit or arena cure is claimed.

## Use and reproduce

Append `KOS_CACHE_P2=1` to the existing public Test 22 Make recipe and use a fresh
OBJDIR for each arm. The normal pinned SDK remains untouched:

| CACHE_LINEWISE | KOS_CACHE_P2 | Behavior |
|---:|---:|---|
| 0 | 0 | Original SDK and port behavior |
| 1 | 0 | Existing port-only linewise workaround |
| 0 | 1 | Repaired whole-cache path in the port and all four KOS users |
| 1 | 1 | Existing game linewise objects, plus repaired KOS users |

From the repository root, set `AUDIT_KOS`, `AUDIT_CXX`, `AUDIT_SDK` and an unused
`AUDIT_OUT` to the local pinned SDK/compiler/header/output paths, then run:

```bash
AUDIT_TOOLS=port/dreamcast/tools/d367/kos_cache_audit
python3 "$AUDIT_TOOLS/verify.py" --kos-root "$AUDIT_KOS" \
  --sh4-cxx "$AUDIT_CXX" --sdk-root "$AUDIT_SDK" --output "$AUDIT_OUT/compile"
AUDIT_PREFIX=${AUDIT_CXX%g++}
python3 "$AUDIT_TOOLS/check_helper.py" --prefix "$AUDIT_PREFIX" \
  --object "$AUDIT_OUT/compile/profile/obj/koscache-p2/cache_p2.o" --output "$AUDIT_OUT/helper"
python3 "$AUDIT_TOOLS/check_thresholds.py" --prefix "$AUDIT_PREFIX" \
  --kos-root "$AUDIT_KOS" --prepared "$AUDIT_OUT/compile/profile/obj/koscache-p2" \
  --output "$AUDIT_OUT/thresholds"
python3 "$AUDIT_TOOLS/inventory.py" --kos-root "$AUDIT_KOS" --output "$AUDIT_OUT/callers.json"
```

The verification tools use assertions: run them with ordinary Python, without
`-O` or `PYTHONOPTIMIZE`. The production preparation and symbol gates use explicit
errors. The baseline commit is pinned in `verify.py`, so rerunning after this
branch's commit still compares against the original Makefile.

### Alternative: full isolated KOS rebuild

For SDK integration testing, the patch also supports a complete rebuild. This
is an **alternative** to the port-local overlay; the overlay intentionally rejects
an already patched KOS header. Create a new SDK worktree, never patch the shared
accepted one. From the RE4 root, with unused `AUDIT_KOS_FIXED`:

```bash
git -C "$AUDIT_KOS" worktree add --detach "$AUDIT_KOS_FIXED" 804b3195ebd1a06a27cc2b3a5eacf7a2429040a3
git -C "$AUDIT_KOS_FIXED" apply --check "$PWD/port/dreamcast/patches/kos-804b319-cache-p2.patch"
git -C "$AUDIT_KOS_FIXED" apply "$PWD/port/dreamcast/patches/kos-804b319-cache-p2.patch"
```

Apply any independently required presentation or other SDK patches to this
isolated tree **before** compiling it, then run:

```bash
export RE4DC_KOS_BASE="$AUDIT_KOS_FIXED"
source port/dreamcast/kos-env.sh
make -C "$KOS_BASE" KOS_CACHE_P2=1 -j4
```

The command-line switch propagates recursively; the patched root Makefile
also exports it and adds `-DKOS_CACHE_P2=1` to KOS_CFLAGS. Rebuild consumers with
that C/C++ macro too, because the range API is inline. For this full-SDK route,
leave the **port Make overlay switch at 0** and add the macro to its compiler flags
(for example `KOS_CFLAGS="$KOS_CFLAGS -DKOS_CACHE_P2=1"`). Verify the SDK archive
defines `_arch_dcache_wback_all_p2` before linking. This full rebuild was not run
in the current environment.

## Separate finding left out of this fix

`arch_dcache_purge_all` has a different large-range threshold, 39936 bytes. Under
`-Os` it also writes the address array from cached code and uses associative
addresses with zero tags; ordinary RAM tags will not match that intended sweep.
Its `-O2` implementation instead uses an eviction buffer. This needs its own
scoped review and controls. `KOS_CACHE_P2` repairs writeback only, not purge or
invalidate. Existing `icache_sync_range` assembly already uses P2 and interrupt
exclusion and is not changed.

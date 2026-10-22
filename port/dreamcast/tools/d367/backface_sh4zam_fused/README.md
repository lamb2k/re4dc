# Reproducible SH4ZAM strip API: first architecture milestone

This unit moves the complete current cull/run/parity/SQ algorithm into a local
patch against the public SDK pin33fa4850. It is **not the fused speed change**.
The source call graph is now:

    RE4 material/clip adapter -> shz_strip_walk_sq / shz_strip_sq
                              -> patched SDK outcodes + assembly cull/run/SQ

The RE4 world adapter passes its count stream, outcodes, cache, limit, cull and
counters. It contains no outcode loop, classification, run selection, parity or
SQ copy. Actor strip and bit7-EOL whole-stream adapters use the same SDK API.
Material/model eligibility and continuation into RE4's existing clipper stay
with RE4. The original CPU1 template remains unchanged.

`0001-strip-sq-api.patch` contains a C-compatible public header, the complete
qualified assembly, generated exact FMAC arithmetic, world caller, and SDK
CMake integration. The API's render policy drops end back runs and inner runs
of at least3 triangles; it preserves exact vertex words and parity, actor flag
synthesis, world ordinary flags, EOL and all callee/FPSCR/opposite-bank state.
Optional committed-span tracing is configured with generic `SHZ_STRIP_TRACE`
and `SHZ_STRIP_TRACE_CALLBACK`; RE4 supplies its existing hash callback symbol.

`materialize.py` verifies clean SDK pin, patch identity and every resulting
source/header. It writes a new owned overlay, or verifies an existing one.
It never edits the vendor checkout/gitlink, fetches a private commit or contacts
upstream. A changed patch needs a fresh OBJDIR/overlay. CPU2 Make rules compile
these actual overlay sources, rather than a renamed game-owned walker. CPU0/C1
add no objects or include paths. The arithmetic generator still checks the real
pinned SDK primitive lowering before CPU2 builds.

Run `bash qualify.sh /absolute/new/output` from this directory. The script
acquires the shared slot2 and per-tree lease for small compiles, then releases
them before opcode interpretation. It refuses an existing output directory.
`materialize_test.py` exercises repeatability and fail-closed controls in fresh
temporary directories. No game data or guest build is used.

Boundary02 actual objects pass4,220 kernel comparisons plus32 mode controls,
and696 complete SDK caller comparisons plus32 mode controls. The caller cases
cover sizes0..255, all/any sign bytes, depth/screen decision order, clip-stop
pointer, exact limit boundaries, batched streams, exact emitted words and
additive counters. Actor caller extraction confirms strip/whole dispatch and
material exclusions. Evidence JSONs bind objects, linked caller, source and
patch identities. Later CMake-only patch addition leaves all runtime source
hashes and compiled byte bodies unchanged.

Independent MODELLED caller-inclusive64-index costs are2,971 cycles all-front,
3,635 all-back and3,815 mixed, versus1,141 for the whole OFF world walk. These
include SDK scan, setup, calls, kernel, counters and return, but not the thin
RE4 adapter. The first-stage SDK boundary **fails** performance acceptance.
No performance, full-build OFF identity, Flycast pixels, memory or console
acceptance is claimed. Root's frozen0f022 source remains separate.

Next implementation is inside this SDK patch: fuse short-strip outcodes and
exact facing, six ABC/parity phases,64-bit mask and lean emission; keep a single
register lease across batches. The qualified SDK assembly remains the long/
exceptional path. See FUSED-NEXT.md for the register and mask plan.

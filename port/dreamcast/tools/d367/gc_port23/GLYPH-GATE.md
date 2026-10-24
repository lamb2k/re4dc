# Glyph upload and accepted-use diagnostic boundary

This adds diagnostic coverage, not a font/menu/HUD asset swap. No source .fnt
allocation or borrowing behavior changes. Stage font storage is also borrowed
as subscreen scratch, so a MessageFont pointer cannot supply a lasting immutable
source proof without additional pre-overwrite ownership hooks.

The bounded boundary here is the actual local upload payload: glyph_cell's
512B decoded/twiddled tile, and glyph_bank's16 exact ARGB8888 palette words
(64B). The same local palette array supplies the actual PVR writes. Identity
hashes only these local buffers, not arbitrary source-font pointers or guessed
allocation extents. Each receives kind/id/full SHA checked catalog identity.
Decode/upload preparation emits nothing. Texture identity does not establish
origin: local conversion of a GC font remains GC/unknown. Catalog derivation
must use pinned reviewed original inputs; ambiguous/shared converted payloads
cannot be upgraded to PS2 from byte equality alone. No guest failure generates
new allowances.

Each uploaded cell and palette carries a monotonic version. Queued GlyphQuad
copies the original cell and palette versions. At actual strip flush, the
diagnostic verifies the exact cell index, bank, cell version and palette
version. A source-font scratch overwrite cannot relabel unchanged uploaded
VRAM, while cell reuse or palette overwrite invalidates stale queued proofs.
Catalog replacement independently invalidates saved checked tokens.

The non-Entry packet route is qualified only during that exact accepted glyph
submission: exact packet pointer, byte extent, actual atlas address, Font
consumer and all original cell/palette versions. It is not a permanent atlas
range exemption. The TA observer handles every textured vertex for this scoped
packet, including same-scene bare-vertex batches after an earlier header.
After successful observation the scope ends, then unlocked emission logs the
actual tile and palette for Font, Texture and Ui. Discarded packets, wrong
pointer/extent/address, nested scope or stale versions fail explicitly.

Palette ownership also matters. The normal TEX_PAL4_ALPHA allocator reserves
the first8 banks for glyphs in actual UI initialization. Legacy TREE_IMPOSTOR
without that ownership allocator is unqualified: accepted glyph matching fails
rather than assuming another package cannot overwrite the glyph palette.

Source-extracted host controls compile actual palette conversion/upload,
glyph-cell cache/decode, source glyph queue, accepted observer and strip-run
flush. Forty glyphs cross three packet batches, including carried bare vertices;
only accepted upload identities emit. Negative controls cover cell/palette
reuse, wrong packet pointer/address, discarded sends and atlas use without the
exact scope. The payloads remain unknown in these tests.

Expected metadata cost before target pricing: GlyphQuad grows8B (384 entries,
3072B), GlyphCell grows12B (64/128 entries,768/1536B), palette banks grow8B
(64B), plus small gated serial/context globals and16 borrowed quad pointers on
the flush stack. The actual target layout/link/heap and full OFF image gates
remain open. No complete I-001 gate follows from this bounded unit; reviewed
font payload seed, remaining consumers and room checkpoints still need work.

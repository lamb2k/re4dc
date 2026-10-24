# Packed hand source and copy contract

The actual hand runtime remains unedited at the initial ticket milestone. This
document separates a tested metadata contract from the pending closed-writer
integration and independent review. No hand coverage or positive slot is claimed.

Root approved one exact full hand-container source proof captured after a
complete successful read at named startup. It must retain the exact original
blob offset/count and real selected geometry/skin/UV/palette ranges through
every CPU read, joined worker result, AICA cache write/readback and current slot
generation. A filename, blob number, destination pointer or matching count is
insufficient without the complete owned copy/lifetime chain.

gc_asset_hand_copy.h has fixed eight-byte source/generation/blob tickets. A
destination loses its positive source before overwrite. Complete success may
publish only the expected current destination generation and same original
source/blob. Failed/partial reads, stale source epochs, wrong blobs, overwritten
destinations, invalidation and counter exhaustion cannot produce positives.
Twenty-four blob values fit five token bits; generation is bounded to 27 bits
and fails closed on exhaustion. The helper neither hashes, reads files/catalogs,
logs, allocates nor waits. It does not itself prove a source read or copy.

The current actual writer inventory in coarse_actor_leon_hands.inc is:

- load_now/read_at writes a static CPU slot from a complete synchronous read;
- job_main writes only its private job buffer; job_poll joins before using it,
  then copies into a slot under LH when that side still wants the blob;
- cache is the only AICA cell writer, under LH; load reads back into a slot;
- yield holds LH, joins/frees the worker, invalidates cells and frees the AICA
  allocation before movie/bank use; CPU slots survive;
- directory publishes rows/blobs/sources once; controlled actor FE/LOD/bake
  preparation may derive a new stream in the same slot after original capture.

The actual pinned KOS implementations used by these calls are synchronous
programmed 32-bit G2 loops, not the separate DMA API. spu_memread waits for prior
FIFO writes before copying, then returns after the full CPU readback. The root
provider paths and SHA256s are:

- /root/work/kos-re4dc-d367/kernel/arch/dreamcast/hardware/spu.c:
  b5765c65041166105ca6c56ecfd52e968f023904f5f3c791006525e3174b73f2
- /root/work/kos-re4dc-d367/kernel/arch/dreamcast/hardware/g2bus.c:
  d4ae2e484f367dd84bd8e66b7dac888531b29a9e1d0bae6880f4c162b9186082

Final provider selection still needs the target map. Closed source-buffer alias
ownership, directory/source epoch, actual completion ordering, every invalidation
and permitted in-place derivation remain integration/review obligations. Any
unaccounted writer or copy must leave the slot unknown. No transformed-byte
hash is required when the complete original-source/controlled-derivation proof
holds. No 6.4 KiB snapshot, per-blob digest cache or new lent allocation is added.

The next helper milestone adds safe startup registration of two stable child
PayloadProof records (44 bytes each on SH4, not yet target measured). Registration
alone has no positive serial. Silent invalidation precedes a slot overwrite;
silent publication inherits only a still-live whole-source serial and current
catalog epoch, with a fresh child serial. The source record must outlive both
children. These fixed metadata operations never bind/read a catalog, hash, log,
flush or allocate. They are not proof that an actual copy completed.

Accepted uses of the same original source retain their coalesced bookkeeping
when a slot is invalidated or republished. A changed source with pending uses
fails explicitly rather than relabeling those uses. Saved child serials reject
same-address reloads, invalid publication revokes any old positive, and source
retirement or catalog replacement invalidates the child. The focused controls
exercise those cases with the real core/helper and assert logging remains
outside the simulated LH/SQ lock. Actual hand copy/derivation integration and
source-handle/directory authentication remain pending.

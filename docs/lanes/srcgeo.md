# srcgeo (lane, 2026-11-17)

Branch lane/srcgeo from lane/island-gca 76d5194b7 (merged 7831dec83). Goal: no GameCube model data read by the native cast on Disc 2 and
Disc 3 (user rule "no GameCube assets"; animation counts too).

## What the cast reads from a source BIN (finding)
- `actor_lifetime.inc re4dc_actor_archive_adopt` digests the archive entry (little-endian BIN, first `normalized.bytes` bytes) against a
  registry SBlob row (package `sblob` section, or the ELF base rows `actor_material_records.inc source_blobs`, family 2 = em11..em17 ARC
  0x1bc..0x1e4). `info()` then proves the 10 ModelData header words and, per part, the 13 material bytes, display-list bytes and polygon
  count (`fmodel` / `fpart` package rows). Positions / normals / weights / UV are digested only by the diagnostic entry.
- The cast DRAWS the package's own PS2 geometry. The BIN is identity + skeleton + material facts. So a package can name a PS2-derived BIN
  (GC-format ModelData with PS2 positions / normals / UV / triangles, `ps2_objects.rebuild`, the form `ps2_ganado_bins.py` writes) and the
  cast binds to it unchanged. No engine change was needed.
- Correction to the island-gca note: the island rows 49a59e4e / bca0ef6a / 7cd6b16c / cf12842d / 2b516e6e / c00b2198 (em1d/e/f ARC
  0x25f..0x279: accessories, props) are NOT cast-bound (no SBlob row names them); `ps2_ganado_bins.py` had simply never run over the island
  archives. The cast-bound BINs (soldier bodies / heads, 0x22b..0x24d) are not judge rows (the package covers their draw); they were kept GC
  only for the digest. pl01 / pl05 / pl11 rows (Ashley, r30c r30f r311 r315 r333) are partner GC draws (no island partner package: CH-FIXES-CARRY row 30).
  The remaining island / castle unknown + gc model rows are st2 / st3 room objects (ETM props / room BINs).

## Switch and data
- `D3_SRCGEO=1` (Disc 3) / `D2_SRCGEO=1` (Disc 2) in rr/recipe.conf: default empty = off. They add data sets `srcgeo` / `srcgeo2`
  (t11-fix.py; stores /root/re4data/private/srcgeo-20261117, srcgeo2-20261117) as the LAST set of D3_DATA / D2_DATA.
- Store = em archives rebuilt with NO cast keep (only BINs a compiled base row digests stay GC) + every room registry / partner package
  re-rowed by `ps2cast/src_blob_patch.py` (fmodel / fpart / sblob rows recomputed with model_registry.bin_facts on the rebuilt BIN; self-check:
  the GC BIN reproduces the package's existing row exactly; layout, geometry, textures and skeleton byte-identical; payload + header crc refreshed).
- Regenerate: `srcgeo/gen.sh <2|3> <out>` (inputs = `srcgeo/chain.py`, the disc's FINAL files: content tree + D?_DATA chain, Disc 1 overlay for
  Disc 2); verify: `ps2cast/srcgeo_verify.py <store>` simulates adoption (ok_new / ok_gc / CLASH / external; CLASH must be 0).
  Regenerate whenever a later D?_DATA set stages an em archive or package the store carries.
- `gc_port23/provenance.py`: a store may carry a `FOLLOW_BYTES` marker (rows the set did not change keep the previous owner's verdict) and
  `${VAR:+,set}` in D2_DATA / D3_DATA is read from the environment.

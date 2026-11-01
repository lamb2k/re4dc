# purge-pics25 provenance rows (lane purge-pics25, 2026-10-25)

The 11 "GameCube picture key in tex.pak" GC-ASSET allowlist rows are 6 keys, all PS2 pictures. The catalog's
provenance.py marks them gc because the last data set that changed their bytes (pak17: loose -> pack, v101: 16-bit ->
VQ) has no RECIPE naming a PS2 source. Neither set changes the picture's origin.

`provenance-pak17.tsv` / `provenance-v101.tsv` are provenance.py `provenance.tsv` rows (output_sha256 = the tex.pak
member, ps2_sha256 = the PS2-side file). To apply: copy each into its store root
(/root/re4data/private/pak17-20261018/provenance.tsv, /root/re4data/private/v101-20261018/provenance.tsv), rebuild the
catalog (provenance.py + build_catalog.py --proofs) and drop the 11 rows from allowlist.json. Coordinator's call:
the stores and the catalog belong to other lanes.

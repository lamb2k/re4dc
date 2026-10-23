# Room interior visibility, lane interior-vis23

`prepare.py` pins an existing room mesh, effective physical policy, original
policy, placement IDs, conversion report and retained camera logs. It exports
the reviewed geometric proof helpers from commit
`fcf49c1dc788734799baadfe4147005f8d3338ff` to private scratch, recording their
exact hashes. It uses the historical instance order and R4PV v1 format.

Only camera-containing X/Z cells get a domain. The emitted Y interval encloses
the recorded camera heights plus an outward rounded configurable margin.
Every unsampled grid cell, out-of-Y camera, invalid package or missing runtime
receipt falls back to drawing all. PCCULL integer eyes choose domains only;
exact PS2CAM matrices are needed for selected-corner replay.

`certify.py PRIVATE` reuses continuous interval geometry proofs, replays every
clear bit from exact current source geometry, and emits the existing R4PV
format. It limits dependency panels to the runtime's current single-LOD cohort
and sixteen-panel maximum, retains the ordinary source placement prefix, and
emits a private certificate only when at least one panel has a useful proof.
An absent optional r4tc file is omitted from input hashes; no descriptor is
invented. Every adaptation and helper hash is recorded.

All outputs, package bytes, matrices, recovered coordinates and certificates
are private. Do not run these tools into a Git checkout. A successful geometry
replay is not actual runtime admission, selected transformed vertices, timing,
pixel correctness or console acceptance. Current runtime source, opacity,
numeric and emitted-prefix guards remain mandatory. No shared runtime or
recipe file is changed by these tools.

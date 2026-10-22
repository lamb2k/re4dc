# r109 consecutive strip metadata

This first visibility23 unit exposes the existing strip-group frustum rejection
before vertex transformation without repacking geometry. It adds no runtime
code or build knob. The existing converter's default behavior is unchanged.

```
python3 port/dreamcast/tools/ps2_strip_groups.py \
    original.re4mesh original.r4pw - new.r4sg --preserve-order --groups 4
```

The dash is mandatory: this mode has no mesh output. Every material/pass uses
up to four consecutive runs of original whole strips. Grid bounds and inclusive
corner ranges refer to the unchanged original corner numbers, including indexed
LOD pool reads. Empty group slots have repeated strip ends and range 1..0.
Malformed CRCs, bounds, references, strip lengths/counts and output/input aliases
are rejected. No policy CRC override or header-retag operation is provided.

For the private r109 experiment, use `qualify.py` with a fresh private output
and mirror directory:

```
python3 port/dreamcast/tools/d367/visibility23/test_metadata.py
python3 port/dreamcast/tools/d367/visibility23/qualify.py \
    --runtime-tree /root/probe/codex-backface-sh4zam \
    --output /root/re4data/private/r109-stripgroups23-20261022-v1 \
    --mirror '/mnt/c/Game Dev/Emulators/re4-assets-private/r109-stripgroups23-20261022-v1'
```

The qualifier pins the exact baseline mesh, original policy, current mip22b
scoped policy, rc19s room data, original SMD/SMX and blackps2 conversion report by SHA256. It
checks genuine R4IM/R4PW CRCs and counts, unchanged placements and non-key part
policy fields. The new sidecar binds baseline mesh CRC `d2e244fc`, size 933152,
1189 meshlets and original policy CRC `5d07de5b`. The actual scoped policy CRC
is `177cae56`; the existing exact WORLD_RECT21 certificate authenticates the
mapping. No certificate or runtime change is included. Raw origin/t15/int at
base `64a28a7b` lacks that mapping and rejects this sidecar alongside the scoped
policy; the integration must include the already qualified mapping from the
recorded runtime source. The old sc21 mesh/sidecar is incompatible.

Host qualification compiles the actual `MeshPackage::adopt` header, provenance
header/certificates, and unmodified R4PW admission block/record structures,
R4SG header predicate and `sg_select` function extracted from the supplied runtime tree. Only filesystem and
allocation glue is substituted. Source hashes identify the exact host-tested
runtime. Both original and scoped policies must accept. Header/record/size,
mesh identity and uncertified-policy mutations must reject. Stale source CRC
and invalid policy records reject before provenance, as in production.

Every original strip is independently checked for ordered, exactly-once group
coverage, exact original index min/max, real strip ends and conservative grid
bounds. Selection cases cover empty slots, shared corners, all kept/cut,
leading/trailing cuts, interior holes, near-plane crossings and the -1 slack.
The actual selector transforms one enclosing surviving `[lo, hi]` interval;
the receipt records its exact transformed count (zero when none survive).
sum of group spans is inventory data and cannot be reported as runtime work.
The pre-change converter and new default path also run on the real baseline:
mesh, sidecar, JSON report and stdout must all match byte-for-byte.

The generated private set contains only `r109/ps2-world.r4sg`, small receipts
and checksums. It intentionally has no replacement mesh, R4PW, room data, LODs
or program. It is deterministic: 4396 nonempty groups, 76128 bytes, SHA256
`f605d3cac29c6a77b54748800ab1ed536b5aebd42b4752961078268fcae5e140`.
Group-count histogram: 42 meshlets with one, 32 with two, 170 with three,
945 with four. All-level corner count 67110; sum of group spans 77642.
These are package counts, not visible-frame costs or savings.

Keep Full view, CPU backface OFF, cones/piece state/dedup OFF and all other
assets fixed for the future A/B. The arrival at (97246,2251,13320), yaw 1, is
Leon state, not a camera matrix or authenticated chapter state. Main owns the
entry camera/census, runtime integration, pixel and gameplay checks, KOS 48 KiB,
r100 s30 heap 4, world/total timing and physical-console acceptance. No new
build, guest, console, memory-fit or performance result is established here.

# r101 reconstruction authoring experiment

The current world remains the default. `tools/world_rebuild27.py` is an explicit
private authoring tool, never a production recipe or stager. The coordinator
owns integration, target measurements, route qualification and releases.

The tool uses the existing Build 11 R4IM/R4PW codec and current strip-group
generator. It does not repeat the completed Blender identity prerequisite.
Its source plan must pin geometry, material/placement policy and ownership IDs.
It supports r101 only and refuses an existing output directory.

Each retained uniquely owned scroll mesh remains exact at every source level.
The runtime admits a changing owner only for a source ID below 250 that occurs
exactly once in R4ID. Shared IDs and static IDs retain their existing ownership;
the tool never moves a feature to a different mesh, part, placement or owner.
All material keys, UV grids, prelit values and changing-object geometry stay
source-derived. No texture, actor, collision, event or sound is an output.

The named additive groups are defined in a private plan. The initial structural
floor keeps terrain, building masses and major openings. Later arms restore
landmarks and protected details. The complete-part protected control is an
upper bound, not the desired cost of retaining a fence rail or roof beam.

`--protected-pieces` maps the previous lost-part evidence to exact connected
source features by placement, part, triangle count and world bounds. An
ambiguous match retains its complete source part and is reported. It never
waives a source feature or manufactures a lost-part PASS. In partial clusters,
the selected source L0 pieces are used at every previously nonempty LOD slot;
previously empty distance slots remain empty. This can increase work relative
to a source coarse level and must be measured on the actual selected view.

`--solid-shells` is a separately named primitive authoring experiment, requiring
NumPy. It reconstructs sufficiently solid projected masses as opaque boxes or
broad planar quads. Current source texture identity remains; UV and prelit
values come from source corners. Open frames and thin/alpha pieces remain
source geometry. The initial conservative trial changed only three features
and increased encoded bytes, so it is not a performance result or an accepted
reconstruction. Projection coverage is a diagnostic, not a required fidelity
policy for future deliberate authoring.

Outputs include geometry, fresh strip groups, unchanged policy/IDs/texture
classes, the whole unchanged source room file, a candidate-specific private
provenance header, per-feature receipts, RECIPE.txt and SHA256SUMS. The room
file's original GRID/OCCL/SRCB/SCDD payloads are deliberately preserved for the
first matched comparison. A separately matched experiment is needed before
repairing inherited SCDD data. No new visibility certificate is inferred.

The private header is included only through the coordinator's default-off
WORLD_REBUILD27 route. Every header row identifies the complete physical R4PW
file and the candidate geometry's byte count/body CRC; private receipts retain
full SHA256 values. A matching tuple maps the unchanged material/placement
policy to its original source CRC. Unknown tuples keep the existing fallback.

Host admission of a generated mesh, source feature preservation, native
emulator qualification, modeled cost, physical-console timing and user look
acceptance are distinct gates. Triangle counts or package bytes establish none
of the timing gates. A sparse floor is not a complete recognizable world.

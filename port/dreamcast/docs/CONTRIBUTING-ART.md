# Contributing art to the Dreamcast port

Help us keep the PS2 models' appearance while meeting the Dreamcast's draw and
memory budgets. Start with one named character or one small world sample.
[Issue #51](https://github.com/lamb2k/re4dc/issues/51) asks for a comparison of the
full PS2 Ganados and the reduced models; it does not select a replacement or
request further reduction.

**Every contributed game asset must come from the PS2 version.** Supply your own
game data and record its version and source-file hashes. Keep extracted files,
meshes, textures, animations, generated packages, game-derived `.blend` files
and comparison captures outside Git. No game files belong in the repository or
a PR. Public contributions can contain tools, settings, hash manifests and
written results; arrange private sample and still-pair review with a maintainer.

## Agree on one sample

Identify the character appearance, model type, room and test build. Record the
actual package hash and selected detail level from the run. A label such as
`g70` is not enough to establish which appearance or package was drawn.

Ask the maintainer for the matching conversion recipe and comparison setup
before editing. Keep the full PS2 source, current reduced model and candidate
separate. Historical tools also contain GameCube and hybrid experiments; those
are not source choices for new art contributions.

## What makes a model compatible

A game package includes the relationships used by animation and drawing. Work
against the existing runtime skeleton and approved PS2-to-runtime binding:

| Keep intact | Why it matters |
|---|---|
| Joint identities, order, hierarchy and bind transforms | Existing animations, attachments and hit locations address those joints. |
| Skin weights and their joint/palette mappings | The same pose must deform the intended vertices. Renumbering bones or dropping weights can break a model that looks correct at rest. |
| Part and material roles, source identities, UV seams, alpha/depth/cull behavior | Body, head, hands, hair and transparent surfaces have different drawing and ownership rules. |
| Animation, hand-pose, gore and attachment contracts | A body reduction must still join the unchanged hands, neck, weapons and alternate parts during play. |

Keep collision, hit zones, events, game state and AI unchanged. Preserve required
normals or prelit colours, units, winding and texture mappings. The existing
packer must rebuild counts, bounds, strips and checksums and pass its admission
checks. An FBX export that looks right in Blender does not establish any of
these package contracts. Do not retarget the rig or replace the packing path
with a generic FBX round trip.

## Use the tools for their supported job

**World inspection and unchanged round trips:**
[`world_blender_roundtrip`](../tools/d367/world_blender_roundtrip/README.md) uses
**Blender 4.4.3, build `802179c51ccc`**. Its README gives the download checksum
and import/export commands. Use `--preserve-index-layout=1` on **both** actions
when retaining an existing noncanonical index layout. First export an unchanged
scene and compare every input/output file hash, retaining all companions.

This world tool is an identity check: geometry, material, topology and LOD edits
are refused. It is not a character importer or an exporter for reduced world
geometry. Report a refusal with the exact message and source hashes; do not
remove a companion or rewrite its CRC to pass.

**Ganado reduction and packing:** the existing
[`glod_rung.py`](../tools/d367/leonlod/glod_rung.py),
[`glod_native.sh`](../tools/d367/leonlod/glod_native.sh) and
[`glod_pack.py`](../tools/d367/leonlod/glod_pack.py) chain starts with the PS2 cast
store. Its reducer retains surviving PS2 vertices and their weights, keeps the
hand roles whole, and uses the existing skeleton, bind data and atlas. Packing
and host checks need the maintainer's private conversion workspace; the public
scripts alone are not a standalone character authoring kit.

The [`bl_ganado.py`](../tools/d367/leonlod/bl_ganado.py) preview script documents
Blender 5.2 and renders a shared camera with flat lighting in the bind pose.
Record its exact Blender build separately. That preview helps compare shape
and UVs; it does not verify animated deformation or in-game lighting.

## Prepare the comparison

1. Name the appearance and record source/package hashes, converter settings,
   repository commit, Blender build and selected detail level. Keep a recipe
   that reproduces the candidate from your own PS2 data.
2. Make a still pair of the **full PS2/native model and candidate** in the same
   pose, camera, distance, lighting, exposure and resolution. Include the
   current reduced model as a third view when diagnosing #51.
3. Include a whole-body view and close-ups of the face, hands, neck/wrist joins
   and UV/material seams. Check silhouette and small detached parts. Do not
   hide differences by changing framing, shading or textures between views.
4. Compare several existing animation poses, including bent elbows/knees,
   turning shoulders, hand grips and applicable alternate/gore parts. A bind
   pose still alone cannot qualify deformation.
5. Report triangles, transformed/strip vertices, draw runs, palette counts,
   package size and RAM/VRAM cost. Mark unmeasured costs as unmeasured. A smaller
   triangle count alone does not establish a faster draw.

## What the maintainer checks

The maintainer confirms that the intended package and detail level actually
draw, with no fallback, then reviews the matched stills and animation poses.
The local game runs must check joins, materials, deformation, gameplay identity,
draw time, memory and room transitions. Console appearance remains part of
acceptance. Any candidate stays separately selectable until these checks and
the look review pass; submitting a sample does not change release defaults.

See [port contribution checks](../CONTRIBUTING-PORT.md#6-send-a-patch) for the
existing runtime gates. The package's
[actor admission checks](../game/platform/include/coarse_actor_preflight.h) and
the [Ganado LOD contract](../game/ps2leon.mk) are the implementation references.

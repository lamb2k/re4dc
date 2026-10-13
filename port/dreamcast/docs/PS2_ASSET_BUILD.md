# Build PS2-derived Dreamcast world assets

`make assets` extracts local discs and runs the existing native-world converter. The
initial verified profile builds **r102 and r106** into R4IM meshes, R4PW placements,
R4ID object IDs and RE4DCTX PowerVR textures, then prepares a candidate overlay.
These are the formats the Dreamcast renderer already uses.

This is the first automated part of a full asset build. It does **not** yet rebuild
the entire game or produce a bootable disc. Keep using `contrib.sh` for a program
build on the existing test disc. Coverage and remaining work are listed below.

## Source discs

Supply your own local images. The builder does not download game data.

| Source | Identification | Use |
| --- | --- | --- |
| Resident Evil 4, PlayStation 2, USA | `SLUS_211.34`; `SYSTEM.CNF` reports `VER = 1.01`, NTSC | World geometry, placements, materials, vertex colours and textures |
| Resident Evil 4, GameCube debug Disc 1 | `G4BE08` | Existing cut-0 lighting calibration: room colour scale and lights for NORMAL groups |

The supported PS2 image is 4,435,836,928 bytes with SHA-256:

```text
eb0874cf29dc48c994fd183e52a3b186b47b0a341281a0c2db24a1f18757cb66
```

The recipe also checks the PS2 executable, `SYSTEM.CNF`, `DATA/BIO4DAT.AFS` location
and AFS index. The executable filename alone does not establish the supported
revision. A different image is rejected before conversion; do not bypass the pins
without checking the extraction and runtime output.

The supported GameCube lighting source is 1,459,978,240 bytes, SHA-256
`b7fcbf121cf7c527aae23838e9c3f0818e31115bb597eb77a2c49c9e8fa46492`.

The GameCube disc is still required by this compatibility recipe. The rendering
target remains Dreamcast-native presentation derived from PS2 assets; retaining
the accepted offline colour calibration does not add a live GameCube renderer.
The current game also retains recovered GameCube simulation code and other asset
dependencies described in [CONTRIBUTING-PORT.md](../CONTRIBUTING-PORT.md#7-a-full-disc-from-your-own-discs).

## Setup and build

Use Linux or WSL on a case-sensitive Linux filesystem. Tested with Ubuntu 24.04,
Python 3.12 and Mono 6.8. From a fresh checkout of this branch:

```sh
sudo apt-get install python3 python3-venv make mono-runtime g++ \
  gcc-powerpc-linux-gnu libc6-dev-powerpc-cross qemu-user
python3 -m venv .assets/venv
.assets/venv/bin/python -m pip install -r port/dreamcast/tools/ps2_assets/requirements.txt

export PS2_ISO='/path/to/Resident Evil 4 (USA).iso'
export GC_ISO='/path/to/Resident Evil 4 Debug (Disc 1).iso'
make assets PYTHON=.assets/venv/bin/python
```

Paths with spaces work. The first run downloads the pinned MIT-licensed JADERLINK
DATUDAS Tool V1.0.4 and PS2 Scenario SMD Tool V1.3.0 release ZIPs, verifies both
archives and executables, and retains their license/credit files in `.assets/tools`.
Further runs can reuse those files without a network connection. Python dependencies
are pinned in `tools/ps2_assets/requirements.txt`; no private helper scripts are required.

The official DATUDAS release executable differs from the maintainers' older local
build of the same source. Extraction output is checked against the retained inputs
during the compatibility audit; the workflow pins the downloadable release.

The PowerPC cross compiler and QEMU are used only by the existing **offline** YZ2
decoder when reading GameCube room lighting. `g++` builds the existing host copy of
the runtime's package checks. These dependencies do not add PowerPC or PS2 emulation
to the Dreamcast game. Missing executables are reported before reading the discs.

To build one supported room or choose an output directory:

```sh
make assets PYTHON=.assets/venv/bin/python ROOMS=r106 ASSETS_OUT=.assets/r106-review
make assets-check PYTHON=.assets/venv/bin/python
```

A successful repeat verifies the source/script fingerprint and output hashes before
reusing the result. A changed recipe, changed output or interrupted build requires a
new `ASSETS_OUT`. The builder never clears an existing output tree. Disc files and
all derived output stay out of Git.

## Outputs and integration

Under `ASSETS_OUT` (default `.assets/worlds`):

| Path | Contents |
| --- | --- |
| `manifest.json` | Source, tool, recipe, Python-version and output hashes; per-room validation |
| `inputs/rXXX` and `aux/rXXX` | Extracted inputs and ancillary room files |
| `rooms/rXXX` | Converted runtime files, source/packed texture previews, conversion report |
| `logs` and `work` | Tool logs and complete intermediate extraction |
| `stage/rooms/rXXX` and `stage/tex` | Validated candidate overlay for later disc integration |

The preflight uses the existing host runtime checker for mesh structure and sidecar
records, plus the existing texture loader rules, ID-to-sidecar binding, CRCs,
texture identity, missing references and texture-key collisions across rooms.
Reusing a build checks its complete staged inventory as well as file hashes.
Reports include mesh bytes and texture VRAM bytes; these are asset costs,
not measured frame time or complete runtime residency.

To integrate a reviewed overlay, the release owner maps its room files to
`dc/native/rXXX` and includes its textures in the release texture pack. A loose
texture copied beside a stale `tex.pak` is not proof that the disc will load it.
Use fixtures bound to the actual build's overlays, check texture loads on the actual
release disc, and run the combined gameplay, movie-memory and route gates. This
command deliberately ends at a candidate overlay and does not modify release
fixtures, test discs or SD cards.

## Compatibility and remaining coverage

The recipe retains PS2 prelighting, lights `0,5` for NORMAL groups, UV guard `0.002`,
`--vertex-alpha tr4` and `--cutout-max-alpha 224`. There is no replacement mesh or
texture format, new runtime lighting, wholesale PS2 EFF loading, or simulation change.

Fresh extraction reproduced all 155 consumed input files across r102/r106, including
both cut-0 lighting JSON files. Both meshes and every texture match the retained
converter references byte for byte, as do material records and placement-to-object
mappings. There are 118 emitted texture files: 76 in r102 and 42 in r106. r102's
77 source texture entries include two that share the same runtime key. Windows
and Linux linear algebra produce tiny differences in some fitted placement
coefficients (maximum observed difference `9.094947017729282e-13` in r102),
so the R4PW and matching R4ID checksums can differ across operating systems. Full
cross-platform binary identity is not claimed. Running the new helper set on
Windows also reproduces the retained sidecars and IDs byte for byte. Build comparisons must distinguish
that from a changed mesh, material, texture, placement mapping or visible transform.

Remaining work toward a complete `make assets` + disc build:

1. Add the remaining reviewed room recipes and comparisons. Preserve **r100 KEEP
   CURRENT** and reproduce the special r101 wrapper before enabling either here.
2. Integrate the additional chapter 2-2 worlds with that lane's code and memory gates.
3. Automate PS2 character/hand data after the active model-correctness work lands;
   keep fallback coverage explicit.
4. Bring movies, audio, UI, generated headers and the release texture-pack selection
   into the top-level recipe, reusing their existing converters.
5. Complete a fresh end-to-end disc build and an independent blind contributor
   attempt. A successful world conversion alone does not establish either.

The October 13 alignment audit used coordinator base `e6d06520`, the live Claude
session and memory, the PS2 room/effect survey, and the active worktrees. PS2 FX
option A remains render-side recipes; `PS2_FX_ROOMS` stays off by default and follows
the coordinator's post-test-9 sequence. The active ch22, issue-26 and PS2 enemy
lanes retain their ownership. The tooling branch was then rebased onto `85e7da5d`,
which includes the landed PS2 enemy work. This tooling does not land other lanes.

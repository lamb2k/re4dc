# M1 native bench

Build in the KOS environment with the private pack directory containing cross.pak and hayfork.pak.

```sh
. port/dreamcast/kos-env.sh
make -j6 -C port/dreamcast/engine/bench native OUT="$PWD/out" PRIVATE_PACK_DIR="$PRIVATE_PACK_DIR"
```

The NAT3 pack contains immutable geometry, material descriptors and 300 ticks of logic inputs. Its NWR3 section retains the whole room's indexed R4IM and group table. Cells own contiguous placement spans. Bounds, UV encoding, inverse binds, texture storage and source blend state are static. The private logic stream carries camera matrices, joint transforms, lights, effects, caster feet, widget state and message records. The loader verifies CRC, references, patch bounds and model streams. It uploads the resident textures before picture one. Both TA vertex buffers are enabled.

The packer takes the private disc directory, capture directory, hexadecimal room ID, output path and static actor table dump. Build actor_static_dump.cpp on the host with the two private generated header directories on the include path. Redirect its standard output to the static table file. The capture directory contains the contiguous LOG3 picture files, Leon's simulation inverse binds and the room's optional model identity catalogue. For the additional model assets native_extra.py follows the source ModelData, TPL and joint tables in the private relocated asset archive. It reads full-detail source streams. Private assets and generated packs stay outside Git.

```sh
python3 port/dreamcast/engine/bake/native_pack.py "$DISC/dc" "$CAPTURE" 101 "$PRIVATE_PACK_DIR/cross.pak" "$STATIC_TABLES"
```

The sample-store observer in model_profile.py takes the path to hwmodel/hwsim.c and an output directory. Set M1_TIMING to the SH-4 ELF address of timing. The optional M1_PHASE_MASK selects function counters for setup/world, characters/volumes, punch-through, translucent/hair, effects, HUD or scene finish in bits zero through six. The simulator still executes the full trace. Subtract the store in timing column six from the store in column seven to obtain the absolute drawing interval in cycles. Divide by 200,000 for milliseconds. timing's row index is zero-based. The retail image alternates rooms and repeats the 300 inputs twice at each load.

## E0 additions (lane eng-e0)

- Build: `Makefile` builds the engine image with fast math (`-mfsca -mfsrra`), `-DNDEBUG`, link-time optimisation,
  `-Os` by default and `-O2` for `render.c` and `native_world.c`. `render/stage_sh4.S` holds the world stage loop and the
  actor strip emitter; `game/platform/avk_sh4.S` supplies the skinned position kernel.
- Load-time conversion (outside the picture): per-part actor streams sorted by weight set with per-bone bounding spheres;
  per-meshlet staged vertex ranges per strip group, TA colours, signed coordinate words.
- Baked visibility: `cc -O2 -I../render bake_vis.c ../render/native_world.c -lm -o bake_vis`, then
  `bake_vis cross.pak CROSS.VIS` (and `FARM.VIS`); put the tables beside the packs on the disc. `bake_vis ... --wrong 1`
  writes the control table (one route-visible cluster instance per cell marked hidden).
- Boot options (empty files in the disc root): `NOVIS` draws the full set (pixel check), `ARMA` stages world vertices in
  operand-cache RAM (survey arm a), `ARMB` uses three short loops over 32-vertex blocks (survey arm b), `DELAY5` adds the
  5 ms busy-wait control, `STILLS` hands every picture of the first 300 to the host, `FARM1` starts in the farm.
- `host_world.c`: host replay of the world selection over a pack (per-picture meshlet, vertex and corner counts).
- `model_profile.py` treats operand-cache RAM (0x7C000000-0x7FFFFFFF) as one-cycle RAM for arm (a); run the observer with
  `--oc-kb 8` for that arm.

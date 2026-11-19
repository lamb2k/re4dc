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

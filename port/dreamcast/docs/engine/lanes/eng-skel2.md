# Lane eng-skel2: the clock fix, collision baked offline (2026-11-21)

Status: finished, unaudited. Continues lane eng-skel1 (its Part B). The clock fix is its own branch and document:
`lane/eng-clock1`, `docs/engine/lanes/eng-clock1.md` (merged here).

## Collision baked offline (the integrator's ruling of 2026-11-21, option 2)

### The baked form (`services/collision/col.h`)
Every file of a room archive's SAT and EAT tables (a table of files or one file; r109, r10c, r10f, r119, r11e and r11f
hold 5 to 12) is replaced, in the archive's place for it, by a baked file:
- the cSatFile header (0x14 B, counts as the original's; `x8` = 0xC0B2, 0 in every original file);
- `ColBakedFile` (offsets);
- the normal table, the original's bytes (the behaviour keeps pointers into it: `pFloor_norm`, hitCheck's normal);
- the ColPiece record (empty in the file) and the tables exactly as `col.cpp bake()` lays them out.
The vertex, edge, polygon and block tables are not kept. A table's header keeps its layout (its offsets point at the
baked files). Every other entry of the archive keeps its bytes.

### Room load: no bake
`cSat::init` (col_model.cpp) sees the magic: `operator=` keeps the counts and points `norm_p` at the file's table
(`vtx`, `edge_p`, `poly_p`, `block_p` are 0: nothing reads them), and `col_baked_setup()` fills the record's table
pointers from the offsets. The pieces live in the room archive (KOS heap) and go with it; `col_room_release()` drops
them from the list; `col_bake_all()` lists a baked piece again without a bake. Pieces made from other data (a door's quad
in play) are still baked when made, into the room carve. Memory line: `E1 SVCMEM collision pieces .. | baked in the room
archive N B, set up N, baked at load 0`.

### The bake step and its receipt (`hostref/svc/colbake.sh`)
`colbake.sh <tree> <out>` bakes every st1 room archive with the engine's own bake (col.cpp, run by the native PC build,
`svc/colb_host.cpp` RE4_COLB_BAKE). `<out>/COLB-RECEIPT.txt`: SHA-256 of the input archives, of colbake.sh,
colb_host.cpp, colb_verify.py, col.cpp, col.h, col_model.cpp and the native re4ref, and of every output.
`colbake.sh --verify <tree> <out>` (colb_verify.py): the receipt against inputs, tools and outputs; each output against
its input: the same entries and bytes but SAT / EAT; each baked file's header the original's but x8, its normal table
the original's bytes, the record empty, its tables' FNV-1a hash the one the bake printed. All 28 st1 rooms: 1.4 s, every
check holds. Control: an output or a tool changed after the receipt fails the verify.

### The PC reference
The native PC builds bake the room's SAT / EAT at room load into the baked form (`host_room_post`, called from
host_glue.cpp's `host_load_room`; the baked files go to a PC area at 0x8F000000, which col_model.cpp's arena check
admits on the PC only) and set the pieces up from it, as the console does. Each file's `oNorm` points back into the
archive's own normal table there, so every pointer the behaviour keeps is the reference's and the dumps compare as before.
`RE4_COLB=0`: the load-time bake as before (the comparison arm). The tables are the same bytes as the console's files
(r101: tables af68a5e3 / 45ae5ee7 both ways).

### The map entry (`col_map_floor`)
The sub screen's map position (src/Sscrn/ss_map.cpp mapPositionCheck, 1262-1340) builds a cSat on the room's SAT file 0
and walks its floor and slope polygons; that needs the vertex and polygon tables the baked form drops. The entry answers
from the baked floor group: the lowest hit of the vertical line through the point (the later polygon on a tie), its
polygon number, hit point and three vertices. Check `hostref/svc/colmap_check.sh`: mapPositionCheck's search loop (the
same lines as ss_map.cpp, checked) with the original At_poly_line_ck on the unbaked file against the entry, at every
point of five fixtures' paths and a 48 x 48 grid, SEck 0 and 1: 0 mismatches (e1-route 3,382 points, door103-walk 2,998,
hill-ashley 4,102, bell-ganado 3,251, square-follow 2,918); control (v[1] and v[2] swapped) fails every hit. Request for
the items / inventory lane: when the sub screen is hosted, mapPositionCheck's room part calls this entry.

### Memory (main RAM map, host/e1_engine.h)
- Services region 1 MB -> 512 KB (0x8cf40000-0x8cfc0000): skeleton pool 262,144 + cloth pool 34,816 (+ SVCPROF 64,512)
  + the room carve for pieces made in play.
- The room archive is bigger in the KOS heap (default image's resident CAM SAT EAT CNS RTP): r101 349,248 -> 517,760
  (+168,512), r11d (hill) 199,232 -> 300,480 (+101,248). With the arena where it was, the hill scene ran 28,672 B over
  (its weapon not drawn). So the behaviour arena moved up 512 KB with the region (default 0x8cc80000-0x8cf40000, fight
  0x8ce00000-0x8cf40000, same sizes): the KOS heap's ceiling is 512 KB higher.

# Existing finer-cell representation, before any geometry search

The unchanged R4PV1 header stores a finite positive float `cell`. The real
`pvs23::layout` accepts smaller positive sizes; there is no 2 m lower bound.
`pvs::frame` divides the selected eye offset by that same scalar, then uses the
cell's unchanged signed-decimetre Y band. Missing/outside cells keep drawing.
This supports finer XZ quantization as a format property, not table admission.

Actual source locations in the frozen owned renderer are native_static.cpp
lines 4975 (header), 5008 (allocation), 5078-5090 (cell selection), and 3012-3015
(cluster-instance target bits). The matching pvs23_format.hpp layout function
requires at most 65,536 grid cells and exact set extent. The loader additionally
caps the whole padded file at 262,144 B. Certificates bind the exact file and
still require all material, source, numeric, clipping and committed receipts.

`cell_layout_checks.py` extracts the real Head and allocation expression and
includes the actual layout header. All 26 host assertions pass under UBSan:

| Grid over the old 44 by 50 m rectangle | Padded bytes with one set | Actual size gate |
| --- | ---: | --- |
| 2 m, 22 by 25 | 4,512 | accepts |
| 500 mm, 88 by 100 | 70,528 | accepts |
| 250 mm, 176 by 200 | 281,728 | refuses |
| Local 250 mm, 128 by 128 (32 m window) | 131,200 | accepts |
| Local one-cell 500 or 250 mm | 128 | accepts |

The current room's placement/part offset storage adds 1,056 B. More distinct
visibility sets add 40 B each before alignment. These are lower-bound one-set
examples, not a proposed runtime allocation. No table or data option was made.
A 250 mm global room grid cannot fit the current loader even with just one set;
a local grid/window can represent it, retaining draw-all outside that window.
A future geometry experiment must record its exact serialized float origin and
size, outward actual selector preimage, authentic matrix-derived eye, unchanged
Y limits and fallback extent. A centered mathematical box alone does not prove
that the actual float selector accepts exactly that box.

The bounded refusal counts remain heuristic. In the ideal predicate, a target
on the same side of the plane as an already uniformly one-sided eye box cannot
be rescued by shrinking only that eye box. Eye-plane crossings may improve
when an authentic eye selects one side. Edge failures may improve because a
smaller whole eye product narrows the shadow-cone requirement. This is why the
same closest source/target pairs are useful next; it is not a reason to keep
increasing the source sample. Current cells have 2 m XZ extent and 600-1400 mm Y
extent. The closest two sampled one-LOD triangles span about 894 by 999 by 391 mm
in world axes, while their best-ranked target box spans 660 by 355 by 864 mm.
These sizes give scale; they are not a proof that all such pairs are impossible.

The next conditional host-only experiment, after independent prototype review,
will retain the frozen source512 and existing target namespace. It will test
only the closest opposite-plane pairs in 500 mm then 250 mm complete domains
centered on authenticated captured matrix eyes, retaining the old cell Y band.
No point-eye inference, new PVS, format/runtime change or gain claim is allowed.
If this nominal bounded check still has no useful candidates, the next research
question is exact coplanar opaque triangle unions or convex patches, without a
watertight-house requirement. Such unions need a separate complete coverage
proof and unchanged source receipts; they are not admitted by this note.

Renderer cuts remain zero. MODELLED ms is unavailable; the >=1 ms GO is not
established. The historic e9bf7 camera profile and current fb254 source policy
remain separately identified. No SDK, guest, media, recipe, converter, actor
or shared source work is part of this unit.

# Actual selected world census — source7a3af776

Both dedicated R-n captures passed frozen source `census.py` with complete passes0/1/2, contiguous flushes and complete part attempts at frame1200, threshold1200. Expected rooms0x101/0x100, pinned original b1/s2 fixtures, cap4 recipe and runtime standard lod_px5 were verified. FAR_LOD4 gives effective scenery tolerance20. All programme/14overlay and base track03 hashes were checked before launch. Both40s requests completed in41.188s;55s guard did not fire.

| Actual one-frame quantity | b1 r101 cross | s2 r100 forest |
|---|---:|---:|
| Queued placement/part rows (distinct pairs) |90|50|
| Zero-pick part rows |9|14|
| Complete flushes |3|3|
| Selected meshlets |334|185|
| Plain / indexed meshlets |309 /25|183 /2|
| Indexed fraction of meshlets |7.485%|1.081%|
| Full plain / indexed vertices |17213 /1148|10452 /39|
| Full selected vertices |18361|10491|
| Indexed fraction of full vertices |6.252%|0.372%|
| Whole / nonempty partial / nr0 picks |111 /162 /61|185 /0 /0|
| Whole / partial / nr0 fraction |33.234% /48.503% /18.263%|100% /0% /0%|
| Contiguous transform-input span before dedup |11020|10491|
| Span / full selected vertices |60.019%|100%|
| Indexed nr0 picks / full vertices |3 /188|0 /0|
| Indexed nr0 fraction of indexed picks |12%|0%|
| Indexed nr0 vertices / full indexed vertices |16.376%|0%|
| Indexed nr0 vertices / all full selected vertices |1.024%|0%|
| Bad ranges/index counts |0|0|

b1 queues: pass0 flush1 has48parts/160picks; pass0 flush2 has35/163; pass1 flush3 has7/11. Pass2 closes successfully with no flush. s2 queues: pass0 has46/169; pass1 has3/13; pass2 has1/3. Zero-pick rows remain represented.

`pv/iv` count full selected vertex_count; `span` is full for whole sentinel0xff, hi-lo+1 for nonempty partial, zero fornr0. These are different populations. In the current DEDUP0 profile, span identifies the selected contiguous transform-input extent before dedup. It is not an accepted-corner/output counter. The188 indexed nr0 vertices show the limited population where the emitter may omit an unused indexed gather; they are not188 measured saved vertices, transformed vertices or a speed result. Binding/borrowing/priming remain. The forest frame has no indexed-nr0 applicability.

Evidence root: `C:\Flycast-Evidence\re4-dreamcast\world-emit23-takeover\7a3af776\runtime-support`. Raw logs and full parsed rows in `R-n-b1-q1` and `R-n-s2-q1`; source parser hash, exact raw log hashes, fractions and per-flush counts in `census-summary.json`. Programme/profile/base/fixture/source receipts are in `launch-receipts`. Diagnostic census is separate from all timing runs.

This supplies actual selection applicability for two individual frames. It does not establish accepted geometry, renderer pixel equivalence, measured gather/transform savings, runtime gates, physical-console speed, or recipe admission.
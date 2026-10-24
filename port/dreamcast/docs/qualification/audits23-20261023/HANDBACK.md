# Bounded cache diagnostic handback

Clean/pushed source **5e4de9a0262d3629c9833c959557de198b2e9f0c**, branch wip/audits23-20261023, tree /root/work/lanes/audits23. Integration a5e972e4 is merged without rewriting. The default-off diagnostic is separate from all four audit fixes; no recipe enables it.

KOS_CACHE_P2_DIAG=1 requires KOS_CACHE_P2=1. Generated helper instrumentation counts every whole writeback and reads pinned TMU2 directly under the original mask. It rejects underflow/reversed/stopped/reconfigured clocks, preserves full/RAM mode coverage and reports overflow. Aligned P2 counters are updated after the original sweep. Room lifecycle/checkpoint APIs publish complete counter intervals outside the helper; boot/transition remain unknown. The first observer snapshot coheres two dirty startup BSS cache lines exactly once, preserving any prior helper counts.

Timing is raw ticks for an observed masked subinterval, with quantization and included/excluded observer work documented. No complete IRQ-latency, frequency, duration, performance or console claim yet. Default-off helper bytes, source guards and object-list controls pass; target object/image equivalence and actual linked helper/SDK caller coverage remain root qualification gates.

Ten RAM groups pass: actual generated ASM-source execution (modes/addresses/SR/ranges), clock positive/negative cases, overflow/carry, P1/unmasked/cached-alias/early-counter/UNF mutations, actual C++ snapshot/logger and cold/warm startup coherence with missing-flush mutation, timer pin rejection, actual build-local preparation, exact0/1 Make guards and source-OFF identity. Command: PYTHONDONTWRITEBYTECODE=1 python3 port/dreamcast/tools/d367/kos_cache_audit/test_cache_diag.py.

HOST-CONTROLS-FINAL.json pins sources and /dev/shm/audits23-final-host-rb_mv0jr/host-controls.log. Original6a/merged2ea and coherence59 receipts are preserved. Independent source review SEALED CLEAR at final 5e; REVIEW-CACHE-DIAG.md and its JSON/logs preserve the independent receipt. Target qualification remains open. ui_bridge claim was released to GC after6a and was not reclaimed by either repair. No SDK/target/guest/build work performed by this author.


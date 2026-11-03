#!/usr/bin/env python3
"""roomscan report: one markdown table over a batch of rooms (PREDICTED world ms per view, base = shipped package scanned
without a plan, plan = the planned package), with mesh bytes and heap 4 headroom.
  report.py <plans dir> <heap tsv: room heap4_free_bytes> <sizes tsv: room shipped_bytes plan_bytes> [rooms...]"""
import json, os, sys
d, heap_tsv, size_tsv = sys.argv[1:4]
rooms = sys.argv[4:]
heap = dict(l.split()[:2] for l in open(heap_tsv) if l.strip())
size = {l.split()[0]: l.split()[1:3] for l in open(size_tsv) if l.strip()}
print('| room | world ms mean base -> plan | worst view base -> plan | world budget | cells changed / total | mesh bytes | heap 4 free after |')
print('|---|---|---|---|---|---|---|')
for r in rooms:
    b = json.load(open(os.path.join(d, r + '-base.json')))['summary']
    p = json.load(open(os.path.join(d, r + '-plan.json')))
    s = p['summary']
    sb, pb = (int(x) for x in size.get(r, (0, 0)))
    hf = int(heap.get(r, 0)) - (pb - sb)
    print('| %s | %.2f -> %.2f | %.2f -> %.2f | %.1f | %d / %d | %+d KB | %d KB |' % (
        r, b['mean_before'], s['mean_after'], b['worst_before'], s['worst_after'], p['budget_world_ms'],
        s['cells_decimated'], p['cells'], (pb - sb) // 1024, hf // 1024))

#!/usr/bin/env python3
"""Require byte-exact model output parity and independent charge conservation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True, help='original output prefix')
    p.add_argument('--profile', type=Path, required=True, help='profiled output prefix')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    results = {}
    for suffix in ('frames.tsv', 'pcs.tsv', 'lines.tsv', 'sum.txt'):
        x = Path(str(a.original) + '.' + suffix).read_bytes()
        y = Path(str(a.profile) + '.' + suffix).read_bytes()
        results[suffix] = dict(equal=x == y, sha256=hashlib.sha256(x).hexdigest())
        assert x == y, f'Model output changed: {suffix}'
    rows = list(csv.DictReader(Path(str(a.profile) + '.context_audit.tsv').open(), delimiter='\t'))
    assert rows
    for row in rows:
        assert row['node_self16'] == row['flat_self16'] == row['charged16'], row
    model_rows = list(csv.DictReader(Path(str(a.profile) + '.frames.tsv').open(), delimiter='\t'))
    assert len(rows) == len(model_rows)
    assert [r['trace'] for r in rows] == [r['trace'] for r in model_rows]
    # Serialized per-PC costs have two-decimal rounding. Bound that loss independently.
    pcs = list(csv.DictReader(Path(str(a.profile) + '.pcs.tsv').open(), delimiter='\t'))
    cats = ('base', 'dep_load', 'dep_fpu', 'dep_fdiv', 'dep_other', 'flock', 'branch', 'imiss', 'dmiss', 'pfwait', 'sq', 'uncached')
    serialized_cycles = sum(float(r[c]) for r in pcs for c in cats)
    exact_cycles = sum(int(r['charged16']) for r in rows) / 16
    bound = len(pcs) * len(cats) * .005 + .001
    assert abs(serialized_cycles - exact_cycles) <= bound, (serialized_cycles, exact_cycles, bound)
    report = dict(status='PASS', outputs=results, samples=len(rows), charged_cycles=exact_cycles,
                  serialized_pc_cycles=serialized_cycles, serialization_rounding_bound=bound,
                  limitation='Parity validates unchanged timing and disjoint charge conservation, not recovered caller completeness.')
    a.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()

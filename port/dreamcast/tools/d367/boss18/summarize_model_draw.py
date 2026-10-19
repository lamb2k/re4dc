#!/usr/bin/env python3
"""Price disjoint self charges under model-witnessed draw invocations.

Run only after unchanged timing/context parity passes. The result prices native
commonModelTrans presentation, not AI, preparation or separate auxiliary actors.
Incomplete roots and witnesses without proven ancestry never become total costs.
"""
import argparse
import csv
import hashlib
import json
from array import array
from collections import Counter, defaultdict
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(profile, witness_dir, ticks):
    proof = json.loads((witness_dir/'build-proof.json').read_text())
    if sha(profile/'runtime.elf') != proof['runtime_elf_sha256'] or sha(profile/'runtime-symbols.json') != proof['symbols_sha256']:
        raise ValueError('Witness/runtime symbol identity differs')
    validation = json.loads((witness_dir/'validation.json').read_text())
    if validation['status'] != 'PASS' or validation['samples'] != len(ticks):
        raise ValueError('Unchanged timing/conservation or sample count not verified')
    # Identical contexts also prove that observation changes no caller ownership.
    for name in ('contexts.tsv', 'function_frames.tsv'):
        if sha(profile/('profile/nominal.'+name)) != sha(witness_dir/('nominal.'+name)):
            raise ValueError('Observation changes context attribution')
    symbols = json.loads((profile/'runtime-symbols.json').read_text())['symbols']
    names = {s['symbol']:s['name'] for s in symbols}
    names[0] = 'UNKNOWN'
    models = {r['model']:r['name'] for r in proof['models']}
    roots = {}
    unresolved = []
    total_witnesses = 0
    with (witness_dir/'model-witnesses.tsv').open() as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            total_witnesses += 1
            sample, node, root, tx = (int(row[k]) for k in ('sample','node','common_root','tx_root'))
            model = row['model']
            if model not in models or not 0 <= sample < len(ticks) or int(row['pc'],16) != proof['accessor_pc'] or int(row['address'],16) != int(model,16)+proof['id_offset'] or int(row['size']) != 1:
                raise ValueError('Witness differs from pinned source accessor/model')
            if root == 0xffffffff or tx == 0xffffffff:
                unresolved.append(row)
                continue
            key = sample, root
            value = model, tx
            if key in roots and roots[key] != value:
                raise ValueError('One draw root has conflicting model ownership')
            roots[key] = value
    charges, irq = Counter(), Counter()
    functions = defaultdict(Counter)
    found = {}
    last = None
    with (witness_dir/'nominal.contexts.tsv').open() as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            sample,node,parent,symbol,kind,owner,complete,invalid,self16,inc16 = map(int,row.values())
            if sample != last:
                inherited = array('i')
                last = sample
            if node != len(inherited) or not 0 <= sample < len(ticks):
                raise ValueError('Context nodes/sample order differs')
            key = sample,node
            root = node if key in roots else (inherited[parent] if parent < node else -1)
            inherited.append(root)
            if key in roots:
                if names[symbol] != 'commonModelTrans':
                    raise ValueError('Witness root is not source model presentation')
                model,tx = roots[key]
                found[key] = dict(sample=sample,tick=ticks[sample],node=node,model=model,transaction_node=tx,complete=complete,invalid=invalid,inclusive16=inc16)
            if root >= 0:
                key = sample,root
                if owner == 5:
                    irq[key] += self16
                else:
                    charges[key] += self16
                    functions[key][names[symbol]] += self16
    if not roots or roots.keys() != found.keys():
        raise ValueError('A witnessed source invocation is absent from contexts')
    factor = 16*200000  # cycles16, SH-4 200 MHz, milliseconds.
    results = {}
    all_qualified = []
    for model,name in models.items():
        rows = []
        for key,r in found.items():
            if r['model'] != model:
                continue
            if charges[key]+irq[key] != r['inclusive16']:
                raise ValueError('Disjoint root charges fail inclusive conservation')
            rows.append(dict(r,exclusive_draw_without_IRQ_ms=charges[key]/factor,excluded_IRQ_ms=irq[key]/factor))
        by_sample = defaultdict(list)
        for r in rows:
            by_sample[r['sample']].append(r)
        unresolved_samples = {int(r['sample']) for r in unresolved if r['model'] == model}
        qualified = {i:sum(r['exclusive_draw_without_IRQ_ms'] for r in v) for i,v in by_sample.items()
                     if i not in unresolved_samples and all(r['complete'] and not r['invalid'] for r in v)}
        all_qualified.append(qualified)
        results[model] = dict(descriptor=name,observed_invocations=len(rows),complete_noninvalid_invocations=sum(bool(r['complete'] and not r['invalid']) for r in rows),rows=rows,qualified_samples=qualified,unresolved_ancestry_samples=sorted(unresolved_samples))
    common = sorted(set.intersection(*(set(q) for q in all_qualified)))
    for result,qualified in zip(results.values(),all_qualified):
        values = [qualified[i] for i in common]
        result['jointly_complete_ms_per_sample'] = sum(values)/len(values) if values else None
    return dict(scope='MODELLED disjoint exclusive self charges below exact model-witnessed commonModelTrans roots; IRQ excluded. Native presentation only. Separate auxiliary actors, preparation and logic outside these roots unpriced. No aggregate cost divided by actors.',ticks=ticks,samples=len(ticks),source_witnesses=total_witnesses,unresolved_witnesses=unresolved,jointly_complete_samples=common,jointly_complete_ticks=[ticks[i] for i in common],results=results,input_sha256={str(p):sha(p) for p in (witness_dir/'build-proof.json',witness_dir/'model-witnesses.tsv',witness_dir/'nominal.contexts.tsv',witness_dir/'validation.json')},schedule='Costs are per captured sample; a separate exact-build schedule proof is required to label them per logic tick or picture. At steady30 every tick is drawn.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--witness-dir',type=Path,required=True)
    parser.add_argument('--ticks',required=True,help='Ordered source ticks, one per replayed trace')
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Output already exists')
    result = summarize(args.profile,args.witness_dir,list(map(int,args.ticks.split(','))))
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v['jointly_complete_ms_per_sample'] for k,v in result['results'].items()},indent=2))
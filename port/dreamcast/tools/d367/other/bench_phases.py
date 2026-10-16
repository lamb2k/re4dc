#!/usr/bin/env python3
"""Account nonoverlapping function self costs inside OTHER_PROFILE phases.

Nominal diagnostic-model costs only. The phase definitions follow the historical
benchmark; no projection ratio or historical console number is used to scale them.
"""
import argparse, collections, csv, hashlib, json, subprocess
from pathlib import Path
import account

PHASES = {0:'logic',1:'actor preparation',2:'actor draw',3:'world draw',
          4:'OTHER',5:'wait tail',6:'instrumentation'}
DENOM = 16 * 200000

def read(path):
    with path.open() as f: return list(csv.DictReader(f,delimiter='\t'))

def write(path,rows,fields):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fields,delimiter='\t');w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True,type=Path)
    p.add_argument('--replay',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--addr2line',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-addr2line')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    groups={int(r['sample_index']):r['group'] for r in read(a.replay/'trace_groups.tsv')}
    counts=collections.Counter(groups.values())
    if set(counts)!={'drawn_image','dropped_image'}: raise ValueError(counts)
    states=read(a.replay/'cg.bench_state_frames.tsv')
    if len(states)!=len(groups): raise ValueError('Missing benchmark state rows')
    for r in states:
        if int(r['final_phase'])!=4:
            raise ValueError(f'Trace must end in OTHER before next phase0: {r}')
        if any(int(r[k]) for k in ('instrumentation_depth','actor_depth','errors')):
            raise ValueError(f'Unbalanced ownership markers: {r}')
        if any(int(r[k])!=1 for k in ('phase0','phase5')):
            raise ValueError(f'Trace must contain one logic phase and one wait-tail phase: {r}')
        if r['instr_begin']!=r['instr_end'] or r['push_actor']!=r['pop_actor']:
            raise ValueError(f'Unbalanced event counts: {r}')
    expected=collections.Counter({(int(r['frame']),r['entry']):int(r['self_cycles_16'])
              for r in read(a.replay/'cg.function_frames.tsv')})
    observed=collections.Counter(); functions=collections.Counter(); sums=collections.Counter()
    for r in read(a.replay/'cg.bench_function_frames.tsv'):
        i,ph,entry,cycles=int(r['frame']),int(r['phase']),r['entry'],int(r['self_cycles_16'])
        observed[(i,entry)]+=cycles
        functions[(groups[i],ph,entry)]+=cycles;sums[(groups[i],ph)]+=cycles
    if observed!=expected: raise ValueError('Benchmark phases do not exactly partition function charges')
    symbols={'00000000':'<unknown code>'}
    for line in (a.replay/'cg.syms.txt').read_text().splitlines():
        addr,kind,name=line.split(None,2);symbols[addr]=name
    entries=sorted({key[2] for key in functions})
    located=subprocess.check_output([a.addr2line,'-e',str(a.evidence/'re4dc-game.elf')],
                                    input='\n'.join(entries)+'\n',text=True).splitlines()
    if len(located)!=len(entries): raise ValueError('addr2line row mismatch')
    files=dict(zip(entries,located))
    classify=account.classifier(Path(__file__).resolve().parents[1]/'benchmark/bench-split.py')
    funrows=[]; cats=collections.Counter()
    for (group,ph,entry),cycles in functions.items():
        fn=symbols[entry];file=files[entry].rsplit(':',1)[0]
        category=classify(fn,file);ms=cycles/DENOM/counts[group]
        funrows.append(dict(group=group,phase=ph,phase_name=PHASES[ph],entry=entry,func=fn,
                            source=files[entry],category=category,nominal_self_ms=ms))
        cats[(group,ph,category)]+=ms
    # A forced draw/drop pair mean is a sum of separate sample-group means.
    # It is not one measured adjacent picture or a console measurement.
    pair=collections.Counter();paircat=collections.Counter()
    for r in funrows: pair[(r['phase'],r['entry'])]+=r['nominal_self_ms']
    for (group,ph,cat),ms in cats.items(): paircat[(ph,cat)]+=ms
    other=[]
    for (ph,entry),ms in pair.items():
        if ph==4: other.append(dict(entry=entry,func=symbols[entry],source=files[entry],
                          category=classify(symbols[entry],files[entry].rsplit(':',1)[0]),nominal_self_ms=ms))
    other.sort(key=lambda r:r['nominal_self_ms'],reverse=True)
    funrows.sort(key=lambda r:(r['group'],r['phase'],-r['nominal_self_ms']))
    write(a.out/'functions.tsv',funrows,('group','phase','phase_name','entry','func','source','category','nominal_self_ms'))
    write(a.out/'other_pair_functions.tsv',other,('entry','func','source','category','nominal_self_ms'))
    catrows=[dict(group=g,phase=ph,phase_name=PHASES[ph],category=c,nominal_self_ms=ms)
             for (g,ph,c),ms in cats.items()]
    catrows.sort(key=lambda r:(r['group'],r['phase'],-r['nominal_self_ms']))
    write(a.out/'categories.tsv',catrows,('group','phase','phase_name','category','nominal_self_ms'))
    group_summary={g:{PHASES[ph]:sums[(g,ph)]/DENOM/n for ph in PHASES} for g,n in counts.items()}
    pair_summary={PHASES[ph]:sum(sums[(g,ph)]/DENOM/n for g,n in counts.items()) for ph in PHASES}
    # Check the frame totals independently of the function partition.
    frames=read(a.replay/'cgsim.frames.tsv');delta=[]
    for i,row in enumerate(frames):
        ms=sum(v for (frame,entry),v in expected.items() if frame==i)/DENOM
        delta.append(ms-float(row['cycles'])/200000)
    if max(map(abs,delta))>1e-7: raise ValueError('Function costs do not reconcile with model frames')
    result=dict(status='PASS',evidence=str(a.evidence),replay=str(a.replay),samples=len(groups),groups=dict(counts),
        elf_sha256=hashlib.sha256((a.evidence/'re4dc-game.elf').read_bytes()).hexdigest(),
        definition_source='76f40d95 src/game/{main,trans}.cpp and port/dreamcast/game/coarse.cpp BENCH_PH / EmMgr snapshot',
        units='nominal instrumented model milliseconds; means within sampled forced image groups',
        reconciliation=dict(all_function_phase_charges_exact=True,all_marker_stacks_balanced=True,all_final_phases_OTHER=True,
                            maximum_frame_delta_ms=max(map(abs,delta))),
        group_phase_means_ms=group_summary,forced_pair_sum_of_separate_means_ms=pair_summary,
        other_pair_categories=[dict(category=c,nominal_self_ms=ms) for (ph,c),ms in
                               sorted(paircat.items(),key=lambda r:-r[1]) if ph==4],
        other_pair_top_functions=other[:40],
        limitations=['This is not the historical 15.8 ms console result or a production speedup.',
            'Instrumentation includes marker PCs and bracketed snapshots/membership work; incidental register, stack, cache and layout perturbations remain.',
            'Interrupts and other KOS threads retain the phase they interrupt, as in the console phase timer.',
            'Forced-pair means combine different sampled iterations, not adjacent captured physical pairs.',
            'Nominal phase costs are not scaled with a whole-frame console projection ratio.'])
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','groups','group_phase_means_ms','forced_pair_sum_of_separate_means_ms','reconciliation')},indent=2))

if __name__=='__main__':main()

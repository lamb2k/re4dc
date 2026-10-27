"""Compare the one authorized B1 LIVE_MASK arm with retained B1 OFF evidence."""
import ast
from collections import Counter
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

root=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-rebuild27-20261027')
private=Path('/root/re4data/private/world-rebuild27-20261027')
helper=Path('/root/work/lanes/world-rebuild27-model/port/dreamcast/tools/d367/benchmark/bench-split.py')
spec=importlib.util.spec_from_file_location('bench',helper);bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_stage=private/'model-stage-v1-B1';new_stage=private/'model-stage-maskon-v1-B1'
x=json.loads((old_stage/'preparation.json').read_text())['data_manifest'];y=json.loads((new_stage/'preparation.json').read_text())['data_manifest']
assert x.keys()==y.keys()
data_diffs={k:dict(before=x[k],after=y[k]) for k in x if x[k]!=y[k]}
assert all(re.fullmatch(r'dc/[^/]+\.ovl',k) for k in data_diffs),data_diffs
for q in ('dc/native/r101/ps2-world.re4mesh','dc/native/r101/ps2-world.r4sg','dc/native/r101/ps2-world.r4pw','dc/native/r101/ps2-world.ids','dc/native/r101/ps2-world.r4tc','dc/native/r101/room.r4rc','dc/warp.txt'):assert x[q]==y[q]
result=dict(scope='One bounded MODELLED B1 LIVE_MASK ON whole-programme comparison with retained OFF; not cache Flycast or console timing',
            count_window='300:329',timed_ticks=[300,329],time_samples=2,
            asset_identity='All prepared file keys identical; only code overlay changes permitted; every world asset and fixture is byte-identical',
            prepared_file_differences=data_diffs,end_delta=json.loads((private/'model-maskon-profile-v1/end-delta.json').read_text()),arms=[])
report_source=Path(__file__).with_name('report-model27.py').read_text();tree=ast.parse(report_source)
category=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='category');ns=dict(re=re);exec(compile(ast.Module(body=[category],type_ignores=[]),'<existing-category-helper>','exec'),ns)
for label,e,profiles in [('OFF',root/'hwmodel-v1-B1-cross',private/'model-profile-v1'),('ON',root/'hwmodel-maskon-v1-B1-cross',private/'model-maskon-profile-v1')]:
    source=json.loads((profiles/'symbols-world.json').read_text());syms=source['symbols'];names={s['symbol']:s['name'] for s in syms};names[0]='UNKNOWN';byname={s['name']:s for s in syms};explicit={s['symbol']:s['owner'] for s in syms if s['owner']}
    trace=(e/'trace/hwtrace.log').read_text();assert 'counts written frames 300:329' in trace and 'hwtrace done: traced 2 frames; exiting' in trace
    counts=(e/'trace/counts.bin').read_bytes();entry={}
    for name in ('Render','re4dc_coarse_draw','re4dc_ps2_world_draw','re4dc_ps2_mesh_draw','re4dc_ps2_world_flush','re4dc_ui_begin','re4dc_pace_begin','re4dc_pace_end'):
        s=byname[name];entry[name]=dict(elf_entry=f"{s['start']:08x}",executions=struct.unpack_from('<I',counts,((s['start']&0xffffff)>>1)*4)[0])
    assert entry['Render']['executions']==30 and entry['re4dc_ps2_mesh_draw']['executions']==90
    (e/'counted-entry-counts.json').write_text(json.dumps(entry,indent=2)+'\n')
    observed=Counter();raw=Counter();valid=Counter();funcs=Counter();last=None
    for rr in csv.DictReader((e/'profile-context/nominal.contexts.tsv').open(),delimiter='\t'):
        r={k:int(v) for k,v in rr.items()};n,parent=r['node'],r['parent'];name=names[r['symbol']]
        if r['sample']!=last:nodes=[];roots=[];last=r['sample']
        assert n==len(nodes)
        newroot=bool(r['owner'] and (n==0 or parent>=n or nodes[parent]['owner']!=r['owner'] or explicit.get(r['symbol'])==r['owner'] or r['kind']==2))
        rt=n if newroot else roots[parent] if parent<n else -1;nodes.append(r);roots.append(rt)
        if name in ('Render','re4dc_ps2_mesh_draw','re4dc_ps2_world_draw'):observed[(r['sample'],name)]+=1
        if r['owner']==6:
            cost=r['self16']/16/200000/2;cat=ns['category'](name);raw[cat]+=cost;funcs[name]+=cost
            if rt>=0 and nodes[rt]['complete'] and not nodes[rt]['invalid']:valid[cat]+=cost
    for sample in (0,1):assert observed[(sample,'Render')]==1 and observed[(sample,'re4dc_ps2_mesh_draw')]==3
    summary=json.loads((e/'profile-context/summary.json').read_text());world=next(v for v in summary['owners'] if v['owner']==6)
    assert abs(sum(raw.values())-world['raw_ms'])<1e-8 and abs(sum(valid.values())-world['validated_root_ms'])<1e-8
    buckets,_=bench.split(e);flat=list(csv.DictReader((e/'proj/rep/functions.tsv').open(),delimiter='\t'))
    source_rows=[dict(function=r['func'],ms=float(r['hw_ms'])) for r in flat if re.search(r'ps2_pass|ScenerySelector|lean::world_out|lean::box_class|sg_select_lean|transform_sched|clip_strip|walk_lean|chunk_emit|direct_begin_batch|ps2_dyn_source',r['func'])]
    scene=(e/'trace/run-output.txt').read_text(encoding='utf-16');scene=[line for line in scene.splitlines() if line.startswith(('warp: start room','warp: placed room','warp: alert at'))]
    cfg=re.sub(r'^Debug.GDBPort = \d+$','Debug.GDBPort = <per-run>',(e/'emu.cfg').read_text(),flags=re.M)
    row=dict(arm=label,evidence=str(e),elf_sha256=sha(e/'re4dc-game.elf'),emulator_sha256=sha(e/'flycast.exe'),emu_config_normalized=cfg,
             elapsed_seconds=float((e/'trace/elapsed.txt').read_text().split()[1]),cpu_work_estimate_ms=sum(buckets.values()),
             world_raw_partial_ms=world['raw_ms'],world_validated_lower_bound_ms=world['validated_root_ms'],validated_roots=world['validated_roots'],observed_roots=world['observed_roots'],
             complete_total_world_ms=None,entry_counts=entry,scene=scene,parity=json.loads((e/'profile-context/parity.json').read_text())['status'],
             categories=[dict(category=k,raw_partial_ms=v,validated_lower_bound_ms=valid[k]) for k,v in raw.most_common()],
             world_context_exclusive_functions=[dict(function=k,raw_partial_ms=v) for k,v in funcs.most_common()],flat_source_self_rows=source_rows)
    result['arms'].append(row)
off,on=result['arms'];assert off['emulator_sha256']==on['emulator_sha256'] and off['emu_config_normalized']==on['emu_config_normalized']
result['delta_on_minus_off']={k:on[k]-off[k] for k in ('cpu_work_estimate_ms','world_raw_partial_ms','world_validated_lower_bound_ms')}
old_flat={r['function']:r['ms'] for r in off['flat_source_self_rows']};new_flat={r['function']:r['ms'] for r in on['flat_source_self_rows']}
result['exclusive_source_self_deltas']=sorted([dict(function=k,off_ms=old_flat.get(k,0),on_ms=new_flat.get(k,0),delta_ms=new_flat.get(k,0)-old_flat.get(k,0)) for k in old_flat.keys()|new_flat.keys()],key=lambda r:r['delta_ms'])
result['definitions']=dict(denominator='Thirty counted source ticks contain 30 Render and 90 mesh entries in each arm; both timed ticks independently contain one Render plus three mesh passes. Timing averages divide by two observed drawn worlds.',
    work='Existing bench-split sum of exclusive function hw_ms, excluding main, re4dc_pace_end and re4dc_vi_retrace_count wholesale; an estimated CPU-work comparison, not frame latency or presentation cadence.',
    world='Same disjoint contextual exporter and explicit world roots. Raw attribution includes incomplete roots. Validated subset is a lower bound; changing validated coverage makes its delta non-equivalent to a total-world saving. Complete total world remains unqualified.',
    change='New programme data/code addresses and model cache effects remain part of this whole-programme comparison. The retained OFF is not freshly rerun; no isolated setup-only saving is claimed.')
(root/'MODELLED-LIVE-MASK-v1.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# B1 LIVE_MASK bounded MODELLED comparison','','| Arm | CPU work estimate ms/draw | Validated world lower bound | Raw partial world attribution | Validated roots |','|---|---:|---:|---:|---:|']
for r in result['arms']:lines.append(f"| {r['arm']} | {r['cpu_work_estimate_ms']:.3f} | {r['world_validated_lower_bound_ms']:.3f} | {r['world_raw_partial_ms']:.3f} | {r['validated_roots']}/{r['observed_roots']} |")
lines+=['',f"ON minus retained OFF CPU-work estimate: {result['delta_on_minus_off']['cpu_work_estimate_ms']:+.3f} ms/draw. `_end` grows {result['end_delta']['delta_bytes']} bytes.",'']+list(result['definitions'].values())
lines+=['','The exclusive source rows localize the change: ps2_pass 0.810→0.347 ms, selector chunk_select 0.303→0.109 ms, world_out 0.271→0.062 ms, box_class 0.267→0.077 ms. By comparison, strip walk 0.292→0.290 ms and clipping 0.199→0.199 ms stay nearly unchanged. These are disjoint exclusive function self rows, providing an alternative view of the same charges; do not add them to contextual or whole-work totals. Programme layout/cache changes remain included.']
lines+=['','All B1 world files and the fixed cross fixture are byte-identical. Emulator executable and normalized configuration match. Both programmes have exact nominal/profile output parity and charge conservation. Only ON is a fresh guest in this follow-up; it exits within 55 seconds. No other arms or guest runs were started. Owned model ISO copies were immediately hash-checked and deleted.','', 'Complete world budget, route, appearance, GPU deadlines and console performance remain unqualified. Source self rows and contextual categories are alternative disjoint views of the same measured charges and must not be added together.','']
(root/'MODELLED-LIVE-MASK-v1.md').write_text('\n'.join(lines))
print(json.dumps(dict(delta=result['delta_on_minus_off'],arms=[{k:r[k] for k in ('arm','cpu_work_estimate_ms','world_raw_partial_ms','world_validated_lower_bound_ms','validated_roots','observed_roots')} for r in result['arms']]),indent=2))

#!/usr/bin/env python3
"""Publish compact build/target receipts while retaining raw-result hashes."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def arm(row):
    traffic=row['traffic']
    result={name:row[name] for name in ('entry_kind','instructions','peak_stack_bytes',
        'model_cycles','output_sha256','pose_sha256','trace_sha256','source_key_bytes') if name in row}
    result.update(cold_icache={k:v for k,v in row['cold_icache'].items() if k not in ('command','scope')},
        traffic={k:v for k,v in traffic['cached'].items() if k not in ('load_accesses','store_accesses','unique_line_bytes')},
        demand_line_visits=traffic['demand_line_visits'],
        repeated_demand_line_visits=traffic['repeated_demand_line_visits'],
        prefetch={k:v for k,v in traffic['prefetch'].items() if k!='scope'})
    result['uncached_bytes']=traffic['uncached']['load_bytes']+traffic['uncached']['store_bytes']
    result['store_queue_bytes']=traffic['store_queue']['load_bytes']+traffic['store_queue']['store_bytes']
    if 'errors' in row:result['errors']=row['errors']
    if 'adapter_calls' in row:
        from collections import Counter
        result['adapter_counts']=dict(Counter(name for name,argument in row['adapter_calls']))
    return result


def compact_case(row):
    return {**{k:v for k,v in row.items() if k not in ('arms','frames')},
        **({'axis_key_counts':list(map(len,row['frames']))} if 'frames' in row else {}),
        'arms':{name:arm(value) for name,value in row['arms'].items()}}


def compact_regions(row):
    drop=('load_accesses','store_accesses','unique_line_bytes','unique_read_lines','unique_write_lines')
    return dict(name=row['name'],regions={arm:{name:{k:v for k,v in data.items() if k not in drop}
        for name,data in regions.items()} for arm,regions in row['regions'].items()})


def relevant_stack(rows):
    wanted=('hfReg','hfClamped','hermiteReg','hermiteFast','hermiteSampleEntry','HermiteInterpolation','MotionMoveCore')
    return [row for row in rows if any(word in row['function'] for word in wanted)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build-controls','target-build','sampler-controls','pose-controls','sequence-controls','traffic-controls','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    build,target,sampler,pose,sequence,traffic=(read(p) for p in (args.build_controls,args.target_build,
        args.sampler_controls,args.pose_controls,args.sequence_controls,args.traffic_controls))
    assert all(x['status']=='PASS' for x in (build,target,sampler,pose,sequence,traffic))
    for raw in (sampler,pose,sequence,traffic):assert raw['target_build_sha256']==sha(args.target_build)
    assert build['source_sha256']['src/game/motion.cpp']==target['source_sha256']['src/game/motion.cpp']
    for name,control in (('l0','zero.o'),('l1','on.o')):
        assert target['arms'][name]['object_sha256']==build['production']['reg1'][control]['sha256']
    production={}
    for name,rows in build['production'].items():
        production[name]={key:{field:value for field,value in row.items() if field!='stack_usage'}
            for key,row in rows.items()}
        for key in ('baseline.o','on.o'):
            production[name][key]['stack_usage']=relevant_stack(rows[key]['stack_usage'])
    profile=build['profiles']['absent']['recipe_inputs']
    receipt=dict(status='PASS',scope=build['scope'],baseline=build['baseline'],knob=build['knob'],
        compiler=build['compiler'],off_identity_comparisons=build['off_identity_comparisons'],
        inactive_on_identity_comparisons=build['inactive_on_identity_comparisons'],
        source_sha256=build['source_sha256'],recipe_inputs=profile,make_identity=build['make_identity'],
        production=production,raw_build_receipt_sha256=sha(args.build_controls),
        target=dict(scope=target['scope'],source_sha256=target['source_sha256'],
            raw_target_build_receipt_sha256=sha(args.target_build),
            arms={name:{k:v for k,v in row.items() if k not in ('elf','stack_usage')} for name,row in target['arms'].items()}))
    save(args.output/'build_receipt.json',receipt)
    save(args.output/'sampler_receipt.json',dict(status='PASS',scope=sampler['scope'],
        fixture_entry_note='Calls actual public HermiteInterpolation or qualified private clamped entry directly using r4/r5/r6. Rejected v1/v2 probes used fixture_sample; their wrapper adds argument/global loads. Compare only paired arms within a receipt.',
        source_sha256=sampler['source_sha256'],target_build_sha256=sampler['target_build_sha256'],
        memory_controls=sampler['memory_controls'],models=sampler['models'],
        cases=[compact_case(row) for row in sampler['cases']],raw_receipt_sha256=sha(args.sampler_controls)))
    save(args.output/'pose_receipt.json',dict(status='PASS',scope=pose['scope'],
        sequence_scope=sequence['scope'],source_sha256={**pose['source_sha256'],**sequence['source_sha256']},
        target_build_sha256=pose['target_build_sha256'],conversion_controls=pose['conversion_controls'],
        models=pose['models'],cases=[compact_case(row) for row in pose['cases']+sequence['cases']],
        raw_receipt_sha256=sha(args.pose_controls),raw_sequence_receipt_sha256=sha(args.sequence_controls)))
    selected={'t5-n8-exact_middle','t5-n8-interior','t5-n8-clamp_ignore_history',
        't5-n8-clamp_invalid_history','t5-mixed','t5-late_runout',*[f't{t}-n8-clamp' for t in (0,5,6)]}
    pose_selected={f't{t}-n16-{mode}' for t in (0,5,6) for mode in ('clamped','interior')}
    save(args.output/'traffic_receipt.json',dict(status='PASS',scope=traffic['scope'],
        source_sha256=traffic['source_sha256'],target_build_sha256=traffic['target_build_sha256'],
        sampler=[compact_regions(row) for row in traffic['sampler'] if row['name'] in selected],
        pose=[compact_regions(row) for row in traffic['pose'] if row['name'] in pose_selected],
        raw_sampler_cases=len(traffic['sampler']),raw_pose_cases=len(traffic['pose']),
        raw_receipt_sha256=sha(args.traffic_controls)))
    print(json.dumps(dict(status='PASS',sampler_cases=len(sampler['cases']),
        pose_cases=len(pose['cases'])+len(sequence['cases']),source_sha256=build['source_sha256'])))


if __name__=='__main__':main()

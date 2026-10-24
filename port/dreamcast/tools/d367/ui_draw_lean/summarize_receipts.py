#!/usr/bin/env python3
"""Create a compact review receipt; reconcile executed full objects with Make.

All input receipts remain reproducible from the neighboring tools. This report
does not turn synthetic phase counts, perfect-D cycles or demand addresses
into measured console cache misses or frame-time results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
import build_profile as p


def read(path):
    value=json.loads(path.read_text());assert value['status']=='PASS',path
    return value


def pin(path):return dict(file=path.parent.name+'/'+path.name,sha256=p.sha(path))


def compact(row):
    t=row['traffic'];d=t['cached']
    value=dict(instructions=row['instructions'],warm_cycles=row['model_cycles'],
        cold_icache_cycles=row['cold_icache']['model_cycles'],
        load_instructions=d['load_instructions'],store_instructions=d['store_instructions'],
        load_bytes=d['load_bytes'],store_bytes=d['store_bytes'],
        distinct_32byte_lines=d['unique_data_lines'],distinct_read_lines=d['unique_read_lines'],
        distinct_write_lines=d['unique_write_lines'],demand_line_visits=t['demand_line_visits'],
        repeated_demand_line_visits=t['repeated_demand_line_visits'],peak_stack_bytes=row['peak_stack_bytes'])
    for key in ('input','output_sha256','packet_sizes','ta_words','state','observations','matrix','compact_words'):
        if key in row:value[key]=row[key]
    assert not t['store_queue']['load_bytes'] and not t['store_queue']['store_bytes']
    assert not t['uncached']['load_bytes'] and not t['uncached']['store_bytes']
    return value


def summarize(args):
    controls=read(args.controls)
    refresh=None
    if args.native_controls:
        refresh=read(args.native_controls)
        assert refresh['baseline']==controls['baseline']
        assert refresh['off_identity_comparisons']==36 and refresh['unchanged_on_comparisons']==0
        assert set(refresh['production'])==set(controls['production'])
        for variant,units in refresh['production'].items():
            assert set(units)=={'native_ui'}
            for suffix in ('ii','o'):
                assert units['native_ui']['baseline.'+suffix]['sha256']==controls['production'][variant]['native_ui']['baseline.'+suffix]['sha256']
            controls['production'][variant]['native_ui']=units['native_ui']
        for relative,digest in refresh['source_sha256'].items():
            if relative!='port/dreamcast/game/platform/native_ui.cpp':assert controls['source_sha256'][relative]==digest
            controls['source_sha256'][relative]=digest
    names=('native','bridge','camera')
    builds={name:read(getattr(args,name+'_build')) for name in names}
    runs={name:read(getattr(args,name+'_run')) for name in names}
    reconciled={};sources=dict(controls['source_sha256'])
    for name,unit in (('native','native_ui'),('bridge','ui_bridge'),('camera','mes')):
        for arm,mode in (('l0','baseline'),('l1','on')):
            digest=builds[name]['arms'][arm]['object_sha256']
            expected=controls['production']['public'][unit][mode+'.o']['sha256']
            assert digest==expected,(name,arm,'executed full object differs from public Make object')
            reconciled[name+'-'+arm]=digest
        for relative,digest in builds[name]['source_sha256'].items():
            if relative.startswith(('port/dreamcast/game/','port/dreamcast/room/','src/')):
                assert p.sha(p.ROOT/relative)==digest,(relative,'runtime source changed')
                if relative in sources:assert sources[relative]==digest
                sources[relative]=digest
        run_key='camera_build_sha256' if name=='camera' else 'build_sha256'
        assert runs[name][run_key]==p.sha(getattr(args,name+'_build'))
    for relative,digest in sources.items():assert p.sha(p.ROOT/relative)==digest,(relative,'source changed')
    production={}
    for variant,units in controls['production'].items():
        production[variant]={}
        for unit,rows in units.items():
            assert all(rows[arm+'.'+suffix]['sha256']==rows['baseline.'+suffix]['sha256']
                for arm in ('absent','zero') for suffix in ('ii','o'))
            stack=lambda row:[x for x in row['stack_usage'] if any(part in x['function'] for part in
                ('ui_draw_quad(', 'glyph_draw_run(', 're4dc_draw_id_quad(', 'messageCamera('))]
            production[variant][unit]=dict(off_ii_sha256=rows['baseline.ii']['sha256'],
                off_object_sha256=rows['baseline.o']['sha256'],on_ii_sha256=rows['on.ii']['sha256'],
                on_object_sha256=rows['on.o']['sha256'],
                off={key:rows['baseline.o'][key] for key in ('executable_bytes','allocated_bytes','zero_fill_bytes')},
                on={key:rows['on.o'][key] for key in ('executable_bytes','allocated_bytes','zero_fill_bytes')},
                off_stack=stack(rows['baseline.o']),on_stack=stack(rows['on.o']))
    inactive=controls['production']['no_messages']['mes']
    assert all(inactive['baseline.'+suffix]['sha256']==inactive['on.'+suffix]['sha256'] for suffix in ('ii','o'))
    phases={}
    for name in names:
        phases[name]=dict(scope=runs[name]['scope'],arms={})
        for arm,info in runs[name]['arms'].items():
            phases[name]['arms'][arm]=({key:compact(row) for key,row in info['cases'].items()}
                if 'cases' in info else compact(info))
    result=dict(status='PASS',baseline=controls['baseline'],knob='UI_DRAW_LEAN',default=0,
        scope=__doc__,compiler=controls['compiler'],source_sha256=sources,
        recipe_sha256=controls['baseline_profile']['recipe_inputs']['recipe_sha256'],
        profiles={name:p.PROFILES[name] for name in production},
        off_preprocessed_and_raw_object_comparisons=controls['off_identity_comparisons'],
        unchanged_on_comparisons=controls['unchanged_on_comparisons'],
        inactive_non_native_message_camera_on_equals_off=True,
        public_executed_full_objects_equal_independent_make_objects=reconciled,
        production=production,phases=phases,interpreter_controls=runs['native']['interpreter_controls'],
        raw_receipts={key:pin(getattr(args,key)) for key in ('controls',*[n+'_'+part for n in names for part in ('build','run')])})
    if refresh:
        result['raw_receipts']['native_identity_refresh']=pin(args.native_controls)
        result['identity_refresh_scope']=dict(retained_unaffected_comparisons=144,refreshed_native_comparisons=36,
            total_distinct_final_comparisons=180,previous_native_control_comparisons=36,
            scope='Only native_ui.cpp changed after the full qualification; original source/Make hashes and all unaffected proofs are retained.')
    if args.candidates:
        trial=read(args.candidates)
        result['candidate_comparison']={name:{k:compact(row) for k,row in info['cases'].items()}
            for name,info in trial['arms'].items()}
        result['raw_receipts']['candidate_comparison']=pin(args.candidates)
        for case in ('quad','glyph1','glyph16'):
            assert compact(trial['arms']['l0']['cases'][case])==phases['native']['arms']['l0'][case],case
            if not args.dimension_run:assert compact(trial['arms']['inline']['cases'][case])==phases['native']['arms']['l1'][case],case
        if args.candidate_build:
            candidate_build=read(args.candidate_build)
            assert trial['build_sha256']==p.sha(args.candidate_build)
            result['candidate_sources']={name:info['source_sha256'] for name,info in candidate_build['arms'].items()}
            result['raw_receipts']['candidate_build']=pin(args.candidate_build)
    if args.dimension_run:
        dimension=read(args.dimension_run)
        result['dimension_hoist_comparison']={name:{k:compact(row) for k,row in info['cases'].items()}
            for name,info in dimension['arms'].items()}
        result['raw_receipts']['dimension_hoist_run']=pin(args.dimension_run)
        for case,row in dimension['arms']['initial']['cases'].items():
            assert compact(row)==phases['native']['arms']['l1'][case],case
        if args.dimension_build:
            dimension_build=read(args.dimension_build)
            assert dimension['build_sha256']==p.sha(args.dimension_build)
            result['dimension_hoist_sources']={name:info['source_sha256'] for name,info in dimension_build['arms'].items()}
            result['raw_receipts']['dimension_hoist_build']=pin(args.dimension_build)
    result['tools_sha256']={str(path.relative_to(p.ROOT)):p.sha(path) for path in sorted(HERE.iterdir())
        if path.suffix in ('.py','.inc') or path.name.endswith('.cpp.in')}
    args.output.write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    q=argparse.ArgumentParser(description=__doc__)
    for name in ('controls','native-build','native-run','bridge-build','bridge-run','camera-build','camera-run','output'):
        q.add_argument('--'+name,type=Path,required=True)
    q.add_argument('--candidates',type=Path)
    q.add_argument('--candidate-build',type=Path)
    q.add_argument('--native-controls',type=Path,help='optional native-only refresh after the full unchanged-TU proof')
    q.add_argument('--dimension-run',type=Path)
    q.add_argument('--dimension-build',type=Path)
    r=summarize(q.parse_args());print(json.dumps(dict(status=r['status'],off=r['off_preprocessed_and_raw_object_comparisons'],
        public_object_reconciliation=len(r['public_executed_full_objects_equal_independent_make_objects']))))


if __name__=='__main__':main()

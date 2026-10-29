#!/usr/bin/env python3
"""Lossless numeric/table compaction of an existing Build35 cost receipt.

Repeated prose, flags, recipe inputs, traffic and model categories move to
content-hashed tables. Commands retain a canonical-JSON SHA256 and item count;
the full source receipt remains the command-level evidence. No cost is rerun.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1]
HELPERS=[
    'port/dreamcast/tools/cloud/build25/cost_run.py',
    'port/dreamcast/tools/d367/actor_bytes_lean/kernel_audit.py',
    'port/dreamcast/tools/d367/world_replay_lean/target_machine.py',
    'port/dreamcast/tools/d367/world_replay_lean/sh4_machine.py',
    'port/dreamcast/tools/d367/backface_sh4_kernel/object_test.py',
    'port/dreamcast/tools/d367/world_replay_lean/memory_trace.py',
    'port/dreamcast/tools/d367/world_replay_lean/pipeline_cost.py',
    'port/dreamcast/tools/d367/world_replay_lean/target_run.py',
    'port/dreamcast/tools/hwmodel/hwsim.c',
]


def digest(data):return hashlib.sha256(data).hexdigest()
def packed(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--integration-ref',required=True)
    args=parser.parse_args();raw=args.input.read_bytes();original=json.loads(raw);assert original['status']=='PASS'
    for name,sha in original['source_sha256'].items():assert digest((ROOT/name).read_bytes())==sha,name
    tables={k:{} for k in ('text','vectors','recipe_inputs','traffic','categories','traffic_parts')}
    seen={k:{} for k in tables}
    def reference(value,kind):
        sha=digest(packed(value))
        if sha not in seen[kind]:
            index=str(len(tables[kind]));seen[kind][sha]=index
            tables[kind][index]={'sha256':sha,'value':compact(value,'_value')}
        return {'table':kind,'ref':seen[kind][sha]}
    def compact(value,key=''):
        if key in ('command','compile_command') and isinstance(value,list):return {'sha256':digest(packed(value)),'items':len(value)}
        if key in ('recipe_inputs','traffic','categories'):return reference(value,key)
        if key in ('scope','limits') and isinstance(value,str):return reference(value,'text')
        if key in ('options','flags','overrides') and isinstance(value,list):return reference(value,'vectors')
        if key in ('store_queue','uncached','prefetch'):return reference(value,'traffic_parts')
        if isinstance(value,dict):return {k:compact(v,k) for k,v in value.items()}
        if isinstance(value,list):return [compact(v) for v in value]
        return value
    result=compact(original)
    def expand(value):
        if isinstance(value,dict):
            if set(value)=={'table','ref'}:return expand(tables[value['table']][value['ref']]['value'])
            return {k:expand(v) for k,v in value.items()}
        if isinstance(value,list):return [expand(v) for v in value]
        return value
    def hash_commands(value,key=''):
        if key in ('command','compile_command') and isinstance(value,list):return {'sha256':digest(packed(value)),'items':len(value)}
        if isinstance(value,dict):return {k:hash_commands(v,k) for k,v in value.items()}
        if isinstance(value,list):return [hash_commands(v) for v in value]
        return value
    # Exact expansion equality checks every original numeric and non-command
    # field, rather than relying on aggregate counts or a selective key list.
    assert expand(result)==hash_commands(original),'compaction changed substantive fields'
    for table in tables.values():
        for row in table.values():assert digest(packed(expand(row['value'])))==row['sha256']
    baseline=subprocess.check_output(['git','rev-parse',args.integration_ref],cwd=ROOT,text=True).strip()
    helper_hashes={}
    for name in HELPERS:
        current=(ROOT/name).read_bytes();control=subprocess.check_output(['git','show',baseline+':'+name],cwd=ROOT)
        assert current==control,(name,'helper differs from integration')
        helper_hashes[name]=digest(current)
    result['tables']=tables
    result['compaction']=dict(schema='build35-window-cost-tables-v1',source_receipt_sha256=digest(raw),source_receipt_bytes=len(raw),
        script_sha256=digest(Path(__file__).read_bytes()),all_non_command_fields_expand_exactly=True,
        command_hash_encoding='SHA256 of canonical JSON with sorted keys and comma/colon separators; no whitespace',
        integration_ref=baseline,reviewed_imported_helper_sha256=helper_hashes,helpers_equal_integration=True,
        reproduce_cost='python3 -B port/dreamcast/tools/cloud/build35/window_cost.py --output "$OUT/window-cost" --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT"',
        reproduce_compaction='python3 -B port/dreamcast/tools/cloud/build35/compact_window_cost.py --input "$OUT/window-cost/window-cost.json" --output "$OUT/window-cost-compact.json" --integration-ref '+baseline,
        reproduction_prerequisites='Use a fresh OUT and the pinned compiler/KOS/SH4ZAM recorded by the source profiles. The driver regenerates the full receipt before compaction. No new target run was made for this metadata-only transformation.')
    data=('{'+'\n'+',\n'.join(json.dumps(k)+':'+json.dumps(v,separators=(',',':')) for k,v in result.items())+'\n}\n').encode()
    assert len(data)<350*1024,len(data)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(data)
    print(json.dumps(dict(status='PASS',cases=len(result['cases']),bytes=len(data),sha256=digest(data),source_receipt_sha256=digest(raw))))


if __name__=='__main__':main()

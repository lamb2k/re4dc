"""Seal PREPARATION-only output inventory. No private shadow oracle."""
import argparse,hashlib,json
from pathlib import Path
import prepare_private as prep
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--expected-source',required=True);ap.add_argument('--expected-report-sha256',required=True);a=ap.parse_args()
 owned=prep.own_sources(a.repo,a.expected_source);directory=a.directory.resolve()
 if directory.is_relative_to(a.repo.resolve()) or {p.name for p in directory.iterdir()}!={'report.json','structural-controls.json'}:raise ValueError('Exact fresh two-output private preparation directory required')
 files={p.name:prep.pin(p) for p in sorted(directory.iterdir())};report=json.loads((directory/'report.json').read_text());controls=json.loads((directory/'structural-controls.json').read_text())
 if files['report.json']['sha256']!=a.expected_report_sha256 or report['preparation_source']!=a.expected_source or report['partition_source']!=prep.PARTITION_SOURCE or report['owned_sources']!=owned or controls['owned_sources']!=owned or controls['plan']!=files['report.json']:raise ValueError('Frozen preparation/control binding changed')
 if report['actual_shadow_predicates']!=0 or controls['private_shadow_predicates']!=0 or report['new_rays']!=0 or controls['new_rays']!=0:raise ValueError('Preparation only, no scene predicates/rays')
 result=dict(classification='PREPARATION_ONLY_NOT_AN_EXECUTION_GRANT',preparation_source=a.expected_source,partition_source=prep.PARTITION_SOURCE,owned_source_files=owned,owned_source_count=len(owned),owned_source_bytes=sum(p['bytes'] for p in owned.values()),output_files=files,output_count_including_seal=3,output_bytes_including_seal=0,seal_bytes=0,all_output_cap_bytes=prep.OUTPUT,proposed_candidate_calls=100000,proposed_candidate_edges=7200000,separate_final_child_checks=10668,separate_final_edges=768096,all75_new_partition_cases='UNTESTED_UNKNOWN',other9600_cases='UNTESTED_UNKNOWN',private_shadow_predicates=0,new_rays=0,ledger_accesses=0,runtime_admitted=False)
 for _ in range(10):
  raw=(json.dumps(result,indent=2)+'\n').encode();result['seal_bytes']=len(raw);result['output_bytes_including_seal']=sum(p['bytes'] for p in files.values())+len(raw)
 raw=(json.dumps(result,indent=2)+'\n').encode()
 if len(raw)!=result['seal_bytes'] or result['output_bytes_including_seal']>prep.OUTPUT:raise ValueError('Aggregate preparation output cap')
 target=directory/'PREPARATION-SEAL.json';target.write_bytes(raw);print(json.dumps(prep.pin(target)))
if __name__=='__main__':main()

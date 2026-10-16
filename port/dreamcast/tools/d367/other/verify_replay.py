#!/usr/bin/env python3
"""Verify exporter-only changes against an original simulator replay."""
import argparse
import csv
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',required=True,type=Path)
    p.add_argument('--exported',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    checks={}
    for name in ('cgsim.frames.tsv','cgsim.pcs.tsv','cg.cg.tsv'):
        old,new=digest(a.original/name),digest(a.exported/name)
        checks[name]={'original_sha256':old,'exported_sha256':new,'byte_identical':old==new}
    if not all(c['byte_identical'] for c in checks.values()):
        raise ValueError('Exporter changed the simulator output')
    with tempfile.TemporaryDirectory(prefix='other-trace-entry-') as temp:
        d=Path(temp)
        (d/'entries.txt').write_text('8c000100\n8c000104\n8c000106\n')
        # Two instruction runs; memory events must not become entry executions.
        records=[(0x8c000100,0x10000003),(0x8c000106,0x20000000),
                 (0x8c000104,0x10000002),(0x8c000100,0x30000000)]
        (d/'trace.bin').write_bytes(b''.join(struct.pack('<II',*r) for r in records))
        text=subprocess.check_output([str(a.exported/'trace_entries'),str(d/'entries.txt'),str(d/'trace.bin')],text=True)
        observed={r['entry']:int(r['executed_entry_pc_count']) for r in csv.DictReader(text.splitlines(),delimiter='\t')}
        expected={'8c000100':1,'8c000104':2,'8c000106':1}
        if observed!=expected:
            raise ValueError(f'Entry scan failed: {observed}')
        (d/'truncated.bin').write_bytes((d/'trace.bin').read_bytes()+b'x')
        rejected=subprocess.run([str(a.exported/'trace_entries'),str(d/'entries.txt'),str(d/'truncated.bin')],
                                capture_output=True).returncode!=0
        if not rejected:
            raise ValueError('Truncated trace was not rejected')
    result={'status':'PASS','original':str(a.original),'exported':str(a.exported),
            'unchanged_model_outputs':checks,'entry_scanner_fixture':{'expected':expected,'observed':observed,
                                                                      'truncated_record_rejected':rejected},
            'scope':'Host profiler only; this validation does not establish console performance or game correctness.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()

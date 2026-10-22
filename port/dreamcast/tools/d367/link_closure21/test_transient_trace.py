#!/usr/bin/env python3
"""Synthetic private generated-data lifecycle controls, never game seals."""
import copy
import gzip
import json
import os
from pathlib import Path
import unittest
import trace_closure as trace

class TransientTests(unittest.TestCase):
    def setUp(self):
        root=os.environ.get('TRANSIENT_TRACE_FIXTURE')
        if not root:self.skipTest('set TRANSIENT_TRACE_FIXTURE to source-only retained namespace')
        self.root=Path(root)
        def read(name):
            path=self.root/name
            return path.read_text() if path.exists() else gzip.decompress(path.with_name(path.name+'.gz').read_bytes()).decode()
        self.contract=json.loads(read('transient-prepinned-policy.json'));self.lines=read('transient-qualified.strace').splitlines()
    def reject(self,lines=None,contract=None):
        with self.assertRaises((ValueError,OSError)):
            trace.validate('\n'.join(self.lines if lines is None else lines),self.contract if contract is None else contract)
    def test_exact_source_fixture(self):self.assertEqual(trace.validate('\n'.join(self.lines),self.contract)['transient_data_files'],2)
    def test_missing_unlinks(self):self.reject([x for x in self.lines if ' unlink('not in x])
    def test_extra_unlink(self):self.reject(self.lines+[next(x for x in self.lines if ' unlink('in x)])
    def test_unlink_pinned_source(self):self.reject(self.lines+[self.lines[0].split()[0]+' unlink('+json.dumps(str(self.root/'fixture-input.dat'))+') = 0'])
    def test_missing_creator(self):self.reject([x for x in self.lines if not('openat('in x and 'tmp'in x and 'O_EXCL'in x)])
    def test_read_before_tool_write(self):
        read=next(x for x in self.lines if 'openat('in x and '/temp/tmp'in x and 'O_RDONLY'in x);lines=[x for x in self.lines if x!=read];idx=next(i for i,x in enumerate(lines)if 'openat('in x and '/temp/tmp'in x and 'O_TRUNC'in x);lines.insert(idx,read);self.reject(lines)
    def test_wrong_writer(self):c=copy.deepcopy(self.contract);c['transient_data'][1]['writers']=c['transient_data'][1]['readers'];self.reject(contract=c)
    def test_wrong_reader(self):c=copy.deepcopy(self.contract);c['transient_data'][1]['readers']=c['transient_data'][1]['writers'];self.reject(contract=c)
    def test_duplicate_read(self):read=next(x for x in self.lines if 'openat('in x and '/temp/tmp'in x and 'O_RDONLY'in x);idx=self.lines.index(read);self.reject(self.lines[:idx]+[read]+self.lines[idx:])
    def test_wrong_count(self):c=copy.deepcopy(self.contract);c['transient_data'][1]['count']=2;self.reject(contract=c)
    def test_bad_count_type(self):c=copy.deepcopy(self.contract);c['transient_data'][1]['count']=True;self.reject(contract=c)
    def test_changed_tool_pin(self):c=copy.deepcopy(self.contract);c['inputs'][0]['pin']['sha256']='0'*64;self.reject(contract=c)
    def test_changed_tool_flag(self):self.reject([x.replace('"-I", "binary"','"-I", "elf32-shl"')for x in self.lines])
    def test_changed_transient_alias(self):self.reject([x.replace('/temp/tmp','/temp/./tmp')for x in self.lines])
    def test_output_postabsence(self):
        line=next(x for x in self.lines if 'openat('in x and '/temp/tmp'in x and 'O_RDONLY'in x);event=trace.parse(line)[0];path=Path(event['resolved']);assert path.parent==self.root/'temp'and not path.exists();path.write_bytes(b'leftover')
        try:self.reject()
        finally:path.unlink()
    def test_default_refuses_transients(self):c=copy.deepcopy(self.contract);c.pop('transient_data');self.reject(contract=c)

if __name__=='__main__':unittest.main(verbosity=2)

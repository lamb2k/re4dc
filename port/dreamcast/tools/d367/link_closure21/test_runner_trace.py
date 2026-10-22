#!/usr/bin/env python3
"""Source-only concrete controller/strict dispatch controls. No tool child is launched."""
import ast
import copy
import gzip
import json
import lzma
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import runner_trace as bridge

class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['RUNNER792_FIXTURE']);cls.plan=bridge.read_json(cls.root/'runner-plan.json.xz')
    def gate(self):
        # unittest.mock imports asyncio/SSL; that harness is not part of the frozen controller.
        with patch.object(bridge.tools,'mapped_host_elfs',return_value=set(self.plan['source_tool_snapshot']['controller_host_elf_maps'])):
            return bridge.Gate(copy.deepcopy(self.plan),{},self.plan['future_root'],self.plan['future_cwd'])
    def test_all41_frozen_commands_prepare_without_execution(self):
        g=self.gate()
        self.assertEqual(len(g.plan['order']),41)
        for name in g.plan['order']:
            # ID patch requires a real fresh generated ELF and is deferred, not replaced by old69f.
            if name=='patch-image-id':g.records.append(dict(name=name));continue
            command=g.plan['steps'][name]['command'];launch,env=g.before(name,command)
            self.assertEqual(launch[len(bridge.TRACE_PREFIX)+2:],command)
            self.assertEqual(env,g.plan['steps'][name]['environment'])
            g.pending=None;g.records.append(dict(name=name))
    def test_unplanned_controller_mapping_refused(self):
        with patch.object(bridge.tools,'mapped_host_elfs',return_value={'/unplanned/lib.so'}),self.assertRaisesRegex(ValueError,'unplanned controller'):
            bridge.Gate(copy.deepcopy(self.plan),{},self.plan['future_root'],self.plan['future_cwd'])
    def test_bad_derive_flag_refused(self):
        g=self.gate();cmd=list(g.plan['steps']['derive-static']['command']);cmd[1]='--remove-section'
        with self.assertRaisesRegex(ValueError,'unknown/changed'):g.before('derive-static',cmd)
    def test_bad_derive_source_refused(self):
        g=self.gate();cmd=list(g.plan['steps']['derive-static']['command']);cmd[-2]='/tmp/stale650.o'
        with self.assertRaisesRegex(ValueError,'unknown/changed'):g.before('derive-static',cmd)
    def test_step_order_refused(self):
        g=self.gate()
        with self.assertRaisesRegex(ValueError,'order'):g.before('base-link',g.plan['steps']['base-link']['command'])
    def test_source_tool_hash_refused(self):
        p=copy.deepcopy(self.plan);p['source_tool_snapshot']['pins'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'drift'):bridge.Gate(p,{},p['future_root'],p['future_cwd'])
    def test_duplicate_same_alias_identity_refused(self):
        p=copy.deepcopy(self.plan);bad=copy.deepcopy(p['source_tool_snapshot']['pins'][0]);bad['sha256']='0'*64;p['source_tool_snapshot']['pins'].append(bad)
        with self.assertRaisesRegex(ValueError,'ambiguous'):bridge.Gate(p,{},p['future_root'],p['future_cwd'])
    def test_conservative_physical_allocation_charge(self):
        from types import SimpleNamespace
        tree=ast.parse(Path(__file__).with_name('next792_controller.py').read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main');node=next(n for n in main.body if isinstance(n,ast.FunctionDef)and n.name=='charged_file');namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-source-allocation-function','exec'),namespace)
        class Fake:
            def __init__(self,size,blocks=None):self.value=SimpleNamespace(st_size=size,**({}if blocks is None else{'st_blocks':blocks}))
            def stat(self):return self.value
        for file,expected in [(Fake(1),4096),(Fake(4097),8192),(Fake(1,64),32768),(Fake(8192,1),8192),(Fake(0,8),4096)]:self.assertEqual(namespace['charged_file'](file),expected)
    def test_all14_sealers_have_exact_nested_calls(self):
        for index in range(14):
            s=self.plan['steps']['seal-'+str(index)];self.assertEqual(len(s['executions']),8);self.assertEqual([x['count']for x in s['transient_data']],[1,5])
            self.assertTrue(s['executions'][0]['argv'][1:4]==['-I','-S','-B'])
            self.assertEqual(sum(1 for r in s['executions']if r['path'].endswith('sh-elf-objcopy')),5)
    def test_real_ld_and_inert_recorder_are_distinct(self):
        s=self.plan['steps']['base-link'];self.assertEqual(len(s['executions']),5);ld=s['executions'][-1]
        self.assertNotIn('inert-linker-recorder',ld['path']);self.assertEqual(ld['argv'][1:],s['executions'][-2]['argv'][1:])
        self.assertEqual(ld['environment'],s['executions'][-2]['environment']);self.assertEqual(len(s['required_reads']),1)
    def test_correct_proposal_overrides_in_frozen_env(self):
        e=self.plan['environment'];self.assertEqual(e['RE4DC_OVL_ID'],'1');self.assertIn('shlelf-tight.ld',e['KOS_LDFLAGS']);self.assertIn('--wrap=',e['GAME_LDFLAGS'])
    def test_controller_has_no_untraced_subprocess_entry(self):
        path=Path(__file__).with_name('next792_controller.py');tree=ast.parse(path.read_text());calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='subprocess'];self.assertEqual([n.func.attr for n in calls],['Popen'])
        self.assertTrue(any(isinstance(n,ast.FunctionDef)and n.name=='main'for n in tree.body))
        self.assertIn("freeze['source_clean_checked_before_entry']",path.read_text())
        self.assertIn('all41_actual_exec_open_traces_qualified',path.read_text())
    def test_driver_comparator_exact_nonce_only(self):
        data=gzip.decompress((self.root/'driver-base-qualified.log.gz').read_bytes());temp=self.root/'temp';pattern=re.compile(rb'"-plugin-opt=-fresolution=('+re.escape(str(temp).encode())+rb'/cc[A-Za-z0-9]{6}\.res)"');found=list(pattern.finditer(data));self.assertEqual(len(found),1);changed=data[:found[0].start(1)]+str(temp).encode()+b'/ccABCDEF.res'+data[found[0].end(1):];self.assertTrue(bridge.compare_driver(data,changed,temp))
        for old,new in [(b'-lkallisti',b'-lkallisti_BAD'),(b'--gc-sections',b'--no-gc-sections'),(b'/collect2 ',b'/collect3 '),(str(temp).encode(),b'/tmp')]:
            with self.subTest(old=old):self.assertFalse(bridge.compare_driver(data,changed.replace(old,new,1),temp))

if __name__=='__main__':unittest.main(verbosity=2)

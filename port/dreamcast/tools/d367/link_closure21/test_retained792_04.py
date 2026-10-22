#!/usr/bin/env python3
"""Focused04 retained helper/source checks; no external child/tool execution."""
import copy,gzip,json,lzma,os,unittest
from pathlib import Path
import runner_trace792_04 as bridge
import trace_closure792_04 as parser
import tool_closure as tools
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.N=Path(os.environ['RUNNER04_FIXTURE']);cls.B=Path('/root/probe/mipmap21-next792-link-20261022-03');cls.trace=(cls.B/'seal-0.strace').read_text();cls.c=json.loads(gzip.decompress((cls.N/'retained03-seal0-contract.json.gz').read_bytes()));cls.plan=json.loads(lzma.decompress((cls.N/'runner-plan.json.xz').read_bytes()));cls.fixture=cls.N/'inert-source-fixture';(cls.fixture/'out').mkdir(parents=True,exist_ok=True);cls.data=cls.fixture/'out/data.fixture';cls.data.write_bytes(b'INERT123')
 def test_exact_retained_seal0(self):
  r=parser.validate(self.trace,self.c);self.assertEqual((r['events'],r['successful_executions'],r['distinct_prepinned_reads'],r['transient_data_files']),(156,8,49,6))
 def test_retained_base_still_passes(self):
  saved=json.loads(gzip.decompress((self.B/'base-link-trace-contract.json.gz').read_bytes()));s=gzip.decompress((self.B/'base-link.strace.gz').read_bytes()).decode();self.assertEqual(parser.validate(s,saved['contract'])['successful_executions'],5)
 def reject(self,text=None,c=None):
  with self.assertRaises((ValueError,OSError)):parser.validate(self.trace if text is None else text,self.c if c is None else c)
 def test_changed_zoneinfo_pin_refused(self):
  c=copy.deepcopy(self.c);next(r for r in c['inputs']if r['pin']['resolved']=='/usr/share/zoneinfo/America/New_York')['pin']['sha256']='0'*64;self.reject(c=c)
 def test_changed_BFD_plugin_pin_refused(self):
  c=copy.deepcopy(self.c);next(r for r in c['inputs']if r['pin']['resolved'].endswith('/bfd-plugins/libdep.so'))['pin']['sha256']='0'*64;self.reject(c=c)
 def test_other_timezone_alias_refused(self):self.reject(self.trace.replace('"/etc/localtime"','"/etc/../etc/localtime"'))
 def test_unknown_plugin_not_admitted(self):self.reject(self.trace.replace('/bfd-plugins/libdep.so','/bfd-plugins/unknown.so'))
 def test_bz2_unlisted_alias_refused(self):self.reject(self.trace.replace('"/lib/x86_64-linux-gnu/libbz2.so.1.0"','"/lib/./x86_64-linux-gnu/libbz2.so.1.0"'))
 def test_write_to_timezone_refused(self):self.reject(self.trace.replace('"/etc/localtime", O_RDONLY|O_CLOEXEC','"/etc/localtime", O_WRONLY|O_CREAT|O_TRUNC'))
 def test_write_to_plugin_refused(self):
  line=next(l for l in self.trace.splitlines(True)if 'openat('in l and '/bfd-plugins/libdep.so'in l);self.reject(self.trace.replace(line,line.replace('O_RDONLY|O_CLOEXEC','O_WRONLY|O_CREAT|O_TRUNC'),1))
 def directory_gate(self):
  g=bridge.Gate.__new__(bridge.Gate);g.plan=copy.deepcopy(self.plan);return g
 def test_actual_BFD_membership_check_passes(self):self.directory_gate().check_directories()
 def test_BFD_extra_member_manifest_refused(self):
  g=self.directory_gate();g.plan['directory_manifests'][0]['members'].append(dict(g.plan['directory_manifests'][0]['members'][0],path='/not/extra.so'))
  with self.assertRaisesRegex(ValueError,'membership changed'):g.check_directories()
 def test_BFD_changed_member_hash_refused(self):
  g=self.directory_gate();g.plan['directory_manifests'][0]['members'][0]['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'member pin changed'):g.check_directories()
 def test_BFD_symlink_change_manifest_refused(self):
  g=self.directory_gate();g.plan['directory_manifests'][0]['members'][0]['symlink_target']='elsewhere.so'
  with self.assertRaisesRegex(ValueError,'member pin changed'):g.check_directories()
 def test_BFD_directory_alias_change_refused(self):
  g=self.directory_gate();g.plan['directory_manifests'][0]['requested_alias']='/usr/lib'
  with self.assertRaisesRegex(ValueError,'alias changed'):g.check_directories()
 def generated_gate(self):
  g=bridge.Gate.__new__(bridge.Gate);g.root=self.fixture;g.context=self.fixture/'context';g.plan=dict(steps={'producer':dict(command=['INERT_SOURCE_ONLY_PRODUCER'],outputs=[str(self.data)]),'consumer':dict(command=['INERT_SOURCE_ONLY_CONSUMER',str(self.data)],generated_inputs=[dict(path=str(self.data),producer='producer')],executions=[],outputs=[],environment={},required_reads=[str(self.data)])},order=['producer','consumer'],absence=[],read_directories=[],directory_manifests=[]);g.frozen=[];g.expected=[];g.pending=None;g.records=[dict(name='producer',actual_returncode=0,result=dict(status='PASS_EXACT_PREPINNED_TRACE'),outputs=[tools.pin(self.data,'generated-output-postchild')],command=['INERT_SOURCE_ONLY_PRODUCER'])];return g
 def test_causal_generated_input_positive(self):
  g=self.generated_gate();rows=g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')]);self.assertEqual(rows[0]['pin'],g.records[0]['outputs'][0])
 def test_generated_before_requires_exact_consumer_argv(self):
  g=self.generated_gate();launch,env=g.before('consumer',g.plan['steps']['consumer']['command']);self.assertEqual(g.pending['contract']['required_reads'],[str(self.data)]);self.assertEqual(g.pending['contract']['inputs'][0]['pin']['sha256'],g.records[0]['outputs'][0]['sha256'])
 def test_missing_producer_refused(self):
  g=self.generated_gate();g.records=[]
  with self.assertRaisesRegex(ValueError,'causally qualified'):g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')])
 def test_failed_producer_refused(self):
  g=self.generated_gate();g.records[0]['actual_returncode']=1
  with self.assertRaisesRegex(ValueError,'causally qualified'):g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')])
 def test_unqualified_producer_trace_refused(self):
  g=self.generated_gate();g.records[0]['result']['status']='FAILED'
  with self.assertRaisesRegex(ValueError,'causally qualified'):g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')])
 def test_changed_producer_argv_refused(self):
  g=self.generated_gate();g.records[0]['command']=['WRONG']
  with self.assertRaisesRegex(ValueError,'causally qualified'):g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')])
 def test_changed_generated_hash_refused(self):
  g=self.generated_gate();g.records[0]['outputs'][0]['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'producer identity'):g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')])
 def test_wrong_generated_path_refused(self):
  g=self.generated_gate();g.plan['steps']['consumer']['generated_inputs'][0]['path']=str(self.fixture/'out/OTHER')
  with self.assertRaisesRegex(ValueError,'argv/producer'):g.before('consumer',g.plan['steps']['consumer']['command'])
 def test_duplicate_generated_producer_refused(self):
  g=self.generated_gate();g.records.append(copy.deepcopy(g.records[0]))
  with self.assertRaisesRegex(ValueError,'causally qualified'):g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')])
 def test_generated_postconsumer_change_rejected_by_parser(self):
  g=self.generated_gate();rows=g.input_policies(generated_inputs=[dict(path=str(self.data),producer='producer')]);original=self.data.read_bytes();self.data.write_bytes(b'CHANGED!')
  try:
   with self.assertRaisesRegex(ValueError,'changed prepinned'):parser.validate('99 unlink("/inert-source-only") = -1 ENOENT (No such file or directory)\n',dict(root_returncode=0,inputs=rows))
  finally:self.data.write_bytes(original)
 def test_generated_symlink_refused(self):
  g=self.generated_gate();alias=self.fixture/'out/link.fixture';alias.symlink_to(self.data)
  try:
   with self.assertRaisesRegex(ValueError,'owned regular'):g.input_policies(generated_inputs=[dict(path=str(alias),producer='producer')])
  finally:alias.unlink()
 def test_generated_outside_owned_root_refused(self):
  g=self.generated_gate()
  with self.assertRaisesRegex(ValueError,'owned regular'):g.input_policies(generated_inputs=[dict(path=str(self.N/'runner-plan.json.xz'),producer='producer')])
 def test_only_two_causal_consumers_manifested(self):
  rules={k:s['generated_inputs']for k,s in self.plan['steps'].items()if 'generated_inputs'in s};self.assertEqual(set(rules),{'scramble','descramble-check'});self.assertEqual(rules['scramble'][0]['producer'],'raw-program');self.assertEqual(rules['descramble-check'][0]['producer'],'scramble')
 def test_all14_sealers_source_family_closed(self):
  report=json.loads((self.N/'remaining-helper-coverage.json').read_text());self.assertTrue(report['all14_seal_family_same']);self.assertEqual(report['stdlib_whole_source_and_native_pins'],618);self.assertTrue(report['no_claim_remaining_actual_steps_replayed'])
 def test_new_resolved_pin_scope_exact(self):
  rows=json.loads((self.N/'root-reviewed-additions.json').read_text())['pins'];self.assertEqual(len(rows),5);self.assertEqual({r['resolved']for r in rows},{'/usr/share/zoneinfo/America/New_York','/opt/toolchains/dc/sh-elf/lib/bfd-plugins/libdep.so','/usr/lib/x86_64-linux-gnu/libbz2.so.1.0.4'})
 def test_diagnostic_is_precise_without_argv_dump(self):
  text=self.trace.replace('/bfd-plugins/libdep.so','/bfd-plugins/unknown.so')
  try:parser.validate(text,self.c)
  except ValueError as e:self.assertIn('PID=',str(e));self.assertIn('requested=',str(e));self.assertIn('resolved=',str(e));self.assertNotIn('argv',str(e))
  else:self.fail('unknown plugin accepted')
if __name__=='__main__':unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Retained02 exact base-link replay and narrow03 controls; never launch tool children."""
import copy,gzip,json,lzma,os,re,unittest
from pathlib import Path
import trace_closure792_03 as parser
import runner_trace792_03 as bridge
class ReplayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.N=Path(os.environ['RUNNER03_FIXTURE']);cls.B=Path('/root/probe/mipmap21-next792-link-20261022-02');cls.trace=(cls.B/'base-link.strace').read_text();cls.c=json.loads(gzip.decompress((cls.N/'retained02-base-contract.json.gz').read_bytes()));cls.plan=json.loads(lzma.decompress((cls.N/'runner-plan.json.xz').read_bytes()));cls.lines=cls.trace.splitlines(True);cls.creates=[l for l in cls.lines if '.cdtor.'in l and 'openat('in l];cls.unlinks=[l for l in cls.lines if '.cdtor.'in l and 'unlink('in l]
 def reject(self,text=None,c=None):
  with self.assertRaises((ValueError,OSError)):parser.validate(self.trace if text is None else text,self.c if c is None else c)
 def test_exact_actual02_positive(self):
  r=parser.validate(self.trace,self.c);self.assertEqual((r['events'],r['successful_executions'],r['distinct_prepinned_reads'],r['transient_data_files']),(1001,5,468,3));self.assertEqual(r['approved_writes'],[str(self.B/'out/re4dc-game.elf')])
 def test_missing_each_placeholder_contract(self):
  for profile in ['gcc_cdtor_c','gcc_cdtor_o']:
   c=copy.deepcopy(self.c);c['transient_data']=[r for r in c['transient_data']if r['profile']!=profile];self.reject(c=c)
 def test_same_pid_required_each_placeholder(self):
  for line in self.unlinks:self.reject(self.trace.replace(line,line.replace('1387925 ','1387999 ',1)))
 def test_wrong_creator_pid_each_placeholder(self):
  for line in self.creates:self.reject(self.trace.replace(line,line.replace('1387925 ','1387999 ',1)))
 def test_missing_exclusive_each_placeholder(self):
  for line in self.creates:self.reject(self.trace.replace(line,line.replace('|O_EXCL','')))
 def test_wrong_temp_suffix(self):self.reject(self.trace.replace('.cdtor.c','.arbitrary.c'))
 def test_outside_owned_root(self):
  for line in self.creates:
   path=re.search(r'"([^\"]+)"',line).group(1);self.reject(self.trace.replace(path,'/tmp/'+Path(path).name))
 def test_missing_unlink_each_placeholder(self):
  for line in self.unlinks:self.reject(self.trace.replace(line,''))
 def test_duplicate_unlink_each_placeholder(self):
  for line in self.unlinks:self.reject(self.trace+line)
 def test_unlink_before_create(self):
  for line in self.unlinks:self.reject(line+self.trace.replace(line,''))
 def test_unexpected_ctor_read(self):
  line=self.creates[0];extra=line.replace('O_RDWR|O_CREAT|O_EXCL, 0600','O_RDONLY');self.reject(self.trace.replace(line,line+extra))
 def test_unexpected_ctor_datawrite(self):
  line=self.creates[1];extra=line.replace('O_RDWR|O_CREAT|O_EXCL, 0600','O_WRONLY');self.reject(self.trace.replace(line,line+extra))
 def test_placeholder_count_drift(self):
  c=copy.deepcopy(self.c);next(r for r in c['transient_data']if r['profile']=='gcc_cdtor_c')['count']=2;self.reject(c=c)
 def test_missing_each_archive_alias(self):
  for policy in self.plan['input_aliases']:
   c=copy.deepcopy(self.c);r=next(r for r in c['inputs']if r['pin']['resolved']==policy['pin']['resolved']);r['aliases']=[x for x in r['aliases']if x not in policy['aliases']];self.reject(c=c)
 def test_unlisted_same_resolved_lexical_alias_refused(self):
  policy=self.plan['input_aliases'][0];alias=policy['aliases'][0];self.reject(self.trace.replace(alias,alias.replace('/lib/gcc/','/lib/./gcc/')))
 def test_changed_archive_pin(self):
  for policy in self.plan['input_aliases']:
   c=copy.deepcopy(self.c);r=next(r for r in c['inputs']if r['pin']['resolved']==policy['pin']['resolved']);r['pin']['sha256']='0'*64;self.reject(c=c)
 def test_unknown_resolved_plugin(self):
  line=next(l for l in self.lines if 'liblto_plugin.so'in l and 'openat('in l);self.reject(self.trace.replace(line,line.replace('liblto_plugin.so','liblto_plugin_BAD.so')))
 def test_extra_frontend_exec_refused(self):
  line=next(l for l in self.lines if 'execve('in l and '/collect2"'in l);self.reject(self.trace+line.replace('/collect2"','/cc1plus"',1))
 def test_changed_linker_option(self):
  self.assertIn('--gc-sections',self.trace);self.reject(self.trace.replace('--gc-sections','--no-gc-sections',1))
 def test_changed_ld_tool_alias(self):self.reject(self.trace.replace('/../../../../sh-elf/bin/ld','/../../../../sh-elf/bin/ld_BAD',1))
 def test_read_inventory_has_no_new_resolved_or_cdtor_reads(self):
  i=json.loads((self.N/'retained02-read-inventory.json').read_text());self.assertEqual(i['unknown_resolved_reads'],[]);self.assertEqual(i['cdtor_reads'],[]);self.assertEqual(len(i['exact_additional_aliases']),3);self.assertEqual(i['distinct_read_resolved'],468)
 def alias_gate(self):
  g=bridge.Gate.__new__(bridge.Gate);g.plan=copy.deepcopy(self.plan);g.root=Path(self.plan['future_root']);g.context=Path(self.plan['future_cwd']);g.frozen=[p['pin']for p in self.plan['input_aliases']];g.expected=[];return g
 def test_actual_bridge_exact_aliases_only(self):
  rows=self.alias_gate().input_policies();self.assertEqual(len(rows),3)
  for p in self.plan['input_aliases']:
   row=next(r for r in rows if r['pin']['resolved']==p['pin']['resolved']);self.assertTrue(set(p['aliases'])<=set(row['aliases']))
 def test_actual_bridge_wrong_alias_target_refused(self):
  g=self.alias_gate();g.plan['input_aliases'][0]['aliases']=[self.plan['input_aliases'][1]['pin']['path']]
  with self.assertRaisesRegex(ValueError,'target differs'):g.input_policies()
 def test_actual_bridge_alias_hash_change_refused(self):
  g=self.alias_gate();g.plan['input_aliases'][0]['pin']['sha256']='0'*64
  with self.assertRaises(ValueError):g.input_policies()
 def test_parser_only_two_profiles_added(self):
  old=Path(__file__).with_name('trace_closure792_02.py').read_text();new=Path(__file__).with_name('trace_closure792_03.py').read_text();needle="NONCES = {'gcc_resolution': r'cc[A-Za-z0-9]{6}\\.res',";addition="\n          'gcc_cdtor_c': r'cc[A-Za-z0-9]{6}\\.cdtor\\.c',\n          'gcc_cdtor_o': r'cc[A-Za-z0-9]{6}\\.cdtor\\.o',";self.assertEqual(new,old.replace(needle,needle+addition))
 def test_controller_only_fresh_namespace_and_bridge_delta(self):
  old=Path(__file__).with_name('next792_controller02.py').read_text();expected=old.replace('mipmap21-next792-link-20261022-02','mipmap21-next792-link-20261022-03').replace('mipmap21-next792-programme-20261022-02','mipmap21-next792-programme-20261022-03').replace('texture-consumers21-next792-runner02-20261022','texture-consumers21-next792-runner03-20261022').replace('NEXT792-LINK-ROOT-02-ALLOCATION.json','NEXT792-LINK-ROOT-03-ALLOCATION.json').replace('from runner_trace792_02 import Gate,compare_driver','from runner_trace792_03 import Gate,compare_driver');self.assertEqual(Path(__file__).with_name('next792_controller03.py').read_text(),expected)
 def test_03_all41_steps_remain_and_only_link_steps_get_two_rules(self):
  self.assertEqual(len(self.plan['order']),41)
  for name,step in self.plan['steps'].items():
   rules=[r for r in step['transient_data']if r['profile'].startswith('gcc_cdtor_')];self.assertEqual(len(rules),2 if name=='base-link'or name.startswith('shift-')else 0)
   for r in rules:self.assertEqual((r['count'],r['reads'],r['writes'],r['same_creator_pid']),(1,0,0,True));self.assertEqual(r['readers'],[]);self.assertEqual(r['writers'],[])
if __name__=='__main__':unittest.main(verbosity=2)

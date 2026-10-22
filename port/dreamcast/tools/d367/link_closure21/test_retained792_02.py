#!/usr/bin/env python3
"""Exact retained01 driver trace and focused lifecycle/source02 tests; no tool child."""
import ast,copy,gzip,hashlib,json,lzma,os,re,unittest
from pathlib import Path
import trace_closure792_02 as parser

class RetainedTraceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.N=Path(os.environ['RUNNER02_FIXTURE']);cls.trace=Path('/root/probe/mipmap21-next792-link-20261022-01/driver-pre.strace').read_text();cls.contract=json.loads(gzip.decompress((cls.N/'retained01-driver-pre-contract.json.gz').read_bytes()));cls.lines=cls.trace.splitlines(True);cls.create=cls.lines[-2];cls.unlink=cls.lines[-1];cls.path=re.search(r'"([^\"]+\.res)"',cls.create).group(1)
 def reject(self,text=None,contract=None):
  with self.assertRaises(ValueError):parser.validate(self.trace if text is None else text,self.contract if contract is None else contract)
 def test_exact_retained_trace_positive(self):
  r=parser.validate(self.trace,self.contract);self.assertEqual((r['events'],r['successful_executions'],r['transient_data_files']),(13,3,1));self.assertEqual(r['approved_writes'],[])
 def test_old_omission_reproduces_failure(self):
  c=copy.deepcopy(self.contract);c['transient_data']=[];self.reject(contract=c)
 def test_missing_unlink(self):self.reject(''.join(self.lines[:-1]))
 def test_duplicate_unlink(self):self.reject(self.trace+self.unlink)
 def test_unlink_before_create(self):self.reject(''.join(self.lines[:-2])+self.unlink+self.create)
 def test_changed_unlink_pid(self):self.reject(''.join(self.lines[:-1])+self.unlink.replace('1385594 ','1385595 ',1))
 def test_same_executable_other_pid_still_refused(self):
  gcc=next(l for l in self.lines if 'execve("/opt/toolchains/dc/sh-elf/bin/sh-elf-g++",'in l);gcc=gcc.replace('1385594 ','1385595 ',1);text=''.join(self.lines[:-1])+gcc+self.unlink.replace('1385594 ','1385595 ',1);c=copy.deepcopy(self.contract);c['executions'][2]['count']=2
  self.reject(text,c);c['transient_data'][0]['same_creator_pid']=False;self.assertEqual(parser.validate(text,c)['successful_executions'],4)
 def test_wrong_creator_pid(self):self.reject(''.join(self.lines[:-2])+self.create.replace('1385594 ','1385595 ',1)+self.unlink)
 def test_outside_owned_root(self):self.reject(self.trace.replace(self.path,'/tmp/cceCfTax.res'))
 def test_other_basename(self):self.reject(self.trace.replace(self.path,self.path.replace('cceCfTax.res','arbitrary.res')))
 def test_only_unlink_path_changed(self):self.reject(''.join(self.lines[:-1])+self.unlink.replace('cceCfTax.res','ccABCDEF.res'))
 def test_create_missing_exclusive(self):self.reject(self.trace.replace('O_RDWR|O_CREAT|O_EXCL','O_RDWR|O_CREAT'))
 def test_create_unapproved_cloexec(self):self.reject(self.trace.replace('O_RDWR|O_CREAT|O_EXCL','O_RDWR|O_CREAT|O_EXCL|O_CLOEXEC'))
 def test_unexpected_data_read(self):self.reject(''.join(self.lines[:-1])+self.create.replace('O_RDWR|O_CREAT|O_EXCL, 0600','O_RDONLY')+self.unlink)
 def test_unexpected_data_write(self):self.reject(''.join(self.lines[:-1])+self.create.replace('O_RDWR|O_CREAT|O_EXCL, 0600','O_WRONLY')+self.unlink)
 def test_access_after_unlink(self):self.reject(self.trace+self.create)
 def test_unrelated_immutable_unlink(self):self.reject(self.trace+self.unlink.replace(self.path,'/usr/lib/x86_64-linux-gnu/libc.so.6'))
 def test_missing_profile_count(self):
  c=copy.deepcopy(self.contract);c['transient_data'][0]['count']=2;self.reject(contract=c)
 def test_wrong_creator_role(self):
  c=copy.deepcopy(self.contract);c['transient_data'][0]['creators']=['/usr/lib/x86_64-linux-gnu/libc.so.6'];self.reject(contract=c)
 def test_unknown_plugin_open(self):self.reject(self.trace+self.create.replace(self.path,'/tmp/unapproved-plugin.so').replace('O_RDWR|O_CREAT|O_EXCL, 0600','O_RDONLY'))
 def test_changed_tool_argv_alias(self):self.reject(self.trace.replace('/opt/toolchains/dc/sh-elf/bin/sh-elf-g++','/opt/toolchains/dc/sh-elf/bin/sh-elf-gxx'))
 def test_changed_flag(self):
  self.assertIn('-###',self.trace);self.reject(self.trace.replace('-###','-##',1))
 def test_changed_environment(self):
  self.assertIn('RE4DC_OVL_ID=1',self.trace);self.reject(self.trace.replace('RE4DC_OVL_ID=1','RE4DC_OVL_ID=0',1))
 def test_changed_library_pin(self):
  c=copy.deepcopy(self.contract);row=next(r for r in c['inputs']if r['pin']['resolved']=='/usr/lib/x86_64-linux-gnu/libc.so.6');row['pin']['sha256']='0'*64;self.reject(contract=c)
 def test_02_concrete_proposal_rebases_only_owned_output_namespace(self):
  proposal=json.loads(Path('/root/re4data/private/texture-consumers21-next792-runner-20261022/concrete-qualified-link-proposal.json').read_text());plan=json.loads(lzma.decompress((self.N/'runner-plan.json.xz').read_bytes()));root=plan['future_root'];command=[arg.replace('/root/probe/mipmap21-next792-link-20261022-01',root)for arg in proposal['command']];self.assertEqual(command,plan['base_command']);self.assertEqual(command,plan['steps']['base-link']['command']);self.assertEqual(command+['-###'],plan['steps']['driver-pre']['command']);self.assertEqual(sum(x==root+'/objects/native_static-linked.o'for x in command),1)
  env={k:v.replace('/root/probe/mipmap21-next792-link-20261022-01',root)for k,v in proposal['environment'].items()};self.assertEqual(env['TMPDIR'],root+'/temp');source=Path(__file__).with_name('next792_controller02.py').read_text();self.assertIn("proposal['command']=[arg.replace",source);self.assertIn("proposal['environment']={key:value.replace",source)
 def test_no_unrelated_parser_changes(self):
  old=Path(__file__).with_name('trace_closure.py').read_text();new=Path(__file__).with_name('trace_closure792_02.py').read_text();expected=old.replace("executable not in transient_rules[state['rule']]['unlinkers']:","executable not in transient_rules[state['rule']]['unlinkers'] or (transient_rules[state['rule']].get('same_creator_pid',False) and event['PID'] != state['creator_PID']):").replace("dict(rule=index, writes=0, reads=0, unlinked=False)","dict(rule=index, writes=0, reads=0, unlinked=False, creator_PID=event['PID'])");self.assertEqual(new,expected)
 def test_02_plan_exact_narrow_delta(self):
  old=json.loads(lzma.decompress(Path('/root/re4data/private/texture-consumers21-next792-runner-20261022/runner-plan.json.xz').read_bytes()));new=json.loads(lzma.decompress((self.N/'runner-plan.json.xz').read_bytes()))
  def remap(v):
   if isinstance(v,str):return v.replace('mipmap21-next792-link-20261022-01','mipmap21-next792-link-20261022-02')
   if isinstance(v,list):return[remap(x)for x in v]
   if isinstance(v,dict):return{k:remap(x)for k,x in v.items()}
   return v
  expected=remap(old)
  for name in ['driver-pre','driver-post']:
   row=new['steps'][name]['transient_data'];self.assertEqual(len(row),1);self.assertEqual((row[0]['count'],row[0]['writes'],row[0]['reads'],row[0]['same_creator_pid']),(1,0,0,True));self.assertEqual(row[0]['writers'],[]);self.assertEqual(row[0]['readers'],[]);expected['steps'][name]['transient_data']=row
  expected['source_bridge_pins']=new['source_bridge_pins'];expected['scope']=new['scope'];self.assertEqual(new,expected);self.assertEqual(len(new['order']),41)
if __name__=='__main__':unittest.main(verbosity=2)

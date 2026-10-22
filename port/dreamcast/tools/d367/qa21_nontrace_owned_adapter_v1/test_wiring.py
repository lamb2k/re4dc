"""Focused actual adapter source tests, with injected pipes/backend/native APIs.
No WinDLL construction, native query, process spawn, realimage/state read or preflight.
"""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import ntpath
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

P=Path(__file__).parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
outer=load('test_outer_wiring',P/'outer-driver.py')
inner=load('test_inner_wiring',P/'inner-adapter.py')
wire=load('test_backend_wiring',P/'wiring-backend.py')
core=load('test_frozen_core',P/'guest-supervisor-core.py')
profile=json.loads((P/'guest-profile-v2.json').read_text())


class Pipe:
    def __init__(self,events,fail=False):self.events=events;self.data=b'';self.closed=False;self.fail=fail
    def write(self,data):self.events.append('write');self.data+=data
    def flush(self):
        self.events.append('flush')
        if self.fail:raise BrokenPipeError('injected release flush')
    def close(self):self.events.append('pipe_close');self.closed=True


class Service:
    def __init__(self,events,fail=False):
        self.events=events;self.fail=fail;self.hold=False;self.collector=types.SimpleNamespace(hold=False);self.stage='cleaned';self.sequence=6;self.records={1:{'actual_fixture':'retained source fixture only'}};self.authority={'sha256':'a'*64}
    def start(self):self.events.append('service_start')
    def close(self):
        self.events.append('service_close')
        if self.fail:raise RuntimeError('injected broker join failure')


def backend(events,pipe_fail=False):
    b=wire.WindowsBackend.__new__(wire.WindowsBackend);b.inner=types.SimpleNamespace(pid=10,stdin=Pipe(events,pipe_fail));b.invocation=Path('C:/owned/control');b.cap=Path('C:/owned/cap');b.job=77;b.guest=None;b.reference_service=None;b.reference_history={'available':False};b.allocation_path=wire.ALLOCATION;b.allocation_sha256='a'*64;b.tools_sha256='b'*64
    b.free=lambda:30000000000;b.global_count=lambda:0;b.evidence_bytes=lambda:10;b.check_deadlines=lambda:None;b.create_private_job=lambda:77;b.spawn_waiting=lambda cmd,job:b.inner;b.arm_deadlines=lambda inner:events.append('arm_deadlines');b.stop_private_job=lambda job:events.append('stop_job');b.wait=lambda inner:events.append('wait_inner');b.wait_private_job_empty=lambda job:events.append('job_empty');b.final_process_telemetry=lambda:{'available':False};b.close_release_pipe=lambda inner:inner.stdin.close()
    return b


class ReleaseAndClosureTests(unittest.TestCase):
    def test_actual_parent_release_starts_service_before_two_line_pipe(self):
        events=[];b=backend(events);service=Service(events)
        with patch.object(wire,'WindowsApi',return_value=object()),patch.object(wire,'Broker',return_value=service),patch.object(wire,'sha',return_value='c'*64):b.release(b.inner)
        self.assertEqual(events,['service_start','write','flush','pipe_close'])
        lines=b.inner.stdin.data.splitlines();self.assertEqual(lines[0],b'owned-job-ready');descriptor=json.loads(lines[1]);self.assertEqual(descriptor['context_sha256'],'c'*64)
        self.assertEqual(Path(descriptor['context_path']),b.invocation/'reference-hooks'/'context.json')
    def test_actual_core_release_exception_closes_service_before_backend_job(self):
        events=[];b=backend(events,True);service=Service(events)
        with patch.object(wire,'WindowsApi',return_value=object()),patch.object(wire,'Broker',return_value=service),patch.object(wire,'sha',return_value='c'*64),patch.object(wire.base.WindowsBackend,'stop_deadlines',lambda self:events.append('base_stop_deadlines')),patch.object(wire.base.WindowsBackend,'close_owned_handles',lambda self,*a:events.append('base_close_handles')):
            result=core.monitor(b,['NO-NATIVE-CHILD'])
        self.assertFalse(result['qualified']);self.assertIn('BrokenPipeError',result['error']);self.assertLess(events.index('arm_deadlines'),events.index('service_start'));self.assertLess(events.index('stop_job'),events.index('service_close'));self.assertLess(events.index('service_close'),events.index('base_stop_deadlines'));self.assertLess(events.index('service_close'),events.index('base_close_handles'));self.assertIsNone(b.reference_service)
    def test_actual_core_broker_close_failure_holds_and_never_closes_backend(self):
        events=[];b=backend(events,True);service=Service(events,True)
        with patch.object(wire,'WindowsApi',return_value=object()),patch.object(wire,'Broker',return_value=service),patch.object(wire,'sha',return_value='c'*64),patch.object(wire.base.WindowsBackend,'stop_deadlines',lambda self:events.append('BAD_DEADLINE_CLOSE')),patch.object(wire.base.WindowsBackend,'close_owned_handles',lambda self,*a:events.append('BAD_HANDLE_CLOSE')):
            result=core.monitor(b,['NO-NATIVE-CHILD'])
        self.assertFalse(result['qualified']);self.assertTrue(service.hold);self.assertTrue(service.collector.hold);self.assertIs(b.reference_service,service);self.assertNotIn('BAD_HANDLE_CLOSE',events);self.assertNotIn('BAD_DEADLINE_CLOSE',events)
    def test_actual_close_retains_guest_acquired_before_core_pid_notice(self):
        events=[];b=backend(events);b.guest={'pid':20,'handle':21};service=Service(events);b.reference_service=service;passed=[]
        with patch.object(wire.base.WindowsBackend,'close_owned_handles',lambda self,job,inner,guest:passed.append((job,guest))):b.close_owned_handles(77,b.inner,None)
        self.assertEqual(passed,[(77,b.guest)]);self.assertEqual(events,['service_close'])
    def test_actual_close_refuses_foreign_core_guest_after_service_join(self):
        events=[];b=backend(events);b.guest={'pid':20};b.reference_service=Service(events)
        with patch.object(wire.base.WindowsBackend,'close_owned_handles',side_effect=AssertionError('must not close')):
            with self.assertRaisesRegex(RuntimeError,'authority differs'):b.close_owned_handles(77,b.inner,{'pid':99})
        self.assertEqual(events,['service_close'])
    def test_repeated_service_close_is_safe_and_completed_receipt_requires_join(self):
        events=[];b=backend(events);b.reference_service=Service(events)
        with self.assertRaisesRegex(RuntimeError,'not closed'):b.reference_receipt()
        b.close_reference_service();b.close_reference_service();self.assertEqual(events,['service_close']);self.assertTrue(b.reference_receipt()['closed_after_join'])


class ReleaseParserTests(unittest.TestCase):
    def packet(self,data=None):return b'owned-job-ready\n'+json.dumps(data or {'context_path':'C:/owned/control/reference-hooks/context.json','context_sha256':'a'*64}).encode()+b'\n'
    def test_actual_inner_release_parser_accepts_exact_descriptor(self):self.assertEqual(inner.read_reference_release(io.BytesIO(self.packet()))['context_sha256'],'a'*64)
    def test_actual_inner_parser_rejects_missing_wrong_or_oversized_release(self):
        for value in (b'',b'wrong\n',b'owned-job-ready\n',b'owned-job-ready\n'+b'x'*4097):
            with self.subTest(value=value[:24]):
                with self.assertRaises((RuntimeError,ValueError)):inner.read_reference_release(io.BytesIO(value))
    def test_actual_inner_descriptor_types_and_extra_fields_refuse(self):
        for descriptor in ({'context_path':True,'context_sha256':'a'*64},{'context_path':'C:/x','context_sha256':True},{'context_path':'C:/x','context_sha256':'a'*64,'extra':1}):
            with self.subTest(descriptor=descriptor):
                with self.assertRaises(RuntimeError):inner.read_reference_release(io.BytesIO(self.packet(descriptor)))
    def test_actual_outer_parser_has_one_mode_and_execute_default_off(self):
        args=['--profile','PROFILE','--profile-sha256','p','--tools-sha256','t','--mode','return-door01','--seed','SEED','--root-allocation',str(wire.ALLOCATION),'--root-allocation-sha256','a']
        self.assertFalse(outer.parse_args(args).execute_root_allocation)
        for role in ('cold-shoot01','cinematic01','return-door-domains01'):
            copyargs=args[:];copyargs[copyargs.index('return-door01')]=role
            with self.subTest(role=role),patch('sys.stderr',io.StringIO()):
                with self.assertRaises(SystemExit):outer.parse_args(copyargs)
    def test_authority_path_cannot_be_template_or_arbitrary_file(self):
        with self.assertRaisesRegex(RuntimeError,'only exact'):wire.validate_authority(P/'FUTURE_ROOT_ALLOCATION_BYTES.json','a'*64,'b'*64,'C:/cap','C:/control')


def norm(path):return str(path).replace('\\','/').lower()


class SeedTests(unittest.TestCase):
    def check(self,frame=533,state=None,profile_pin=None):
        pin=json.loads((P/'SEED_CONTRACT.json').read_text());seed=Path(pin['seed']);profile_sha='4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b'
        row={'qualified':True,'profile_sha256':profile_sha,'program_sha256':outer.PROGRAM}
        checkpoint={'audit':{k:pin[k] for k in ('state_sha256','frame','room','log_head')},'state_edits':False,'parent':None};checkpoint['audit']['frame']=frame
        old_read=Path.read_text
        def read(path,*args,**kwargs):
            if norm(path).endswith('/cold-shoot01-control/qualification.json'):return json.dumps(row)
            if norm(path).endswith('/cold-shoot01/checkpoint.json'):return json.dumps(checkpoint)
            return old_read(path,*args,**kwargs)
        def hash_file(path,*args):return (state or pin['state_sha256']) if norm(path).endswith('disc.state') else pin['checkpoint_sha256']
        with patch.object(outer,'no_alias',lambda path:Path(str(path).replace('\\','/'))),patch.object(outer,'hash_file',hash_file),patch.object(Path,'read_text',read):outer.validate_seed(profile,'return-door01',seed,profile_pin or profile_sha)
    def test_exact_e81e_533_seed_positive(self):self.check()
    def test_wrong_state_frame_or_parent_profile_refuses(self):
        for change in ({'frame':534},{'state':'f'*64},{'profile_pin':'other'}):
            with self.subTest(change=change):
                with self.assertRaises(RuntimeError):self.check(**change)


class StaticWiringTests(unittest.TestCase):
    def test_exact_reviewed_hooks_and_frozen_core_guards_are_mirrored(self):
        reviewed=json.loads((P/'REVIEWED_COMPONENTS.json').read_text())
        for name,pin in reviewed['local_hooks'].items():self.assertEqual(hashlib.sha256((P/'reference-hooks'/name).read_bytes()).hexdigest(),pin)
        original=P.parent/'qa21_nontrace_domains_exit_v1'
        for name in ('guest-supervisor-core.py','windows-backend.py','controller-core.py','policies.py','input-deadlines.py','observe.py','observer-v2.py','layout-contract.py','capture-budget.py','global-ui-ABI-supplement.json','exact-log-symbols.json','guest-profile-v2.json'):
            self.assertEqual((P/name).read_bytes(),(original/name).read_bytes(),name)
    def test_all_original_inner_input_observer_watch_functions_unchanged(self):
        def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,ast.FunctionDef)}
        old=functions(P.parent/'qa21_nontrace_domains_exit_v1'/'inner-adapter.py');new=functions(P/'inner-adapter.py')
        for name in old:
            if name!='main':self.assertEqual(old[name],new[name],name)
    def test_reviewed_child_gate_positions_and_no_generic_unlink_remain(self):
        text=(P/'reference-hooks'/'checkpoint_runner18.child.py').read_text()
        self.assertLess(text.index('hooks.staged()'),text.index('    try:'+'\n'+'        proc = subprocess.Popen'))
        self.assertLess(text.index('hooks.guest_started(proc)'),text.index("(cap / 'flycast.pid').write_text"))
        self.assertNotIn('.unlink()',text)


class ReferenceApi:
    def __init__(self):
        self.contract=json.loads((P/'reference-hooks'/'COLLECTOR_CONTRACT.json').read_text());self.declarations=json.loads((P/'reference-hooks'/'retained-all-track-declarations.json').read_text());self.refs={};self.handles={};self.next=1;self.hashes=0;self.deletes=[]
        for image in self.contract['proposed_phase_rules']['prelaunch']['paths']:
            for name,record in self.declarations['files'].items():
                key=ntpath.normcase(ntpath.normpath(ntpath.join(ntpath.dirname(image),name)));pin=record['references'][0]
                self.refs[key]={'native_file_id':record['native_file_id'].split()[-1],'volume':55,'size':pin['bytes'],'mtime_ns':pin['mtime_ns'],'allocated':512,'links':3 if name=='track03.iso' else 14,'attributes':0,'deleted':False,'directory':False}
    def open_file(self,path,delete=False,directory=False):
        key=ntpath.normcase(ntpath.normpath(str(path)))
        if not directory and key not in self.refs:raise FileNotFoundError(key)
        self.next+=1;self.handles[self.next]=key;return self.next
    def final_path(self,h):return self.handles[h]
    def stat(self,h):return copy.deepcopy(self.refs[self.handles[h]])
    def names(self,path):return sorted(k for k in self.refs if k.endswith('track03.iso'))
    def hash_file(self,h,guard):
        guard();self.hashes+=1;record=self.declarations['files'][ntpath.basename(self.handles[h])]
        return {'sha256':record['sha256'],'bytes':record['references'][0]['bytes']}
    def close(self,h):del self.handles[h]
    def delete_opened_link(self,h):self.deletes.append(h);raise AssertionError('preflight cannot delete')


class VirtualPath:
    api=None;metadata={}
    def __init__(self,path):self.key=ntpath.normcase(ntpath.normpath(str(path)))
    def __str__(self):return self.key
    def __truediv__(self,name):return VirtualPath(ntpath.join(self.key,name))
    def __eq__(self,other):return isinstance(other,VirtualPath) and self.key==other.key
    def samefile(self,other):return self.api.refs[self.key]['native_file_id']==self.api.refs[other.key]['native_file_id']
    def read_text(self):return json.dumps(self.metadata[self.key])
    def stat(self):
        row=self.api.refs[self.key];return types.SimpleNamespace(st_size=row['size'],st_mtime_ns=row['mtime_ns'],st_nlink=row['links'])


class ActualReferenceExtensionTests(unittest.TestCase):
    def run_extension(self,extra=False):
        api=ReferenceApi();VirtualPath.api=api;refs=profile['retained_source_references'];meta={}
        meta[VirtualPath(refs['qualification']['path']).key]={'qualified':False,'source':outer.SOURCE,'program_sha256':outer.PROGRAM,'elf_sha256':outer.ELF,'image_sha256':outer.IMAGE}
        meta[VirtualPath(refs['owner']['path']).key]={'lane':'qa21-combined-regression','programme':outer.PROGRAM,'image':outer.IMAGE}
        extra_receipt=json.loads((P/'EXTRA_REFERENCE_RECEIPT.json').read_text());meta[VirtualPath(extra_receipt['path']).key]={k:v for k,v in extra_receipt.items() if k not in ('path','sha256')};VirtualPath.metadata=meta
        hashes={VirtualPath(refs[k]['path']).key:refs[k]['sha256'] for k in ('qualification','owner')};hashes[VirtualPath(extra_receipt['path']).key]=extra_receipt['sha256']
        if extra:
            row=copy.deepcopy(next(v for k,v in api.refs.items() if k.endswith('track03.iso')));api.refs[VirtualPath('C:/unexpected/track03.iso').key]=row
            for key,value in api.refs.items():
                if key.endswith('track03.iso'):value['links']=4
        def fake_hash(path,guard=lambda:None):guard();return hashes[VirtualPath(path).key]
        with patch.object(outer,'no_alias',lambda path:VirtualPath(path)),patch.object(outer,'hash_file',fake_hash),patch('native_reference_api.WindowsApi',return_value=api):
            try:result=outer.validate_source_references(profile,VirtualPath(profile['disc']['path']),lambda:None,lambda path:int(api.refs[path.key]['native_file_id'],16))
            except BaseException:
                self.assertEqual(api.handles,{});self.assertEqual(api.deletes,[]);raise
        self.assertEqual(api.handles,{});self.assertEqual(api.deletes,[]);return result,api
    def test_actual_outer_extension_uses_real_collector_three_reference_proof(self):
        result,api=self.run_extension();self.assertEqual(len(result['before']['names']),3);self.assertEqual(api.hashes,3);self.assertEqual(result['before'],result['after'])
    def test_actual_outer_extension_fourth_ref_refuses_and_closes_no_unlink(self):
        with self.assertRaises(RuntimeError):self.run_extension(extra=True)


class DefaultAndAuthorityTests(unittest.TestCase):
    def test_actual_outer_default_off_before_hash_or_backend_import(self):
        with patch.object(outer,'os',types.SimpleNamespace(name='nt')),patch.object(outer,'parse_args',return_value=types.SimpleNamespace(execute_root_allocation=False)),patch.object(outer,'hash_file',side_effect=AssertionError('no hash before default guard')),patch.object(outer,'load',side_effect=AssertionError('no runtime import before default guard')):
            with self.assertRaisesRegex(RuntimeError,'default-off'):outer.main()
    def test_actual_backend_missing_authority_prevents_native_base_constructor(self):
        with patch.object(wire,'validate_authority',side_effect=FileNotFoundError('fixture missing ROOT allocation')),patch.object(wire.base.WindowsBackend,'__init__',side_effect=AssertionError('native constructor forbidden')):
            with self.assertRaises(FileNotFoundError):wire.WindowsBackend(Path('C:/cap'),Path('C:/control'),'disc','e'*64,None,allocation=wire.ALLOCATION,allocation_sha256='a'*64,tools_sha256='b'*64)


class FutureContractTests(unittest.TestCase):
    def test_literal_future_root_bytes_match_real_authority_schema_without_root_io(self):
        raw=(P/'FUTURE_ROOT_ALLOCATION_BYTES.json').read_bytes();request=json.loads((P/'LAUNCH_REQUEST.json').read_text());original=Path.read_bytes;reads=[]
        def read(path):
            if path==wire.ALLOCATION:reads.append(str(path));return raw
            return original(path)
        with patch.object(Path,'read_bytes',read):
            proof=wire.validate_authority(wire.ALLOCATION,request['root_allocation_sha256'],request['tools_sha256'],Path(request['cap']),Path(request['control']))
        self.assertEqual(len(reads),1);self.assertEqual(proof['contents']['attempt_limit'],1)
        self.assertEqual(proof['contents']['tools_sha256'],hashlib.sha256((P/'source-manifest.json').read_bytes()).hexdigest())
    def test_literal_future_command_parser_and_pins_exact(self):
        request=json.loads((P/'LAUNCH_REQUEST.json').read_text());args=outer.parse_args(request['argv'][3:])
        self.assertTrue(args.execute_root_allocation);self.assertEqual(args.mode,'return-door01');self.assertEqual(args.tools_sha256,request['tools_sha256']);self.assertEqual(args.profile_sha256,'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b');self.assertEqual(args.root_allocation,wire.ALLOCATION)
        self.assertEqual(hashlib.sha256((P/'FUTURE_ROOT_ALLOCATION_BYTES.json').read_bytes()).hexdigest(),args.root_allocation_sha256)
        self.assertEqual(request['allocation_status'],'UNALLOCATED; source-only future request')


if __name__=='__main__':unittest.main(verbosity=2)

"""Focused injected-API tests. No WinDLL, native query, image, preflight or guest.
Exercises concrete Collector/Broker/Proxy and actual child main/launch-try AST.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import ntpath
import sys
import types
import unittest
from unittest.mock import patch

P=Path(__file__).parent
sys.path.insert(0,str(P))
from native_reference_api import canonical,WindowsApi
from reference_collector import Collector,Refusal
from parent_reference_broker import Broker,allocation_proof,PROFILE,SOURCE
from child_reference_proxy import Proxy

CONTRACT=json.loads((P/'COLLECTOR_CONTRACT.json').read_text())
DECL=json.loads((P/'retained-all-track-declarations.json').read_text())


class Api:
    def __init__(self,phase='staged_owned'):
        self.refs={};self.opened={};self.next=1;self.closed=[];self.deleted=[];self.mutate=None;self.hash_count=0;self.calls=[];self.processes={};self.pids=[10];self.duplicates={}
        for image in CONTRACT['proposed_phase_rules'][phase]['paths']:
            for name,item in DECL['files'].items():
                pin=item['references'][0];path=canonical(ntpath.join(ntpath.dirname(image),name))
                self.refs[path]=dict(volume=55,native_file_id=item['native_file_id'].split()[-1],size=pin['bytes'],mtime_ns=pin['mtime_ns'],allocated=500,links=4 if name=='track03.iso' else 15,attributes=0,deleted=False,directory=False)
        self.recount()
    def recount(self):
        for path,stat in self.refs.items():stat['links']=sum(v['native_file_id']==stat['native_file_id'] for v in self.refs.values()) if path.endswith('track03.iso') else 12+sum(p.endswith(ntpath.basename(path)) for p in self.refs)
    def open_file(self,path,delete=False,directory=False):
        path=canonical(path);self.next+=1;self.opened[self.next]=(path,delete,directory)
        if not directory and path not in self.refs:raise FileNotFoundError(path)
        self.calls.append(('open',path,delete,directory));return self.next
    def final_path(self,h):return self.opened[h][0]
    def close(self,h):self.closed.append(h);self.opened.pop(h,None)
    def stat(self,h):return copy.deepcopy(self.refs[self.opened[h][0]])
    def names(self,path):return sorted(p for p in self.refs if p.endswith('track03.iso'))
    def hash_file(self,h,guard):
        guard();self.hash_count+=1;name=ntpath.basename(self.opened[h][0]);decl=DECL['files'][name]
        if self.mutate:self.mutate(self)
        guard();return {'sha256':decl['sha256'],'bytes':decl['references'][0]['bytes']}
    def delete_opened_link(self,h):
        path,delete,_=self.opened[h]
        if not delete:raise RuntimeError('no DELETE access')
        self.deleted.append(path);del self.refs[path];self.close(h);self.recount()
    def process(self,h,job,pinned=None,require_live=False):
        value=copy.deepcopy(self.processes[h]);self.calls.append(('process',h,job,require_live))
        if job!=77:raise Refusal('wrong job')
        if pinned and any(value[k]!=pinned[k] for k in ('pid','start_filetime','path')):raise Refusal('birth/path changed')
        if require_live and value['phase']!='live':raise Refusal('not live')
        return value
    def job_pids(self,job):return self.pids[:]
    def duplicate(self,inner,remote):self.calls.append(('duplicate',inner,remote));return self.duplicates[remote]
    def now_filetime(self):return 10000100


def proc(pid=10,path='C:/Python/python.exe',phase='live'):
    return dict(pid=pid,start_filetime=100,exit_filetime=200 if phase=='exited' else 0,path=canonical(path),phase=phase,wait_status=0 if phase=='exited' else 258,kernel_100ns=0,user_100ns=0)


def collector(phase='staged_owned'):
    api=Api(phase);return api,Collector(api,CONTRACT,DECL,lambda:None)


class CollectorTests(unittest.TestCase):
    def test_full_native_refs_and_hashes(self):
        api,c=collector();r=c.validate('staged_owned')
        self.assertEqual(len(r['before']['references']),12);self.assertEqual(len(r['hashes']),3)
        self.assertEqual(r['before'],r['after']);self.assertEqual(api.hash_count,3)
    def test_no_delete_access_held_during_staged_or_live_guest(self):
        api,c=collector();c.validate('staged_owned');c.validate('live_owned')
        self.assertFalse(any(call[2] for call in api.calls if call[0]=='open'))
    def test_fifth_name_before_hash_preserves_fourth(self):
        api,c=collector();api.refs[canonical('C:/foreign/track03.iso')]=copy.deepcopy(next(v for k,v in api.refs.items() if k.endswith('track03.iso')));api.recount()
        with self.assertRaises(Refusal):c.validate('staged_owned')
        self.assertTrue(c.hold);self.assertEqual(api.deleted,[]);self.assertEqual(api.hash_count,0)
    def test_race_between_hashes_preserves_fourth(self):
        api,c=collector()
        def mutate(a):
            a.mutate=None;a.refs[canonical('C:/foreign/track03.iso')]=copy.deepcopy(next(v for k,v in a.refs.items() if k.endswith('track03.iso')));a.recount()
        api.mutate=mutate
        with self.assertRaises(Refusal):c.validate('staged_owned')
        self.assertTrue(c.hold);self.assertEqual(api.deleted,[])
    def test_replaced_common_alias_refuses(self):
        api,c=collector();path=canonical(ntpath.join(c.cap,'track02.raw'));api.refs[path]['native_file_id']='0x'+'f'*32
        with self.assertRaises(Refusal):c.validate('staged_owned')
        self.assertEqual(api.deleted,[])
    def test_stat_race_across_hash_refuses(self):
        api,c=collector()
        def mutate(a):
            a.mutate=None
            for s in a.refs.values():s['allocated']+=1
        api.mutate=mutate
        with self.assertRaisesRegex(Refusal,'race'):c.validate('staged_owned')
    def test_hash_or_guard_exception_latches_hold(self):
        api,c=collector();c.guard=lambda:(_ for _ in ()).throw(OSError('disk unavailable'))
        with self.assertRaises(Refusal):c.validate('staged_owned')
        self.assertTrue(c.hold);self.assertEqual(api.deleted,[])
    def test_cleanup_only_three_owned_aliases_after_actual_callback(self):
        api,c=collector();calls=[]
        def stopped():calls.append('actual');return {'guest':proc(20,phase='exited'),'reader':proc(30,phase='exited')}
        r=c.cleanup(stopped)
        self.assertGreaterEqual(len(calls),5);self.assertEqual(len(r['removed_only_owned']),3)
        self.assertTrue(all(ntpath.dirname(p)==canonical(c.cap) for p in api.deleted))
        self.assertTrue(api.deleted[-1].endswith('track03.iso'));self.assertEqual(len(api.names('unused')),3)
    def test_pending_exit_never_deletes(self):
        api,c=collector()
        def pending():raise Refusal('actual wait258 pending')
        with self.assertRaises(Refusal):c.cleanup(pending)
        self.assertEqual(api.deleted,[]);self.assertTrue(c.hold)
    def test_hold_forbids_cleanup_even_with_success_claim(self):
        api,c=collector();c.hold=True
        with self.assertRaises(Refusal):c.cleanup(lambda:{'caller_boolean':True})
        self.assertEqual(api.deleted,[])


class Backend:
    def __init__(self):
        self.job=77;self.inner=types.SimpleNamespace(pid=10,_handle=11);self.inner_identity={k:proc()[k] for k in ('pid','start_filetime','path')};self.stops=[];self.guest=None;self.emu_sha='e'*64;self.clock=lambda:1.0
    def check_deadlines(self):pass
    def free(self):return 30000000000
    def evidence_bytes(self):return 1000
    def global_count(self):return 0
    def stop_private_job(self,job):self.stops.append(job)


def broker():
    b=Broker.__new__(Broker);b.backend=Backend();b.api=Api();b.cap=Path(CONTRACT['new_output_contract_proposal']['output_name'])
    b.job=77;b.inner=b.backend.inner;b.inner_pin=b.backend.inner_identity;b.api.processes[11]=proc();b.guest=None;b.reader=None;b.hold=False;b.collector=types.SimpleNamespace(hold=False);b.authority={'sha256':'a'*64};return b


class BrokerTests(unittest.TestCase):
    def test_retained_guest_birth_path_job_not_boolean(self):
        b=broker();b.cap=Path('C:/owned');b.api.duplicates[91]=21;b.api.processes[21]=proc(20,'C:/owned/flycast.exe');b.api.pids=[10,20]
        with patch('parent_reference_broker.digest',return_value=b.backend.emu_sha):r=b.retain_remote({'process':{'pid':20,'remote_handle':91}},'guest')
        self.assertEqual(r['pin']['start_filetime'],100);self.assertEqual(b.backend.guest['handle'],21)
        self.assertIn(('duplicate',11,91),b.api.calls)
    def test_remote_pid_handle_disagreement_fails(self):
        b=broker();b.api.duplicates[91]=21;b.api.processes[21]=proc(99,'C:/owned/flycast.exe')
        with self.assertRaises(Refusal):b.retain_remote({'process':{'pid':20,'remote_handle':91}},'guest')
        self.assertIn(21,b.api.closed)
    def test_cleanup_actual_pending_wait_refuses(self):
        b=broker();b.guest={'handle':21,'pin':{k:proc(20)[k] for k in ('pid','start_filetime','path')}};b.reader={'handle':31,'pin':{k:proc(30)[k] for k in ('pid','start_filetime','path')}}
        b.api.processes[21]=proc(20,phase='pending');b.api.processes[31]=proc(30,phase='exited')
        with self.assertRaises(Refusal):b.stopped()
    def test_job_foreign_member_refuses_even_inner_alive(self):
        b=broker();b.api.pids=[10,999]
        with self.assertRaises(Refusal):b.inner_proof()
    def test_exact_source_birth_change_refuses(self):
        b=broker();b.api.processes[11]['start_filetime']=101
        with self.assertRaises(Refusal):b.inner_proof()
    def test_resource_and_refusal_stop_only_retained_job(self):
        b=broker();b.backend.free=lambda:19394461695
        with self.assertRaises(Refusal):b.resource_guard()
        r=b.fail(Refusal('fullnames race'));self.assertFalse(r['ok']);self.assertTrue(b.hold);self.assertTrue(b.collector.hold);self.assertEqual(b.backend.stops,[77])
    def test_nonnumeric_or_boolean_remote_proofs_refuse(self):
        b=broker()
        for value in ({'separate_root_allocation':True},{'process':{'pid':True,'remote_handle':91}}):
            with self.assertRaises(Refusal):b.retain_remote(value,'guest')


class MemoryPath:
    store={}
    def __init__(self,text):self.text=str(text)
    def __str__(self):return self.text
    def __truediv__(self,name):return MemoryPath(self.text+'/'+name)
    def exists(self):return self.text in self.store
    def mkdir(self,**kw):
        if self.exists():raise FileExistsError(self.text)
        self.store[self.text]='DIR'
    def read_text(self):return self.store[self.text]
    def write_text(self,data):self.store[self.text]=data


class Hooks:
    def __init__(self,event):self.event=event;self.created=[];self.events=[];self.hold=False
    def before_create(self,*args):self.events.append('before_create')
    def cap_created(self):self.events.append('cap_created')
    def link_created(self,src,dst):self.created.append((str(src),str(dst)))
    def staged(self):
        self.events.append('staged')
        if self.event=='staged':self.hold=True;raise Refusal('staged native race')
    def guest_started(self,p):self.events.append('guest');self.hold=True;raise Refusal('actual guest identity refusal')
    def reader_started(self,p):raise AssertionError('reader must not start')
    def cleanup(self,status):
        self.events.append('cleanup')
        if self.hold:raise Refusal('preserve fourth')


def runner_ast():
    return next(n for n in ast.parse((P/'checkpoint_runner18.child.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')


class RunnerBoundaryTests(unittest.TestCase):
    def test_actual_main_staged_refusal_before_launch_try_preserves_all(self):
        MemoryPath.store={'C:/disc/disc.gdi':'gdi','C:/disc/track01.bin':'1','C:/disc/track02.raw':'2','C:/disc/track03.iso':'3'}
        args=types.SimpleNamespace(seconds=41,cap='C:/newcap',base=None,disc='C:/disc')
        parser=types.SimpleNamespace(add_argument=lambda *a,**kw:None,parse_args=lambda:args)
        hooks=Hooks('staged');launches=[]
        def link(src,dst):MemoryPath.store[str(dst)]=MemoryPath.store[str(src)]
        gl={'argparse':types.SimpleNamespace(ArgumentParser=lambda:parser),'Path':MemoryPath,'os':types.SimpleNamespace(environ={},link=link,path=types.SimpleNamespace(getsize=lambda p:1)),
            'REFERENCE_HOOKS':hooks,'__file__':'child.py','TRACKS':('disc.gdi','track01.bin','track02.raw','track03.iso'),
            'shutil':types.SimpleNamespace(copyfile=link),'subprocess':types.SimpleNamespace(Popen=lambda *a,**kw:launches.append(a))}
        exec(compile(ast.Module(body=[runner_ast()],type_ignores=[]),'actual-child-main','exec'),gl)
        with self.assertRaisesRegex(Refusal,'staged'):gl['main']()
        self.assertEqual(launches,[]);self.assertEqual(len(hooks.created),3)
        self.assertTrue(all('C:/newcap/'+n in MemoryPath.store for n in ('track01.bin','track02.raw','track03.iso')))
    def test_actual_launch_try_guest_refusal_cannot_unlink_fourth(self):
        node=next(n for n in runner_ast().body if isinstance(n,ast.Try) and any(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='proc' for t in x.targets) for x in n.body))
        class Child:
            def __init__(self):self.pid=20;self.returncode=None
            def poll(self):return self.returncode
            def wait(self,timeout):self.returncode=0;return 0
        child=Child();hooks=Hooks('guest');closed=[];stream=types.SimpleNamespace(close=lambda:closed.append(1))
        gl={'proc':None,'reader':None,'subprocess':types.SimpleNamespace(Popen=lambda *a,**kw:child,STDOUT=1,TimeoutExpired=TimeoutError),
            'cap':MemoryPath('C:/newcap'),'serial':stream,'log':stream,'logerr':stream,'startup':None,'env':None,'hooks':hooks,
            'rep':{'status':'STARTING','errors':[]},'windows_of':lambda p:[],'time':types.SimpleNamespace(monotonic=lambda:1.0),
            'Exception':Exception,'last_growth':0,'t0':0,'now':lambda:'now','json':json}
        with self.assertRaisesRegex(Refusal,'preserve fourth'):exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-launch-try','exec'),gl)
        self.assertEqual(child.returncode,0);self.assertNotIn('C:/newcap/flycast.pid',MemoryPath.store);self.assertEqual(closed,[1,1,1]);self.assertEqual(hooks.events,['guest','cleanup'])
    def test_disarmed_actual_main_refuses_before_cap_mutation(self):
        MemoryPath.store={};args=types.SimpleNamespace(seconds=41,cap='C:/newcap')
        parser=types.SimpleNamespace(add_argument=lambda *a,**kw:None,parse_args=lambda:args)
        gl={'argparse':types.SimpleNamespace(ArgumentParser=lambda:parser),'Path':MemoryPath,'os':types.SimpleNamespace(environ={}), 'REFERENCE_HOOKS':None}
        exec(compile(ast.Module(body=[runner_ast()],type_ignores=[]),'actual-main','exec'),gl)
        with self.assertRaisesRegex(RuntimeError,'DISARMED'):gl['main']()
        self.assertEqual(MemoryPath.store,{})
    def test_no_unlink_and_gate_order_in_actual_source(self):
        n=runner_ast();text=(P/'checkpoint_runner18.child.py').read_text()
        self.assertFalse(any(isinstance(x,ast.Attribute) and x.attr=='unlink' for x in ast.walk(n)))
        self.assertLess(text.index('hooks.staged()'),text.index('    try:'+'\n'+'        proc = subprocess.Popen'))
        self.assertLess(text.index('hooks.guest_started(proc)'),text.index("(cap / 'flycast.pid').write_text"))
        self.assertIn('hooks.before_spawn()  # outside launch try',text)
    def test_production_runner_frozen_and_profile4c_unchanged(self):
        origin=json.loads((P/'runner-origin.json').read_text())
        self.assertEqual(hashlib.sha256((P/'checkpoint_runner18.original.txt').read_bytes()).hexdigest(),origin['sha256'])
        self.assertEqual(hashlib.sha256((P/'guest-profile-v2.json').read_bytes()).hexdigest(),'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b')
    def test_windows_native_operations_remain_lazy(self):
        # Actual constructor rejects POSIX; no DLL instantiated by any test.
        if sys.platform!='win32':
            with self.assertRaisesRegex(RuntimeError,'Windows only'):WindowsApi()
        tree=ast.parse((P/'native_reference_api.py').read_text())
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='WinDLL' for n in tree.body))

class NativeMethodTests(unittest.TestCase):
    def api(self,exited=0,status=258,member=1,path='C:/Python/python.exe'):
        api=WindowsApi.__new__(WindowsApi)
        def times(h,*values):
            for dest,value in zip(values,(100,exited,10,20)):dest._obj.value=value
            return 1
        def query(h,flags,buf,size):buf.value=path;return 1
        def in_job(h,job,result):result._obj.value=member;return 1
        api.k=types.SimpleNamespace(GetProcessId=lambda h:10,GetProcessTimes=times,WaitForSingleObject=lambda h,t:status,QueryFullProcessImageNameW=query,IsProcessInJob=in_job)
        return api
    def test_actual_native_method_live_birth_and_job(self):
        api=self.api();r=api.process(11,77,require_live=True)
        self.assertEqual(r['phase'],'live');self.assertEqual(r['start_filetime'],100);self.assertEqual(r['path'],canonical('C:/Python/python.exe'))
    def test_actual_native_method_pending_timestamp_not_signaled(self):
        api=self.api(exited=200,status=258);pin={k:proc()[k] for k in ('pid','start_filetime','path')}
        self.assertEqual(api.process(11,77,pin)['phase'],'pending')
        with self.assertRaisesRegex(RuntimeError,'not live'):api.process(11,77,pin,require_live=True)
    def test_actual_native_method_signaled_exit_requires_existing_pin(self):
        api=self.api(exited=200,status=0);pin={k:proc()[k] for k in ('pid','start_filetime','path')}
        self.assertEqual(api.process(11,77,pin)['phase'],'exited')
        with self.assertRaisesRegex(RuntimeError,'new identity after process exit'):api.process(11,77)
    def test_actual_native_method_failed_wait_and_foreign_job(self):
        with self.assertRaisesRegex(RuntimeError,'wait failed'):self.api(status=0xffffffff).process(11,77)
        with self.assertRaisesRegex(RuntimeError,'outside exact private job'):self.api(member=0).process(11,77)
    def test_actual_native_open_reparse_and_path_alias_refuse(self):
        api=WindowsApi.__new__(WindowsApi);closed=[]
        api.k=types.SimpleNamespace(CreateFileW=lambda *a:55,CloseHandle=lambda h:closed.append(h) or 1)
        api.stat=lambda h:{'attributes':0x400};api.final_path=lambda h:canonical('C:/source/file')
        with self.assertRaisesRegex(RuntimeError,'reparse'):api.open_file('C:/source/file')
        self.assertEqual(closed,[55]);api.stat=lambda h:{'attributes':0};api.final_path=lambda h:canonical('C:/foreign/file')
        with self.assertRaisesRegex(RuntimeError,'alias'):api.open_file('C:/source/file')
        self.assertEqual(closed,[55,55])
    def test_actual_native_delete_exact_retained_handle_only(self):
        api=WindowsApi.__new__(WindowsApi);calls=[]
        def disposition(h,kind,info,length):calls.append((h,kind,info._obj.value));return 1
        api.k=types.SimpleNamespace(SetFileInformationByHandle=disposition,CloseHandle=lambda h:calls.append(('close',h)) or 1)
        api.delete_opened_link(55);self.assertEqual(calls,[(55,4,1),('close',55)])


class ProxyTests(unittest.TestCase):
    def proxy(self):
        import threading
        x=Proxy.__new__(Proxy);x.context={'nonce':'n','inner_pid':10};x.control=MemoryPath('control');x.clock=lambda:0;x.origin=0;x.sequence=0;x.hold=False;x.lock=threading.RLock();return x
    def test_actual_request_refusal_latches_and_never_authorizes_cleanup(self):
        x=self.proxy();MemoryPath.store={'control/response-001.json':json.dumps({'ok':False,'error':'native fullnames race'})};writes=[]
        with patch('child_reference_proxy.os.getpid',return_value=10),patch('child_reference_proxy.atomic_new',side_effect=lambda path,data:writes.append((str(path),data))):
            with self.assertRaises(Refusal):x.request('staged',{'created_links':[]})
            with self.assertRaises(Refusal):x.cleanup('RUN_COMPLETE')
        self.assertTrue(x.hold);self.assertEqual(len(writes),2);self.assertEqual(writes[-1][0],'control/REFERENCE-HOLD.json')
    def test_actual_request_wrong_nonce_or_sequence_latches(self):
        x=self.proxy();MemoryPath.store={'control/response-001.json':json.dumps({'ok':True,'nonce':'foreign','sequence':1,'event':'staged'})}
        with patch('child_reference_proxy.os.getpid',return_value=10),patch('child_reference_proxy.atomic_new',return_value=None):
            with self.assertRaisesRegex(Refusal,'stale/foreign'):x.request('staged',{})
        self.assertTrue(x.hold)
    def test_actual_creator_marker_is_exclusive_actual_context_data(self):
        x=self.proxy();x.cap=MemoryPath('cap');x.context.update(runner_sha256='r'*64,allocation_sha256='a'*64);written=[]
        with patch('child_reference_proxy.os.getpid',return_value=10),patch('child_reference_proxy.atomic_new',side_effect=lambda path,data:written.append((str(path),data))):x.cap_created()
        self.assertEqual(written,[('cap/.owned-reference-creator.json',{'inner_pid':10,'nonce':'n','runner_sha256':'r'*64,'allocation_sha256':'a'*64})])


class BrokerCollectorFlowTests(unittest.TestCase):
    def setup_flow(self):
        b=broker();b.api=Api('prelaunch');b.api.processes[11]=proc();b.contract=CONTRACT
        b.cap=Path(CONTRACT['proposed_phase_rules']['staged_owned']['paths'][-1]).parent
        b.collector=Collector(b.api,CONTRACT,DECL,b.resource_guard);b.stage='new';b.sequence=0;b.nonce='nonce';b.runner_sha='r'*64;b.records={};b.marker_handle=None
        b.marker_proof=lambda:{'actual_fixture_marker':'native marker tested independently'}
        def call(event,payload):return b.dispatch({'nonce':b.nonce,'sequence':b.sequence+1,'pid':10,'event':event,'payload':payload})
        payload={'cap':canonical(str(b.cap)),'disc':canonical(b.collector.source),'runner_sha256':b.runner_sha,'seconds':41,'period':0,'name':'return-door01'}
        with patch('parent_reference_broker.Path.exists',return_value=False):self.assertTrue(call('prelaunch',payload)['ok'])
        staged=Api('staged_owned');b.api.refs=staged.refs
        ledger=[{'source':canonical(ntpath.join(b.collector.source,n)),'destination':canonical(str(b.cap/n))} for n in ('track01.bin','track02.raw','track03.iso')]
        return b,call,ledger
    def test_actual_broker_and_collector_four_link_lifecycle_to_owned_cleanup(self):
        b,call,ledger=self.setup_flow();self.assertTrue(call('staged',{'created_links':ledger})['ok']);self.assertTrue(call('before_spawn',{})['ok'])
        b.api.duplicates[91]=21;b.api.processes[21]=proc(20,str(b.cap/'flycast.exe'));b.api.pids=[10,20]
        with patch('parent_reference_broker.digest',return_value=b.backend.emu_sha):r=call('guest',{'process':{'pid':20,'remote_handle':91}})
        self.assertTrue(r['ok']);self.assertEqual(b.backend.guest['identity']['start_filetime'],100)
        b.api.duplicates[92]=31;b.api.processes[31]=proc(30);b.api.pids=[10,20,30]
        self.assertTrue(call('reader',{'process':{'pid':30,'remote_handle':92}})['ok'])
        b.api.processes[21].update(phase='exited',wait_status=0,exit_filetime=200)
        b.api.processes[31].update(phase='exited',wait_status=0,exit_filetime=200);b.api.pids=[10]
        r=call('cleanup',{'run_status':'RUN_COMPLETE'});self.assertTrue(r['ok']);self.assertEqual(b.stage,'cleaned')
        self.assertEqual(len(b.api.names('source')),3);self.assertEqual(len(b.api.deleted),3)
    def test_actual_staged_collector_refusal_holds_all_current_links(self):
        b,call,ledger=self.setup_flow();b.api.refs[canonical('C:/unexpected/track03.iso')]=copy.deepcopy(next(v for k,v in b.api.refs.items() if k.endswith('track03.iso')));b.api.recount()
        r=call('staged',{'created_links':ledger});self.assertFalse(r['ok']);self.assertTrue(b.hold);self.assertEqual(b.api.deleted,[])
        self.assertEqual(b.backend.stops,[77]);self.assertEqual(len(b.api.names('source')),5)
    def test_actual_creation_ledger_failure_holds_without_hash_or_delete(self):
        b,call,ledger=self.setup_flow();before=b.api.hash_count;r=call('staged',{'created_links':ledger[:-1]})
        self.assertFalse(r['ok']);self.assertEqual(b.api.hash_count,before);self.assertEqual(b.api.deleted,[]);self.assertEqual(len(b.api.names('source')),4)


class AllocationSchemaTests(unittest.TestCase):
    def proof(self,change=None):
        expected={'profile_sha256':PROFILE,'tools_sha256':'b'*64,'contract_sha256':'c'*64,'runner_sha256':'d'*64,'tools_source':SOURCE,
                  'semantic_mode':'return-door01','cap':canonical('C:/cap'),'control':canonical('C:/control'),'attempt_limit':1,
                  'inner_seconds':41,'input_cutoff_seconds':40.75,'private_job_seconds':47.0,'absolute_actual_seconds':47.5,
                  'evidence_cap_bytes':60000000,'runtime_floor_bytes':19394461696}
        if change:expected.update(change)
        raw=json.dumps(expected).encode();sha=hashlib.sha256(raw).hexdigest()
        with patch('parent_reference_broker.Path.read_bytes',return_value=raw):return allocation_proof('NOT-REAL',sha,'C:/cap','C:/control','c'*64,'d'*64,'b'*64)
    def test_actual_allocation_file_hash_and_schema_proof(self):
        r=self.proof();self.assertEqual(r['contents']['attempt_limit'],1);self.assertEqual(len(r['sha256']),64)
    def test_actual_schema_never_accepts_true_as_one_attempt(self):
        with self.assertRaisesRegex(Refusal,'types'):self.proof({'attempt_limit':True})
    def test_actual_allocation_disallows_changed_bounds(self):
        with self.assertRaises(Refusal):self.proof({'absolute_actual_seconds':48.0})


if __name__=='__main__':unittest.main(verbosity=2)
